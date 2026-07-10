"""
Data quality checks for Bug Discovery OAI log files.

Detects:
  - Truncated / abruptly cut-off captures (mid-line, mid-token, short vs peers)
  - Missing timestamps (when the log format expects them)
  - Empty or sparse log sections
  - Incomplete event coverage vs expected late-stage milestones
    (e.g. expected events missing from the capture tail)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.guardrails.config import (
    GUARDRAILS_BD_DATA_QUALITY_ENABLED,
    GUARDRAILS_BD_DATA_QUALITY_EMPTY_GAP_LINES,
    GUARDRAILS_BD_DATA_QUALITY_MIN_COMPLETENESS,
    GUARDRAILS_BD_DATA_QUALITY_MIN_LENGTH_RATIO,
    GUARDRAILS_BD_DATA_QUALITY_MIN_PEER_STEPS,
    GUARDRAILS_BD_DATA_QUALITY_MIN_TIMESTAMP_RATIO,
    GUARDRAILS_BD_DATA_QUALITY_MODE,
    MAX_SCAN_CHARS,
)
from app.guardrails.log_milestone_extractor import (
    detect_scenario,
    extract_milestone_sequence,
)

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
_TIMESTAMP_RE = re.compile(
    r"\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\]"
    r"|\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}"
    r"|frame\s*=\s*\d+\s*,\s*slot\s*=\s*\d+",
    re.IGNORECASE,
)
_OAI_LAYER_RE = re.compile(
    r"\[(?:ITTI|MAC|NR_MAC|PHY|NR_PHY|RRC|NR_RRC|NGAP|PDCP|RLC|NAS|"
    r"ENB_APP|GNB_APP|S1AP|X2AP|GTPU|GTPV1_U|UTIL|OPT|HW|CONFIG|F1AP|SCTP)\]",
    re.IGNORECASE,
)
# Full OAI runtime line: [LAYER] [timestamp] message...
_OAI_FULL_LINE_RE = re.compile(
    r"^\s*(?:\x1b\[[0-9;]*m)*\[(?P<layer>[A-Z0-9_]+)\]\s+"
    r"(?:(?:\x1b\[[0-9;]*m)*\[(?P<ts>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\]\s+)?"
    r"(?P<msg>.*)$",
    re.IGNORECASE,
)
_PARTIAL_TIMESTAMP_RE = re.compile(
    r"\[\d{1,4}(?:-\d{0,2})?(?:-\d{0,2})?(?:\s+\d{0,2})?(?::\d{0,2})?(?::\d{0,2})?(?:\.\d*)?$"
)
_TRUNCATION_MARKERS = re.compile(
    r"\b(truncated|cut off|incomplete capture|file ended unexpectedly|"
    r"unexpected EOF|broken pipe)\b",
    re.IGNORECASE,
)
_BUILD_HINT_RE = re.compile(
    r"cmake|CMake|OPENAIR_DIR|build_oai|nr-softmodem|compilation of",
    re.IGNORECASE,
)
_WORD_CHAR_RE = re.compile(r"[A-Za-z0-9_]$")
_TERMINAL_PUNCT_RE = re.compile(r"[.!?…)\]]$")

# Expected late-stage milestones by scenario (used for "last 30% missing")
_EXPECTED_TAIL_BY_SCENARIO: Dict[str, Tuple[str, ...]] = {
    "registration": (
        "msg3_received",
        "contention_resolved",
        "rrc_connection_request",
        "rrc_setup_sent",
        "rrc_setup_complete",
        "rrc_connected",
        "ngap_initial_ue",
        "registration_complete",
    ),
    "cu_stack": (
        "ngap_setup_request",
        "ngap_setup_response",
        "ngap_register_cnf",
        "f1ap_start",
    ),
}

_FAILURE_MARKERS = frozenset({
    "contention_timer_expired",
    "build_compile_fail",
    "seg_fault",
})
_SUCCESS_MARKERS = frozenset({
    "rrc_setup_complete",
    "rrc_connected",
    "registration_complete",
    "ngap_setup_response",
    "contention_resolved",
})
_IN_PROGRESS_MARKERS = frozenset({
    "ra_start",
    "prach_detected",
    "msg2_sent",
    "msg3_tx",
    "msg3_received",
    "rrc_connection_request",
    "rrc_setup_sent",
    "ngap_setup_request",
    "stack_init",
    "sib1_decoded",
})


@dataclass
class DataQualityResult:
    passed: bool
    blocked: bool
    warned: bool
    completeness_score: float
    truncated: bool = False
    missing_timestamps: bool = False
    empty_sections: bool = False
    incomplete_tail: bool = False
    missing_tail_percent: float = 0.0
    scenario: str = "unknown"
    messages: List[str] = field(default_factory=list)
    checks: List[Dict[str, Any]] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "warned": self.warned,
            "completeness_score": round(self.completeness_score, 4),
            "truncated": self.truncated,
            "missing_timestamps": self.missing_timestamps,
            "empty_sections": self.empty_sections,
            "incomplete_tail": self.incomplete_tail,
            "missing_tail_percent": round(self.missing_tail_percent, 1),
            "scenario": self.scenario,
            "messages": self.messages,
            "checks": self.checks,
            "evidence": self.evidence,
            "mode": GUARDRAILS_BD_DATA_QUALITY_MODE,
        }


def _read_text(path: Path) -> str:
    """Read up to MAX_SCAN_CHARS, snapped to the last complete line."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    if len(raw) <= MAX_SCAN_CHARS:
        return raw
    window = raw[:MAX_SCAN_CHARS]
    snap = window.rfind("\n")
    if snap > MAX_SCAN_CHARS // 2:
        return window[: snap + 1]
    return window


