"""Tests for Registration / PDU Session / Handover scenario message coverage."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_app = ModuleType("app")
_g = ModuleType("app.guardrails")
sys.modules.setdefault("app", _app)
sys.modules.setdefault("app.guardrails", _g)
_app.guardrails = _g

_spec = importlib.util.spec_from_file_location(
    "app.guardrails.scenario_message_coverage",
    BACKEND_DIR / "app/guardrails/scenario_message_coverage.py",
)
assert _spec and _spec.loader
_smc = importlib.util.module_from_spec(_spec)
sys.modules["app.guardrails.scenario_message_coverage"] = _smc
_spec.loader.exec_module(_smc)
_g.scenario_message_coverage = _smc

validate_scenario_message_coverage = _smc.validate_scenario_message_coverage


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _full_suite() -> list:
    return [
        {
            "testCaseID": "TC_REG_001",
            "title": "Registration Test - positive",
            "testSteps": [
                "UE sends Registration Request",
                "Network returns Registration Accept",
                "UE sends Registration Complete",
            ],
            "expectedResults": ["UE registered"],
        },
        {
            "testCaseID": "TC_PDU_001",
            "title": "PDU Session Test - establishment",
            "testSteps": [
                "Send PDU Session Establishment Request",
                "Perform PDU Session Authentication",
                "Receive PDU Session Accept",
                "Complete User Plane Setup and N3 Tunnel Creation",
                "Verify SMF/UPF and QoS Flow",
            ],
            "expectedResults": ["PDU Session Establishment successful"],
        },
        {
            "testCaseID": "TC_HO_001",
            "title": "Handover Test - Xn mobility",
            "testSteps": [
                "UE sends Measurement Report",
                "Source gNB sends Handover Required",
                "Target gNB receives Handover Request and returns Handover Request Ack",
                "UE applies RRC Reconfiguration",
                "AMF performs Path Switch",
                "Handover Complete",
            ],
            "expectedResults": ["Xn Handover succeeds"],
        },
    ]


def test_full_suite_passes() -> None:
    result = validate_scenario_message_coverage(json.dumps(_full_suite()))
    _assert(result.passed, result.to_dict())
    triggered = [c for c in result.checks if c.triggered]
    _assert(len(triggered) == 3, triggered)
    print("OK full_suite_passes")


def test_registration_only_fails_pdu_and_handover() -> None:
    cases = [
        {
            "testCaseID": "TC_POS_001",
            "title": "Positive Registration",
            "testSteps": ["Registration Request", "Registration Accept"],
            "expectedResults": ["OK"],
        }
    ]
    result = validate_scenario_message_coverage(json.dumps(cases))
    _assert(not result.passed, result.to_dict())
    failed = {c.scenario_id: c for c in result.checks if c.triggered and not c.passed}
    _assert("pdu_session" in failed, failed)
    _assert("handover" in failed, failed)
    _assert(any("PDU Session" in w for w in result.warnings), result.warnings)
    _assert(any("Handover" in w for w in result.warnings), result.warnings)
    print("OK registration_only_fails_others")


def test_secondary_node_release_is_not_handover() -> None:
    cases = _full_suite()
    cases[2] = {
        "testCaseID": "TC_INT_001",
        "title": "Secondary Node Release integration",
        "testSteps": ["Trigger Secondary Node Release", "Confirm SgNB Release"],
        "expectedResults": ["SN released"],
    }
    result = validate_scenario_message_coverage(json.dumps(cases))
    _assert(not result.passed, result.to_dict())
    ho = next(c for c in result.checks if c.scenario_id == "handover")
    _assert(not ho.dedicated_testcase, ho.to_dict())
    _assert(not ho.passed, ho.to_dict())
    print("OK secondary_node_release_not_handover")


def test_pdu_missing_establishment_events() -> None:
    cases = _full_suite()
    cases[1] = {
        "testCaseID": "TC_PDU_002",
        "title": "PDU Session Test",
        "testSteps": ["Open a data bearer"],
        "expectedResults": ["Session active"],
    }
    result = validate_scenario_message_coverage(json.dumps(cases))
    _assert(not result.passed, result.to_dict())
    pdu = next(c for c in result.checks if c.scenario_id == "pdu_session")
    _assert(not pdu.passed, pdu.to_dict())
    print("OK pdu_missing_establishment")


def test_handover_with_request_passes() -> None:
    cases = _full_suite()
    result = validate_scenario_message_coverage(json.dumps(cases))
    ho = next(c for c in result.checks if c.scenario_id == "handover")
    _assert(ho.passed and ho.dedicated_testcase, ho.to_dict())
    print("OK handover_with_request_passes")


if __name__ == "__main__":
    test_full_suite_passes()
    test_registration_only_fails_pdu_and_handover()
    test_secondary_node_release_is_not_handover()
    test_pdu_missing_establishment_events()
    test_handover_with_request_passes()
    print("All scenario message coverage tests passed.")
