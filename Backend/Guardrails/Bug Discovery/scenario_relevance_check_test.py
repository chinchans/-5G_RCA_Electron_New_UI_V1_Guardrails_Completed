"""Tests for Bug Discovery scenario relevance (advisory Registration / PDU over RCA)."""

from __future__ import annotations

import importlib.util
import re
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

_config = importlib.util.spec_from_file_location(
    "app.guardrails.config", BACKEND_DIR / "app/guardrails/config.py"
)
assert _config and _config.loader
_config_mod = importlib.util.module_from_spec(_config)
sys.modules["app.guardrails.config"] = _config_mod
_config.loader.exec_module(_config_mod)
_g.config = _config_mod

_spec = importlib.util.spec_from_file_location(
    "app.guardrails.scenario_relevance_check",
    BACKEND_DIR / "app/guardrails/scenario_relevance_check.py",
)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["app.guardrails.scenario_relevance_check"] = _mod
_spec.loader.exec_module(_mod)
_g.scenario_relevance_check = _mod

check_scenario_relevance_text = _mod.check_scenario_relevance_text
check_scenario_relevance = _mod.check_scenario_relevance
_REGISTRATION_FAIL_MESSAGE = _mod._REGISTRATION_FAIL_MESSAGE
_PDU_SESSION_FAIL_MESSAGE = _mod._PDU_SESSION_FAIL_MESSAGE
_BOTH_REG_PDU_FAIL_MESSAGE = _mod._BOTH_REG_PDU_FAIL_MESSAGE
_RACH_FAIL_MESSAGE = _mod._RACH_FAIL_MESSAGE

_FULL_CU_FLOW = """
[NR_RRC]   Decoding CCCH: RNTI 0388, payload_size 6
[NR_RRC]   [--] (cellID 0, UE ID 1 RNTI 0388) Create UE context: CU UE ID 1
[RRC]   activate SRB 1 of UE 1
[NR_RRC]   [DL] (cellID 1, UE ID 1 RNTI 0388) Send RRC Setup
[F1AP]   CU send DL_RRC_MESSAGE_TRANSFER
[NR_RRC]   [UL] (cellID 1, UE ID 1 RNTI 0388) Received RRCSetupComplete (RRC_CONNECTED reached)
[NGAP]   Selected PLMN in the NG Initial UE Message: MCC=208 MNC=95
[NGAP]   UE 1: Selected AMF 'OAI-AMF' (assoc_id 335)
[NR_RRC]   UE 1 Logical Channel DL-DCCH, Generate SecurityModeCommand (bytes 3)
[NR_RRC]   [UL] (cellID 1, UE ID 1 RNTI 0388) Received Security Mode Complete
[NR_RRC]   UE 1: Logical Channel DL-DCCH, Generate NR UECapabilityEnquiry (bytes 8, xid 1)
[NR_RRC]   [UL] (cellID 1, UE ID 1 RNTI 0388) Received UE capabilities
[NR_RRC]   Send message to ngap: NGAP_UE_CAPABILITIES_IND
[NR_RRC]   Send message to sctp: NGAP_InitialContextSetupResponse
[NGAP]   PDUSESSIONSetup initiating message
[NR_RRC]   UE 1: received PDU Session Resource Setup Request
[NR_RRC]   Added QoS flow with qfi=6, total number of QoS flows = 1
[NR_RRC]   Added PDU Session 10, (total nb of sessions = 1)
[NR_RRC]   Bearer Context Setup: PDU Session ID=10, incoming TEID=0x0000006f, Addr=10.244.0.32
[NR_RRC]   [DL] (cellID 1, UE ID 1 RNTI 0388) Generate RRCReconfiguration (bytes 315, xid 3)
[F1AP]   CU Task Received F1AP_DL_RRC_MESSAGE for instance 0
[F1AP]   CU send DL_RRC_MESSAGE_TRANSFER
[F1AP]   CU_handle_UL_RRC_MESSAGE_TRANSFER
[F1AP]   UL RRC MESSAGE for SRB 1 in DCCH
[NR_RRC]   [UL] (cellID 1, UE ID 1 RNTI 0388) Received RRCReconfigurationComplete
[NR_RRC]   PDU Session Setup: ID=10, outgoing TEID=0x47f7480e, Addr=10.138.77.140
[NR_RRC]   NGAP_PDUSESSION_SETUP_RESP: sending the message
"""


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_missing_rach_warns_registration_and_pdu_but_does_not_block() -> None:
    text = """
[MAC] PRACH placing PRACH
[NR_RRC] some unrelated rrc noise
"""
    result = check_scenario_relevance_text(text, log_filename="ue_runtime.log")
    _assert(result.warned, result.to_dict())
    _assert(not result.blocked, result.to_dict())
    _assert(result.passed, result.to_dict())
    _assert(_RACH_FAIL_MESSAGE in result.messages, result.messages)
    _assert(_BOTH_REG_PDU_FAIL_MESSAGE in result.messages, result.messages)
    _assert(_REGISTRATION_FAIL_MESSAGE not in result.messages, result.messages)
    _assert(_PDU_SESSION_FAIL_MESSAGE not in result.messages, result.messages)
    print("OK missing_rach_advisory_registration_and_pdu")


