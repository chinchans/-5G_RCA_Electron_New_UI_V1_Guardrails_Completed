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
from app.guardrails.config import (
    INTENT_COVERAGE_DOMAIN_GATE,
    INTENT_COVERAGE_MATCH_MODE,
    INTENT_COVERAGE_NLI_THRESHOLD,
    INTENT_COVERAGE_USE_NLI,
)
from app.guardrails.tsg_prompt_guardrail import (
    _OFF_TOPIC_REFINE_SIGNALS,
    _TELECOM_DATASET_SIGNALS,
    _signal_hits,
)
from app.guardrails.intent_graph_store import load_intent_graph_model

CLAUSE_ID_RE = re.compile(r"\b\d+(?:\.\d+)+\b")
JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
VALID_MATCH_MODES = frozenset({"keyword", "hybrid", "semantic"})

_REFUSAL_CORPUS_SIGNALS = frozenset({
    "cannot provide",
    "cannot generate",
    "no information related",
    "unrelated to the content",
    "unrelated to the dataset",
    "requested topic is unrelated",
    "does not contain information",
    "i cannot provide a summary",
})

_PROCEDURE_TOKEN_ALIASES: Dict[str, Tuple[str, ...]] = {
    "lte": ("lte", "e-utran", "eutran", "e utran"),
    "5g": ("5g", "nr", "gnodeb", "gnb"),
    "nsa": ("nsa", "endc", "en-dc", "secondary node"),
    "attach": ("attach", "registration", "camp on"),
    "detach": ("detach", "deregister", "power off", "switch off"),
}


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


def _humanize_identifier(value: str) -> str:
    text = str(value).strip()
    if not text:
        return ""
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", text)
    text = re.sub(r"(\d)([A-Za-z])", r"\1 \2", text)
    text = re.sub(r"([A-Za-z])(\d)", r"\1 \2", text)
    return text


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
        if key in {"testCaseID", "testCaseId"} and value:
            parts.append(_humanize_identifier(str(value)))
            continue
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


def _label_tokens(node: IntentNode) -> List[str]:
    return [token.lower() for token in re.findall(r"[a-zA-Z0-9]+", node.label) if len(token) > 1]


def _procedure_token_present(lower: str, token: str) -> bool:
    aliases = _PROCEDURE_TOKEN_ALIASES.get(token, (token,))
    return any(alias in lower for alias in aliases)


def _match_distributed_procedures(text: str, index: _GraphMatchIndex) -> Set[str]:
    """Match procedures when label tokens co-occur in text (e.g. LTE + detach)."""
    lower = text.lower()
    matched: Set[str] = set()
    for node in index.matchable_nodes:
        if node.type != "procedure":
            continue
        tokens = _label_tokens(node)
        if tokens and all(_procedure_token_present(lower, token) for token in tokens):
            matched.add(node.id)
    return matched


def _semantic_text_matches(text: str, index: _GraphMatchIndex) -> Set[str]:
    matched = _match_distributed_procedures(text, index)
    matched.update(_match_text_to_intents(text, index))
    return matched


def _build_intent_hypothesis(node: IntentNode) -> str:
    parts = [node.label]
    if node.keywords:
        parts.extend(node.keywords[:6])
    if node.clause_ids:
        parts.append(f"3GPP clause {' '.join(node.clause_ids)}")
    return ". ".join(parts)


def _resolve_match_mode(match_mode: Optional[str], use_nli_for_gaps: Optional[bool]) -> str:
    mode = (match_mode or INTENT_COVERAGE_MATCH_MODE or "hybrid").lower().strip()
    if mode not in VALID_MATCH_MODES:
        mode = "hybrid"
    if use_nli_for_gaps is False and mode == "hybrid":
        return "keyword"
    if use_nli_for_gaps is True and mode == "keyword":
        return "hybrid"
    return mode


def _semantic_nli_enabled(match_mode: str, use_nli_for_gaps: Optional[bool]) -> bool:
    if match_mode == "semantic":
        return True
    if match_mode == "keyword":
        return False
    if use_nli_for_gaps is not None:
        return use_nli_for_gaps
    return INTENT_COVERAGE_USE_NLI


