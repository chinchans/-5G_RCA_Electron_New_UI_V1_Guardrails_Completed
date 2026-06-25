#!/usr/bin/env python3
"""
Output Guardrails — JSON examples for Specification Intelligence.

Shows one valid extraction payload (ACCEPTED) and one invalid payload (REJECTED),
then runs both through the validation pipeline.

Usage:
    python spec_intelligence_output_guardrails_test.py
    python spec_intelligence_output_guardrails_test.py --json-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.guardrails.output_validators import run_output_guardrails

# ---------------------------------------------------------------------------
# Shared O-RAN context (LTE/5G NSA attach and detach of single UE)
# ---------------------------------------------------------------------------

_SECTION = "5 Test cases"
_SUBSECTION = "LTE/5G NSA attach and detach of single UE"
_SECTION_TEXT = (
    "LTE/5G NSA attach and detach of single UE\n"
    "The purpose of this test is to validate E2E O-RAN C-plane functionality "
    "with a single UE, as described in 3GPP TS 23.401 Clause 5.3.2.1."
)
_CLAUSE_TEXT = (
    "5.3.2.1 E-UTRAN Initial Attach\n"
    "A UE needs to register with the network to receive services (3GPP TS 23.401)."
)

# =============================================================================
# EXAMPLE 1 — Valid extraction output (passes all validators → ACCEPTED)
# =============================================================================

VALID_EXTRACTION_JSON: Dict[str, Any] = {
    "metadata": {
        "source_file_id": "O-RAN.WG1.TIFG-E2E-TestSpecification-R003-v06.00.docx",
        "source_document_path": "/tmp/uploaded_docs/oran-e2e-test.docx",
        "section": _SECTION,
        "subsection": _SUBSECTION,
        "safe_subsection": "LTE_5G NSA attach and detach of single UE",
        "dataset_folder": "/tmp/datasets/LTE_5G_NSA_attach",
    },
    "section_text": _SECTION_TEXT,
    "references": [
        {
            "reference": "3GPP TS 23.401",
            "clauses": ["5.3.2.1"],
            "source_file": "23401-i00.txt",
            "status": "present",
        }
    ],
    "clauses": ["5.3.2.1"],
    "present_references": ["23401-i00.txt"],
    "missing_references": [],
    "ref_clause_map": {"3GPP TS 23.401": ["5.3.2.1"]},
    "graph": {
        "directed": True,
        "multigraph": False,
        "nodes": [
            {"id": "start"},
            {"id": "3GPP TS 23.401"},
            {"id": "5.3.2.1"},
        ],
        "edges": [
            {"source": "start", "target": "3GPP TS 23.401"},
            {"source": "3GPP TS 23.401", "target": "5.3.2.1"},
        ],
    },
    "total_content": _SECTION_TEXT + "\n\n" + _CLAUSE_TEXT,
    "clause_files": [
        {
            "clause_id": "5.3.2.1",
            "file_path": "/tmp/datasets/LTE_5G_NSA_attach/5_3_2_1_file.txt",
            "source_reference": "3GPP TS 23.401",
            "content": _CLAUSE_TEXT,
            "traceable": True,
        }
    ],
}

# =============================================================================
# EXAMPLE 2 — Invalid extraction output (fails validators → REJECTED)
# Intentionally corrupted for testing — not normal system behaviour.
# =============================================================================

INVALID_EXTRACTION_JSON: Dict[str, Any] = {
    "metadata": {
        "source_file_id": "",  # ✗ missing required document id
        "source_document_path": "/tmp/bad.docx",
        "section": _SECTION,
        "subsection": _SUBSECTION,
        "safe_subsection": "LTE_5G NSA attach and detach of single UE",
        "dataset_folder": "/tmp/datasets/LTE_5G_NSA_attach",
    },
    "section_text": _SECTION_TEXT,
    "references": [
        {
            "reference": "3GPP TS 23.401",
            "clauses": ["E-UTRAN Initial Attach"],  # ✗ not a clause number
            "source_file": "23401-i00.txt",
            "status": "present",
        }
    ],
    "clauses": ["5.3.2.1"],
    "present_references": ["23401-i00.txt"],
    "missing_references": [],
    "ref_clause_map": {
        "3GPP TS 23.401": ["E-UTRAN Initial Attach"],  # ✗ invalid hierarchy
    },
    "graph": {
        "directed": True,
        "multigraph": False,
        "nodes": [{"id": "3GPP TS 23.401"}],  # ✗ missing "start" node
        "edges": [],
    },
    "total_content": "Unrelated text — not traceable to source.",  # ✗ traceability
    "clause_files": [
        {
            "clause_id": "5.3.2.1",
            "file_path": "/tmp/datasets/LTE_5G_NSA_attach/5_3_2_1_file.txt",
            "source_reference": None,
            "content": "N/A",
            "traceable": False,
        }
    ],
}


def print_json_block(title: str, payload: Dict[str, Any]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    print(json.dumps(payload, indent=2))


def print_verdict(label: str, payload: Dict[str, Any], expect_blocked: bool) -> bool:
    _, verdict = run_output_guardrails(payload)
    ok = verdict.blocked == expect_blocked

    print(f"\n{label}")
    print("-" * len(label))
    print(f"Decision : {'REJECTED' if verdict.blocked else 'ACCEPTED'}")
    print(f"Schema   : {'PASS' if verdict.schema.passed else 'FAIL'}")
    print(f"Hierarchy: {'PASS' if verdict.hierarchy.passed else 'FAIL'}")
    print(f"Trace    : {'PASS' if verdict.traceability.passed else 'FAIL'}")
    print(f"NLI      : {'PASS' if verdict.groundedness.passed else 'FAIL'}")

    if verdict.all_errors:
        print("Errors:")
        for err in verdict.all_errors:
            print(f"  • {err}")

    if verdict.groundedness.warnings:
        print("NLI warnings:")
        for warn in verdict.groundedness.warnings:
            print(f"  • {warn}")

    print(f"Result   : {'OK' if ok else 'UNEXPECTED'}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Output guardrails JSON examples")
    parser.add_argument("--json-only", action="store_true", help="Print JSON examples only")
    args = parser.parse_args()

    print("Specification Intelligence — Output Guardrails JSON Examples")
    print_json_block("VALID extraction output (expected: ACCEPTED)", VALID_EXTRACTION_JSON)
    print_json_block("INVALID extraction output (expected: REJECTED)", INVALID_EXTRACTION_JSON)

    if args.json_only:
        return 0

    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)

    ok_valid = print_verdict("Test Case 1", VALID_EXTRACTION_JSON, expect_blocked=False)
    ok_invalid = print_verdict("Test Case 2", INVALID_EXTRACTION_JSON, expect_blocked=True)

    return 0 if ok_valid and ok_invalid else 1


if __name__ == "__main__":
    sys.exit(main())
