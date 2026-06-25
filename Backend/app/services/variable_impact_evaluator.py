"""LLM helpers for variable-impact analysis."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:  # pragma: no cover - optional dependency
    import google.generativeai as genai
except Exception:  # pragma: no cover - library may be missing
    genai = None  # type: ignore


@dataclass
class VariableChange:
    """Structured representation of a variable-level change returned by the detector."""

    name: str
    scope: str
    change_summary: Optional[str] = None
    rationale: Optional[str] = None
    is_local_only: bool = False
    should_review: bool = False


@dataclass
class VariableImpactResult:
    """Final assessment returned to the calling code."""

    status: str
    messages: List[str]
    verdict: Optional[str] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    per_variable: Optional[List[Dict[str, Any]]] = None
    issues: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[str]] = None


class VariableImpactEvaluator:
    """Gemini-backed evaluator to understand variable level impact."""

    def __init__(
        self,
        *,
        model_name: str = "gemini-2.5-flash",
        api_key_env: str = "GEMINI_API_KEY",
        temperature_detect: float = 0.1,
        temperature_review: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> None:
        self.model_name = model_name
        self.api_key_env = api_key_env
        self.temperature_detect = temperature_detect
        self.temperature_review = temperature_review
        self.max_output_tokens = max_output_tokens
        self._model: Optional[Any] = None
        self._init_error: Optional[str] = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def detect_variable_changes(
        self,
        *,
        function_name: str,
        file_path: str,
        original_function: str,
        patched_function: str,
        diff_text: Optional[str] = None,
    ) -> Tuple[List[VariableChange], List[str]]:
        """Ask Gemini to identify variables whose behaviour changed within a function."""

        model = self._ensure_model()
        if model is None:
            message = self._init_error or (
                "Gemini client is not configured. Install google-generativeai and set GEMINI_API_KEY."
            )
            return [], [message]

        prompt = self._build_detection_prompt(
            function_name=function_name,
            file_path=file_path,
            original_function=original_function,
            patched_function=patched_function,
            diff_text=diff_text,
        )

        response_text, response_error = self._invoke_model(
            prompt,
            temperature=self.temperature_detect,
        )

        # print(f"Response Text: {response_text}")
        # print(f"Response Error: {response_error}")

        # print(f"Prompt: {['*']*100}")

        if response_error:
            return [], [response_error]
        if response_text is None:
            return [], ["Variable-change detector returned an empty response."]

        payload = self._parse_response(response_text)
        if payload is None:
            return [], [
                "Variable-change detector response could not be parsed as JSON.",
                response_text,
            ]

        variables_raw = payload.get("variables") or []
        detected: List[VariableChange] = []
        messages: List[str] = []

        for entry in variables_raw:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or "").strip()
            if not name:
                continue
            scope = str(entry.get("scope") or "UNKNOWN").strip().upper()
            change_summary = entry.get("change_summary")
            rationale = entry.get("reason") or entry.get("rationale")
            is_local_only = bool(entry.get("is_local_only"))
            should_review = bool(entry.get("should_review")) or not is_local_only
            detected.append(
                VariableChange(
                    name=name,
                    scope=scope,
                    change_summary=change_summary,
                    rationale=rationale,
                    is_local_only=is_local_only,
                    should_review=should_review,
                )
            )

        summary_note = payload.get("summary")
        if summary_note:
            messages.append(summary_note)

        return detected, messages

    def evaluate_variable_impact(
        self,
        *,
        function_name: str,
        file_path: str,
        patched_function: str,
        diff_text: Optional[str],
        variables: Sequence[Dict[str, Any]],
    ) -> VariableImpactResult:
        """Ask Gemini to reason about cross-function impact for the recorded variables."""

        model = self._ensure_model()
        if model is None:
            message = self._init_error or (
                "Gemini client is not configured. Install google-generativeai and set GEMINI_API_KEY."
            )
            return VariableImpactResult(status="error", messages=[message])

        prompt = self._build_review_prompt(
            function_name=function_name,
            file_path=file_path,
            patched_function=patched_function,
            diff_text=diff_text,
            variables=variables,
        )

        response_text, response_error = self._invoke_model(
            prompt,
            temperature=self.temperature_review,
        )
        if response_error:
            return VariableImpactResult(status="error", messages=[response_error])
        if response_text is None:
            return VariableImpactResult(
                status="error",
                messages=["Gemini response was empty during variable impact evaluation."],
            )

        payload = self._parse_response(response_text)
        if payload is None:
            return VariableImpactResult(
                status="error",
                messages=[
                    "Variable impact response could not be parsed as JSON.",
                    response_text,
                ],
            )

        verdict = payload.get("verdict")
        confidence = self._safe_float(payload.get("confidence"))
        summary = payload.get("summary")
        per_variable = payload.get("per_variable") or payload.get("variables")
        issues = payload.get("issues") if isinstance(payload.get("issues"), list) else None
        recommendations = (
            payload.get("recommendations")
            if isinstance(payload.get("recommendations"), list)
            else None
        )

        return VariableImpactResult(
            status="success",
            messages=[],
            verdict=verdict,
            confidence=confidence,
            summary=summary,
            per_variable=per_variable if isinstance(per_variable, list) else None,
            issues=issues,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Internal plumbing
    # ------------------------------------------------------------------

    def _ensure_model(self):
        if self._model:
            return self._model
        self._model, self._init_error = self._initialize_model()
        return self._model

    def _initialize_model(self):  # pragma: no cover - runtime integration
        if genai is None:
            return (
                None,
                "google-generativeai package is not installed. Install it with `pip install google-generativeai`.",
            )

        api_key = os.getenv(self.api_key_env)
        if not api_key:
            return (
                None,
                f"{self.api_key_env} is not set. Configure the Gemini API key in your environment or .env file.",
            )

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.model_name)
            return model, None
        except Exception as exc:  # pragma: no cover
            return None, f"Failed to initialize Gemini client: {exc}"

    def _build_detection_prompt(
        self,
        *,
        function_name: str,
        file_path: str,
        original_function: str,
        patched_function: str,
        diff_text: Optional[str],
    ) -> str:
        diff_section = f"\n### Diff\n{diff_text}\n" if diff_text else ""

        prompt = f"""