def test_registration_missing_message() -> None:
    # RACH present — no RegistrationRequest and no later security/ICS evidence.
    text = """
[NR_RRC]   Decoding CCCH: RNTI 0388, payload_size 6
[NR_RRC]   Create UE context: CU UE ID 1
[RRC]   activate SRB 1 of UE 1
[NR_RRC]   Send RRC Setup
[NR_RRC]   Received RRCSetupComplete (RRC_CONNECTED reached)
"""
    result = check_scenario_relevance_text(
        text,
        log_filename="callflow.log",
        reported_scenario="registration",
    )
    _assert(result.warned and not result.blocked, result.to_dict())
    _assert(_REGISTRATION_FAIL_MESSAGE in result.messages, result.messages)
    _assert(_RACH_FAIL_MESSAGE not in result.messages, result.messages)
    print("OK registration_missing_message")


def test_rrc_setup_complete_implies_rach() -> None:
    text = """
[NR_RRC] Received RRCSetupComplete (RRC_CONNECTED reached)
[NGAP] Selected AMF
[NAS] Registration Request
[NR_RRC] Generate SecurityModeCommand
[NR_RRC] Received Security Mode Complete
"""
    result = check_scenario_relevance_text(
        text,
        log_filename="partial_rach.log",
        reported_scenario="registration",
    )
    rach = next(c for c in result.checks if c.get("scenario_id") == "rach_setup")
    _assert(rach.get("passed"), rach)
    _assert(_RACH_FAIL_MESSAGE not in result.messages, result.messages)
    print("OK rrc_setup_complete_implies_rach")


def test_security_mode_implies_registration_request() -> None:
    text = """
[NR_RRC] Decoding CCCH
[NR_RRC] Create UE context
[RRC] activate SRB 1
[NR_RRC] Send RRC Setup
[NR_RRC] Received RRCSetupComplete
[NGAP] Selected AMF
[NR_RRC] Generate SecurityModeCommand
[NR_RRC] Received Security Mode Complete
"""
    result = check_scenario_relevance_text(
        text,
        log_filename="no_reg_req.log",
        reported_scenario="attach",
    )
    _assert(_REGISTRATION_FAIL_MESSAGE not in result.messages, result.to_dict())
    reg = next(c for c in result.checks if c.get("scenario_id") == "registration")
    _assert(reg.get("passed"), reg)
    print("OK security_mode_implies_registration_request")


def test_ics_response_waives_missing_security_mode() -> None:
    """ICS Response without SMC/SMC Complete must not fail Registration."""
    text = """
[NR_RRC]   Decoding CCCH: RNTI 0388, payload_size 6
[NR_RRC]   Create UE context: CU UE ID 1
[RRC]   activate SRB 1 of UE 1
[NR_RRC]   Send RRC Setup
[NR_RRC]   Received RRCSetupComplete (RRC_CONNECTED reached)
[NGAP]   Selected PLMN in the NG Initial UE Message: MCC=208 MNC=95
[NGAP]   Selected AMF 'OAI-AMF'
[NR_RRC]   Generate NR UECapabilityEnquiry
[NR_RRC]   Received UE capabilities
[NR_RRC]   Send message to ngap: NGAP_UE_CAPABILITIES_IND
[NR_RRC]   Send message to sctp: NGAP_InitialContextSetupResponse
"""
    result = check_scenario_relevance_text(
        text,
        log_filename="callflow.log",
        reported_scenario="registration",
    )
    _assert(_REGISTRATION_FAIL_MESSAGE not in result.messages, result.to_dict())
    reg = next(c for c in result.checks if c.get("scenario_id") == "registration")
    _assert(reg.get("passed"), reg)
    waived = (result.evidence or {}).get("registration_waived") or []
    _assert("SecurityModeCommand" in waived or "SecurityModeComplete" in waived, waived)
    print("OK ics_response_waives_missing_security_mode")


