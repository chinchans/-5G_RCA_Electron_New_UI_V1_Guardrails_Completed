"""Layer 1 prompt extraction for TSG intent guardrails.

Strips trusted system/application template text and isolates the user-provided
delta so RoBERTa is not diluted by hundreds of developer-authored telecom rules.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PromptExtractionResult:
    payload: str
    mode: str  # trusted_baseline | user_delta | full_user | full_user_rewrite | empty
    baseline_chars: int = 0
    submitted_chars: int = 0
    added_line_count: int = 0
    added_lines: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "payload_preview": (self.payload or "")[:240],
            "payload_chars": len(self.payload or ""),
            "baseline_chars": self.baseline_chars,
            "submitted_chars": self.submitted_chars,
            "added_line_count": self.added_line_count,
            "added_lines_preview": self.added_lines[:8],
        }


def flatten_prompt_content(content: Any) -> str:
    """Normalize dict/string prompt templates into a single string."""
    if content is None:
        return ""
    if isinstance(content, dict):
        system = str(content.get("System Prompt") or content.get("system") or "")
        user = str(content.get("User Prompt") or content.get("user") or "")
        if system and user:
            return f"{system}\n\n{user}".strip()
        return (system or user or str(content)).strip()
    return str(content).strip()


def _normalize_line(line: str) -> str:
    return " ".join((line or "").strip().split())


def extract_user_prompt_payload(
    submitted: str,
    baseline: Optional[str] = None,
) -> PromptExtractionResult:
    """Extract user-authored content from a submitted prompt.

    Modes:
      - trusted_baseline: submitted matches factory/baseline template → no user delta
      - user_delta: only added/changed lines vs baseline
      - full_user / full_user_rewrite: no usable baseline, or mostly rewritten
      - empty: no submitted text
    """
    submitted_text = (submitted or "").strip()
    baseline_text = (baseline or "").strip()

    if not submitted_text:
        return PromptExtractionResult(payload="", mode="empty")

    if not baseline_text:
        return PromptExtractionResult(
            payload=submitted_text,
            mode="full_user",
            submitted_chars=len(submitted_text),
        )

    submitted_norm = _normalize_line(submitted_text)
    baseline_norm = _normalize_line(baseline_text)
    if submitted_norm == baseline_norm:
        return PromptExtractionResult(
            payload="",
            mode="trusted_baseline",
            baseline_chars=len(baseline_text),
            submitted_chars=len(submitted_text),
        )

    baseline_counts: Counter[str] = Counter()
    for line in baseline_text.splitlines():
        key = _normalize_line(line)
        if key:
            baseline_counts[key] += 1

    added_lines: List[str] = []
    submitted_nonempty = 0
    for line in submitted_text.splitlines():
        raw = (line or "").rstrip()
        key = _normalize_line(raw)
        if not key:
            continue
        submitted_nonempty += 1
        if baseline_counts[key] > 0:
            baseline_counts[key] -= 1
        else:
            added_lines.append(raw.strip())

    if not added_lines:
        # Reordered / whitespace-equivalent → treat as trusted
        return PromptExtractionResult(
            payload="",
            mode="trusted_baseline",
            baseline_chars=len(baseline_text),
            submitted_chars=len(submitted_text),
        )

    rewrite_ratio = len(added_lines) / max(1, submitted_nonempty)
    if rewrite_ratio >= 0.60:
        # Mostly rewritten — classify the full submitted prompt (still without
        # pretending the factory template is present if it was removed).
        return PromptExtractionResult(
            payload=submitted_text,
            mode="full_user_rewrite",
            baseline_chars=len(baseline_text),
            submitted_chars=len(submitted_text),
            added_line_count=len(added_lines),
            added_lines=added_lines[:40],
        )

    payload = "\n".join(added_lines).strip()
    return PromptExtractionResult(
        payload=payload,
        mode="user_delta",
        baseline_chars=len(baseline_text),
        submitted_chars=len(submitted_text),
        added_line_count=len(added_lines),
        added_lines=added_lines[:40],
    )


def resolve_tsg_baseline_prompt(template_key: str) -> str:
    """Resolve factory/default baseline text for a TSG template key.

    Built-in keys use ``default_prompts`` (factory text before JSON overrides) so
    corrupted saved templates cannot hide planted OOS as a trusted baseline.
    User-saved custom keys fall back to the current stored prompt.
    """
    key = (template_key or "").strip()
    if not key or key.lower() in {"custom", "refine"}:
        return ""

    try:
        # Local import avoids circular dependency at module load time.
        from app.api.endpoints import test_script_generator
    except Exception:
        try:
            from app.services.test_script_generator import TestScriptGenerator

            test_script_generator = TestScriptGenerator()
        except Exception:
            return ""

    defaults = {}
    try:
        defaults = test_script_generator.get_default_prompts() or {}
    except Exception:
        defaults = {}

    if key in defaults:
        return flatten_prompt_content(defaults.get(key))

    prompts = {}
    try:
        prompts = test_script_generator.get_prompts() or {}
    except Exception:
        prompts = {}
    return flatten_prompt_content(prompts.get(key))
