"""Output guardrail validators for Specification Intelligence extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from pydantic import ValidationError

from app.guardrails.output_schemas import (
    ClauseFileEntry,
    KnowledgeGraph,
    ReferenceEntry,
    SpecIntelDatasetOutput,
)

TS_REFERENCE_RE = re.compile(r"3GPP\s+TS\s+\d+\.\d+", re.IGNORECASE)
CLAUSE_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)+\b")


@dataclass
class ValidationStepResult:
    step: str
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "step": self.step,
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
        }
        if self.details:
            payload["details"] = self.details
        return payload


@dataclass
class OutputGuardrailVerdict:
    passed: bool
    blocked: bool
    schema: ValidationStepResult
    hierarchy: ValidationStepResult
    traceability: ValidationStepResult
    groundedness: ValidationStepResult

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "schema_validation": self.schema.to_dict(),
            "hierarchy_validation": self.hierarchy.to_dict(),
            "source_traceability_validation": self.traceability.to_dict(),
            "nli_groundedness_validation": self.groundedness.to_dict(),
        }

    @property
    def all_errors(self) -> List[str]:
        return (
            self.schema.errors
            + self.hierarchy.errors
            + self.traceability.errors
            + self.groundedness.errors
        )


def validate_schema(raw: Dict[str, Any]) -> tuple[Optional[SpecIntelDatasetOutput], ValidationStepResult]:
    """Layer 1: Pydantic schema validation."""
    result = ValidationStepResult(step="schema_validation", passed=True)
    try:
        model = SpecIntelDatasetOutput.model_validate(raw)
        return model, result
    except ValidationError as exc:
        result.passed = False
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", ()))
            result.errors.append(f"{loc}: {err.get('msg', 'invalid')}")
        return None, result


def validate_hierarchy(dataset: SpecIntelDatasetOutput) -> ValidationStepResult:
    """Layer 2: reference → clause graph hierarchy checks."""
    result = ValidationStepResult(step="hierarchy_validation", passed=True)
    graph = dataset.graph

    node_ids: Set[str] = {n.id for n in graph.nodes}
    ref_nodes = {nid for nid in node_ids if TS_REFERENCE_RE.search(nid)}
    clause_nodes = node_ids - ref_nodes - {"start"}

    edges_by_source: Dict[str, List[str]] = {}
    for edge in graph.edges:
        edges_by_source.setdefault(edge.source, []).append(edge.target)

    start_children = edges_by_source.get("start", [])
    if not start_children and ref_nodes:
        result.warnings.append("Graph 'start' node has no outgoing edges to references")

    for ref in ref_nodes:
        if ref not in start_children and "start" in node_ids:
            result.warnings.append(f"Reference '{ref}' is not directly linked from 'start'")

    orphan_clauses = []
    for clause_node in clause_nodes:
        parents = [e.source for e in graph.edges if e.target == clause_node]
        if not parents:
            orphan_clauses.append(clause_node)
    if orphan_clauses:
        result.warnings.append(
            f"{len(orphan_clauses)} clause node(s) not linked from a reference in the graph"
        )

    for ref, mapped_clauses in dataset.ref_clause_map.items():
        if not mapped_clauses:
            result.warnings.append(f"Reference '{ref}' has no mapped clauses")
            continue
        for clause in mapped_clauses:
            clause_num = _extract_clause_number(clause)
            if not clause_num:
                result.errors.append(f"Invalid clause format under '{ref}': {clause}")
                result.passed = False

    declared = {_extract_clause_number(c) or c for c in dataset.clauses}
    file_ids = {cf.clause_id for cf in dataset.clause_files}
    if declared and file_ids:
        overlap = declared.intersection(file_ids)
        if not overlap:
            result.warnings.append(
                "No overlap between declared clause list and clause file identifiers"
            )

    return result


def validate_source_traceability(dataset: SpecIntelDatasetOutput) -> ValidationStepResult:
    """Layer 3: every output artifact traces back to source document / 3GPP specs."""
    result = ValidationStepResult(step="source_traceability_validation", passed=True)

    meta = dataset.metadata
    if meta.section.lower() not in dataset.section_text.lower()[:500]:
        result.warnings.append("Section title not found near start of extracted section text")

    if meta.subsection.lower() not in dataset.section_text.lower()[:800]:
        result.warnings.append("Subsection title not found near start of extracted section text")

    if meta.safe_subsection not in dataset.total_content[:2000]:
        result.warnings.append("Subsection identifier not reflected in total_content header")

    section_snippet = " ".join(dataset.section_text.split())[:500]
    total_normalized = " ".join(dataset.total_content.split())
    if section_snippet and section_snippet not in total_normalized:
        result.errors.append("total_content does not include the source section_text")
        result.passed = False

    if not dataset.clause_files and dataset.clauses:
        result.warnings.append(
            "Clauses were identified but no clause files were produced for traceability"
        )

    untraceable = [cf.file_path for cf in dataset.clause_files if not cf.traceable]
    if untraceable:
        result.errors.append(
            f"{len(untraceable)} clause file(s) lack source reference traceability"
        )
        result.passed = False

    for ref_entry in dataset.references:
        if ref_entry.status == "present" and not ref_entry.source_file:
            result.warnings.append(f"Present reference '{ref_entry.reference}' has no source_file")

    if dataset.missing_references:
        result.warnings.append(
            f"{len(dataset.missing_references)} missing 3GPP reference(s) documented: "
            f"{', '.join(dataset.missing_references[:3])}"
            f"{'…' if len(dataset.missing_references) > 3 else ''}"
        )

    for cf in dataset.clause_files:
        if len(cf.content.strip()) < 20:
            result.errors.append(f"Clause file '{cf.clause_id}' content too short to be traceable")
            result.passed = False

    return result


def validate_groundedness_nli(dataset: SpecIntelDatasetOutput) -> ValidationStepResult:
    """Layer 4: NLI groundedness — extracted claims must be supported by clause sources."""
    from app.guardrails.nli_groundedness_service import run_nli_groundedness

    result = ValidationStepResult(step="nli_groundedness_validation", passed=True)
    nli = run_nli_groundedness(
        section_text=dataset.section_text,
        total_content=dataset.total_content,
        recursive_extraction_text=dataset.recursive_extraction_text,
        clause_files=dataset.clause_files,
        oran_source_text=dataset.section_text,
    )

    result.warnings.extend(nli.warnings)
    if nli.errors:
        result.errors.extend(nli.errors)
        result.passed = False
    result.details = nli.to_dict()

    return result


def run_output_guardrails(raw: Dict[str, Any]) -> tuple[Optional[SpecIntelDatasetOutput], OutputGuardrailVerdict]:
    """Run schema → hierarchy → source traceability → NLI groundedness validation pipeline."""
    dataset, schema_result = validate_schema(raw)

    if dataset is None:
        empty_h = ValidationStepResult(step="hierarchy_validation", passed=False, errors=["Skipped: schema invalid"])
        empty_t = ValidationStepResult(
            step="source_traceability_validation", passed=False, errors=["Skipped: schema invalid"]
        )
        empty_g = ValidationStepResult(
            step="nli_groundedness_validation", passed=False, errors=["Skipped: schema invalid"]
        )
        verdict = OutputGuardrailVerdict(
            passed=False,
            blocked=True,
            schema=schema_result,
            hierarchy=empty_h,
            traceability=empty_t,
            groundedness=empty_g,
        )
        return None, verdict

    hierarchy_result = validate_hierarchy(dataset)
    traceability_result = validate_source_traceability(dataset)
    groundedness_result = validate_groundedness_nli(dataset)

    passed = (
        schema_result.passed
        and hierarchy_result.passed
        and traceability_result.passed
        and groundedness_result.passed
    )
    blocked = not passed

    verdict = OutputGuardrailVerdict(
        passed=passed,
        blocked=blocked,
        schema=schema_result,
        hierarchy=hierarchy_result,
        traceability=traceability_result,
        groundedness=groundedness_result,
    )
    return dataset, verdict


def _extract_clause_number(clause: str) -> Optional[str]:
    match = CLAUSE_NUMBER_RE.search(clause or "")
    return match.group(0) if match else None
