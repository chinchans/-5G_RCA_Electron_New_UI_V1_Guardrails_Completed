#!/usr/bin/env python3
"""Benchmark and test Specification Intelligence API endpoints for input guardrails without UI.

Endpoint under test:
  - GET  /api/dataset/guardrails/status
  - POST /api/dataset/upload-document

Usage:
  1. Start backend server:
     cd Backend
     ./venv/bin/python main.py

  2. In another terminal, run this test:
     ./venv/bin/python Guardrails/spec_intelligence_upload_api_test.py
     ./venv/bin/python Guardrails/spec_intelligence_upload_api_test.py --file path/to/document.docx
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' module not found. Install it via: pip install requests")
    sys.exit(1)

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SERVER_URL = "http://localhost:8000"


def check_guardrails_status(server_url: str) -> bool:
    """Test GET /api/dataset/guardrails/status."""
    status_url = f"{server_url.rstrip('/')}/api/dataset/guardrails/status"
    print(f"\n🔍 Checking Guardrail Status: {status_url}")
    try:
        t0 = time.perf_counter()
        resp = requests.get(status_url, timeout=5)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        if resp.status_code == 200:
            data = resp.json()
            guardrails_info = data.get("guardrails", {})
            print(f"✅ Status Check Passed (HTTP 200 - {latency_ms:.2f} ms)")
            print(f"   • Enabled      : {guardrails_info.get('enabled')}")
            print(f"   • Backend      : {guardrails_info.get('backend')}")
            print(f"   • Model Loaded : {guardrails_info.get('model_loaded')}")
            print(f"   • Threshold    : {guardrails_info.get('threshold')}")
            return True
        else:
            print(f"❌ Status Check Failed (HTTP {resp.status_code}): {resp.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error: Cannot connect to {server_url}.")
        print("   Please start the backend server first: cd Backend && ./venv/bin/python main.py")
        return False
    except Exception as exc:
        print(f"❌ Error checking status: {exc}")
        return False


def test_upload_document(server_url: str, file_path: Path) -> bool:
    """Test POST /api/dataset/upload-document."""
    upload_url = f"{server_url.rstrip('/')}/api/dataset/upload-document"
    print(f"\n📤 Testing Document Upload & Input Guardrail Scan")
    print(f"   • Target File : {file_path}")
    print(f"   • File Size   : {file_path.stat().st_size:,} bytes")

    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}")
        return False

    t0 = time.perf_counter()
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            resp = requests.post(upload_url, files=files, timeout=300)
        
        latency_ms = (time.perf_counter() - t0) * 1000.0

        if resp.status_code == 200:
            data = resp.json()
            guard_data = data.get("guardrails", {})
            scan_data = guard_data.get("scan", {}) or {}
            print(f"✅ Upload & Scan Completed (HTTP 200 - {latency_ms:.2f} ms)")
            print(f"   • File ID        : {data.get('file_id')}")
            print(f"   • Verdict Passed : {guard_data.get('passed')}")
            print(f"   • Verdict Blocked: {guard_data.get('blocked')}")
            print(f"   • Scan Safe      : {scan_data.get('safe')}")
            print(f"   • Injection Score: {scan_data.get('score')}")
            print(f"   • Chunks Scanned : {scan_data.get('chunks_scanned')}")
            print(f"   • Unsafe Chunks  : {scan_data.get('unsafe_chunks')}")
            return True
        elif resp.status_code in (400, 422):
            data = resp.json()
            print(f"⛔ UPLOAD BLOCKED BY GUARDRAIL (HTTP {resp.status_code} - {latency_ms:.2f} ms)")
            detail = data.get("detail")
            if isinstance(detail, dict):
                print(f"   • Reason : {detail.get('message')}")
                print(f"   • Details: {detail.get('reasons')}")
            else:
                print(f"   • Detail : {detail}")
            return True
        else:
            print(f"❌ Unexpected Error (HTTP {resp.status_code} - {latency_ms:.2f} ms)")
            print(f"   • Response: {resp.text}")
            return False

    except Exception as exc:
        print(f"❌ Upload Error: {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Specification Intelligence Upload API & Input Guardrails")
    parser.add_argument("--server", default=DEFAULT_SERVER_URL, help="Backend server URL (default: http://localhost:8000)")
    parser.add_argument("--file", help="Path to specification document file to upload")
    args = parser.parse_args()

    print("=" * 70)
    print("🛡️ Specification Intelligence API Guardrail Test Suite")
    print("=" * 70)

    server_running = check_guardrails_status(args.server)
    if not server_running:
        sys.exit(1)

    if args.file:
        test_file = Path(args.file)
    else:
        # Default test fixture file
        test_file = BACKEND_DIR / "Guardrails" / "Bug Discovery" / "ue_rach_failure_test.log"

    if test_file.exists():
        test_upload_document(args.server, test_file)
    else:
        print(f"\n⚠️ Default test file not found at {test_file}. Pass a file using --file path/to/doc.docx")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