def test_ics_request_waives_missing_security_mode() -> None:
    text = """
[NR_RRC] Decoding CCCH
[NR_RRC] Create UE context
[RRC] activate SRB 1
[NR_RRC] Send RRC Setup
[NGAP] NG Initial UE Message
[NGAP] Selected AMF
[NGAP] InitialContextSetupRequest
"""
    result = check_scenario_relevance_text(
        text,
        log_filename="cu_partial.log",
        reported_scenario="attach",
    )
    _assert(_REGISTRATION_FAIL_MESSAGE not in result.messages, result.to_dict())
    print("OK ics_request_waives_missing_security_mode")


def test_pdu_missing_message() -> None:
    text = """
[NR_RRC]   Decoding CCCH: RNTI 0388, payload_size 6
[NR_RRC]   Create UE context: CU UE ID 1
[RRC]   activate SRB 1 of UE 1
[NR_RRC]   Send RRC Setup
[NR_RRC]   Received RRCSetupComplete (RRC_CONNECTED reached)
[NGAP]   Selected PLMN in the NG Initial UE Message: MCC=208 MNC=95
[NGAP]   Selected AMF 'OAI-AMF'
[NR_RRC]   Generate SecurityModeCommand
[NR_RRC]   Received Security Mode Complete
[NR_RRC]   Generate NR UECapabilityEnquiry
[NR_RRC]   Received UE capabilities
[NR_RRC]   Send message to ngap: NGAP_UE_CAPABILITIES_IND
[NR_RRC]   Send message to sctp: NGAP_InitialContextSetupResponse
"""
    result = check_scenario_relevance_text(
        text,
        log_filename="callflow.log",
        reported_scenario="registration pdu_session",
    )
    _assert(result.warned and not result.blocked, result.to_dict())
    _assert(_PDU_SESSION_FAIL_MESSAGE in result.messages, result.messages)
    _assert(_REGISTRATION_FAIL_MESSAGE not in result.messages, result.messages)
    _assert(
        result.scenario_match_score < 1.0,
        f"PDU missing must reduce scenario match below 100%: {result.scenario_match_score}",
    )
    print(f"OK pdu_missing_message match={result.scenario_match_score:.2f}")


def test_full_cu_registration_and_pdu_passes() -> None:
    result = check_scenario_relevance_text(_FULL_CU_FLOW, log_filename="success_cu_gnb.log")
    _assert(result.passed and not result.warned and not result.blocked, result.to_dict())
    print("OK full_cu_registration_pdu_passes")


def test_build_log_advisory_both_messages() -> None:
    text = "\n".join(
        [
            'Running "cmake"',
            "OPENAIR_DIR=/oai",
            "cmake_targets/build",
            "CMakeFiles/nr-softmodem",
            "Will compile gNB",
            "build have failed",
        ]
    )
    result = check_scenario_relevance_text(text, log_filename="CMake_errror.log")
    _assert(result.warned and not result.blocked and result.passed, result.to_dict())
    _assert(_RACH_FAIL_MESSAGE in result.messages, result.messages)
    _assert(_BOTH_REG_PDU_FAIL_MESSAGE in result.messages, result.messages)
    print("OK build_log_advisory_both_messages")


def test_handover_not_confused_with_sn_release() -> None:
    text = _FULL_CU_FLOW + """
[NR_RRC] Secondary Node Release procedure started
[NR_RRC] SgNB Release Request Acknowledge
"""
    result = check_scenario_relevance_text(text, log_filename="sn_release.log")
    ho = next((c for c in result.checks if c.get("scenario_id") == "handover"), None)
    _assert(ho is None or not ho.get("expected"), result.to_dict())
    print("OK sn_release_not_handover")


