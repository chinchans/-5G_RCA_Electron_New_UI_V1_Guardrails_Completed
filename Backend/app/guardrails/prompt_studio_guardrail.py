"""Input guardrails for Prompt Studio template create / save."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.guardrails.config import (
    GUARDRAILS_PROMPT_STUDIO_ENABLED,
    GUARDRAILS_PROMPT_STUDIO_REQUIRE_LAYER2,
    GUARDRAILS_PROMPT_STUDIO_SCOPE_ENABLED,
    GUARDRAILS_TSG_FORCE_LAYER2,
)
from app.guardrails.input_guardrail import GuardrailVerdict, get_spec_intel_guardrail
from app.guardrails.llama_guard_service import ensure_prompt_guard_loaded
from app.guardrails.tsg_prompt_guardrail import (
    _OFF_TOPIC_REFINE_SIGNALS,
    _TELECOM_DATASET_SIGNALS,
    _signal_hits,
)

_TEMPLATE_NAME_RE = re.compile(r"^[\w][\w\s\-]{0,79}$")

_PLACEHOLDER_RE = re.compile(
    r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_\-]*)\s*\}\}"
    r"|\{\s*([a-zA-Z_][a-zA-Z0-9_\-]*)\s*\}"
    r"|<([A-Z][A-Z0-9_\-]*)>"
)

_SHELL_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\$\([^)]{0,200}\)"),
    re.compile(r"`[^`\n]{1,200}`"),
    re.compile(r";\s*rm\s+-[a-z]*f"),
    re.compile(r"\|\s*(?:bash|sh|zsh|cmd|powershell)\b", re.I),
    re.compile(r"&&\s*(?:sudo|rm|curl|wget|chmod|chown|mkfs)\b", re.I),
    re.compile(r">\s*/etc/"),
    re.compile(r"\b(?:wget|curl)\s+https?://", re.I),
)

_PROMPT_STUDIO_ALLOWED_SIGNALS = frozenset({
    "test", "script", "case", "rca", "root cause", "bug", "fix", "patch", "log",
    "5g", "lte", "nr", "nsa", "rrc", "nas", "attach", "detach", "ue", "gnb",
    "oran", "o-ran", "3gpp", "amf", "smf", "ran", "ngap", "handover",
    "registration", "pdu session", "telecom", "oai", "openair", "code",
    "analyze", "analysis", "validate", "verify", "prompt", "template",
    "developer", "tester", "analyst", "kpi", "signaling", "procedure",
})


@dataclass
class PromptStudioGuardrailResult:
    passed: bool
    blocked: bool
    messages: List[str] = field(default_factory=list)
    checks: List[Dict[str, Any]] = field(default_factory=list)
    layers: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "messages": self.messages,
            "checks": self.checks,
            "layers": self.layers,
        }


def _add_check(
    checks: List[Dict[str, Any]],
    *,
    check_id: str,
    passed: bool,
    detail: str,
    severity: str = "error",
) -> None:
    checks.append({
        "check": check_id,
        "passed": passed,
        "severity": severity if not passed else "info",
        "detail": detail,
    })


def _extract_placeholders(text: str) -> List[str]:
    names: List[str] = []
    for match in _PLACEHOLDER_RE.finditer(text or ""):
        name = next((g for g in match.groups() if g), None)
        if name and name not in names:
            names.append(name)
    return names


def _shell_injection_hits(text: str) -> List[str]:
    hits: List[str] = []
    for pattern in _SHELL_INJECTION_PATTERNS:
        if pattern.search(text or ""):
            hits.append(pattern.pattern)
    return hits


def validate_template_structure(
    template_name: str,
    template_content: str,
) -> Optional[str]:
    """Return block reason when template name/content structure is invalid."""
    name = (template_name or "").strip()
    content = (template_content or "").strip()

    if not name:
        return "Template name is required."
    if not _TEMPLATE_NAME_RE.match(name):
        return (
            "Template name must use letters, numbers, spaces, or hyphens only "
            "(no shell metacharacters)."
        )

    for hit in _shell_injection_hits(name):
        return "Template name contains executable shell patterns and was rejected."

    if not content:
        return "Template prompt content is required."

    # Placeholders are optional. When present, reject unsafe / shell-like names.
    placeholders = _extract_placeholders(content)

    for hit in _shell_injection_hits(content):
        return (
            "Template prompt contains executable shell injection patterns "
            "(e.g. $(...), backticks, piped bash). Remove them before saving."
        )

    for placeholder in placeholders:
        lowered = placeholder.lower()
        if lowered in {"cmd", "command", "shell", "exec", "eval", "system"}:
            return (
                f"Placeholder {{{placeholder}}} is not allowed — "
                "use descriptive telecom/RCA names instead."
            )
    return None


def validate_prompt_studio_scope(
    template_content: str,
    *,
    reference_doc: str = "",
) -> Optional[str]:
    """Return block reason when prompt is off-topic for telecom / RCA / testing."""
    if not GUARDRAILS_PROMPT_STUDIO_SCOPE_ENABLED:
        return None

    blob = f"{template_content or ''}\n{reference_doc or ''}".strip()
    if not blob:
        return None

    lowered = blob.lower()
    for phrase in _OFF_TOPIC_REFINE_SIGNALS:
        if phrase in lowered:
            return (
                f"Template is off-topic for this telecom/RCA workbench (detected: {phrase!r}). "
                "Prompts must target 5G testing, RCA, bug analysis, or code validation."
            )

    if _signal_hits(blob, _TELECOM_DATASET_SIGNALS) > 0:
        return None
    if _signal_hits(blob, _PROMPT_STUDIO_ALLOWED_SIGNALS) > 0:
        return None

    return (
        "Template does not appear related to telecom, RCA, testing, or code analysis. "
        "Include 5G/OAI/testing context in the prompt."
    )


def validate_prompt_studio_security(
    template_content: str,
    *,
    template_name: str = "",
) -> GuardrailVerdict:
    """L1 (+ optional L2) security scan for Prompt Studio templates (injection / jailbreak)."""
    text = (template_content or "").strip()
    if not text:
        return GuardrailVerdict(passed=True, blocked=False, layers={"empty": True})

    force_layer2 = bool(
        GUARDRAILS_PROMPT_STUDIO_REQUIRE_LAYER2 or GUARDRAILS_TSG_FORCE_LAYER2
    )
    if force_layer2:
        ensure_prompt_guard_loaded()

    # Default: deterministic Layer 1 for Add/Save. Opt into L2 via REQUIRE_LAYER2.
    layer_mode = "default" if force_layer2 else "layer1_only"

    guard = get_spec_intel_guardrail()
    return guard.scan_text(
        text,
        context="prompt_studio_save",
        force_layer2_all_chunks=force_layer2,
        require_layer2_strict=GUARDRAILS_PROMPT_STUDIO_REQUIRE_LAYER2 if force_layer2 else False,
        layer_mode=layer_mode,
    )


def validate_prompt_studio_template(
    *,
    template_name: str,
    template_content: str,
    role: str = "",
    reference_doc: str = "",
) -> PromptStudioGuardrailResult:
    """Run structure, scope, and L1+L2 checks for Prompt Studio Add/Save template."""
    if not GUARDRAILS_PROMPT_STUDIO_ENABLED:
        return PromptStudioGuardrailResult(passed=True, blocked=False)

    messages: List[str] = []
    checks: List[Dict[str, Any]] = []
    layers: Dict[str, Any] = {"role": role or None}

    structure_reason = validate_template_structure(template_name, template_content)
    _add_check(
        checks,
        check_id="template_structure",
        passed=structure_reason is None,
        detail=structure_reason or "Template structure is valid.",
    )
    if structure_reason:
        messages.append(structure_reason)

    scope_reason = validate_prompt_studio_scope(
        template_content,
        reference_doc=reference_doc,
    )
    _add_check(
        checks,
        check_id="telecom_scope",
        passed=scope_reason is None,
        detail=scope_reason or "Template scope is aligned with telecom/RCA/testing.",
    )
    if scope_reason:
        messages.append(scope_reason)

    security = validate_prompt_studio_security(template_content, template_name=template_name)
    layers["security"] = security.to_dict()
    if security.blocked:
        reason = (
            security.reasons[0]
            if security.reasons
            else "Prompt blocked: possible prompt injection or jailbreak detected."
        )
        messages.append(reason)
        _add_check(checks, check_id="security_l1_l2", passed=False, detail=reason)
    else:
        _add_check(
            checks,
            check_id="security_l1_l2",
            passed=True,
            detail="L1/L2 security scan passed.",
        )

    if reference_doc and reference_doc.strip():
        ref_security = validate_prompt_studio_security(reference_doc, template_name="reference_doc")
        layers["reference_security"] = ref_security.to_dict()
        if ref_security.blocked:
            reason = "Reference document blocked by security guardrails."
            messages.append(reason)
            _add_check(checks, check_id="reference_security", passed=False, detail=reason)
        else:
            _add_check(
                checks,
                check_id="reference_security",
                passed=True,
                detail="Reference document security scan passed.",
            )

    blocked = bool(messages)
    # Prefer security reasons first so Add Template shows injection clearly.
    if blocked:
        security_msgs = [
            c["detail"]
            for c in checks
            if c.get("check") in {"security_l1_l2", "reference_security"} and not c.get("passed")
        ]
        other_msgs = [m for m in messages if m not in security_msgs]
        messages = list(dict.fromkeys([*security_msgs, *other_msgs]))

    return PromptStudioGuardrailResult(
        passed=not blocked,
        blocked=blocked,
        messages=messages,
        checks=checks,
        layers=layers,
    )


def raise_if_prompt_studio_blocked(result: PromptStudioGuardrailResult) -> None:
    if not result.blocked:
        return

    guard = get_spec_intel_guardrail()
    security_layer = (result.layers or {}).get("security") or {}
    findings = security_layer.get("findings") or security_layer.get("scan", {}).get("findings") or []

    detail = {
        "error": "prompt_blocked_by_guardrails",
        "message": result.messages[0] if result.messages else "Template blocked by Prompt Studio guardrails.",
        "blocked_by": "prompt_studio",
        "reasons": result.messages,
        "guardrails": {
            "passed": False,
            "blocked": True,
            "layers": result.layers,
            "reasons": result.messages,
        },
        "findings": findings,
        "checks": result.checks,
    }
    raise HTTPException(status_code=422, detail=detail)


def validate_prompt_studio_or_raise(
    *,
    template_name: str,
    template_content: str,
    role: str = "",
    reference_doc: str = "",
) -> PromptStudioGuardrailResult:
    result = validate_prompt_studio_template(
        template_name=template_name,
        template_content=template_content,
        role=role,
        reference_doc=reference_doc,
    )
    raise_if_prompt_studio_blocked(result)
    return result
