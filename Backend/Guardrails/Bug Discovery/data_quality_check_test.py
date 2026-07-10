"""Tests for Bug Discovery data quality checks."""

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
_guardrails_pkg.log_milestone_extractor = _extractor
_store = _load_guardrail_module(
    "app/guardrails/log_pattern_store.py",
    "app.guardrails.log_pattern_store",
)
_guardrails_pkg.log_pattern_store = _store
_hist = _load_guardrail_module(
    "app/guardrails/historical_pattern_check.py",
    "app.guardrails.historical_pattern_check",
)
_guardrails_pkg.historical_pattern_check = _hist
_dq = _load_guardrail_module(
    "app/guardrails/data_quality_check.py",
    "app.guardrails.data_quality_check",
)
_guardrails_pkg.data_quality_check = _dq


check_data_quality_text = _dq.check_data_quality_text
check_data_quality = _dq.check_data_quality

SUCCESS_RRC = BACKEND_DIR / "resources/test_logs/TC_successful_rrc_connection_establishment_5421.log"
RACH_FAILURE = Path(__file__).resolve().parent / "ue_rach_failure_test.log"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_complete_rrc_log_passes() -> None:
    result = check_data_quality(SUCCESS_RRC)
    _assert(not result.incomplete_tail, f"complete RRC should not flag incomplete_tail: {result.messages}")
    _assert(not result.truncated, result.messages)
    _assert(result.completeness_score >= 0.7, result.completeness_score)
    print(f"OK complete_rrc: score={result.completeness_score:.2f} warned={result.warned}")


def test_truncated_midline() -> None:
    text = (
        "[MAC] [2025-09-11 18:24:48.000000] Initialization of 4-step contention-based random access procedure\n"
        "[PHY] [2025-09-11 18:24:48.001000] PRACH [UE 0] placing PRACH\n"
        "[NR_MAC] [2025-09-11 18:24:48.002000] RA-Msg3 transmitted\n"
        "[MAC] [2025-09-11 18:24:48.003000] incomplete line without closin"
    )
    result = check_data_quality_text(text)
    _assert(result.truncated, f"expected truncated: {result.evidence}")
    _assert(result.warned or result.blocked, result.messages)
    print(f"OK truncated: messages={result.messages}")


def test_empty_sections() -> None:
    text = "line1\n" + ("\n" * 50) + "line2\n"
    result = check_data_quality_text(text)
    _assert(result.empty_sections, f"expected empty sections: {result.evidence}")
    print(f"OK empty_sections: {result.messages}")


def test_incomplete_tail_registration() -> None:
    # Early RACH events only — no failure marker and no late RRC/NGAP tail
    text = "\n".join([
        "[MAC] [2025-09-11 18:24:48.000000] Initialization of 4-step contention-based random access procedure",
        "[PHY] [2025-09-11 18:24:48.001000] PRACH [UE 0] placing PRACH in position 2828",
        "[NR_MAC] [2025-09-11 18:24:48.002000] [RAPROC] RA-Msg3 transmitted",
        "[MAC] [2025-09-11 18:24:48.003000] In nr_Msg3_transmitted: contention resolution timer set",
        "[MAC] [2025-09-11 18:24:48.004000] waiting for contention resolution",
        "[PHY] [2025-09-11 18:24:48.005000] PUSCH decoding in progress",
        "[MAC] [2025-09-11 18:24:48.006000] still waiting",
        "[NR_MAC] [2025-09-11 18:24:48.007000] RAPROC ongoing",
    ])
    result = check_data_quality_text(text)
    _assert(result.incomplete_tail or result.warned, f"expected incomplete: {result.to_dict()}")
    _assert(
        any("incomplete" in m.lower() or "missing" in m.lower() for m in result.messages),
        result.messages,
    )
    print(f"OK incomplete_tail: missing={result.missing_tail_percent:.0f}% messages={result.messages}")


def test_rach_failure_not_flagged_as_incomplete() -> None:
    result = check_data_quality(RACH_FAILURE)
    _assert(not result.incomplete_tail, f"failure log should not be incomplete_tail: {result.messages}")
    _assert(not result.truncated, f"full rach fixture should not be truncated via scan-window artifact: {result.evidence.get('truncation')}")
    print(f"OK rach_failure_complete_capture: score={result.completeness_score:.2f}")


def test_midline_cuts_detected() -> None:
    cases = {
        "partial_ts": "[MAC]   [2",
        "mid_msg": "[NR_RRC]   [2025-09-11 18:24:48.299323]  nr_mac_rrc_data_req_ue: Pa",
    }
    for name, text in cases.items():
        result = check_data_quality_text(text)
        _assert(result.truncated, f"{name} should be truncated: {result.evidence}")
    print("OK midline_cuts")


def test_large_midbyte_truncation_detected() -> None:
    """Byte-cut past MAX_SCAN_CHARS must still use the true buffer end."""
    if not RACH_FAILURE.exists():
        print("SKIP large_midbyte_truncation (fixture missing)")
        return
    full = RACH_FAILURE.read_text(encoding="utf-8", errors="replace")
    cut = full[: max(1, len(full) // 2)]
    result = check_data_quality_text(cut)
    _assert(result.truncated, f"50% mid-byte cut should be truncated: {result.evidence.get('truncation')}")
    print(f"OK large_midbyte_truncation: reason={(result.evidence.get('truncation') or {}).get('reason')}")


def test_clean_half_file_truncation_detected() -> None:
    """Line-aligned half capture should still flag via peer byte-size ratio."""
    if not RACH_FAILURE.exists():
        print("SKIP clean_half_file_truncation (fixture missing)")
        return
    full = RACH_FAILURE.read_text(encoding="utf-8", errors="replace")
    lines = full.splitlines()
    cut = "\n".join(lines[: max(1, len(lines) // 2)]) + "\n"
    result = check_data_quality_text(cut)
    _assert(
        result.truncated or result.incomplete_tail,
        f"50% line-aligned cut should be incomplete: {result.evidence.get('truncation')}",
    )
    print(f"OK clean_half_file_truncation: reason={(result.evidence.get('truncation') or {}).get('reason')}")


def test_explicit_truncation_marker() -> None:
    text = "[MAC] start\n[PHY] mid\n[RRC] end\n--- truncated ---\n"
    result = check_data_quality_text(text)
    _assert(result.truncated, result.messages)
    print("OK truncation_marker")


if __name__ == "__main__":
    test_complete_rrc_log_passes()
    test_truncated_midline()
    test_empty_sections()
    test_incomplete_tail_registration()
    test_rach_failure_not_flagged_as_incomplete()
    test_midline_cuts_detected()
    test_large_midbyte_truncation_detected()
    test_clean_half_file_truncation_detected()
    test_explicit_truncation_marker()
    print("All data quality tests passed.")
