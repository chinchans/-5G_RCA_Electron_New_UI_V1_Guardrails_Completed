"""
Local NLI groundedness checks using cross-encoder/nli-deberta-v3-small.

Validates that extracted claims (recursive LLM output or appended clause text)
are semantically supported by the corresponding 3GPP clause file content.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.guardrails.config import (
    GUARDRAILS_ENABLED,
    HF_TOKEN,
    NLI_CONTRADICTION_THRESHOLD,
    NLI_GROUNDEDNESS_ENABLED,
    NLI_MAX_PAIRS,
    NLI_MAX_PREMISE_CHARS,
    NLI_MODEL,
    NLI_SKIP_ON_MODEL_ERROR,
    NLI_STRICT,
)

logger = logging.getLogger(__name__)

RECURSIVE_MARKER = "RECURSIVE EXTRACTION RESULTS"
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
MIN_SENTENCE_CHARS = 25
MIN_WORD_LEN = 3
MODIFICATION_TAG_RE = re.compile(r"\[MODIFICATION\s+\d+:\s*(\w+)\]\s*", re.IGNORECASE)
MIN_SOURCE_ALIGN_SCORE = 20.0

# cross-encoder/nli-deberta-v3-small label order
NLI_LABELS = ("contradiction", "entailment", "neutral")


@dataclass
class NliPairResult:
    premise_preview: str
    hypothesis_preview: str
    contradiction: float
    entailment: float
    neutral: float
    top_label: str
    clause_id: Optional[str] = None
    hypothesis_text: str = ""
    line_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clause_id": self.clause_id,
            "premise_preview": self.premise_preview,
            "hypothesis_preview": self.hypothesis_preview,
            "hypothesis_text": self.hypothesis_text,
            "line_number": self.line_number,
            "contradiction": round(self.contradiction, 4),
            "entailment": round(self.entailment, 4),
            "neutral": round(self.neutral, 4),
            "top_label": self.top_label,
        }


@dataclass
class NliGroundednessResult:
    available: bool
    pairs_checked: int = 0
    contradictions: List[NliPairResult] = field(default_factory=list)
    neutral_findings: List[NliPairResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    load_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        if self.metadata.get("advisory_only"):
            return True
        return not self.errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "pairs_checked": self.pairs_checked,
            "passed": self.passed,
            "contradictions": [c.to_dict() for c in self.contradictions],
            "neutral_findings": [n.to_dict() for n in self.neutral_findings],
            "warnings": self.warnings,
            "errors": self.errors,
            "load_error": self.load_error,
            "metadata": self.metadata,
            "nli_highlights": build_nli_highlights(self),
        }


class _NliCrossEncoder:
    """Lazy-loaded cross-encoder for NLI groundedness."""

    def __init__(self) -> None:
        self._model = None
        self.available = False
        self._load_error: Optional[str] = None
        self._label_ids: Dict[str, int] = {name: idx for idx, name in enumerate(NLI_LABELS)}

    def load(self) -> bool:
        if self._model is not None:
            return self.available
        try:
            from sentence_transformers import CrossEncoder

            kwargs: Dict[str, Any] = {}
            if HF_TOKEN:
                kwargs["token"] = HF_TOKEN

            logger.info("Loading NLI cross-encoder: %s", NLI_MODEL)
            self._model = CrossEncoder(NLI_MODEL, **kwargs)
            self.available = True
            logger.info("NLI cross-encoder loaded successfully")
        except Exception as exc:
            self._load_error = str(exc)
            self.available = False
            logger.warning("Failed to load NLI model %s: %s", NLI_MODEL, exc)
        return self.available

    def predict_probs(self, pairs: Sequence[Tuple[str, str]]) -> List[Tuple[float, float, float]]:
        if not self._model or not pairs:
            return []

        import numpy as np

        logits = self._model.predict(list(pairs), batch_size=8, show_progress_bar=False)
        logits = np.asarray(logits, dtype=float)
        if logits.ndim == 1:
            logits = logits.reshape(1, -1)

        # Stable softmax per row
        logits = logits - logits.max(axis=1, keepdims=True)
        exp = np.exp(logits)
        probs = exp / exp.sum(axis=1, keepdims=True)

        c_idx = self._label_ids["contradiction"]
        e_idx = self._label_ids["entailment"]
        n_idx = self._label_ids["neutral"]
        return [(float(row[c_idx]), float(row[e_idx]), float(row[n_idx])) for row in probs]


_nli_model = _NliCrossEncoder()


def _split_sentences(text: str) -> List[str]:
    parts = SENTENCE_SPLIT_RE.split(text.strip())
    sentences: List[str] = []
    for part in parts:
        cleaned = " ".join(part.split())
        if len(cleaned) >= MIN_SENTENCE_CHARS:
            sentences.append(cleaned)
    return sentences


def _word_set(text: str) -> set[str]:
    return {
        w.lower()
        for w in re.findall(r"\b[a-zA-Z0-9][a-zA-Z0-9.-]*\b", text)
        if len(w) >= MIN_WORD_LEN
    }


def _truncate(text: str, max_chars: int) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _best_clause_for_sentence(sentence: str, clause_files: Sequence[Any]) -> Optional[Any]:
    sentence_lower = sentence.lower()
    best = None
    best_score = 0.0

    for cf in clause_files:
        clause_id = getattr(cf, "clause_id", "") or ""
        if clause_id and clause_id in sentence:
            return cf

        content_words = _word_set(getattr(cf, "content", "") or "")
        sentence_words = _word_set(sentence)
        if not content_words or not sentence_words:
            continue
        overlap = len(content_words & sentence_words)
        score = overlap / max(len(sentence_words), 1)
        if score > best_score:
            best_score = score
            best = cf

    return best if best_score >= 0.15 else None


def _extract_claim_text(section_text: str, total_content: str, recursive_text: Optional[str]) -> str:
    if recursive_text:
        return recursive_text.strip()

    section_norm = section_text.strip()
    total_norm = total_content.strip()
    if section_norm and total_norm.startswith(section_norm):
        extra = total_norm[len(section_norm) :].strip()
        if RECURSIVE_MARKER in extra:
            extra = extra.split(RECURSIVE_MARKER, 1)[-1].strip()
        return extra
    return ""


def _strip_modification_tag(text: str) -> str:
    return MODIFICATION_TAG_RE.sub("", text).strip()


def _oran_body_text(text: str) -> str:
    body = text
    if RECURSIVE_MARKER in body:
        body = body.split(RECURSIVE_MARKER, 1)[0]
    parts = body.strip().split("\n", 1)
    return parts[1].strip() if len(parts) > 1 else body.strip()


def _align_source_sentence(modified_sentence: str, source_sentences: List[str]) -> Optional[str]:
    """
    Find the O-RAN source sentence that best matches a modified claim.
    Uses text before an inline [MODIFICATION] tag, then prefix/word overlap.
    """
    tag_match = MODIFICATION_TAG_RE.search(modified_sentence)
    anchor = modified_sentence[: tag_match.start()].strip() if tag_match else ""
    stripped = _strip_modification_tag(modified_sentence)

    best: Optional[str] = None
    best_score = 0.0
    for src in source_sentences:
        src_lower = src.lower()
        for candidate in (anchor, stripped):
            if not candidate:
                continue
            cand_lower = candidate.lower()
            prefix_len = 0
            while prefix_len < min(len(src_lower), len(cand_lower)) and src_lower[prefix_len] == cand_lower[prefix_len]:
                prefix_len += 1
            src_words = _word_set(src)
            cand_words = _word_set(candidate)
            overlap = len(src_words & cand_words) / max(len(cand_words), 1)
            score = prefix_len + overlap * 80.0
            if score > best_score:
                best_score = score
                best = src

    return best if best_score >= MIN_SOURCE_ALIGN_SCORE else None


def _fallback_premise(oran_source_text: str, aligned: Optional[str]) -> str:
    if aligned:
        return _truncate(aligned, NLI_MAX_PREMISE_CHARS)
    # Short local context — not the full subsection (dilutes NLI scores).
    body = _oran_body_text(oran_source_text)
    return _truncate(body, min(NLI_MAX_PREMISE_CHARS, 600))


def _line_number_for_hypothesis(hypothesis: str, total_content: str) -> Optional[int]:
    """Locate the line in the uploaded dataset that contains the NLI hypothesis."""
    if not hypothesis or not total_content:
        return None

    lines = total_content.splitlines()
    candidates = [
        hypothesis,
        _strip_modification_tag(hypothesis),
        hypothesis.strip(),
    ]
    seen: set[str] = set()
    for needle in candidates:
        norm_needle = " ".join(needle.split())
        if not norm_needle or norm_needle in seen:
            continue
        seen.add(norm_needle)
        for line_no, line in enumerate(lines, start=1):
            norm_line = " ".join(line.split())
            if norm_needle in norm_line or norm_needle in line:
                return line_no
    return None


def build_nli_highlights(result: NliGroundednessResult) -> List[Dict[str, Any]]:
    """Structured highlight entries for UI line coloring."""
    highlights: List[Dict[str, Any]] = []
    for item in result.contradictions:
        highlights.append({**item.to_dict(), "classification": "contradiction"})
    for item in result.neutral_findings:
        highlights.append({**item.to_dict(), "classification": "neutral"})
    return highlights


def _sentence_in_source(sentence: str, source: str) -> bool:
    """True when the sentence is already present in the O-RAN source text."""
    norm_sent = " ".join(sentence.split()).lower()
    norm_src = " ".join(source.split()).lower()
    return bool(norm_sent) and norm_sent in norm_src


def collect_oran_nli_pairs(
    *,
    oran_source_text: str,
    total_content: str,
    max_pairs: int,
) -> List[Tuple[str, str, Optional[str]]]:
    """
    NLI pairs: aligned O-RAN source sentence (premise) vs modified claim (hypothesis).

    Comparing each changed sentence against the full subsection dilutes contradiction
    signal; align to the closest original sentence instead.
    """
    if not oran_source_text.strip():
        return []

    claim_text = _oran_body_text(total_content)
    if not claim_text:
        return []

    source_sentences = _split_sentences(_oran_body_text(oran_source_text))
    if not source_sentences:
        source_sentences = _split_sentences(oran_source_text)

    pairs: List[Tuple[str, str, Optional[str]]] = []
    seen_hypotheses: set[str] = set()
    claim_sentences = _split_sentences(claim_text)

    for index, sentence in enumerate(claim_sentences):
        norm_sentence = " ".join(sentence.split())
        if not norm_sentence or norm_sentence in seen_hypotheses:
            continue
        if _sentence_in_source(sentence, oran_source_text):
            continue

        align_text = sentence
        if MODIFICATION_TAG_RE.match(sentence.strip()):
            # Sentence split placed the tag at the start — align from modification body.
            align_text = _strip_modification_tag(sentence) or sentence

        aligned = _align_source_sentence(align_text, source_sentences)
        premise = _fallback_premise(oran_source_text, aligned)
        pairs.append((premise, sentence, "oran_subsection"))
        seen_hypotheses.add(norm_sentence)
        if len(pairs) >= max_pairs:
            break

    return pairs


def collect_nli_pairs(
    *,
    section_text: str,
    total_content: str,
    recursive_extraction_text: Optional[str],
    clause_files: Sequence[Any],
    max_pairs: int = NLI_MAX_PAIRS,
) -> List[Tuple[str, str, Optional[str]]]:
    """Return (premise, hypothesis, clause_id) tuples for NLI scoring."""
    if not clause_files:
        return []

    claim_text = _extract_claim_text(section_text, total_content, recursive_extraction_text)
    if not claim_text:
        return []

    pairs: List[Tuple[str, str, Optional[str]]] = []
    for sentence in _split_sentences(claim_text):
        clause = _best_clause_for_sentence(sentence, clause_files)
        if clause is None:
            continue
        premise = _truncate(clause.content, NLI_MAX_PREMISE_CHARS)
        if not premise:
            continue
        pairs.append((premise, sentence, clause.clause_id))
        if len(pairs) >= max_pairs:
            break

    return pairs


def run_nli_groundedness(
    *,
    section_text: str,
    total_content: str,
    recursive_extraction_text: Optional[str],
    clause_files: Sequence[Any],
    oran_source_text: Optional[str] = None,
    advisory_only: bool = False,
) -> NliGroundednessResult:
    """Score premise→hypothesis pairs; block on contradictions unless advisory_only."""
    result = NliGroundednessResult(available=False)

    if not GUARDRAILS_ENABLED or not NLI_GROUNDEDNESS_ENABLED:
        result.warnings.append("NLI groundedness disabled by configuration")
        result.available = True
        return result

    oran_premise = (oran_source_text or section_text or "").strip()
    oran_budget = max(1, NLI_MAX_PAIRS // 2)
    clause_budget = max(1, NLI_MAX_PAIRS - oran_budget)

    oran_pairs = collect_oran_nli_pairs(
        oran_source_text=oran_premise,
        total_content=total_content,
        max_pairs=oran_budget,
    )
    clause_pairs = collect_nli_pairs(
        section_text=section_text,
        total_content=total_content,
        recursive_extraction_text=recursive_extraction_text,
        clause_files=clause_files,
        max_pairs=clause_budget,
    )
    pairs = oran_pairs + clause_pairs

    if not pairs:
        result.available = True
        result.warnings.append("No O-RAN or clause-grounded claims found for NLI verification")
        return result

    if not _nli_model.load():
        result.load_error = _nli_model._load_error
        msg = f"NLI model unavailable: {result.load_error}"
        if NLI_SKIP_ON_MODEL_ERROR:
            result.available = False
            result.warnings.append(msg)
            return result
        result.errors.append(msg)
        return result

    result.available = True
    nli_pairs = [(premise, hypothesis) for premise, hypothesis, _ in pairs]
    probs = _nli_model.predict_probs(nli_pairs)
    result.pairs_checked = len(probs)

    for (premise, hypothesis, clause_id), (c_prob, e_prob, n_prob) in zip(pairs, probs):
        label_scores = {
            "contradiction": c_prob,
            "entailment": e_prob,
            "neutral": n_prob,
        }
        top_label = max(label_scores, key=label_scores.get)
        source_label = "O-RAN source" if clause_id == "oran_subsection" else f"clause '{clause_id or 'unknown'}'"

        pair_result = NliPairResult(
            premise_preview=_truncate(premise, 120),
            hypothesis_preview=_truncate(hypothesis, 120),
            hypothesis_text=hypothesis,
            line_number=_line_number_for_hypothesis(hypothesis, total_content),
            contradiction=c_prob,
            entailment=e_prob,
            neutral=n_prob,
            top_label=top_label,
            clause_id=clause_id,
        )

        is_contradiction = (
            top_label == "contradiction" and c_prob >= NLI_CONTRADICTION_THRESHOLD
        ) or (
            c_prob >= NLI_CONTRADICTION_THRESHOLD
            and c_prob > e_prob
            and c_prob > n_prob
        )

        if is_contradiction:
            result.contradictions.append(pair_result)
            if not advisory_only:
                result.errors.append(
                    f"NLI contradiction ({c_prob:.2f}) for {source_label}: "
                    f"{pair_result.hypothesis_preview}"
                )
            else:
                result.warnings.append(
                    f"NLI contradiction ({c_prob:.2f}) for {source_label}: "
                    f"{pair_result.hypothesis_preview}"
                )
        elif NLI_STRICT and top_label != "entailment":
            result.warnings.append(
                f"NLI not entailed ({top_label}, e={e_prob:.2f}) for {source_label}: "
                f"{pair_result.hypothesis_preview}"
            )
        elif top_label == "neutral":
            result.neutral_findings.append(pair_result)
            result.warnings.append(
                f"NLI neutral ({n_prob:.2f}) for {source_label}: "
                f"{pair_result.hypothesis_preview}"
            )

    result.metadata = {
        "model": NLI_MODEL,
        "contradiction_threshold": NLI_CONTRADICTION_THRESHOLD,
        "strict_mode": NLI_STRICT,
        "advisory_only": advisory_only,
        "oran_pairs_checked": len(oran_pairs),
        "clause_pairs_checked": len(clause_pairs),
        "oran_source_used": bool(oran_premise),
    }
    return result
