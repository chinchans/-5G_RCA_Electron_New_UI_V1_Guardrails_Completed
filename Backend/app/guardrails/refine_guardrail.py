"""Guardrails for Test Script Generator prompt refinement flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.guardrails.intent_coverage_service import (
    parse_test_cases_from_generation,
    validate_intent_coverage,
)
from app.guardrails.test_script_guardrail import validate_generated_test_script


@dataclass
class RefineGuardrailVerdict:
    passed: bool
    blocked: bool
    refinement_source: str = "test_script"
    reasons: List[str] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    script_verdict: Optional[Dict[str, Any]] = None
    intent_coverage: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "refinement_source": self.refinement_source,
            "reasons": self.reasons,
            "findings": self.findings,
            "script_verdict": self.script_verdict,
            "intent_coverage": self.intent_coverage,
        }


def detect_refinement_source(
    previous_response: Optional[str],
    explicit: Optional[str] = None,
) -> str:
    if explicit in {"test_case", "test_script"}:
        return explicit
    if parse_test_cases_from_generation(previous_response or ""):
        return "test_case"
    return "test_script"


def validate_refined_output(
    refined_text: str,
    *,
    source_text: str = "",
    dataset_folder: Optional[str] = None,
    new_prompt: str = "",
    previous_response: Optional[str] = None,
    refinement_source: Optional[str] = None,
) -> RefineGuardrailVerdict:
    """Validate refined output for both test-case and test-script refinement paths."""
    source = detect_refinement_source(previous_response, refinement_source)

    if source == "test_case":
        return _validate_refined_test_cases(
            refined_text,
            source_text=source_text,
            dataset_folder=dataset_folder,
        )

    script_verdict = validate_generated_test_script(
        refined_text,
        source_text=source_text,
        dataset_folder=dataset_folder,
        language="python",
        refine_strict=True,
    )
    reasons = list(script_verdict.reasons)
    findings = list(script_verdict.findings)

    return RefineGuardrailVerdict(
        passed=not script_verdict.blocked,
        blocked=script_verdict.blocked,
        refinement_source=source,
        reasons=list(dict.fromkeys(reasons)),
        findings=findings,
        script_verdict=script_verdict.to_dict(),
    )


def _validate_refined_test_cases(
    refined_text: str,
    *,
    source_text: str,
    dataset_folder: Optional[str],
) -> RefineGuardrailVerdict:
    findings: List[Dict[str, Any]] = []
    reasons: List[str] = []

    parsed_cases = parse_test_cases_from_generation(refined_text)
    if not parsed_cases:
        reason = (
            "Refined output must remain valid structured test case JSON when refining test cases."
        )
        findings.append(
            {
                "layer": "script_guardrail",
                "check": "test_case_structure",
                "severity": "error",
                "detail": reason,
            }
        )
        return RefineGuardrailVerdict(
            passed=False,
            blocked=True,
            refinement_source="test_case",
            reasons=[reason],
            findings=findings,
        )

    if not dataset_folder:
        warning = "Intent coverage skipped — dataset folder not provided for refined test cases."
        return RefineGuardrailVerdict(
            passed=True,
            blocked=False,
            refinement_source="test_case",
            reasons=[],
            findings=[
                {
                    "layer": "intent_coverage",
                    "check": "dataset_folder",
                    "severity": "warning",
                    "detail": warning,
                }
            ],
        )

    coverage = validate_intent_coverage(
        Path(dataset_folder),
        refined_text,
        require_structured_json=True,
        advisory_only=False,
    )
    coverage_dict = coverage.to_dict()

    if not coverage.passed:
        reason = (
            "Refined test cases failed intent coverage guardrail for the loaded dataset."
        )
        reasons.append(reason)
        if coverage.errors:
            reasons.extend(coverage.errors[:3])
        if coverage.warnings:
            reasons.extend(coverage.warnings[:2])
        findings.append(
            {
                "layer": "intent_coverage",
                "check": "mandatory_intent_coverage",
                "severity": "error",
                "detail": reason,
            }
        )

    return RefineGuardrailVerdict(
        passed=coverage.passed,
        blocked=not coverage.passed,
        refinement_source="test_case",
        reasons=list(dict.fromkeys(reasons)),
        findings=findings,
        intent_coverage=coverage_dict,
    )
