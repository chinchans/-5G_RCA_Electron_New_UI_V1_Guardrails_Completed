"""Structural and traceability guardrails for generated test scripts."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.guardrails.test_script_groundedness import validate_script_groundedness
from app.guardrails.test_script_traceability import (
    build_and_save_traceability_matrix,
    validate_script_traceability,
)
from app.guardrails.tsg_prompt_guardrail import (
    _OFF_TOPIC_REFINE_SIGNALS,
    _TELECOM_DATASET_SIGNALS,
    _signal_hits,
    _is_telecom_dataset,
)
from app.guardrails.config import GUARDRAILS_REFINE_STRICT_OUTPUT, GUARDRAILS_SCRIPT_SCOPE_ENABLED

_FENCED_CODE_RE = re.compile(r"```(?:python|py)?\s*([\s\S]*?)```", re.IGNORECASE)


@dataclass
class ScriptGuardrailVerdict:
    passed: bool
    blocked: bool
    reasons: List[str] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "reasons": self.reasons,
            "findings": self.findings,
            "metadata": self.metadata,
        }


def _add_finding(findings: List[Dict[str, Any]], check: str, detail: str, severity: str = "error") -> None:
    findings.append(
        {
            "layer": "script_guardrail",
            "check": check,
            "severity": severity,
            "detail": detail,
        }
    )


def _extract_code_block(text: str) -> str:
    if not text:
        return ""
    stripped = text.strip()
    m = _FENCED_CODE_RE.search(stripped)
    if m:
        return m.group(1).strip()
    return stripped


def validate_script_dataset_scope(
    generated_script: str,
    *,
    source_text: str = "",
) -> Optional[str]:
    """Block scripts that are clearly off-topic for a loaded telecom dataset."""
    if not GUARDRAILS_SCRIPT_SCOPE_ENABLED:
        return None
    if not _is_telecom_dataset(source_text or ""):
        return None

    script = _extract_code_block(generated_script).lower()
    if not script:
        return None

    telecom_hits = _signal_hits(script, _TELECOM_DATASET_SIGNALS)

    for phrase in _OFF_TOPIC_REFINE_SIGNALS:
        if phrase in script and telecom_hits == 0:
            return (
                f"Generated script is off-topic for the loaded telecom dataset (detected: {phrase!r}). "
                "Refined output must stay aligned with the dataset and test-script task."
            )
    return None


def validate_generated_test_script(
    generated_script: str,
    *,
    source_text: str = "",
    dataset_folder: Optional[str] = None,
    language: str = "python",
    refine_strict: bool = False,
) -> ScriptGuardrailVerdict:
    """Validate generated test scripts: syntax, traceability, and groundedness."""
    strict_refine = refine_strict and GUARDRAILS_REFINE_STRICT_OUTPUT
    findings: List[Dict[str, Any]] = []
    reasons: List[str] = []
    script = _extract_code_block(generated_script)
    lang = (language or "python").strip().lower()

    if dataset_folder:
        try:
            build_and_save_traceability_matrix(source_text, dataset_folder)
        except Exception:
            pass

    if not script:
        _add_finding(findings, "non_empty_script", "Generated script is empty.")
        return ScriptGuardrailVerdict(
            passed=False,
            blocked=True,
            reasons=["Generated script is empty."],
            findings=findings,
            metadata={"language": lang},
        )

    if lang not in {"python", "py"}:
        return ScriptGuardrailVerdict(
            passed=True,
            blocked=False,
            reasons=[],
            findings=findings,
            metadata={"language": lang, "note": "non_python_script_skipped"},
        )

    try:
        ast.parse(script)
    except SyntaxError as exc:
        detail = f"Syntax error at line {exc.lineno}: {exc.msg}"
        _add_finding(findings, "ast_parse", detail)
        return ScriptGuardrailVerdict(
            passed=False,
            blocked=True,
            reasons=[f"Syntax validation failed: {detail}"],
            findings=findings,
            metadata={"language": "python"},
        )

    trace_verdict = validate_script_traceability(
        script,
        source_text=source_text,
        dataset_folder=dataset_folder,
        require_trace_comments=strict_refine,
    )
    if trace_verdict.blocked:
        reasons.extend(trace_verdict.reasons)
        findings.extend(trace_verdict.findings)

    groundedness_verdict = validate_script_groundedness(
        script,
        source_text=source_text,
        dataset_folder=dataset_folder,
        valid_trace_mappings=trace_verdict.mappings,
        refine_strict=strict_refine,
    )
    if groundedness_verdict.blocked:
        reasons.extend(groundedness_verdict.reasons)
        findings.extend(groundedness_verdict.findings)

    scope_reason = validate_script_dataset_scope(script, source_text=source_text)
    if scope_reason:
        reasons.append(scope_reason)
        _add_finding(findings, "dataset_scope", scope_reason)

    checks_enforced = ["syntax", "traceability"]
    if not groundedness_verdict.skipped:
        checks_enforced.append("groundedness")
    if scope_reason:
        checks_enforced.append("dataset_scope")

    blocked = bool(reasons)
    metadata: Dict[str, Any] = {
        "language": "python",
        "checks_enforced": checks_enforced,
        "refine_strict": strict_refine,
        "traceability": trace_verdict.to_dict(),
        "groundedness": groundedness_verdict.to_dict(),
    }

    return ScriptGuardrailVerdict(
        passed=not blocked,
        blocked=blocked,
        reasons=list(dict.fromkeys(reasons)),
        findings=findings,
        metadata=metadata,
    )