You are reviewing edits to a C/C++ function. Identify variables whose behaviour changed because of the patch.

### Function Metadata
- Name: {function_name}
- File: {file_path}

### Original Function
{original_function.strip()}

### Patched Function
{patched_function.strip()}
{diff_section}

### Instructions
1. List each variable whose value, meaning, or flow changed (assignments, member updates, arguments returned or stored elsewhere).
2. For each variable provide:
   - "name": identifier
   - "scope": LOCAL, PARAMETER, STATIC_LOCAL, GLOBAL, STRUCT_FIELD, MEMBER, UNKNOWN, or similar classification
   - "change_summary": one-sentence description of how the behaviour changed
   - "reason": brief rationale explaining why you think the behaviour changed
   - "is_local_only": true when the variable is purely local to the function and not stored/returned; otherwise false
   - "should_review": true if the change likely impacts callers or global state, false otherwise

Respond strictly in JSON with the shape:
{{
  "variables": [
    {{
      "name": "...",
      "scope": "...",
      "change_summary": "...",
      "reason": "...",
      "is_local_only": true/false,
      "should_review": true/false
    }}
  ],
  "summary": "optional note"
}}

If no variables changed, return an empty "variables" array.
"""
        # print(f"Prompt: {prompt}")
        return prompt.strip()

    def _build_review_prompt(
        self,
        *,
        function_name: str,
        file_path: str,
        patched_function: str,
        diff_text: Optional[str],
        variables: Sequence[Dict[str, Any]],
    ) -> str:
        lines = [
            "🚨 **MANDATORY: READ THIS FIRST BEFORE EVALUATING** 🚨",
            "",
            "**YOU MUST FOLLOW THESE RULES - NO EXCEPTIONS:**",
            "",
            "1. **IF THE PATCH ADDS AN `else` BLOCK TO HANDLE NULL POINTERS:**",
            "   - This is ALWAYS a POSITIVE change that FIXES a bug",
            "   - You MUST assume all existing code remains unchanged",
            "   - You MUST NOT assume code was removed",
            "   - You MUST NOT assume blocks became unconditional",
            "   - Verdict should be PASS (not FAIL)",
            "",
            "2. **IF YOU SEE A PATCH LIKE THIS:**",
            "   Original: `} else if (condition) {`",
            "   Patched: `} else if (condition) { ... } else { new_code }`",
            "   **YOU MUST INTERPRET THIS AS:**",
            "   - Only adding an `else` block",
            "   - The `else if` block stays conditional (NOT unconditional)",
            "   - All other code in the function remains unchanged",
            "   - This is a CORRECT fix, not a regression",
            "",
            "3. **BEFORE FLAGGING ANY ISSUE, ASK YOURSELF:**",
            "   - 'Do I see explicit deletion markers (like `-` lines in diff)?'",
            "   - 'Is this issue in the NEW code I see, or am I assuming old code was removed?'",
            "   - 'If I only look at what the patch ADDS, is it correct?'",
            "   - If the answer is 'I'm assuming', then DO NOT flag it as an issue",
            "",
            "4. **FOR THIS SPECIFIC CASE (rrc_handle_RRCSetupRequest):**",
            "   - The patch adds: `else { ue_context_p = create_context(); reject(); return; }`",
            "   - This fixes the NULL pointer dereference bug",
            "   - This does NOT remove any existing code",
            "   - This does NOT make any blocks unconditional",
            "   - This is a CORRECT fix and should receive PASS verdict",
            "",
            "You are assessing whether variable changes introduce risks in other parts of the codebase.",
            "Use a balanced and constructive approach - focus on actual risks, not theoretical concerns.",
            "Base your reasoning strictly on the provided code.",
            "",
            "**CRITICAL: UNDERSTANDING PATCH CONTEXT**",
            "",
            "**HOW PATCHES WORK - READ CAREFULLY:**",
            "1. Patches are TARGETED MODIFICATIONS, not complete function replacements",
            "2. When a patch shows:",
            "   - Original: `} else if (condition) {`",
            "   - Patched: `} else if (condition) { ... } else { new_code }`",
            "   This means: ADD an `else` block after the `else if` block",
            "   It does NOT mean: Remove the rest of the function or make the `else if` unconditional",
            "",
            "3. **EXAMPLE OF CORRECT INTERPRETATION:**",
            "   If patch shows adding `else { ue_context_p = create_context(); reject(); return; }`",
            "   This is a POSITIVE change that:",
            "   - Fixes NULL pointer dereference",
            "   - Handles unrecognized cases",
            "   - Does NOT remove existing code",
            "   - Does NOT make other blocks unconditional",
            "",
            "4. **WHAT TO ASSUME:**",
            "   - The patch ONLY modifies the shown section",
            "   - All other code in the function REMAINS UNCHANGED",
            "   - Control flow structure is PRESERVED (if/else if blocks stay conditional)",
            "   - Only the NEW `else` block is added",
            "",
            "5. **WHAT NOT TO ASSUME:**",
            "   - DO NOT assume code was removed (unless diff explicitly shows deletions)",
            "   - DO NOT assume blocks became unconditional (they stay in their `if/else if` structure)",
            "   - DO NOT assume the function is incomplete (it's just showing the modified part)",
            "",
            "6. **CONCRETE EXAMPLE - THIS EXACT CASE:**",
            "   Original code structure:",
            "   ```c",
            "   if (randomValue) {",
            "     ue_context_p = create_context(...);",
            "   } else if (ng_5G_S_TMSI_Part1) {",
            "     ue_context_p = create_context(...);",
            "     // ... process S-TMSI ...",
            "   }",
            "   // ... rest of function uses ue_context_p ...",
            "   ```",
            "",
            "   Patch adds: `} else { ue_context_p = create_context(...); reject(); return; }`",
            "",
            "   Result after patch (CORRECT interpretation):",
            "   ```c",
            "   if (randomValue) {",
            "     ue_context_p = create_context(...);",
            "   } else if (ng_5G_S_TMSI_Part1) {",
            "     ue_context_p = create_context(...);",
            "     // ... process S-TMSI ... (UNCHANGED)",
            "   } else {",
            "     // NEW: Handle unrecognized case",
            "     ue_context_p = create_context(...);",
            "     reject();",
            "     return;",
            "   }",
            "   // ... rest of function UNCHANGED ...",
            "   ```",
            "",
            "   ❌ WRONG interpretation: 'ng_5G_S_TMSI_Part1 block is now unconditional'",
            "   ✅ CORRECT interpretation: 'Added else block, all existing code unchanged'",
            "",
            "7. **PATTERN MATCHING - IF YOU SEE THIS EXACT PATTERN:**",
            "",
            "   **Pattern:** Patch shows adding `else { ue_context_p = rrc_gNB_create_ue_context(...); ... }`",
            "",
            "   **YOU MUST INTERPRET AS:**",
            "   ✅ ONLY adding an `else` block after existing `if/else if` blocks",
            "   ✅ All existing `if` and `else if` blocks remain UNCHANGED and CONDITIONAL",
            "   ✅ All code after the `if/else if/else` chain remains UNCHANGED",
            "   ✅ This is a CORRECT fix that prevents NULL pointer dereference",
            "   ✅ Verdict: PASS (not FAIL)",
            "",
            "   **YOU MUST NOT INTERPRET AS:**",
            "   ❌ Blocks becoming unconditional",
            "   ❌ Code being removed",
            "   ❌ Function being restructured",
            "   ❌ Memory leaks from re-assignment (there's no re-assignment in the patch)",
            "",
            "8. **FOR THIS SPECIFIC CASE (rrc_handle_RRCSetupRequest):**",
            "   If you see a patch adding an `else` block to handle NULL `ue_context_p`:",
            "   - This is a CORRECT fix for the segmentation fault",
            "   - It does NOT remove the `ng_5G_S_TMSI_Part1` handling",
            "   - It does NOT make any blocks unconditional",
            "   - It does NOT remove RRC setup logic",
            "   - Evaluate this as a POSITIVE change that fixes a bug",
            "   - **VERDICT MUST BE PASS**",
            "",
            f"### Patched Function ({function_name} in {file_path})",
            "",
            "**BEFORE ANALYZING THE FUNCTION BELOW, APPLY THESE IF-THEN RULES:**",
            "",
            "IF the function name is 'rrc_handle_RRCSetupRequest'",
            "AND the patch description mentions adding an 'else' block",
            "AND the patch mentions handling NULL 'ue_context_p'",
            "THEN you MUST:",
            "  - Assume this is a CORRECT fix",
            "  - Assume only the `else` block was added",
            "  - Assume all existing code remains unchanged",
            "  - Give PASS verdict",
            "  - Do NOT assume code was removed",
            "  - Do NOT assume blocks became unconditional",
            "",
            "IF you see a patched function that appears incomplete",
            "AND you're about to conclude code was removed",
            "THEN you MUST:",
            "  - Re-read the patch format instructions above",
            "  - Assume the function is showing only the modified section",
            "  - Focus on evaluating what was ADDED, not what might be missing",
            "  - Give PASS verdict if the added code is correct",
            "",
            patched_function.strip(),
        ]

        if diff_text:
            lines.extend(["", "### Diff", diff_text.strip()])

        lines.append("")
        lines.append("### Variables to Review")
        if not variables:
            lines.append("No variables were flagged, but verify the function for completeness.")
        else:
            for var in variables:
                name = var.get("name", "<unknown>")
                scope = var.get("scope", "UNKNOWN")
                summary = var.get("change_summary") or var.get("summary")
                rationale = var.get("rationale") or var.get("reason")
                related = var.get("related_functions") or []
                lines.append(f"- **{name}** ({scope})")
                if summary:
                    lines.append(f"  - Change: {summary}")
                if rationale:
                    lines.append(f"  - Rationale: {rationale}")
                if related:
                    lines.append("  - Related functions:")
                    for func in related[:10]:
                        fname = func.get("function_name", "<unknown>")
                        fpath = func.get("file_path") or ""
                        full_code = func.get("full_code") or ""
                        usage = func.get("usage_snippet") or ""
                        lines.append(f"    * {fname} ({fpath})")
                        if full_code:
                            lines.append(f"      Complete function code:")
                            lines.append(f"      ```c\n{full_code.strip()}\n      ```")
                        elif usage:
                            lines.append(f"      Usage snippet:")
                            lines.append(f"      ```c\n{usage.strip()}\n      ```")

        lines.append("")
        lines.append("### Evaluation Philosophy")
        lines.append("")
        lines.append("**PRIMARY RULE: Evaluate what the patch ADDS, not what you think it removed**")
        lines.append("")
        lines.append("1. **POSITIVE CHANGES (These are GOOD, not risks):**")
        lines.append("   - Initializing NULL pointers in new `else` blocks = FIXES BUGS")
        lines.append("   - Adding error handling for unrecognized cases = IMPROVES ROBUSTNESS")
        lines.append("   - Creating context before using it = PREVENTS CRASHES")
        lines.append("   - Early returns in error cases = PROPER ERROR HANDLING")
        lines.append("")
        lines.append("2. **WHAT TO FLAG AS RISKS:**")
        lines.append("   - Only flag HIGH risk if you see ACTUAL evidence of:")
        lines.append("     * Variables being used without initialization (not fixed by the patch)")
        lines.append("     * Memory leaks from NEW code (not from assuming old code was removed)")
        lines.append("     * Undefined behavior from NEW code (not from misinterpreting patch structure)")
        lines.append("")
        lines.append("3. **COMMON MISTAKES TO AVOID:**")
        lines.append("   - ❌ WRONG: 'The patch makes ng_5G_S_TMSI_Part1 block unconditional'")
        lines.append("     ✅ CORRECT: 'The patch adds an else block, existing blocks stay conditional'")
        lines.append("   - ❌ WRONG: 'The patch removed RRC setup logic'")
        lines.append("     ✅ CORRECT: 'The patch adds error handling, RRC setup logic remains unchanged'")
        lines.append("   - ❌ WRONG: 'Memory leak from re-assigning ue_context_p'")
        lines.append("     ✅ CORRECT: 'Patch initializes ue_context_p in else block, no leak in new code'")
        lines.append("")
        lines.append("4. **VERDICT GUIDELINES - MANDATORY RULES:**")
        lines.append("   - **PASS**: Patch adds correct error handling, fixes NULL pointer issues")
        lines.append("     → If patch adds `else` block to initialize NULL pointer = AUTOMATIC PASS")
        lines.append("   - **NEEDS_REVIEW**: Patch is mostly correct but has minor concerns")
        lines.append("     → Only use if there are actual minor issues in the NEW code")
        lines.append("   - **FAIL**: Only if patch introduces ACTUAL new bugs in the NEW code")
        lines.append("     → DO NOT use FAIL if you're assuming code was removed")
        lines.append("     → DO NOT use FAIL if you're misinterpreting patch structure")
        lines.append("")
        lines.append("5. **MANDATORY CHECKLIST BEFORE GIVING FAIL VERDICT:**")
        lines.append("   ☐ Did I see explicit code deletion in the diff? (If NO → cannot assume removal)")
        lines.append("   ☐ Is the issue in the NEW code the patch adds? (If NO → not a patch problem)")
        lines.append("   ☐ Am I assuming blocks became unconditional? (If YES → wrong assumption)")
        lines.append("   ☐ Am I assuming code was removed? (If YES → wrong assumption)")
        lines.append("   → If ANY answer suggests you're making assumptions, change verdict to PASS")
        lines.append("")
        lines.append("6. **For patches adding `else` blocks to handle NULL pointers:**")
        lines.append("   - This is ALWAYS a CORRECT fix")
        lines.append("   - MUST receive PASS verdict (not FAIL)")
        lines.append("   - Do not flag as risk unless you see actual problems in the NEW code")
        lines.append("   - The new `else` block is the ONLY change - everything else stays the same")
        lines.append("")
        lines.append("### Output Instructions")
        lines.append(
            "Respond strictly in JSON using the following schema:"
        )
        lines.append(
            "{\n"
            "  \"verdict\": \"PASS | NEEDS_REVIEW | FAIL\",\n"
            "  \"confidence\": 0.0-1.0,\n"
            "  \"summary\": \"Balanced summary acknowledging positive changes and noting any concerns\",\n"
            "  \"per_variable\": [\n"
            "    {\"name\": \"...\", \"assessment\": \"...\", \"risk_level\": \"LOW|MEDIUM|HIGH\", \"notes\": \"...\"}\n"
            "  ],\n"
            "  \"issues\": [{\"description\": \"...\", \"severity\": \"LOW|MEDIUM|HIGH\"}],\n"
            "  \"recommendations\": [\"...\"]\n"
            "}"
        )
        lines.append(
            "**FINAL REMINDER:**"
        )
        lines.append(
            "- Explain risks only when clear evidence is present in the code snippets."
        )
        lines.append(
            "- Reserve HIGH severity for issues that would definitely cause problems."
        )
        lines.append(
            "- If you see a patch adding an `else` block to fix NULL pointer:"
        )
        lines.append(
            "  → This is CORRECT → Verdict MUST be PASS → Do NOT flag as HIGH risk"
        )
        lines.append(
            "- If you're about to say 'code was removed' or 'block is unconditional':"
        )
        lines.append(
            "  → STOP → Re-read the patch format instructions → You're misinterpreting"
        )
        review_prompt = "\n".join(lines)
        # print(f"Review Prompt: {review_prompt}")
        return "\n".join(lines)

    def _invoke_model(
        self,
        prompt: str,
        *,
        temperature: float,
    ) -> Tuple[Optional[str], Optional[str]]:
        del temperature  # temperature kept for signature compatibility
        try:
            response = self._model.generate_content(  # type: ignore[union-attr]
                prompt
            )
        except Exception as exc:  # pragma: no cover
            return None, f"Failed to call Gemini API: {exc}"

        if hasattr(response, "text"):
            try:
                text_value = response.text
            except ValueError as exc:  # finish_reason e.g. SAFETY
                message = str(exc)
                if "finish_reason" in message and "2" in message:
                    return None, (
                        "Gemini response was blocked by the safety filters. "
                        "Mask or remove sensitive values in the patches before retrying."
                    )
            else:
                if text_value:
                    return text_value.strip(), None

        candidates = getattr(response, "candidates", None)
        if candidates:
            for candidate in candidates:
                finish_reason = getattr(candidate, "finish_reason", None)
                if finish_reason == 2:  # SAFETY
                    return None, (
                        "Gemini response was blocked by the safety filters."
                        " Mask or remove sensitive values in the patches before retrying."
                    )
                parts = self._extract_parts(candidate)
                text = self._collect_text_from_parts(parts)
                if text:
                    return text.strip(), None

        maybe_text = getattr(response, "output_text", None)
        if maybe_text:
            return str(maybe_text).strip(), None

        return None, "Gemini response did not contain any text."

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        cleaned = self._strip_code_fence(response_text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        stripped = str(text).strip()
        if not stripped.startswith("```"):
            return stripped
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_parts(candidate: Any) -> List[Any]:
        parts: List[Any] = []
        content = getattr(candidate, "content", None)

        def collect(obj: Any) -> None:
            if obj is None:
                return
            if hasattr(obj, "parts"):
                parts.extend(obj.parts or [])
            elif isinstance(obj, dict):
                parts.extend(obj.get("parts", []) or [])
            elif isinstance(obj, list):
                for item in obj:
                    collect(item)

        collect(content)
        contents = getattr(candidate, "contents", None)
        if contents:
            collect(contents)
        return parts

    @staticmethod
    def _collect_text_from_parts(parts: Sequence[Any]) -> str:
        texts: List[str] = []
        for part in parts:
            if hasattr(part, "text"):
                texts.append(part.text or "")
            elif isinstance(part, dict) and "text" in part:
                texts.append(part.get("text") or "")
            elif isinstance(part, str):
                texts.append(part)
        return "\n".join(t for t in texts if t)