def _read_file_tail(path: Path, max_bytes: int = 8192) -> str:
    """Read the true end of the file for EOF truncation checks."""
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > max_bytes:
            handle.seek(size - max_bytes)
        data = handle.read()
    return data.decode("utf-8", errors="replace")


def _strip_ansi(line: str) -> str:
    return _ANSI_ESCAPE.sub("", line or "").rstrip()


def _non_empty_lines(text: str) -> List[str]:
    """Lines with real content after stripping ANSI (ignore ESC-only lines)."""
    return [line for line in text.splitlines() if _strip_ansi(line).strip()]


def _effective_last_line(text: str) -> Tuple[str, bool]:
    """Return (last meaningful raw line, file_ends_with_newline)."""
    ends_nl = bool(text) and text.endswith(("\n", "\r"))
    for line in reversed(text.splitlines()):
        if _strip_ansi(line).strip():
            return line, ends_nl
    return "", ends_nl


def _message_looks_cut(msg: str) -> bool:
    """True when a log message body looks cut mid-token / mid-phrase."""
    msg = (msg or "").rstrip()
    if not msg:
        return True
    if msg.endswith(("...", "…")):
        return False
    if _TERMINAL_PUNCT_RE.search(msg):
        return False
    if msg.endswith((",", "=", ":", "(", "[", "{", "\\", "-", "/", "|", "&", "+")):
        return True
    tokens = re.findall(r"[A-Za-z0-9_]+", msg)
    if not tokens:
        return False
    last_token = tokens[-1]
    if re.search(r"[:\s]\s*[A-Za-z]{1,8}$", msg) and not msg.endswith((".", "!", "?", ")", "]")):
        if last_token.upper() in {
            "OK", "SA", "UE", "DU", "CU", "AMF", "SMF", "UPF", "RRC", "MAC", "PHY",
            "NGAP", "PDCP", "RLC", "NAS", "F1AP", "SCTP", "ITTI",
        }:
            return False
        if len(last_token) <= 8:
            return True
    return False


def _last_line_is_mid_cut(last_raw: str, *, ends_with_newline: bool) -> Tuple[bool, str]:
    """Detect EOF mid-line / mid-token."""
    last = _strip_ansi(last_raw)
    if not last:
        return True, "empty_last_line"

    no_trailing_nl = not ends_with_newline

    if last.lstrip().startswith("[") and "]" not in last:
        return True, "partial_layer_tag"

    if "]" in last:
        after_first = last.split("]", 1)[1]
        if "[" in after_first:
            open_idx = after_first.rfind("[")
            if "]" not in after_first[open_idx:]:
                return True, "partial_bracket_field"

    if last.count("[") > last.count("]") and _PARTIAL_TIMESTAMP_RE.search(last):
        return True, "partial_timestamp"

    match = _OAI_FULL_LINE_RE.match(last_raw) or _OAI_FULL_LINE_RE.match(last)
    if match:
        ts = match.group("ts")
        msg = (match.group("msg") or "").strip()
        if no_trailing_nl and _message_looks_cut(msg):
            return True, "mid_message_cut"
        if ts and len(msg) <= 2 and no_trailing_nl:
            return True, "empty_message_after_timestamp"

    if re.match(r"^\s*frame\s*=", last, re.IGNORECASE):
        if ":" in last and no_trailing_nl and _message_looks_cut(last.rsplit(":", 1)[-1].strip()):
            return True, "mid_message_cut"

    if no_trailing_nl and _message_looks_cut(last):
        return True, "mid_token_eof"

    if no_trailing_nl and re.search(r":\s*[A-Za-z]{1,8}$", last):
        return True, "colon_fragment"

    return False, ""


