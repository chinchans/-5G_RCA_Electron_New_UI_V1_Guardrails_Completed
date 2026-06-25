"""LLM-based judge that reviews code fixes for correctness."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:  # pragma: no cover - optional dependency
    import google.generativeai as genai
except Exception:  # pragma: no cover - library may be missing
    genai = None  # type: ignore


@dataclass
class JudgeReviewResult:
    """Structured response returned to the UI."""

    status: str
    messages: List[str]
    verdict: Optional[str] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    reasoning: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    issues: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[str]] = None


class LLMJudgeEvaluator:
    """Wrapper around Gemini to act as an automated code judge."""

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

    def evaluate(
        self,
        *,
        error_summary: str,
        code_changes: List[Dict[str, Any]],
        config_changes: Optional[List[Dict[str, Any]]] = None,
    ) -> JudgeReviewResult:
        """Judge whether the proposed fixes correctly resolve the issue."""

        if not self._model:
            self._model, self._init_error = self._initialize_model()

        if not self._model:
            message = self._init_error or (
                "Gemini client is not configured. Install google-generativeai and set GEMINI_API_KEY."
            )
            return JudgeReviewResult(status="error", messages=[message])

        if not code_changes and not config_changes:
            return JudgeReviewResult(
                status="error",
                messages=["No code or configuration changes provided for LLM judge evaluation."],
            )

        prompt = self._build_prompt(
            error_summary=error_summary,
            code_changes=code_changes,
            config_changes=config_changes,
        )
        # print(f"Prompt: {prompt}")

        response_text, response_error = self._invoke_model(prompt, temperature=self.temperature)
        if response_error:
            return JudgeReviewResult(status="error", messages=[response_error])

        if response_text is None:
            return JudgeReviewResult(
                status="error",
                messages=["LLM judge response was empty or could not be generated."],
            )

        parsed = self._parse_response(response_text)
        if parsed is None:
            return JudgeReviewResult(
                status="error",
                messages=[
                    "LLM judge response could not be parsed as JSON.",
                    "Raw response:",
                    response_text,
                ],
            )

        messages: List[str] = []
        verdict = parsed.get("verdict")
        confidence = parsed.get("confidence")
        summary = parsed.get("summary")
        reasoning = parsed.get("reasoning")
        criteria = parsed.get("criteria")
        issues = parsed.get("issues") if isinstance(parsed.get("issues"), list) else None
        recommendations = (
            parsed.get("recommendations")
            if isinstance(parsed.get("recommendations"), list)
            else None
        )

        return JudgeReviewResult(
            status="success",
            messages=messages,
            verdict=verdict,
            confidence=self._safe_float(confidence),
            summary=summary,
            reasoning=reasoning,
            criteria=criteria if isinstance(criteria, dict) else None,
            issues=issues,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------


    def _get_deployment_context(self) -> str:
        deployment_prefix = (
            "We have an OpenAirInterface-5G codebase with UE, gNB, and core network parts. "
            "The UE is the user equipment, the gNB is the base station, and the core network connects them. "
            "Deployment context: "
        )
        path = Path("Error_fixing_pipelin/database/error_patterns_structured.json")
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            deployment_context = data.get("deployment_context", {})
            return deployment_prefix + str(deployment_context)
        except Exception:
            return deployment_prefix + "unavailable."

    def _initialize_model(self):
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
        config_changes: Optional[List[Dict[str, Any]]],
    ) -> str:
        change_sections = []
        for idx, change in enumerate(code_changes, start=1):
            parts = [f"Fix {idx}:"]
            location = ", ".join(
                filter(
                    None,
                    [
                        change.get("file_path"),
                        change.get("function_name"),
                    ],
                )
            )
            if location:
                parts.append(f"Location: {location}")
            description = change.get("description")
            if description:
                parts.append(f"Description: {description}")

            original = change.get("original_code") or ""
            patched = change.get("patched_code") or ""
            diff = change.get("diff") or ""

            if original:
                parts.append("Original Code:\n" + original)
            if patched:
                parts.append("Proposed Fix:\n" + patched)
            if diff:
                parts.append("Diff:\n" + diff)

            change_sections.append("\n".join(parts))

        if change_sections:
            code_section = os.linesep.join(change_sections)
        else:
            code_section = "No code modifications were provided for this review."

        config_section = ""
        if config_changes:
            bullet_lines = []
            for entry in config_changes:
                name = entry.get("parameter_name") or entry.get("config_name") or "Unknown parameter"
                file_path = entry.get("file_path", "Unknown file")
                current_value = entry.get("current_value")
                proposed_value = entry.get("proposed_value")
                description = entry.get("description")
                line_parts = [f"{name} in {file_path}"]
                if current_value is not None:
                    line_parts.append(f"current={current_value}")
                if proposed_value is not None:
                    line_parts.append(f"new={proposed_value}")
                bullet_lines.append("- " + " • ".join(line_parts))
                if description:
                    bullet_lines.append(f"  Note: {description}")
            if bullet_lines:
                config_section = "\nConfiguration Changes:\n" + "\n".join(bullet_lines) + "\n"

        deployment_context = self._get_deployment_context()

        prompt = f"""
You are an expert software engineer and code reviewer acting as a constructive and balanced evaluator.
Your task is to assess whether the proposed fix resolves the reported issue, recognizing that fixes can be
functionally correct even if they have minor improvements that could be made.

**EVALUATION PHILOSOPHY:**
- Focus on whether the fix addresses the core issue and prevents the reported error
- Minor issues (like log message clarity, additional NULL checks for robustness) should be noted as 
  suggestions, not blockers
