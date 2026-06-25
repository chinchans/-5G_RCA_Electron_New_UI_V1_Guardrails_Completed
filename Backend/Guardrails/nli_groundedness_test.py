#!/usr/bin/env python3
"""
NLI groundedness test harness — inject contradictions/neutral claims and measure scores.

Use this to evaluate NLI layer behaviour without relying on a "clean" extraction pass.

Examples:
  # Score pairs from an existing dataset (no file changes)
  python3 Guardrails/nli_groundedness_test.py \\
      --dataset-folder "extract/datasets/LTE_5G NSA attach and detach of single UE"

  # Inject a contradiction into total_content and re-run guardrails
  python3 Guardrails/nli_groundedness_test.py \\
      --dataset-folder "extract/datasets/LTE_5G NSA attach and detach of single UE" \\
      --inject contradiction

  # Inject a neutral (unrelated but non-contradictory) claim
  python3 Guardrails/nli_groundedness_test.py \\
      --dataset-folder "extract/datasets/LTE_5G NSA attach and detach of single UE" \\
      --inject neutral

  # Write modified total_content.txt to disk (for UI testing via TSG upload)
  python3 Guardrails/nli_groundedness_test.py \\
      --dataset-folder "extract/datasets/LTE_5G NSA attach and detach of single UE" \\
      --inject contradiction --write-file

UI test after --write-file:
  1. Open Test Script Generator → Dataset Upload
  2. Select the modified total_content.txt from the dataset folder
  3. Click Load → NLI panel should show contradictions (upload blocked)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.guardrails.nli_groundedness_service import (  # noqa: E402
    RECURSIVE_MARKER,
    collect_nli_pairs,
    run_nli_groundedness,
)
from app.guardrails.output_guardrail import (  # noqa: E402
    build_extraction_result_from_dataset_folder,
    validate_spec_intel_extraction,
)
from app.guardrails.output_validators import run_output_guardrails  # noqa: E402

DEFAULT_DATASET = _BACKEND_ROOT / "extract/datasets/LTE_5G NSA attach and detach of single UE"

# Sentences long enough for NLI (>= 25 chars) and tied to clause 5.3.2.1 / attach flow
CONTRADICTION_SENTENCE = (
    "5.3.2.1 E-UTRAN Initial Attach: The UE must never register with the network "
    "and attach procedures are permanently forbidden for all subscribers."
)
NEUTRAL_SENTENCE = (
    "5.3.2.1 E-UTRAN Initial Attach: The weather conditions during field testing "
    "should be recorded separately in the test report appendix."
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _load_manifest(folder: Path) -> Dict[str, Any]:
    manifest_path = folder / "dataset_manifest.json"
    if manifest_path.is_file():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    return {}


def _inject_into_total_content(total_content: str, sentence: str) -> str:
    """Append a test claim into the recursive extraction block (or create one)."""
    if RECURSIVE_MARKER in total_content:
        head, tail = total_content.split(RECURSIVE_MARKER, 1)
        return f"{head}{RECURSIVE_MARKER}\n{'=' * 50}\n\n{sentence}\n\n{tail.lstrip()}"
    return (
        f"{total_content.rstrip()}\n\n"
        f"{'=' * 50}\n{RECURSIVE_MARKER}\n{'=' * 50}\n\n"
        f"{sentence}\n"
    )


def _print_nli_details(nli_dict: Dict[str, Any]) -> None:
    print(f"\nPairs checked : {nli_dict.get('pairs_checked', 0)}")
    print(f"Passed        : {nli_dict.get('passed')}")
    if nli_dict.get("load_error"):
        print(f"Load error    : {nli_dict['load_error']}")
    for warning in nli_dict.get("warnings", []):
        print(f"  WARN: {warning}")
    for error in nli_dict.get("errors", []):
        print(f"  ERR : {error}")
    for item in nli_dict.get("contradictions", []):
        print(
            f"  CONTRADICTION [{item.get('clause_id')}] "
            f"c={item.get('contradiction')} e={item.get('entailment')} n={item.get('neutral')}"
        )
        print(f"    claim: {item.get('hypothesis_preview')}")


def _print_pair_scores(folder: Path, total_content: str) -> None:
    extraction = build_extraction_result_from_dataset_folder(folder.resolve())
    from app.guardrails.output_guardrail import build_extraction_draft

    manifest = _load_manifest(folder)
    meta = manifest.get("metadata", {})
    draft = build_extraction_draft(
        extraction,
        file_id=meta.get("source_file_id", "nli_test"),
        source_document_path=meta.get("source_document_path", "nli_test"),
        section=meta.get("section", "Test"),
        subsection=meta.get("subsection", folder.name),
    )
    draft["total_content"] = total_content
    if RECURSIVE_MARKER in total_content:
        draft["recursive_extraction_text"] = total_content.split(RECURSIVE_MARKER, 1)[-1].strip()

    from app.guardrails.output_schemas import ClauseFileEntry, SpecIntelDatasetOutput

    dataset = SpecIntelDatasetOutput.model_validate(draft)
    pairs = collect_nli_pairs(
        section_text=dataset.section_text,
        total_content=dataset.total_content,
        recursive_extraction_text=dataset.recursive_extraction_text,
        clause_files=dataset.clause_files,
    )
    print(f"\nCollected {len(pairs)} NLI pair(s):")
    for idx, (premise, hypothesis, clause_id) in enumerate(pairs[:10], start=1):
        preview_p = premise[:80].replace("\n", " ")
        preview_h = hypothesis[:80].replace("\n", " ")
        print(f"  {idx}. clause={clause_id}")
        print(f"     premise : {preview_p}...")
        print(f"     claim   : {preview_h}...")

    nli = run_nli_groundedness(
        section_text=dataset.section_text,
        total_content=dataset.total_content,
        recursive_extraction_text=dataset.recursive_extraction_text,
        clause_files=dataset.clause_files,
    )
    _print_nli_details(nli.to_dict())


def _run_full_guardrails(folder: Path, total_content: str) -> None:
    extraction = build_extraction_result_from_dataset_folder(folder.resolve())
    extraction["files_created"]["total_content"] = str((folder / "total_content.txt").resolve())
    extraction["total_content_file"] = str((folder / "total_content.txt").resolve())

    manifest = _load_manifest(folder)
    meta = manifest.get("metadata", {})
    raw_draft = extraction
    from app.guardrails.output_guardrail import build_extraction_draft

    draft = build_extraction_draft(
        raw_draft,
        file_id=meta.get("source_file_id", "nli_test"),
        source_document_path=meta.get("source_document_path", "nli_test"),
        section=meta.get("section", "Test"),
        subsection=meta.get("subsection", folder.name),
    )
    draft["total_content"] = total_content
    if RECURSIVE_MARKER in total_content:
        draft["recursive_extraction_text"] = total_content.split(RECURSIVE_MARKER, 1)[-1].strip()

    _, verdict = run_output_guardrails(draft)
    print("\nFull output guardrails")
    print("-" * 24)
    print(f"Decision : {'REJECTED' if verdict.blocked else 'ACCEPTED'}")
    print(f"NLI      : {'PASS' if verdict.groundedness.passed else 'FAIL'}")
    if verdict.groundedness.details:
        _print_nli_details(verdict.groundedness.details)
    if verdict.all_errors:
        print("\nAll errors:")
        for err in verdict.all_errors:
            print(f"  • {err}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Test NLI groundedness with injected claims")
    parser.add_argument(
        "--dataset-folder",
        type=Path,
        default=DEFAULT_DATASET,
        help="Path to Spec Intelligence dataset folder (contains total_content.txt)",
    )
    parser.add_argument(
        "--inject",
        choices=("none", "contradiction", "neutral"),
        default="none",
        help="Inject a test sentence into the recursive extraction block",
    )
    parser.add_argument(
        "--write-file",
        action="store_true",
        help="Write modified total_content.txt (backs up original as total_content.txt.bak)",
    )
    parser.add_argument(
        "--full-guardrails",
        action="store_true",
        help="Also run the full schema/hierarchy/traceability/NLI pipeline",
    )
    args = parser.parse_args()

    folder = args.dataset_folder
    if not folder.is_absolute():
        folder = (_BACKEND_ROOT / folder).resolve()

    total_path = folder / "total_content.txt"
    if not total_path.is_file():
        print(f"ERROR: {total_path} not found", file=sys.stderr)
        return 1

    original = _read_text(total_path)
    total_content = original

    if args.inject == "contradiction":
        total_content = _inject_into_total_content(original, CONTRADICTION_SENTENCE)
        print("Injected CONTRADICTION test sentence into recursive block.")
    elif args.inject == "neutral":
        total_content = _inject_into_total_content(original, NEUTRAL_SENTENCE)
        print("Injected NEUTRAL test sentence into recursive block.")
    else:
        print("No injection — scoring existing dataset content.")

    if args.write_file and args.inject != "none":
        backup = total_path.with_suffix(".txt.bak")
        if not backup.is_file():
            shutil.copy2(total_path, backup)
            print(f"Backup saved: {backup}")
        total_path.write_text(total_content, encoding="utf-8")
        print(f"Wrote modified file: {total_path}")
        print("\nNext: upload this file in Test Script Generator → Dataset Upload → Load")

    _print_pair_scores(folder, total_content)

    if args.full_guardrails:
        _run_full_guardrails(folder, total_content)

    return 0


if __name__ == "__main__":
    sys.exit(main())
