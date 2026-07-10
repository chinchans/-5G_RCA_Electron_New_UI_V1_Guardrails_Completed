"""
Learned log pattern store — built from previously completed RCA analyses.

Patterns are promoted when Bug Discovery finishes a successful analysis and are
also synced from resources/bug_history/*.json on load.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.guardrails.config import BACKEND_DIR, GUARDRAILS_BD_HISTORICAL_NGRAM_SIZE
from app.guardrails.log_milestone_extractor import (
    build_ngrams,
    detect_scenario,
    extract_milestones_from_file,
)

BUG_HISTORY_DIR = BACKEND_DIR / "resources" / "bug_history"
LEARNED_PATTERNS_FILE = (
    BACKEND_DIR / "resources" / "guardrails" / "log_patterns" / "learned_patterns.json"
)


def _pattern_payload(
    pattern_id: str,
    log_path: Path,
    steps: List[str],
    *,
    log_file: str,
    scenario: str,
    history_file: Optional[str] = None,
    description: Optional[str] = None,
    ngram_size: int = GUARDRAILS_BD_HISTORICAL_NGRAM_SIZE,
) -> Dict[str, Any]:
    grams = build_ngrams(steps, ngram_size)
    return {
        "id": pattern_id,
        "scenario": scenario,
        "description": description or f"Learned from previous RCA on {log_file}",
        "source": log_path.name,
        "log_file": log_file,
        "log_path": str(log_path),
        "history_file": history_file,
        "source_type": "learned",
        "steps": steps,
        "ngrams": [list(g) for g in grams],
    }


def _resolve_log_path(raw_path: Optional[str], log_file: Optional[str]) -> Optional[Path]:
    if raw_path:
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = (BACKEND_DIR / path).resolve()
        else:
            path = path.resolve()
        if path.is_file():
            return path
    if log_file:
        candidates = [
            BACKEND_DIR / "app/services/Error_fixing_pipelin/log_files" / log_file,
            BACKEND_DIR / "resources/rca_logs" / log_file,
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        # Search rca_logs for uuid-prefixed uploads
        rca_dir = BACKEND_DIR / "resources/rca_logs"
        if rca_dir.is_dir():
            for match in rca_dir.glob(f"*_{log_file}"):
                if match.is_file():
                    return match.resolve()
    return None


def _is_completed_analysis(record: Dict[str, Any]) -> bool:
    summary = (record.get("results") or {}).get("summary") or {}
    return bool(summary.get("analysis_completed"))


def pattern_from_history_record(
    record: Dict[str, Any],
    history_filename: str,
    ngram_size: int = GUARDRAILS_BD_HISTORICAL_NGRAM_SIZE,
) -> Optional[Dict[str, Any]]:
    if not _is_completed_analysis(record):
        return None

    log_file = str(record.get("log_file") or "").strip()
    log_path = _resolve_log_path(record.get("log_path"), log_file)
    if not log_path:
        return None

    steps = extract_milestones_from_file(log_path)
    if len(steps) < 2:
        return None

    if not log_file:
        log_file = log_path.name

    scenario = detect_scenario(steps, log_path.read_text(encoding="utf-8", errors="replace")[:8000])
    pattern_id = f"learned_{Path(log_file).stem}"
    return _pattern_payload(
        pattern_id,
        log_path,
        steps,
        log_file=log_file,
        scenario=scenario,
        history_file=history_filename,
        ngram_size=ngram_size,
    )


def sync_patterns_from_bug_history(
    history_dir: Optional[Path] = None,
    ngram_size: int = GUARDRAILS_BD_HISTORICAL_NGRAM_SIZE,
) -> List[Dict[str, Any]]:
    """Load one pattern per log file from completed bug_history analyses (latest wins)."""
    root = history_dir or BUG_HISTORY_DIR
    if not root.is_dir():
        return []

    latest_by_log: Dict[str, Dict[str, Any]] = {}
    for path in sorted(root.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        pattern = pattern_from_history_record(record, path.name, ngram_size=ngram_size)
        if not pattern:
            continue
        log_key = str(pattern.get("log_file") or "").lower()
        if log_key:
            latest_by_log[log_key] = pattern

    return list(latest_by_log.values())


def load_learned_pattern_payload(force_sync: bool = False) -> Dict[str, Any]:
    patterns = sync_patterns_from_bug_history() if force_sync else None
    if patterns is None and LEARNED_PATTERNS_FILE.is_file():
        try:
            payload = json.loads(LEARNED_PATTERNS_FILE.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get("patterns"):
                return payload
        except (OSError, json.JSONDecodeError):
            pass
        patterns = sync_patterns_from_bug_history()
    elif patterns is None:
        patterns = sync_patterns_from_bug_history()

    return {"version": 1, "patterns": patterns or []}


def save_learned_patterns(patterns: List[Dict[str, Any]]) -> Path:
    LEARNED_PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "patterns": patterns}
    LEARNED_PATTERNS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return LEARNED_PATTERNS_FILE


def refresh_learned_patterns() -> List[Dict[str, Any]]:
    patterns = sync_patterns_from_bug_history()
    save_learned_patterns(patterns)
    return patterns


def promote_log_pattern(
    log_path: str | Path,
    log_file: Optional[str] = None,
    history_file: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Add or update a learned pattern after a successful RCA run."""
    path = Path(log_path).expanduser().resolve()
    if not path.is_file():
        return None

    steps = extract_milestones_from_file(path)
    if len(steps) < 2:
        return None

    resolved_log_file = log_file or path.name
    scenario = detect_scenario(steps, path.read_text(encoding="utf-8", errors="replace")[:8000])
    pattern = _pattern_payload(
        f"learned_{Path(resolved_log_file).stem}",
        path,
        steps,
        log_file=resolved_log_file,
        scenario=scenario,
        history_file=history_file,
    )

    existing_payload = load_learned_pattern_payload()
    patterns: List[Dict[str, Any]] = list(existing_payload.get("patterns") or [])
    key = resolved_log_file.lower()
    patterns = [p for p in patterns if str(p.get("log_file", "")).lower() != key]
    patterns.append(pattern)
    save_learned_patterns(patterns)
    return pattern
