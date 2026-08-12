#!/usr/bin/env python3
"""Batch document scanner for Specification Intelligence input guardrails.

Recursively scans all adversarial documents (.docx, .pdf, .txt, .doc) in a directory
(e.g., Backend/Guardrails/Prompt Injection & Jailbreaking Testing) and generates a 
per-file & per-folder block/pass security report.

Usage:
  cd Backend
  ./venv/bin/python Guardrails/batch_document_guardrail_test.py
  ./venv/bin/python Guardrails/batch_document_guardrail_test.py --mode api
  ./venv/bin/python Guardrails/batch_document_guardrail_test.py --dir "Guardrails/Prompt Injection & Jailbreaking Testing/Level 1"
  ./venv/bin/python Guardrails/batch_document_guardrail_test.py --report Guardrails/reports/document_benchmark_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_DOCS_DIR = (
    BACKEND_DIR
    / "Guardrails"
    / "Prompt Injection & Jailbreaking Testing"
    / "Tests"
)
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".html", ".htm"}


def scan_file_local(file_path: Path, guardrail: Any) -> Dict[str, Any]:
    """Scan a single document file using local SpecIntelInputGuardrail python engine."""
    t0 = time.perf_counter()
    try:
        verdict = guardrail.scan_file(file_path, context="upload")
        latency_ms = (time.perf_counter() - t0) * 1000.0
        scan_obj = verdict.scan
        score = getattr(scan_obj, "score", 0.0) if scan_obj else 0.0
        chunks_scanned = getattr(scan_obj, "chunks_scanned", 0) if scan_obj else 0
        unsafe_chunks = getattr(scan_obj, "unsafe_chunks", 0) if scan_obj else 0
        matched_patterns = getattr(scan_obj, "matched_patterns", []) if scan_obj else []

        return {
            "file": str(file_path.name),
            "rel_path": str(file_path.relative_to(BACKEND_DIR)),
            "folder": file_path.parent.name,
            "size_bytes": file_path.stat().st_size,
            "passed": verdict.passed,
            "blocked": verdict.blocked,
            "latency_ms": round(latency_ms, 2),
            "score": round(score, 4),
            "chunks_scanned": chunks_scanned,
            "unsafe_chunks": unsafe_chunks,
            "matched_patterns": matched_patterns,
            "reasons": verdict.reasons,
            "error": None,
        }
    except Exception as exc:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "file": str(file_path.name),
            "rel_path": str(file_path.relative_to(BACKEND_DIR)),
            "folder": file_path.parent.name,
            "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
            "passed": False,
            "blocked": True,
            "latency_ms": round(latency_ms, 2),
            "score": 0.0,
            "chunks_scanned": 0,
            "unsafe_chunks": 0,
            "matched_patterns": [],
            "reasons": [str(exc)],
            "error": str(exc),
        }


def scan_file_api(file_path: Path, server_url: str) -> Dict[str, Any]:
    """Scan a document file via HTTP POST /api/dataset/upload-document."""
    import requests

    upload_url = f"{server_url.rstrip('/')}/api/dataset/upload-document"
    t0 = time.perf_counter()
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            resp = requests.post(upload_url, files=files, timeout=300)
        
        latency_ms = (time.perf_counter() - t0) * 1000.0

        if resp.status_code == 200:
            data = resp.json()
            guard_data = data.get("guardrails", {})
            scan_info = guard_data.get("scan", {}) or {}
            return {
                "file": str(file_path.name),
                "rel_path": str(file_path.relative_to(BACKEND_DIR)),
                "folder": file_path.parent.name,
                "size_bytes": file_path.stat().st_size,
                "passed": True,
                "blocked": False,
                "latency_ms": round(latency_ms, 2),
                "score": round(scan_info.get("score") or 0.0, 4),
                "chunks_scanned": scan_info.get("chunks_scanned", 0),
                "unsafe_chunks": scan_info.get("unsafe_chunks", 0),
                "matched_patterns": scan_info.get("matched_patterns", []),
                "reasons": [],
                "error": None,
            }
        elif resp.status_code in (400, 422):
            data = resp.json()
            detail = data.get("detail")
            reasons = detail.get("reasons", []) if isinstance(detail, dict) else [str(detail)]
            return {
                "file": str(file_path.name),
                "rel_path": str(file_path.relative_to(BACKEND_DIR)),
                "folder": file_path.parent.name,
                "size_bytes": file_path.stat().st_size,
                "passed": False,
                "blocked": True,
                "latency_ms": round(latency_ms, 2),
                "score": 0.99,
                "chunks_scanned": 1,
                "unsafe_chunks": 1,
                "matched_patterns": [],
                "reasons": reasons,
                "error": None,
            }
        else:
            return {
                "file": str(file_path.name),
                "rel_path": str(file_path.relative_to(BACKEND_DIR)),
                "folder": file_path.parent.name,
                "size_bytes": file_path.stat().st_size,
                "passed": False,
                "blocked": True,
                "latency_ms": round(latency_ms, 2),
                "score": 0.0,
                "chunks_scanned": 0,
                "unsafe_chunks": 0,
                "matched_patterns": [],
                "reasons": [f"HTTP {resp.status_code}: {resp.text}"],
                "error": f"HTTP {resp.status_code}",
            }
    except Exception as exc:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "file": str(file_path.name),
            "rel_path": str(file_path.relative_to(BACKEND_DIR)),
            "folder": file_path.parent.name,
            "size_bytes": file_path.stat().st_size,
            "passed": False,
            "blocked": True,
            "latency_ms": round(latency_ms, 2),
            "score": 0.0,
            "chunks_scanned": 0,
            "unsafe_chunks": 0,
            "matched_patterns": [],
            "reasons": [str(exc)],
            "error": str(exc),
        }


def run_batch_scan(
    docs_dir: Path,
    mode: str = "local",
    server_url: str = "http://localhost:8000",
    report_path: Optional[Path] = None,
) -> Dict[str, Any]:
    print("=" * 80)
    print("🛡️ Specification Intelligence Batch Document Guardrail Benchmark")
    print("=" * 80)
    print(f"📁 Target Directory : {docs_dir}")
    print(f"⚡ Scan Mode        : {mode.upper()}")

    if not docs_dir.exists():
        print(f"❌ Error: Directory not found: {docs_dir}")
        sys.exit(1)

    # Discover document files recursively
    all_files = [
        p for p in docs_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS and not p.name.startswith(".~")
    ]
    all_files.sort(key=lambda p: (p.parent.name, p.name))

    if not all_files:
        print(f"⚠️ No matching document files ({', '.join(ALLOWED_EXTENSIONS)}) found in {docs_dir}")
        sys.exit(1)

    print(f"📊 Found {len(all_files)} documents across {len(set(p.parent.name for p in all_files))} subfolder(s)")
    print("-" * 80)

    guardrail = None
    if mode == "local":
        from app.guardrails.input_guardrail import SpecIntelInputGuardrail
        print("⏳ Initializing SpecIntelInputGuardrail engine...")
        guardrail = SpecIntelInputGuardrail()

    results: List[Dict[str, Any]] = []
    folder_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "blocked": 0, "passed": 0})

    for idx, file_path in enumerate(all_files, 1):
        folder_name = file_path.parent.name
        print(f"[{idx:02d}/{len(all_files):02d}] Scanning {file_path.relative_to(docs_dir)}...", end="", flush=True)

        if mode == "local":
            res = scan_file_local(file_path, guardrail)
        else:
            res = scan_file_api(file_path, server_url)

        results.append(res)
        folder_stats[folder_name]["total"] += 1

        if res["blocked"]:
            folder_stats[folder_name]["blocked"] += 1
            status_tag = "⛔ BLOCKED"
        else:
            folder_stats[folder_name]["passed"] += 1
            status_tag = "✅ PASSED "

        print(f"\r[{idx:02d}/{len(all_files):02d}] {status_tag} | {file_path.name:<32} | Score: {res['score']:.4f} | Latency: {res['latency_ms']:7.2f}ms")

    # Aggregate Statistics
    total_docs = len(results)
    total_blocked = sum(1 for r in results if r["blocked"])
    total_passed = sum(1 for r in results if r["passed"])
    avg_latency = sum(r["latency_ms"] for r in results) / total_docs if total_docs else 0.0

    print("\n" + "=" * 80)
    print("📈 BATCH DOCUMENT SCAN SUMMARY REPORT")
    print("=" * 80)
    print(f" • Total Documents Scanned : {total_docs}")
    print(f" • Intercepted / Blocked   : {total_blocked} ({total_blocked/total_docs*100:.1f}%)")
    print(f" • Passed / Allowed        : {total_passed} ({total_passed/total_docs*100:.1f}%)")
    print(f" • Average Scan Latency    : {avg_latency:.2f} ms")
    print("-" * 80)
    print("📂 BREAKDOWN BY CATEGORY / FOLDER:")
    print(f"{'Folder Name':<30} | {'Total':<7} | {'Blocked':<9} | {'Passed':<8} | {'Block Rate':<10}")
    print("-" * 75)
    for folder, stats in sorted(folder_stats.items()):
        tot = stats["total"]
        blk = stats["blocked"]
        pas = stats["passed"]
        rate = (blk / tot * 100.0) if tot else 0.0
        print(f"{folder:<30} | {tot:<7} | {blk:<9} | {pas:<8} | {rate:6.1f}%")

    print("=" * 80)

    summary_payload = {
        "target_directory": str(docs_dir),
        "mode": mode,
        "total_documents": total_docs,
        "total_blocked": total_blocked,
        "total_passed": total_passed,
        "block_rate_percent": round((total_blocked / total_docs * 100) if total_docs else 0.0, 2),
        "average_latency_ms": round(avg_latency, 2),
        "folder_breakdown": dict(folder_stats),
        "results": results,
    }

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
        print(f"📄 Detailed Report JSON saved to: {report_path}")

    return summary_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch Document Guardrail Benchmark")
    parser.add_argument(
        "--dir",
        default=str(DEFAULT_DOCS_DIR),
        help=f"Directory containing test documents (default: {DEFAULT_DOCS_DIR.name})",
    )
    parser.add_argument(
        "--mode",
        choices=["local", "api"],
        default="local",
        help="Scanning mode: 'local' (direct Python engine) or 'api' (HTTP POST /api/dataset/upload-document)",
    )
    parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="Backend server URL for --mode api (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--report",
        default="Guardrails/reports/batch_document_scan_report.json",
        help="Path to save JSON benchmark report",
    )

    args = parser.parse_args()
    docs_dir = Path(args.dir)
    if not docs_dir.is_absolute():
        docs_dir = (BACKEND_DIR / docs_dir).resolve()

    report_path = Path(args.report) if args.report else None
    if report_path and not report_path.is_absolute():
        report_path = (BACKEND_DIR / report_path).resolve()

    run_batch_scan(
        docs_dir=docs_dir,
        mode=args.mode,
        server_url=args.server,
        report_path=report_path,
    )


if __name__ == "__main__":
    main()
