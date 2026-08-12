"""Tests for Bug Discovery confidence-based context check."""

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

# Lightweight deps used by context confidence / scenario
for rel, name in (
    ("app/guardrails/log_milestone_extractor.py", "app.guardrails.log_milestone_extractor"),
    ("app/guardrails/log_pattern_store.py", "app.guardrails.log_pattern_store"),
    ("app/guardrails/telecom_domain_check.py", "app.guardrails.telecom_domain_check"),
    ("app/guardrails/historical_pattern_check.py", "app.guardrails.historical_pattern_check"),
    ("app/guardrails/data_quality_check.py", "app.guardrails.data_quality_check"),
    ("app/guardrails/scenario_relevance_check.py", "app.guardrails.scenario_relevance_check"),
    ("app/guardrails/context_confidence_check.py", "app.guardrails.context_confidence_check"),
):
    mod = _load_guardrail_module(rel, name)
    setattr(_guardrails_pkg, name.rsplit(".", 1)[-1], mod)

_telecom = sys.modules["app.guardrails.telecom_domain_check"]
_scenario = sys.modules["app.guardrails.scenario_relevance_check"]
_context = sys.modules["app.guardrails.context_confidence_check"]
_hist = sys.modules["app.guardrails.historical_pattern_check"]
_dq = sys.modules["app.guardrails.data_quality_check"]

check_telecom_domain = _telecom.check_telecom_domain
check_scenario_relevance = _scenario.check_scenario_relevance
check_historical_pattern = _hist.check_historical_pattern
check_data_quality = _dq.check_data_quality
compute_context_confidence = _context.compute_context_confidence

LOG_DIR = BACKEND_DIR / "app/services/Error_fixing_pipelin/log_files"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_scorecard_fields_present() -> None:
    log = LOG_DIR / "success_ue_gnb.log"
    if not log.exists():
        print("SKIP success_ue_gnb.log")
        return
    telecom = check_telecom_domain(log)
    historical = check_historical_pattern(log)
    data_quality = check_data_quality(log)
    scenario = check_scenario_relevance(log, reported_scenario="attach")
    sample = log.read_text(encoding="utf-8", errors="replace")[:80000]
    result = compute_context_confidence(
        telecom=telecom,
        historical=historical,
        data_quality=data_quality,
        scenario=scenario,
        filename=log.name,
        log_text=sample,
    )
    _assert(len(result.scorecard) == 5, f"expected 5 scorecard lines, got {result.scorecard}")
    _assert(result.scorecard[0].startswith("Telecom relevance:"), result.scorecard[0])
    _assert(result.scorecard[1].startswith("Scenario match:"), result.scorecard[1])
    _assert(result.scorecard[2].startswith("Completeness:"), result.scorecard[2])
    _assert(result.scorecard[3].startswith("Environment match:"), result.scorecard[3])
    _assert(result.scorecard[4].startswith("Overall context score:"), result.scorecard[4])
    payload = result.to_dict()
    for key in (
        "telecom_relevance",
        "scenario_match",
        "completeness",
        "environment_match",
        "overall",
        "threshold",
    ):
        _assert(key in payload, f"missing {key}")
    print(
        f"OK scorecard: overall={result.overall:.2f} "
        f"scenario={result.scenario_match:.2f} env={result.environment_match:.2f}"
    )


def test_attach_alias_sets_registration() -> None:
    sample = """
[NR_RRC] Decoding CCCH: RRCSetupRequest
[NR_RRC] Send RRC Setup
[NR_RRC] Received RRCSetupComplete
[NAS] Registration Request
"""
    result = _scenario.check_scenario_relevance_text(
        sample,
        log_filename="ue_attach.log",
        reported_scenario="attach",
    )
    _assert("registration" in result.expected_scenarios, result.expected_scenarios)
    _assert(result.target_scenario == "attach", result.target_scenario)
    _assert(isinstance(result.scenario_match_score, float), "missing match score")
    _assert(result.scenario_match_score > 0, f"score={result.scenario_match_score}")
    print(f"OK attach alias: match={result.scenario_match_score:.2f}")


def test_success_ue_not_blocked_advisory() -> None:
    log = LOG_DIR / "success_ue_gnb.log"
    if not log.exists():
        print("SKIP success_ue_gnb.log")
        return
    telecom = check_telecom_domain(log)
    historical = check_historical_pattern(log)
    data_quality = check_data_quality(log)
    scenario = check_scenario_relevance(log, reported_scenario="attach")
    sample = log.read_text(encoding="utf-8", errors="replace")[:80000]
    result = compute_context_confidence(
        telecom=telecom,
        historical=historical,
        data_quality=data_quality,
        scenario=scenario,
        filename=log.name,
        log_text=sample,
    )
    _assert(not result.blocked, f"should not block in advisory: {result.messages}")
    print(
        f"OK success_ue context: overall={result.overall:.2f} "
        f"warned={result.warned} blocked={result.blocked}"
    )


