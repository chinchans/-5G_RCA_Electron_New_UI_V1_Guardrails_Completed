#!/usr/bin/env python3
"""Offline accuracy + latency eval for the fine-tuned RoBERTa guardrail classifier.

Uses labeled prompts under Datasets/ (default: CLEAN_NOTEBOOKLM_3370_MERGED_PROMPTS.json).

Examples:
  cd Backend
  ./venv/bin/python Guardrails/Fine-tuning/eval_guardrail_classifier.py
  ./venv/bin/python Guardrails/Fine-tuning/eval_guardrail_classifier.py --limit 200 --mode windows
  ./venv/bin/python Guardrails/Fine-tuning/eval_guardrail_classifier.py --report /tmp/roberta_eval.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_DATASET = (
    BACKEND_DIR
    / "Guardrails"
    / "Fine-tuning"
    / "Datasets"
    / "Testng_prompts"
    / "TESTING_PROMPTS_NOTEBOOKLM_OUT_OF_SCOPE_no_citations.json"
)

LABELS = ("TELECOM_WORKBENCH", "OUT_OF_SCOPE", "PROMPT_INJECTION")


def _load_records(path: Path) -> List[Dict[str, str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    records: List[Dict[str, str]] = []

    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            label = str(item.get("label") or "").strip().upper()
            if text and label:
                records.append({"text": text, "label": label})
        return records

    if not isinstance(raw, dict) or "text" not in raw or "label" not in raw:
        raise ValueError(
            f"Unsupported dataset shape in {path}. "
            "Expected list of {{text,label}} or pandas column-oriented JSON."
        )

    texts = raw["text"]
    labels = raw["label"]
    if isinstance(texts, dict) and isinstance(labels, dict):
        for key in texts:
            text = str(texts.get(key) or "").strip()
            label = str(labels.get(key) or "").strip().upper()
            if text and label:
                records.append({"text": text, "label": label})
        return records

    if isinstance(texts, list) and isinstance(labels, list):
        for text, label in zip(texts, labels):
            t = str(text or "").strip()
            lab = str(label or "").strip().upper()
            if t and lab:
                records.append({"text": t, "label": lab})
        return records

    raise ValueError(f"Could not parse text/label columns from {path}")


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


def _percentile(sorted_values: Sequence[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return float(sorted_values[f])
    return float(sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f))


def _metrics(
    y_true: List[str],
    y_pred: List[str],
) -> Dict[str, Any]:
    total = len(y_true)
    correct = sum(1 for a, b in zip(y_true, y_pred) if a == b)
    accuracy = (correct / total) if total else 0.0

    confusion: Dict[str, Dict[str, int]] = {
        actual: {pred: 0 for pred in LABELS} for actual in LABELS
    }
    for actual, pred in zip(y_true, y_pred):
        if actual not in confusion:
            confusion[actual] = {p: 0 for p in LABELS}
        if pred not in confusion[actual]:
            confusion[actual][pred] = 0
        confusion[actual][pred] += 1

    per_class: Dict[str, Dict[str, float]] = {}
    for label in LABELS:
        tp = confusion.get(label, {}).get(label, 0)
        fp = sum(
            confusion.get(other, {}).get(label, 0)
            for other in LABELS
            if other != label
        )
        fn = sum(
            confusion.get(label, {}).get(other, 0)
            for other in LABELS
            if other != label
        )
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            (2 * precision * recall / (precision + recall))
            if (precision + recall)
            else 0.0
        )
        support = sum(confusion.get(label, {}).values())
        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }

    return {
        "total": total,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "per_class": per_class,
        "confusion": confusion,
    }


def _predict_one(text: str, mode: str) -> Tuple[str, float, bool]:
    from app.guardrails.guardrail_classifier import (
        classify_prompt,
        classify_prompt_with_windows,
    )

    if mode == "windows":
        result = classify_prompt_with_windows(text)
        return result.predicted_label, float(result.confidence_score), bool(result.blocked)

    result = classify_prompt(text)
    # full-text mode: blocked = confident OOS / injection (mirrors coarse production rule)
    from app.guardrails.guardrail_classifier import (
        LABEL_OUT_OF_SCOPE,
        LABEL_PROMPT_INJECTION,
        _is_confident_label,
    )
    from app.guardrails.config import GUARDRAIL_CLASSIFIER_INJECTION_MAX_CHARS

    blocked = _is_confident_label(result, LABEL_OUT_OF_SCOPE) or (
        _is_confident_label(result, LABEL_PROMPT_INJECTION)
        and len(text.strip()) <= GUARDRAIL_CLASSIFIER_INJECTION_MAX_CHARS
    )
    return result.predicted_label, float(result.confidence_score), blocked


def run_eval(
    dataset: Path,
    *,
    mode: str = "full",
    limit: Optional[int] = None,
    seed: int = 42,
    label_filter: Optional[str] = None,
) -> Dict[str, Any]:
    from app.guardrails.guardrail_classifier import ensure_guardrail_classifier_loaded

    records = _load_records(dataset)
    records = [
        {"text": r["text"], "label": _normalize_label(r["label"])}
        for r in records
        if _normalize_label(r["label"]) in LABELS
    ]
    if label_filter:
        want = _normalize_label(label_filter)
        records = [r for r in records if r["label"] == want]

    if not records:
        raise RuntimeError(f"No usable labeled rows in {dataset}")

    rng = random.Random(seed)
    rng.shuffle(records)
    if limit is not None and limit > 0:
        records = records[:limit]

    print(f"Dataset: {dataset}")
    print(f"Mode: {mode}  |  samples: {len(records)}  |  seed: {seed}")
    print(f"Label mix: {dict(Counter(r['label'] for r in records))}")
    print("Loading classifier…")
    ensure_guardrail_classifier_loaded()

    y_true: List[str] = []
    y_pred: List[str] = []
    latencies_ms: List[float] = []
    blocked_flags: List[bool] = []
    errors: List[Dict[str, Any]] = []

    for idx, row in enumerate(records, start=1):
        text = row["text"]
        actual = row["label"]
        t0 = time.perf_counter()
        try:
            pred, _conf, blocked = _predict_one(text, mode)
        except Exception as exc:  # noqa: BLE001 — collect and continue
            errors.append({"index": idx, "error": str(exc), "text": text[:120]})
            pred = "ERROR"
            blocked = False
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(elapsed_ms)
        y_true.append(actual)
        y_pred.append(pred)
        blocked_flags.append(blocked)

        if idx % 50 == 0 or idx == len(records):
            running_acc = sum(1 for a, b in zip(y_true, y_pred) if a == b) / len(y_true)
            print(f"  [{idx}/{len(records)}] running accuracy={running_acc:.3f}")

    # Drop ERROR rows from metrics (keep them in report)
    valid_pairs = [(a, b) for a, b in zip(y_true, y_pred) if b != "ERROR"]
    metrics = _metrics(
        [a for a, _ in valid_pairs],
        [b for _, b in valid_pairs],
    )
    lat_sorted = sorted(latencies_ms)
    latency = {
        "count": len(latencies_ms),
        "mean_ms": round(sum(latencies_ms) / len(latencies_ms), 2) if latencies_ms else 0.0,
        "p50_ms": round(_percentile(lat_sorted, 50), 2),
        "p95_ms": round(_percentile(lat_sorted, 95), 2),
        "max_ms": round(lat_sorted[-1], 2) if lat_sorted else 0.0,
    }

    # Expected block rate for OOS / injection labels under this mode
    expected_block = sum(1 for a in y_true if a in {"OUT_OF_SCOPE", "PROMPT_INJECTION"})
    actual_block = sum(1 for flag in blocked_flags if flag)

    report = {
        "dataset": str(dataset),
        "mode": mode,
        "seed": seed,
        "sample_count": len(records),
        "metrics": metrics,
        "latency_ms": latency,
        "blocked_count": actual_block,
        "expected_non_telecom_count": expected_block,
        "errors": errors[:20],
        "error_count": len(errors),
    }
    return report


def _print_report(report: Dict[str, Any]) -> None:
    m = report["metrics"]
    print("\n======== Guardrail classifier eval ========")
    print(f"Accuracy: {m['accuracy']:.4f}  ({m['correct']}/{m['total']})")
    print("\nPer-class:")
    for label, stats in m["per_class"].items():
        print(
            f"  {label:20s}  P={stats['precision']:.3f}  "
            f"R={stats['recall']:.3f}  F1={stats['f1']:.3f}  "
            f"n={stats['support']}"
        )
    print("\nConfusion (rows=actual, cols=predicted):")
    header = "actual\\pred".ljust(20) + "".join(f"{lab[:10]:>12}" for lab in LABELS)
    print(header)
    for actual in LABELS:
        row = actual[:20].ljust(20)
        for pred in LABELS:
            row += f"{m['confusion'].get(actual, {}).get(pred, 0):>12}"
        print(row)
    lat = report["latency_ms"]
    print(
        f"\nLatency ms: mean={lat['mean_ms']}  p50={lat['p50_ms']}  "
        f"p95={lat['p95_ms']}  max={lat['max_ms']}"
    )
    if report["error_count"]:
        print(f"Errors: {report['error_count']} (showing up to 20 in report JSON)")
    print("===========================================\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Path to labeled JSON dataset",
    )
    parser.add_argument(
        "--mode",
        choices=("full", "windows"),
        default="full",
        help="full=classify_prompt; windows=classify_prompt_with_windows (production TSG path)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only N shuffled samples")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--label",
        default=None,
        help="Optional single-label filter (TELECOM_WORKBENCH|OUT_OF_SCOPE|PROMPT_INJECTION)",
    )
    parser.add_argument("--report", type=Path, default=None, help="Write full JSON report here")
    parser.add_argument(
        "--min-accuracy",
        type=float,
        default=None,
        help="Exit non-zero if accuracy falls below this threshold (CI gate)",
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"Dataset not found: {args.dataset}", file=sys.stderr)
        return 2

    report = run_eval(
        args.dataset,
        mode=args.mode,
        limit=args.limit,
        seed=args.seed,
        label_filter=args.label,
    )
    _print_report(report)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote report: {args.report}")

    if args.min_accuracy is not None and report["metrics"]["accuracy"] < args.min_accuracy:
        print(
            f"FAIL: accuracy {report['metrics']['accuracy']} < min-accuracy {args.min_accuracy}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