def _step_set_jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _is_step_prefix(shorter: Sequence[str], longer: Sequence[str]) -> bool:
    if not shorter or not longer or len(shorter) > len(longer):
        return False
    if list(longer[: len(shorter)]) == list(shorter):
        return True
    need = max(2, int(len(shorter) * 0.6))
    idx = 0
    matched = 0
    for step in longer:
        if idx < len(shorter) and step == shorter[idx]:
            matched += 1
            idx += 1
            if matched >= need:
                return True
    return matched >= need


def _peer_file_size(pattern: Any) -> Optional[int]:
    """Best-effort size of the peer's original log on disk."""
    try:
        from app.guardrails.log_pattern_store import _resolve_log_path
    except Exception:
        return None
    path = _resolve_log_path(getattr(pattern, "log_path", None), getattr(pattern, "log_file", None))
    if path is None or not path.is_file():
        return None
    try:
        return int(path.stat().st_size)
    except OSError:
        return None


def _peer_length_stats(scenario: str, steps: Sequence[str]) -> Dict[str, Any]:
    """Compare current steps to the nearest *similar* learned pattern."""
    try:
        from app.guardrails.historical_pattern_check import load_patterns
    except Exception:
        return {"skipped": True, "reason": "patterns_unavailable"}

    catalog = [p for p in load_patterns() if len(p.steps) >= GUARDRAILS_BD_DATA_QUALITY_MIN_PEER_STEPS]
    if not catalog:
        return {"skipped": True, "reason": "no_peer_patterns"}

    same_scenario = [p for p in catalog if p.scenario == scenario] or catalog
    best = None
    best_score = -1.0
    for pattern in same_scenario:
        jaccard = _step_set_jaccard(steps, pattern.steps)
        prefix = 1.0 if _is_step_prefix(steps, pattern.steps) else 0.0
        score = (0.55 * jaccard) + (0.45 * prefix) + min(0.05, len(pattern.steps) / 5000.0)
        if score > best_score:
            best_score = score
            best = pattern

    if best is None or best_score < 0.25:
        return {"skipped": True, "reason": "no_similar_peer", "best_score": round(best_score, 4)}

    current = len(steps)
    peer_steps = len(best.steps)
    ratio = current / max(1, peer_steps)
    peer_bytes = _peer_file_size(best)
    return {
        "peer_count": len(same_scenario),
        "peer_id": best.id,
        "peer_log_file": best.log_file,
        "peer_steps": peer_steps,
        "peer_bytes": peer_bytes,
        "current_steps": current,
        "similarity": round(best_score, 4),
        "is_prefix": _is_step_prefix(steps, best.steps),
        "length_ratio": round(ratio, 4),
        "threshold": GUARDRAILS_BD_DATA_QUALITY_MIN_LENGTH_RATIO,
    }