- A fix that resolves the root cause should be evaluated positively, even if it could be enhanced
- Be constructive and balanced in your assessment

**CRITICAL: UNDERSTANDING PATCH FORMAT**
- The "Original Code" and "Proposed Fix" are CODE SNIPPETS, not complete functions
- The "Proposed Fix" is meant to REPLACE the "Original Code" at a specific location in the function
- The patch may show control structures (if/else) that appear incomplete when viewed in isolation
- **DO NOT assume the entire function was replaced** - only the snippet shown is being modified
- When evaluating syntax, consider that the patch will be inserted into the existing function structure
- If the patch shows an `else` block, it will be placed after the corresponding `if/else if` blocks in the actual code
- Focus on whether the LOGIC of the fix is correct, not whether the snippet appears syntactically complete in isolation

{deployment_context}

### Bug Summary
{error_summary}

### Candidate Fixes
{code_section}

{config_section}

### Evaluation Criteria
Assess the candidate fix against the following criteria with a balanced perspective:
1. Functional correctness – Does the fix address the bug and satisfy the requirements? 
   **If yes, this is the most important criterion and should heavily influence the verdict.**
   **When evaluating: Consider if the patch logic (when inserted at the specified location) would resolve the error.**
2. Syntax correctness – Does the code compile or run without syntax/runtime errors?
   **IMPORTANT: The patch snippet may appear incomplete when viewed alone. Evaluate whether the patch, 
   when inserted at the location indicated by "line_numbers" and replacing "original_code", would create 
   valid syntax in the context of the full function. Do not reject based on the snippet appearing incomplete.**
3. Safety and security – Does the fix avoid introducing security vulnerabilities or undefined behaviour?
   **Note: Additional defensive checks (like NULL checks) are enhancements, not requirements for a passing verdict.**
4. Style and maintainability – Does the fix follow good coding practices and readability?
5. Performance – Does the fix avoid unnecessary regressions or inefficiencies?
6. Completeness – Does it cover all relevant edge cases implied by the bug?
   **Note: Handling the primary error case is sufficient; edge cases can be noted as suggestions.**
7. Deployment context – Does the fix comply with the deployment context of the codebase?
8. Configuration changes – Does the fix comply with the configuration changes of the codebase?

### Verdict Guidelines
- **PASS**: The fix correctly addresses the reported bug and resolves the issue. Minor improvements can be noted as recommendations.
- **NEEDS_REVIEW**: The fix addresses the bug but has significant concerns that need attention before deployment.
- **FAIL**: The fix does not address the bug, introduces new critical issues, or makes the problem worse.

**IMPORTANT**: If a fix correctly resolves the root cause of the bug (e.g., initializes a NULL pointer before use, 
adds missing error handling), it should generally receive a PASS verdict, even if there are minor suggestions 
for improvement (like better log messages or additional defensive checks).

**CRITICAL REMINDER ABOUT PATCH INTERPRETATION:**
- When you see a patch that adds an `else` block to handle NULL pointer cases, this is a CORRECT fix
- Do not assume the rest of the function was removed - the patch may only show the modified section
- If the patch shows `ue_context_p = rrc_gNB_create_ue_context(...)` in an `else` block, this fixes the NULL pointer issue
- Evaluate based on whether the LOGIC is correct, not whether the snippet appears complete in isolation
- A patch that initializes a NULL pointer before use should be evaluated as FUNCTIONALLY CORRECT

### Output Instructions
Respond strictly in JSON with the following schema:
{{
  "verdict": "PASS | FAIL | NEEDS_REVIEW",
  "confidence": 0.0-1.0,
  "summary": "Brief summary acknowledging the fix's effectiveness and any minor improvements",
  "reasoning": "Balanced explanation that recognizes what the fix does correctly, then notes any suggestions",
  "criteria": {{
    "functional_correctness": "PASS | FAIL | UNKNOWN",
    "syntax_correctness": "PASS | FAIL | UNKNOWN",
    "safety": "PASS | FAIL | UNKNOWN",
    "style": "PASS | FAIL | UNKNOWN",
    "performance": "PASS | FAIL | UNKNOWN",
    "completeness": "PASS | FAIL | UNKNOWN",
    "deployment_context": "PASS | FAIL | UNKNOWN",
    "configuration_changes": "PASS | FAIL | UNKNOWN"
  }},
  "issues": [
    {{
      "category": "",
      "description": "",
      "severity": "LOW | MEDIUM | HIGH"
    }}
  ],
  "recommendations": ["Constructive suggestions for minor improvements (not blockers)"]
}}

**Tone Guidelines:**
- Use positive language when the fix addresses the core issue
- Frame suggestions as enhancements rather than failures
- Acknowledge what the fix does correctly before noting improvements
- Reserve HIGH severity for issues that would cause the fix to fail or introduce new bugs

Do not include any text outside the JSON object.
"""
        # print(f"Prompt: {prompt}")
        return prompt.strip()

    def _invoke_model(
        self,
        prompt: str,
        *,
        temperature: Optional[float] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        try:
            response = self._model.generate_content(  # type: ignore[union-attr]
                prompt
            )
        except Exception as exc:
            return None, f"Failed to call Gemini API: {exc}"

        if hasattr(response, "text"):
            try:
                text_value = response.text
            except ValueError as exc:
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
                        "Gemini response was blocked by the safety filters. "
                        "Mask or remove sensitive values in the patches before retrying."
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