def test_nginx_hard_fail_still_telecom() -> None:
    nginx = FIXTURES / "nginx_access.log"
    if not nginx.exists():
        print("SKIP nginx_access.log")
        return
    telecom = check_telecom_domain(nginx)
    _assert(telecom.blocked, "nginx should still be blocked by telecom domain")
    result = compute_context_confidence(
        telecom=telecom,
        historical=None,
        data_quality=None,
        scenario=None,
        filename=nginx.name,
        log_text=nginx.read_text(encoding="utf-8", errors="replace"),
    )
    _assert(result.overall < result.threshold, f"nginx overall should be low: {result.overall}")
    _assert(any("Telecom relevance:" in line for line in result.scorecard), result.scorecard)
    print(f"OK nginx context overall={result.overall:.2f} (telecom blocked separately)")


def test_cmake_error_matches_reference_scorecard() -> None:
    """CMake/build log reference: telecom 90 / scenario 5 / completeness 10 / env 95 / overall 50."""
    log = LOG_DIR / "CMake_error_1.log"
    if not log.exists():
        print("SKIP CMake_error_1.log")
        return
    telecom = check_telecom_domain(log)
    historical = check_historical_pattern(log)
    data_quality = check_data_quality(log)
    scenario = check_scenario_relevance(log, reported_scenario="attach")
    sample = log.read_text(encoding="utf-8", errors="replace")[:80000]
    result = compute_context_confidence(
        telecom=telecom,
        historical=historical,
        data_quality=data_quality,
        scenario=scenario,
        filename=log.name,
        log_text=sample,
    )
    _assert(round(result.telecom_relevance, 2) == 0.90, result.telecom_relevance)
    _assert(round(result.scenario_match, 2) == 0.05, result.scenario_match)
    _assert(round(result.completeness, 2) == 0.10, result.completeness)
    _assert(round(result.environment_match, 2) == 0.95, result.environment_match)
    _assert(round(result.overall, 2) == 0.50, result.overall)
    _assert(result.evidence.get("is_build_capture") is True, result.evidence)
    print(
        f"OK cmake reference: telecom={result.telecom_relevance:.2f} "
        f"scenario={result.scenario_match:.2f} completeness={result.completeness:.2f} "
        f"env={result.environment_match:.2f} overall={result.overall:.2f}"
    )


def test_success_cu_matches_reference_scorecard() -> None:
    """success_cu reference: telecom 100 / scenario 100 / completeness 92 / env 100 / overall 98."""
    log = LOG_DIR / "success_cu_gnb.log"
    if not log.exists():
        print("SKIP success_cu_gnb.log")
        return
    telecom = check_telecom_domain(log)
    historical = check_historical_pattern(log)
    data_quality = check_data_quality(log)
    scenario = check_scenario_relevance(log, reported_scenario="attach")
    sample = log.read_text(encoding="utf-8", errors="replace")[:80000]
    result = compute_context_confidence(
        telecom=telecom,
        historical=historical,
        data_quality=data_quality,
        scenario=scenario,
        filename=log.name,
        log_text=sample,
    )
    _assert(round(result.telecom_relevance, 2) == 1.00, result.telecom_relevance)
    _assert(round(result.scenario_match, 2) == 1.00, result.scenario_match)
    _assert(round(result.completeness, 2) == 0.92, result.completeness)
    _assert(round(result.environment_match, 2) == 1.00, result.environment_match)
    _assert(round(result.overall, 2) == 0.98, result.overall)
    _assert(result.evidence.get("is_build_capture") is False, result.evidence)
    print(
        f"OK success_cu reference: telecom={result.telecom_relevance:.2f} "
        f"scenario={result.scenario_match:.2f} completeness={result.completeness:.2f} "
        f"env={result.environment_match:.2f} overall={result.overall:.2f}"
    )


def main() -> None:
    test_attach_alias_sets_registration()
    test_scorecard_fields_present()
    test_success_ue_not_blocked_advisory()
    test_nginx_hard_fail_still_telecom()
    test_cmake_error_matches_reference_scorecard()
    test_success_cu_matches_reference_scorecard()
    print("All context confidence tests passed.")


if __name__ == "__main__":
    main()