def _match_test_case_keyword_intents(
    test_case: Dict[str, Any],
    index: _GraphMatchIndex,
    *,
    match_mode: str = "hybrid",
) -> Set[str]:
    """Keyword / clause / distributed-procedure matches only (no NLI)."""
    matched: Set[str] = set()
    text = _flatten_test_case_text(test_case)

    explicit = test_case.get("covers_intents") or test_case.get("coversIntents") or []
    if isinstance(explicit, list):
        for item in explicit:
            item_str = str(item).strip()
            if item_str in index.nodes_by_id:
                matched.add(item_str)

    if match_mode == "keyword":
        matched.update(_match_text_to_intents(text, index))
    else:
        matched.update(_semantic_text_matches(text, index))
    return matched


def _combined_test_case_text(test_cases: Sequence[Dict[str, Any]]) -> str:
    return " ".join(_flatten_test_case_text(case) for case in test_cases)


def _count_off_topic_signals(text: str) -> int:
    lowered = (text or "").lower()
    return sum(1 for phrase in _OFF_TOPIC_REFINE_SIGNALS if phrase in lowered)


def _is_telecom_intent_graph(index: _GraphMatchIndex) -> bool:
    return bool(index.mandatory_nodes)


def _evaluate_suite_domain_alignment(
    test_cases: Sequence[Dict[str, Any]],
    index: _GraphMatchIndex,
) -> Tuple[bool, str]:
    if not INTENT_COVERAGE_DOMAIN_GATE or not _is_telecom_intent_graph(index):
        return True, ""

    combined = _combined_test_case_text(test_cases)
    if not combined.strip():
        return False, "Generated test cases are empty."

    off_topic_hits = _count_off_topic_signals(combined)
    telecom_hits = _signal_hits(combined, _TELECOM_DATASET_SIGNALS)

    if off_topic_hits > 0 and telecom_hits < 2:
        sample = next(
            (phrase for phrase in _OFF_TOPIC_REFINE_SIGNALS if phrase in combined.lower()),
            "off-topic content",
        )
        return (
            False,
            "Generated test cases appear off-topic for the loaded telecom dataset "
            f"(detected: {sample!r}).",
        )

    if telecom_hits == 0:
        return (
            False,
            "Generated test cases do not reference telecom/5G procedures from the loaded dataset.",
        )
    return True, ""


def _is_refusal_corpus(text: str) -> bool:
    lowered = (text or "").lower()
    return any(signal in lowered for signal in _REFUSAL_CORPUS_SIGNALS)


def _match_test_case_to_intents(
    test_case: Dict[str, Any],
    index: _GraphMatchIndex,
    *,
    match_mode: str = "hybrid",
    use_nli: bool = False,
    allow_nli: bool = True,
) -> Set[str]:
    matched = _match_test_case_keyword_intents(test_case, index, match_mode=match_mode)

    if use_nli and allow_nli:
        if match_mode == "semantic":
            nli_nodes = list(index.mandatory_nodes)
        else:
            nli_nodes = [node for node in index.mandatory_nodes if node.id not in matched]
        if nli_nodes:
            text = _flatten_test_case_text(test_case)
            matched.update(_nli_semantic_matches(text, nli_nodes))

    return matched


def _nli_entailment_scores(text: str, nodes: Sequence[IntentNode]) -> Dict[str, float]:
    try:
        from app.guardrails.nli_groundedness_service import _nli_model
    except ImportError:
        return {}

    if not _nli_model.load() or not nodes:
        return {}

    premise = " ".join(text.split())
    if len(premise) > 4000:
        premise = premise[:4000]

    pairs = [(premise, _build_intent_hypothesis(node)) for node in nodes]
    probs = _nli_model.predict_probs(pairs)
    scores: Dict[str, float] = {}
    for node, row in zip(nodes, probs):
        _contradiction, entailment, _neutral = row
        scores[node.id] = float(entailment)
    return scores


def _nli_semantic_matches(text: str, nodes: Sequence[IntentNode]) -> Set[str]:
    scores = _nli_entailment_scores(text, nodes)
    return {
        node_id
        for node_id, entailment in scores.items()
        if entailment >= INTENT_COVERAGE_NLI_THRESHOLD
    }


