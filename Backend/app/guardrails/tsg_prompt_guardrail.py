"""Input guardrails for Test Script Generator user-editable prompts."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from app.guardrails.config import GUARDRAILS_TSG_FORCE_LAYER2, GUARDRAILS_TSG_PROMPT_ENABLED
from app.guardrails.input_guardrail import GuardrailVerdict, get_spec_intel_guardrail

_TSG_SCAN_TEMPLATE_KEYS = frozenset({"test case", "custom"})


def should_scan_tsg_prompt(template_key: Optional[str]) -> bool:
    """Return True when the template is user-editable on the TSG test-case flow."""
    if not GUARDRAILS_TSG_PROMPT_ENABLED:
        return False
    return (template_key or "").strip().lower() in _TSG_SCAN_TEMPLATE_KEYS


def validate_tsg_user_prompt(
    text: str,
    *,
    context: str = "tsg_generate",
    template_key: str = "",
) -> GuardrailVerdict:
    """Run layered injection scan on a TSG prompt (modified template, refine, save)."""
    if not GUARDRAILS_TSG_PROMPT_ENABLED:
        return GuardrailVerdict(passed=True, blocked=False, layers={"enabled": False})

    if not text or not text.strip():
        return GuardrailVerdict(passed=True, blocked=False, layers={"empty": True})

    guard = get_spec_intel_guardrail()
    return guard.scan_text(
        text,
        context=context,
        force_layer2_all_chunks=GUARDRAILS_TSG_FORCE_LAYER2,
    )


def raise_if_tsg_prompt_blocked(
    verdict: GuardrailVerdict,
    *,
    template_key: str = "",
) -> None:
    """Raise HTTP 422 when prompt injection / jailbreak is detected."""
    if not verdict.blocked:
        return

    guard = get_spec_intel_guardrail()
    findings = guard._findings_for_rejection(verdict)
    detail = {
        "error": "prompt_blocked_by_guardrails",
        "message": (
            "Prompt rejected by input security guardrails. "
            "Remove instruction-override or data-exfiltration text and try again."
        ),
        "template_key": template_key or None,
        "reasons": verdict.reasons,
        "guardrails": verdict.to_dict(),
        "findings": findings,
    }
    raise HTTPException(status_code=422, detail=detail)


def validate_tsg_prompt_or_raise(
    text: str,
    *,
    context: str,
    template_key: str = "",
) -> None:
    """Validate prompt text and raise if blocked."""
    verdict = validate_tsg_user_prompt(text, context=context, template_key=template_key)
    raise_if_tsg_prompt_blocked(verdict, template_key=template_key)
