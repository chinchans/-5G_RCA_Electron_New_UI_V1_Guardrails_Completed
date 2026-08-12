"""
Historical pattern matching for Bug Discovery OAI logs.

Goal:
  - Keep patterns learned from logs the application has successfully analyzed before
  - When a new log has no close match in that history, advise human review

Pipeline:
  1. Canonical milestone extraction
  2. Sliding-window N-gram tokenization
  3. Levenshtein + cosine similarity vs learned patterns
  4. No close match → new log warning (advisory by default)
"""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.guardrails.config import (
    BACKEND_DIR,
    GUARDRAILS_BD_HISTORICAL_MIN_PATTERNS,
    GUARDRAILS_BD_HISTORICAL_MIN_SIMILARITY,
    GUARDRAILS_BD_HISTORICAL_NGRAM_SIZE,
    GUARDRAILS_BD_HISTORICAL_PATTERN_ENABLED,
    GUARDRAILS_BD_HISTORICAL_PATTERN_MODE,
    GUARDRAILS_BD_HISTORICAL_WEIGHT_COSINE,
    GUARDRAILS_BD_HISTORICAL_WEIGHT_LEVENSHTEIN,
    MAX_SCAN_CHARS,
)
from app.guardrails.log_milestone_extractor import (
    build_ngrams,
    detect_scenario,
    extract_milestone_sequence,
    extract_milestones_from_file,
)
from app.guardrails.log_pattern_store import load_learned_pattern_payload, refresh_learned_patterns

PATTERN_DIR = BACKEND_DIR / "resources" / "guardrails" / "log_patterns"


def _normalize_upload_filename(filename: str) -> str:
    """Strip UUID prefix from rca_logs uploads (e.g. abc123_success_du_gnb.log)."""
    name = Path(filename).name
    if "_" not in name:
        return name
    prefix, remainder = name.split("_", 1)
    if len(prefix) == 36:
        try:
            import uuid
            uuid.UUID(prefix)
            return remainder or name
        except ValueError:
            pass
    return name


@dataclass
class LogPattern:
    id: str
    scenario: str
    description: str
    source: str
    steps: List[str]
    ngrams: List[List[str]] = field(default_factory=list)
    log_file: Optional[str] = None
    log_path: Optional[str] = None
    history_file: Optional[str] = None
    source_type: str = "learned"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogPattern":
        return cls(
            id=str(data.get("id", "")),
            scenario=str(data.get("scenario", "unknown")),
            description=str(data.get("description", "")),
            source=str(data.get("source", "")),
            steps=list(data.get("steps") or []),
            ngrams=[list(item) for item in (data.get("ngrams") or [])],
            log_file=data.get("log_file"),
            log_path=data.get("log_path"),
            history_file=data.get("history_file"),
            source_type=str(data.get("source_type") or "learned"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scenario": self.scenario,
            "description": self.description,
            "source": self.source,
            "steps": self.steps,
            "ngrams": self.ngrams,
            "log_file": self.log_file,
            "log_path": self.log_path,
            "history_file": self.history_file,
            "source_type": self.source_type,
        }


@dataclass
class HistoricalPatternResult:
    passed: bool
    blocked: bool
    warned: bool
    similarity_score: float
    scenario: str
    is_new_log: bool = False
    is_known_log: bool = False
    matched_log_file: Optional[str] = None
    best_pattern_id: Optional[str] = None
    best_pattern_description: Optional[str] = None
    step_count: int = 0
    steps: List[str] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)
    checks: List[Dict[str, Any]] = field(default_factory=list)
    skipped: bool = False
    skip_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "warned": self.warned,
            "similarity_score": round(self.similarity_score, 4),
            "scenario": self.scenario,
            "is_new_log": self.is_new_log,
            "is_known_log": self.is_known_log,
            "matched_log_file": self.matched_log_file,
            "best_pattern_id": self.best_pattern_id,
            "best_pattern_description": self.best_pattern_description,
            "step_count": self.step_count,
            "steps": self.steps,
            "messages": self.messages,
            "checks": self.checks,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "threshold": GUARDRAILS_BD_HISTORICAL_MIN_SIMILARITY,
            "mode": GUARDRAILS_BD_HISTORICAL_PATTERN_MODE,
        }


