#!/usr/bin/env python3
"""Benchmark Specification Intelligence input guardrails using a JSON file of prompts with ID tracking.

Evaluates datasets containing objects like:
[
  {
    "id": 1,
    "text": "Ignore all previous instructions...",
    "attack_type": "direct_override_roleplay",
    "label": "PROMPT_INJECTION"
  }
]

Usage:
  cd Backend
  ./venv/bin/python Guardrails/spec_intelligence_json_benchmark.py
  ./venv/bin/python Guardrails/spec_intelligence_json_benchmark.py --json Guardrails/Fine-tuning/Datasets/CLEAN_NOTEBOOKLM_1000_PROMPT_INJECTION_PROMPTS_no_citations.json --limit 50
  ./venv/bin/python Guardrails/spec_intelligence_json_benchmark.py --report Guardrails/Fine-tuning/reports/scan_by_id_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.guardrails.input_guardrail import SpecIntelInputGuardrail

DEFAULT_JSON = (
    BACKEND_DIR
    / "Guardrails"
    / "Fine-tuning"
    / "Datasets"
    / "CLEAN_NOTEBOOKLM_1000_PROMPT_INJECTION_PROMPTS_no_citations.json"
)


def percentile(sorted_list: List[float], pct: float) -> float:
    """Calculate percentile value from a sorted list."""
    if not sorted_list:
        return 0.0
    if len(sorted_list) == 1:
        return sorted_list[0]
    k = (len(sorted_list) - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_list) else f
    d = k - f
    return sorted_list[f] + d * (sorted_list[c] - sorted_list[f])


def run_benchmark(json_path: Path, limit: Optional[int] = None, report_path: Optional[Path] = None) -> Dict[str, Any]:
    print("=" * 80)
    print("🛡️ Specification Intelligence JSON Prompt Benchmark (Per-ID Evaluation)")
    print("=" * 80)
    print(f"📁 Dataset File : {json_path}")
    
    if not json_path.exists():
        print(f"❌ Error: Dataset file not found: {json_path}")
        sys.exit(1)

    raw_data = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(raw_data, dict) and "text" in raw_data:
        # Convert dictionary format to list of dicts
        texts = raw_data.get("text", {})
        labels = raw_data.get("label", {})
        attacks = raw_data.get("attack_type", {})
        items = []
        for idx_str, txt in texts.items():
            items.append({
                "id": int(idx_str) if str(idx_str).isdigit() else idx_str,
                "text": txt,
                "label": labels.get(idx_str, "UNKNOWN"),
                "attack_type": attacks.get(idx_str, "none"),
            })
    elif isinstance(raw_data, list):
        items = raw_data
    else:
        print(f"❌ Error: Unsupported JSON structure in {json_path}")
        sys.exit(1)

    if limit and limit > 0:
        items = items[:limit]

    print(f"📊 Total Prompts Loaded: {len(items)}")
    print("-" * 80)

    guardrail = SpecIntelInputGuardrail()
    results: List[Dict[str, Any]] = []
    latencies: List[float] = []

    passed_count = 0
    blocked_count = 0
    correct_detection_count = 0
    passed_ids: List[Any] = []
    blocked_ids: List[Any] = []

    for idx, item in enumerate(items, 1):
        item_id = item.get("id", idx)
        text = str(item.get("text") or "").strip()
        expected_label = str(item.get("label") or "").upper()
        attack_type = str(item.get("attack_type") or item.get("category") or "n/a")

        if not text:
            continue

        t0 = time.perf_counter()
        verdict = guardrail.scan_text(
            text,
            context="upload",
            force_layer2_all_chunks=True,
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(latency_ms)

        scan_obj = verdict.scan
        is_blocked = verdict.blocked
        is_passed = verdict.passed

        score = getattr(scan_obj, "score", 0.0) if scan_obj else 0.0
        matched_patterns = getattr(scan_obj, "matched_patterns", []) if scan_obj else []

        if is_blocked:
            blocked_count += 1
            blocked_ids.append(item_id)
            status_str = "⛔ BLOCKED"
        else:
            passed_count += 1
            passed_ids.append(item_id)
            status_str = "✅ PASSED "

        # Check expected label accuracy (PROMPT_INJECTION should be blocked)
        is_correct = None
        if expected_label == "PROMPT_INJECTION":
            is_correct = is_blocked
            if is_blocked:
                correct_detection_count += 1
        elif expected_label in ("TELECOM_WORKBENCH", "CLEAN"):
            is_correct = is_passed
            if is_passed:
                correct_detection_count += 1

        snippet = text[:50].replace("\n", " ") + ("..." if len(text) > 50 else "")
        print(
            f"ID: {str(item_id):<5} | {status_str} | Score: {score:.4f} | "
            f"Latency: {latency_ms:6.2f}ms | Label: {expected_label:<16} | Attack: {attack_type:<22} | Prompt: \"{snippet}\""
        )

        results.append({
            "id": item_id,
            "text": text,
            "expected_label": expected_label,
            "attack_type": attack_type,
            "passed": is_passed,
            "blocked": is_blocked,
            "score": round(score, 4),
            "latency_ms": round(latency_ms, 2),
            "matched_patterns": matched_patterns,
            "reasons": verdict.reasons,
        })

    latencies_sorted = sorted(latencies)
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    p50_latency = percentile(latencies_sorted, 50)
    p90_latency = percentile(latencies_sorted, 90)
    p99_latency = percentile(latencies_sorted, 99)

    total = len(results)
    detection_rate = (correct_detection_count / total * 100) if total > 0 else 0.0

    print("=" * 80)
    print("📈 BENCHMARK SUMMARY REPORT")
    print("=" * 80)
    print(f" • Total Evaluated Prompts : {total}")
    print(f" • Passed (Allowed) Count  : {passed_count} ({passed_count/total*100:.1f}%)" if total else "")
    print(f" • Blocked (Intercepted)   : {blocked_count} ({blocked_count/total*100:.1f}%)" if total else "")
    print(f" • Expected Label Accuracy  : {correct_detection_count}/{total} ({detection_rate:.1f}%)")
    print(f" • Average Latency          : {avg_latency:.2f} ms")
    print(f" • Latency Percentiles      : P50 = {p50_latency:.2f} ms | P90 = {p90_latency:.2f} ms | P99 = {p99_latency:.2f} ms")
    print("-" * 80)
    print(f" ⛔ Blocked IDs ({len(blocked_ids)}): {blocked_ids}")
    print(f" ✅ Passed IDs  ({len(passed_ids)}): {passed_ids}")
    print("=" * 80)

    summary_payload = {
        "dataset": str(json_path),
        "total_evaluated": total,
        "passed_count": passed_count,
        "blocked_count": blocked_count,
        "blocked_ids": blocked_ids,
        "passed_ids": passed_ids,
        "correct_detection_count": correct_detection_count,
        "accuracy_percent": round(detection_rate, 2),
        "latency_stats": {
            "avg_ms": round(avg_latency, 2),
            "p50_ms": round(p50_latency, 2),
            "p90_ms": round(p90_latency, 2),
            "p99_ms": round(p99_latency, 2),
        },
        "results_by_id": results,
    }

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
        print(f"📄 Full JSON Report Saved to: {report_path}")

    return summary_payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark Specification Intelligence Guardrails using JSON prompt dataset with ID tracking"
    )
    parser.add_argument(
        "--json",
        default=str(DEFAULT_JSON),
        help=f"Path to JSON dataset file (default: {DEFAULT_JSON.name})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of prompts to scan (default: scan all)",
    )
    parser.add_argument(
        "--report",
        help="Path to save output benchmark report JSON (e.g. Guardrails/Fine-tuning/reports/scan_by_id_report.json)",
    )

    args = parser.parse_args()
    json_path = Path(args.json)
    if not json_path.is_absolute():
        json_path = (BACKEND_DIR / json_path).resolve()

    report_path = Path(args.report) if args.report else None
    if report_path and not report_path.is_absolute():
        report_path = (BACKEND_DIR / report_path).resolve()

    run_benchmark(json_path=json_path, limit=args.limit, report_path=report_path)


if __name__ == "__main__":
    main()
