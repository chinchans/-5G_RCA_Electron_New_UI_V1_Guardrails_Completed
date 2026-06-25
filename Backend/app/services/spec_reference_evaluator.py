"""LLM-based 3GPP specification compliance evaluation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

try:  # pragma: no cover - optional dependency
    import google.generativeai as genai
except Exception:  # pragma: no cover - the library may be missing
    genai = None  # type: ignore


@dataclass
class SpecReviewResult:
    """Structured response returned to the UI."""

    status: str
    messages: List[str]
    verdict: Optional[str] = None
    confidence: Optional[float] = None
    issues: Optional[List[Dict[str, Any]]] = None
    raw_response: Optional[str] = None
    summary: Optional[str] = None
    reasoning: Optional[str] = None
    recommendations: Optional[List[str]] = None
    will_fix_issue: Optional[bool] = None


class SpecReferenceEvaluator:
    """Wrapper around Gemini 1.5 Flash for spec-compliance review."""

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        api_key_env: str = "GEMINI_API_KEY",
        temperature: float = 0.1,
        max_output_tokens: int = 2048,
    ) -> None:
        self.model_name = model_name
        self.api_key_env = api_key_env
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self._model, self._init_error = self._initialize_model()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        *,
        error_summary: str,
        code_changes: List[Dict[str, Any]],
        spec_context: str,
        additional_notes: Optional[str] = None,
    ) -> SpecReviewResult:
        """Run the 3GPP spec reference review with the configured LLM."""

        if not self._model:
            # Attempt to re-initialize in case the environment changed after startup.
            self._model, self._init_error = self._initialize_model()

        if not self._model:
            message = self._init_error or (
                "Gemini client is not configured. Install google-generativeai and set GEMINI_API_KEY."
            )
            return SpecReviewResult(
                status="error",
                messages=[message],
            )

        if not spec_context.strip():
            return SpecReviewResult(
                status="warning",
                messages=[
                    "No 3GPP specification context was provided; proceeding with code-based review only."
                ],
                verdict="APPROVE_WITH_WARNINGS",
                confidence=None,
                issues=None,
                summary="Specification context missing. Unable to verify against 3GPP references.",
            )

        if not code_changes:
            return SpecReviewResult(
                status="error",
                messages=["No code changes provided for spec review."],
            )

        prompt = self._build_prompt(
            error_summary=error_summary,
            code_changes=code_changes,
            spec_context=spec_context,
            additional_notes=additional_notes,
        )

        response_text, response_error = self._invoke_model(prompt)
        if response_error:
            return SpecReviewResult(
                status="error",
                messages=[response_error],
            )

        if response_text is None:
            return SpecReviewResult(
                status="error",
                messages=["Gemini response was empty or could not be generated."],
            )

        parsed = self._parse_response(response_text)
        if parsed is None:
            return SpecReviewResult(
                status="error",
                messages=[
                    "Gemini response could not be parsed as JSON.",
                    "Raw response:",
                    response_text,
                ],
                raw_response=response_text,
            )

        messages: List[str] = []
        verdict = parsed.get("overall_verdict") or parsed.get("verdict")
        confidence = parsed.get("confidence")
        issues = parsed.get("spec_violations") or parsed.get("findings")

        summary = parsed.get("summary")
        reasoning = parsed.get("reasoning")
        recommendations_data = parsed.get("recommendations")
        if recommendations_data and not isinstance(recommendations_data, list):
            messages.append(str(recommendations_data))
            recommendations: Optional[List[str]] = None
        else:
            recommendations = recommendations_data

        return SpecReviewResult(
            status="success",
            messages=messages,
            verdict=verdict,
            confidence=self._safe_float(confidence),
            issues=issues if isinstance(issues, list) else None,
            raw_response=response_text,
            summary=summary,
            reasoning=reasoning,
            recommendations=recommendations if isinstance(recommendations, list) else None,
            will_fix_issue=parsed.get("will_fix_issue"),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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

    def _build_prompt(
        self,
        *,
        error_summary: str,
        code_changes: List[Dict[str, Any]],
        spec_context: str,
        additional_notes: Optional[str],
    ) -> str:
        code_blocks = []
        for idx, change in enumerate(code_changes, start=1):
            parts = [f"Change {idx}:"]
            file_path = change.get("file_path")
            function_name = change.get("function_name")
            change_type = change.get("change_type")
            if change_type:
                parts.append(f"Type: {change_type}")
            if file_path or function_name:
                parts.append("Location: " + ", ".join(filter(None, [file_path, function_name])))
            description = change.get("description")
            if description:
                parts.append(f"Description: {description}")
            diff_text = change.get("diff") or change.get("patched_code") or ""
            if diff_text:
                parts.append("Code Diff:\n" + diff_text)
            function_original = change.get("function_original")
            if function_original:
                parts.append("Original Function:\n" + function_original)
            function_patched = change.get("function_patched")
            if function_patched:
                parts.append("Proposed Function:\n" + function_patched)
            code_blocks.append("\n".join(parts))

        notes_section = f"Additional Context:\n{additional_notes}" if additional_notes else ""

        prompt = f"""
You are a senior 3GPP specification compliance reviewer for 5G RAN software. Evaluate whether the proposed 
fix is correct and compliant with the referenced standards, using a balanced and constructive approach.

**EVALUATION PHILOSOPHY:**
- Primary focus: Does the fix resolve the reported error?
- Secondary focus: Is the fix compliant with 3GPP specifications?
- Minor enhancements (better logging, additional defensive checks) should be noted as suggestions, not violations
- A fix that correctly addresses the error and is generally compliant should be approved, even with minor improvements possible

