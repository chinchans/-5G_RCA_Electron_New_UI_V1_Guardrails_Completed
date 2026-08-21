#!/usr/bin/env python3
"""Per-id RoBERTa domain-classifier eval.

Unlike eval_guardrail_classifier.py (aggregate metrics only), this script
classifies every record and writes/prints a row for each ``id``.

Default dataset: TESTING_PROMPTS_NOTEBOOKLM_OUT_OF_SCOPE_no_citations.json

Examples:
  cd Backend
  ./venv/bin/python Guardrails/Fine-tuning/eval_guardrail_classifier_by_id.py
  ./venv/bin/python Guardrails/Fine-tuning/eval_guardrail_classifier_by_id.py \\
      --dataset Guardrails/Fine-tuning/Datasets/Testng_prompts/TESTING_PROMPTS_NOTEBOOKLM_OUT_OF_SCOPE_no_citations.json \\
      --report Guardrails/Fine-tuning/reports/per_id_eval.json
  ./venv/bin/python Guardrails/Fine-tuning/eval_guardrail_classifier_by_id.py --failures-only
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_DATASET = (
    BACKEND_DIR
    / "Guardrails"
    / "Fine-tuning"
    / "Datasets"
    / "Testng_prompts"
    / "TESTING_PROMPTS_TOTAL_TELECOM_WORKBENCH.json"
)

DOMAIN_LABELS = ("TELECOM_WORKBENCH", "OUT_OF_SCOPE")


def _normalize_label(label: str) -> str:
    lab = (label or "").strip().upper()
    aliases = {
        "TELECOM": "TELECOM_WORKBENCH",
        "TELECOM_WORKBENCH": "TELECOM_WORKBENCH",
        "OOS": "OUT_OF_SCOPE",
        "OUT_OF_SCOPE": "OUT_OF_SCOPE",
        "INJECTION": "PROMPT_INJECTION",
        "PROMPT_INJECTION": "PROMPT_INJECTION",
    }
    return aliases.get(lab, lab)


def _load_records(path: Path) -> List[Dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(
            f"Expected a JSON list of objects with id/text/label in {path}"
        )

    records: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        record_id = item.get("id", idx)
        records.append(
            {
                "id": record_id,
                "text": text,
                "label": _normalize_label(str(item.get("label") or "")),
                "category": item.get("category") or "",
            }
        )
    if not records:
        raise RuntimeError(f"No usable records in {path}")
    return records


def _predict(text: str, mode: str) -> Dict[str, Any]:
    from app.guardrails.guardrail_classifier import (
        classify_prompt,
        classify_prompt_with_windows,
    )

    if mode == "windows":
        scan = classify_prompt_with_windows(text)
        return {
            "predicted_label": scan.predicted_label,
            "confidence_score": float(scan.confidence_score),
            "probabilities": dict(scan.probabilities or {}),
            "blocked": bool(scan.blocked),
            "detail": scan.detail,
            "mode_detail": scan.mode,
        }

    result = classify_prompt(text)
    return {
        "predicted_label": result.predicted_label,
        "confidence_score": float(result.confidence_score),
        "probabilities": dict(result.probabilities or {}),
        "blocked": result.predicted_label == "OUT_OF_SCOPE",
        "detail": result.detail,
        "mode_detail": "full",
    }


def run_per_id_eval(
    dataset: Path,
    *,
    mode: str = "full",
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    from app.guardrails.guardrail_classifier import ensure_guardrail_classifier_loaded

    records = _load_records(dataset)
    if limit is not None and limit > 0:
        records = records[:limit]

    print(f"Dataset: {dataset}")
    print(f"Mode: {mode}  |  records: {len(records)}")
    print(f"Expected label mix: {dict(Counter(r['label'] for r in records))}")
    print("Loading classifier…")
    ensure_guardrail_classifier_loaded()

    rows: List[Dict[str, Any]] = []
    correct = 0

    for i, rec in enumerate(records, start=1):
        t0 = time.perf_counter()
        try:
            pred = _predict(rec["text"], mode)
            error = None
        except Exception as exc:  # noqa: BLE001
            pred = {
                "predicted_label": "ERROR",
                "confidence_score": 0.0,
                "probabilities": {},
                "blocked": False,
                "detail": str(exc),
                "mode_detail": mode,
            }
            error = str(exc)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        expected = rec["label"]
        predicted = pred["predicted_label"]
        is_correct = predicted == expected and error is None
        if is_correct:
            correct += 1

        row = {
            "id": rec["id"],
            "expected_label": expected,
            "predicted_label": predicted,
            "correct": is_correct,
            "confidence_score": round(float(pred["confidence_score"]), 4),
            "probabilities": {
                k: round(float(v), 4)
                for k, v in (pred.get("probabilities") or {}).items()
            },
            "blocked": bool(pred.get("blocked")),
            "latency_ms": round(latency_ms, 2),
            "category": rec.get("category") or "",
            "detail": pred.get("detail") or "",
            "mode": pred.get("mode_detail") or mode,
            "text_preview": rec["text"][:160].replace("\n", " "),
            "error": error,
        }
        rows.append(row)

        status = "OK" if is_correct else "FAIL"
        print(
            f"[{status}] id={rec['id']!s:>4}  "
            f"exp={expected:20s} pred={predicted:20s}  "
            f"conf={row['confidence_score']:.3f}  "
            f"{row['latency_ms']:.0f}ms"
        )
        if i % 25 == 0:
            print(f"  … progress {i}/{len(records)}  running_acc={correct / i:.3f}")

    total = len(rows)
    summary = {
        "dataset": str(dataset),
        "mode": mode,
        "total": total,
        "correct": correct,
        "incorrect": total - correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "predicted_mix": dict(Counter(r["predicted_label"] for r in rows)),
        "expected_mix": dict(Counter(r["expected_label"] for r in rows)),
        "failed_ids": [r["id"] for r in rows if not r["correct"]],
    }
    return {"summary": summary, "results": rows}


def _print_summary(summary: Dict[str, Any]) -> None:
    print("\n======== Per-id classifier eval ========")
    print(
        f"Accuracy: {summary['accuracy']:.4f}  "
        f"({summary['correct']}/{summary['total']})"
    )
    print(f"Predicted mix: {summary['predicted_mix']}")
    print(f"Failed ids ({len(summary['failed_ids'])}): {summary['failed_ids']}")
    print("========================================\n")


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id",
        "expected_label",
        "predicted_label",
        "correct",
        "confidence_score",
        "blocked",
        "latency_ms",
        "category",
        "detail",
        "mode",
        "text_preview",
        "error",
        "prob_TELECOM_WORKBENCH",
        "prob_OUT_OF_SCOPE",
        "prob_PROMPT_INJECTION",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            probs = row.get("probabilities") or {}
            writer.writerow(
                {
                    "id": row["id"],
                    "expected_label": row["expected_label"],
                    "predicted_label": row["predicted_label"],
                    "correct": row["correct"],
                    "confidence_score": row["confidence_score"],
                    "blocked": row["blocked"],
                    "latency_ms": row["latency_ms"],
                    "category": row["category"],
                    "detail": row["detail"],
                    "mode": row["mode"],
                    "text_preview": row["text_preview"],
                    "error": row.get("error") or "",
                    "prob_TELECOM_WORKBENCH": probs.get("TELECOM_WORKBENCH", ""),
                    "prob_OUT_OF_SCOPE": probs.get("OUT_OF_SCOPE", ""),
                    "prob_PROMPT_INJECTION": probs.get("PROMPT_INJECTION", ""),
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--mode",
        choices=("full", "windows"),
        default="full",
        help="full=classify_prompt; windows=classify_prompt_with_windows",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write full JSON report (summary + per-id results)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Also write a flat CSV with one row per id",
    )
    parser.add_argument(
        "--failures-only",
        action="store_true",
        help="Only keep failed ids in the written report/CSV (console still shows all)",
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"Dataset not found: {args.dataset}", file=sys.stderr)
        return 2

    payload = run_per_id_eval(args.dataset, mode=args.mode, limit=args.limit)
    _print_summary(payload["summary"])

    results = payload["results"]
    export_results = (
        [r for r in results if not r["correct"]] if args.failures_only else results
    )
    export_payload = {
        "summary": payload["summary"],
        "results": export_results,
    }

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(export_payload, indent=2), encoding="utf-8")
        print(f"Wrote JSON report: {args.report}")

    if args.csv:
        _write_csv(args.csv, export_results)
        print(f"Wrote CSV report: {args.csv}")

    # Default report if neither path given
    if args.report is None and args.csv is None:
        default_report = (
            BACKEND_DIR
            / "Guardrails"
            / "Fine-tuning"
            / "reports"
            / "per_id_eval.json"
        )
        default_report.parent.mkdir(parents=True, exist_ok=True)
        default_report.write_text(json.dumps(export_payload, indent=2), encoding="utf-8")
        print(f"Wrote JSON report: {default_report}")

    return 0 if payload["summary"]["incorrect"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
