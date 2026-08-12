#!/usr/bin/env python3
"""Golden allow/block suite for production intent-classifier paths.

Covers TSG Generate, Prompt Studio Add Template (prompt_studio_save), and Refine.

Examples:
  cd Backend
  ./venv/bin/python Guardrails/Fine-tuning/run_golden_guardrail_cases.py
  ./venv/bin/python Guardrails/Fine-tuning/run_golden_guardrail_cases.py --cases Guardrails/Fine-tuning/golden_cases.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_CASES = Path(__file__).resolve().parent / "golden_cases.json"


def _blocked_by_classifier(
    text: str,
    *,
    context: str,
    previous_response: str = "",
    text_content: str = "",
    template_key: str = "Golden",
) -> Dict[str, Any]:
    """Return {blocked, label, detail, latency_ms} using production raise path."""
    from fastapi import HTTPException

    from app.guardrails.guardrail_classifier import ensure_guardrail_classifier_loaded
    from app.guardrails.tsg_prompt_guardrail import raise_if_classifier_blocked

    ensure_guardrail_classifier_loaded()
    t0 = time.perf_counter()
    try:
        result = raise_if_classifier_blocked(
            text,
            template_key=template_key,
            context=context,
            previous_response=previous_response or None,
            text_content=text_content or None,
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        # None = classifier disabled / skipped empty; treat as allow
        if result is None:
            return {
                "blocked": False,
                "label": "SKIPPED",
                "detail": "classifier_skipped",
                "latency_ms": round(latency_ms, 2),
            }
        return {
            "blocked": False,
            "label": result.predicted_label,
            "detail": result.detail,
            "latency_ms": round(latency_ms, 2),
        }
    except HTTPException as exc:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        classifier = detail.get("classifier") or {}
        return {
            "blocked": True,
            "label": classifier.get("predicted_label") or detail.get("blocked_by") or "BLOCKED",
            "detail": detail.get("message") or str(detail),
            "latency_ms": round(latency_ms, 2),
            "http_status": exc.status_code,
        }


def _also_check_refine_scope(
    text: str,
    *,
    previous_response: str = "",
    text_content: str = "",
) -> Optional[str]:
    from app.guardrails.tsg_prompt_guardrail import validate_refine_prompt_scope

    return validate_refine_prompt_scope(
        text,
        text_content=text_content,
        previous_response=previous_response,
    )


def run_cases(cases_path: Path) -> Dict[str, Any]:
    cases: List[Dict[str, Any]] = json.loads(cases_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise RuntimeError(f"No cases in {cases_path}")

    results: List[Dict[str, Any]] = []
    passed = 0
    failed = 0

    print(f"Golden cases: {cases_path} ({len(cases)} cases)")
    print("-" * 72)

    for case in cases:
        case_id = case.get("id") or "unnamed"
        context = (case.get("context") or "tsg_generate").strip()
        text = (case.get("text") or "").strip()
        expect_blocked = bool(case.get("expect_blocked"))
        previous_response = case.get("previous_response") or ""
        text_content = case.get("text_content") or ""

        outcome = _blocked_by_classifier(
            text,
            context=context,
            previous_response=previous_response,
            text_content=text_content,
            template_key=case_id,
        )

        # Refine also has keyword/off-topic scope gate in production.
        scope_reason = None
        if context == "tsg_refine":
            scope_reason = _also_check_refine_scope(
                text,
                previous_response=previous_response,
                text_content=text_content,
            )
            if scope_reason:
                outcome = {
                    **outcome,
                    "blocked": True,
                    "label": outcome.get("label") or "refine_scope",
                    "detail": scope_reason,
                    "blocked_by_scope": True,
                }

        ok = bool(outcome["blocked"]) == expect_blocked
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1

        line = (
            f"[{status}] {case_id:32s} context={context:18s} "
            f"expect_blocked={expect_blocked} got={outcome['blocked']} "
            f"label={outcome.get('label')}  {outcome['latency_ms']:.0f}ms"
        )
        print(line)
        if not ok:
            print(f"       detail: {str(outcome.get('detail'))[:160]}")
            if case.get("notes"):
                print(f"       notes:  {case['notes']}")

        results.append(
            {
                "id": case_id,
                "passed": ok,
                "expect_blocked": expect_blocked,
                "got_blocked": outcome["blocked"],
                "label": outcome.get("label"),
                "detail": outcome.get("detail"),
                "latency_ms": outcome.get("latency_ms"),
                "context": context,
                "scope_reason": scope_reason,
            }
        )

    print("-" * 72)
    print(f"Summary: {passed} passed, {failed} failed, {len(cases)} total")
    return {
        "cases_path": str(cases_path),
        "passed": passed,
        "failed": failed,
        "total": len(cases),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    if not args.cases.exists():
        print(f"Cases file not found: {args.cases}", file=sys.stderr)
        return 2

    summary = run_cases(args.cases)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Wrote report: {args.report}")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
