"""
Ensure generated test cases include mandatory dedicated scenarios:

  - Registration Test → Registration Request/Accept (+ Registration Complete when present)
  - PDU Session Test → PDU Session Establishment flow (not just attach/registration)
  - Handover Test → true mobility events (NOT Secondary Node Release)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


@dataclass
class ScenarioMessageCheck:
    scenario_id: str
    label: str
    triggered: bool
    passed: bool
    missing: List[str] = field(default_factory=list)
    message: str = ""
    dedicated_testcase: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "label": self.label,
            "triggered": self.triggered,
            "passed": self.passed,
            "missing": self.missing,
            "message": self.message,
            "dedicated_testcase": self.dedicated_testcase,
        }


@dataclass
class ScenarioMessageCoverageResult:
    available: bool
    passed: bool
    advisory_only: bool
    checks: List[ScenarioMessageCheck] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "passed": self.passed,
            "advisory_only": self.advisory_only,
            "checks": [c.to_dict() for c in self.checks],
            "warnings": self.warnings,
            "errors": self.errors,
        }


# Always required in every generated 5G test-case suite.
_SCENARIO_SPECS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "registration",
        "label": "Registration",
        "always_required": True,
        "dedicated_title_tokens": (
            "registration",
            "register",
            "reg_req",
            "reg accept",
            "attach",
            "attach_detach",
        ),
        "dedicated_exclude_tokens": (),
        "required_groups": (
            ("Registration Request", ("registration request", "reg request", "attach request", "initial attach", "attach_req")),
            ("Registration Accept", ("registration accept", "reg accept", "attach accept", "attach_acc")),
        ),
        "optional_bonus_groups": (
            ("Registration Complete", ("registration complete", "attach complete")),
        ),
        "fail_message": (
            "Registration Test → Should contain Registration Request/Accept (or Attach Request/Accept) messages."
        ),
        "missing_dedicated_message": (
            "No dedicated Registration / Attach testcase exists."
        ),
    },
    {
        "id": "pdu_session",
        "label": "PDU Session",
        "always_required": True,
        "dedicated_title_tokens": (
            "pdu session",
            "pdu_session",
            "pdusession",
            "session establishment",
            "qos flow",
            "attach",
        ),
        "dedicated_exclude_tokens": (),
        "required_groups": (
            (
                "PDU Session Establishment",
                (
                    "pdu session establishment",
                    "pdu session establishment request",
                    "pdu session establishment accept",
                    "pdu session resource setup",
                    "pdu session setup",
                    "pdu session accept",
                    "bearer setup",
                    "erab setup",
                    "activate default eps bearer context accept",
                    "pdusessionestablishmentaccept",
                ),
            ),
        ),
        "prefer_groups": (),
        "fail_message": (
            "PDU Session Test → Should contain PDU Session Establishment events "
            "(Request → Authentication → Accept → User Plane / N3 Tunnel)."
        ),
        "missing_dedicated_message": (
            "No dedicated PDU Session testcase exists."
        ),
    },
    {
        "id": "handover",
        "label": "Handover",
        "always_required": False,  # Only required when primary feature involves mobility/handover or dedicated case exists
        "dedicated_title_tokens": (
            "handover",
            "hand-over",
            "hand over",
            "xn handover",
            "n2 handover",
            "ng handover",
            "inter-gnb",
            "inter gnb",
            "inter-du",
            "inter du",
            "inter-cu",
            "inter cu",
            "mobility",
            "path switch",
            "measurement report",
        ),
        # Secondary Node Release is NOT handover / mobility.
        "dedicated_exclude_tokens": (
            "secondary node release",
            "sgnb release",
            "sn release",
        ),
        "required_groups": (
            (
                "Handover / mobility event",
                (
                    "measurement report",
                    "handover required",
                    "handover request",
                    "handover request ack",
                    "handover request acknowledge",
                    "handover command",
                    "handover complete",
                    "handover preparation",
                    "rrc reconfiguration",
                    "path switch",
                    "path switch request",
                    "xn handover",
                    "n2 handover",
                    "ng handover",
                    "inter-gnb",
                    "inter gnb",
                    "inter-du",
                    "inter du",
                    "inter-cu",
                    "inter cu",
                    "inter-gnb mobility",
                    "mobility event",
                ),
            ),
        ),
        "fail_message": (
            "Handover Test → Should contain mobility/handover events "
            "(Measurement Report → Handover Required/Request → Path Switch → Complete). "
            "Secondary Node Release is not handover."
        ),
        "missing_dedicated_message": (
            "No dedicated Handover testcase exists "
            "(Secondary Node Release is not handover)."
        ),
    },
)


def _parse_json_payload(raw: str) -> Any:
    text = (raw or "").strip()
    if not text:
        return None
    fence = JSON_FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return None


def _parse_test_cases(generated_text: str) -> List[Dict[str, Any]]:
    parsed = _parse_json_payload(generated_text)
    if isinstance(parsed, list):
        return [c for c in parsed if isinstance(c, dict)]
    if isinstance(parsed, dict):
        cases = parsed.get("test_cases") or parsed.get("testCases")
        if isinstance(cases, list):
            return [c for c in cases if isinstance(c, dict)]
    return []


def _flatten_test_case_text(test_case: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in (
        "testCaseID",
        "testCaseId",
        "title",
        "description",
        "preconditions",
        "testSteps",
        "expectedResults",
        "verificationMethods",
        "postconditions",
    ):
        value = test_case.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    return " ".join(parts)


def _normalize_primary_feature(value: Optional[str]) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").replace("-", " ").split())


def _case_title_blob(test_case: Dict[str, Any]) -> str:
    parts = [
        str(test_case.get("testCaseID") or test_case.get("testCaseId") or ""),
        str(test_case.get("title") or ""),
        str(test_case.get("description") or ""),
    ]
    return " ".join(parts).lower()


def _suite_text(test_cases: Sequence[Dict[str, Any]]) -> str:
    return " ".join(_flatten_test_case_text(case) for case in test_cases).lower()


def _group_satisfied(corpus: str, phrases: Sequence[str]) -> bool:
    return any(phrase in corpus for phrase in phrases)


def _has_dedicated_testcase(
    title_blobs: Sequence[str],
    tokens: Sequence[str],
    exclude_tokens: Sequence[str] = (),
) -> bool:
    for title in title_blobs:
        if any(ex in title for ex in exclude_tokens):
            continue
        if any(tok in title for tok in tokens):
            return True
    return False


def _dedicated_case_corpus(
    test_cases: Sequence[Dict[str, Any]],
    tokens: Sequence[str],
    exclude_tokens: Sequence[str] = (),
) -> str:
    """Text from only the dedicated scenario test cases (preferred for event matching)."""
    parts: List[str] = []
    for case in test_cases:
        title = _case_title_blob(case)
        if any(ex in title for ex in exclude_tokens):
            continue
        if any(tok in title for tok in tokens):
            parts.append(_flatten_test_case_text(case).lower())
    return " ".join(parts)


def validate_scenario_message_coverage(
    generated_text: str,
    *,
    primary_feature: Optional[str] = None,
    test_cases: Optional[Sequence[Dict[str, Any]]] = None,
    advisory_only: bool = True,
    require_all_scenarios: bool = True,
) -> ScenarioMessageCoverageResult:
    """
    Validate that the suite includes dedicated Registration, PDU Session, and Handover tests.

    By default all three scenarios are always required (not only when Primary Feature is set).
    Secondary Node Release does not count as Handover.
    """
    feat_norm = _normalize_primary_feature(primary_feature)
    cases = list(test_cases) if test_cases is not None else _parse_test_cases(generated_text)
    if not cases:
        return ScenarioMessageCoverageResult(
            available=False,
            passed=True,
            advisory_only=advisory_only,
            warnings=["Scenario message coverage skipped — no structured test cases found."],
        )

    suite_lower = _suite_text(cases)
    title_blobs = [_case_title_blob(case) for case in cases]

    checks: List[ScenarioMessageCheck] = []
    warnings: List[str] = []
    errors: List[str] = []

    for spec in _SCENARIO_SPECS:
        always = bool(spec.get("always_required")) and require_all_scenarios
        # Handover scenario is only mandatory if primary feature explicitly involves mobility/handover
        if spec["id"] == "handover" and feat_norm:
            mobility_tokens = ("handover", "mobility", "xn", "n2", "inter gnb", "path switch")
            if not any(tok in feat_norm for tok in mobility_tokens):
                always = False

        dedicated = _has_dedicated_testcase(
            title_blobs,
            spec["dedicated_title_tokens"],
            spec.get("dedicated_exclude_tokens") or (),
        )
        triggered = always or dedicated
        if not triggered:
            checks.append(
                ScenarioMessageCheck(
                    scenario_id=spec["id"],
                    label=spec["label"],
                    triggered=False,
                    passed=True,
                    dedicated_testcase=False,
                )
            )
            continue

        missing: List[str] = []
        if not dedicated:
            missing.append("Dedicated testcase")

        # Prefer events inside dedicated cases; fall back to full suite.
        dedicated_corpus = _dedicated_case_corpus(
            cases,
            spec["dedicated_title_tokens"],
            spec.get("dedicated_exclude_tokens") or (),
        )
        event_corpus = dedicated_corpus or suite_lower

        prefer = spec.get("prefer_groups") or ()
        if prefer:
            # If prefer groups exist, require at least one prefer group OR the broad required group.
            prefer_ok = any(_group_satisfied(event_corpus, phrases) for _, phrases in prefer)
            broad_ok = all(
                _group_satisfied(event_corpus, phrases) for _, phrases in spec["required_groups"]
            )
            if not (prefer_ok or broad_ok):
                for label, _phrases in prefer:
                    missing.append(label)
                for label, phrases in spec["required_groups"]:
                    if not _group_satisfied(event_corpus, phrases):
                        missing.append(label)
        else:
            for label, phrases in spec["required_groups"]:
                if not _group_satisfied(event_corpus, phrases):
                    missing.append(label)

        passed = not missing
        if not dedicated:
            message = spec["missing_dedicated_message"]
        elif not passed:
            message = spec["fail_message"]
        else:
            message = ""

        # Deduplicate missing labels while preserving order
        missing = list(dict.fromkeys(missing))

        checks.append(
            ScenarioMessageCheck(
                scenario_id=spec["id"],
                label=spec["label"],
                triggered=True,
                passed=passed,
                missing=missing,
                message=message,
                dedicated_testcase=dedicated,
            )
        )
        if not passed:
            detail = message
            if missing:
                detail = f"{message} Missing: {', '.join(missing)}."
            warnings.append(detail)
            if not advisory_only:
                errors.append(detail)

    triggered_failed = [c for c in checks if c.triggered and not c.passed]
    return ScenarioMessageCoverageResult(
        available=True,
        passed=not triggered_failed,
        advisory_only=advisory_only,
        checks=checks,
        warnings=warnings,
        errors=errors,
    )