def _check_truncation(
    text: str,
    lines: Sequence[str],
    steps: Sequence[str],
    scenario: str,
    content_chars: Optional[int] = None,
) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """Detect abrupt cut-off / truncated capture."""
    evidence: Dict[str, Any] = {}
    if not lines:
        return True, {"reason": "no_content_lines"}, "Log file has no content lines."

    last_raw, ends_nl = _effective_last_line(text)
    last = _strip_ansi(last_raw)
    evidence["last_line_preview"] = last[:160]
    evidence["ends_with_newline"] = ends_nl
    if content_chars is not None:
        evidence["content_chars"] = content_chars

    if _TRUNCATION_MARKERS.search(text[-4000:]):
        evidence["reason"] = "explicit_truncation_marker"
        return True, evidence, "Log file contains an explicit truncation / incomplete-capture marker."

    mid_cut, mid_reason = _last_line_is_mid_cut(last_raw, ends_with_newline=ends_nl)
    if mid_cut:
        evidence["reason"] = mid_reason
        return True, evidence, (
            "Log file appears truncated (capture ends mid-line / mid-message)."
        )

    oai_hits = sum(1 for line in lines if _OAI_LAYER_RE.search(line))
    evidence["oai_line_hits"] = oai_hits
    evidence["line_count"] = len(lines)
    if oai_hits >= 3 and len(lines) < 8:
        evidence["reason"] = "abnormally_short"
        return True, evidence, "Log file appears truncated (too few lines for an OAI runtime capture)."

    peer = _peer_length_stats(scenario, steps)
    evidence["peer_length"] = peer
    if not peer.get("skipped"):
        step_ratio = float(peer.get("length_ratio") or 1.0)
        similar_enough = float(peer.get("similarity") or 0) >= 0.35
        is_prefix = bool(peer.get("is_prefix"))
        # Clear step-prefix of a known capture: flag earlier (70%) than blind length (40%).
        length_limit = 0.70 if is_prefix else GUARDRAILS_BD_DATA_QUALITY_MIN_LENGTH_RATIO

        # Prefer byte-size ratio when the peer log is on disk — step counts from a
        # MAX_SCAN_CHARS window can look "complete" even when the file was cut in half.
        size_ratio: Optional[float] = None
        peer_bytes = peer.get("peer_bytes")
        if content_chars is not None and peer_bytes and int(peer_bytes) > 0:
            size_ratio = float(content_chars) / float(peer_bytes)
            evidence["size_ratio"] = round(size_ratio, 4)

        effective_ratio = size_ratio if size_ratio is not None else step_ratio
        if similar_enough and effective_ratio < length_limit and len(steps) >= 2:
            missing_pct = max(0.0, (1.0 - effective_ratio) * 100.0)
            evidence["reason"] = "short_vs_learned_peers"
            evidence["missing_vs_peer_percent"] = round(missing_pct, 1)
            evidence["length_limit_used"] = length_limit
            evidence["ratio_basis"] = "bytes" if size_ratio is not None else "steps"
            return True, evidence, (
                "Log file appears incomplete; expected events are missing."
            )

    step_set = set(steps)
    in_progress = bool(step_set & _IN_PROGRESS_MARKERS)
    has_terminal = bool(step_set & (_FAILURE_MARKERS | _SUCCESS_MARKERS))
    if in_progress and not has_terminal and oai_hits >= 5:
        if len(steps) < 6 or (peer and not peer.get("skipped") and float(peer.get("length_ratio") or 1) < 0.7):
            evidence["reason"] = "procedure_cut_before_outcome"
            return True, evidence, (
                "Log file appears truncated (procedure started but capture ended "
                "before a success or failure outcome)."
            )

    return False, evidence, None


def _check_timestamps(text: str, lines: Sequence[str]) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """Flag missing timestamps when the log looks like a timestamped OAI runtime log."""
    if _BUILD_HINT_RE.search(text[:8000]) and not _TIMESTAMP_RE.search(text[:8000]):
        return False, {"skipped": True, "reason": "build_log"}, None

    sample = lines[: min(200, len(lines))] or lines
    if not sample:
        return True, {"timestamp_ratio": 0.0}, "Log file has no lines to inspect for timestamps."

    stamped = sum(1 for line in sample if _TIMESTAMP_RE.search(line))
    ratio = stamped / max(1, len(sample))
    evidence = {
        "sample_lines": len(sample),
        "timestamped_lines": stamped,
        "timestamp_ratio": round(ratio, 4),
    }

    oai_hits = sum(1 for line in sample if _OAI_LAYER_RE.search(line))
    evidence["oai_sample_hits"] = oai_hits
    if oai_hits < 3:
        return False, {**evidence, "skipped": True, "reason": "not_runtime_oai"}, None

    # Only warn on sparse timestamps when the file clearly uses the timestamped format
    # (majority of OAI lines in the sample are stamped) but coverage dropped.
    oai_sample = [line for line in sample if _OAI_LAYER_RE.search(line)]
    if oai_sample:
        oai_stamped = sum(1 for line in oai_sample if _TIMESTAMP_RE.search(line))
        oai_ratio = oai_stamped / max(1, len(oai_sample))
        evidence["oai_timestamp_ratio"] = round(oai_ratio, 4)
        if 0 < oai_ratio < GUARDRAILS_BD_DATA_QUALITY_MIN_TIMESTAMP_RATIO:
            return True, evidence, (
                f"Log file has sparse timestamps ({oai_ratio:.0%} of OAI lines); "
                "capture may be incomplete or mixed formats."
            )

    return False, evidence, None