_pattern_cache: Optional[List[LogPattern]] = None


def _levenshtein_distance(a: Sequence[str], b: Sequence[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, token_a in enumerate(a, start=1):
        curr = [i]
        for j, token_b in enumerate(b, start=1):
            cost = 0 if token_a == token_b else 1
            curr.append(min(curr[-1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def levenshtein_similarity(a: Sequence[str], b: Sequence[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    distance = _levenshtein_distance(a, b)
    return 1.0 - (distance / max(len(a), len(b)))


def _ngram_counter(sequence: Sequence[str], n: int) -> Counter:
    return Counter(build_ngrams(sequence, n))


def cosine_similarity_ngrams(a: Sequence[str], b: Sequence[str], n: int) -> float:
    grams_a = _ngram_counter(a, n)
    grams_b = _ngram_counter(b, n)
    if not grams_a and not grams_b:
        return 1.0
    if not grams_a or not grams_b:
        return 0.0
    keys = set(grams_a) | set(grams_b)
    dot = sum(grams_a[k] * grams_b[k] for k in keys)
    mag_a = math.sqrt(sum(v * v for v in grams_a.values()))
    mag_b = math.sqrt(sum(v * v for v in grams_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def combined_similarity(
    current_steps: Sequence[str],
    pattern_steps: Sequence[str],
    ngram_size: int,
    weight_levenshtein: float,
    weight_cosine: float,
) -> Dict[str, float]:
    lev = levenshtein_similarity(current_steps, pattern_steps)
    cos = cosine_similarity_ngrams(current_steps, pattern_steps, ngram_size)
    total_weight = weight_levenshtein + weight_cosine
    if total_weight <= 0:
        combined = lev
    else:
        combined = ((weight_levenshtein * lev) + (weight_cosine * cos)) / total_weight
    return {"combined": combined, "levenshtein": lev, "cosine": cos}


def load_patterns(pattern_dir: Optional[Path] = None, force_reload: bool = False) -> List[LogPattern]:
    """Load learned patterns from previous RCA runs (primary source)."""
    global _pattern_cache
    if _pattern_cache is not None and not force_reload:
        return _pattern_cache

    payload = load_learned_pattern_payload()
    patterns = [LogPattern.from_dict(item) for item in (payload.get("patterns") or []) if isinstance(item, dict)]

    # Fallback: static bootstrap patterns only when no learned history exists yet
    if not patterns:
        root = pattern_dir or PATTERN_DIR
        if root.is_dir():
            for path in sorted(root.glob("patterns.json")):
                try:
                    static_payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                for item in static_payload.get("patterns") or []:
                    if isinstance(item, dict):
                        item = dict(item)
                        item.setdefault("source_type", "bootstrap")
                        patterns.append(LogPattern.from_dict(item))

    _pattern_cache = patterns
    return patterns


def match_against_patterns(
    steps: Sequence[str],
    patterns: Optional[Sequence[LogPattern]] = None,
) -> Tuple[float, Optional[LogPattern], List[Dict[str, Any]]]:
    catalog = list(patterns) if patterns is not None else load_patterns()
    if not catalog:
        return 0.0, None, []

    best_score = -1.0
    best_pattern: Optional[LogPattern] = None
    checks: List[Dict[str, Any]] = []

    for pattern in catalog:
        scores = combined_similarity(
            steps,
            pattern.steps,
            GUARDRAILS_BD_HISTORICAL_NGRAM_SIZE,
            GUARDRAILS_BD_HISTORICAL_WEIGHT_LEVENSHTEIN,
            GUARDRAILS_BD_HISTORICAL_WEIGHT_COSINE,
        )
        checks.append({
            "pattern_id": pattern.id,
            "pattern_log_file": pattern.log_file,
            "pattern_description": pattern.description,
            "combined_score": round(scores["combined"], 4),
            "levenshtein_score": round(scores["levenshtein"], 4),
            "cosine_score": round(scores["cosine"], 4),
        })
        if scores["combined"] > best_score:
            best_score = scores["combined"]
            best_pattern = pattern

    return best_score, best_pattern, checks


def _skip_result(scenario: str, reason: str, steps: Optional[List[str]] = None) -> HistoricalPatternResult:
    return HistoricalPatternResult(
        passed=True,
        blocked=False,
        warned=False,
        similarity_score=1.0,
        scenario=scenario,
        steps=steps or [],
        step_count=len(steps or []),
        skipped=True,
        skip_reason=reason,
    )


def check_historical_pattern_text(
    text: str,
    log_filename: Optional[str] = None,
) -> HistoricalPatternResult:
    if not GUARDRAILS_BD_HISTORICAL_PATTERN_ENABLED:
        return _skip_result("unknown", "historical_pattern_disabled")

    sample = text[:MAX_SCAN_CHARS]
    steps = extract_milestone_sequence(sample)
    scenario = detect_scenario(steps, sample)

    if len(steps) < 2:
        return _skip_result(scenario, "insufficient_milestones", steps)

    patterns = load_patterns()
    if len(patterns) < GUARDRAILS_BD_HISTORICAL_MIN_PATTERNS:
        return HistoricalPatternResult(
            passed=True,
            blocked=False,
            warned=True,
            similarity_score=0.0,
            scenario=scenario,
            is_new_log=True,
            is_known_log=False,
            step_count=len(steps),
            steps=steps,
            messages=[
                "No historical log patterns are available yet.",
                "This log should be treated as new — human review is recommended.",
            ],
            skip_reason="no_learned_patterns_yet",
        )

    best_score, best_pattern, checks = match_against_patterns(steps, patterns)
    threshold = GUARDRAILS_BD_HISTORICAL_MIN_SIMILARITY

    # Fast path: same filename as a previously analyzed log
    filename_known = False
    if log_filename and patterns:
        normalized = _normalize_upload_filename(log_filename).lower()
        filename_known = any(
            str(p.log_file or "").lower() == normalized or str(p.source or "").lower() == normalized
            for p in patterns
        )

    is_known = filename_known or best_score >= threshold
    is_new = not is_known

    # New-log detection is always advisory: warn in the UI, never block Start RCA.
    # Mode balanced/strict remains available for future sequence-mismatch rules,
    # but "no similar prior log" must not stop analysis.
    blocked = False
    warned = is_new
    passed = True

    messages: List[str] = []
    matched_log_file = None
    if is_known:
        matched_log_file = best_pattern.log_file if best_pattern else log_filename
        if matched_log_file and best_score >= threshold:
            messages.append(
                f"Recognized as similar to a previously analyzed log ({matched_log_file})."
            )
    elif is_new:
        messages.append(
            "This appears to be a new log file — the system has not analyzed a similar log before."
        )
        messages.append(
            "Human review is recommended before relying on automated RCA results."
        )

    return HistoricalPatternResult(
        passed=passed,
        blocked=blocked,
        warned=warned,
        similarity_score=best_score if best_score >= 0 else 0.0,
        scenario=scenario,
        is_new_log=is_new,
        is_known_log=is_known,
        matched_log_file=matched_log_file,
        best_pattern_id=best_pattern.id if best_pattern else None,
        best_pattern_description=best_pattern.description if best_pattern else None,
        step_count=len(steps),
        steps=steps,
        messages=messages,
        checks=checks,
    )


def check_historical_pattern(path: Path) -> HistoricalPatternResult:
    content = path.read_text(encoding="utf-8", errors="replace")
    return check_historical_pattern_text(content, log_filename=_normalize_upload_filename(path.name))


def reload_learned_patterns() -> List[LogPattern]:
    """Force refresh from bug_history and reload the in-memory cache."""
    refresh_learned_patterns()
    return load_patterns(force_reload=True)