**CRITICAL: UNDERSTANDING PATCH FORMAT**
- The code changes shown may be SNIPPETS or COMPLETE functions depending on what was provided
- If you see "Code Diff" or "Proposed Function" that shows control structures (if/else) appearing incomplete,
  understand that this may be a targeted patch meant to be inserted at a specific location
- The "Original Function" and "Proposed Function" may show the full function, OR just the modified section
- **DO NOT assume code was removed** unless you can clearly see in the diff that it was deleted
- When evaluating syntax, consider the patch in context - an `else` block snippet is meant to be placed after
  the corresponding `if/else if` blocks in the actual codebase
- Focus on whether the LOGIC and INTENT of the fix is correct and compliant, not just syntax in isolation

### Error Summary
{error_summary}

### Proposed Code Changes
{os.linesep.join(code_blocks)}

### 3GPP Specification Context
{spec_context}

{notes_section}

### Review Instructions
1. **Primary Assessment**: Determine if the code change addresses the reported error. This is the most important criterion.
   - Evaluate the LOGIC of the fix: if it initializes NULL pointers, adds missing error handling, or handles edge cases,
     these are positive changes that address the error
   - Do not reject based on patch format appearing incomplete - focus on whether the fix logic is sound
2. **Compliance Check**: Check compliance with the provided 3GPP specification text. Note that:
   - If the fix correctly handles the error case and follows standard practices, it is likely compliant
   - Minor improvements (log message clarity, additional NULL checks) do not constitute spec violations
   - Adding error handling for unrecognized values (like rejecting with RRCReject) is generally compliant
3. **Balanced Evaluation**: 
   - If the fix resolves the error and is generally compliant, use APPROVE or APPROVE_WITH_WARNINGS
   - Only use REJECT if the fix violates specifications or fails to address the error
   - Frame suggestions as enhancements rather than violations
   - **If a patch adds an `else` block to handle NULL pointer issues, this is a CORRECT fix and should be approved**
4. **Verdict Guidelines**:
   - **APPROVE**: Fix correctly addresses the error and is compliant. Minor suggestions can be in recommendations.
   - **APPROVE_WITH_WARNINGS**: Fix addresses the error but has minor concerns or suggestions for improvement.
   - **REJECT**: Fix does not address the error, violates specifications, or introduces critical issues.
5. Respond strictly in JSON using the following schema:
{{
  "overall_verdict": "APPROVE | APPROVE_WITH_WARNINGS | REJECT",
  "confidence": 0.0-1.0,
  "spec_violations": [
    {{
      "spec_reference": "",
      "severity": "LOW | MEDIUM | HIGH | CRITICAL",
      "description": "",
      "suggested_action": ""
    }}
  ],
  "summary": "Balanced summary that acknowledges fix effectiveness and notes any suggestions",
  "reasoning": "Constructive explanation recognizing what the fix does correctly, then noting any enhancements",
  "recommendations": ["Suggestions for minor improvements (not blockers)"],
  "will_fix_issue": true | false
}}

**Tone Guidelines:**
- Start by acknowledging what the fix does correctly
- Use constructive language for suggestions
- Reserve CRITICAL severity for actual specification violations
- Frame improvements as enhancements, not failures

Ensure the response is valid JSON with double quotes.
"""
        # print(f"Prompt: {prompt}")
        return prompt.strip()

    def _invoke_model(self, prompt: str) -> tuple[Optional[str], Optional[str]]:  # pragma: no cover - API call
        try:
            response = self._model.generate_content(prompt)  # type: ignore[union-attr]

            if hasattr(response, "text") and response.text:
                return response.text.strip(), None

            candidates = getattr(response, "candidates", None)
            if candidates:
                for candidate in candidates:
                    finish_reason = getattr(candidate, "finish_reason", None)
                    if finish_reason == 2:  # SAFETY
                        return None, (
                            "Gemini response was blocked by the safety filters. "
                            "Mask or remove sensitive values in the patches before retrying."
                        )
                    parts = self._extract_parts(candidate)
                    joined = self._collect_text_from_parts(parts)
                    if joined:
                        return joined.strip(), None

            maybe_text = getattr(response, "output_text", None)
            if maybe_text:
                return str(maybe_text).strip(), None

            return None, "Gemini response did not contain any text."
        except Exception as exc:
            return None, f"Failed to call Gemini API: {exc}"

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        cleaned = self._strip_code_fence(response_text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        stripped = text.strip()
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
        """Extract content parts from a Gemini candidate regardless of SDK structure."""

        parts: List[Any] = []
        content = getattr(candidate, "content", None)

        def collect_from(obj: Any) -> None:
            if obj is None:
                return
            if hasattr(obj, "parts"):
                parts.extend(obj.parts or [])
            elif isinstance(obj, dict):
                parts.extend(obj.get("parts", []) or [])
            elif isinstance(obj, list):
                for item in obj:
                    collect_from(item)

        collect_from(content)

        # Some SDK variants expose candidate.contents (list of Content)
        contents = getattr(candidate, "contents", None)
        if contents:
            collect_from(contents)

        return parts

    @staticmethod
    def _collect_text_from_parts(parts: Sequence[Any]) -> str:
        """Collect plain text from Gemini parts."""

        texts: List[str] = []
        for part in parts:
            if hasattr(part, "text"):
                texts.append(part.text or "")
            elif isinstance(part, dict) and "text" in part:
                texts.append(part.get("text") or "")
            elif isinstance(part, str):
                texts.append(part)
        return "\n".join(t for t in texts if t)
