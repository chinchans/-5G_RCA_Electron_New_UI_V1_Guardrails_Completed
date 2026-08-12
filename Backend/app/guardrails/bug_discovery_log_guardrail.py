"""Input guardrails for Bug Discovery log files (telecom domain + historical + data quality + scenario relevance + context confidence + security)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException

from app.guardrails.config import (
    GUARDRAILS_BUG_DISCOVERY_INPUT_ENABLED,
    GUARDRAILS_BUG_DISCOVERY_LOG_ENABLED,
    GUARDRAILS_BD_CONTEXT_CONFIDENCE_ENABLED,
    GUARDRAILS_BD_DATA_QUALITY_ENABLED,
    GUARDRAILS_BD_HISTORICAL_PATTERN_ENABLED,
    GUARDRAILS_BD_SCENARIO_RELEVANCE_ENABLED,
    GUARDRAILS_BD_TELECOM_DOMAIN_ENABLED,
    GUARDRAILS_ENABLED,
    MAX_SCAN_CHARS,
    MAX_UPLOAD_BYTES,
)
from app.guardrails.context_confidence_check import (
    ContextConfidenceResult,
    compute_context_confidence,
)
from app.guardrails.data_quality_check import DataQualityResult, check_data_quality
from app.guardrails.historical_pattern_check import (
    HistoricalPatternResult,
    check_historical_pattern,
)
from app.guardrails.input_guardrail import GuardrailVerdict, get_spec_intel_guardrail
from app.guardrails.scenario_relevance_check import (
    ScenarioRelevanceResult,
    check_scenario_relevance,
)
from app.guardrails.telecom_domain_check import TelecomDomainResult, check_telecom_domain

_LOG_EXTENSIONS = frozenset({".log", ".txt"})
_DEFAULT_BD_SCENARIO = "attach"


def _resolve_log_path(log_file_path: str) -> Path:
    if not log_file_path or not str(log_file_path).strip():
        raise HTTPException(status_code=400, detail="Log file path is required.")

    path = Path(log_file_path).expanduser()
    try:
        path = path.resolve()
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid log file path: {exc}") from exc

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Log file not found: {path}")
    if not path.is_file():
        raise HTTPException(status_code=400, detail=f"Path is not a file: {path}")
    if path.suffix.lower() not in _LOG_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported log file type '{path.suffix}'. Allowed: .log, .txt",
        )

    size = path.stat().st_size
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Log file exceeds maximum scan size ({MAX_UPLOAD_BYTES // (1024 * 1024)} MB).",
        )
    if size == 0:
        raise HTTPException(status_code=400, detail="Log file is empty.")
    return path


def _telecom_blocked_verdict(quality: TelecomDomainResult) -> GuardrailVerdict:
    reasons = list(quality.messages) or [
        "Provided logs do not appear to be from a supported 5G network component."
    ]
    return GuardrailVerdict(
        passed=False,
        blocked=True,
        reasons=reasons,
        layers={
            "telecom_domain": quality.to_dict(),
            "security_skipped": True,
        },
    )


def _historical_blocked_verdict(
    historical: HistoricalPatternResult,
    quality: Optional[TelecomDomainResult] = None,
) -> GuardrailVerdict:
    reasons = list(historical.messages) or [
        "Current log sequence differs significantly from known historical patterns."
    ]
    layers: Dict[str, Any] = {
        "historical_pattern": historical.to_dict(),
        "security_skipped": True,
    }
    if quality is not None:
        layers["telecom_domain"] = quality.to_dict()
    return GuardrailVerdict(
        passed=False,
        blocked=True,
        reasons=reasons,
        layers=layers,
    )


def _data_quality_blocked_verdict(
    data_quality: DataQualityResult,
    quality: Optional[TelecomDomainResult] = None,
    historical: Optional[HistoricalPatternResult] = None,
) -> GuardrailVerdict:
    reasons = list(data_quality.messages) or [
        "Log file appears incomplete; expected events are missing."
    ]
    layers: Dict[str, Any] = {
        "data_quality": data_quality.to_dict(),
        "security_skipped": True,
    }
    if quality is not None:
        layers["telecom_domain"] = quality.to_dict()
    if historical is not None:
        layers["historical_pattern"] = historical.to_dict()
    return GuardrailVerdict(
        passed=False,
        blocked=True,
        reasons=reasons,
        layers=layers,
    )


def _scenario_blocked_verdict(
    scenario: ScenarioRelevanceResult,
    quality: Optional[TelecomDomainResult] = None,
    historical: Optional[HistoricalPatternResult] = None,
    data_quality: Optional[DataQualityResult] = None,
) -> GuardrailVerdict:
    reasons = list(scenario.messages) or [
        "Expected PDU Session Setup events/Registration logs not found."
    ]
    layers: Dict[str, Any] = {
        "scenario_relevance": scenario.to_dict(),
        "security_skipped": True,
    }
    if quality is not None:
        layers["telecom_domain"] = quality.to_dict()
    if historical is not None:
        layers["historical_pattern"] = historical.to_dict()
    if data_quality is not None:
        layers["data_quality"] = data_quality.to_dict()
    return GuardrailVerdict(
        passed=False,
        blocked=True,
        reasons=reasons,
        layers=layers,
    )


def _context_blocked_verdict(
    context: ContextConfidenceResult,
    quality: Optional[TelecomDomainResult] = None,
    historical: Optional[HistoricalPatternResult] = None,
    data_quality: Optional[DataQualityResult] = None,
    scenario: Optional[ScenarioRelevanceResult] = None,
) -> GuardrailVerdict:
    reasons = list(context.messages) or [
        f"Overall context score {int(round(context.overall * 100))}% is below "
        f"{int(round(context.threshold * 100))}% threshold."
    ]
    layers: Dict[str, Any] = {
        "context_confidence": context.to_dict(),
        "security_skipped": True,
    }
    if quality is not None:
        layers["telecom_domain"] = quality.to_dict()
    if historical is not None:
        layers["historical_pattern"] = historical.to_dict()
    if data_quality is not None:
        layers["data_quality"] = data_quality.to_dict()
    if scenario is not None:
        layers["scenario_relevance"] = scenario.to_dict()
    return GuardrailVerdict(
        passed=False,
        blocked=True,
        reasons=reasons,
        layers=layers,
    )


def _merge_historical_into_verdict(
    verdict: GuardrailVerdict,
    historical: HistoricalPatternResult,
) -> GuardrailVerdict:
    layers = dict(verdict.layers or {})
    layers["historical_pattern"] = historical.to_dict()

    if historical.blocked:
        merged_reasons = list(dict.fromkeys(list(verdict.reasons) + list(historical.messages)))
        return GuardrailVerdict(
            passed=False,
            blocked=True,
            reasons=merged_reasons,
            scan=verdict.scan,
            layers=layers,
        )

    if historical.warned and historical.messages:
        layers["historical_pattern_warnings"] = historical.messages

    return GuardrailVerdict(
        passed=verdict.passed and not verdict.blocked,
        blocked=verdict.blocked,
        reasons=verdict.reasons,
        scan=verdict.scan,
        layers=layers,
    )


def _merge_data_quality_into_verdict(
    verdict: GuardrailVerdict,
    data_quality: DataQualityResult,
) -> GuardrailVerdict:
    layers = dict(verdict.layers or {})
    layers["data_quality"] = data_quality.to_dict()

    if data_quality.blocked:
        merged_reasons = list(dict.fromkeys(list(verdict.reasons) + list(data_quality.messages)))
        return GuardrailVerdict(
            passed=False,
            blocked=True,
            reasons=merged_reasons,
            scan=verdict.scan,
            layers=layers,
        )

    if data_quality.warned and data_quality.messages:
        layers["data_quality_warnings"] = data_quality.messages

    return GuardrailVerdict(
        passed=verdict.passed and not verdict.blocked,
        blocked=verdict.blocked,
        reasons=verdict.reasons,
        scan=verdict.scan,
        layers=layers,
    )


def _merge_scenario_into_verdict(
    verdict: GuardrailVerdict,
    scenario: ScenarioRelevanceResult,
) -> GuardrailVerdict:
    layers = dict(verdict.layers or {})
    layers["scenario_relevance"] = scenario.to_dict()

    if scenario.blocked:
        merged_reasons = list(dict.fromkeys(list(verdict.reasons) + list(scenario.messages)))
        return GuardrailVerdict(
            passed=False,
            blocked=True,
            reasons=merged_reasons,
            scan=verdict.scan,
            layers=layers,
        )

    if scenario.warned and scenario.messages:
        layers["scenario_relevance_warnings"] = scenario.messages

    return GuardrailVerdict(
        passed=verdict.passed and not verdict.blocked,
        blocked=verdict.blocked,
        reasons=verdict.reasons,
        scan=verdict.scan,
        layers=layers,
    )


def _merge_context_into_verdict(
    verdict: GuardrailVerdict,
    context: ContextConfidenceResult,
) -> GuardrailVerdict:
    layers = dict(verdict.layers or {})
    layers["context_confidence"] = context.to_dict()

    if context.blocked:
        merged_reasons = list(dict.fromkeys(list(verdict.reasons) + list(context.messages)))
        return GuardrailVerdict(
            passed=False,
            blocked=True,
            reasons=merged_reasons,
            scan=verdict.scan,
            layers=layers,
        )

    if context.warned and context.messages:
        layers["context_confidence_warnings"] = context.messages

    return GuardrailVerdict(
        passed=verdict.passed and not verdict.blocked,
        blocked=verdict.blocked,
        reasons=verdict.reasons,
        scan=verdict.scan,
        layers=layers,
    )


def _merge_quality_into_verdict(
    verdict: GuardrailVerdict,
    quality: TelecomDomainResult,
) -> GuardrailVerdict:
    layers = dict(verdict.layers or {})
    layers["telecom_domain"] = quality.to_dict()

    if quality.blocked:
        merged_reasons = list(dict.fromkeys(list(verdict.reasons) + list(quality.messages)))
        return GuardrailVerdict(
            passed=False,
            blocked=True,
            reasons=merged_reasons,
            scan=verdict.scan,
            layers=layers,
        )

    if quality.warned and quality.messages:
        layers["telecom_domain_warnings"] = quality.messages

    return GuardrailVerdict(
        passed=verdict.passed and not verdict.blocked,
        blocked=verdict.blocked,
        reasons=verdict.reasons,
        scan=verdict.scan,
        layers=layers,
    )


def validate_bug_discovery_log_file(
    log_file_path: str,
    *,
    reported_scenario: Optional[str] = None,
) -> GuardrailVerdict:
    """Run telecom → historical → data quality → scenario → context confidence → optional security."""
    if not GUARDRAILS_ENABLED or not GUARDRAILS_BUG_DISCOVERY_LOG_ENABLED:
        return GuardrailVerdict(passed=True, blocked=False, layers={"enabled": False})

    path = _resolve_log_path(log_file_path)
    scenario_label = (reported_scenario or "").strip() or _DEFAULT_BD_SCENARIO

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        raw = ""
    log_sample = raw if len(raw) <= MAX_SCAN_CHARS else raw[:MAX_SCAN_CHARS]

    quality: Optional[TelecomDomainResult] = None
    if GUARDRAILS_BD_TELECOM_DOMAIN_ENABLED:
        quality = check_telecom_domain(path)
        if quality.blocked:
            return _telecom_blocked_verdict(quality)

    historical: Optional[HistoricalPatternResult] = None
    if GUARDRAILS_BD_HISTORICAL_PATTERN_ENABLED:
        historical = check_historical_pattern(path)
        if historical.blocked:
            return _historical_blocked_verdict(historical, quality)

    data_quality: Optional[DataQualityResult] = None
    if GUARDRAILS_BD_DATA_QUALITY_ENABLED:
        data_quality = check_data_quality(path)
        if data_quality.blocked:
            return _data_quality_blocked_verdict(data_quality, quality, historical)

    scenario: Optional[ScenarioRelevanceResult] = None
    if GUARDRAILS_BD_SCENARIO_RELEVANCE_ENABLED:
        scenario = check_scenario_relevance(path, reported_scenario=scenario_label)
        if scenario.blocked:
            return _scenario_blocked_verdict(scenario, quality, historical, data_quality)

    context: Optional[ContextConfidenceResult] = None
    if GUARDRAILS_BD_CONTEXT_CONFIDENCE_ENABLED:
        context = compute_context_confidence(
            telecom=quality,
            historical=historical,
            data_quality=data_quality,
            scenario=scenario,
            filename=path.name,
            log_text=log_sample,
        )
        if context.blocked:
            return _context_blocked_verdict(
                context, quality, historical, data_quality, scenario
            )

    if GUARDRAILS_BUG_DISCOVERY_INPUT_ENABLED:
        guard = get_spec_intel_guardrail()
        verdict = guard.scan_file(path, context="bug_discovery_log")
    else:
        verdict = GuardrailVerdict(
            passed=True,
            blocked=False,
            layers={"input_security": {"enabled": False}},
        )

    if quality is not None:
        verdict = _merge_quality_into_verdict(verdict, quality)

    if historical is not None:
        verdict = _merge_historical_into_verdict(verdict, historical)

    if data_quality is not None:
        verdict = _merge_data_quality_into_verdict(verdict, data_quality)

    if scenario is not None:
        verdict = _merge_scenario_into_verdict(verdict, scenario)

    if context is not None:
        verdict = _merge_context_into_verdict(verdict, context)

    return verdict


def raise_if_bug_log_blocked(verdict: GuardrailVerdict) -> None:
    """Raise HTTP 422 when log content fails input guardrails."""
    if not verdict.blocked:
        return

    layers = verdict.layers or {}
    is_telecom_block = bool(layers.get("telecom_domain", {}).get("blocked"))
    if is_telecom_block:
        quality = layers.get("telecom_domain") or {}
        raise HTTPException(
            status_code=422,
            detail={
                "error": "log_blocked_by_telecom_domain",
                "message": "Log file rejected: not a valid OpenAirInterface / 5G telecom log.",
                "reasons": verdict.reasons,
                "guardrails": verdict.to_dict(),
                "quality": quality,
                "findings": quality.get("checks") or [],
            },
        )

    is_historical_block = bool(layers.get("historical_pattern", {}).get("blocked"))
    if is_historical_block:
        historical = layers.get("historical_pattern") or {}
        raise HTTPException(
            status_code=422,
            detail={
                "error": "log_blocked_by_historical_pattern",
                "message": (
                    "Log file rejected: this log has no close match in previously "
                    "analyzed logs (treated as a new log type)."
                ),
                "reasons": verdict.reasons,
                "guardrails": verdict.to_dict(),
                "historical_pattern": historical,
                "findings": historical.get("checks") or [],
            },
        )

    is_data_quality_block = bool(layers.get("data_quality", {}).get("blocked"))
    if is_data_quality_block:
        data_quality = layers.get("data_quality") or {}
        raise HTTPException(
            status_code=422,
            detail={
                "error": "log_blocked_by_data_quality",
                "message": (
                    data_quality.get("messages", [None])[0]
                    or "Log file appears incomplete; expected events are missing."
                ),
                "reasons": verdict.reasons,
                "guardrails": verdict.to_dict(),
                "data_quality": data_quality,
                "findings": data_quality.get("checks") or [],
            },
        )

    is_scenario_block = bool(layers.get("scenario_relevance", {}).get("blocked"))
    if is_scenario_block:
        scenario = layers.get("scenario_relevance") or {}
        raise HTTPException(
            status_code=422,
            detail={
                "error": "log_blocked_by_scenario_relevance",
                "message": (
                    (scenario.get("messages") or [None])[0]
                    or (
                        "Expected PDU Session Setup events/Registration logs not found."
                    )
                ),
                "reasons": verdict.reasons,
                "guardrails": verdict.to_dict(),
                "scenario_relevance": scenario,
                "findings": scenario.get("checks") or [],
            },
        )

    is_context_block = bool(layers.get("context_confidence", {}).get("blocked"))
    if is_context_block:
        context = layers.get("context_confidence") or {}
        raise HTTPException(
            status_code=422,
            detail={
                "error": "log_blocked_by_context_confidence",
                "message": (
                    (context.get("messages") or [None])[0]
                    or "Overall context score is below the configured threshold."
                ),
                "reasons": verdict.reasons,
                "guardrails": verdict.to_dict(),
                "context_confidence": context,
                "findings": context.get("scorecard") or [],
            },
        )

    guard = get_spec_intel_guardrail()
    findings = guard._findings_for_rejection(verdict)
    raise HTTPException(
        status_code=422,
        detail={
            "error": "document_blocked_by_guardrails",
            "message": "Log file rejected by input security guardrails.",
            "reasons": verdict.reasons,
            "guardrails": verdict.to_dict(),
            "findings": findings,
        },
    )


def validate_bug_discovery_log_or_raise(log_file_path: Optional[str]) -> None:
    """Validate log file path when provided."""
    if not log_file_path:
        return
    verdict = validate_bug_discovery_log_file(log_file_path)
    raise_if_bug_log_blocked(verdict)