def test_real_success_ue_fixture_if_present() -> None:
    path = BACKEND_DIR / "Guardrails/Bug Discovery/success_ue_gnb.log"
    if not path.exists():
        print("SKIP real_success_ue_fixture")
        return
    result = check_scenario_relevance(path)
    _assert(result.passed and not result.blocked, result.to_dict())
    print(f"OK real_success_ue_fixture warned={result.warned}")


def test_real_success_cu_fixture_if_present() -> None:
    path = BACKEND_DIR / "Guardrails/Bug Discovery/success_cu_gnb.log"
    if not path.exists():
        print("SKIP real_success_cu_fixture")
        return
    result = check_scenario_relevance(path)
    _assert(result.passed and not result.blocked, result.to_dict())
    print(f"OK real_success_cu_fixture warned={result.warned} skipped={result.skipped}")


def test_joined_registration_request_matches_spaced_phrase() -> None:
    """RegistrationRequest (no space) should satisfy 'registration request'."""
    text = """
[NR_RRC] Decoding CCCH: RNTI 0388
[NR_RRC] Create UE context: CU UE ID 1
[RRC] activate SRB 1 of UE 1
[NR_RRC] Send RRC Setup
[NR_RRC] Received RRCSetupComplete (RRC_CONNECTED reached)
[NAS] RegistrationRequest
[NGAP] Selected AMF 'OAI-AMF'
[NR_RRC] Generate SecurityModeCommand
[NR_RRC] Received Security Mode Complete
[NR_RRC] Generate NR UECapabilityEnquiry
[NR_RRC] Received UE capabilities
[NR_RRC] Send message to ngap: NGAP_UE_CAPABILITIES_IND
[NR_RRC] Send message to sctp: NGAP_InitialContextSetupResponse
"""
    _assert(_mod._phrase_in_corpus(_mod._normalize_blob(text), "registration request"), "joined form missed")
    result = check_scenario_relevance_text(text, log_filename="ue_attach.log", reported_scenario="attach")
    missing = (result.evidence or {}).get("missing", {}).get("registration") or []
    _assert("RegistrationRequest" not in missing, f"still missing RegistrationRequest: {missing}")
    print("OK joined_registration_request_matches")


def test_all_registration_and_pdu_spaced_phrases_match_joined() -> None:
    """Every spaced Registration/RACH/PDU phrase also matches its joined form."""
    groups = (
        list(_mod._RACH_SETUP_GROUPS)
        + list(_mod._REGISTRATION_CORE_GROUPS)
        + list(_mod._REGISTRATION_CU_EXTRA_GROUPS)
        + list(_mod._PDU_SESSION_GROUPS)
        + list(_mod._PDU_SESSION_CU_EXTRA_GROUPS)
    )
    checked = 0
    for label, phrases in groups:
        for phrase in phrases:
            if not re.search(r"[\s_\-]", phrase):
                continue
            joined = re.sub(r"[\s_\-]+", "", phrase)
            _assert(
                _mod._phrase_in_corpus(joined, phrase),
                f"{label}: '{phrase}' should match corpus '{joined}'",
            )
            checked += 1
    _assert(checked > 0, "expected at least one spaced phrase to check")
    print(f"OK all_registration_pdu_spaced_phrases_match_joined checked={checked}")


if __name__ == "__main__":
    test_missing_rach_warns_registration_and_pdu_but_does_not_block()
    test_registration_missing_message()
    test_rrc_setup_complete_implies_rach()
    test_security_mode_implies_registration_request()
    test_ics_response_waives_missing_security_mode()
    test_ics_request_waives_missing_security_mode()
    test_pdu_missing_message()
    test_full_cu_registration_and_pdu_passes()
    test_build_log_advisory_both_messages()
    test_handover_not_confused_with_sn_release()
    test_joined_registration_request_matches_spaced_phrase()
    test_all_registration_and_pdu_spaced_phrases_match_joined()
    test_real_success_ue_fixture_if_present()
    test_real_success_cu_fixture_if_present()
    print("All scenario relevance tests passed.")
