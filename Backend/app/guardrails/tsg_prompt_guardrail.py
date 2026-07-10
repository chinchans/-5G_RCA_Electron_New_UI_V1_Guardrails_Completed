"""Input guardrails for Test Script Generator user-editable prompts."""

from __future__ import annotations

import re
from typing import Optional

from fastapi import HTTPException

from app.guardrails.config import (
    GUARDRAILS_TSG_FORCE_LAYER2,
    GUARDRAILS_TSG_PROMPT_ENABLED,
    GUARDRAILS_TSG_REFINE_SCOPE_ENABLED,
    GUARDRAILS_TSG_REQUIRE_LAYER2,
)
from app.guardrails.input_guardrail import GuardrailVerdict, get_spec_intel_guardrail
from app.guardrails.llama_guard_service import ensure_prompt_guard_loaded

_BUILTIN_TSG_PROMPT_KEYS = frozenset({"test case", "test script", "custom"})

_TELECOM_DATASET_SIGNALS = frozenset({
    "5g", "lte", "nr", "nsa", "rrc", "nas", "attach", "detach", "ue", "enb", "gnb",
    "oran", "o-ran", "3gpp", "amf", "smf", "ran", "ngap", "s1ap", "e2ap", "handover",
    "registration", "pdu session", "bearer", "cell", "radio",
})

_REFINE_PROMPT_ALLOWED_SIGNALS = frozenset({
    "test", "script", "case", "pytest", "assert", "validate", "verify", "refine",
    "update", "fix", "add", "remove", "change", "method", "class", "function",
    "import", "def ", "procedure", "step", "expected", "log", "kpi", "tc_",
    "attach", "detach", "rrc", "nas", "5g", "lte", "nr", "ue", "oran", "iteration",
})

_OFF_TOPIC_REFINE_SIGNALS = frozenset({
    "geopolitical", "cold war", "eastern europe", "political analysis",
    "border change", "historical analysis", "world war", "economy of",
    "stock market", "cryptocurrency", "recipe", "weather forecast",
    "sourdough", "baking bread", "bake bread", "bread baking", "fermentation", "fermentation process",
    "wild yeast", "wild yeasts", "lactic acid bacteria", "baking sourdough",
    "chemical and physical changes", "gluten network", "proofing dough",
    "sci-fi", "science fiction", "cinematic history", "cinematic", "film history",
    "film archive", "film archives", "movie history", "filmmaking", "metropolis",
    "space opera", "space operas", "blockbuster", "chronological summary",
})


def should_scan_tsg_prompt(
    template_key: Optional[str],
    *,
    custom_prompt_provided: bool = False,
    save_template: bool = False,
) -> bool:
    """Return True when TSG prompt text should run guardrails before use."""
    if not GUARDRAILS_TSG_PROMPT_ENABLED:
        return False
    if save_template:
        return bool((template_key or "").strip())
    # UI always sends editor text as custom_prompt on Generate — scan every template
    if custom_prompt_provided:
        return True
    return (template_key or "").strip().lower() in _BUILTIN_TSG_PROMPT_KEYS


def _layer_mode_for_context(context: str) -> str:
    """Save Template → Layer 1 only; Generate/Refine → Layer 2 (Llama Guard) only."""
    if context == "tsg_save_template":
        return "layer1_only"
    if context in ("tsg_generate", "tsg_refine"):
        return "layer2_only"
    return "default"


def validate_tsg_user_prompt(
    text: str,
    *,
    context: str = "tsg_generate",
    template_key: str = "",
) -> GuardrailVerdict:
    """Run context-appropriate guardrail layer on a TSG prompt."""
    if not GUARDRAILS_TSG_PROMPT_ENABLED:
        return GuardrailVerdict(passed=True, blocked=False, layers={"enabled": False})

    if not text or not text.strip():
        return GuardrailVerdict(passed=True, blocked=False, layers={"empty": True})

    layer_mode = _layer_mode_for_context(context)
    force_layer2 = layer_mode == "layer2_only" or (
        layer_mode == "default" and GUARDRAILS_TSG_FORCE_LAYER2
    )

    if force_layer2:
        ensure_prompt_guard_loaded()

    guard = get_spec_intel_guardrail()
    return guard.scan_text(
        text,
        context=context,
        force_layer2_all_chunks=force_layer2,
        require_layer2_strict=GUARDRAILS_TSG_REQUIRE_LAYER2 if force_layer2 else False,
        layer_mode=layer_mode,
    )


