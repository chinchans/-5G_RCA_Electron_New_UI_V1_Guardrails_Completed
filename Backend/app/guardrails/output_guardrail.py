"""Build extraction drafts and run output guardrails for Specification Intelligence."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.guardrails.config import (
    BACKEND_DIR,
    GUARDRAILS_ENABLED,
    LEGACY_SPEC_INTEL_EXTRACT_ROOT,
    SPEC_INTEL_DATASETS_DIR,
    SPEC_INTEL_EXTRACT_ROOT,
)
from app.guardrails.output_schemas import (
    ClauseFileEntry,
    ExtractionMetadata,
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    ReferenceEntry,
    SpecIntelDatasetOutput,
)
from app.guardrails.output_validators import OutputGuardrailVerdict, run_output_guardrails

OUTPUT_GUARDRAILS_ENABLED = GUARDRAILS_ENABLED

RECURSIVE_MARKER = "RECURSIVE EXTRACTION RESULTS"
TS_REFERENCE_RE = re.compile(r"3GPP\s+TS\s+[\d.]+", re.IGNORECASE)
CLAUSE_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)+\b")
REF_CLAUSE_LINE_RE = re.compile(
    r"3GPP\s+TS\s+([\d.]+).*?(?:Clause|clause)\s+([\d.]+)",
    re.IGNORECASE,
)


def _safe_subsection_name(subsection: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", subsection)


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _load_graph(graph_path: Optional[str]) -> KnowledgeGraph:
    if not graph_path:
        raise ValueError("graph_json_path is missing from extraction result")

    path = Path(graph_path)
    if not path.is_absolute():
        path = (BACKEND_DIR / path).resolve()

    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = [GraphNode(id=str(n["id"])) for n in data.get("nodes", []) if n.get("id")]
    edges = [
        GraphEdge(source=str(e["source"]), target=str(e["target"]))
        for e in data.get("edges", [])
        if e.get("source") and e.get("target")
    ]
    return KnowledgeGraph(
        directed=bool(data.get("directed", True)),
        multigraph=bool(data.get("multigraph", False)),
        nodes=nodes,
        edges=edges,
    )


def _build_ref_clause_map(references: List[str], clauses: List[str]) -> Dict[str, List[str]]:
    """Best-effort map when explicit map not returned from extractor."""
    if not references:
        return {}
    if len(references) == 1:
        return {references[0]: list(clauses)}
    return {ref: [] for ref in references}


def _resolve_traceable_reference(
    clause_id: str,
    graph: KnowledgeGraph,
    present_ref_map: Dict[str, str],
) -> Optional[str]:
    clause_nodes = {n.id for n in graph.nodes if clause_id in n.id or n.id.endswith(clause_id)}
    for edge in graph.edges:
        if edge.target in clause_nodes or clause_id in edge.target:
            source = edge.source
            if source in present_ref_map:
                return present_ref_map[source]
            if source.startswith("3GPP") or re.search(r"\d{5}", source):
                return source
    return None


def _build_minimal_graph(
    references: List[str],
    clauses: List[str],
    ref_clause_map: Dict[str, List[str]],
) -> KnowledgeGraph:
    nodes: List[GraphNode] = [GraphNode(id="start")]
    edges: List[GraphEdge] = []
    seen_nodes = {"start"}

    for ref in references or ["3GPP TS unknown"]:
        if ref not in seen_nodes:
            nodes.append(GraphNode(id=ref))
            seen_nodes.add(ref)
        edges.append(GraphEdge(source="start", target=ref))

    for clause in clauses:
        if clause not in seen_nodes:
            nodes.append(GraphNode(id=clause))
            seen_nodes.add(clause)
        mapped_refs = [ref for ref, mapped in ref_clause_map.items() if clause in mapped]
        for ref in mapped_refs or (references[:1] if references else ["3GPP TS unknown"]):
            edges.append(GraphEdge(source=ref, target=clause))

    return KnowledgeGraph(nodes=nodes, edges=edges)


def build_extraction_draft(
    extraction_result: Dict[str, Any],
    *,
    file_id: str,
    source_document_path: str,
    section: str,
    subsection: str,
    ref_clause_map: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """Assemble a dict suitable for Pydantic schema validation from extraction output."""
    safe_sub = _safe_subsection_name(subsection)
    files_created = extraction_result.get("files_created") or {}

    total_path = Path(extraction_result.get("total_content_file") or files_created.get("total_content") or "")
    if total_path and not total_path.is_absolute():
        total_path = (BACKEND_DIR / total_path).resolve()
    total_content = _read_text(total_path)

    section_path = Path(files_created.get("initial_text") or "")
    if section_path and not section_path.is_absolute():
        section_path = (BACKEND_DIR / section_path).resolve()
    section_text = extraction_result.get("section_text") or _read_text(section_path)

    recursive_marker = "RECURSIVE EXTRACTION RESULTS"
    recursive_text = None
    if recursive_marker in total_content:
        recursive_text = total_content.split(recursive_marker, 1)[-1].strip()

    references_raw: List[str] = list(extraction_result.get("references") or [])
    clauses_raw: List[str] = list(extraction_result.get("clauses") or [])
    present_files: List[str] = list(extraction_result.get("present_references") or [])
    missing_refs: List[str] = list(extraction_result.get("missing_references") or [])

    present_ref_map: Dict[str, str] = dict(extraction_result.get("present_ref_map") or {})
    explicit_map = ref_clause_map or extraction_result.get("ref_clause_map") or _build_ref_clause_map(
        references_raw, clauses_raw
    )

    graph_path = extraction_result.get("output_file") or files_created.get("graph_json")
    resolved_graph = _resolve_backend_path(str(graph_path)) if graph_path else None
    if resolved_graph and resolved_graph.is_file():
        graph = _load_graph(str(resolved_graph))
    else:
        graph = _build_minimal_graph(references_raw, clauses_raw, explicit_map)

    reference_entries: List[ReferenceEntry] = []
    for ref in references_raw:
        status = "missing" if ref in missing_refs else "present"
        source_file = present_ref_map.get(ref)
        reference_entries.append(
            ReferenceEntry(
                reference=ref,
                clauses=explicit_map.get(ref, []),
                source_file=source_file,
                status=status,
            )
        )

    clause_file_entries: List[ClauseFileEntry] = []
    from_validated_dataset = bool(extraction_result.get("from_validated_dataset"))
    for clause_path_str in files_created.get("clause_files") or []:
        cf_path = Path(clause_path_str)
        if not cf_path.is_absolute():
            cf_path = (BACKEND_DIR / cf_path).resolve()
        content = _read_text(cf_path)
        clause_id = cf_path.stem.replace("_file", "").replace("_", ".")
        source_ref = _resolve_traceable_reference(clause_id, graph, present_ref_map)
        traceable = (
            from_validated_dataset
            or bool(source_ref)
            or bool(present_files)
            or "3GPP TS" in content[:800]
            or re.search(r"\bTS\s+\d+\.\d+", content[:800]) is not None
        )
        clause_file_entries.append(
            ClauseFileEntry(
                clause_id=clause_id,
                file_path=str(cf_path),
                source_reference=source_ref,
                content=content,
                traceable=traceable,
            )
        )

    dataset_folder = str(total_path.parent) if total_path else str(
        (BACKEND_DIR / "resources" / "extract" / "datasets" / safe_sub).resolve()
    )

    return SpecIntelDatasetOutput(
        metadata=ExtractionMetadata(
            source_file_id=file_id,
            source_document_path=str(source_document_path),
            section=section,
            subsection=subsection,
            safe_subsection=safe_sub,
            dataset_folder=dataset_folder,
        ),
        section_text=section_text,
        references=reference_entries,
        clauses=clauses_raw,
        present_references=present_files,
        missing_references=missing_refs,
        ref_clause_map=explicit_map,
        graph=graph,
        total_content=total_content,
        recursive_extraction_text=recursive_text,
        clause_files=clause_file_entries,
        graph_json_path=str(graph_path) if graph_path else None,
    ).model_dump()


def _resolve_backend_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = (BACKEND_DIR / path).resolve()
    else:
        path = path.resolve()
    return path


def validate_saved_dataset_on_disk(
    extraction_result: Dict[str, Any],
    *,
    file_id: str,
    source_document_path: str,
    section: str,
    subsection: str,
) -> tuple[Optional[SpecIntelDatasetOutput], OutputGuardrailVerdict]:
    """
    Validate dataset files under Backend/extract/datasets after they are written.
    Confirms txt/json artifacts exist on disk, then runs schema → hierarchy → traceability → NLI groundedness.
    """
    from app.guardrails.output_validators import OutputGuardrailVerdict, ValidationStepResult

    files_created = extraction_result.get("files_created") or {}
    missing: List[str] = []

    for key in ("initial_text", "total_content"):
        raw = files_created.get(key)
        if not raw:
            missing.append(f"Missing path for {key}")
            continue
        if not _resolve_backend_path(str(raw)).is_file():
            missing.append(f"Dataset file not found on disk: {raw}")

    for raw in files_created.get("clause_files") or []:
        if not _resolve_backend_path(str(raw)).is_file():
            missing.append(f"Clause file not found on disk: {raw}")

    graph_raw = extraction_result.get("output_file") or files_created.get("graph_json")
    if graph_raw and not _resolve_backend_path(str(graph_raw)).is_file():
        missing.append(f"Graph JSON not found on disk: {graph_raw}")

    if missing:
        file_check = ValidationStepResult(step="dataset_files_on_disk", passed=False, errors=missing)
        skipped = ValidationStepResult(step="skipped", passed=False, errors=["Skipped: dataset files missing on disk"])
        return None, OutputGuardrailVerdict(
            passed=False,
            blocked=True,
            schema=file_check,
            hierarchy=skipped,
            traceability=skipped,
            groundedness=skipped,
        )

    return validate_spec_intel_extraction(
        extraction_result,
        file_id=file_id,
        source_document_path=source_document_path,
        section=section,
        subsection=subsection,
    )


def validate_spec_intel_extraction(
    extraction_result: Dict[str, Any],
    *,
    file_id: str,
    source_document_path: str,
    section: str,
    subsection: str,
) -> tuple[Optional[SpecIntelDatasetOutput], OutputGuardrailVerdict]:
    if not OUTPUT_GUARDRAILS_ENABLED:
        draft = build_extraction_draft(
            extraction_result,
            file_id=file_id,
            source_document_path=source_document_path,
            section=section,
            subsection=subsection,
        )
        from app.guardrails.output_validators import ValidationStepResult

        ok = ValidationStepResult(step="disabled", passed=True)
        verdict = OutputGuardrailVerdict(
            passed=True, blocked=False, schema=ok, hierarchy=ok, traceability=ok, groundedness=ok
        )
        return SpecIntelDatasetOutput.model_validate(draft), verdict

    raw = build_extraction_draft(
        extraction_result,
        file_id=file_id,
        source_document_path=source_document_path,
        section=section,
        subsection=subsection,
    )
    return run_output_guardrails(raw)


def _dataset_search_roots() -> List[Path]:
    roots: List[Path] = []
    for root in (SPEC_INTEL_DATASETS_DIR, LEGACY_SPEC_INTEL_EXTRACT_ROOT / "datasets"):
        if root.is_dir():
            roots.append(root.resolve())
    return roots


def _is_clause_filename(name: str) -> bool:
    return name.endswith("_file.txt")


def _is_section_filename(name: str) -> bool:
    return name.endswith("_section.txt")


def is_spec_intel_dataset_upload(saved_paths: List[Path]) -> bool:
    """True when upload looks like a Specification Intelligence dataset (not generic docs)."""
    for path in saved_paths:
        name = path.name.lower()
        if name in ("total_content.txt", "dataset_manifest.json"):
            return True
        if _is_clause_filename(path.name) or _is_section_filename(path.name):
            return True
        if path.suffix.lower() == ".txt" and RECURSIVE_MARKER in _read_text(path)[:8000]:
            return True
    return False


def is_tsg_nli_upload(
    saved_paths: List[Path],
    original_filenames: Optional[List[str]] = None,
) -> bool:
    """True when TSG dataset upload should run NLI review (all upload types including PDF)."""
    return bool(saved_paths)


def _infer_title_from_text(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned and len(cleaned) >= 3:
            return cleaned
    return ""


def _match_folder_by_scanning_known_titles(text: str) -> Optional[Path]:
    """Match when uploaded document text contains a known dataset subsection title."""
    sample = text[:12000].lower()
    if not sample:
        return None

    for root in _dataset_search_roots():
        for subdir in root.iterdir():
            if not subdir.is_dir():
                continue
            total_path = subdir / "total_content.txt"
            if not total_path.is_file():
                continue
            title = _read_text(total_path).split("\n", 1)[0].strip()
            if title and title.lower() in sample:
                return subdir.resolve()
    return None


def _extract_tsg_upload_text(path: Path, max_chars: int = 200_000) -> str:
    from app.guardrails.document_text_extractor import extract_text_for_scan

    return extract_text_for_scan(path, max_chars=max_chars)


def _resolve_tsg_upload_content(
    saved_paths: List[Path],
    original_filenames: Optional[List[str]] = None,
) -> tuple[str, str, Path]:
    """
    Return (upload_type, extracted_text, source_path).
    upload_type: total_content | pdf | docx | text | other
    """
    names = original_filenames or []
    total_path = _resolve_total_content_upload(saved_paths, original_filenames)
    if total_path and total_path.is_file():
        return "total_content", _read_text(total_path), total_path

    for path, original in zip(saved_paths, names if names else [""] * len(saved_paths)):
        orig_lower = (original or path.name).lower()
        suffix = path.suffix.lower()

        if suffix == ".pdf" or orig_lower.endswith(".pdf"):
            return "pdf", _extract_tsg_upload_text(path), path
        if suffix in (".docx", ".doc") or orig_lower.endswith((".docx", ".doc")):
            return "docx", _extract_tsg_upload_text(path), path
        if suffix == ".txt" or orig_lower.endswith(".txt"):
            return "text", _read_text(path), path

    if saved_paths:
        path = saved_paths[0]
        return "other", _extract_tsg_upload_text(path), path

    return "unknown", "", Path()


def _tsg_skipped_steps(upload_note: str) -> ValidationStepResult:
    from app.guardrails.output_validators import ValidationStepResult

    return ValidationStepResult(
        step="skipped",
        passed=True,
        warnings=[upload_note],
    )


def _tsg_nli_verdict(
    *,
    groundedness: "ValidationStepResult",
) -> "OutputGuardrailVerdict":
    from app.guardrails.output_validators import OutputGuardrailVerdict, ValidationStepResult

    skipped = _tsg_skipped_steps("NLI review for Test Script Generator dataset upload")
    return OutputGuardrailVerdict(
        passed=groundedness.passed,
        blocked=not groundedness.passed,
        schema=skipped,
        hierarchy=skipped,
        traceability=skipped,
        groundedness=groundedness,
    )


def _resolve_total_content_upload(
    saved_paths: List[Path],
    original_filenames: Optional[List[str]] = None,
) -> Optional[Path]:
    """Find uploaded total_content file (by original name or saved path)."""
    if original_filenames:
        for path, original in zip(saved_paths, original_filenames):
            if original and Path(original).name.lower() == "total_content.txt":
                return path
    return _find_uploaded_file(saved_paths, "total_content.txt") or (
        saved_paths[0] if len(saved_paths) == 1 and saved_paths[0].suffix.lower() == ".txt" else None
    )


def resolve_dataset_folder_by_title(title: str) -> Optional[Path]:
    """Match Spec Intelligence dataset folder using the first-line subsection title."""
    normalized = title.strip().lower()
    if not normalized:
        return None

    for root in _dataset_search_roots():
        direct = root / title.strip()
        if direct.is_dir() and (direct / "total_content.txt").is_file():
            return direct.resolve()

        for subdir in root.iterdir():
            if not subdir.is_dir():
                continue
            if subdir.name.strip().lower() == normalized and (subdir / "total_content.txt").is_file():
                return subdir.resolve()
            total_path = subdir / "total_content.txt"
            if total_path.is_file():
                first_line = _read_text(total_path).split("\n", 1)[0].strip().lower()
                if first_line == normalized:
                    return subdir.resolve()
    return None


def load_oran_section_text(folder: Path) -> str:
    """Load O-RAN subsection text extracted during Specification Intelligence."""
    section_files = sorted(folder.glob("*_section.txt"))
    if section_files:
        return _read_text(section_files[0])
    return ""


def _find_uploaded_file(saved_paths: List[Path], target_name: str) -> Optional[Path]:
    target = target_name.lower()
    for path in saved_paths:
        if path.name.lower() == target:
            return path
    return None


def _match_dataset_folder_from_content(content: str) -> Optional[Path]:
    header = content[:4000]
    first_line = content.split("\n", 1)[0].strip().lower()
    if not first_line:
        return None

    for root in _dataset_search_roots():
        for subdir in root.iterdir():
            if not subdir.is_dir():
                continue
            total_path = subdir / "total_content.txt"
            if not total_path.is_file():
                continue
            existing = _read_text(total_path)
            if existing[:400] == header[:400]:
                return subdir.resolve()
            if existing.split("\n", 1)[0].strip().lower() == first_line:
                return subdir.resolve()
    return None


def resolve_spec_intel_dataset_folder(saved_paths: List[Path]) -> Optional[Path]:
    """Locate canonical Spec Intelligence dataset folder for uploaded artifacts."""
    for path in saved_paths:
        if path.name == "dataset_manifest.json" and path.is_file():
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
                folder = manifest.get("metadata", {}).get("dataset_folder")
                if folder:
                    resolved = Path(folder).resolve()
                    if resolved.is_dir() and (resolved / "total_content.txt").is_file():
                        return resolved
            except (json.JSONDecodeError, OSError):
                pass

    total_upload = _find_uploaded_file(saved_paths, "total_content.txt")
    if total_upload and total_upload.is_file():
        matched = _match_dataset_folder_from_content(_read_text(total_upload))
        if matched:
            return matched

    for path in saved_paths:
        if path.suffix.lower() != ".txt":
            continue
        if RECURSIVE_MARKER in _read_text(path)[:8000]:
            matched = _match_dataset_folder_from_content(_read_text(path))
            if matched:
                return matched

    clause_dirs = {p.parent.resolve() for p in saved_paths if _is_clause_filename(p.name)}
    if len(clause_dirs) == 1:
        folder = next(iter(clause_dirs))
        if (folder / "total_content.txt").is_file():
            return folder

    return None


def _find_graph_json(folder: Path, safe_subsection: str) -> Optional[Path]:
    candidates = [
        folder / "output.json",
        SPEC_INTEL_EXTRACT_ROOT / "output.json",
        SPEC_INTEL_EXTRACT_ROOT / f"{safe_subsection}_output.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    for candidate in SPEC_INTEL_EXTRACT_ROOT.glob("*_output.json"):
        if candidate.is_file():
            return candidate.resolve()
    return None


def _parse_refs_clauses_from_graph(graph_path: Optional[Path]) -> tuple[List[str], List[str], Dict[str, List[str]]]:
    if not graph_path or not graph_path.is_file():
        return [], [], {}

    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [], [], {}

    node_ids = [str(n["id"]) for n in data.get("nodes", []) if n.get("id")]
    references = [node for node in node_ids if TS_REFERENCE_RE.search(node)]
    clauses = [
        node
        for node in node_ids
        if node not in references and node != "start" and CLAUSE_NUMBER_RE.search(node)
    ]

    ref_clause_map: Dict[str, List[str]] = {ref: [] for ref in references}
    for edge in data.get("edges", []):
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        if source in ref_clause_map and target in clauses and target not in ref_clause_map[source]:
            ref_clause_map[source].append(target)

    return references, clauses, ref_clause_map


def _parse_refs_clauses_from_total_content(total_content: str, clause_ids: List[str]) -> tuple[List[str], List[str], Dict[str, List[str]]]:
    references: List[str] = []
    ref_clause_map: Dict[str, List[str]] = {}

    for match in REF_CLAUSE_LINE_RE.finditer(total_content):
        ref = f"3GPP TS {match.group(1)}"
        clause = match.group(2)
        if ref not in references:
            references.append(ref)
        ref_clause_map.setdefault(ref, [])
        if clause not in ref_clause_map[ref]:
            ref_clause_map[ref].append(clause)

    clauses = list(clause_ids)
    if not clauses:
        for mapped in ref_clause_map.values():
            for clause in mapped:
                if clause not in clauses:
                    clauses.append(clause)

    return references, clauses, ref_clause_map


def _load_manifest(folder: Optional[Path], saved_paths: List[Path]) -> Dict[str, Any]:
    candidates: List[Path] = []
    if folder:
        candidates.append(folder / "dataset_manifest.json")
    manifest_upload = _find_uploaded_file(saved_paths, "dataset_manifest.json")
    if manifest_upload:
        candidates.append(manifest_upload)

    for candidate in candidates:
        if candidate.is_file():
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
    return {}


def build_extraction_result_from_dataset_folder(
    folder: Path,
    *,
    saved_paths: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    """Build extraction_result dict from a saved Spec Intelligence dataset folder."""
    saved_paths = saved_paths or []
    manifest = _load_manifest(folder, saved_paths)
    meta = manifest.get("metadata", {})

    total_path = folder / "total_content.txt"
    section_files = sorted(folder.glob("*_section.txt"))
    section_path = section_files[0] if section_files else None
    clause_files = sorted(folder.glob("*_file.txt"))

    uploaded_total = _find_uploaded_file(saved_paths, "total_content.txt")
    if uploaded_total and uploaded_total.is_file():
        total_path = uploaded_total

    uploaded_section = next((p for p in saved_paths if _is_section_filename(p.name)), None)
    if uploaded_section and uploaded_section.is_file():
        section_path = uploaded_section

    uploaded_clause_files = sorted(p for p in saved_paths if _is_clause_filename(p.name))
    if uploaded_clause_files:
        clause_files = uploaded_clause_files

    safe_sub = meta.get("safe_subsection") or _safe_subsection_name(folder.name)
    graph_path = _find_graph_json(folder, safe_sub)
    references, clauses, ref_clause_map = _parse_refs_clauses_from_graph(graph_path)
    if not references:
        clause_ids = [p.stem.replace("_file", "").replace("_", ".") for p in clause_files]
        references, clauses, ref_clause_map = _parse_refs_clauses_from_total_content(
            _read_text(total_path), clause_ids
        )

    return {
        "section_text": _read_text(section_path) if section_path else _read_text(total_path)[:3000],
        "references": references,
        "clauses": clauses,
        "present_references": ["validated_spec_intel_dataset"] if manifest.get("validated") else [],
        "missing_references": list(meta.get("missing_references", [])),
        "ref_clause_map": ref_clause_map,
        "from_validated_dataset": bool(manifest.get("validated")),
        "total_content_file": str(total_path.resolve()),
        "output_file": str(graph_path) if graph_path else None,
        "files_created": {
            "initial_text": str(section_path.resolve()) if section_path else "",
            "total_content": str(total_path.resolve()),
            "graph_json": str(graph_path) if graph_path else None,
            "clause_files": [str(p.resolve()) for p in clause_files],
        },
    }


def build_extraction_result_from_uploaded_files(saved_paths: List[Path]) -> Dict[str, Any]:
    """Build extraction_result dict when only uploaded files are available."""
    total_path = _find_uploaded_file(saved_paths, "total_content.txt")
    if total_path is None:
        for path in saved_paths:
            if path.suffix.lower() == ".txt" and RECURSIVE_MARKER in _read_text(path)[:8000]:
                total_path = path
                break
    if total_path is None:
        raise ValueError("No total_content dataset file found in upload")

    section_path = next((p for p in saved_paths if _is_section_filename(p.name)), None)
    clause_files = sorted(p for p in saved_paths if _is_clause_filename(p.name))
    graph_path = next(
        (
            p
            for p in saved_paths
            if p.suffix.lower() == ".json" and ("output" in p.name.lower() or p.name == "dataset_manifest.json")
        ),
        None,
    )
    if graph_path and graph_path.name == "dataset_manifest.json":
        graph_path = None

    clause_ids = [p.stem.replace("_file", "").replace("_", ".") for p in clause_files]
    references, clauses, ref_clause_map = _parse_refs_clauses_from_graph(graph_path)
    if not references:
        references, clauses, ref_clause_map = _parse_refs_clauses_from_total_content(
            _read_text(total_path), clause_ids
        )

    return {
        "section_text": _read_text(section_path) if section_path else _read_text(total_path)[:3000],
        "references": references,
        "clauses": clauses,
        "present_references": [],
        "missing_references": [],
        "ref_clause_map": ref_clause_map,
        "total_content_file": str(total_path.resolve()),
        "output_file": str(graph_path.resolve()) if graph_path else None,
        "files_created": {
            "initial_text": str(section_path.resolve()) if section_path else "",
            "total_content": str(total_path.resolve()),
            "graph_json": str(graph_path.resolve()) if graph_path else None,
            "clause_files": [str(p.resolve()) for p in clause_files],
        },
    }


def validate_tsg_dataset_upload(
    saved_paths: List[Path],
    *,
    original_filenames: Optional[List[str]] = None,
) -> tuple[Optional[SpecIntelDatasetOutput], Optional[OutputGuardrailVerdict], bool]:
    """
    NLI groundedness panel for all Test Script Generator dataset uploads.

    - PDF / DOCX / TXT: input guardrails + NLI review (panel always returned).
    - total_content.txt: full NLI against O-RAN subsection + 3GPP clauses.
    - PDF with matching Spec Intelligence title: same NLI against O-RAN source.
    - PDF without dataset match: input guardrails pass; NLI panel shows informational status.
    """
    from app.guardrails.nli_groundedness_service import run_nli_groundedness
    from app.guardrails.output_validators import ValidationStepResult

    if not OUTPUT_GUARDRAILS_ENABLED or not is_tsg_nli_upload(saved_paths, original_filenames):
        return None, None, False

    upload_type, content, source_path = _resolve_tsg_upload_content(saved_paths, original_filenames)
    original_name = ""
    if original_filenames:
        original_name = original_filenames[0] or source_path.name
    else:
        original_name = source_path.name

    base_details: Dict[str, Any] = {
        "upload_type": upload_type,
        "upload_filename": original_name,
    }

    if not content.strip():
        groundedness = ValidationStepResult(
            step="nli_groundedness_validation",
            passed=True,
            warnings=[
                f"Could not extract readable text from {upload_type.upper()} upload for NLI groundedness."
            ],
            details={**base_details, "available": False},
        )
        return None, _tsg_nli_verdict(groundedness=groundedness), True

    title = _infer_title_from_text(content)
    folder = (
        resolve_dataset_folder_by_title(title)
        or _match_dataset_folder_from_content(content)
        or _match_folder_by_scanning_known_titles(content)
    )

    if not folder:
        groundedness = ValidationStepResult(
            step="nli_groundedness_validation",
            passed=True,
            warnings=[
                "Input guardrails passed. "
                f"No Spec Intelligence dataset matched for '{title or original_name}'. "
                "NLI groundedness against O-RAN source was not applied (reference document only)."
            ],
            details={
                **base_details,
                "available": True,
                "dataset_title": title,
                "dataset_matched": False,
            },
        )
        return None, _tsg_nli_verdict(groundedness=groundedness), True

    manifest = _load_manifest(folder, saved_paths)
    meta = manifest.get("metadata", {})
    oran_source = load_oran_section_text(folder)
    resolved_title = meta.get("subsection") or title or folder.name

    extraction_result = build_extraction_result_from_dataset_folder(
        folder,
        saved_paths=[source_path] if upload_type == "total_content" else [],
    )
    extraction_result["files_created"]["total_content"] = str(
        (folder / "total_content.txt").resolve()
    )
    extraction_result["total_content_file"] = str((folder / "total_content.txt").resolve())

    draft = build_extraction_draft(
        extraction_result,
        file_id=meta.get("source_file_id", "tsg_dataset_upload"),
        source_document_path=meta.get("source_document_path", "tsg_dataset_upload"),
        section=meta.get("section", "Unknown"),
        subsection=resolved_title,
    )
    draft["total_content"] = content
    if RECURSIVE_MARKER in content:
        draft["recursive_extraction_text"] = content.split(RECURSIVE_MARKER, 1)[-1].strip()
    if oran_source:
        draft["section_text"] = oran_source

    dataset = SpecIntelDatasetOutput.model_validate(draft)
    nli = run_nli_groundedness(
        section_text=dataset.section_text,
        total_content=dataset.total_content,
        recursive_extraction_text=dataset.recursive_extraction_text,
        clause_files=dataset.clause_files,
        oran_source_text=oran_source or dataset.section_text,
        advisory_only=True,
    )

    groundedness = ValidationStepResult(
        step="nli_groundedness_validation",
        passed=True,
        errors=[],
        warnings=list(nli.warnings),
        details={
            **nli.to_dict(),
            **base_details,
            "dataset_title": resolved_title,
            "dataset_matched": True,
            "advisory_mode": True,
            "oran_source_document": meta.get("source_document_path"),
            "oran_section_file": str(sorted(folder.glob("*_section.txt"))[0])
            if list(folder.glob("*_section.txt"))
            else None,
            "dataset_folder": str(folder.resolve()),
        },
    )

    return dataset, _tsg_nli_verdict(groundedness=groundedness), True


def cleanup_failed_extraction(extraction_result: Dict[str, Any]) -> None:
    """Remove dataset artifacts when output guardrails fail."""
    files_created = extraction_result.get("files_created") or {}
    paths = set()
    for key in ("initial_text", "total_content", "graph_json"):
        if files_created.get(key):
            paths.add(Path(files_created[key]))
    for cf in files_created.get("clause_files") or []:
        paths.add(Path(cf))

    folders = set()
    for p in paths:
        resolved = p if p.is_absolute() else (BACKEND_DIR / p)
        if resolved.is_file():
            try:
                resolved.unlink(missing_ok=True)
            except OSError:
                pass
            folders.add(resolved.parent)

    for folder in folders:
        manifest = folder / "dataset_manifest.json"
        if manifest.is_file():
            try:
                manifest.unlink(missing_ok=True)
            except OSError:
                pass
        if folder.is_dir() and "datasets" in str(folder):
            try:
                if not any(folder.iterdir()):
                    folder.rmdir()
            except OSError:
                pass
