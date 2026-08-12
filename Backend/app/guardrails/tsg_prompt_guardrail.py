"""Input guardrails for Test Script Generator user-editable prompts."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from fastapi import HTTPException

from app.guardrails.config import (
    GUARDRAIL_CLASSIFIER_MIN_CONFIDENCE,
    GUARDRAIL_CLASSIFIER_REFINE_ANCHOR_CHARS,
    GUARDRAILS_FAIL_OPEN_ON_MODEL_ERROR,
    GUARDRAILS_TSG_CLASSIFIER_ENABLED,
    GUARDRAILS_TSG_FORCE_LAYER2,
    GUARDRAILS_TSG_PROMPT_ENABLED,
    GUARDRAILS_TSG_PROMPT_EXTRACTION_ENABLED,
    GUARDRAILS_TSG_REFINE_CONTEXT_INJECT_ENABLED,
    GUARDRAILS_TSG_REFINE_SCOPE_ENABLED,
    GUARDRAILS_TSG_REQUIRE_CLASSIFIER,
    GUARDRAILS_TSG_REQUIRE_LAYER2,
)
from app.guardrails.guardrail_classifier import (
    LABEL_OUT_OF_SCOPE,
    LABEL_PROMPT_INJECTION,
    LABEL_TELECOM,
    ClassifierResult,
    WindowScanResult,
    _has_telecom_signals,
    _is_confident_label,
    _sentence_oos_veto,
    classify_prompt,
    classify_prompt_with_windows,
    ensure_guardrail_classifier_loaded,
    split_sentences,
)
from app.guardrails.prompt_extraction import (
    PromptExtractionResult,
    extract_user_prompt_payload,
    resolve_tsg_baseline_prompt,
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
    # Common follow-up intents on generated output
    "optimise", "optimize", "improve", "refactor", "cleanup", "clean up",
    "simplify", "rewrite", "polish", "enhance", "code", "output", "response",
    "explain", "describe", "summarise", "summarize", "document", "comment",
    "extend", "expand", "modify", "adjust", "tweak", "rework", "format",
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
    "lava cake", "french revolution", "plan a trip", "samsung tv",
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
    if context in ("tsg_save_template", "prompt_studio_save"):
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


def build_refine_session_anchor(
    previous_response: str = "",
    text_content: str = "",
) -> str:
    """Pick a short telecom domain anchor from the active refine session."""
    blob = (previous_response or "").strip() or (text_content or "").strip()
    if not blob:
        return ""

    max_chars = max(120, GUARDRAIL_CLASSIFIER_REFINE_ANCHOR_CHARS)
    for sentence in split_sentences(blob, limit=60):
        if _has_telecom_signals(sentence):
            return sentence[:max_chars].strip()

    # Fallback: head of prior output / dataset (often still domain-heavy JSON/test cases)
    head = " ".join(blob.split())
    return head[:max_chars].strip()


def build_refine_classifier_input(
    follow_up: str,
    *,
    previous_response: str = "",
    text_content: str = "",
) -> Dict[str, Any]:
    """Prepend parent session anchor to a follow-up prompt for intent classification."""
    follow = (follow_up or "").strip()
    if not follow:
        return {"scan_text": "", "session_active": False, "anchor_preview": ""}

    if not GUARDRAILS_TSG_REFINE_CONTEXT_INJECT_ENABLED:
        return {"scan_text": follow, "session_active": False, "anchor_preview": ""}

    anchor = build_refine_session_anchor(previous_response, text_content)
    if not anchor:
        return {"scan_text": follow, "session_active": False, "anchor_preview": ""}

    scan_text = (
        f"Active 5G/telecom Test Script Generator session context:\n{anchor}\n\n"
        f"Follow-up request for the generated output:\n{follow}"
    )
    return {
        "scan_text": scan_text,
        "session_active": True,
        "anchor_preview": anchor[:160],
    }


def _classifier_block_message(result: ClassifierResult, *, scan: Optional[WindowScanResult] = None) -> str:
    label = (result.predicted_label or "").upper()
    if label == LABEL_OUT_OF_SCOPE:
        if scan and scan.mode == "anchor_windows" and scan.blocked_window_preview:
            return (
                "Prompt rejected as out of scope: an off-topic segment was detected "
                "inside an otherwise telecom-looking request. "
                "Remove unrelated content and keep the prompt focused on 5G/telecom testing."
            )
        if scan and scan.mode == "sentence_veto" and scan.blocked_window_preview:
            return (
                "Prompt rejected as out of scope: an off-topic sentence was detected "
                f"({scan.blocked_window_preview!r}). "
                "Remove unrelated content and keep the prompt focused on 5G/telecom testing."
            )
        if scan and scan.mode == "no_telecom_anchor":
            return (
                "Prompt rejected as out of scope: no telecom/5G domain sentence was found. "
                "Include a clear 5G/telecom testing request."
            )
        return (
            "Prompt rejected as out of scope for the 5G/telecom Test Script Generator. "
            "Ask about telecom procedures, test cases, or test-script generation instead."
        )
    if label == LABEL_PROMPT_INJECTION:
        return (
            "Prompt rejected by the intent classifier as a prompt-injection / jailbreak attempt. "
            "Remove instruction-override language and retry with a telecom testing request."
        )
    return (
        f"Prompt rejected by the intent classifier (label={label}). "
        "Use a telecom / test-script related prompt."
    )


def raise_if_classifier_blocked(
    text: str,
    *,
    template_key: str = "",
    context: str = "",
    baseline_prompt: Optional[str] = None,
    previous_response: Optional[str] = None,
    text_content: Optional[str] = None,
) -> Optional[ClassifierResult]:
    """Hybrid intent guard: Layer-1 prompt extraction + Layer-2 anchor windows.

    For refine/follow-up prompts, prepend parent session telecom context before
    classification so short asks like "explain the dataset" stay in-scope.
    """
    if not GUARDRAILS_TSG_CLASSIFIER_ENABLED:
        return None
    # prompt_studio_save: Add Template uses the same windowed RoBERTa path as Generate
    if context not in ("tsg_generate", "tsg_refine", "prompt_studio_save"):
        return None
    if not text or not text.strip():
        return None

    ensure_guardrail_classifier_loaded()

    extraction: Optional[PromptExtractionResult] = None
    refine_meta: Optional[Dict[str, Any]] = None
    scan_text = text

    if context == "tsg_refine":
        # Follow-up box: inject parent session anchor; use a lightweight classifier path
        # (1-2 model calls) instead of full multi-window scanning.
        refine_meta = build_refine_classifier_input(
            text,
            previous_response=previous_response or "",
            text_content=text_content or "",
        )
        scan_text = refine_meta["scan_text"] or text

        # Catch clear off-topic follow-ups on the raw user text first (fast).
        veto = _sentence_oos_veto(split_sentences(text, limit=None), max_classifications=12)
        if veto is not None:
            veto_index, veto_sentence, veto_result = veto
            scan = WindowScanResult(
                predicted_label=LABEL_OUT_OF_SCOPE,
                confidence_score=veto_result.confidence_score,
                probabilities=veto_result.probabilities,
                available=True,
                detail="refine_followup_sentence_veto",
                blocked=True,
                mode="sentence_veto",
                sentence_count=1,
                windows_scanned=0,
                blocked_window_index=veto_index,
                blocked_window_preview=veto_sentence[:160],
                full_text=veto_result,
            )
        else:
            full = classify_prompt(scan_text)
            # RoBERTa is domain-only (telecom vs OOS); Llama Guard handles injection.
            blocked = _is_confident_label(full, LABEL_OUT_OF_SCOPE)
            # If parent session is active and the combined text is telecom, allow.
            if refine_meta.get("session_active") and _is_confident_label(full, LABEL_TELECOM):
                blocked = False
            scan = WindowScanResult(
                predicted_label=full.predicted_label,
                confidence_score=full.confidence_score,
                probabilities=full.probabilities,
                available=full.available,
                detail=(
                    "refine_context_active"
                    if refine_meta.get("session_active")
                    else "refine_standalone"
                ),
                blocked=blocked,
                mode="full_text",
                sentence_count=len(split_sentences(scan_text, limit=20)),
                windows_scanned=0,
                full_text=full,
            )
    elif GUARDRAILS_TSG_PROMPT_EXTRACTION_ENABLED:
        baseline = baseline_prompt
        if baseline is None:
            baseline = resolve_tsg_baseline_prompt(template_key)
        extraction = extract_user_prompt_payload(text, baseline)
        if extraction.mode in {"trusted_baseline", "empty"}:
            # No user delta vs trusted template → skip intent classifier.
            return ClassifierResult(
                predicted_label=LABEL_TELECOM,
                confidence_score=1.0,
                probabilities={
                    LABEL_TELECOM: 1.0,
                    LABEL_OUT_OF_SCOPE: 0.0,
                    LABEL_PROMPT_INJECTION: 0.0,
                },
                available=True,
                detail=f"extraction_{extraction.mode}",
            )
        scan_text = extraction.payload or text

    if context != "tsg_refine":
        scan = classify_prompt_with_windows(scan_text)

    detail_bits = [scan.detail or "ok"]
    if extraction is not None:
        detail_bits.append(f"extraction:{extraction.mode}")
    if refine_meta is not None:
        detail_bits.append(
            "refine_context:" + ("active" if refine_meta.get("session_active") else "standalone")
        )
    scan.detail = "|".join(detail_bits)
    result = scan.to_classifier_result()

    def _classifier_payload() -> Dict[str, Any]:
        payload = scan.to_dict()
        if extraction is not None:
            payload["extraction"] = extraction.to_dict()
        if refine_meta is not None:
            payload["refine_context"] = {
                "session_active": bool(refine_meta.get("session_active")),
                "anchor_preview": refine_meta.get("anchor_preview") or "",
            }
        return payload

    if not result.available:
        if GUARDRAILS_TSG_REQUIRE_CLASSIFIER or not GUARDRAILS_FAIL_OPEN_ON_MODEL_ERROR:
            detail = {
                "error": "prompt_blocked_by_guardrails",
                "message": (
                    "Prompt could not be verified by the fine-tuned intent classifier. "
                    "Classifier model is unavailable."
                ),
                "blocked_by": "intent_classifier",
                "template_key": template_key or None,
                "reasons": [result.detail or "classifier_unavailable"],
                "guardrails": {
                    "passed": False,
                    "blocked": True,
                    "layers": {"intent_classifier": _classifier_payload()},
                    "reasons": [result.detail or "classifier_unavailable"],
                },
                "findings": [
                    {
                        "layer": "intent_classifier",
                        "check": "model_availability",
                        "severity": "error",
                        "detail": result.detail or "classifier_unavailable",
                    }
                ],
                "classifier": _classifier_payload(),
            }
            raise HTTPException(status_code=422, detail=detail)
        return result

    if not scan.blocked:
        return result

    label = (result.predicted_label or "").upper()
    # Domain classifier only enforces OUT_OF_SCOPE; injection is Llama Guard's job.
    if label != LABEL_OUT_OF_SCOPE:
        return result

    if result.confidence_score < GUARDRAIL_CLASSIFIER_MIN_CONFIDENCE:
        if not GUARDRAILS_TSG_REQUIRE_CLASSIFIER:
            return result

    message = _classifier_block_message(result, scan=scan)
    findings = [
        {
            "layer": "intent_classifier",
            "check": "intent_label",
            "severity": "error",
            "detail": message,
            "predicted_label": label,
            "confidence_score": result.confidence_score,
            "probabilities": result.probabilities,
            "mode": scan.mode,
            "anchor_index": scan.anchor_index,
            "blocked_window_index": scan.blocked_window_index,
            "extraction_mode": extraction.mode if extraction else None,
            "refine_session_active": (
                bool(refine_meta.get("session_active")) if refine_meta else None
            ),
        }
    ]
    detail = {
        "error": "prompt_blocked_by_guardrails",
        "message": message,
        "blocked_by": "intent_classifier",
        "template_key": template_key or None,
        "reasons": [message],
        "guardrails": {
            "passed": False,
            "blocked": True,
            "layers": {"intent_classifier": _classifier_payload()},
            "reasons": [message],
        },
        "findings": findings,
        "classifier": _classifier_payload(),
    }
    raise HTTPException(status_code=422, detail=detail)


def validate_tsg_prompt_or_raise(
    text: str,
    *,
    context: str,
    template_key: str = "",
    baseline_prompt: Optional[str] = None,
    previous_response: Optional[str] = None,
    text_content: Optional[str] = None,
) -> None:
    """Validate prompt text (security + fine-tuned intent) and raise if blocked."""
    verdict = validate_tsg_user_prompt(text, context=context, template_key=template_key)
    raise_if_tsg_prompt_blocked(verdict, template_key=template_key, context=context)
    raise_if_classifier_blocked(
        text,
        template_key=template_key,
        context=context,
        baseline_prompt=baseline_prompt,
        previous_response=previous_response,
        text_content=text_content,
    )


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
    """Return a block reason when a refine prompt is clearly off-topic.

    With an active generated output, do not require brittle keyword hits
    (\"update/validate/extend\"). Relevance is handled by the context-injected
    intent classifier; this layer only blocks explicit off-topic phrases.
    """
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
                "Refine prompts must request changes related to the generated test output or dataset."
            )

    # Active follow-up session: prior generated output provides context.
    # Allow natural requests (\"optimise the code\", \"explain this\") unless off-topic.
    if (previous_response or "").strip():
        return None

    # Cold refine with no prior output still needs a clear workbench signal.
    if _signal_hits(prompt, _REFINE_PROMPT_ALLOWED_SIGNALS | _TELECOM_DATASET_SIGNALS) == 0:
        return (
            "New prompt does not appear related to the loaded telecom dataset or generated test output. "
            "Ask to update, improve, explain, or extend the generated result."
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
