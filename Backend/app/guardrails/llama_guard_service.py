"""
Tiered input guardrail scan:

  Chunk → Layer 1 (regex / literals) → suspicious?
    No  → continue (skip Llama Guard — low latency)
    Yes → Layer 2 (Llama Guard) → reject if unsafe, else continue

Backends for Layer 2:
  - transformers: Meta Llama Prompt Guard 2
  - ollama: Llama Guard 3 via local Ollama API
  - rules_only: Layer 1 suspicious chunks block without ML
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

from app.guardrails.config import (
    GUARDRAILS_ENABLED,
    GUARDRAILS_FAIL_OPEN_ON_MODEL_ERROR,
    GUARDRAILS_REQUIRE_UPLOAD_LAYER2,
    HF_TOKEN,
    INJECTION_THRESHOLD,
    LLAMA_GUARD_BACKEND,
    OLLAMA_BASE_URL,
    OLLAMA_GUARD_MODEL,
    PROMPT_GUARD_MAX_LENGTH,
    PROMPT_GUARD_MODEL,
)
from app.guardrails.document_text_extractor import chunk_text, chunk_text_with_spans
from app.guardrails.injection_patterns import (
    find_layer1_pattern_details,
    find_layer1_suspicious_patterns,
    is_chunk_blocking_without_layer2,
    is_chunk_suspicious,
)
from app.guardrails.text_location import LocationContext, build_finding

logger = logging.getLogger(__name__)


def _chunk_snippet(chunk: str, max_len: int = 160) -> str:
    text = (chunk or "").replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


@dataclass
class ScanResult:
    safe: bool
    backend: str
    label: str
    score: float
    matched_patterns: List[str] = field(default_factory=list)
    unsafe_chunks: int = 0
    chunks_scanned: int = 0
    detail: str = ""
    findings: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class _PromptGuardModel:
    """Lazy-loaded Meta Llama Prompt Guard 2 (sequence classification)."""

    def __init__(self) -> None:
        self._tokenizer = None
        self._model = None
        self._label_injection_id: Optional[int] = None
        self.available = False
        self._load_error: Optional[str] = None

    def load(self) -> bool:
        if self._model is not None:
            return self.available
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            kwargs: Dict[str, Any] = {}
            if HF_TOKEN:
                kwargs["token"] = HF_TOKEN

            logger.info("Loading Llama Prompt Guard model: %s", PROMPT_GUARD_MODEL)
            self._tokenizer = AutoTokenizer.from_pretrained(PROMPT_GUARD_MODEL, **kwargs)
            self._model = AutoModelForSequenceClassification.from_pretrained(
                PROMPT_GUARD_MODEL, **kwargs
            )
            self._model.eval()

            id2label = getattr(self._model.config, "id2label", {}) or {}
            for idx, label in id2label.items():
                if str(label).upper() in ("INJECTION", "LABEL_1", "UNSAFE", "JAILBREAK"):
                    self._label_injection_id = int(idx)
                    break
            if self._label_injection_id is None:
                self._label_injection_id = 1 if len(id2label) > 1 else 0

            self.available = True
            logger.info("Llama Prompt Guard loaded (injection class id=%s)", self._label_injection_id)
            return True
        except Exception as exc:
            self._load_error = str(exc)
            logger.warning("Llama Prompt Guard unavailable: %s", exc)
            self.available = False
            return False

    def classify(self, text: str) -> tuple[str, float]:
        import torch

        if not self.available or not self._model or not self._tokenizer:
            return "UNKNOWN", 0.0

        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=PROMPT_GUARD_MAX_LENGTH,
        )
        with torch.no_grad():
            logits = self._model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)
            predicted = int(logits.argmax(dim=-1).item())
            confidence = float(probs[0][predicted].item())

        if predicted == self._label_injection_id:
            return "INJECTION", confidence
        return "BENIGN", confidence


_prompt_guard: Optional[_PromptGuardModel] = None


def _get_prompt_guard() -> _PromptGuardModel:
    global _prompt_guard
    if _prompt_guard is None:
        _prompt_guard = _PromptGuardModel()
    return _prompt_guard


def _classify_chunk_with_prompt_guard(chunk: str) -> tuple[str, float]:
    guard = _get_prompt_guard()
    if not guard.load():
        # Model unavailable — do not treat as injection (tiered scan uses rules_only instead)
        return "BENIGN", 0.0
    return guard.classify(chunk)


def _classify_chunk_with_ollama(chunk: str) -> tuple[str, float]:
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_GUARD_MODEL,
                "messages": [{"role": "user", "content": chunk[:8000]}],
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        body = resp.json()
        content = (body.get("message") or {}).get("content", "").strip().lower()
        unsafe = content.startswith("unsafe") or "unsafe" in content.split("\n")[0]
        return ("INJECTION", 1.0) if unsafe else ("BENIGN", 0.0)
    except Exception as exc:
        logger.warning("Ollama Llama Guard chunk scan failed: %s", exc)
        return "UNKNOWN", 0.0


def _resolve_layer2_classifier(
    layer2_backend: str,
    *,
    require_full_layer2: bool = False,
) -> tuple[Optional[Any], str]:
    """
    Return (classify_fn, effective_backend).
    When require_full_layer2 is True (upload scan), never downgrade to tiered Layer-1-only.
    """
    if layer2_backend == "transformers":
        guard = _get_prompt_guard()
        if guard.load():
            return _classify_chunk_with_prompt_guard, layer2_backend
        if require_full_layer2:
            try:
                health = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
                if health.ok:
                    logger.warning(
                        "Prompt Guard unavailable; falling back to Ollama Llama Guard for full upload scan."
                    )
                    return _classify_chunk_with_ollama, "ollama_fallback"
            except Exception:
                pass
        if require_full_layer2:
            logger.warning(
                "Full Layer 2 upload scan required but Llama Prompt Guard unavailable: %s",
                guard._load_error,
            )
            return None, "layer2_unavailable"
        if GUARDRAILS_FAIL_OPEN_ON_MODEL_ERROR:
            logger.warning(
                "Llama Prompt Guard unavailable (%s); Layer 2 skipped (tiered Layer 1 only).",
                guard._load_error,
            )
            return None, "layer1_only"
        return None, "rules_only"

    if layer2_backend == "ollama":
        return _classify_chunk_with_ollama, layer2_backend

    return None, "rules_only"


def _tiered_chunk_scan(
    chunks: List[str],
    chunk_spans: Optional[List[tuple[int, int]]] = None,
    *,
    layer2_backend: str,
    location: Optional[LocationContext] = None,
    require_full_layer2: bool = False,
) -> ScanResult:
    """
    Layer 1 on all chunks; Layer 2 (Llama Guard) only on Layer-1-suspicious chunks.
    """
    all_patterns: List[str] = []
    suspicious_indices: List[int] = []
    findings: List[Dict[str, Any]] = []

    for index, chunk in enumerate(chunks):
        patterns = find_layer1_suspicious_patterns(chunk)
        if patterns:
            suspicious_indices.append(index)
            all_patterns.extend(patterns)
            if chunk_spans and index < len(chunk_spans):
                base_offset = chunk_spans[index][0]
            else:
                base_offset = 0
            for hit in find_layer1_pattern_details(chunk, base_offset=base_offset):
                findings.append(
                    build_finding(
                        layer="layer1",
                        pattern=hit.pattern_id,
                        matched_text=hit.matched_text,
                        char_offset=hit.char_offset,
                        location=location,
                    )
                )

    layer2_scanned = 0
    unsafe_chunks = 0
    worst_label = "BENIGN"
    worst_score = 0.0

    classify_fn, layer2_backend = _resolve_layer2_classifier(
        layer2_backend,
        require_full_layer2=require_full_layer2,
    )

    for index in suspicious_indices:
        chunk = chunks[index]
        if chunk_spans and index < len(chunk_spans):
            chunk_start = chunk_spans[index][0]
        else:
            chunk_start = 0
        if classify_fn is None:
            if layer2_backend == "layer1_only":
                if not is_chunk_blocking_without_layer2(chunk):
                    continue
                unsafe_chunks += 1
                worst_label = "INJECTION"
                worst_score = max(worst_score, 0.85)
                for hit in find_layer1_pattern_details(chunk, base_offset=chunk_start):
                    findings.append(
                        build_finding(
                            layer="layer1",
                            pattern=hit.pattern_id,
                            matched_text=hit.matched_text,
                            char_offset=hit.char_offset,
                            location=location,
                            score=0.85,
                            reason="High-confidence injection pattern (model unavailable).",
                        )
                    )
                continue
            unsafe_chunks += 1
            worst_label = "INJECTION"
            worst_score = max(worst_score, 0.85)
            findings.append(
                build_finding(
                    layer="layer2",
                    pattern="rules_only:INJECTION",
                    matched_text=_chunk_snippet(chunk),
                    char_offset=chunk_start,
                    location=location,
                    score=0.85,
                    reason="Model backend unavailable; rules-only mode treats suspicious chunk as unsafe.",
                )
            )
            continue

        layer2_scanned += 1
        label, score = classify_fn(chunk)
        if label == "UNKNOWN":
            if require_full_layer2:
                unsafe_chunks += 1
                worst_label = "UNVERIFIED"
                worst_score = max(worst_score, 1.0)
                findings.append(
                    build_finding(
                        layer="layer2",
                        pattern=f"{layer2_backend}:UNKNOWN",
                        matched_text=_chunk_snippet(chunk),
                        char_offset=chunk_start,
                        location=location,
                        score=1.0,
                        reason="Llama Guard backend did not return a verdict for this chunk.",
                    )
                )
            continue
        injection_score = score if label == "INJECTION" else (1.0 - score)

        if label == "INJECTION" and injection_score >= INJECTION_THRESHOLD:
            unsafe_chunks += 1
            if injection_score > worst_score:
                worst_score = injection_score
                worst_label = "INJECTION"
            findings.append(
                build_finding(
                    layer="layer2",
                    pattern=f"{layer2_backend}:{label}",
                    matched_text=_chunk_snippet(chunk),
                    char_offset=chunk_start,
                    location=location,
                    score=injection_score,
                    reason="Llama Guard classified this chunk as prompt injection.",
                )
            )

    unique_patterns = list(dict.fromkeys(all_patterns))
    clean_chunks = len(chunks) - len(suspicious_indices)
    safe = worst_label not in ("INJECTION", "UNVERIFIED") and unsafe_chunks == 0

    detail = (
        f"Tiered scan: {len(chunks)} chunk(s); "
        f"L1 suspicious={len(suspicious_indices)}; "
        f"L2 llama_scanned={layer2_scanned}; "
        f"L1 clean (skipped L2)={clean_chunks}; "
        f"unsafe={unsafe_chunks}"
    )

    return ScanResult(
        safe=safe,
        backend=layer2_backend if layer2_scanned else "layer1_only",
        label=worst_label,
        score=worst_score,
        matched_patterns=unique_patterns,
        chunks_scanned=len(chunks),
        unsafe_chunks=unsafe_chunks,
        detail=detail,
        findings=findings,
        metadata={
            "pipeline": "tiered",
            "layer1_total_chunks": len(chunks),
            "layer1_suspicious_chunks": len(suspicious_indices),
            "layer1_clean_chunks": clean_chunks,
            "layer2_llama_scanned_chunks": layer2_scanned,
            "layer2_skipped_chunks": clean_chunks,
        },
    )


def _full_chunk_scan(
    chunks: List[str],
    chunk_spans: Optional[List[tuple[int, int]]] = None,
    *,
    layer2_backend: str,
    location: Optional[LocationContext] = None,
    require_full_layer2: bool = False,
) -> ScanResult:
    """
    Layer 1 on all chunks; Layer 2 (Llama Guard) on *every* chunk.

    Used for initial document upload, to avoid false negatives when Layer 1 is too strict
    or when jailbreak patterns are obfuscated and not caught by deterministic rules.
    """
    all_patterns: List[str] = []
    findings: List[Dict[str, Any]] = []
    for idx, chunk in enumerate(chunks):
        all_patterns.extend(find_layer1_suspicious_patterns(chunk))
        if chunk_spans and idx < len(chunk_spans):
            base_offset = chunk_spans[idx][0]
        else:
            base_offset = 0
        for hit in find_layer1_pattern_details(chunk, base_offset=base_offset):
            findings.append(
                build_finding(
                    layer="layer1",
                    pattern=hit.pattern_id,
                    matched_text=hit.matched_text,
                    char_offset=hit.char_offset,
                    location=location,
                )
            )

    layer2_scanned = 0
    unsafe_chunks = 0
    worst_label = "BENIGN"
    worst_score = 0.0

    classify_fn, layer2_backend = _resolve_layer2_classifier(
        layer2_backend,
        require_full_layer2=require_full_layer2,
    )
    if classify_fn is None:
        if require_full_layer2 and layer2_backend == "layer2_unavailable":
            guard = _get_prompt_guard()
            model_error = guard._load_error or "Llama Prompt Guard model not loaded"
            strict_upload = bool(require_full_layer2 and GUARDRAILS_REQUIRE_UPLOAD_LAYER2)
            if strict_upload:
                detail = (
                    f"Full Layer 2 upload scan required but model unavailable: {model_error}"
                )
                findings.append(
                    build_finding(
                        layer="layer2",
                        pattern="layer2_unavailable:UNVERIFIED",
                        matched_text="",
                        char_offset=0,
                        location=location,
                        score=1.0,
                        reason=(
                            "Llama Prompt Guard is required for upload but could not be loaded. "
                            f"Install backend dependencies (torch, transformers) or set "
                            "GUARDRAILS_REQUIRE_UPLOAD_LAYER2=false."
                        ),
                    )
                )
                return ScanResult(
                    safe=False,
                    backend="layer2_unavailable",
                    label="UNVERIFIED",
                    score=1.0,
                    matched_patterns=list(dict.fromkeys(all_patterns)),
                    chunks_scanned=len(chunks),
                    unsafe_chunks=len(chunks),
                    detail=detail,
                    findings=findings,
                    metadata={
                        "pipeline": "full_layer2",
                        "layer1_total_chunks": len(chunks),
                        "layer1_suspicious_chunks": None,
                        "layer1_clean_chunks": None,
                        "layer2_llama_scanned_chunks": 0,
                        "layer2_skipped_chunks": len(chunks),
                        "layer2_unavailable": True,
                        "model_error": model_error,
                        "require_upload_layer2": True,
                    },
                )
            logger.warning(
                "Full Layer 2 upload scan unavailable (%s); falling back to tiered Layer 1 scan.",
                model_error,
            )
        else:
            logger.warning("Full Layer 2 scan unavailable; falling back to tiered Layer 1 scan.")
        tiered = _tiered_chunk_scan(
            chunks,
            chunk_spans,
            layer2_backend=layer2_backend,
            location=location,
        )
        tiered.metadata = {
            **(tiered.metadata or {}),
            "upload_layer2_fallback": True,
            "requested_pipeline": "full_layer2",
            "layer2_unavailable": layer2_backend == "layer2_unavailable",
            "model_error": (
                _get_prompt_guard()._load_error
                if layer2_backend == "layer2_unavailable"
                else None
            ),
        }
        return tiered

    for idx, chunk in enumerate(chunks):
        if chunk_spans and idx < len(chunk_spans):
            chunk_start = chunk_spans[idx][0]
        else:
            chunk_start = 0

        layer2_scanned += 1
        label, score = classify_fn(chunk)
        injection_score = score if label == "INJECTION" else (1.0 - score)

        if label == "INJECTION" and injection_score >= INJECTION_THRESHOLD:
            unsafe_chunks += 1
            if injection_score > worst_score:
                worst_score = injection_score
                worst_label = "INJECTION"
            findings.append(
                build_finding(
                    layer="layer2",
                    pattern=f"{layer2_backend}:{label}",
                    matched_text=_chunk_snippet(chunk),
                    char_offset=chunk_start,
                    location=location,
                    score=injection_score,
                    reason="Llama Guard classified this chunk as prompt injection.",
                )
            )

    unique_patterns = list(dict.fromkeys(all_patterns))
    if unsafe_chunks == 0 and any(p.startswith("malicious:") for p in unique_patterns):
        unsafe_chunks = 1
        worst_label = "INJECTION"
        worst_score = max(worst_score, 0.9)
        findings.append(
            build_finding(
                layer="layer1",
                pattern="malicious_literal_block",
                matched_text="",
                char_offset=0,
                location=location,
                score=0.9,
                reason="High-risk malicious literal detected in upload chunk.",
            )
        )
    safe = worst_label not in ("INJECTION", "UNVERIFIED") and unsafe_chunks == 0

    detail = (
        f"Full scan: {len(chunks)} chunk(s); "
        f"L2 llama_scanned={layer2_scanned}; "
        f"unsafe={unsafe_chunks}"
    )

    return ScanResult(
        safe=safe,
        backend=layer2_backend if layer2_scanned else "rules_only",
        label=worst_label,
        score=worst_score,
        matched_patterns=unique_patterns,
        chunks_scanned=len(chunks),
        unsafe_chunks=unsafe_chunks,
        detail=detail,
        findings=findings,
        metadata={
            "pipeline": "full_layer2",
            "layer1_total_chunks": len(chunks),
            "layer1_suspicious_chunks": None,
            "layer1_clean_chunks": None,
            "layer2_llama_scanned_chunks": layer2_scanned,
            "layer2_skipped_chunks": 0,
        },
    )


def _scan_with_rules_tiered(text: str) -> ScanResult:
    """Rules-only mode: Layer 1 suspicious chunks are treated as unsafe."""
    chunks = chunk_text(text, max_chars=1800, overlap=150) or [text]
    # No reliable spans here (legacy path) — findings will still include line numbers.
    return _tiered_chunk_scan(chunks, layer2_backend="rules_only")


def scan_document_text(
    text: str,
    *,
    force_layer2_all_chunks: bool = False,
    location: Optional[LocationContext] = None,
) -> ScanResult:
    """
    Tiered document scan:
      1. Chunk text
      2. Layer 1 regex/literal filter on every chunk
      3. Layer 2 Llama Guard only on suspicious chunks
    """
    if not GUARDRAILS_ENABLED:
        return ScanResult(safe=True, backend="disabled", label="BENIGN", score=0.0)

    if not text or not text.strip():
        return ScanResult(safe=True, backend="empty", label="BENIGN", score=0.0)

    chunks = chunk_text(text, max_chars=1800, overlap=150)
    if not chunks:
        return ScanResult(safe=True, backend="empty", label="BENIGN", score=0.0)

    chunk_triplets = chunk_text_with_spans(text, max_chars=1800, overlap=150)
    spans = [(start, end) for _chunk, start, end in chunk_triplets] if chunk_triplets else None
    if chunk_triplets:
        chunks = [_chunk for _chunk, _start, _end in chunk_triplets]

    backend = LLAMA_GUARD_BACKEND
    if backend in ("transformers", "ollama"):
        if force_layer2_all_chunks:
            return _full_chunk_scan(
                chunks,
                spans,
                layer2_backend=backend,
                location=location,
                require_full_layer2=True,
            )
        return _tiered_chunk_scan(chunks, spans, layer2_backend=backend, location=location)

    return _scan_with_rules_tiered(text)


def ensure_prompt_guard_loaded() -> bool:
    """Eager-load Llama Prompt Guard (used before full upload scans)."""
    if LLAMA_GUARD_BACKEND != "transformers":
        return True
    return _get_prompt_guard().load()


def get_guard_status() -> Dict[str, Any]:
    """Health/status for guardrail layer (used by status API)."""
    backend = LLAMA_GUARD_BACKEND
    status: Dict[str, Any] = {
        "enabled": GUARDRAILS_ENABLED,
        "pipeline": "upload: full_layer2 (Llama Guard on every chunk) | other: tiered (L1 → L2 on suspicious only)",
        "backend": backend,
        "prompt_guard_model": PROMPT_GUARD_MODEL,
        "ollama_model": OLLAMA_GUARD_MODEL,
        "injection_threshold": INJECTION_THRESHOLD,
        "model_loaded": False,
        "model_error": None,
    }
    if not GUARDRAILS_ENABLED:
        return status

    if backend == "transformers":
        guard = _get_prompt_guard()
        status["model_loaded"] = guard.load()
        status["model_error"] = guard._load_error
    elif backend == "ollama":
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
            status["model_loaded"] = r.ok
            if not r.ok:
                status["model_error"] = f"Ollama unreachable: HTTP {r.status_code}"
        except Exception as exc:
            status["model_loaded"] = False
            status["model_error"] = str(exc)
    else:
        status["model_loaded"] = True
        status["backend"] = "rules_only"

    return status
