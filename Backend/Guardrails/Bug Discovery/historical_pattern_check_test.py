"""Tests for historical pattern matching (Bug Discovery) — learned log detection."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _load_guardrail_module(relative: str, module_name: str) -> ModuleType:
    path = BACKEND_DIR / relative
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_app_pkg = ModuleType("app")
_guardrails_pkg = ModuleType("app.guardrails")
sys.modules.setdefault("app", _app_pkg)
sys.modules.setdefault("app.guardrails", _guardrails_pkg)
_app_pkg.guardrails = _guardrails_pkg

_config = _load_guardrail_module("app/guardrails/config.py", "app.guardrails.config")
_guardrails_pkg.config = _config

_extractor = _load_guardrail_module(
    "app/guardrails/log_milestone_extractor.py",
    "app.guardrails.log_milestone_extractor",
)
_store = _load_guardrail_module(
    "app/guardrails/log_pattern_store.py",
    "app.guardrails.log_pattern_store",
)
_historical = _load_guardrail_module(
    "app/guardrails/historical_pattern_check.py",
    "app.guardrails.historical_pattern_check",
)

extract_milestone_sequence = _extractor.extract_milestone_sequence
detect_scenario = _extractor.detect_scenario
build_ngrams = _extractor.build_ngrams
levenshtein_similarity = _historical.levenshtein_similarity
cosine_similarity_ngrams = _historical.cosine_similarity_ngrams
check_historical_pattern = _historical.check_historical_pattern
load_patterns = _historical.load_patterns
refresh_learned_patterns = _store.refresh_learned_patterns

FIXTURES = Path(__file__).resolve().parent
KNOWN_LOG = BACKEND_DIR / "app/services/Error_fixing_pipelin/log_files/ue_rach_failure.log"
NEW_LOG = BACKEND_DIR / "app/services/Error_fixing_pipelin/log_files/success_cu_gnb.log"
BUILD_LOG = BACKEND_DIR / "app/services/Error_fixing_pipelin/log_files/CMake_error_1.log"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_learned_patterns_synced_from_history() -> None:
    patterns = refresh_learned_patterns()
    _assert(len(patterns) >= 2, f"expected learned patterns, got {len(patterns)}")
    print(f"OK learned_sync: {len(patterns)} patterns")


def test_known_log_from_previous_rca() -> None:
    load_patterns(force_reload=True)
    result = check_historical_pattern(KNOWN_LOG)
    _assert(result.is_known_log, f"expected known log, got new={result.is_new_log}")
    _assert(not result.warned, f"known log should not warn: {result.messages}")
    _assert(result.similarity_score >= 0.65, f"low score: {result.similarity_score}")
    print(f"OK known_log: {KNOWN_LOG.name} score={result.similarity_score:.3f}")


def test_new_log_triggers_human_review_warning() -> None:
    # Short but extractable OAI-like sequence that stays below similarity threshold.
    synthetic = """
[NGAP] Send NGSetupRequest to AMF
[NGAP] Received NGSetupResponse from AMF
[F1AP] Starting F1AP
[NAS] Registration Request
[PHY] totally unique xyz_quantum_marker_781
[MAC] Contention resolution timer has expired unique_seq_only
"""
    result = _historical.check_historical_pattern_text(
        synthetic,
        log_filename="brand_new_unique_xyz.log",
    )
    _assert(result.is_new_log, f"expected new log, known={result.is_known_log} score={result.similarity_score}")
    _assert(result.warned, f"new log should warn: {result.messages}")
    _assert(not result.blocked, "new log must never block RCA analysis")
    _assert(result.passed, "new log must pass so Start RCA continues")
    _assert(any("new log file" in m.lower() for m in result.messages), result.messages)
    _assert(any("human review" in m.lower() for m in result.messages), result.messages)
    _assert(
        not any("closest prior" in m.lower() for m in result.messages),
        f"closest prior match must not appear in messages: {result.messages}",
    )
    print(f"OK new_log: warned score={result.similarity_score:.3f}")


def test_similar_build_log_recognized_from_history() -> None:
    result = check_historical_pattern(BUILD_LOG)
    _assert(result.is_known_log, f"build log should match learned cmake pattern: {result.messages}")
    print(f"OK build_known: score={result.similarity_score:.3f}")


def test_milestone_extraction() -> None:
    text = KNOWN_LOG.read_text(encoding="utf-8", errors="replace")
    steps = extract_milestone_sequence(text)
    _assert(len(steps) >= 2, steps)
    _assert(detect_scenario(steps, text) == "registration", detect_scenario(steps, text))
    print(f"OK milestones: {len(steps)} steps")


def test_ngram_and_similarity_helpers() -> None:
    a = ["stack_init", "ra_start", "msg3_tx", "contention_timer_expired"]
    b = ["stack_init", "ra_start", "msg3_tx", "contention_timer_expired"]
    grams = build_ngrams(a, 3)
    _assert(len(grams) == 2, grams)
    _assert(levenshtein_similarity(a, b) == 1.0, "identical sequences")
    _assert(cosine_similarity_ngrams(a, b, 3) >= 0.999, "identical n-grams")
    print("OK helpers")


if __name__ == "__main__":
    test_learned_patterns_synced_from_history()
    test_milestone_extraction()
    test_ngram_and_similarity_helpers()
    test_known_log_from_previous_rca()
    test_new_log_triggers_human_review_warning()
    test_similar_build_log_recognized_from_history()
    print("All historical pattern tests passed.")
