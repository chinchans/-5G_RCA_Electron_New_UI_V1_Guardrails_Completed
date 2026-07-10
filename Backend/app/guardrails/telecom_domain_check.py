"""
OpenAirInterface telecom domain validation for Bug Discovery logs.

Approach order:
  1. Structural OAI fingerprint (layer tags, timestamps, ITTI/TASK/LOG macros)
  2. Component + signaling evidence (not keyword-only)
  3. Weighted hybrid score with negative-domain penalty
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.guardrails.config import (
    GUARDRAILS_BD_TELECOM_DOMAIN_ENABLED,
    GUARDRAILS_BD_TELECOM_DOMAIN_MODE,
    GUARDRAILS_BD_TELECOM_MIN_OVERALL,
    GUARDRAILS_BD_TELECOM_MIN_STRUCTURAL,
    MAX_SCAN_CHARS,
)

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

_OAI_LAYER_NAMES = (
    "ITTI",
    "MAC",
    "NR_MAC",
    "PHY",
    "NR_PHY",
    "RRC",
    "NR_RRC",
    "NGAP",
    "PDCP",
    "RLC",
    "NAS",
    "ENB_APP",
    "GNB_APP",
    "S1AP",
    "X2AP",
    "GTPV1_U",
    "GTPU",
    "UTIL",
    "OPT",
    "HW",
    "CONFIG",
    "F1AP",
    "SCTP",
    "TPOOL",
)
_LAYER_PATTERN = "|".join(re.escape(name) for name in _OAI_LAYER_NAMES)

# Timestamped OAI line: [LAYER] [YYYY-MM-DD HH:MM:SS.micro]  (typical UE / ITTI logs)
_OAI_TIMESTAMPED_LINE_RE = re.compile(
    rf"(?:\x1b\[[0-9;]*m)*\[({_LAYER_PATTERN})\]\s+"
    r"\[\d{{4}}-\d{{2}}-\d{{2}}\s+\d{{2}}:\d{{2}}:\d{{2}}(?:\.\d+)?\]",
    re.IGNORECASE,
)
# Plain OAI line: [LAYER]   message  (typical gNB console / GDB captures — no timestamp)
_OAI_PLAIN_LINE_RE = re.compile(
    rf"(?:\x1b\[[0-9;]*m)*\[({_LAYER_PATTERN})\]\s+\S",
    re.IGNORECASE,
)
_LAYER_TAG_RE = re.compile(rf"\[({_LAYER_PATTERN})\]", re.IGNORECASE)
_TIMESTAMP_RE = re.compile(r"\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\]")
_ITTI_RE = re.compile(r"Starting itti queue|TASK_[A-Z0-9_]+", re.IGNORECASE)
_LOG_MACRO_RE = re.compile(r"LOG_[EWID]\s*\(", re.IGNORECASE)
_NFAPI_RE = re.compile(r"\bnfapi\b", re.IGNORECASE)
_GNB_FRAMEWORK_RE = re.compile(
    r"threadCreate|Initialized RAN|nr-softmodem|openairinterface|F1AP:|ngran_DU|nr-softmodem",
    re.IGNORECASE,
)
# OAI build / compile logs (cmake, build_oai, linker errors) — valid for Bug Discovery RCA
_OAI_BUILD_LINE_RE = re.compile(
    r"Will compile gNB|OPENAIR_DIR|build_oai|cmake_targets|nr-softmodem|nr-cuup|"
    r"openair[23]/|CMakeFiles|F1AP_|NGAP_|asn1_(?:f1ap|nr_rrc|lte_rrc)|"
    r"gmake\[|Running \"cmake|build have failed|compilation of",
    re.IGNORECASE,
)
_OAI_BUILD_STRONG_MARKERS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"Will compile gNB", re.IGNORECASE),
    re.compile(r"OPENAIR_DIR", re.IGNORECASE),
    re.compile(r"build_oai|cmake_targets", re.IGNORECASE),
    re.compile(r"nr-softmodem|nr-cuup", re.IGNORECASE),
    re.compile(r"openair[23]/", re.IGNORECASE),
)

_COMPONENT_PATTERNS: Dict[str, re.Pattern[str]] = {
    "gNB_RAN": re.compile(
        r"\bgNB\b|\beNB\b|GNB_APP|MAC_GNB|PHY_ENB|TASK_RRC_GNB|openair",
        re.IGNORECASE,
    ),
    "OAI_build": re.compile(
        r"Will compile gNB|OPENAIR_DIR|build_oai|cmake_targets|nr-softmodem|nr-cuup",
        re.IGNORECASE,
    ),
    "UE": re.compile(
        r"\bUE\b|NAS_UE|RRC_UE|TASK_MAC_UE|\[UE\s+\d+\]",
        re.IGNORECASE,
    ),
    "5G_Core": re.compile(
        r"\bAMF\b|\bSMF\b|\bUPF\b|NGAP|SCTP|GUAMI|ngap_gNB",
        re.IGNORECASE,
    ),
    "RAN_stack": re.compile(
        r"\b(ITTI|nfapi|MAC|PHY|RRC|PDCP|RLC)\b|candidate_ra|RAPROC|PRACH",
        re.IGNORECASE,
    ),
}

_SIGNALING_PATTERNS: Dict[str, re.Pattern[str]] = {
    "RRC": re.compile(
        r"RRCSetup|RRCConnection|RRCReject|nr_mac_rrc|RRC_",
        re.IGNORECASE,
    ),
    "NAS": re.compile(
        r"\bNAS\b|Registration Request|Registration Accept|attach|detach",
        re.IGNORECASE,
    ),
    "NGAP_N2": re.compile(r"NGAP|N2\b|S1AP|X2AP|F1AP_|f1ap_", re.IGNORECASE),
    "RACH_RA": re.compile(
        r"RACH|random access|contention resolution|candidate_ra|CB-RA|RAPROC|PRACH",
        re.IGNORECASE,
    ),
    "PDU_Session": re.compile(
        r"PDU Session|SM context|N1N2|pdu session establishment",
        re.IGNORECASE,
    ),
    "Interfaces": re.compile(r"\bN[234]\b|GTPU|GTP", re.IGNORECASE),
}

_NEGATIVE_STRONG: Dict[str, re.Pattern[str]] = {
    "web_server": re.compile(
        r"GET\s+/\S+|POST\s+/\S+|HTTP/\d\.\d|nginx|apache|Status:\s*\d{3}",
        re.IGNORECASE,
    ),
    "database": re.compile(
        r"SELECT\s+.+\s+FROM|INSERT\s+INTO|postgres|mongodb|redis|mysql|sqlite",
        re.IGNORECASE,
    ),
    "windows_os": re.compile(
        r"Event\s+ID\s*:|EventID|winlogon|Application\s+Error|Windows\s+Event|"
        r"Microsoft-Windows|SourceModuleType\":\"im_msvistalog|SourceModuleName\":\"in_win\"",
        re.IGNORECASE,
    ),
    "generic_app": re.compile(
        r"Traceback \(most recent call last\)|npm\s+ERR!|Exception in thread",
        re.IGNORECASE,
    ),
}

_FILENAME_HINT_RE = re.compile(
    r"(?:rach|attach|detach|ngap|rrc|mac|ue|gnb|amf|registration|handover|pdu|"
    r"cmake|build|compile|segfault|segmentation|error|failure|fault)",
    re.IGNORECASE,
)


def _build_log_signal(text: str, build_line_hits: int, total_lines: int) -> float:
    marker_hits = sum(1 for pattern in _OAI_BUILD_STRONG_MARKERS if pattern.search(text))
    marker_signal = min(1.0, marker_hits / max(2, len(_OAI_BUILD_STRONG_MARKERS) * 0.4))
    line_signal = _ratio(build_line_hits, total_lines)
    return max(marker_signal, min(1.0, line_signal * 2.5))


def _is_oai_build_log(structural_meta: Dict[str, Any]) -> bool:
    return (
        structural_meta.get("fingerprint") == "oai_build"
        or structural_meta.get("build_signal", 0) >= 0.35
        or structural_meta.get("build_line_ratio", 0) >= 0.08
    )


@dataclass
class TelecomDomainResult:
    passed: bool
    blocked: bool
    warned: bool
    telecom_relevance: float
    structural_score: float
    component_score: float
    signaling_score: float
    negative_penalty: float
    filename_hint_score: float
    profile: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    messages: List[str] = field(default_factory=list)
    checks: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "warned": self.warned,
            "telecom_relevance": round(self.telecom_relevance, 4),
            "context_scores": {
                "structural": round(self.structural_score, 4),
                "component": round(self.component_score, 4),
                "signaling": round(self.signaling_score, 4),
                "negative_penalty": round(self.negative_penalty, 4),
                "filename_hint": round(self.filename_hint_score, 4),
                "overall": round(self.telecom_relevance, 4),
            },
            "profile": self.profile,
            "evidence": self.evidence,
            "messages": self.messages,
            "checks": self.checks,
        }


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text)


def _sample_lines(path: Path, max_chars: int = MAX_SCAN_CHARS) -> List[str]:
    """Read log text with head/middle/tail sampling for large files."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    if len(raw) <= max_chars:
        return [ln.strip() for ln in raw.splitlines() if ln.strip()]

    lines = raw.splitlines()
    non_empty = [ln.strip() for ln in lines if ln.strip()]
    if not non_empty:
        return []

    n = len(non_empty)
    head_n = max(1, int(n * 0.30))
    tail_n = max(1, int(n * 0.20))
    mid_budget = max(0, min(500, n - head_n - tail_n))

    sampled: List[str] = []
    sampled.extend(non_empty[:head_n])
    if mid_budget > 0 and n > head_n + tail_n:
        mid_start = head_n
        mid_end = n - tail_n
        mid_span = mid_end - mid_start
        step = max(1, mid_span // mid_budget)
        for idx in range(mid_start, mid_end, step):
            sampled.append(non_empty[idx])
            if len(sampled) >= head_n + mid_budget:
                break
    sampled.extend(non_empty[-tail_n:])
    return sampled


def _ratio(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return min(1.0, count / total)


def _family_hits(text: str, patterns: Dict[str, re.Pattern[str]]) -> Set[str]:
    found: Set[str] = set()
    for name, pattern in patterns.items():
        if pattern.search(text):
            found.add(name)
    return found


def _score_families(found: Set[str], total_families: int) -> float:
    if total_families <= 0:
        return 0.0
    return min(1.0, len(found) / max(2, total_families * 0.5))


def _compute_structural(lines: List[str]) -> Tuple[float, Dict[str, Any]]:
    if not lines:
        return 0.0, {"line_count": 0}

    timestamped_hits = 0
    plain_hits = 0
    layer_tag_hits = 0
    timestamp_hits = 0
    itti_hits = 0
    log_macro_hits = 0
    nfapi_hits = 0
    gnb_framework_hits = 0
    build_line_hits = 0
    layers_seen: Set[str] = set()

    for line in lines:
        clean = _strip_ansi(line)
        is_timestamped = bool(_OAI_TIMESTAMPED_LINE_RE.search(clean))
        if is_timestamped:
            timestamped_hits += 1
        elif _OAI_PLAIN_LINE_RE.search(clean):
            plain_hits += 1
        if _OAI_BUILD_LINE_RE.search(clean):
            build_line_hits += 1

        layer_match = _LAYER_TAG_RE.search(clean)
        if layer_match:
            layer_tag_hits += 1
            layers_seen.add(layer_match.group(1).upper())
        if _TIMESTAMP_RE.search(clean):
            timestamp_hits += 1
        if _ITTI_RE.search(clean):
            itti_hits += 1
        if _LOG_MACRO_RE.search(clean):
            log_macro_hits += 1
        if _NFAPI_RE.search(clean):
            nfapi_hits += 1
        if _GNB_FRAMEWORK_RE.search(clean):
            gnb_framework_hits += 1

    total = len(lines)
    joined = "\n".join(lines)
    timestamped_ratio = _ratio(timestamped_hits, total)
    plain_line_ratio = _ratio(plain_hits, total)
    build_line_ratio = _ratio(build_line_hits, total)
    oai_line_ratio = _ratio(timestamped_hits + plain_hits, total)
    layer_ratio = _ratio(layer_tag_hits, total)
    timestamp_ratio = _ratio(timestamp_hits, total)
    framework_signal = min(
        1.0,
        (itti_hits + log_macro_hits + nfapi_hits + gnb_framework_hits) / 6.0,
    )
    build_signal = _build_log_signal(joined, build_line_hits, total)

    runtime_structural = (
        0.30 * timestamped_ratio
        + 0.35 * plain_line_ratio
        + 0.20 * layer_ratio
        + 0.15 * framework_signal
    )
    build_structural = 0.55 * build_line_ratio + 0.45 * build_signal
    structural = max(runtime_structural, build_structural)

    if build_signal >= 0.35 or build_line_ratio >= 0.08:
        fingerprint = "oai_build"
    elif timestamped_ratio >= plain_line_ratio:
        fingerprint = "oai_timestamped"
    elif plain_line_ratio > 0:
        fingerprint = "oai_plain"
    else:
        fingerprint = "unknown"

    return structural, {
        "line_count": total,
        "oai_line_ratio": round(oai_line_ratio, 4),
        "timestamped_line_ratio": round(timestamped_ratio, 4),
        "plain_line_ratio": round(plain_line_ratio, 4),
        "build_line_ratio": round(build_line_ratio, 4),
        "build_signal": round(build_signal, 4),
        "layer_tag_ratio": round(layer_ratio, 4),
        "timestamp_ratio": round(timestamp_ratio, 4),
        "itti_hits": itti_hits,
        "log_macro_hits": log_macro_hits,
        "nfapi_hits": nfapi_hits,
        "gnb_framework_hits": gnb_framework_hits,
        "build_line_hits": build_line_hits,
        "layers_seen": sorted(layers_seen),
        "framework_signal": round(framework_signal, 4),
        "fingerprint": fingerprint,
    }


def _detect_profile(structural_meta: Dict[str, Any], components: Set[str]) -> str:
    if _is_oai_build_log(structural_meta) or "OAI_build" in components:
        return "oai_build"
    layers = set(structural_meta.get("layers_seen") or [])
    if "NGAP" in layers or "5G_Core" in components:
        return "oai_core"
    if "GNB_APP" in layers or "gNB_RAN" in components:
        return "oai_gnb"
    if "UE" in components or any(layer in layers for layer in ("MAC", "NR_MAC", "PHY")):
        return "oai_ue"
    if structural_meta.get("oai_line_ratio", 0) >= 0.1:
        return "oai_generic"
    return "unknown"


def check_telecom_domain_text(
    text: str,
    *,
    filename: str = "",
    mode: Optional[str] = None,
    min_overall: Optional[float] = None,
    min_structural: Optional[float] = None,
) -> TelecomDomainResult:
    """Run telecom domain validation on in-memory log text."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return _evaluate_lines(
        lines,
        filename=filename,
        mode=mode,
        min_overall=min_overall,
        min_structural=min_structural,
    )


def check_telecom_domain(path: Path) -> TelecomDomainResult:
    """Run telecom domain validation on a log file path."""
    if not GUARDRAILS_BD_TELECOM_DOMAIN_ENABLED:
        return TelecomDomainResult(
            passed=True,
            blocked=False,
            warned=False,
            telecom_relevance=1.0,
            structural_score=1.0,
            component_score=1.0,
            signaling_score=1.0,
            negative_penalty=0.0,
            filename_hint_score=0.0,
            profile="disabled",
            messages=[],
        )

    lines = _sample_lines(path)
    return _evaluate_lines(lines, filename=path.name)


def _evaluate_lines(
    lines: List[str],
    *,
    filename: str = "",
    mode: Optional[str] = None,
    min_overall: Optional[float] = None,
    min_structural: Optional[float] = None,
) -> TelecomDomainResult:
    mode = (mode or GUARDRAILS_BD_TELECOM_DOMAIN_MODE).lower().strip()
    min_overall = GUARDRAILS_BD_TELECOM_MIN_OVERALL if min_overall is None else min_overall
    min_structural = GUARDRAILS_BD_TELECOM_MIN_STRUCTURAL if min_structural is None else min_structural

    joined = "\n".join(lines)
    structural_score, structural_meta = _compute_structural(lines)

    components = _family_hits(joined, _COMPONENT_PATTERNS)
    signaling = _family_hits(joined, _SIGNALING_PATTERNS)
    negatives = _family_hits(joined, _NEGATIVE_STRONG)

    component_score = _score_families(components, len(_COMPONENT_PATTERNS))
    signaling_score = _score_families(signaling, len(_SIGNALING_PATTERNS))
    negative_penalty = min(1.0, len(negatives) * 0.35)
    filename_hint_score = 1.0 if _FILENAME_HINT_RE.search(filename) else 0.0

    telecom_relevance = max(
        0.0,
        min(
            1.0,
            0.35 * structural_score
            + 0.25 * component_score
            + 0.25 * signaling_score
            + 0.05 * filename_hint_score
            - 0.30 * negative_penalty,
        ),
    )

    profile = _detect_profile(structural_meta, components)
    checks: List[Dict[str, Any]] = []
    messages: List[str] = []

    # --- Check 1: Structural OAI fingerprint (first gate) ---
    plain_line_ratio = structural_meta.get("plain_line_ratio", 0)
    oai_line_ratio = structural_meta.get("oai_line_ratio", 0)
    layer_tag_ratio = structural_meta.get("layer_tag_ratio", 0)
    build_line_ratio = structural_meta.get("build_line_ratio", 0)
    build_signal = structural_meta.get("build_signal", 0)
    is_build_log = _is_oai_build_log(structural_meta)
    has_oai_fingerprint = (
        oai_line_ratio >= 0.08
        or plain_line_ratio >= 0.10
        or layer_tag_ratio >= 0.12
        or build_line_ratio >= 0.05
        or build_signal >= 0.35
    )
    has_framework = (
        structural_meta.get("itti_hits", 0) > 0
        or structural_meta.get("log_macro_hits", 0) > 0
        or structural_meta.get("nfapi_hits", 0) > 0
        or structural_meta.get("gnb_framework_hits", 0) > 0
        or structural_meta.get("timestamp_ratio", 0) >= 0.20
        or plain_line_ratio >= 0.10
        or build_signal >= 0.25
        or build_line_ratio >= 0.05
    )
    structural_pass = (
        structural_score >= min_structural and has_oai_fingerprint and has_framework
    )
    checks.append(
        {
            "id": "oai_structural_fingerprint",
            "passed": structural_pass,
            "score": round(structural_score, 4),
            "message": (
                "Log matches OpenAirInterface structural fingerprint."
                if structural_pass
                else "Log does not match the expected OpenAirInterface log structure "
                "(layer tags, timestamps, ITTI/TASK/LOG macros)."
            ),
        }
    )
    if not structural_pass:
        messages.append(
            "Provided logs do not appear to be from a supported 5G network component."
        )

    # --- Check 2: Negative domain ---
    negative_pass = len(negatives) == 0 or structural_pass and telecom_relevance >= 0.55
    checks.append(
        {
            "id": "negative_domain",
            "passed": negative_pass,
            "families": sorted(negatives),
            "message": (
                "No unsupported log domains detected (web, database, OS)."
                if negative_pass
                else f"Unsupported log domain detected: {', '.join(sorted(negatives))}."
            ),
        }
    )
    if negatives and not negative_pass:
        messages.append(
            "Provided logs do not appear to be from a supported 5G network component."
        )

    # --- Check 3: Component + signaling co-evidence ---
    has_component = len(components) >= 1
    has_signaling = len(signaling) >= 1
    co_evidence_pass = (has_component and has_signaling) or (is_build_log and has_component)
    checks.append(
        {
            "id": "component_signaling_evidence",
            "passed": co_evidence_pass,
            "components": sorted(components),
            "signaling": sorted(signaling),
            "message": (
                "Component and signaling evidence present."
                if co_evidence_pass
                else "Insufficient telecom component and signaling evidence in log content."
            ),
        }
    )
    if structural_pass and not co_evidence_pass:
        messages.append(
            "Log structure looks like OAI but lacks clear component and signaling evidence "
            "for 5G bug discovery."
        )

    # --- Check 4: Overall confidence ---
    overall_pass = telecom_relevance >= min_overall
    checks.append(
        {
            "id": "telecom_relevance_score",
            "passed": overall_pass,
            "score": round(telecom_relevance, 4),
            "threshold": min_overall,
            "message": (
                f"Overall telecom relevance {telecom_relevance * 100:.0f}% "
                f"(threshold {min_overall * 100:.0f}%)."
            ),
        }
    )
    if structural_pass and not overall_pass:
        messages.append(
            f"Overall context score {telecom_relevance * 100:.0f}% is below "
            f"{min_overall * 100:.0f}% threshold. RCA may be unreliable."
        )

    # Verdict policy
    hard_block = (
        not structural_pass
        or (negatives and not structural_pass)
        or (negatives and len(negatives) >= 2 and structural_score < 0.4)
        or (structural_pass and not has_component and not has_signaling and structural_score < 0.45)
    )

    if mode == "advisory":
        blocked = False
        warned = bool(messages) or not overall_pass
        passed = not hard_block or True  # advisory never blocks
        if hard_block or not overall_pass:
            warned = True
    elif mode == "strict":
        blocked = hard_block or not overall_pass or not co_evidence_pass
        warned = False
        passed = not blocked
    else:  # balanced
        # Do not block valid OAI runtime or OAI build logs that pass structural fingerprint
        blocked = hard_block or (
            structural_pass
            and not overall_pass
            and plain_line_ratio < 0.08
            and not is_build_log
        )
        warned = (not blocked) and (not co_evidence_pass or not overall_pass)
        passed = not blocked

    if blocked and not messages:
        messages.append(
            "Provided logs do not appear to be from a supported 5G network component."
        )

    return TelecomDomainResult(
        passed=passed,
        blocked=blocked,
        warned=warned,
        telecom_relevance=telecom_relevance,
        structural_score=structural_score,
        component_score=component_score,
        signaling_score=signaling_score,
        negative_penalty=negative_penalty,
        filename_hint_score=filename_hint_score,
        profile=profile,
        evidence={
            "structural": structural_meta,
            "components": sorted(components),
            "signaling": sorted(signaling),
            "negatives": sorted(negatives),
        },
        messages=messages,
        checks=checks,
    )
