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
ENUM_PREFIX_RE = re.compile(
    r"^(?:NOTE\s*\d+[a-z]?:|(?:\d+\.)+\s*|\d+[\.)]\s*)",
    re.IGNORECASE,
)
DECORATIVE_SEPARATOR_RE = re.compile(r"^[\s=*#\-_~.+>|/\\]+$")
TEST_STATEMENT_TAG_RE = re.compile(r"^\[\s*TEST\s+STATEMENT.*\]$", re.IGNORECASE)
HTML_COMMENT_RE = re.compile(r"<!--[\s\S]*?-->", re.IGNORECASE)
ANNOTATION_PREFIX_RE = re.compile(
    r"^(?:ground\s+truth\b|directly\s+stated\b|document\s+explicitly\s+states\b|note:|\/\/)",
    re.IGNORECASE,
)
MIN_SOURCE_ALIGN_SCORE = 20.0
NLI_PREMISE_CANDIDATE_TOP_K = 12
MIN_PREMISE_CANDIDATE_CHARS = 40
# Skip NLI reporting when the best premise strongly entails an unmodified claim.
NLI_ENTAILMENT_SKIP_THRESHOLD = 0.75

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
    premise_text: str = ""
    line_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clause_id": self.clause_id,
            "premise_preview": self.premise_preview,
            "hypothesis_preview": self.hypothesis_preview,
            "hypothesis_text": self.hypothesis_text,
            "premise_text": self.premise_text,
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


def _normalize_for_match(text: str) -> str:
    return " ".join(text.split()).lower()


def _strip_sentence_prefixes(text: str) -> str:
    """Remove leading NOTE / numbered-list prefixes so claims align across formats."""
    cleaned = " ".join((text or "").split())
    previous = None
    while cleaned and cleaned != previous:
        previous = cleaned
        cleaned = ENUM_PREFIX_RE.sub("", cleaned, count=1).strip()
    return cleaned


def _normalize_sentence_core(text: str) -> str:
    return _normalize_for_match(_strip_sentence_prefixes(_strip_modification_tag(text)))


def _is_decorative_or_non_claim(text: str) -> bool:
    cleaned = (text or "").strip()
    if len(cleaned) < MIN_SENTENCE_CHARS:
        return True
    if DECORATIVE_SEPARATOR_RE.match(cleaned):
        return True
    if cleaned.count("=") >= 10 and len(set(cleaned)) <= 3:
        return True
    # Ignore HTML comments (e.g. <!-- Ground Truth: CONTRADICTION... -->)
    if cleaned.startswith("<!--") or cleaned.endswith("-->") or HTML_COMMENT_RE.search(cleaned):
        return True
    # Ignore dataset metadata tags (e.g. [TEST STATEMENT 2 - CONTRADICTION])
    if TEST_STATEMENT_TAG_RE.match(cleaned) or (cleaned.startswith("[") and cleaned.endswith("]") and "STATEMENT" in cleaned.upper()):
        return True
    # Ignore ground truth annotations or explanation text lines
    if ANNOTATION_PREFIX_RE.search(cleaned):
        return True
    return False


def _score_sentence_alignment(hypothesis: str, source: str) -> float:
    """
    Lexical alignment score between a hypothesis and a candidate source sentence.
    Higher scores indicate a better semantic match for NLI premise selection.
    """
    hyp_norm = _normalize_sentence_core(hypothesis)
    src_norm = _normalize_sentence_core(source)
    if not hyp_norm or not src_norm:
        return 0.0

    if hyp_norm == src_norm:
        return 1000.0
    if hyp_norm in src_norm or src_norm in hyp_norm:
        return 900.0 + min(len(hyp_norm), len(src_norm))

    prefix_len = 0
    while prefix_len < min(len(src_norm), len(hyp_norm)) and src_norm[prefix_len] == hyp_norm[prefix_len]:
        prefix_len += 1

    src_words = _word_set(src_norm)
    hyp_words = _word_set(hyp_norm)
    if not hyp_words:
        return 0.0

    overlap = len(src_words & hyp_words)
    overlap_ratio = overlap / len(hyp_words)
    union = src_words | hyp_words
    jaccard = overlap / len(union) if union else 0.0

    return prefix_len + overlap_ratio * 100.0 + jaccard * 50.0


