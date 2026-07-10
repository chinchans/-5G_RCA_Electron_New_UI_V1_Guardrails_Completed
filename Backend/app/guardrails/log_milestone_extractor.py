"""
Canonical milestone extraction from OpenAirInterface log files.

Maps noisy OAI log lines to ordered milestone IDs for historical pattern matching.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from app.guardrails.config import MAX_SCAN_CHARS

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
_TIMESTAMP_RE = re.compile(
    r"\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\]"
)
_FRAME_SLOT_RE = re.compile(
    r"frame\s*=\s*\d+\s*,\s*slot\s*=\s*\d+\s*:",
    re.IGNORECASE,
)
_HEX_ADDR_RE = re.compile(r"\b0x[0-9a-fA-F]+\b")
_UE_ID_RE = re.compile(r"\[UE\s+\d+\]|\bUE\s+\d+\b|TC-RNTI\s+\d+|rnti\s+\d+", re.IGNORECASE)
_NUMERIC_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
_WHITESPACE_RE = re.compile(r"\s+")

# (milestone_id, compiled pattern) — first match per line wins
_MILESTONE_RULES: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("build_cmake", re.compile(r"Running \"cmake|CMake Error|cmake_targets|CMakeFiles", re.I)),
    ("build_compile_fail", re.compile(r"build have failed|compilation of|undefined reference|error:", re.I)),
    ("seg_fault", re.compile(r"Segmentation fault|segfault|SIGSEGV", re.I)),
    ("stack_init", re.compile(
        r"Starting itti queue|threadCreate\(\)|Initialized RAN|nfapi running mode|"
        r"Entering main loop",
        re.I,
    )),
    ("ngap_setup_request", re.compile(r"Send NGSetupRequest|NGSetupRequest to AMF", re.I)),
    ("ngap_setup_response", re.compile(r"Received NGSetupResponse|NGSetupResponse from AMF", re.I)),
    ("ngap_register_cnf", re.compile(r"NGAP_REGISTER_GNB_CNF|associated AMF", re.I)),
    ("f1ap_start", re.compile(r"Starting F1AP", re.I)),
    ("prach_detected", re.compile(
        r"Detected PRACH|PRACH \[UE|placing PRACH|nr_handle_prach|Processing PRACH request",
        re.I,
    )),
    ("ra_start", re.compile(
        r"contention-based random access|4-step.*random access|"
        r"Initialization of.*random access procedure",
        re.I,
    )),
    ("msg2_sent", re.compile(
        r"Transmitted RAR|Random Access Response|Preparing Random Access Response|"
        r"nr_generate_Msg2|Scheduling PDSCH transmission for RAR",
        re.I,
    )),
    ("msg3_tx", re.compile(r"RA-Msg3 transmitted|UL grant provided for Msg3", re.I)),
    ("msg3_received", re.compile(r"Received Msg3", re.I)),
    ("contention_resolved", re.compile(r"Contention resolution successful", re.I)),
    ("contention_timer_expired", re.compile(
        r"Contention resolution timer has expired|RA procedure has failed",
        re.I,
    )),
    ("rrc_connection_request", re.compile(
        r"RRC Connection Request|RRCSetupRequest|Forwarding RRC Connection Request|"
        r"Processing RRC Connection Request",
        re.I,
    )),
    ("rrc_setup_sent", re.compile(r"RRCSetup message sent|Scheduling RRCSetup", re.I)),
    ("rrc_setup_complete", re.compile(r"RRC Setup Complete|process_RRCSetupComplete", re.I)),
    ("rrc_connected", re.compile(
        r"RRC_CONNECTED|RRC connection successfully established|state changed to RRC_CONNECTED",
        re.I,
    )),
    ("ngap_initial_ue", re.compile(
        r"Initial UE Message|ngap_gNB_initial_ue_message|Sending Initial UE Message",
        re.I,
    )),
    ("registration_complete", re.compile(
        r"Successful RRC Connection Establishment|Registration Request",
        re.I,
    )),
    ("sib1_decoded", re.compile(r"SIB1 decoded", re.I)),
    ("rrc_setup_request_ue", re.compile(r"Generating RRCSetupRequest|RRCSetupRequest Encoded", re.I)),
)

_SCENARIO_HINTS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("build", re.compile(r"cmake|CMake|build have failed|OPENAIR_DIR|nr-softmodem", re.I)),
    ("registration", re.compile(
        r"RRCSetup|PRACH|random access|Msg3|RRC Connection|Initial UE Message|"
        r"contention resolution",
        re.I,
    )),
    ("cu_stack", re.compile(r"NGSetupRequest|NGSetupResponse|Starting F1AP|NGAP layer", re.I)),
)


def normalize_log_line(line: str) -> str:
    """Strip timestamps, ANSI codes, UE/thread IDs, and variable numeric tokens."""
    text = _ANSI_ESCAPE.sub("", line or "")
    text = _TIMESTAMP_RE.sub("", text)
    text = _FRAME_SLOT_RE.sub("", text)
    text = _UE_ID_RE.sub("UE", text)
    text = _HEX_ADDR_RE.sub("HEX", text)
    text = _NUMERIC_RE.sub("N", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def extract_milestone_from_line(line: str) -> Optional[str]:
    """Return the first matching milestone for a single log line."""
    normalized = normalize_log_line(line)
    if not normalized:
        return None
    for milestone_id, pattern in _MILESTONE_RULES:
        if pattern.search(normalized) or pattern.search(line):
            return milestone_id
    return None


def extract_milestone_sequence(text: str) -> List[str]:
    """Extract ordered canonical steps; collapse consecutive duplicates."""
    steps: List[str] = []
    for raw_line in text.splitlines():
        milestone = extract_milestone_from_line(raw_line)
        if milestone is None:
            continue
        if steps and steps[-1] == milestone:
            continue
        steps.append(milestone)
    return steps


def extract_milestones_from_file(path: Path, max_chars: int = MAX_SCAN_CHARS) -> List[str]:
    content = path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    return extract_milestone_sequence(content)


def detect_scenario(steps: Sequence[str], text: str = "") -> str:
    """Infer scenario family for pattern routing."""
    step_set = set(steps)
    if step_set & {"build_cmake", "build_compile_fail"}:
        return "build"

    registration_chain = {
        "prach_detected",
        "msg2_sent",
        "msg3_received",
        "rrc_setup_complete",
        "rrc_setup_sent",
        "rrc_connection_request",
    }
    if step_set & registration_chain:
        return "registration"
    if step_set & {"ra_start", "msg3_tx", "contention_timer_expired", "contention_resolved"}:
        return "registration"
    if step_set & {"rrc_setup_request_ue", "sib1_decoded"}:
        return "registration"

    if step_set & {"ngap_setup_request", "ngap_setup_response", "f1ap_start", "ngap_register_cnf"}:
        return "cu_stack"

    if step_set & {"registration_complete", "rrc_connected", "ngap_initial_ue"}:
        return "registration"

    if "stack_init" in step_set:
        return "generic_runtime"

    sample = text[:8000] if text else ""
    for scenario, pattern in _SCENARIO_HINTS:
        if pattern.search(sample):
            return scenario
    return "unknown"


def build_ngrams(sequence: Sequence[str], n: int) -> List[Tuple[str, ...]]:
    """Sliding-window N-grams over canonical steps."""
    if n <= 0:
        return []
    if not sequence:
        return []
    if len(sequence) < n:
        return [tuple(sequence)]
    return [tuple(sequence[i : i + n]) for i in range(len(sequence) - n + 1)]


def summarize_extraction(steps: Sequence[str], scenario: str) -> Dict[str, object]:
    return {
        "step_count": len(steps),
        "scenario": scenario,
        "steps": list(steps),
    }
