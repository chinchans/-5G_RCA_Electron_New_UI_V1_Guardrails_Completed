"""Fine-tuned RoBERTa domain classifier for TSG prompt guardrails.

Active classes (logit-masked at inference):
  TELECOM_WORKBENCH — in-scope telecom / test-automation prompts
  OUT_OF_SCOPE      — off-topic / general knowledge prompts

PROMPT_INJECTION (model index 2) is masked out — Llama Prompt Guard handles
injection / jailbreak detection separately. The checkpoint still has 3 output
heads; we slice logits to indices 0 and 1 and softmax only over those.

Also provides Dynamic-Anchor + Anchor-Injected Sliding Window scanning to catch
planted out-of-scope sentences without false-positiving generic auxiliary steps.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.guardrails.config import (
    GUARDRAIL_CLASSIFIER_DEVICE,
    GUARDRAIL_CLASSIFIER_MAX_LENGTH,
    GUARDRAIL_CLASSIFIER_MAX_SENTENCES,
    GUARDRAIL_CLASSIFIER_MAX_WINDOWS,
    GUARDRAIL_CLASSIFIER_MIN_CONFIDENCE,
    GUARDRAIL_CLASSIFIER_MODEL_PATH,
    GUARDRAIL_CLASSIFIER_WINDOW_SIZE,
    GUARDRAILS_FAIL_OPEN_ON_MODEL_ERROR,
    GUARDRAILS_TSG_CLASSIFIER_WINDOW_ENABLED,
)

logger = logging.getLogger(__name__)

LABEL_TELECOM = "TELECOM_WORKBENCH"
LABEL_OUT_OF_SCOPE = "OUT_OF_SCOPE"
LABEL_PROMPT_INJECTION = "PROMPT_INJECTION"  # masked at inference; kept for API compat

DEFAULT_ID2LABEL = {
    0: LABEL_TELECOM,
    1: LABEL_OUT_OF_SCOPE,
    2: LABEL_PROMPT_INJECTION,
}

# Domain-only heads used for softmax (ignore PROMPT_INJECTION = index 2).
DOMAIN_CLASS_IDS: Tuple[int, int] = (0, 1)
DOMAIN_ID2LABEL = {
    0: LABEL_TELECOM,
    1: LABEL_OUT_OF_SCOPE,
}

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")

# Domain tokens that prove a sentence still belongs to the workbench.
_TELECOM_SIGNAL_RE = re.compile(
    r"\b(?:"
    r"5g|lte|nr|nsa|rrc|nas|attach|detach|ue|enb|gnb|gnb\-du|du\-?\d*|cu\-?\d*|"
    r"oran|o\-ran|3gpp|amf|smf|upf|ran|ngap|s1ap|e2ap|f1ap|handover|ltm|"
    r"registration|pdu\s*session|bearer|cell|radio|qos|n3|xn|inter\-gnb|"
    r"telecom|oai|openair|pytest|test\s*case|test\s*script"
    r")\b",
    re.I,
)

# Generic engineering steps that look OOS alone but are valid with a telecom anchor.
_AUXILIARY_ACTION_RE = re.compile(
    r"\b(?:"
    r"save|export|write|store|parse|filter|extract|format|validate|verify|"
    r"generate|create|produce|collect|capture|log|logs|output|json|csv|yaml|"
    r"xml|table|summary|report|workspace|directory|file|files|timestamp|"
    r"status\s*code|200\s*ok|structured|results?"
    r")\b",
    re.I,
)

# Short greetings / review fluff that should not veto a telecom payload.
_FLUFF_RE = re.compile(
    r"^\s*(?:"
    r"hi\b|hello\b|hey\b|thanks\b|thank you\b|please review\b|"
    r"good (?:morning|afternoon|evening)\b|"
    r"i have a question\b|regarding my setup\b|team[,:]?"
    r")",
    re.I,
)


@dataclass
class ClassifierResult:
    predicted_label: str
    confidence_score: float
    probabilities: Dict[str, float] = field(default_factory=dict)
    available: bool = True
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "predicted_label": self.predicted_label,
            "confidence_score": self.confidence_score,
            "probabilities": self.probabilities,
            "available": self.available,
            "detail": self.detail,
        }


@dataclass
class WindowScanResult:
    """Aggregate result of full-text + dynamic-anchor sliding-window scan."""

    predicted_label: str
    confidence_score: float
    probabilities: Dict[str, float] = field(default_factory=dict)
    available: bool = True
    detail: str = ""
    blocked: bool = False
    mode: str = "full_text"  # full_text | window_windows | no_telecom_anchor
    sentence_count: int = 0
    windows_scanned: int = 0
    anchor_index: Optional[int] = None
    anchor_preview: str = ""
    blocked_window_index: Optional[int] = None
    blocked_window_preview: str = ""
    full_text: Optional[ClassifierResult] = None

    def to_classifier_result(self) -> ClassifierResult:
        return ClassifierResult(
            predicted_label=self.predicted_label,
            confidence_score=self.confidence_score,
            probabilities=self.probabilities,
            available=self.available,
            detail=self.detail,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "predicted_label": self.predicted_label,
            "confidence_score": self.confidence_score,
            "probabilities": self.probabilities,
            "available": self.available,
            "detail": self.detail,
            "blocked": self.blocked,
            "mode": self.mode,
            "sentence_count": self.sentence_count,
            "windows_scanned": self.windows_scanned,
            "anchor_index": self.anchor_index,
            "anchor_preview": self.anchor_preview,
            "blocked_window_index": self.blocked_window_index,
            "blocked_window_preview": self.blocked_window_preview,
            "full_text": self.full_text.to_dict() if self.full_text else None,
        }


class GuardrailClassifier:
    """Lazy-loaded local RoBERTa sequence classifier."""

    def __init__(self, model_path: Optional[Path] = None) -> None:
        self.model_path = Path(model_path or GUARDRAIL_CLASSIFIER_MODEL_PATH)
        self._tokenizer = None
        self._model = None
        self._id2label: Dict[int, str] = dict(DEFAULT_ID2LABEL)
        self._device = "cpu"
        self.available = False
        self._load_error: Optional[str] = None
        self._lock = threading.Lock()

    def load(self) -> bool:
        if self._model is not None:
            return self.available

        with self._lock:
            if self._model is not None:
                return self.available

            try:
                import torch
                from transformers import AutoModelForSequenceClassification, AutoTokenizer

                if not self.model_path.is_dir():
                    raise FileNotFoundError(f"Classifier model directory not found: {self.model_path}")

                weights = self.model_path / "model.safetensors"
                if not weights.is_file():
                    raise FileNotFoundError(f"Missing model weights: {weights}")

                preferred = (GUARDRAIL_CLASSIFIER_DEVICE or "auto").lower().strip()
                if preferred == "cuda" and torch.cuda.is_available():
                    self._device = "cuda"
                elif preferred == "cpu":
                    self._device = "cpu"
                else:
                    self._device = "cuda" if torch.cuda.is_available() else "cpu"

                logger.info(
                    "Loading fine-tuned guardrail classifier from %s (device=%s)",
                    self.model_path,
                    self._device,
                )
                self._tokenizer = AutoTokenizer.from_pretrained(
                    str(self.model_path),
                    local_files_only=True,
                )
                self._model = AutoModelForSequenceClassification.from_pretrained(
                    str(self.model_path),
                    local_files_only=True,
                )
                self._model.to(self._device)
                self._model.eval()

                raw_id2label = getattr(self._model.config, "id2label", None) or {}
                if raw_id2label:
                    self._id2label = {
                        int(idx): str(label).upper()
                        for idx, label in raw_id2label.items()
                    }

                self.available = True
                self._load_error = None
                logger.info(
                    "Guardrail classifier loaded (classes=%s)",
                    sorted(self._id2label.items()),
                )
                return True
            except Exception as exc:
                self._load_error = str(exc)
                self.available = False
                self._tokenizer = None
                self._model = None
                logger.warning("Guardrail classifier unavailable: %s", exc)
                return False

    def classify(self, text: str) -> ClassifierResult:
        """Classify a prompt as TELECOM_WORKBENCH vs OUT_OF_SCOPE only.

        Raw model still emits 3 logits; index 2 (PROMPT_INJECTION) is masked and
        softmax is recomputed over the remaining domain classes.
        """
        prompt = (text or "").strip()
        if not prompt:
            return ClassifierResult(
                predicted_label=LABEL_TELECOM,
                confidence_score=1.0,
                probabilities={
                    LABEL_TELECOM: 1.0,
                    LABEL_OUT_OF_SCOPE: 0.0,
                    LABEL_PROMPT_INJECTION: 0.0,
                },
                available=True,
                detail="empty_prompt",
            )

        if not self.load():
            return ClassifierResult(
                predicted_label="UNKNOWN",
                confidence_score=0.0,
                probabilities={},
                available=False,
                detail=self._load_error or "model_unavailable",
            )

        import torch
        import torch.nn.functional as F

        assert self._tokenizer is not None and self._model is not None

        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=GUARDRAIL_CLASSIFIER_MAX_LENGTH,
            padding=False,
        )
        inputs = {key: value.to(self._device) for key, value in inputs.items()}

        with torch.no_grad():
            logits = self._model(**inputs).logits[0]
            # Mask PROMPT_INJECTION: keep only TELECOM (0) and OUT_OF_SCOPE (1).
            domain_logits = logits[list(DOMAIN_CLASS_IDS)]
            domain_probs = F.softmax(domain_logits, dim=-1)

        probabilities: Dict[str, float] = {
            LABEL_TELECOM: float(domain_probs[0].item()),
            LABEL_OUT_OF_SCOPE: float(domain_probs[1].item()),
            LABEL_PROMPT_INJECTION: 0.0,
        }

        pred_local_idx = int(torch.argmax(domain_probs).item())
        pred_idx = DOMAIN_CLASS_IDS[pred_local_idx]
        predicted_label = DOMAIN_ID2LABEL[pred_idx]
        confidence = float(probabilities[predicted_label])

        return ClassifierResult(
            predicted_label=predicted_label,
            confidence_score=confidence,
            probabilities=probabilities,
            available=True,
            detail="ok_domain_2class",
        )


_classifier: Optional[GuardrailClassifier] = None
_classifier_lock = threading.Lock()


def get_guardrail_classifier() -> GuardrailClassifier:
    global _classifier
    if _classifier is None:
        with _classifier_lock:
            if _classifier is None:
                _classifier = GuardrailClassifier()
    return _classifier


def ensure_guardrail_classifier_loaded() -> bool:
    return get_guardrail_classifier().load()


def classify_prompt(text: str) -> ClassifierResult:
    return get_guardrail_classifier().classify(text)


def classifier_status() -> Dict[str, Any]:
    clf = get_guardrail_classifier()
    return {
        "available": clf.available,
        "model_path": str(clf.model_path),
        "load_error": clf._load_error,
        "fail_open": GUARDRAILS_FAIL_OPEN_ON_MODEL_ERROR,
    }


def split_sentences(text: str, *, limit: Optional[int] = None) -> List[str]:
    """Lightweight sentence splitter (no NLTK dependency).

    ``limit`` caps returned sentences. Pass None for a full split (used by OOS veto
    so planted off-topic lines near the end of long templates are not dropped).
    """
    raw = (text or "").strip()
    if not raw:
        return []

    parts: List[str] = []
    for chunk in _SENTENCE_SPLIT_RE.split(raw):
        sentence = " ".join(chunk.split()).strip()
        # Normalize bullet / markdown list markers for downstream checks
        sentence = re.sub(r"^(?:[-*•]|\d+[.)])\s+", "", sentence)
        if sentence:
            parts.append(sentence)

    if not parts and raw:
        return [raw]
    if limit is None:
        return parts
    return parts[: max(1, int(limit))]


def _preview(text: str, limit: int = 160) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _has_telecom_signals(text: str) -> bool:
    return bool(_TELECOM_SIGNAL_RE.search(text or ""))


def _is_auxiliary_action(text: str) -> bool:
    return bool(_AUXILIARY_ACTION_RE.search(text or ""))


def _is_fluff_sentence(text: str) -> bool:
    sentence = (text or "").strip()
    if not sentence:
        return True
    if _FLUFF_RE.search(sentence):
        return True
    # Very short non-question fragments without domain terms
    words = sentence.split()
    return len(words) <= 6 and "?" not in sentence and not _has_telecom_signals(sentence)


def _is_contentful_oos_candidate(text: str) -> bool:
    """True when a sentence looks like a real off-topic implant worth model checks.

    Length alone is not enough: long Test Case templates contain many generic
    instruction lines ("Ensure no major point is missed") that RoBERTa labels
    OUT_OF_SCOPE in isolation. Require a stronger off-topic cue.
    """
    sentence = (text or "").strip()
    sentence = re.sub(r"^(?:[-*•]|\d+[.)])\s+", "", sentence)
    if not sentence:
        return False
    if _has_telecom_signals(sentence):
        return False
    if _is_auxiliary_action(sentence):
        return False

    lowered = sentence.lower()

    # Strong topical implants first (before short-fluff heuristic).
    if re.search(
        r"\b(?:movies?|films?|netflix|cinema|vibes|night out|"
        r"french revolution|revolution in \d{3,4}|bake|baking|recipe|lava cake|"
        r"trip|travel|vacation|hotel|itinerary|weather|"
        r"bluetooth|headphones|samsung tv|bose|"
        r"cryptocurrency|bitcoin|stock market|poem|poetry)\b",
        lowered,
    ):
        return True

    if _is_fluff_sentence(sentence):
        return False

    # Direct off-topic asks / recommendations
    if re.match(
        r"^(?:how|what|why|where|when|who|whom|which)\b",
        lowered,
    ) and not re.search(
        r"\b(?:test|script|case|log|command|interface|scenario|json|document|coverage)\b",
        lowered,
    ):
        return True

    if re.match(
        r"^(?:recommend|suggest|plan|bake|cook|write a poem)\b",
        lowered,
    ):
        return True

    return False


def _is_confident_label(result: ClassifierResult, label: str) -> bool:
    return (
        result.available
        and (result.predicted_label or "").upper() == label
        and result.confidence_score >= GUARDRAIL_CLASSIFIER_MIN_CONFIDENCE
    )


def _local_window_bounds(
    index: int,
    sentence_count: int,
    window_size: int,
) -> Tuple[int, int]:
    """Return [start, end) for a window centered near sentence ``index``."""
    if sentence_count <= 0:
        return 0, 0
    if sentence_count <= window_size:
        return 0, sentence_count
    left = max(0, window_size // 2)
    start = max(0, index - left)
    end = min(sentence_count, start + window_size)
    start = max(0, end - window_size)
    return start, end


def build_anchor_injected_windows(
    sentences: List[str],
    anchor_index: int,
    *,
    window_size: int = 3,
) -> List[Tuple[int, str]]:
    """Build unique anchor-injected sliding windows.

    Each window is: dynamic_telecom_anchor + local (prev/current/next) sentences,
    without duplicating the anchor when it already sits inside the local span.
    """
    if not sentences:
        return []

    size = max(1, int(window_size or 3))
    anchor = sentences[anchor_index]
    windows: List[Tuple[int, str]] = []
    seen = set()

    for i in range(len(sentences)):
        start, end = _local_window_bounds(i, len(sentences), size)
        local = sentences[start:end]
        if anchor_index < start or anchor_index >= end:
            chunk_parts = [anchor, *local]
        else:
            chunk_parts = list(local)
        chunk = " ".join(chunk_parts).strip()
        if not chunk or chunk in seen:
            continue
        seen.add(chunk)
        windows.append((i, chunk))
        if len(windows) >= max(1, GUARDRAIL_CLASSIFIER_MAX_WINDOWS):
            break

    return windows


def find_telecom_anchor(
    sentences: List[str],
    *,
    classify_fn=None,
) -> Tuple[Optional[int], Optional[ClassifierResult]]:
    """Return index of the first sentence classified as TELECOM_WORKBENCH."""
    classify_fn = classify_fn or classify_prompt
    for idx, sentence in enumerate(sentences):
        # Prefer explicit domain vocabulary before spending a model call when possible,
        # but still require model confirmation for anchor selection.
        result = classify_fn(sentence)
        if _is_confident_label(result, LABEL_TELECOM):
            return idx, result
        # Fallback: strong telecom lexicon + not confidently OOS
        if _has_telecom_signals(sentence) and not _is_confident_label(result, LABEL_OUT_OF_SCOPE):
            return idx, result
    # Lexicon-only fallback when the model never emits TELECOM on short fragments
    for idx, sentence in enumerate(sentences):
        if _has_telecom_signals(sentence):
            return idx, ClassifierResult(
                predicted_label=LABEL_TELECOM,
                confidence_score=0.6,
                probabilities={
                    LABEL_TELECOM: 0.6,
                    LABEL_OUT_OF_SCOPE: 0.4,
                    LABEL_PROMPT_INJECTION: 0.0,
                },
                available=True,
                detail="telecom_lexicon_anchor_fallback",
            )
    return None, None


def _sentence_oos_veto(
    sentences: List[str],
    *,
    classify_fn=None,
    max_classifications: int = 48,
) -> Optional[Tuple[int, str, ClassifierResult]]:
    """Block contentful alone-OOS sentences that are not fluff/auxiliary/telecom.

    Scans the full sentence list (including the tail of long templates) but only
    runs the model on cheap prefiltered candidates.
    """
    classify_fn = classify_fn or classify_prompt
    classified = 0
    # Scan tail-first: planted OOS is usually appended near the end of templates.
    order = list(range(len(sentences) - 1, -1, -1))
    for idx in order:
        sentence = sentences[idx]
        if not _is_contentful_oos_candidate(sentence):
            continue
        result = classify_fn(sentence)
        classified += 1
        if _is_confident_label(result, LABEL_OUT_OF_SCOPE):
            return idx, sentence, result
        if classified >= max_classifications:
            break
    return None


def _sentences_for_window_scan(sentences: List[str]) -> List[str]:
    """Keep window scan bounded while always retaining the prompt head and tail."""
    max_n = max(1, GUARDRAIL_CLASSIFIER_MAX_SENTENCES)
    if len(sentences) <= max_n:
        return list(sentences)
    head = max_n // 2
    tail = max_n - head
    selected = list(sentences[:head]) + list(sentences[-tail:])
    # Preserve order / uniqueness
    seen = set()
    out: List[str] = []
    for sentence in selected:
        if sentence in seen:
            continue
        seen.add(sentence)
        out.append(sentence)
    return out


def classify_prompt_with_windows(text: str) -> WindowScanResult:
    """Full-text classify + dynamic-anchor windows + sentence-level OOS veto.

    Why sentence veto exists:
      This RoBERTa checkpoint still labels ``telecom_anchor + cake`` as TELECOM
      (attention dilution). Anchor-injected windows alone therefore miss planted
      OOS. We additionally classify suspicious sentences in isolation and block
      only contentful OOS lines that are not fluff/auxiliary/telecom fragments.

    Why we split \"all sentences\" vs \"window sentences\":
      Long default Test Case templates exceed the old 80-sentence cap, so planted
      movie/history lines at the end were never scanned. Veto now uses the full
      split; windows stay bounded via head+tail sampling.
    """
    prompt = (text or "").strip()
    full = classify_prompt(prompt)
    if not full.available:
        return WindowScanResult(
            predicted_label=full.predicted_label,
            confidence_score=full.confidence_score,
            probabilities=full.probabilities,
            available=False,
            detail=full.detail,
            blocked=False,
            mode="unavailable",
            full_text=full,
        )

    all_sentences = split_sentences(prompt, limit=None)
    if (
        not GUARDRAILS_TSG_CLASSIFIER_WINDOW_ENABLED
        or len(all_sentences) <= 1
    ):
        blocked = _is_confident_label(full, LABEL_OUT_OF_SCOPE)
        return WindowScanResult(
            predicted_label=full.predicted_label,
            confidence_score=full.confidence_score,
            probabilities=full.probabilities,
            available=True,
            detail=full.detail or "full_text_only",
            blocked=blocked,
            mode="full_text",
            sentence_count=len(all_sentences),
            windows_scanned=0,
            full_text=full,
        )

    # Fast reject pure OOS payloads
    if _is_confident_label(full, LABEL_OUT_OF_SCOPE):
        return WindowScanResult(
            predicted_label=full.predicted_label,
            confidence_score=full.confidence_score,
            probabilities=full.probabilities,
            available=True,
            detail="full_text_out_of_scope",
            blocked=True,
            mode="full_text",
            sentence_count=len(all_sentences),
            windows_scanned=0,
            full_text=full,
        )

    window_sentences = _sentences_for_window_scan(all_sentences)
    anchor_index, anchor_result = find_telecom_anchor(window_sentences)
    if anchor_index is None:
        # Try full list lexicon/model anchor before giving up
        anchor_index_full, anchor_result = find_telecom_anchor(all_sentences)
        if anchor_index_full is None:
            return WindowScanResult(
                predicted_label=LABEL_OUT_OF_SCOPE,
                confidence_score=max(full.confidence_score, 0.9),
                probabilities={
                    LABEL_TELECOM: 0.0,
                    LABEL_OUT_OF_SCOPE: 1.0,
                    LABEL_PROMPT_INJECTION: 0.0,
                },
                available=True,
                detail="no_telecom_anchor",
                blocked=True,
                mode="no_telecom_anchor",
                sentence_count=len(all_sentences),
                windows_scanned=0,
                full_text=full,
            )
        # Remap to window sentence list if possible
        anchor_sentence = all_sentences[anchor_index_full]
        if anchor_sentence in window_sentences:
            anchor_index = window_sentences.index(anchor_sentence)
        else:
            window_sentences = [anchor_sentence, *window_sentences]
            anchor_index = 0

    # Primary planted-OOS defense: scan ALL sentences (tail-first)
    veto = _sentence_oos_veto(all_sentences)
    if veto is not None:
        veto_index, veto_sentence, veto_result = veto
        return WindowScanResult(
            predicted_label=LABEL_OUT_OF_SCOPE,
            confidence_score=veto_result.confidence_score,
            probabilities=veto_result.probabilities,
            available=True,
            detail="sentence_out_of_scope",
            blocked=True,
            mode="sentence_veto",
            sentence_count=len(all_sentences),
            windows_scanned=0,
            anchor_index=anchor_index,
            anchor_preview=_preview(window_sentences[anchor_index]),
            blocked_window_index=veto_index,
            blocked_window_preview=_preview(veto_sentence),
            full_text=full,
        )

    windows = build_anchor_injected_windows(
        window_sentences,
        anchor_index,
        window_size=GUARDRAIL_CLASSIFIER_WINDOW_SIZE,
    )

    windows_scanned = 0
    for window_index, chunk in windows:
        windows_scanned += 1
        result = classify_prompt(chunk)
        if not result.available:
            continue

        label = (result.predicted_label or "").upper()
        if label == LABEL_OUT_OF_SCOPE and result.confidence_score >= GUARDRAIL_CLASSIFIER_MIN_CONFIDENCE:
            return WindowScanResult(
                predicted_label=LABEL_OUT_OF_SCOPE,
                confidence_score=result.confidence_score,
                probabilities=result.probabilities,
                available=True,
                detail="window_out_of_scope",
                blocked=True,
                mode="anchor_windows",
                sentence_count=len(all_sentences),
                windows_scanned=windows_scanned,
                anchor_index=anchor_index,
                anchor_preview=_preview(window_sentences[anchor_index]),
                blocked_window_index=window_index,
                blocked_window_preview=_preview(chunk),
                full_text=full,
            )

    return WindowScanResult(
        predicted_label=LABEL_TELECOM,
        confidence_score=(
            anchor_result.confidence_score
            if anchor_result
            else full.confidence_score
        ),
        probabilities=full.probabilities
        if full.predicted_label == LABEL_TELECOM
        else {
            LABEL_TELECOM: 1.0,
            LABEL_OUT_OF_SCOPE: 0.0,
            LABEL_PROMPT_INJECTION: 0.0,
        },
        available=True,
        detail="anchor_windows_passed",
        blocked=False,
        mode="anchor_windows",
        sentence_count=len(all_sentences),
        windows_scanned=windows_scanned,
        anchor_index=anchor_index,
        anchor_preview=_preview(window_sentences[anchor_index]),
        full_text=full,
    )
