"""
Build and persist canonical log patterns from reference OAI log files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.guardrails.config import BACKEND_DIR
from app.guardrails.historical_pattern_check import LogPattern, PATTERN_DIR, load_patterns
from app.guardrails.log_milestone_extractor import (
    build_ngrams,
    detect_scenario,
    extract_milestones_from_file,
)

DEFAULT_SOURCES: Dict[str, Dict[str, str]] = {
    "registration_success_rrc_5421": {
        "path": "resources/test_logs/TC_successful_rrc_connection_establishment_5421.log",
        "scenario": "registration",
        "description": "Successful RRC connection establishment and NGAP Initial UE Message",
    },
    "registration_success_cu_gnb": {
        "path": "Guardrails/Bug Discovery/success_cu_gnb.log",
        "scenario": "cu_stack",
        "description": "Successful CU gNB NGAP setup and F1AP bring-up",
    },
    "registration_success_du_gnb": {
        "path": "Guardrails/Bug Discovery/success_du_gnb.log",
        "scenario": "cu_stack",
        "description": "Successful DU gNB stack initialization",
    },
}


def pattern_from_log(
    pattern_id: str,
    log_path: Path,
    scenario: str,
    description: str,
    ngram_size: int = 3,
) -> LogPattern:
    steps = extract_milestones_from_file(log_path)
    if not scenario or scenario == "unknown":
        scenario = detect_scenario(steps, log_path.read_text(encoding="utf-8", errors="replace")[:8000])
    grams = build_ngrams(steps, ngram_size)
    return LogPattern(
        id=pattern_id,
        scenario=scenario,
        description=description,
        source=log_path.name,
        steps=steps,
        ngrams=[list(g) for g in grams],
    )


def build_patterns_from_sources(
    sources: Optional[Dict[str, Dict[str, str]]] = None,
    backend_dir: Optional[Path] = None,
    ngram_size: int = 3,
) -> List[LogPattern]:
    root = backend_dir or BACKEND_DIR
    catalog = sources or DEFAULT_SOURCES
    patterns: List[LogPattern] = []
    for pattern_id, meta in catalog.items():
        rel = meta["path"]
        log_path = root / rel
        if not log_path.is_file():
            continue
        patterns.append(
            pattern_from_log(
                pattern_id=pattern_id,
                log_path=log_path,
                scenario=meta["scenario"],
                description=meta["description"],
                ngram_size=ngram_size,
            )
        )
    return patterns


def save_patterns(
    patterns: List[LogPattern],
    output_dir: Optional[Path] = None,
    filename: str = "patterns.json",
) -> Path:
    out_dir = output_dir or PATTERN_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        "version": 1,
        "patterns": [p.to_dict() for p in patterns],
    }
    out_path = out_dir / filename
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    load_patterns(force_reload=True)
    return out_path


def build_and_save_default_patterns(ngram_size: int = 3) -> Path:
    patterns = build_patterns_from_sources(ngram_size=ngram_size)
    return save_patterns(patterns)


if __name__ == "__main__":
    path = build_and_save_default_patterns()
    print(f"Wrote {path}")