def _suite_semantic_gap_fill(
    test_cases: Sequence[Dict[str, Any]],
    index: _GraphMatchIndex,
    covered_intents: Set[str],
    *,
    allow_nli: bool = True,
) -> Set[str]:
    if not allow_nli:
        return set()
    uncovered = [node for node in index.mandatory_nodes if node.id not in covered_intents]
    if not uncovered:
        return set()

    best_scores: Dict[str, float] = {node.id: 0.0 for node in uncovered}
    for test_case in test_cases:
        scores = _nli_entailment_scores(_flatten_test_case_text(test_case), uncovered)
        for node_id, entailment in scores.items():
            if entailment > best_scores[node_id]:
                best_scores[node_id] = entailment

    return {
        node_id
        for node_id, entailment in best_scores.items()
        if entailment >= INTENT_COVERAGE_NLI_THRESHOLD
    }


def validate_intent_coverage(
    dataset_folder: Path | str,
    generated_text: str,
    *,
    use_nli_for_gaps: Optional[bool] = None,
    match_mode: Optional[str] = None,
    advisory_only: bool = True,
    require_structured_json: bool = False,
) -> IntentCoverageResult:
    resolved_mode = _resolve_match_mode(match_mode, use_nli_for_gaps)
    use_nli = _semantic_nli_enabled(resolved_mode, use_nli_for_gaps)
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
        if require_structured_json:
            return IntentCoverageResult(
                available=True,
                passed=False,
                advisory_only=advisory_only,
                warnings=["Structured JSON test cases were not detected in refined output."],
                errors=[
                    "Refined output must remain valid structured test case JSON when refining test cases."
                ],
            )
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

    if corpus_fallback and _is_refusal_corpus(generated_text):
        return IntentCoverageResult(
            available=True,
            passed=False,
            advisory_only=advisory_only,
            coverage_percent=0.0,
            mandatory_total=len(index.mandatory_nodes),
            mandatory_covered=0,
            warnings=["Structured JSON test cases were not detected; output appears to refuse or deflect."],
            errors=[
                "Generated output is unrelated to the dataset and cannot be treated as test case coverage."
            ],
        )

    domain_ok, domain_reason = _evaluate_suite_domain_alignment(test_cases, index)
    allow_nli = domain_ok and use_nli
    strict_mode = require_structured_json or not advisory_only

    covered_intents: Set[str] = set()
    keyword_covered_intents: Set[str] = set()
    mappings: List[IntentCoverageMapping] = []
    ungrounded: List[str] = []

    for test_case in test_cases:
        case_id = str(
            test_case.get("testCaseID")
            or test_case.get("testCaseId")
            or test_case.get("id")
            or "unknown"
        )
        keyword_ids = _match_test_case_keyword_intents(
            test_case,
            index,
            match_mode=resolved_mode,
        )
        keyword_covered_intents.update(keyword_ids)

        intent_ids = sorted(
            _match_test_case_to_intents(
                test_case,
                index,
                match_mode=resolved_mode,
                use_nli=use_nli,
                allow_nli=allow_nli,
            )
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

    if allow_nli:
        covered_intents.update(
            _suite_semantic_gap_fill(test_cases, index, covered_intents, allow_nli=True)
        )
    else:
        covered_intents = set(keyword_covered_intents)

    covered_intents = index.expand(covered_intents)
    keyword_covered_intents = index.expand(keyword_covered_intents)

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
    errors: List[str] = []
    if corpus_fallback:
        warnings.append(
            "Structured JSON test cases were not detected; validated full generated output as a single corpus."
        )
    if not domain_ok:
        errors.append(domain_reason)
        warnings.append("NLI semantic gap-fill disabled because content failed dataset domain alignment.")
    if ungrounded:
        warning = (
            f"{len(ungrounded)} test case(s) did not map to any intent graph node "
            f"({', '.join(ungrounded[:5])}{'…' if len(ungrounded) > 5 else ''})."
        )
        warnings.append(warning)
        if strict_mode:
            errors.append(warning)
    if uncovered_intents:
        labels = ", ".join(item["label"] for item in uncovered_intents[:4])
        suffix = "…" if len(uncovered_intents) > 4 else ""
        warnings.append(f"Uncovered mandatory intents: {labels}{suffix}.")
        if strict_mode:
            errors.append(f"Uncovered mandatory intents: {labels}{suffix}.")

    passed = mandatory_covered == mandatory_total if mandatory_total else True
    if not domain_ok:
        passed = False
    if strict_mode and ungrounded:
        passed = False
    if strict_mode and uncovered_intents:
        passed = False

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
        errors=[] if passed else (errors or ["Mandatory intent coverage incomplete."]),
    )