def _check_empty_sections_in_text(text: str) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    all_lines = text.splitlines()
    if not all_lines:
        return True, {"empty_ratio": 1.0, "total_lines": 0}, "Log file is empty."

    content = [line for line in all_lines if _strip_ansi(line).strip()]
    empty_ratio = 1.0 - (len(content) / max(1, len(all_lines)))
    evidence: Dict[str, Any] = {
        "total_lines": len(all_lines),
        "content_lines": len(content),
        "empty_ratio": round(empty_ratio, 4),
    }

    if len(content) == 0:
        return True, evidence, "Log file has no non-empty lines."

    if len(content) < 3 and len(all_lines) >= 10:
        return True, evidence, "Log file sections appear empty (almost no content lines)."

    gap = 0
    max_gap = 0
    for line in all_lines:
        if not line.strip():
            gap += 1
            max_gap = max(max_gap, gap)
        else:
            gap = 0
    evidence["max_blank_gap"] = max_gap
    if max_gap >= GUARDRAILS_BD_DATA_QUALITY_EMPTY_GAP_LINES:
        return True, evidence, (
            f"Log file has a large empty section ({max_gap} consecutive blank lines)."
        )

    if empty_ratio >= 0.7 and len(all_lines) >= 40:
        return True, evidence, (
            f"Log file appears mostly empty ({empty_ratio:.0%} blank lines)."
        )

    return False, evidence, None


def _check_incomplete_tail(
    steps: Sequence[str],
    scenario: str,
) -> Tuple[bool, float, Dict[str, Any], Optional[str]]:
    """
    Compare observed milestones to expected late-stage events for the scenario.

    Failure markers count as a complete failed-procedure capture — unless the
    capture also looks like it stopped mid-procedure before those markers
    (handled separately by truncation).
    """
    expected = _EXPECTED_TAIL_BY_SCENARIO.get(scenario)
    if not expected or len(steps) < 1:
        return False, 0.0, {"skipped": True, "reason": "no_expected_tail"}, None

    step_set = set(steps)
    if step_set & _FAILURE_MARKERS:
        return False, 0.0, {
            "skipped": True,
            "reason": "failure_outcome_present",
            "failure_markers": sorted(step_set & _FAILURE_MARKERS),
        }, None

    present = [event for event in expected if event in step_set]
    missing = [event for event in expected if event not in step_set]
    coverage = len(present) / max(1, len(expected))
    missing_percent = (1.0 - coverage) * 100.0

    evidence = {
        "scenario": scenario,
        "expected_tail": list(expected),
        "present_tail": present,
        "missing_tail": missing,
        "tail_coverage": round(coverage, 4),
        "missing_tail_percent": round(missing_percent, 1),
    }

    early_signals = {
        "registration": {"prach_detected", "ra_start", "msg3_tx", "msg2_sent", "sib1_decoded"},
        "cu_stack": {"stack_init", "ngap_setup_request"},
    }
    early = early_signals.get(scenario, set())
    saw_early = bool(step_set & early) or len(steps) >= 2

    threshold_missing = (1.0 - GUARDRAILS_BD_DATA_QUALITY_MIN_COMPLETENESS) * 100.0
    if saw_early and missing_percent >= threshold_missing and len(missing) >= 2:
        msg = "Log file appears incomplete; expected events are missing."
        return True, missing_percent, evidence, msg

    return False, missing_percent, evidence, None


