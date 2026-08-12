"""
Confidence-based context check for Bug Discovery.

Aggregates telecom relevance, attach/scenario match, completeness, and
environment match (vs past successful investigations) into an overall score.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.guardrails.config import (
    BACKEND_DIR,
    GUARDRAILS_BD_CONTEXT_CONFIDENCE_ENABLED,
    GUARDRAILS_BD_CONTEXT_CONFIDENCE_MODE,
    GUARDRAILS_BD_CONTEXT_MIN_OVERALL,
    GUARDRAILS_BD_HISTORICAL_MIN_SIMILARITY,
    MAX_SCAN_CHARS,
)
from app.guardrails.data_quality_check import DataQualityResult
from app.guardrails.historical_pattern_check import HistoricalPatternResult
from app.guardrails.log_pattern_store import load_learned_pattern_payload
from app.guardrails.scenario_relevance_check import (
    ScenarioRelevanceResult,
    _attach_match_score,
    _normalize_blob,
)
from app.guardrails.telecom_domain_check import TelecomDomainResult

_WEIGHT_TELECOM = 0.30
_WEIGHT_SCENARIO = 0.30
_WEIGHT_COMPLETENESS = 0.20
_WEIGHT_ENVIRONMENT = 0.20

# Reference floors (cmake / build attach context vs rich runtime CU attach).
_BUILD_TELECOM_FLOOR = 0.90
_BUILD_SCENARIO_FLOOR = 0.05
_BUILD_COMPLETENESS = 0.10
_BUILD_ENVIRONMENT_CAP = 0.95
_RUNTIME_TELECOM_FLOOR = 1.00
_RUNTIME_MISSING_AUTH_COMPLETENESS = 0.92

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

_ENV_FACET_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("rfsim", re.compile(r"\brfsim\b|--rfsim", re.I)),
    ("nr_softmodem", re.compile(r"nr-softmodem|nr-uesoftmodem", re.I)),
    ("du_conf", re.compile(r"du_gnb\.conf|GENERIC-NR-5GC/CONF/du", re.I)),
    ("cu_conf", re.compile(r"cu_gnb\.conf|gnb\.sa\.band|/CONF/cu", re.I)),
    ("ue_conf", re.compile(r"ue\.conf|nrue", re.I)),
    ("ngran_du", re.compile(r"ngran_DU|nodeType.*DU", re.I)),
    ("ngran_cu", re.compile(r"ngran_CU|nodeType.*CU", re.I)),
    ("f1ap", re.compile(r"\bF1AP\b|Starting F1AP", re.I)),
    ("ngap", re.compile(r"\bNGAP\b|NGSetup", re.I)),
    ("cmake_build", re.compile(r"build_oai|cmake_targets|Will compile gNB", re.I)),
    ("band_nr", re.compile(r"\bband\s+\d+|DL frequency", re.I)),
)

# Runtime stack / signaling markers used to lift telecom relevance toward 100%.
_RUNTIME_STACK_MARKERS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"\bNR_RRC\b", re.I),
    re.compile(r"\bNGAP\b", re.I),
    re.compile(r"\bF1AP\b", re.I),
    re.compile(r"\bSCTP\b", re.I),
    re.compile(r"\bGTPU\b|\bGTP-U\b", re.I),
    re.compile(r"\bPDCP\b", re.I),
    re.compile(r"\bSDAP\b", re.I),
    re.compile(r"\bE1AP\b", re.I),
    re.compile(r"\bAMF\b", re.I),
    re.compile(r"\bngran_?(?:CU|DU)\b|\bDU\b.*\bCU\b|\bCU\b.*\bDU\b", re.I),
)

_AUTH_MARKERS = re.compile(
    r"authentication\s+request|authentication\s+response|authentication\s+failure|"
    r"auth[_\s-]?request|5g-aka|nas\s+authentication|security\s+mode\s+command.*auth|"
    r"\bauthenticate\b",
    re.I,
)

_BUILD_HINT_RE = re.compile(
    r"Will compile gNB|OPENAIR_DIR|Running \"cmake|CMAKE_BUILD_TYPE|"
    r"build have failed|cmake_targets|asn1c supports|compilation of|"
    r"No package '|Checking for module",
    re.I,
)

_RUNTIME_CALLFLOW_RE = re.compile(
    r"Decoding CCCH|Send RRC Setup|RRCSetupComplete|RegistrationRequest|"
    r"NG Initial UE Message|SecurityModeCommand|PDU Session|"
    r"InitialContextSetup|RRCReconfiguration|pdusessionsetup|"
    r"NGAP_PDUSESSION|Create UE context",
    re.I,
)


@dataclass
class ContextConfidenceResult:
    passed: bool
    blocked: bool
    warned: bool
    telecom_relevance: float
    scenario_match: float
    completeness: float
    environment_match: float
    overall: float
    threshold: float
    messages: List[str] = field(default_factory=list)
    scorecard: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    skipped: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "warned": self.warned,
            "skipped": self.skipped,
            "telecom_relevance": round(self.telecom_relevance, 4),
            "scenario_match": round(self.scenario_match, 4),
            "completeness": round(self.completeness, 4),
            "environment_match": round(self.environment_match, 4),
            "overall": round(self.overall, 4),
            "threshold": self.threshold,
            "messages": self.messages,
            "scorecard": self.scorecard,
            "evidence": self.evidence,
            "mode": GUARDRAILS_BD_CONTEXT_CONFIDENCE_MODE,
            "target_scenario": "attach",
        }


def _pct(value: float) -> int:
    return int(round(max(0.0, min(1.0, value)) * 100))


def _build_scorecard(
    telecom: float,
    scenario: float,
    completeness: float,
    environment: float,
    overall: float,
) -> List[str]:
    return [
        f"Telecom relevance: {_pct(telecom)}%",
        f"Scenario match: {_pct(scenario)}%",
        f"Completeness: {_pct(completeness)}%",
        f"Environment match: {_pct(environment)}%",
        f"Overall context score: {_pct(overall)}%",
    ]


def _mode_flags(below_threshold: bool) -> Tuple[bool, bool, bool]:
    """Return (passed, blocked, warned)."""
    if not below_threshold:
        return True, False, False
    mode = str(GUARDRAILS_BD_CONTEXT_CONFIDENCE_MODE or "advisory").strip().lower()
    blocked = mode in ("balanced", "strict")
    warned = mode == "advisory" or not blocked
    return (not blocked), blocked, warned


def _component_family(filename: str, text: str, profile: str = "") -> str:
    name = (filename or "").lower()
    blob = f"{name}\n{(text or '')[:4000]}".lower()
    profile_l = (profile or "").lower()
    if "build" in profile_l or re.search(r"cmake|build_oai|compile", blob):
        if not re.search(r"\[(?:mac|nr_mac|phy|rrc|ngap|f1ap)\]", blob):
            return "build"
    if re.search(r"(^|[_\-])du([_\-]|$)|\bdu_gnb\b|ngran_du", name) or "ngran_du" in blob:
        return "du"
    if re.search(r"(^|[_\-])cu([_\-]|$)|\bcu_gnb\b|ngran_cu", name) or "ngran_cu" in blob:
        return "cu"
    if re.search(r"(^|[_\-])ue([_\-]|$)|\bue_gnb\b|uesoftmodem", name) or "nr-uesoftmodem" in blob:
        return "ue"
    if "gnb" in name or "softmodem" in blob:
        return "gnb"
    return "unknown"


def _extract_env_facets(text: str, filename: str, profile: str = "") -> Set[str]:
    facets: Set[str] = set()
    family = _component_family(filename, text, profile)
    facets.add(f"component:{family}")
    clean = _ANSI_ESCAPE.sub("", text or "")
    for name, pattern in _ENV_FACET_PATTERNS:
        if pattern.search(clean) or pattern.search(filename or ""):
            facets.add(name)
    return facets


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _resolve_peer_log(matched_log_file: Optional[str], pattern_id: Optional[str]) -> Optional[Path]:
    if matched_log_file:
        candidates = [
            BACKEND_DIR / "app/services/Error_fixing_pipelin/log_files" / matched_log_file,
            BACKEND_DIR / "resources/rca_logs" / matched_log_file,
            Path(matched_log_file),
        ]
        for candidate in candidates:
            try:
                if candidate.is_file():
                    return candidate.resolve()
            except OSError:
                continue
        rca_dir = BACKEND_DIR / "resources/rca_logs"
        if rca_dir.is_dir():
            for match in rca_dir.glob(f"*_{matched_log_file}"):
                if match.is_file():
                    return match.resolve()

    if pattern_id:
        payload = load_learned_pattern_payload()
        for item in payload.get("patterns") or []:
            if not isinstance(item, dict):
                continue
            if item.get("id") != pattern_id and item.get("log_file") != matched_log_file:
                continue
            raw = item.get("log_path") or ""
            if raw:
                path = Path(raw)
                if path.is_file():
                    return path.resolve()
            log_file = item.get("log_file")
            if log_file:
                return _resolve_peer_log(str(log_file), None)
    return None


def _read_sample(path: Path) -> str:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(raw) <= MAX_SCAN_CHARS:
        return raw
    return raw[:MAX_SCAN_CHARS]


def _environment_match(
    *,
    filename: str,
    log_text: str,
    profile: str,
    historical: Optional[HistoricalPatternResult],
) -> Tuple[float, Dict[str, Any]]:
    current_facets = _extract_env_facets(log_text, filename, profile)
    evidence: Dict[str, Any] = {
        "current_facets": sorted(current_facets),
        "component": _component_family(filename, log_text, profile),
    }

    similarity = float(historical.similarity_score) if historical is not None else 0.0
    threshold = float(GUARDRAILS_BD_HISTORICAL_MIN_SIMILARITY or 0.65)
    scaled_hist = min(1.0, similarity / threshold) if threshold > 0 else similarity

    peer_path: Optional[Path] = None
    if historical is not None:
        peer_path = _resolve_peer_log(historical.matched_log_file, historical.best_pattern_id)
        evidence["matched_log_file"] = historical.matched_log_file
        evidence["similarity_score"] = round(similarity, 4)

    jaccard = 0.0
    same_component = False
    if peer_path is not None:
        peer_text = _read_sample(peer_path)
        peer_facets = _extract_env_facets(peer_text, peer_path.name, "")
        jaccard = _jaccard(current_facets, peer_facets)
        same_component = (
            _component_family(filename, log_text, profile)
            == _component_family(peer_path.name, peer_text, "")
        )
        evidence["peer_facets"] = sorted(peer_facets)
        evidence["peer_path"] = str(peer_path)
        evidence["facet_jaccard"] = round(jaccard, 4)
        evidence["same_component"] = same_component
    else:
        # No peer file: local env consistency for a recognized OAI family.
        family = evidence["component"]
        local = 0.55 if family in {"du", "cu", "ue", "gnb"} else 0.35
        if "rfsim" in current_facets or "nr_softmodem" in current_facets:
            local = min(1.0, local + 0.2)
        if len(current_facets) >= 4:
            local = min(1.0, local + 0.15)
        jaccard = local
        evidence["peer_facets"] = []
        evidence["local_env_score"] = round(local, 4)

    # Prefer same-component peers from past successful investigations.
    if same_component:
        score = 0.55 * jaccard + 0.45 * scaled_hist
    elif historical is not None and historical.is_known_log:
        score = 0.40 * jaccard + 0.60 * scaled_hist
    else:
        score = 0.70 * jaccard + 0.30 * scaled_hist

    return max(0.0, min(1.0, score)), evidence


def _is_build_capture(
    *,
    profile: str,
    filename: str,
    log_text: str,
    data_quality: Optional[DataQualityResult],
    scenario: Optional[ScenarioRelevanceResult] = None,
) -> bool:
    """True only for build/compiler-only captures (no UE call-flow evidence).

    Mixed files (CMake output concatenated with later CU/UE runtime) must NOT be
    treated as build-only — otherwise telecom floors to 90% and completeness to 10%.
    """
    # Runtime attach / registration evidence wins over leading cmake noise.
    if scenario is not None and not scenario.skipped:
        attach = {}
        if isinstance(scenario.evidence, dict):
            attach = dict(scenario.evidence.get("attach_match") or {})
        if int(attach.get("found") or 0) > 0:
            return False
        checks = scenario.checks if isinstance(scenario.checks, list) else []
        for check in checks:
            if not isinstance(check, dict):
                continue
            if check.get("expected") and check.get("scenario_id") in {
                "rach_setup",
                "registration",
                "pdu_session",
                "handover",
            } and check.get("passed"):
                return False

    sample = log_text or ""
    runtime_hits = len(_RUNTIME_CALLFLOW_RE.findall(sample))
    if runtime_hits > 0:
        return False

    if (profile or "").lower() == "oai_build":
        return True
    if data_quality is not None and str(getattr(data_quality, "scenario", "") or "").lower() == "build":
        return True
    name = (filename or "").lower()
    if ("cmake" in name or "build" in name) and runtime_hits == 0:
        return True
    build_hits = len(_BUILD_HINT_RE.findall(sample[:8000]))
    return build_hits >= 3 and runtime_hits == 0


def _runtime_stack_marker_count(log_text: str) -> int:
    return sum(1 for pattern in _RUNTIME_STACK_MARKERS if pattern.search(log_text or ""))


def _calibrate_telecom_relevance(
    raw: float,
    *,
    profile: str,
    log_text: str,
    is_build: bool,
) -> Tuple[float, Dict[str, Any]]:
    """Map domain score to context-confidence semantics (reference samples).

    - OAI CMake/build logs with telecom evidence → ~90%
    - Rich runtime CU/DU stack markers → ~100%
    """
    evidence: Dict[str, Any] = {"raw": round(raw, 4), "is_build": is_build}
    score = max(0.0, min(1.0, float(raw)))

    if is_build:
        # Build logs are still telecom (OAI/gNB/ASN.1/cmake) even without signaling.
        if score >= 0.50:
            score = max(score, _BUILD_TELECOM_FLOOR)
        evidence["calibration"] = "build_telecom_floor"
        return score, evidence

    markers = _runtime_stack_marker_count(log_text)
    evidence["stack_markers"] = markers
    if markers >= 5 or (profile or "").lower() in {"oai_gnb", "oai_core", "oai_ue"} and markers >= 3:
        score = max(score, _RUNTIME_TELECOM_FLOOR)
        evidence["calibration"] = "runtime_stack_floor"
        return score, evidence

    if markers >= 3 and score >= 0.55:
        score = max(score, 0.95)
        evidence["calibration"] = "runtime_partial_floor"
    return score, evidence


def _calibrate_scenario_match(
    raw: float,
    *,
    is_build: bool,
    scenario: Optional[ScenarioRelevanceResult],
) -> Tuple[float, Dict[str, Any]]:
    """Attach/Registration/Call-flow match for context confidence.

    Build / compiler logs with no RRC/NGAP/NAS runtime → ~5% floor.
    Fully matched attach procedure → 100%.
    Missing expected PDU/registration events → never report 100%.
    """
    evidence: Dict[str, Any] = {"raw": round(float(raw or 0.0), 4), "is_build": is_build}
    score = max(0.0, min(1.0, float(raw or 0.0)))

    has_warnings = bool(scenario and scenario.messages)
    failed = []
    if scenario is not None and isinstance(scenario.evidence, dict):
        failed = list(scenario.evidence.get("failed_scenarios") or [])
    evidence["failed_scenarios"] = failed
    evidence["has_warning_messages"] = has_warnings

    if (
        scenario is not None
        and not scenario.skipped
        and scenario.passed
        and not scenario.warned
        and not scenario.messages
        and not failed
    ):
        evidence["calibration"] = "full_pass"
        return 1.0, evidence

    # Never surface 100% while the UI warns about missing expected events.
    if has_warnings or failed:
        if is_build and score <= _BUILD_SCENARIO_FLOOR:
            evidence["calibration"] = "build_with_missing_callflow"
            return _BUILD_SCENARIO_FLOOR, evidence
        if score >= 1.0:
            score = 0.99
        evidence["calibration"] = "penalize_failed_expected_procedures"
        return score, evidence

    if is_build and score <= _BUILD_SCENARIO_FLOOR:
        evidence["calibration"] = "build_no_runtime_floor"
        return _BUILD_SCENARIO_FLOOR, evidence

    if score <= 0.0 and is_build:
        evidence["calibration"] = "build_zero_floor"
        return _BUILD_SCENARIO_FLOOR, evidence

    return score, evidence


def _calibrate_completeness(
    *,
    is_build: bool,
    scenario: Optional[ScenarioRelevanceResult],
    data_quality: Optional[DataQualityResult],
    log_text: str,
) -> Tuple[float, Dict[str, Any]]:
    """Completeness vs the *intended Attach/Registration scenario*.

    Reference:
      - CMake/build-only capture → ~10% (compiler output, no protocol execution)
      - Full CU attach call-flow missing explicit Authentication → ~92%
      - Otherwise blend data-quality with attach checklist coverage
    """
    evidence: Dict[str, Any] = {"is_build": is_build}
    dq_score = 1.0
    if data_quality is not None:
        dq_score = float(data_quality.completeness_score or 0.0)
        evidence["data_quality_score"] = round(dq_score, 4)

    if is_build:
        evidence["calibration"] = "build_no_protocol_execution"
        return _BUILD_COMPLETENESS, evidence

    attach_meta: Dict[str, Any] = {}
    if scenario is not None and isinstance(scenario.evidence, dict):
        attach_meta = dict(scenario.evidence.get("attach_match") or {})
    evidence["attach_match"] = attach_meta

    full_pass = (
        scenario is not None
        and not scenario.skipped
        and scenario.passed
        and not scenario.warned
        and not scenario.messages
    )
    has_auth = bool(_AUTH_MARKERS.search(log_text or ""))
    evidence["has_authentication"] = has_auth

    if full_pass:
        if has_auth:
            evidence["calibration"] = "full_attach_with_auth"
            return min(1.0, max(dq_score, 0.98)), evidence
        evidence["calibration"] = "full_attach_missing_auth"
        return _RUNTIME_MISSING_AUTH_COMPLETENESS, evidence

    # Partial attach coverage: prefer scenario checklist over DQ truncation score.
    total = int(attach_meta.get("total") or 0)
    found = int(attach_meta.get("found") or 0)
    if total > 0:
        attach_fraction = found / total
        # Blend lightly with DQ so truncated runtime logs still get penalized.
        score = 0.75 * attach_fraction + 0.25 * dq_score
        evidence["calibration"] = "partial_attach_blend"
        evidence["attach_fraction"] = round(attach_fraction, 4)
        return max(0.0, min(1.0, score)), evidence

    evidence["calibration"] = "data_quality_fallback"
    return max(0.0, min(1.0, dq_score)), evidence


def _calibrate_environment(
    raw: float,
    *,
    is_build: bool,
) -> Tuple[float, Dict[str, Any]]:
    score = max(0.0, min(1.0, float(raw)))
    evidence: Dict[str, Any] = {"raw": round(score, 4), "is_build": is_build}
    if is_build:
        # OAI CMake/Linux/ASN.1 build env is a strong match, but not a runtime SA CU/DU deploy.
        score = min(score, _BUILD_ENVIRONMENT_CAP)
        if score >= 0.80:
            score = max(score, 0.90)
            score = min(score, _BUILD_ENVIRONMENT_CAP)
        evidence["calibration"] = "build_environment_cap"
    return score, evidence


def compute_context_confidence(
    *,
    telecom: Optional[TelecomDomainResult] = None,
    historical: Optional[HistoricalPatternResult] = None,
    data_quality: Optional[DataQualityResult] = None,
    scenario: Optional[ScenarioRelevanceResult] = None,
    filename: str = "",
    log_text: str = "",
) -> ContextConfidenceResult:
    threshold = float(GUARDRAILS_BD_CONTEXT_MIN_OVERALL or 0.70)

    if not GUARDRAILS_BD_CONTEXT_CONFIDENCE_ENABLED:
        scorecard = _build_scorecard(1.0, 1.0, 1.0, 1.0, 1.0)
        return ContextConfidenceResult(
            passed=True,
            blocked=False,
            warned=False,
            telecom_relevance=1.0,
            scenario_match=1.0,
            completeness=1.0,
            environment_match=1.0,
            overall=1.0,
            threshold=threshold,
            scorecard=scorecard,
            skipped=True,
            evidence={"reason": "disabled"},
        )

    telecom_raw = 1.0
    profile = ""
    if telecom is not None:
        telecom_raw = float(telecom.telecom_relevance or 0.0)
        profile = str(telecom.profile or "")

    is_build = _is_build_capture(
        profile=profile,
        filename=filename,
        log_text=log_text,
        data_quality=data_quality,
        scenario=scenario,
    )

    telecom_score, telecom_ev = _calibrate_telecom_relevance(
        telecom_raw,
        profile=profile,
        log_text=log_text,
        is_build=is_build,
    )

    scenario_raw = 0.0
    if scenario is not None:
        scenario_raw = float(getattr(scenario, "scenario_match_score", 0.0) or 0.0)
    elif log_text:
        scenario_raw, _ = _attach_match_score(_normalize_blob(log_text))
    else:
        scenario_raw = 1.0

    scenario_score, scenario_ev = _calibrate_scenario_match(
        scenario_raw,
        is_build=is_build,
        scenario=scenario,
    )

    completeness, completeness_ev = _calibrate_completeness(
        is_build=is_build,
        scenario=scenario,
        data_quality=data_quality,
        log_text=log_text,
    )

    environment_raw, env_evidence = _environment_match(
        filename=filename,
        log_text=log_text,
        profile=profile,
        historical=historical,
    )
    environment, env_cal_ev = _calibrate_environment(environment_raw, is_build=is_build)
    env_evidence = {**env_evidence, "calibration": env_cal_ev}

    overall = (
        _WEIGHT_TELECOM * telecom_score
        + _WEIGHT_SCENARIO * scenario_score
        + _WEIGHT_COMPLETENESS * completeness
        + _WEIGHT_ENVIRONMENT * environment
    )
    overall = max(0.0, min(1.0, overall))

    scorecard = _build_scorecard(
        telecom_score, scenario_score, completeness, environment, overall
    )
    below = overall < threshold
    passed, blocked, warned = _mode_flags(below)

    messages: List[str] = []
    if below:
        messages.append(
            f"Overall context score {_pct(overall)}% is below {_pct(threshold)}% threshold."
        )
        messages.extend(scorecard)

    return ContextConfidenceResult(
        passed=passed,
        blocked=blocked,
        warned=warned,
        telecom_relevance=telecom_score,
        scenario_match=scenario_score,
        completeness=completeness,
        environment_match=environment,
        overall=overall,
        threshold=threshold,
        messages=messages,
        scorecard=scorecard,
        evidence={
            "weights": {
                "telecom": _WEIGHT_TELECOM,
                "scenario": _WEIGHT_SCENARIO,
                "completeness": _WEIGHT_COMPLETENESS,
                "environment": _WEIGHT_ENVIRONMENT,
            },
            "environment": env_evidence,
            "telecom_calibration": telecom_ev,
            "scenario_calibration": scenario_ev,
            "completeness_calibration": completeness_ev,
            "is_build_capture": is_build,
            "target_scenario": "attach",
            "below_threshold": below,
        },
    )
