"""Validate generated test cases against intent coverage graphs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from app.guardrails.intent_graph_schemas import (
    IntentCoverageMapping,
    IntentCoverageResult,
    IntentGraph,
    IntentNode,
)
from app.guardrails.intent_graph_store import load_intent_graph_model

CLAUSE_ID_RE = re.compile(r"\b\d+(?:\.\d+)+\b")
JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
NLI_ENTAILMENT_THRESHOLD = 0.55


@dataclass
class _GraphMatchIndex:
    nodes_by_id: Dict[str, IntentNode]
    mandatory_nodes: List[IntentNode]
    matchable_nodes: List[IntentNode]
    expansion: Dict[str, Tuple[str, ...]]

    @classmethod
    def from_graph(cls, graph: IntentGraph) -> "_GraphMatchIndex":
        nodes_by_id = {node.id: node for node in graph.nodes}
        mandatory_nodes = [
            node for node in graph.nodes if node.mandatory and node.type in {"procedure", "kpi"}
        ]
        matchable_nodes = [node for node in graph.nodes if node.type in {"procedure", "kpi", "clause"}]
        expansion: Dict[str, List[str]] = {}
        for edge in graph.edges:
            expansion.setdefault(edge.source, []).append(edge.target)
        return cls(
            nodes_by_id=nodes_by_id,
            mandatory_nodes=mandatory_nodes,
            matchable_nodes=matchable_nodes,
            expansion={source: tuple(targets) for source, targets in expansion.items()},
        )

    def expand(self, covered: Set[str]) -> Set[str]:
        expanded = set(covered)
        queue = list(covered)
        while queue:
            source = queue.pop()
            for target in self.expansion.get(source, ()):
                if target not in expanded:
                    expanded.add(target)
                    queue.append(target)
        return expanded


def _flatten_test_case_text(test_case: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in (
        "testCaseID",
        "testCaseId",
        "title",
        "description",
        "preconditions",
        "testSteps",
        "expectedResults",
        "verificationMethods",
        "postconditions",
    ):
        value = test_case.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    covers = test_case.get("covers_intents") or test_case.get("coversIntents")
    if isinstance(covers, list):
        parts.extend(str(item) for item in covers)
    return " ".join(parts)


def _parse_json_payload(raw: str) -> Any:
    text = raw.strip()
    if not text:
        return None
    fence = JSON_FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return None


def parse_test_cases_from_generation(generated_text: str) -> List[Dict[str, Any]]:
    """Extract test case objects from LLM output or saved JSON wrapper."""
    if not generated_text or not str(generated_text).strip():
        return []

    parsed = _parse_json_payload(generated_text)
    if isinstance(parsed, list):
        return [c for c in parsed if isinstance(c, dict)]
    if isinstance(parsed, dict):
        cases = parsed.get("test_cases") or parsed.get("testCases")
        if isinstance(cases, str):
            inner = _parse_json_payload(cases)
            if isinstance(inner, list):
                return [c for c in inner if isinstance(c, dict)]
        if isinstance(cases, list):
            return [c for c in cases if isinstance(c, dict)]
    return []


def _clause_match(found_clause_ids: Set[str], clause_ids: Sequence[str]) -> bool:
    if not clause_ids or not found_clause_ids:
        return False
    normalized = {cid.rstrip(".") for cid in clause_ids}
    for clause_id in normalized:
        if clause_id in found_clause_ids:
            return True
        prefix = clause_id + "."
        if any(fid.startswith(prefix) or clause_id.startswith(fid + ".") for fid in found_clause_ids):
            return True
    return False


def _match_text_to_intents(text: str, index: _GraphMatchIndex) -> Set[str]:
    lower = text.lower()
    found_clauses = {m.group(0) for m in CLAUSE_ID_RE.finditer(text)}
    matched: Set[str] = set()

    for node in index.matchable_nodes:
        if node.clause_ids and _clause_match(found_clauses, node.clause_ids):
            matched.add(node.id)
            continue
        if any(keyword in lower for keyword in node.keywords if keyword):
            matched.add(node.id)
    return matched


def _match_test_case_to_intents(
    test_case: Dict[str, Any],
    index: _GraphMatchIndex,
    *,
    use_nli: bool = False,
) -> Set[str]:
    matched: Set[str] = set()

    explicit = test_case.get("covers_intents") or test_case.get("coversIntents") or []
    if isinstance(explicit, list):
        for item in explicit:
            item_str = str(item).strip()
            if item_str in index.nodes_by_id:
                matched.add(item_str)

    matched.update(_match_text_to_intents(_flatten_test_case_text(test_case), index))

    if use_nli:
        unmatched = [
            node
            for node in index.mandatory_nodes
            if node.id not in matched
        ]
        if unmatched:
            matched.update(_nli_semantic_matches(_flatten_test_case_text(test_case), unmatched))

    return matched


def _nli_semantic_matches(text: str, nodes: Sequence[IntentNode]) -> Set[str]:
    try:
        from app.guardrails.nli_groundedness_service import _nli_model
    except ImportError:
        return set()

    if not _nli_model.load() or not nodes:
        return set()

    premise = " ".join(text.split())
    if len(premise) > 4000:
        premise = premise[:4000]

    pairs = [
        (premise, f"{node.label}. {' '.join(node.keywords[:4])}")
        for node in nodes
    ]
    probs = _nli_model.predict_probs(pairs)
    matched: Set[str] = set()
    for node, row in zip(nodes, probs):
        _contradiction, entailment, _neutral = row
        if entailment >= NLI_ENTAILMENT_THRESHOLD:
            matched.add(node.id)
    return matched


def validate_intent_coverage(
    dataset_folder: Path | str,
    generated_text: str,
    *,
    use_nli_for_gaps: bool = False,
    advisory_only: bool = True,
) -> IntentCoverageResult:
    folder = Path(dataset_folder).resolve()
    if not folder.is_dir():
        return IntentCoverageResult(
            available=False,
            passed=False,
            advisory_only=advisory_only,
            errors=[f"Dataset folder not found: {folder}"],
        )

    try:
        graph = load_intent_graph_model(folder)
        index = _GraphMatchIndex.from_graph(graph)
    except Exception as exc:
        return IntentCoverageResult(
            available=False,
            passed=False,
            advisory_only=advisory_only,
            errors=[f"Failed to load intent graph: {exc}"],
        )

    test_cases = parse_test_cases_from_generation(generated_text)
    corpus_fallback = False
    if not test_cases and generated_text and generated_text.strip():
        corpus_fallback = True
        test_cases = [
            {
                "testCaseID": "GENERATED_OUTPUT",
                "title": "Generated test case output",
                "description": generated_text,
                "testSteps": [generated_text],
                "expectedResults": [],
                "verificationMethods": [generated_text],
            }
        ]
    if not test_cases:
        return IntentCoverageResult(
            available=True,
            passed=False,
            advisory_only=advisory_only,
            warnings=["No generated content available for intent coverage validation."],
            errors=["Could not validate intent coverage — empty generation output."],
        )

    covered_intents: Set[str] = set()
    mappings: List[IntentCoverageMapping] = []
    ungrounded: List[str] = []

    for test_case in test_cases:
        case_id = str(
            test_case.get("testCaseID")
            or test_case.get("testCaseId")
            or test_case.get("id")
            or "unknown"
        )
        intent_ids = sorted(
            _match_test_case_to_intents(test_case, index, use_nli=use_nli_for_gaps)
        )
        if not intent_ids:
            ungrounded.append(case_id)
        covered_intents.update(intent_ids)
        mappings.append(
            IntentCoverageMapping(
                test_case_id=case_id,
                title=str(test_case.get("title") or ""),
                category="",
                intent_ids=intent_ids,
            )
        )

    covered_intents = index.expand(covered_intents)

    mandatory_nodes = index.mandatory_nodes
    mandatory_total = len(mandatory_nodes)
    mandatory_covered = sum(1 for node in mandatory_nodes if node.id in covered_intents)
    coverage_percent = (
        round((mandatory_covered / mandatory_total) * 100.0, 1) if mandatory_total else 100.0
    )

    uncovered_intents = [
        {"id": node.id, "type": node.type, "label": node.label}
        for node in mandatory_nodes
        if node.id not in covered_intents
    ]

    warnings: List[str] = []
    if corpus_fallback:
        warnings.append(
            "Structured JSON test cases were not detected; validated full generated output as a single corpus."
        )
    if ungrounded:
        warnings.append(
            f"{len(ungrounded)} test case(s) did not map to any intent graph node "
            f"({', '.join(ungrounded[:5])}{'…' if len(ungrounded) > 5 else ''})."
        )
    if uncovered_intents:
        labels = ", ".join(item["label"] for item in uncovered_intents[:4])
        suffix = "…" if len(uncovered_intents) > 4 else ""
        warnings.append(f"Uncovered mandatory intents: {labels}{suffix}.")

    passed = mandatory_covered == mandatory_total if mandatory_total else True

    return IntentCoverageResult(
        available=True,
        passed=passed,
        advisory_only=advisory_only,
        coverage_percent=coverage_percent,
        mandatory_total=mandatory_total,
        mandatory_covered=mandatory_covered,
        category_total=0,
        categories_covered=0,
        uncovered_intents=uncovered_intents,
        uncovered_categories=[],
        test_case_mappings=mappings,
        ungrounded_test_cases=ungrounded,
        warnings=warnings,
        errors=[] if passed or advisory_only else ["Mandatory intent coverage incomplete."],
    )