def _alignment_candidates(hypothesis: str) -> List[str]:
    """Build hypothesis variants used when searching for the best source sentence."""
    candidates: List[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        norm = " ".join((text or "").split())
        if norm and norm not in seen:
            seen.add(norm)
            candidates.append(norm)

    add(hypothesis)
    stripped = _strip_modification_tag(hypothesis)
    if stripped:
        add(stripped)

    tag_match = MODIFICATION_TAG_RE.search(hypothesis)
    if tag_match:
        anchor = hypothesis[: tag_match.start()].strip()
        add(anchor)

    return candidates


def _best_matching_source_sentence(
    hypothesis: str,
    source_sentences: Sequence[str],
    *,
    min_score: float = MIN_SOURCE_ALIGN_SCORE,
) -> Optional[str]:
    """Pick the single source sentence that best matches the hypothesis."""
    if not source_sentences:
        return None

    best: Optional[str] = None
    best_score = 0.0
    for src in source_sentences:
        for candidate in _alignment_candidates(hypothesis):
            score = _score_sentence_alignment(candidate, src)
            if score > best_score:
                best_score = score
                best = src

    return best if best_score >= min_score else None


def _align_source_sentence(modified_sentence: str, source_sentences: List[str]) -> Optional[str]:
    """Find the O-RAN source sentence that best matches a modified claim."""
    return _best_matching_source_sentence(modified_sentence, source_sentences)


def _index_clause_sentences(
    clause_files: Sequence[Any],
) -> Tuple[List[Tuple[str, str]], Dict[str, List[str]]]:
    """
    Index all sentences from clause files.

    Returns:
        (flat list of (clause_id, sentence), per-clause sentence lists)
    """
    flat: List[Tuple[str, str]] = []
    per_clause: Dict[str, List[str]] = {}
    for cf in clause_files:
        clause_id = getattr(cf, "clause_id", "") or ""
        content = getattr(cf, "content", "") or ""
        sentences = _split_sentences(content)
        per_clause[clause_id] = sentences
        for sentence in sentences:
            flat.append((clause_id, sentence))
    return flat, per_clause


def _clause_id_for_sentence(
    sentence: str,
    indexed_sentences: Sequence[Tuple[str, str]],
) -> Optional[str]:
    """Resolve which clause a matched source sentence belongs to."""
    norm = _normalize_sentence_core(sentence)
    for clause_id, src in indexed_sentences:
        if _normalize_sentence_core(src) == norm:
            return clause_id
    return None


def _hypothesis_in_source_catalog(
    hypothesis: str,
    source_sentences: Sequence[str],
) -> bool:
    """True when the hypothesis is a faithful copy of (or excerpt from) a source sentence."""
    hyp_core = _normalize_sentence_core(hypothesis)
    if not hyp_core or len(hyp_core) < MIN_SENTENCE_CHARS:
        return False

    for src in source_sentences:
        src_core = _normalize_sentence_core(src)
        if not src_core:
            continue
        if hyp_core == src_core:
            return True
        if hyp_core in src_core:
            return True
    return False


def _top_lexical_premise_candidates(
    hypothesis: str,
    indexed_sentences: Sequence[Tuple[str, str]],
    *,
    top_k: int = NLI_PREMISE_CANDIDATE_TOP_K,
) -> List[Tuple[str, str]]:
    """
    Rank candidate premise sentences across every indexed source chunk.

    Returns (premise_text, clause_id) tuples ordered best-first.
    """
    scored: List[Tuple[float, str, str]] = []
    for clause_id, src in indexed_sentences:
        for candidate in _alignment_candidates(hypothesis):
            score = _score_sentence_alignment(candidate, src)
            if score < MIN_SOURCE_ALIGN_SCORE:
                continue
            src_core = _normalize_sentence_core(src)
            if len(src_core) < MIN_PREMISE_CANDIDATE_CHARS and score < 1000.0:
                continue
            scored.append((score, src, clause_id))

    scored.sort(key=lambda item: item[0], reverse=True)

    results: List[Tuple[str, str]] = []
    seen: set[str] = set()
    for _, src, clause_id in scored:
        key = _normalize_sentence_core(src)
        if not key or key in seen:
            continue
        seen.add(key)
        results.append((src, clause_id))
        if len(results) >= top_k:
            break
    return results


def _select_best_premise_with_nli(
    hypothesis: str,
    candidates: Sequence[Tuple[str, str]],
) -> Optional[Tuple[str, str, Tuple[float, float, float]]]:
    """
    Use the NLI cross-encoder to pick the semantically best premise among candidates.

    Returns (premise, clause_id, (contradiction, entailment, neutral)) or None.
    """
    if not candidates:
        return None

    pairs = [(premise, hypothesis) for premise, _ in candidates]
    probs = _nli_model.predict_probs(pairs)
    # Pick premise candidate with strongest entailment or contradiction signal
    best_index = max(range(len(probs)), key=lambda idx: max(probs[idx][0], probs[idx][1]))
    premise, clause_id = candidates[best_index]
    return premise, clause_id, probs[best_index]


def _resolve_premise_for_hypothesis(
    hypothesis: str,
    indexed_sentences: Sequence[Tuple[str, str]],
    *,
    clause_hint: Optional[str] = None,
    source_kind: str = "clause",
) -> Optional[Tuple[str, Optional[str], Tuple[float, float, float]]]:
    """
    Find the best premise for a hypothesis by searching all source chunks.

    Uses lexical pre-filtering across every chunk, then NLI entailment to pick
    the most semantically aligned premise sentence.
    """
    candidates = _top_lexical_premise_candidates(hypothesis, indexed_sentences)
    if not candidates and clause_hint:
        hint_candidates = [
            (sentence, clause_hint)
            for cid, sentence in indexed_sentences
            if cid == clause_hint
        ]
        candidates = hint_candidates[:NLI_PREMISE_CANDIDATE_TOP_K]

    if not candidates:
        return None

    selected = _select_best_premise_with_nli(hypothesis, candidates)
    if not selected:
        return None

    premise, clause_id, probs = selected
    resolved_clause = clause_id or clause_hint
    if source_kind == "oran":
        resolved_clause = "oran_subsection"
    return _truncate(premise, NLI_MAX_PREMISE_CHARS), resolved_clause, probs


def _premise_for_clause_hypothesis(
    hypothesis: str,
    clause_files: Sequence[Any],
    indexed_sentences: Sequence[Tuple[str, str]],
    per_clause_sentences: Dict[str, List[str]],
) -> Tuple[Optional[str], Optional[str]]:
    """
  Legacy lexical-only premise lookup (used by tests and tooling).

  Production NLI scoring resolves premises in run_nli_groundedness via
  _resolve_premise_for_hypothesis, which searches all chunks and uses NLI ranking.
    """
    del per_clause_sentences  # global search only
    aligned = _best_matching_source_sentence(
        hypothesis,
        [sentence for _, sentence in indexed_sentences],
    )
    if not aligned:
        return None, None

    clause_id = _clause_id_for_sentence(aligned, indexed_sentences)
    if not clause_id:
        hinted = _best_clause_for_sentence(hypothesis, clause_files)
        clause_id = hinted.clause_id if hinted else None
    return _truncate(aligned, NLI_MAX_PREMISE_CHARS), clause_id


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
    return _hypothesis_in_source_catalog(sentence, _split_sentences(source))


def _index_oran_sentences(oran_source_text: str) -> List[Tuple[str, str]]:
    sentences = _split_sentences(_oran_body_text(oran_source_text))
    if not sentences:
        sentences = _split_sentences(oran_source_text)
    return [("oran_subsection", sentence) for sentence in sentences]


def collect_oran_nli_hypotheses(
    *,
    oran_source_text: str,
    total_content: str,
    max_pairs: int,
) -> List[str]:
    """Collect O-RAN subsection hypotheses that differ from the original source."""
    if not oran_source_text.strip():
        return []

    claim_text = _oran_body_text(total_content)
    if not claim_text:
        return []

    source_sentences = _split_sentences(_oran_body_text(oran_source_text))
    if not source_sentences:
        source_sentences = _split_sentences(oran_source_text)

    hypotheses: List[str] = []
    seen_hypotheses: set[str] = set()

    for sentence in _split_sentences(claim_text):
        norm_sentence = " ".join(sentence.split())
        if not norm_sentence or norm_sentence in seen_hypotheses:
            continue
        if _is_decorative_or_non_claim(sentence):
            continue
        if _hypothesis_in_source_catalog(sentence, source_sentences):
            continue

        align_text = sentence
        if MODIFICATION_TAG_RE.match(sentence.strip()):
            align_text = _strip_modification_tag(sentence) or sentence
            if _hypothesis_in_source_catalog(align_text, source_sentences):
                continue

        hypotheses.append(sentence)
        seen_hypotheses.add(norm_sentence)
        if len(hypotheses) >= max_pairs:
            break

    return hypotheses


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
    del oran_source_text, total_content, max_pairs
    # Premise resolution is performed in run_nli_groundedness after NLI model load.
    return []


def collect_clause_nli_hypotheses(
    *,
    section_text: str,
    total_content: str,
    recursive_extraction_text: Optional[str],
    clause_files: Sequence[Any],
    max_pairs: int = NLI_MAX_PAIRS,
) -> List[Tuple[str, Optional[str]]]:
    """Collect clause-grounded hypotheses that differ from indexed 3GPP source chunks."""
    if not clause_files:
        return []

    claim_text = _extract_claim_text(section_text, total_content, recursive_extraction_text)
    if not claim_text:
        return []

    indexed_sentences, _ = _index_clause_sentences(clause_files)
    if not indexed_sentences:
        return []

    source_sentences = [sentence for _, sentence in indexed_sentences]
    hypotheses: List[Tuple[str, Optional[str]]] = []
    seen_hypotheses: set[str] = set()

    for sentence in _split_sentences(claim_text):
        norm_sentence = " ".join(sentence.split())
        if not norm_sentence or norm_sentence in seen_hypotheses:
            continue
        if _is_decorative_or_non_claim(sentence):
            continue
        if _hypothesis_in_source_catalog(sentence, source_sentences):
            continue

        clause_hint = None
        hinted = _best_clause_for_sentence(sentence, clause_files)
        if hinted is not None:
            clause_hint = hinted.clause_id

        hypotheses.append((sentence, clause_hint))
        seen_hypotheses.add(norm_sentence)
        if len(hypotheses) >= max_pairs:
            break

    return hypotheses


def collect_nli_pairs(
    *,
    section_text: str,
    total_content: str,
    recursive_extraction_text: Optional[str],
    clause_files: Sequence[Any],
    max_pairs: int = NLI_MAX_PAIRS,
) -> List[Tuple[str, str, Optional[str]]]:
    """Return (premise, hypothesis, clause_id) tuples using lexical premise alignment."""
    hypotheses = collect_clause_nli_hypotheses(
        section_text=section_text,
        total_content=total_content,
        recursive_extraction_text=recursive_extraction_text,
        clause_files=clause_files,
        max_pairs=max_pairs,
    )
    if not hypotheses:
        return []

    indexed_sentences, per_clause_sentences = _index_clause_sentences(clause_files)
    pairs: List[Tuple[str, str, Optional[str]]] = []
    for hypothesis, _ in hypotheses:
        premise, clause_id = _premise_for_clause_hypothesis(
            hypothesis,
            clause_files,
            indexed_sentences,
            per_clause_sentences,
        )
        if premise and clause_id:
            pairs.append((premise, hypothesis, clause_id))
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

    oran_hypotheses = collect_oran_nli_hypotheses(
        oran_source_text=oran_premise,
        total_content=total_content,
        max_pairs=oran_budget,
    )
    clause_hypotheses = collect_clause_nli_hypotheses(
        section_text=section_text,
        total_content=total_content,
        recursive_extraction_text=recursive_extraction_text,
        clause_files=clause_files,
        max_pairs=clause_budget,
    )

    if not oran_hypotheses and not clause_hypotheses:
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

    indexed_sources: List[Tuple[str, str]] = []
    if oran_premise:
        indexed_sources.extend(_index_oran_sentences(oran_premise))
    if clause_files:
        clause_indexed, _ = _index_clause_sentences(clause_files)
        indexed_sources.extend(clause_indexed)

    if not indexed_sources:
        result.available = True
        result.warnings.append("No source sentences available for NLI premise alignment")
        return result

    pairs: List[Tuple[str, str, Optional[str], Tuple[float, float, float]]] = []
    skipped_faithful = 0

    for hypothesis in oran_hypotheses:
        resolved = _resolve_premise_for_hypothesis(
            hypothesis,
            indexed_sources,
            source_kind="oran",
        )
        if not resolved:
            continue
        premise, clause_id, probs = resolved
        c_prob, e_prob, n_prob = probs
        if e_prob >= NLI_ENTAILMENT_SKIP_THRESHOLD and e_prob >= c_prob and e_prob >= n_prob:
            skipped_faithful += 1
            continue
        pairs.append((premise, hypothesis, clause_id, probs))

    for hypothesis, clause_hint in clause_hypotheses:
        resolved = _resolve_premise_for_hypothesis(
            hypothesis,
            indexed_sources,
            clause_hint=clause_hint,
            source_kind="clause",
        )
        if not resolved:
            continue
        premise, clause_id, probs = resolved
        c_prob, e_prob, n_prob = probs
        if e_prob >= NLI_ENTAILMENT_SKIP_THRESHOLD and e_prob >= c_prob and e_prob >= n_prob:
            skipped_faithful += 1
            continue
        pairs.append((premise, hypothesis, clause_id, probs))

    if not pairs:
        result.available = True
        result.metadata = {
            "model": NLI_MODEL,
            "contradiction_threshold": NLI_CONTRADICTION_THRESHOLD,
            "strict_mode": NLI_STRICT,
            "advisory_only": advisory_only,
            "oran_hypotheses": len(oran_hypotheses),
            "clause_hypotheses": len(clause_hypotheses),
            "skipped_faithful_matches": skipped_faithful,
            "oran_source_used": bool(oran_premise),
        }
        if skipped_faithful:
            result.warnings.append(
                f"All {skipped_faithful} candidate claim(s) were faithfully entailed by source text"
            )
        else:
            result.warnings.append("No O-RAN or clause-grounded claims found for NLI verification")
        return result

    result.available = True
    result.pairs_checked = len(pairs)

    for premise, hypothesis, clause_id, (c_prob, e_prob, n_prob) in pairs:
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
            premise_text=premise,
            line_number=_line_number_for_hypothesis(hypothesis, total_content),
            contradiction=c_prob,
            entailment=e_prob,
            neutral=n_prob,
            top_label=top_label,
            clause_id=clause_id,
        )

        # Generic, probabilistic NLI classification (no hardcoded strings or dataset-specific rules)
        is_contradiction = (
            top_label == "contradiction"
            and c_prob >= NLI_CONTRADICTION_THRESHOLD
            and c_prob > n_prob
            and c_prob > e_prob
        )
        is_neutral = (
            top_label == "neutral"
            or (n_prob >= c_prob and n_prob >= e_prob)
            or (top_label != "contradiction" and top_label != "entailment")
        )

        if is_contradiction:
            pair_result.top_label = "contradiction"
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
        elif is_neutral:
            pair_result.top_label = "neutral"
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
        "oran_hypotheses": len(oran_hypotheses),
        "clause_hypotheses": len(clause_hypotheses),
        "oran_pairs_checked": sum(1 for _, _, cid, _ in pairs if cid == "oran_subsection"),
        "clause_pairs_checked": sum(1 for _, _, cid, _ in pairs if cid != "oran_subsection"),
        "skipped_faithful_matches": skipped_faithful,
        "oran_source_used": bool(oran_premise),
        "premise_selection": "global_nli_ranked",
    }
    return result
