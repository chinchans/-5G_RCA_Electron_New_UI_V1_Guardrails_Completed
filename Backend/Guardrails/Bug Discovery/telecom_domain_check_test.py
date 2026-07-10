"""Tests for OAI telecom domain validation (Bug Discovery)."""

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


# Load without pulling FastAPI via app.guardrails.__init__
_app_pkg = ModuleType("app")
_guardrails_pkg = ModuleType("app.guardrails")
sys.modules.setdefault("app", _app_pkg)
sys.modules.setdefault("app.guardrails", _guardrails_pkg)
_app_pkg.guardrails = _guardrails_pkg

_config = _load_guardrail_module("app/guardrails/config.py", "app.guardrails.config")
_guardrails_pkg.config = _config

_telecom = _load_guardrail_module(
    "app/guardrails/telecom_domain_check.py",
    "app.guardrails.telecom_domain_check",
)
check_telecom_domain = _telecom.check_telecom_domain
check_telecom_domain_text = _telecom.check_telecom_domain_text

FIXTURES = Path(__file__).resolve().parent / "fixtures"
OAI_LOG = Path(__file__).resolve().parent / "ue_rach_failure_test.log"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_oai_rach_log_passes() -> None:
    result = check_telecom_domain(OAI_LOG)
    _assert(result.structural_score >= 0.25, f"low structural: {result.structural_score}")
    _assert(result.telecom_relevance >= 0.65, f"low relevance: {result.telecom_relevance}")
    _assert(result.passed, f"expected pass, got blocked={result.blocked} messages={result.messages}")
    _assert(not result.blocked, "OAI log should not be blocked")
    print(f"OK oai_rach: relevance={result.telecom_relevance:.2f} profile={result.profile}")


def test_nginx_blocked() -> None:
    result = check_telecom_domain(FIXTURES / "nginx_access.log")
    _assert(result.blocked, "nginx log should be blocked")
    _assert(result.structural_score < 0.25, "nginx should fail structural")
    print(f"OK nginx: blocked relevance={result.telecom_relevance:.2f}")


def test_fake_keywords_blocked() -> None:
    result = check_telecom_domain(FIXTURES / "fake_5g_keywords.log")
    _assert(result.blocked, "keyword-only doc should be blocked")
    print(f"OK fake_keywords: blocked relevance={result.telecom_relevance:.2f}")


def test_postgres_blocked() -> None:
    result = check_telecom_domain(FIXTURES / "postgres_query.log")
    _assert(result.blocked, "postgres log should be blocked")
    print(f"OK postgres: blocked relevance={result.telecom_relevance:.2f}")


def test_minimal_oai_structure_passes() -> None:
    sample = """
[ITTI]   [2025-07-12 10:35:20.001234]  Starting itti queue: TASK_NGAP as task 17
[MAC]   [2025-07-12 10:35:21.001234]  [UE 0] CB-RA: Contention resolution timer has expired
[NR_RRC]   [2025-07-12 10:35:22.001234]  nr_mac_rrc_data_req_ue: Payload size = 56
"""
    result = check_telecom_domain_text(sample, filename="ue_rach_failure_test.log")
    _assert(result.structural_score >= 0.25, f"minimal OAI structural low: {result.structural_score}")
    _assert(not result.blocked, "minimal OAI structure should not block")
    print(f"OK minimal_oai: relevance={result.telecom_relevance:.2f}")


def test_gnb_plain_oai_log_passes() -> None:
    log = BACKEND_DIR / "app/services/Error_fixing_pipelin/log_files/gnb.log"
    if not log.exists():
        print("SKIP gnb.log (file not found)")
        return
    result = check_telecom_domain(log)
    _assert(not result.blocked, f"gnb.log blocked: {result.messages}")
    _assert(result.structural_score >= 0.25, f"gnb structural low: {result.structural_score}")
    print(f"OK gnb.log: relevance={result.telecom_relevance:.2f} profile={result.profile}")


def test_cmake_build_log_passes() -> None:
    log = BACKEND_DIR / "app/services/Error_fixing_pipelin/log_files/CMake_error_1.log"
    result = check_telecom_domain(log)
    _assert(not result.blocked, f"CMake_error_1.log blocked: {result.messages}")
    print(f"OK cmake_build: relevance={result.telecom_relevance:.2f} profile={result.profile}")


def test_all_pipeline_log_files_pass() -> None:
    log_dir = BACKEND_DIR / "app/services/Error_fixing_pipelin/log_files"
    blocked = []
    for path in sorted(log_dir.iterdir()):
        if path.suffix.lower() not in {".log", ".txt"}:
            continue
        result = check_telecom_domain(path)
        if result.blocked:
            blocked.append(path.name)
    _assert(not blocked, f"pipeline log_files blocked: {blocked}")
    print(f"OK all pipeline logs pass ({len(list(log_dir.glob('*.log')))} files)")


def test_windows_log_blocked() -> None:
    win_log = (
        Path(__file__).resolve().parent
        / "Testing/Log files/Windows Log files/WinEvents.log"
    )
    if not win_log.exists():
        print("SKIP windows log (file not found)")
        return
    result = check_telecom_domain(win_log)
    _assert(result.blocked, "Windows event log should be blocked")
    _assert(
        any("5G network component" in message for message in result.messages),
        f"expected domain message, got {result.messages}",
    )
    print(f"OK windows: blocked relevance={result.telecom_relevance:.2f}")


def main() -> None:
    test_oai_rach_log_passes()
    test_gnb_plain_oai_log_passes()
    test_cmake_build_log_passes()
    test_all_pipeline_log_files_pass()
    test_windows_log_blocked()
    test_nginx_blocked()
    test_fake_keywords_blocked()
    test_postgres_blocked()
    test_minimal_oai_structure_passes()
    print("All telecom domain tests passed.")


if __name__ == "__main__":
    main()