def raise_if_tsg_prompt_blocked(
    verdict: GuardrailVerdict,
    *,
    template_key: str = "",
    context: str = "",
) -> None:
    """Raise HTTP 422 when prompt injection / jailbreak is detected."""
    if not verdict.blocked:
        return

    layer_mode = _layer_mode_for_context(context)
    guard = get_spec_intel_guardrail()
    findings = guard._findings_for_rejection(verdict)

    if layer_mode == "layer1_only":
        message = (
            "Prompt rejected by regex security guardrails. "
            "Remove instruction-override or suspicious text before saving the template."
        )
        blocked_by = "layer1"
    else:
        message = (
            "Prompt rejected by Llama Guard security guardrails. "
            "Remove instruction-override or data-exfiltration text and try again."
        )
        blocked_by = "layer2"

    detail = {
        "error": "prompt_blocked_by_guardrails",
        "message": message,
        "blocked_by": blocked_by,
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
    raise_if_tsg_prompt_blocked(verdict, template_key=template_key, context=context)


def _signal_hits(text: str, signals: frozenset) -> int:
    lowered = (text or "").lower()
    hits = 0
    for signal in signals:
        if len(signal) <= 3:
            if re.search(rf"\b{re.escape(signal)}\b", lowered):
                hits += 1
        elif signal in lowered:
            hits += 1
    return hits


def _is_telecom_dataset(text: str) -> bool:
    return _signal_hits(text, _TELECOM_DATASET_SIGNALS) >= 2


def validate_refine_prompt_scope(
    new_prompt: str,
    *,
    text_content: str = "",
    previous_response: Optional[str] = None,
) -> Optional[str]:
    """Return a block reason when a refine prompt is clearly off-topic for the loaded dataset."""
    if not GUARDRAILS_TSG_REFINE_SCOPE_ENABLED:
        return None

    dataset = (text_content or "") + "\n" + (previous_response or "")
    if not _is_telecom_dataset(dataset):
        return None

    prompt = (new_prompt or "").strip()
    if not prompt:
        return None

    lowered = prompt.lower()
    for phrase in _OFF_TOPIC_REFINE_SIGNALS:
        if phrase in lowered:
            return (
                f"New prompt is off-topic for this 5G/telecom workbench (detected: {phrase!r}). "
                "Refine prompts must request test-script or test-case changes aligned with the loaded dataset."
            )

    if _signal_hits(prompt, _REFINE_PROMPT_ALLOWED_SIGNALS | _TELECOM_DATASET_SIGNALS) == 0:
        return (
            "New prompt does not appear to request test-script or telecom test changes for the loaded dataset. "
            "Ask to update, validate, or extend the generated test script instead."
        )
    return None


def validate_refine_prompt_or_raise(
    new_prompt: str,
    *,
    text_content: str = "",
    previous_response: Optional[str] = None,
    template_key: str = "Refine",
) -> None:
    """Validate refine prompt scope and raise if blocked."""
    reason = validate_refine_prompt_scope(
        new_prompt,
        text_content=text_content,
        previous_response=previous_response,
    )
    if not reason:
        return

    detail = {
        "error": "prompt_blocked_by_guardrails",
        "message": reason,
        "blocked_by": "refine_scope",
        "template_key": template_key,
        "reasons": [reason],
        "guardrails": {
            "passed": False,
            "blocked": True,
            "layers": {"refine_scope": True},
            "reasons": [reason],
        },
        "findings": [
            {
                "layer": "refine_scope",
                "check": "dataset_alignment",
                "severity": "error",
                "detail": reason,
            }
        ],
    }
    raise HTTPException(status_code=422, detail=detail)
