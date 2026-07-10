"""Traceability guardrails for generated test scripts mapped to source test cases."""

from __future__ import annotations

import ast
import json
import re
import tokenize
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from app.guardrails.config import (
    GUARDRAILS_SCRIPT_TRACEABILITY_ENABLED,
    GUARDRAILS_SCRIPT_TRACEABILITY_MIN_PERCENT,
    GUARDRAILS_SCRIPT_TRACEABILITY_STRICT,
)
from app.guardrails.intent_coverage_service import parse_test_cases_from_generation

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
_MESSAGE_TOKEN_RE = re.compile(
    r"\b(RRC[A-Za-z0-9]+|Attach\s+(?:Request|Accept|Complete)|"
    r"Detach\s+(?:Request|Accept|Complete)|SgNB\s+[A-Za-z\s]+|NAS\s+[A-Za-z\s]+)\b",
    re.IGNORECASE,
)
_TRACE_COMMENT_RE = re.compile(
    r"^\s*#?\s*(?P<id>[A-Za-z][A-Za-z0-9_-]{2,})\s*:\s*(?P<title>.+?)\s*$"
)
_STEP_KEYS = ("steps", "testSteps", "test_steps")
_EXPECTED_KEYS = ("expectedResults", "expectedResult", "expected_results", "expected_result")


@dataclass
class TraceabilityMatrixEntry:
    test_case_id: str
    title: str
    steps: List[str] = field(default_factory=list)
    expected_results: List[str] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)
    ie_names: List[str] = field(default_factory=list)
    intents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_case_id": self.test_case_id,
            "title": self.title,
            "steps": self.steps,
            "expected_results": self.expected_results,
            "messages": self.messages,
            "ie_names": self.ie_names,
            "intents": self.intents,
        }


@dataclass
class TestUnitTrace:
    function_name: str
    line: int
    case_id: str
    title: str
    source: str  # comment | docstring


@dataclass
class TraceabilityVerdict:
    passed: bool
    blocked: bool
    reasons: List[str] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    missing_test_case_ids: List[str] = field(default_factory=list)
    unmapped_test_functions: List[str] = field(default_factory=list)
    mappings: List[Dict[str, Any]] = field(default_factory=list)
    coverage_percent: float = 100.0
    matrix_size: int = 0
    skipped: bool = False
    skip_reason: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "reasons": self.reasons,
            "findings": self.findings,
            "missing_test_case_ids": self.missing_test_case_ids,
            "unmapped_test_functions": self.unmapped_test_functions,
            "mappings": self.mappings,
            "coverage_percent": self.coverage_percent,
            "matrix_size": self.matrix_size,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "warnings": self.warnings,
        }


def _normalize_id(case_id: str) -> str:
    text = re.sub(r"[^a-z0-9]", "", (case_id or "").lower())
    if text.startswith("tc") and len(text) > 2:
        text = text[2:]
    return text


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def _case_id_from_dict(case: Dict[str, Any]) -> str:
    for key in ("testCaseID", "testCaseId", "id", "test_id", "testId"):
        value = case.get(key)
        if value:
            return str(value).strip()
    return ""


def _case_title_from_dict(case: Dict[str, Any]) -> str:
    for key in ("title", "description", "name", "summary"):
        value = case.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    case_id = _case_id_from_dict(case)
    return case_id or ""


def _list_field(case: Dict[str, Any], keys: Sequence[str]) -> List[str]:
    for key in keys:
        value = case.get(key)
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
    return []


