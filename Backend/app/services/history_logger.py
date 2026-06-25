from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _get_backend_resources_dir() -> Path:
    """
    Resolve the backend resources directory.

    The project structure keeps runtime artifacts under `Backend/resources`.
    We derive the path relative to this file to avoid dependence on the
    current working directory.
    """
    backend_root = Path(__file__).resolve().parent.parent.parent
    resources_dir = backend_root / "resources"
    resources_dir.mkdir(parents=True, exist_ok=True)
    return resources_dir


def _get_history_dir() -> Path:
    """
    Ensure the history directory exists inside backend resources and return it.
    """
    history_dir = _get_backend_resources_dir() / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir


def _load_history(file_path: Path) -> List[Dict[str, Any]]:
    """
    Load existing history entries from the given JSON file.

    Returns an empty list if the file does not exist or cannot be parsed.
    """
    if not file_path.exists():
        return []

    try:
        with file_path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
            if isinstance(data, list):
                return data
            # If the file exists but does not contain a list, fall back to empty list.
            return []
    except (json.JSONDecodeError, OSError):
        # Corrupted or unreadable file – start fresh while preserving original file for inspection.
        return []


def _write_history(file_path: Path, entries: List[Dict[str, Any]]) -> None:
    """
    Persist the provided entries list to disk.
    """
    # Ensure parent directory exists even if file was moved or deleted externally.
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as fp:
        json.dump(entries, fp, ensure_ascii=False, indent=2)


def append_history_record(
    filename: str,
    record: Dict[str, Any],
    timestamp: Optional[datetime] = None,
) -> Path:
    """
    Append a history record to the specified JSON file.

    Args:
        filename: Target JSON filename (e.g. "test_case_history.json").
        record:   Dictionary containing the data to store.
        timestamp: Optional datetime to override the automatic timestamp.

    Returns:
        Path to the JSON history file that was updated.
    """
    history_dir = _get_history_dir()
    file_path = history_dir / filename

    # Normalize timestamp
    record = dict(record)  # Work on a copy to avoid mutating caller data.
    if "timestamp" not in record or not record["timestamp"]:
        record["timestamp"] = (timestamp or datetime.utcnow()).isoformat()

    entries = _load_history(file_path)
    entries.append(record)
    _write_history(file_path, entries)

    return file_path


def load_history_entries(filename: str) -> List[Dict[str, Any]]:
    """
    Return all history entries stored in the requested JSON file.
    """
    history_dir = _get_history_dir()
    file_path = history_dir / filename
    return _load_history(file_path)


__all__ = ["append_history_record", "load_history_entries"]

