"""
Scenario relevance for Bug Discovery logs.

Advisory overlay on RCA (never blocks Start RCA):
  - Missing Registration → "Expected registration test events not found..."
  - Missing PDU Session → "Expected PDU Session Setup events not found..."

RACH / RRC setup (commands 1 & 2) counts as part of Registration.
PDU Session uses OAI commands 1–5 (PDUSessionSetup … NGAP_PDUSession_Setup_RESP).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from app.guardrails.config import (
    GUARDRAILS_BD_SCENARIO_RELEVANCE_ENABLED,
    GUARDRAILS_BD_SCENARIO_RELEVANCE_MODE,
    MAX_SCAN_CHARS,
)

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
_BUILD_HINT_RE = re.compile(
    r"Will compile gNB|OPENAIR_DIR|build_oai|cmake_targets|CMakeFiles|"
    r"gmake\[|Running \"cmake|build have failed|compilation of",
    re.IGNORECASE,
)
_RUNTIME_HINT_RE = re.compile(
    r"\[(?:NAS|NR_RRC|RRC|NGAP|MAC|NR_MAC|PHY|NR_PHY|ITTI|F1AP)\]|"
    r"PRACH|RRCSetup|Registration|PDU Session|Handover",
    re.IGNORECASE,
)

_REGISTRATION_FAIL_MESSAGE = "Expected registration test events not found."
_PDU_SESSION_FAIL_MESSAGE = "Expected PDU Session Setup events not found."
_BOTH_REG_PDU_FAIL_MESSAGE = (
    "Expected registration test events & PDU Session events are not found."
)
_RACH_FAIL_MESSAGE = "RACH setup is missing."
_HANDOVER_FAIL_MESSAGE = "Expected Handover / mobility events not found."
# Back-compat alias
_DEFAULT_FAIL_MESSAGE = _REGISTRATION_FAIL_MESSAGE

# ---------------------------------------------------------------------------
# RACH / RRC setup gate — commands 1 & 2 (must both be present)
# ---------------------------------------------------------------------------
_RACH_SETUP_GROUPS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "RRCSetupRequest",
        (
            # CU / gNB
            "decoding ccch",
            "create ue context",
            "rrcsetuprequest",
            "rrc setup request",
            "rrcconnectionrequest",
            "rrc connection request",
            "requested rrcconnectionrequest",
            # UE side / RACH initialization
            "ra-msg3 transmitted",
            "msg3 transmitted",
            "initiating ra procedure",
            "generating ra-msg2",
        ),
    ),
    (
        "RRCSetup",
        (
            # CU / gNB
            "send rrc setup",
            "activate srb 1",
            "activate srb1",
            "dl_rrc_message_transfer",
            "cu send dl_rrc_message_transfer",
            # UE side / MSG4 completion
            "received nr_rrcsetup",
            "added srb 1",
            "added srb1",
            "generate msg4",
            "received ack of msg4",
        ),
    ),
)

# ---------------------------------------------------------------------------
# Registration follow-on (after RACH is up) — commands 3–11
# InitialContextSetupRequest (10) is optional: many OAI builds never print it.
# CU-only NGAP markers (9, 11) are required only on CU-side captures.
# ---------------------------------------------------------------------------
_REGISTRATION_CORE_GROUPS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "RRCSetupComplete",
        (
            "received rrcsetupcomplete",
            "rrcsetupcomplete",
            "rrc_connected reached",
            "(rrc_connected reached)",
        ),
    ),
    (
        "RegistrationRequest",
        (
            # Explicit NAS (UE / some builds)
            "registration request",
            "generate initial nas message: registration request",
            "nas registration request",
            # OAI CU often only shows NG Initial UE Message
            "ng initial ue message",
            "initial ue message",
            "selected amf",
            "selected plmn in the ng initial ue message",
        ),
    ),
    (
        "SecurityModeCommand",
        (
            "securitymodecommand",
            "security mode command",
            "generate securitymodecommand",
            "generate security mode command",
            "received securitymodecommand",
            "received security mode command",
        ),
    ),
    (
        "SecurityModeComplete",
        (
            "security mode complete",
            "securitymodecomplete",
            "encoding securitymodecomplete",
            "received security mode complete",
        ),
    ),
    (
        "UECapabilityEnquiry",
        (
            "uecapabilityenquiry",
            "generate nr uecapabilityenquiry",
            "processing uecapabilityenquiry",
        ),
    ),
    (
        "UECapabilityInformation",
        (
            "received ue capabilities",
            "uecapabilityinformation",
            "received ue capability",
        ),
    ),
)

_REGISTRATION_CU_EXTRA_GROUPS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "NGAP_UE_CAPABILITIES_IND",
        (
            "ngap_ue_capabilities_ind",
            "send message to ngap: ngap_ue_capabilities_ind",
        ),
    ),
    (
        # Often unlogged on some captures; presence of Response implies Request.
        "InitialContextSetupRequest",
        (
            "initialcontextsetuprequest",
            "initial context setup request",
            "ngap_initialcontextsetuprequest",
            "send message to ngap: ngap_initialcontextsetuprequest",
        ),
    ),
    (
        "NGAP_InitialContextSetupResponse",
        (
            "ngap_initialcontextsetupresponse",
            "initialcontextsetupresponse",
            "initial context setup response",
            "send message to sctp: ngap_initialcontextsetupresponse",
        ),
    ),
)

# Soft / mid-procedure steps that OAI logs frequently omit even when the
# later procedure succeeded. Presence of a stronger later step waives these.
_REGISTRATION_SOFT_STEPS = frozenset(
    {
        "RRCSetupRequest",
        "RRCSetup",
        "RRCSetupComplete",
        # RegistrationRequest is hard unless a later mid/end step implies it.
        "SecurityModeCommand",
        "SecurityModeComplete",
        "UECapabilityEnquiry",
        "UECapabilityInformation",
        "NGAP_UE_CAPABILITIES_IND",
        "InitialContextSetupRequest",
        "NGAP_InitialContextSetupResponse",
    }
)

_RACH_STEP_LABELS = frozenset({"RRCSetupRequest", "RRCSetup"})

# If a later step is present, treat earlier steps as satisfied (often unlogged).
_REGISTRATION_STEP_IMPLIES: Dict[str, Tuple[str, ...]] = {
    # RACH is complete once UE is in RRC Connected.
    "RRCSetupComplete": ("RRCSetupRequest", "RRCSetup"),
    # Security mode proves Registration Request was already exchanged.
    "SecurityModeCommand": (
        "RRCSetupRequest",
        "RRCSetup",
        "RRCSetupComplete",
        "RegistrationRequest",
    ),
    "SecurityModeComplete": (
        "RRCSetupRequest",
        "RRCSetup",
        "RRCSetupComplete",
        "RegistrationRequest",
        "SecurityModeCommand",
    ),
    "UECapabilityEnquiry": (
        "RRCSetupRequest",
        "RRCSetup",
        "RRCSetupComplete",
        "RegistrationRequest",
        "SecurityModeCommand",
        "SecurityModeComplete",
    ),
    "UECapabilityInformation": (
        "RRCSetupRequest",
        "RRCSetup",
        "RRCSetupComplete",
        "RegistrationRequest",
        "SecurityModeCommand",
        "SecurityModeComplete",
        "UECapabilityEnquiry",
    ),
    "NGAP_UE_CAPABILITIES_IND": (
        "RRCSetupRequest",
        "RRCSetup",
        "RRCSetupComplete",
        "RegistrationRequest",
        "SecurityModeCommand",
        "SecurityModeComplete",
        "UECapabilityEnquiry",
        "UECapabilityInformation",
    ),
    "InitialContextSetupRequest": (
        "RRCSetupRequest",
        "RRCSetup",
        "RRCSetupComplete",
        "RegistrationRequest",
        "SecurityModeCommand",
        "SecurityModeComplete",
        "UECapabilityEnquiry",
        "UECapabilityInformation",
        "NGAP_UE_CAPABILITIES_IND",
    ),
    "NGAP_InitialContextSetupResponse": (
        "RRCSetupRequest",
        "RRCSetup",
        "RRCSetupComplete",
        "RegistrationRequest",
        "SecurityModeCommand",
        "SecurityModeComplete",
        "UECapabilityEnquiry",
        "UECapabilityInformation",
        "NGAP_UE_CAPABILITIES_IND",
        "InitialContextSetupRequest",
    ),
    "RegistrationRequest": (
        "RRCSetupRequest",
        "RRCSetup",
        "RRCSetupComplete",
    ),
    # PDU after attach also proves registration / RACH mid-steps occurred.
    "PDUSessionSetup": (
        "RRCSetupRequest",
        "RRCSetup",
        "RRCSetupComplete",
        "RegistrationRequest",
        "SecurityModeCommand",
        "SecurityModeComplete",
        "UECapabilityEnquiry",
        "UECapabilityInformation",
        "NGAP_UE_CAPABILITIES_IND",
        "InitialContextSetupRequest",
        "NGAP_InitialContextSetupResponse",
    ),
    "RRCReconfiguration": (
        "RRCSetupRequest",
        "RRCSetup",
        "RRCSetupComplete",
        "RegistrationRequest",
        "SecurityModeCommand",
        "SecurityModeComplete",
        "PDUSessionSetup",
    ),
    "RRCReconfigurationComplete": (
        "RRCSetupRequest",
        "RRCSetup",
        "RRCSetupComplete",
        "RegistrationRequest",
        "SecurityModeCommand",
        "SecurityModeComplete",
        "PDUSessionSetup",
        "RRCReconfiguration",
    ),
}

# ---------------------------------------------------------------------------
# PDU Session procedure (after RACH is up) — commands 1–5 (CU OAI phrases)
# UE softmodem builds often only show NAS Accept + RRCReconfiguration*; those
# remain accepted as alternate evidence for the same steps.
# ---------------------------------------------------------------------------
_PDU_SESSION_GROUPS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "PDUSessionSetup",
        (
            # CU / gNB — AMF initiates PDU Session Setup
            "pdusessionsetup initiating message",
            "pdusessionsetup",
            "received pdu session resource setup request",
            "pdu session resource setup request",
            "added qos flow",
            "added pdu session",
            "bearer context setup",
            # UE / NAS
            "pdu session establishment request",
            "pdu session establishment accept",
            "received pdu session establishment accept",
            "pdu session establishment",
        ),
    ),
    (
        "RRCReconfiguration",
        (
            # CU prepares RRC Reconfiguration carrying PDU Session config
            "generate rrcreconfiguration",
            "rrcreconfiguration (bytes",
            # UE receives / applies radio bearer config from Reconfiguration
            "rrcreconfiguration includes radio bearer",
            "rrcreconfiguration includes measurement",
            "rrcreconfiguration includes",
        ),
    ),
    (
        "RRCReconfigurationComplete",
        (
            "received rrcreconfigurationcomplete",
            "rrcreconfigurationcomplete encoded",
            "generating rrcreconfigurationcomplete",
            "rrcreconfigurationcomplete",
        ),
    ),
)

# CU final response toward AMF (often missing on UE-only logs)
_PDU_SESSION_CU_EXTRA_GROUPS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "PDU Session Setup Response",
        (
            "pdu session setup:",
            "outgoing teid",
            "pdu session setup: id=",
        ),
    ),
    (
        "NGAP_PDUSession_Setup_RESP",
        (
            "ngap_pdusession_setup_resp",
            "ngap_pdusession_setup_resp: sending the message",
            "ngap_pdusession_setup_resp:sending the message",
        ),
    ),
)

_HANDOVER_GROUPS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "Handover / mobility event",
        (
            "measurement report",
            "handover required",
            "handover request",
            "handover request ack",
            "handover request acknowledge",
            "handover command",
            "handover complete",
            "path switch",
            "xn handover",
            "n2 handover",
            "ng handover",
        ),
    ),
)

_SCENARIO_SPECS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "registration",
        "label": "Registration",
        "hint_tokens": (
            "registration",
            "register",
            "attach",
            "rach",
            "rrc_connection",
            "rrc connection",
        ),
        "fail_label": "Registration logs",
    },
    {
        "id": "pdu_session",
        "label": "PDU Session",
        "hint_tokens": (
            "pdu session",
            "pdu_session",
            "pdusession",
            "session establishment",
            "qos flow",
            "smf",
            "upf",
        ),
        "fail_label": "PDU Session Setup events",
    },
    {
        "id": "handover",
        "label": "Handover",
        "hint_tokens": (
            "handover",
            "hand-over",
            "hand over",
            "mobility",
            "path switch",
            "xn handover",
            "n2 handover",
            "inter-gnb",
            "inter-du",
            "inter-cu",
        ),
        "exclude_hint_tokens": (
            "secondary node release",
            "sgnb release",
            "sn release",
        ),
        "fail_label": "Handover / mobility events",
    },
)


@dataclass
class ScenarioCheckDetail:
    scenario_id: str
    label: str
    expected: bool
    passed: bool
    missing: List[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "label": self.label,
            "expected": self.expected,
            "passed": self.passed,
            "missing": self.missing,
            "message": self.message,
        }


@dataclass
class ScenarioRelevanceResult:
    passed: bool
    blocked: bool
    warned: bool
    skipped: bool = False
    messages: List[str] = field(default_factory=list)
    expected_scenarios: List[str] = field(default_factory=list)
    checks: List[Dict[str, Any]] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    # Fraction of attach/registration checklist events present (0–1).
    scenario_match_score: float = 0.0
    target_scenario: str = "attach"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "warned": self.warned,
            "skipped": self.skipped,
            "messages": self.messages,
            "expected_scenarios": self.expected_scenarios,
            "checks": self.checks,
            "evidence": self.evidence,
            "scenario_match_score": round(self.scenario_match_score, 4),
            "target_scenario": self.target_scenario,
            "mode": GUARDRAILS_BD_SCENARIO_RELEVANCE_MODE,
        }


def _read_sample(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if len(raw) <= MAX_SCAN_CHARS:
        return raw
    window = raw[:MAX_SCAN_CHARS]
    snap = window.rfind("\n")
    if snap > MAX_SCAN_CHARS // 2:
        return window[: snap + 1]
    return window


def _normalize_blob(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text or "").lower()


def _phrase_variants(phrase: str) -> Tuple[str, ...]:
    """Return spaced and joined forms of a phrase (case already lower).

    Applies to every Registration / PDU / RACH command phrase:
      "registration request" → also "registrationrequest"
      "pdu session establishment accept" → also "pdusessionestablishmentaccept"
      "rrc-setup-request" / "rrc_setup_request" → also "rrcsetuprequest"
    """
    raw = (phrase or "").strip().lower()
    if not raw:
        return ()
    variants = {raw}
    joined = re.sub(r"[\s_\-]+", "", raw)
    if joined:
        variants.add(joined)
    return tuple(variants)


def _expand_command_groups(
    groups: Sequence[Tuple[str, Tuple[str, ...]]],
) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    """Materialize spaced + joined phrase aliases for each command group."""
    expanded: List[Tuple[str, Tuple[str, ...]]] = []
    for label, phrases in groups:
        ordered: List[str] = []
        seen: Set[str] = set()
        for phrase in phrases:
            for variant in _phrase_variants(phrase):
                if variant not in seen:
                    seen.add(variant)
                    ordered.append(variant)
        expanded.append((label, tuple(ordered)))
    return tuple(expanded)


def _phrase_in_corpus(corpus: str, phrase: str) -> bool:
    return any(variant in corpus for variant in _phrase_variants(phrase))


def _group_satisfied(corpus: str, phrases: Sequence[str]) -> bool:
    """True if any phrase (or its spaced/joined form) appears in the log."""
    return any(_phrase_in_corpus(corpus, phrase) for phrase in phrases)


def _missing_groups(
    corpus: str,
    groups: Sequence[Tuple[str, Tuple[str, ...]]],
) -> List[str]:
    return [label for label, phrases in groups if not _group_satisfied(corpus, phrases)]


def _present_group_labels(
    corpus: str,
    groups: Sequence[Tuple[str, Tuple[str, ...]]],
) -> Set[str]:
    return {label for label, phrases in groups if _group_satisfied(corpus, phrases)}


def _waive_implied_registration_missing(
    missing: Sequence[str],
    present: Set[str],
) -> Tuple[List[str], List[str]]:
    """Drop earlier steps implied by later captured commands.

    Returns (remaining_missing, waived_labels).
    """
    waived: Set[str] = set()
    for present_label, implied in _REGISTRATION_STEP_IMPLIES.items():
        if present_label not in present:
            continue
        for earlier in implied:
            waived.add(earlier)

    # Strong late markers: waive the full soft / often-unlogged set.
    strong_late = present & {
        "SecurityModeCommand",
        "SecurityModeComplete",
        "InitialContextSetupRequest",
        "NGAP_InitialContextSetupResponse",
        "PDUSessionSetup",
        "NGAP_UE_CAPABILITIES_IND",
        "UECapabilityInformation",
        "RRCReconfiguration",
        "RRCReconfigurationComplete",
    }
    if strong_late:
        waived.update(_REGISTRATION_SOFT_STEPS)
        # Later security/context/PDU evidence also implies Registration Request.
        waived.add("RegistrationRequest")

    # RRCSetupComplete alone proves RACH, not full registration.
    if "RRCSetupComplete" in present:
        waived.update(_RACH_STEP_LABELS)

    remaining = [label for label in missing if label not in waived]
    return remaining, sorted(waived & set(missing))


def _compose_scenario_messages(
    *,
    rach_failed: bool,
    registration_failed: bool,
    pdu_failed: bool,
    handover_failed: bool = False,
) -> List[str]:
    """Build user-facing messages: combined when both missing, else only missing ones."""
    messages: List[str] = []
    if rach_failed:
        messages.append(_RACH_FAIL_MESSAGE)
    if registration_failed and pdu_failed:
        messages.append(_BOTH_REG_PDU_FAIL_MESSAGE)
    elif registration_failed:
        messages.append(_REGISTRATION_FAIL_MESSAGE)
    elif pdu_failed:
        messages.append(_PDU_SESSION_FAIL_MESSAGE)
    if handover_failed:
        messages.append(_HANDOVER_FAIL_MESSAGE)
    return messages


def _registration_groups_for_capture(corpus: str) -> List[Tuple[str, Tuple[str, ...]]]:
    groups = list(_REGISTRATION_CORE_GROUPS)
    if _is_cu_side_capture(corpus):
        groups.extend(_REGISTRATION_CU_EXTRA_GROUPS)
    return groups


# Ensure Registration + PDU (+ RACH gate) command phrases match spaced AND joined forms.
_RACH_SETUP_GROUPS = _expand_command_groups(_RACH_SETUP_GROUPS)
_REGISTRATION_CORE_GROUPS = _expand_command_groups(_REGISTRATION_CORE_GROUPS)
_REGISTRATION_CU_EXTRA_GROUPS = _expand_command_groups(_REGISTRATION_CU_EXTRA_GROUPS)
_PDU_SESSION_GROUPS = _expand_command_groups(_PDU_SESSION_GROUPS)
_PDU_SESSION_CU_EXTRA_GROUPS = _expand_command_groups(_PDU_SESSION_CU_EXTRA_GROUPS)


def _is_build_log(text: str) -> bool:
    build_hits = len(_BUILD_HINT_RE.findall(text[:8000]))
    runtime_hits = len(_RUNTIME_HINT_RE.findall(text[:8000]))
    return build_hits >= 3 and runtime_hits < 2


def _token_in_text(token: str, text: str) -> bool:
    """Substring match with word-ish boundaries so 'rach' does not match inside 'prach'."""
    token = (token or "").strip().lower()
    if not token:
        return False
    if " " in token or "_" in token or "-" in token:
        return _phrase_in_corpus(text, token)
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", text))


def _is_du_only_log(corpus: str, filename: str = "") -> bool:
    name = (filename or "").lower()
    if re.search(r"(^|[_\-])du([_\-]|$)|_du\.|du_gnb|ngran_du", name):
        return True
    has_f1 = "f1ap" in corpus or "starting f1ap" in corpus
    has_ngap = "ngap" in corpus or "ngsetup" in corpus
    has_nas_reg = _phrase_in_corpus(corpus, "registration request") or _phrase_in_corpus(
        corpus, "registration accept"
    )
    has_frame_slot = "frame.slot" in corpus
    return has_f1 and not has_ngap and not has_nas_reg and has_frame_slot


def _is_stack_bringup_only(corpus: str, filename: str = "") -> bool:
    """CU/DU stack start logs without UE call-flow procedures."""
    name = (filename or "").lower()
    has_real_ue = bool(
        re.search(
            r"registration request|registration accept|"
            r"pdu session establishment|pdu session resource setup|"
            r"rrc setup request|rrcsetuprequest|received rrcsetupcomplete|"
            r"send rrc setup|decoding ccch|random access procedure|prach \[ue|"
            r"ra-msg3 transmitted|received nr_rrcsetup|initiating ra procedure|"
            r"generating ra-msg2|generate msg4|received ack of msg4",
            corpus,
            re.I,
        )
    )
    if re.search(r"(^|[_\-])cu([_\-]|$)|cu_gnb|ngran_cu", name) and "ue" not in name:
        return not has_real_ue
    if _is_du_only_log(corpus, name):
        return True
    has_stack = bool(
        re.search(r"ngsetuprequest|ngsetupresponse|starting f1ap|associated amf", corpus, re.I)
    )
    return has_stack and not has_real_ue


def _is_cu_side_capture(corpus: str) -> bool:
    """True when the log looks like a CU/gNB capture (not UE softmodem)."""
    return bool(
        re.search(
            r"decoding ccch|send rrc setup|dl_rrc_message_transfer|"
            r"ng initial ue message|selected amf|ngap_initialcontextsetupresponse|"
            r"ngap_ue_capabilities_ind",
            corpus,
            re.I,
        )
    )


_UE_CALLFLOW_HINT_RE = re.compile(
    r"PRACH|random access|RRC Setup|RRCSetup|Registration|PDU Session|\[NAS\]|"
    r"Decoding CCCH|RA-Msg3|Initiating RA procedure|Generating RA-Msg2|Generate Msg4|Received Ack of Msg4",
    re.IGNORECASE,
)


def _normalize_reported_scenario(reported_scenario: Optional[str]) -> str:
    """Normalize Bug Discovery scenario labels (attach → registration family)."""
    reported = " ".join(str(reported_scenario or "").lower().replace("-", " ").replace("_", " ").split())
    if reported in ("attach", "ue attach", "single attach", "5g attach"):
        return "attach"
    return reported


def _attach_registration_groups(corpus: str) -> List[Tuple[str, Tuple[str, ...]]]:
    groups: List[Tuple[str, Tuple[str, ...]]] = list(_RACH_SETUP_GROUPS) + list(_REGISTRATION_CORE_GROUPS)
    if _is_cu_side_capture(corpus):
        groups.extend(_REGISTRATION_CU_EXTRA_GROUPS)
    return groups


def _attach_match_score(corpus: str) -> Tuple[float, Dict[str, Any]]:
    """Fraction of attach/registration checklist groups found (with soft-step waivers)."""
    groups = _attach_registration_groups(corpus)
    if not groups:
        return 1.0, {"found": 0, "total": 0, "missing": []}
    present = _present_group_labels(corpus, groups)
    present |= _present_group_labels(corpus, _PDU_SESSION_GROUPS)
    present |= _present_group_labels(corpus, _PDU_SESSION_CU_EXTRA_GROUPS)
    raw_missing = _missing_groups(corpus, groups)
    missing, waived = _waive_implied_registration_missing(raw_missing, present)
    found = len(groups) - len(missing)
    score = found / len(groups)
    return score, {
        "found": found,
        "total": len(groups),
        "missing": missing,
        "waived": waived,
        "groups": [label for label, _ in groups],
    }


def _expected_procedure_groups(
    corpus: str,
    expected: Set[str],
) -> List[Tuple[str, Tuple[str, ...]]]:
    """Checklist groups for every procedure the guardrail expects on this log."""
    groups: List[Tuple[str, Tuple[str, ...]]] = []
    if expected & {"registration", "pdu_session"}:
        groups.extend(_RACH_SETUP_GROUPS)
    if "registration" in expected:
        groups.extend(_registration_groups_for_capture(corpus))
    if "pdu_session" in expected:
        groups.extend(_PDU_SESSION_GROUPS)
        if _is_cu_side_capture(corpus):
            groups.extend(_PDU_SESSION_CU_EXTRA_GROUPS)
    if "handover" in expected:
        groups.extend(_HANDOVER_GROUPS)
    # De-dupe by label while preserving order.
    out: List[Tuple[str, Tuple[str, ...]]] = []
    seen: Set[str] = set()
    for label, phrases in groups:
        if label in seen:
            continue
        seen.add(label)
        out.append((label, phrases))
    return out


def _scenario_match_score(
    corpus: str,
    expected: Set[str],
) -> Tuple[float, Dict[str, Any]]:
    """Fraction of *expected* Attach/Registration/PDU/Handover groups present.

    Unlike `_attach_match_score` (registration-only), this score drops when PDU
    or other expected procedures are missing — so the UI never shows 100% with
    "Expected PDU Session Setup events not found."
    """
    groups = _expected_procedure_groups(corpus, expected)
    if not groups:
        attach_score, attach_meta = _attach_match_score(corpus)
        return attach_score, {**attach_meta, "scope": "attach_fallback"}

    present = _present_group_labels(corpus, groups)
    # Later PDU / handover markers can still waive soft registration steps.
    present |= _present_group_labels(corpus, _PDU_SESSION_GROUPS)
    present |= _present_group_labels(corpus, _PDU_SESSION_CU_EXTRA_GROUPS)
    raw_missing = _missing_groups(corpus, groups)
    missing, waived = _waive_implied_registration_missing(raw_missing, present)
    found = len(groups) - len(missing)
    score = found / len(groups) if groups else 1.0
    return score, {
        "found": found,
        "total": len(groups),
        "missing": missing,
        "waived": waived,
        "groups": [label for label, _ in groups],
        "expected_scenarios": sorted(expected),
        "scope": "expected_procedures",
    }


def _infer_scenarios(
    *,
    filename: str,
    corpus: str,
    reported_scenario: Optional[str] = None,
    force_callflow_for_build: bool = False,
) -> Set[str]:
    expected: Set[str] = set()
    name = (filename or "").lower()
    reported = _normalize_reported_scenario(reported_scenario)

    # Explicit attach/registration request always targets registration checklist.
    if reported in ("attach", "registration") or "attach" in reported.split():
        expected.add("registration")
        # Keep other scenarios if also hinted in reported text below.

    if _is_stack_bringup_only(corpus, name) and not reported and not force_callflow_for_build:
        return set()

    for spec in _SCENARIO_SPECS:
        sid = spec["id"]
        tokens = spec["hint_tokens"]
        excludes = spec.get("exclude_hint_tokens") or ()

        if reported:
            if any(_token_in_text(tok, reported) or tok in reported for tok in tokens) or sid.replace("_", " ") in reported:
                if not any(ex in reported for ex in excludes):
                    expected.add(sid)
                continue

        hinted = any(_token_in_text(tok, name) for tok in tokens) or any(
            _token_in_text(tok, corpus) for tok in tokens
        )
        if hinted and not any(ex in corpus for ex in excludes):
            if sid == "handover" and any(ex in name or ex in corpus for ex in excludes):
                if not any(
                    _token_in_text(tok, name) or _token_in_text(tok, corpus)
                    for tok in ("handover", "path switch", "measurement report", "xn", "n2")
                ):
                    continue
            expected.add(sid)

    # Build/CMake error logs have no signaling — still expect Registration + PDU
    # so the RACH gate can surface the scenario-relevance message on the UI.
    if force_callflow_for_build and not expected:
        expected.update({"registration", "pdu_session"})
        return expected

    if not expected and _RUNTIME_HINT_RE.search(corpus):
        if (
            not _is_build_log(corpus)
            and not _is_stack_bringup_only(corpus, name)
            and (_UE_CALLFLOW_HINT_RE.search(corpus) or "ue" in name)
        ):
            expected.update({"registration", "pdu_session"})

    return expected


def _mode_flags(has_issue: bool) -> Tuple[bool, bool, bool]:
    """Return (passed, blocked, warned) from GUARDRAILS_BD_SCENARIO_RELEVANCE_MODE.

    Modes (same pattern as other Bug Discovery guardrails):
      - advisory: warn in UI, do not block Start RCA
      - balanced / strict: warn + block Start RCA until scenario events are present
    """
    if not has_issue:
        return True, False, False
    mode = str(GUARDRAILS_BD_SCENARIO_RELEVANCE_MODE or "advisory").strip().lower()
    blocked = mode in ("balanced", "strict")
    warned = mode == "advisory" or not blocked
    return (not blocked), blocked, warned


def check_scenario_relevance_text(
    text: str,
    *,
    log_filename: Optional[str] = None,
    reported_scenario: Optional[str] = None,
) -> ScenarioRelevanceResult:
    if not GUARDRAILS_BD_SCENARIO_RELEVANCE_ENABLED:
        return ScenarioRelevanceResult(
            passed=True,
            blocked=False,
            warned=False,
            skipped=True,
            checks=[{"check": "scenario_relevance", "skipped": True}],
            scenario_match_score=1.0,
            target_scenario="attach",
        )

    corpus = _normalize_blob(text)
    attach_score, attach_meta = _attach_match_score(corpus)

    # Build / CMake error logs still go through scenario relevance: they do not
    # contain RACH/Registration/PDU signaling, so the UI should surface that.

    expected = _infer_scenarios(
        filename=log_filename or "",
        corpus=corpus,
        reported_scenario=reported_scenario,
        force_callflow_for_build=_is_build_log(text),
    )
    if not expected:
        return ScenarioRelevanceResult(
            passed=True,
            blocked=False,
            warned=False,
            skipped=True,
            evidence={"reason": "no_scenario_inferred", "attach_match": attach_meta},
            checks=[{"check": "scenario_relevance", "skipped": True, "reason": "no_scenario"}],
            scenario_match_score=attach_score,
            target_scenario="attach",
        )

    match_score, match_meta = _scenario_match_score(corpus, expected)
    details: List[ScenarioCheckDetail] = []
    messages: List[str] = []
    evidence: Dict[str, Any] = {
        "attach_match": attach_meta,
        "scenario_match": match_meta,
    }
    failed = False
    rach_failed = False
    registration_failed = False
    pdu_failed = False
    handover_failed = False

    reg_groups = _registration_groups_for_capture(corpus) if "registration" in expected else []
    pdu_groups: List[Tuple[str, Tuple[str, ...]]] = []
    if "pdu_session" in expected:
        pdu_groups = list(_PDU_SESSION_GROUPS)
        if _is_cu_side_capture(corpus):
            pdu_groups.extend(_PDU_SESSION_CU_EXTRA_GROUPS)

    present: Set[str] = set()
    if expected & {"registration", "pdu_session"}:
        present |= _present_group_labels(corpus, list(_RACH_SETUP_GROUPS) + reg_groups)
        present |= _present_group_labels(corpus, pdu_groups or list(_PDU_SESSION_GROUPS))

    # --- RACH gate (waived when RRCSetupComplete / later evidence exists) ---
    rach_missing: List[str] = []
    if expected & {"registration", "pdu_session"}:
        rach_raw = _missing_groups(corpus, _RACH_SETUP_GROUPS)
        rach_missing, rach_waived = _waive_implied_registration_missing(rach_raw, present)
        rach_missing = [m for m in rach_missing if m in _RACH_STEP_LABELS]
        rach_ok = not rach_missing
        rach_failed = not rach_ok
        evidence["rach_setup"] = {
            "passed": rach_ok,
            "missing": rach_missing,
            "waived": rach_waived,
            "inferred": bool(rach_waived) and rach_ok,
        }
        details.append(
            ScenarioCheckDetail(
                scenario_id="rach_setup",
                label="RACH / RRC Setup",
                expected=True,
                passed=rach_ok,
                missing=rach_missing,
                message="" if rach_ok else _RACH_FAIL_MESSAGE,
            )
        )

    # --- Registration ---
    if "registration" in expected:
        raw_reg_missing: List[str] = []
        for label in list(rach_missing) + _missing_groups(corpus, reg_groups):
            if label not in raw_reg_missing:
                raw_reg_missing.append(label)
        reg_missing, waived = _waive_implied_registration_missing(raw_reg_missing, present)
        # RACH-only gaps are reported via the RACH message, not as registration fail,
        # when no other registration steps are still hard-missing.
        hard_reg_missing = [m for m in reg_missing if m not in _RACH_STEP_LABELS]
        registration_failed = bool(hard_reg_missing)
        ok = not registration_failed
        details.append(
            ScenarioCheckDetail(
                scenario_id="registration",
                label="Registration",
                expected=True,
                passed=ok,
                missing=hard_reg_missing,
                message="" if ok else _REGISTRATION_FAIL_MESSAGE,
            )
        )
        if waived:
            evidence["registration_waived"] = waived
        if not ok:
            failed = True
            evidence.setdefault("missing", {})["registration"] = hard_reg_missing
    else:
        details.append(
            ScenarioCheckDetail(
                scenario_id="registration",
                label="Registration",
                expected=False,
                passed=True,
            )
        )

    # --- PDU Session ---
    if "pdu_session" in expected:
        raw_pdu_missing = _missing_groups(corpus, pdu_groups)
        # Ending commands imply earlier PDU steps (and RACH / registration soft steps).
        pdu_missing, pdu_waived = _waive_implied_registration_missing(raw_pdu_missing, present)
        # Only keep true PDU group labels as PDU failures.
        pdu_labels = {label for label, _ in pdu_groups}
        pdu_missing = [m for m in pdu_missing if m in pdu_labels]
        pdu_failed = bool(pdu_missing)
        ok = not pdu_failed
        details.append(
            ScenarioCheckDetail(
                scenario_id="pdu_session",
                label="PDU Session",
                expected=True,
                passed=ok,
                missing=pdu_missing,
                message="" if ok else _PDU_SESSION_FAIL_MESSAGE,
            )
        )
        if pdu_waived:
            evidence["pdu_waived"] = pdu_waived
        if not ok:
            failed = True
            evidence.setdefault("missing", {})["pdu_session"] = pdu_missing
    else:
        details.append(
            ScenarioCheckDetail(
                scenario_id="pdu_session",
                label="PDU Session",
                expected=False,
                passed=True,
            )
        )

    # --- Handover ---
    if "handover" in expected:
        missing = _missing_groups(corpus, _HANDOVER_GROUPS)
        handover_failed = bool(missing)
        ok = not handover_failed
        details.append(
            ScenarioCheckDetail(
                scenario_id="handover",
                label="Handover",
                expected=True,
                passed=ok,
                missing=missing,
                message="" if ok else _HANDOVER_FAIL_MESSAGE,
            )
        )
        if not ok:
            failed = True
            evidence.setdefault("missing", {})["handover"] = missing
    else:
        details.append(
            ScenarioCheckDetail(
                scenario_id="handover",
                label="Handover",
                expected=False,
                passed=True,
            )
        )

    if rach_failed:
        failed = True

    if not failed:
        return ScenarioRelevanceResult(
            passed=True,
            blocked=False,
            warned=False,
            expected_scenarios=sorted(expected),
            checks=[d.to_dict() for d in details],
            evidence={**evidence, "matched": True, "attach_match": attach_meta},
            scenario_match_score=1.0,
            target_scenario="attach",
        )

    messages = _compose_scenario_messages(
        rach_failed=rach_failed,
        registration_failed=registration_failed,
        pdu_failed=pdu_failed,
        handover_failed=handover_failed,
    )
    # If only RACH failed and registration/PDU were expected but waived, keep RACH msg.
    if not messages and rach_failed:
        messages = [_RACH_FAIL_MESSAGE]

    passed, blocked, warned = _mode_flags(True)
    # Never advertise 100% when an expected procedure failed (e.g. PDU missing).
    final_score = min(float(match_score), 0.99) if match_score >= 1.0 else float(match_score)
    return ScenarioRelevanceResult(
        passed=passed,
        blocked=blocked,
        warned=warned,
        messages=messages,
        expected_scenarios=sorted(expected),
        checks=[d.to_dict() for d in details],
        evidence={
            **evidence,
            "failed_scenarios": [
                d.scenario_id for d in details if d.expected and not d.passed
            ],
        },
        scenario_match_score=final_score,
        target_scenario="attach",
    )


def check_scenario_relevance(
    path: Path,
    *,
    reported_scenario: Optional[str] = None,
) -> ScenarioRelevanceResult:
    sample = _read_sample(path)
    return check_scenario_relevance_text(
        sample,
        log_filename=path.name,
        reported_scenario=reported_scenario,
    )
