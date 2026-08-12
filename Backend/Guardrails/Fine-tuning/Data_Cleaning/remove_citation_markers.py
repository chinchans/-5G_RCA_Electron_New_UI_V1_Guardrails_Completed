#!/usr/bin/env python3
"""Remove citation markers like [1], [1, 2], [4, 5] from dataset prompt text,
and assign a stable sequential ``id`` to each data point.

Usage:
  cd Backend/Guardrails/Fine-tuning/Data_Cleaning
  python remove_citation_markers.py
  python remove_citation_markers.py --input ../Datasets/NOTEBOOKLM_1600_OUT_OF_SCOPE_PROMPTS.json
  python remove_citation_markers.py --input path/to/in.json --output path/to/out.json
  python remove_citation_markers.py --start-id 1
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Matches: [1]  [1, 2]  [4, 5]  [1,2,3]  (spaces optional)
CITATION_RE = re.compile(r"\s*\[\s*\d+(?:\s*,\s*\d+)*\s*\]")

# Collapse leftover double spaces after removal
SPACE_RE = re.compile(r"[ \t]{2,}")


def clean_text(text: str) -> str:
    cleaned = CITATION_RE.sub("", text or "")
    cleaned = SPACE_RE.sub(" ", cleaned)
    # tidy spaces before punctuation: "vibes ." -> "vibes."
    cleaned = re.sub(r" +([.,;:!?])", r"\1", cleaned)
    return cleaned.strip()


def _with_id(item: Dict[str, Any], record_id: int) -> Dict[str, Any]:
    """Return a new dict with ``id`` first, then remaining fields."""
    rest = {k: v for k, v in item.items() if k != "id"}
    return {"id": record_id, **rest}


def clean_records(
    data: Any,
    *,
    start_id: int = 1,
) -> Tuple[Any, int, int]:
    """Clean citations and add sequential ids.

    Supports list-of-dicts or pandas column-oriented {"text": {...}, ...}.

    Returns:
        (cleaned_data, citation_changes, id_count)
    """
    changed = 0

    if isinstance(data, list):
        out: List[Dict[str, Any]] = []
        for offset, item in enumerate(data):
            record_id = start_id + offset
            if isinstance(item, dict) and "text" in item:
                original = item.get("text") or ""
                cleaned = clean_text(original)
                if cleaned != original:
                    changed += 1
                new_item = dict(item)
                new_item["text"] = cleaned
                out.append(_with_id(new_item, record_id))
            elif isinstance(item, dict):
                out.append(_with_id(dict(item), record_id))
            else:
                out.append({"id": record_id, "value": item})
        return out, changed, len(out)

    if isinstance(data, dict) and isinstance(data.get("text"), dict):
        texts = data["text"]
        keys = list(texts.keys())
        new_texts: Dict[str, Any] = {}
        new_ids: Dict[str, int] = {}
        for offset, key in enumerate(keys):
            record_id = start_id + offset
            original = texts.get(key) or ""
            cleaned = clean_text(str(original))
            if cleaned != str(original):
                changed += 1
            new_texts[key] = cleaned
            new_ids[key] = record_id
        out = dict(data)
        out["text"] = new_texts
        out["id"] = new_ids
        return out, changed, len(keys)

    raise ValueError(
        "Unsupported JSON shape: expected list of objects or pandas-style columns."
    )


def main() -> None:
    here = Path(__file__).resolve().parent
    default_in = (
        here.parent
        / "Datasets"
        / "CLEAN_NOTEBOOKLM_1000_PROMPT_INJECTION_PROMPTS.json"
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=default_in)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Defaults to <input_stem>_no_citations.json next to the input file",
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=1,
        help="First id value (default: 1). Subsequent rows use start_id+1, …",
    )
    args = parser.parse_args()

    in_path = args.input
    out_path = args.output or in_path.with_name(f"{in_path.stem}_no_citations.json")

    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned, changed, id_count = clean_records(data, start_id=args.start_id)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    print(f"Input:   {in_path}")
    print(f"Output:  {out_path}")
    print(f"Texts cleaned (citations removed): {changed}")
    print(f"IDs assigned: {id_count} (start_id={args.start_id})")


if __name__ == "__main__":
    main()