def check_data_quality_text(
    text: str,
    file_tail: Optional[str] = None,
    content_chars: Optional[int] = None,
) -> DataQualityResult:
    if not GUARDRAILS_BD_DATA_QUALITY_ENABLED:
        return DataQualityResult(
            passed=True,
            blocked=False,
            warned=False,
            completeness_score=1.0,
            messages=[],
            checks=[{"check": "data_quality", "skipped": True}],
        )

    # Snap scan window to a line boundary so MAX_SCAN_CHARS never invents a mid-line cut.
    sample = text[:MAX_SCAN_CHARS]
    if len(text) > MAX_SCAN_CHARS:
        snap = sample.rfind("\n")
        if snap > MAX_SCAN_CHARS // 2:
            sample = sample[: snap + 1]

    lines = _non_empty_lines(sample)
    steps = extract_milestone_sequence(sample)
    scenario = detect_scenario(steps, sample)

    checks: List[Dict[str, Any]] = []
    messages: List[str] = []
    evidence: Dict[str, Any] = {"step_count": len(steps), "content_lines": len(lines)}

    # EOF mid-line detection must use the *true* end of the buffer/file.
    # Never use a line-snapped sample here — that hides real truncations past MAX_SCAN_CHARS.
    if file_tail is not None:
        eof_text = file_tail
    else:
        eof_text = text[-8192:] if len(text) > 8192 else text

    total_chars = content_chars if content_chars is not None else len(text)
    truncated, trunc_ev, trunc_msg = _check_truncation(
        eof_text, lines, steps, scenario, content_chars=total_chars
    )

    checks.append({"check": "truncation", "failed": truncated, "evidence": trunc_ev})
    evidence["truncation"] = trunc_ev
    if trunc_msg:
        messages.append(trunc_msg)

    missing_ts, ts_ev, ts_msg = _check_timestamps(sample, lines)
    checks.append({"check": "timestamps", "failed": missing_ts, "evidence": ts_ev})
    evidence["timestamps"] = ts_ev
    if ts_msg:
        messages.append(ts_msg)

    empty_sec, empty_ev, empty_msg = _check_empty_sections_in_text(sample)
    checks.append({"check": "empty_sections", "failed": empty_sec, "evidence": empty_ev})
    evidence["empty_sections"] = empty_ev
    if empty_msg:
        messages.append(empty_msg)

    incomplete_tail, missing_pct, tail_ev, tail_msg = _check_incomplete_tail(steps, scenario)
    checks.append({"check": "incomplete_tail", "failed": incomplete_tail, "evidence": tail_ev})
    evidence["incomplete_tail"] = tail_ev
    if tail_msg:
        messages.insert(0, tail_msg)

    peer = (trunc_ev or {}).get("peer_length") or {}
    if truncated and peer.get("missing_vs_peer_percent") and not any(
        "incomplete" in m.lower() for m in messages
    ):
        messages.insert(0, "Log file appears incomplete; expected events are missing.")

    score = 1.0
    if truncated:
        score -= 0.40
    if missing_ts:
        score -= 0.15
    if empty_sec:
        score -= 0.25
    if incomplete_tail:
        score -= min(0.40, (missing_pct / 100.0) * 0.5)
    score = max(0.0, min(1.0, score))

    has_issue = truncated or missing_ts or empty_sec or incomplete_tail
    mode = GUARDRAILS_BD_DATA_QUALITY_MODE
    blocked = has_issue and mode in ("balanced", "strict")
    warned = has_issue and mode == "advisory"
    if mode == "strict" and score < GUARDRAILS_BD_DATA_QUALITY_MIN_COMPLETENESS:
        blocked = True
        warned = False

    if has_issue and not any("incomplete" in m.lower() for m in messages):
        if incomplete_tail:
            messages.insert(0, "Log file appears incomplete; expected events are missing.")
        elif truncated:
            messages.insert(0, "Log file appears truncated or incomplete.")

    return DataQualityResult(
        passed=not blocked,
        blocked=blocked,
        warned=warned,
        completeness_score=score,
        truncated=truncated,
        missing_timestamps=missing_ts,
        empty_sections=empty_sec,
        incomplete_tail=incomplete_tail,
        missing_tail_percent=missing_pct,
        scenario=scenario,
        messages=list(dict.fromkeys(messages)),
        checks=checks,
        evidence=evidence,
    )


def check_data_quality(path: Path) -> DataQualityResult:
    """Scan a log file using a line-snapped body sample plus the true file tail."""
    body = _read_text(path)
    tail = _read_file_tail(path)
    try:
        size = int(path.stat().st_size)
    except OSError:
        size = len(body)
    return check_data_quality_text(body, file_tail=tail, content_chars=size)