def _extract_messages_and_ies(case: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    blob = " ".join(
        _list_field(case, _STEP_KEYS)
        + _list_field(case, _EXPECTED_KEYS)
        + [_case_title_from_dict(case)]
    )
    messages = list(dict.fromkeys(m.group(0).strip() for m in _MESSAGE_TOKEN_RE.finditer(blob)))
    ie_candidates = _IDENT_RE.findall(blob)
    ie_names = [
        token
        for token in ie_candidates
        if token.lower() not in {"the", "and", "for", "with", "from", "that", "this", "test", "case"}
    ][:12]
    return messages, list(dict.fromkeys(ie_names))


def _matrix_entry_from_case(case: Dict[str, Any]) -> Optional[TraceabilityMatrixEntry]:
    case_id = _case_id_from_dict(case)
    if not case_id:
        return None
    title = _case_title_from_dict(case) or case_id
    messages, ie_names = _extract_messages_and_ies(case)
    intents_raw = case.get("covers_intents") or case.get("coversIntents") or []
    intents = [str(item).strip() for item in intents_raw] if isinstance(intents_raw, list) else []
    return TraceabilityMatrixEntry(
        test_case_id=case_id,
        title=title,
        steps=_list_field(case, _STEP_KEYS),
        expected_results=_list_field(case, _EXPECTED_KEYS),
        messages=messages,
        ie_names=ie_names,
        intents=intents,
    )


def _load_test_cases_from_json_file(path: Path) -> List[Dict[str, Any]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return []
    cases = parse_test_cases_from_generation(raw)
    if cases:
        return cases
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [c for c in parsed if isinstance(c, dict)]
    if isinstance(parsed, dict):
        inner = parsed.get("test_cases") or parsed.get("testCases")
        if isinstance(inner, list):
            return [c for c in inner if isinstance(c, dict)]
    return []


def discover_test_cases(source_text: str = "", dataset_folder: Optional[str] = None) -> List[Dict[str, Any]]:
    """Collect test case dicts from generation text and optional dataset folder."""
    merged: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    def _add_cases(cases: Sequence[Dict[str, Any]]) -> None:
        for case in cases:
            case_id = _case_id_from_dict(case)
            norm = _normalize_id(case_id)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            merged.append(case)

    _add_cases(parse_test_cases_from_generation(source_text or ""))

    if dataset_folder:
        folder = Path(dataset_folder)
        if folder.is_dir():
            for path in sorted(folder.glob("*.json")):
                if path.name in {"intent_graph.json", "dataset_manifest.json", "traceability_matrix.json"}:
                    continue
                _add_cases(_load_test_cases_from_json_file(path))

    return merged


def build_traceability_matrix(
    source_text: str = "",
    dataset_folder: Optional[str] = None,
) -> List[TraceabilityMatrixEntry]:
    """Build test_case_id → artifacts index from available test case JSON."""
    entries: List[TraceabilityMatrixEntry] = []
    for case in discover_test_cases(source_text, dataset_folder):
        entry = _matrix_entry_from_case(case)
        if entry:
            entries.append(entry)
    return entries


def build_and_save_traceability_matrix(
    source_text: str = "",
    dataset_folder: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Persist traceability matrix beside dataset when folder is known."""
    if not dataset_folder:
        return None
    folder = Path(dataset_folder)
    if not folder.is_dir():
        return None

    matrix = build_traceability_matrix(source_text, dataset_folder)
    if not matrix:
        return None

    payload = {
        "version": 1,
        "entries": [entry.to_dict() for entry in matrix],
        "test_case_count": len(matrix),
    }
    out_path = folder / "traceability_matrix.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "path": str(out_path),
        "test_case_count": len(matrix),
        "test_case_ids": [entry.test_case_id for entry in matrix],
    }


def load_saved_traceability_matrix(dataset_folder: Optional[str]) -> List[TraceabilityMatrixEntry]:
    if not dataset_folder:
        return []
    path = Path(dataset_folder) / "traceability_matrix.json"
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    entries = payload.get("entries") or []
    result: List[TraceabilityMatrixEntry] = []
    for item in entries:
        if not isinstance(item, dict) or not item.get("test_case_id"):
            continue
        result.append(
            TraceabilityMatrixEntry(
                test_case_id=str(item["test_case_id"]),
                title=str(item.get("title") or item["test_case_id"]),
                steps=list(item.get("steps") or []),
                expected_results=list(item.get("expected_results") or []),
                messages=list(item.get("messages") or []),
                ie_names=list(item.get("ie_names") or []),
                intents=list(item.get("intents") or []),
            )
        )
    return result


def _parse_trace_line(text: str) -> Optional[Tuple[str, str]]:
    match = _TRACE_COMMENT_RE.match(text.strip())
    if not match:
        return None
    case_id = match.group("id").strip()
    title = match.group("title").strip()
    if not case_id or not title:
        return None
    return case_id, title


def _comment_map_by_line(script: str) -> Dict[int, Tuple[str, str]]:
    mapping: Dict[int, Tuple[str, str]] = {}
    try:
        tokens = tokenize.generate_tokens(StringIO(script).readline)
    except tokenize.TokenError:
        return mapping
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        parsed = _parse_trace_line(token.string)
        if parsed:
            mapping[token.start[0]] = parsed
    return mapping


def _nearest_trace_comment(
    function_line: int,
    comment_map: Dict[int, Tuple[str, str]],
    *,
    max_gap: int = 3,
) -> Optional[Tuple[str, str, str]]:
    for offset in range(0, max_gap + 1):
        line = function_line - offset
        if line in comment_map:
            case_id, title = comment_map[line]
            return case_id, title, "comment"
    return None


def _docstring_trace(node: ast.AST) -> Optional[Tuple[str, str, str]]:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return None
    doc = ast.get_docstring(node, clean=False)
    if not doc:
        return None
    first_line = doc.strip().splitlines()[0].strip()
    parsed = _parse_trace_line(first_line) or _parse_trace_line(f"# {first_line}")
    if not parsed:
        return None
    case_id, title = parsed
    return case_id, title, "docstring"


def extract_test_unit_traces(script: str) -> Tuple[List[TestUnitTrace], List[str]]:
    """Parse traced code units linked via # <testCaseID>: <title> comments.

    Supports any function, async function, or class — not limited to test_* names.
    """
    traces: List[TestUnitTrace] = []
    unmapped: List[str] = []
    comment_map = _comment_map_by_line(script)

    try:
        tree = ast.parse(script)
    except SyntaxError:
        return traces, unmapped

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("__"):
                continue

            linked = _nearest_trace_comment(node.lineno, comment_map)
            if not linked:
                linked = _docstring_trace(node)
            if linked:
                case_id, title, source = linked
                traces.append(
                    TestUnitTrace(
                        function_name=node.name,
                        line=node.lineno,
                        case_id=case_id,
                        title=title,
                        source=source,
                    )
                )

    return traces, unmapped


def _title_matches(expected: str, found: str) -> bool:
    expected_n = _normalize_title(expected)
    found_n = _normalize_title(found)
    if not expected_n:
        return True
    if not found_n:
        return False
    return (
        expected_n == found_n
        or expected_n.startswith(found_n)
        or found_n.startswith(expected_n)
        or expected_n in found_n
        or found_n in expected_n
    )


def _resolve_matrix(
    source_text: str,
    dataset_folder: Optional[str],
) -> List[TraceabilityMatrixEntry]:
    saved = load_saved_traceability_matrix(dataset_folder)
    if saved:
        return saved
    return build_traceability_matrix(source_text, dataset_folder)


def _resolve_matrix_entry(
    case_id: str,
    matrix_by_norm: Dict[str, TraceabilityMatrixEntry],
    matrix: Sequence[TraceabilityMatrixEntry],
) -> Optional[TraceabilityMatrixEntry]:
    norm_id = _normalize_id(case_id)
    entry = matrix_by_norm.get(norm_id)
    if entry:
        return entry
    for candidate in matrix:
        candidate_norm = _normalize_id(candidate.test_case_id)
        if candidate_norm.startswith(norm_id) or norm_id.startswith(candidate_norm):
            return candidate
    return None


def validate_script_traceability(
    script: str,
    *,
    source_text: str = "",
    dataset_folder: Optional[str] = None,
    strict: Optional[bool] = None,
    min_coverage_percent: Optional[float] = None,
    require_trace_comments: bool = False,
) -> TraceabilityVerdict:
    """Validate generated script traceability comments against source test cases."""
    if not GUARDRAILS_SCRIPT_TRACEABILITY_ENABLED:
        return TraceabilityVerdict(
            passed=True,
            blocked=False,
            skipped=True,
            skip_reason="traceability_guardrail_disabled",
        )

    matrix = _resolve_matrix(source_text, dataset_folder)
    if not matrix:
        return TraceabilityVerdict(
            passed=True,
            blocked=False,
            skipped=True,
            skip_reason="no_source_test_cases_found",
        )

    strict_mode = GUARDRAILS_SCRIPT_TRACEABILITY_STRICT if strict is None else strict
    min_pct = (
        GUARDRAILS_SCRIPT_TRACEABILITY_MIN_PERCENT
        if min_coverage_percent is None
        else min_coverage_percent
    )

    traces, unmapped_no_comment = extract_test_unit_traces(script)
    if not traces:
        if require_trace_comments and matrix:
            reason = (
                "Refined script must include # <testCaseID>: <title> traceability comments "
                "above test classes or methods when source test cases exist."
            )
            return TraceabilityVerdict(
                passed=False,
                blocked=True,
                reasons=[reason],
                findings=[
                    {
                        "layer": "script_guardrail",
                        "check": "traceability",
                        "severity": "error",
                        "detail": reason,
                    }
                ],
                matrix_size=len(matrix),
                skip_reason="no_traceability_comments_in_script",
            )
        return TraceabilityVerdict(
            passed=True,
            blocked=False,
            skipped=True,
            skip_reason="no_traceability_comments_in_script",
            matrix_size=len(matrix),
            warnings=[
                "No # <testCaseID>: <title> comments found in script; "
                "traceability validation skipped. Add comments above test classes or "
                "methods to enable mapping checks.",
            ],
        )

    matrix_by_norm = {_normalize_id(entry.test_case_id): entry for entry in matrix}
    referenced_norm_ids: Set[str] = set()
    mappings: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    reasons: List[str] = []
    unmapped_functions: List[str] = list(unmapped_no_comment)

    for trace in traces:
        norm_id = _normalize_id(trace.case_id)
        entry = _resolve_matrix_entry(trace.case_id, matrix_by_norm, matrix)
        if not entry:
            unmapped_functions.append(trace.function_name)
            findings.append(
                {
                    "layer": "script_guardrail",
                    "check": "traceability",
                    "severity": "error",
                    "detail": (
                        f"{trace.function_name} references unknown test case id "
                        f"'{trace.case_id}' in traceability comment."
                    ),
                }
            )
            continue
        if not _title_matches(entry.title, trace.title):
            findings.append(
                {
                    "layer": "script_guardrail",
                    "check": "traceability",
                    "severity": "warning",
                    "detail": (
                        f"{trace.function_name} traceability title differs for "
                        f"{entry.test_case_id}: expected '{entry.title}', found '{trace.title}'."
                    ),
                }
            )

        referenced_norm_ids.add(_normalize_id(entry.test_case_id))
        mappings.append(
            {
                "test_case_id": entry.test_case_id,
                "title": entry.title,
                "test_function": trace.function_name,
                "line": trace.line,
                "source": trace.source,
            }
        )

    missing_ids: List[str] = []
    for entry in matrix:
        if _normalize_id(entry.test_case_id) not in referenced_norm_ids:
            missing_ids.append(entry.test_case_id)

    coverage_percent = round((len(referenced_norm_ids) / len(matrix)) * 100.0, 2)
    required_percent = 100.0 if strict_mode else float(min_pct)

    require_full_matrix_coverage = False

    if missing_ids and require_full_matrix_coverage:
        sample = ", ".join(missing_ids[:5])
        findings.append(
            {
                "layer": "script_guardrail",
                "check": "traceability",
                "severity": "error",
                "detail": f"Missing traceability for {len(missing_ids)} test case(s): {sample}",
            }
        )
        reasons.append(
            f"Missing traceability comments for test case id(s): {sample}"
            f"{'…' if len(missing_ids) > 5 else ''}."
        )

    if unmapped_functions:
        sample = ", ".join(sorted(dict.fromkeys(unmapped_functions))[:5])
        findings.append(
            {
                "layer": "script_guardrail",
                "check": "traceability",
                "severity": "error",
                "detail": (
                    f"{len(unmapped_functions)} traced unit(s) reference unknown or invalid "
                    f"traceability comments (format: # <testCaseID>: <title>): {sample}"
                ),
            }
        )
        reasons.append(
            f"Unmapped traced units (invalid traceability comment): {sample}"
            f"{'…' if len(unmapped_functions) > 5 else ''}."
        )

    blocked = False
    if strict_mode:
        blocked = bool(unmapped_functions or (missing_ids and require_full_matrix_coverage))
    else:
        blocked = coverage_percent < required_percent

    if blocked and not reasons:
        reasons.append(
            f"Traceability coverage {coverage_percent}% is below required {required_percent}%."
        )

    return TraceabilityVerdict(
        passed=not blocked,
        blocked=blocked,
        reasons=list(dict.fromkeys(reasons)),
        findings=findings,
        missing_test_case_ids=missing_ids,
        unmapped_test_functions=sorted(dict.fromkeys(unmapped_functions)),
        mappings=mappings,
        coverage_percent=coverage_percent,
        matrix_size=len(matrix),
    )
