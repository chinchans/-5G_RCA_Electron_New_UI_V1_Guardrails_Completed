"""NLI groundedness guardrails: generated test scripts vs source test cases."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from app.guardrails.config import (
    GUARDRAILS_SCRIPT_GROUNDEDNESS_ENABLED,
    GUARDRAILS_SCRIPT_GROUNDEDNESS_MODE,
    NLI_CONTRADICTION_THRESHOLD,
    NLI_SKIP_ON_MODEL_ERROR,
    SCRIPT_GROUNDEDNESS_ENTAILMENT_THRESHOLD,
    SCRIPT_GROUNDEDNESS_LEVEL2_BLOCK_FLOOR_PERCENT,
    SCRIPT_GROUNDEDNESS_LEVEL2_MIN_PERCENT,
    SCRIPT_GROUNDEDNESS_MAX_CLAIMS_PER_FUNCTION,
    SCRIPT_GROUNDEDNESS_MAX_PAIRS,
)
from app.guardrails.test_script_traceability import (
    TraceabilityMatrixEntry,
    TestUnitTrace,
    _resolve_matrix,
    extract_test_unit_traces,
)

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{2,}")
_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "test",
        "case",
        "step",
        "using",
        "verify",
        "ensure",
        "check",
        "each",
        "all",
        "any",
        "are",
        "was",
        "were",
        "has",
        "have",
        "into",
        "via",
        "per",
    }
)


@dataclass
class FunctionGroundednessResult:
    function_name: str
    test_case_id: str
    claims_total: int = 0
    claims_grounded: int = 0
    claims_contradicted: int = 0
    grounded_percent: float = 100.0
    requirements_total: int = 0
    requirements_covered: int = 0
    requirement_coverage_percent: float = 100.0
    ungrounded_claims: List[str] = field(default_factory=list)
    contradicted_claims: List[str] = field(default_factory=list)
    missing_requirements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_name": self.function_name,
            "test_case_id": self.test_case_id,
            "claims_total": self.claims_total,
            "claims_grounded": self.claims_grounded,
            "claims_contradicted": self.claims_contradicted,
            "grounded_percent": self.grounded_percent,
            "requirements_total": self.requirements_total,
            "requirements_covered": self.requirements_covered,
            "requirement_coverage_percent": self.requirement_coverage_percent,
            "ungrounded_claims": self.ungrounded_claims,
            "contradicted_claims": self.contradicted_claims,
            "missing_requirements": self.missing_requirements,
        }


@dataclass
class ScriptGroundednessVerdict:
    passed: bool
    blocked: bool
    mode: str = "level2"
    reasons: List[str] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    per_function: List[FunctionGroundednessResult] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""
    model_available: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "mode": self.mode,
            "reasons": self.reasons,
            "findings": self.findings,
            "per_function": [item.to_dict() for item in self.per_function],
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "model_available": self.model_available,
        }


def _significant_words(text: str) -> List[str]:
    words = [w.lower() for w in _WORD_RE.findall(text)]
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


def _keyword_overlap_supported(premise: str, hypothesis: str, *, min_ratio: float = 0.45) -> bool:
    premise_words = set(_significant_words(premise))
    hyp_words = _significant_words(hypothesis)
    if not hyp_words:
        return False
    overlap = sum(1 for word in hyp_words if word in premise_words)
    return (overlap / len(hyp_words)) >= min_ratio


def _normalize_for_match(text: str) -> str:
    normalized = re.sub(r"[_\-]+", " ", text)
    normalized = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", normalized)
    normalized = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip().lower()


def _keyword_requirement_in_script(requirement: str, script_text: str, *, min_ratio: float = 0.5) -> bool:
    script_words = set(_significant_words(_normalize_for_match(script_text)))
    req_words = _significant_words(_normalize_for_match(requirement))
    if not req_words:
        return True
    overlap = sum(1 for word in req_words if word in script_words)
    return (overlap / len(req_words)) >= min_ratio


def _truncate(text: str, limit: int = 2000) -> str:
    compact = " ".join(text.split())
    return compact[:limit] if len(compact) > limit else compact


def _nli_score(premise: str, hypothesis: str) -> Tuple[float, float, float]:
    try:
        from app.guardrails.nli_groundedness_service import _nli_model
    except ImportError:
        return 0.0, 0.0, 0.0

    if not _nli_model.load():
        return 0.0, 0.0, 0.0

    row = _nli_model.predict_probs([(_truncate(premise), _truncate(hypothesis, 512))])
    if not row:
        return 0.0, 0.0, 0.0
    return row[0]


def _claim_is_grounded(premise: str, claim: str) -> bool:
    if _keyword_overlap_supported(premise, claim):
        return True
    _contradiction, entailment, _neutral = _nli_score(premise, claim)
    return entailment >= SCRIPT_GROUNDEDNESS_ENTAILMENT_THRESHOLD


def _claim_is_contradicted(premise: str, claim: str) -> bool:
    contradiction, _entailment, _neutral = _nli_score(premise, claim)
    return contradiction >= NLI_CONTRADICTION_THRESHOLD


def _requirement_covered(script_text: str, requirement: str, premise: str) -> bool:
    normalized_script = _normalize_for_match(script_text)
    if _keyword_requirement_in_script(requirement, normalized_script):
        return True
    if _keyword_overlap_supported(requirement, normalized_script, min_ratio=0.4):
        return True
    _contradiction, entailment, _neutral = _nli_score(normalized_script, requirement)
    if entailment >= SCRIPT_GROUNDEDNESS_ENTAILMENT_THRESHOLD:
        return True
    _c2, e2, _n2 = _nli_score(premise, requirement)
    if e2 >= SCRIPT_GROUNDEDNESS_ENTAILMENT_THRESHOLD and _keyword_overlap_supported(
        normalized_script, requirement, min_ratio=0.35
    ):
        return True
    return False


def _build_test_case_premise(entry: TraceabilityMatrixEntry) -> str:
    parts: List[str] = [entry.title]
    parts.extend(entry.steps)
    parts.extend(entry.expected_results)
    if entry.messages:
        parts.extend(entry.messages)
    return " ".join(parts)


def _requirements_from_entry(entry: TraceabilityMatrixEntry) -> List[str]:
    reqs: List[str] = []
    for item in list(entry.steps) + list(entry.expected_results):
        text = str(item).strip()
        if len(text) >= 12:
            reqs.append(text)
    return list(dict.fromkeys(reqs))


def _code_node_for_trace(tree: ast.AST, trace: TestUnitTrace) -> Optional[ast.AST]:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name == trace.function_name and node.lineno == trace.line:
            return node
    return None


def _source_segment(script: str, node: ast.AST) -> str:
    try:
        segment = ast.get_source_segment(script, node)
        if segment:
            return segment
    except (TypeError, ValueError):
        pass
    return ""


def _string_from_node(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.strip()
    if isinstance(node, ast.JoinedStr):
        parts: List[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
        joined = "".join(parts).strip()
        return joined or None
    return None


def extract_claims_from_function(script: str, func_node: ast.AST) -> List[str]:
    """Extract checkable claims (assertions, validation strings) from a test function."""
    claims: List[str] = []
    seen: Set[str] = set()

    def _add_claim(text: str) -> None:
        cleaned = " ".join(text.split()).strip()
        if len(cleaned) < 8 or cleaned in seen:
            return
        seen.add(cleaned)
        claims.append(cleaned)

    for node in ast.walk(func_node):
        if isinstance(node, ast.Assert):
            segment = _source_segment(script, node) or "assert"
            _add_claim(segment)
            test = node.test
            if isinstance(test, ast.Compare):
                for comparator in test.comparators:
                    value = _string_from_node(comparator)
                    if value:
                        _add_claim(value)
            elif isinstance(test, ast.Call):
                for arg in test.args:
                    value = _string_from_node(arg)
                    if value:
                        _add_claim(value)
        elif isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Attribute):
                name = func.attr.lower()
            elif isinstance(func, ast.Name):
                name = func.id.lower()
            if name in {"assert", "assertin", "assertequal", "asserttrue", "assertfalse"}:
                segment = _source_segment(script, node)
                if segment:
                    _add_claim(segment)
            if name in {"info", "debug", "warning", "error", "log", "validate", "verify", "check"}:
                for arg in node.args[:2]:
                    value = _string_from_node(arg)
                    if value and len(value) >= 8:
                        _add_claim(value)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value.strip()
            if len(value) >= 16 and any(
                token in value.lower()
                for token in ("attach", "detach", "rrc", "nas", "assert", "verify", "message", "success", "fail")
            ):
                _add_claim(value)

    return claims[:SCRIPT_GROUNDEDNESS_MAX_CLAIMS_PER_FUNCTION]


def _evaluate_function_groundedness(
    *,
    trace: TestUnitTrace,
    entry: TraceabilityMatrixEntry,
    script: str,
    func_node: ast.AST,
    mode: str,
    model_available: bool,
) -> FunctionGroundednessResult:
    premise = _build_test_case_premise(entry)
    body_text = _source_segment(script, func_node) or premise
    claims = extract_claims_from_function(script, func_node)
    requirements = _requirements_from_entry(entry)

    result = FunctionGroundednessResult(
        function_name=trace.function_name,
        test_case_id=entry.test_case_id,
        claims_total=len(claims),
        requirements_total=len(requirements),
    )

    grounded = 0
    for claim in claims:
        if not model_available:
            if _keyword_overlap_supported(premise, claim):
                grounded += 1
            else:
                result.ungrounded_claims.append(claim)
            continue

        if _claim_is_contradicted(premise, claim):
            result.claims_contradicted += 1
            result.contradicted_claims.append(claim)
            continue
        if _claim_is_grounded(premise, claim):
            grounded += 1
        else:
            result.ungrounded_claims.append(claim)

    result.claims_grounded = grounded
    if claims:
        result.grounded_percent = round((grounded / len(claims)) * 100.0, 1)
    else:
        result.grounded_percent = 100.0

    if mode == "level3" and requirements:
        covered = 0
        for requirement in requirements:
            if _requirement_covered(body_text, requirement, premise):
                covered += 1
            else:
                result.missing_requirements.append(requirement)
        result.requirements_covered = covered
        result.requirement_coverage_percent = round((covered / len(requirements)) * 100.0, 1)

    return result


def _extract_script_corpus(script: str) -> str:
    parts: List[str] = []
    try:
        tree = ast.parse(script)
    except SyntaxError:
        return _normalize_for_match(script)[:4000]

    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            parts.append(_normalize_for_match(node.name))
            doc = ast.get_docstring(node)
            if doc:
                parts.append(_normalize_for_match(doc))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) > 3:
            parts.append(_normalize_for_match(node.value))
    return _normalize_for_match(" ".join(parts))


def _matrix_entry_hypothesis(entry: TraceabilityMatrixEntry) -> str:
    parts = [entry.title]
    parts.extend(entry.steps[:6])
    parts.extend(entry.expected_results[:4])
    parts.extend(entry.messages[:4])
    return _truncate(" ".join(part for part in parts if part), 800)


def validate_whole_script_groundedness(
    script: str,
    *,
    source_text: str = "",
    dataset_folder: Optional[str] = None,
    mode: Optional[str] = None,
) -> ScriptGroundednessVerdict:
    """Refine-mode groundedness when no per-function trace comments exist."""
    resolved_mode = (mode or GUARDRAILS_SCRIPT_GROUNDEDNESS_MODE or "level2").lower().strip()
    matrix = _resolve_matrix(source_text, dataset_folder)
    if not matrix:
        return ScriptGroundednessVerdict(
            passed=True,
            blocked=False,
            mode=resolved_mode,
            skipped=True,
            skip_reason="no_source_test_cases_found",
        )

    script_corpus = _extract_script_corpus(script)
    if not script_corpus.strip():
        return ScriptGroundednessVerdict(
            passed=False,
            blocked=True,
            mode=resolved_mode,
            reasons=["Refined script has no testable content to validate against source test cases."],
            findings=[
                {
                    "layer": "script_guardrail",
                    "check": "groundedness",
                    "severity": "error",
                    "detail": "Script body is empty or unreadable for groundedness checks.",
                }
            ],
        )

    findings: List[Dict[str, Any]] = []
    reasons: List[str] = []
    blocked = False
    grounded_entries = 0
    evaluated = 0

    for entry in matrix[:SCRIPT_GROUNDEDNESS_MAX_PAIRS]:
        hypothesis = _matrix_entry_hypothesis(entry)
        if not hypothesis.strip():
            continue
        evaluated += 1
        if _claim_is_contradicted(script_corpus, hypothesis):
            blocked = True
            detail = (
                f"Refined script content contradicts source test case "
                f"'{entry.test_case_id}: {entry.title}'."
            )
            findings.append(
                {
                    "layer": "script_guardrail",
                    "check": "groundedness",
                    "severity": "error",
                    "detail": detail,
                }
            )
            reasons.append(detail)
            continue
        if _claim_is_grounded(script_corpus, hypothesis) or _requirement_covered(
            script_corpus, hypothesis, script_corpus
        ):
            grounded_entries += 1

    grounded_percent = (
        round((grounded_entries / evaluated) * 100.0, 1) if evaluated else 0.0
    )
    if evaluated and grounded_percent < SCRIPT_GROUNDEDNESS_LEVEL2_BLOCK_FLOOR_PERCENT:
        blocked = True
        detail = (
            f"Refined script groundedness {grounded_percent}% is below floor "
            f"{SCRIPT_GROUNDEDNESS_LEVEL2_BLOCK_FLOOR_PERCENT}% against source test cases."
        )
        findings.append(
            {
                "layer": "script_guardrail",
                "check": "groundedness",
                "severity": "error",
                "detail": detail,
            }
        )
        reasons.append(detail)

    return ScriptGroundednessVerdict(
        passed=not blocked,
        blocked=blocked,
        mode=resolved_mode,
        reasons=reasons,
        findings=findings,
        per_function=[],
        skipped=False,
        skip_reason="",
    )


def validate_script_groundedness(
    script: str,
    *,
    source_text: str = "",
    dataset_folder: Optional[str] = None,
    mode: Optional[str] = None,
    valid_trace_mappings: Optional[Sequence[Dict[str, Any]]] = None,
    refine_strict: bool = False,
) -> ScriptGroundednessVerdict:
    """Validate script content against source test cases (Level 2 or Level 3)."""
    resolved_mode = (mode or GUARDRAILS_SCRIPT_GROUNDEDNESS_MODE or "level2").lower().strip()
    if resolved_mode in {"off", "disabled", "false", "none"}:
        return ScriptGroundednessVerdict(
            passed=True,
            blocked=False,
            mode=resolved_mode,
            skipped=True,
            skip_reason="script_groundedness_disabled",
        )

    if not GUARDRAILS_SCRIPT_GROUNDEDNESS_ENABLED:
        return ScriptGroundednessVerdict(
            passed=True,
            blocked=False,
            mode=resolved_mode,
            skipped=True,
            skip_reason="script_groundedness_disabled",
        )

    matrix = _resolve_matrix(source_text, dataset_folder)
    if not matrix:
        return ScriptGroundednessVerdict(
            passed=True,
            blocked=False,
            mode=resolved_mode,
            skipped=True,
            skip_reason="no_source_test_cases_found",
        )

    try:
        tree = ast.parse(script)
    except SyntaxError:
        return ScriptGroundednessVerdict(
            passed=True,
            blocked=False,
            mode=resolved_mode,
            skipped=True,
            skip_reason="script_syntax_invalid",
        )

    traces, _unmapped = extract_test_unit_traces(script)
    if valid_trace_mappings:
        allowed = {
            (item.get("test_function"), item.get("test_case_id"))
            for item in valid_trace_mappings
            if item.get("test_function") and item.get("test_case_id")
        }
        traces = [
            trace
            for trace in traces
            if (trace.function_name, trace.case_id) in allowed
            or any(
                m.get("test_function") == trace.function_name
                and m.get("test_case_id") == trace.case_id
                for m in valid_trace_mappings
            )
        ]

    if not traces:
        if refine_strict:
            return validate_whole_script_groundedness(
                script,
                source_text=source_text,
                dataset_folder=dataset_folder,
                mode=resolved_mode,
            )
        return ScriptGroundednessVerdict(
            passed=True,
            blocked=False,
            mode=resolved_mode,
            skipped=True,
            skip_reason="no_mapped_test_functions_for_groundedness",
        )

    matrix_by_id = {entry.test_case_id: entry for entry in matrix}
    try:
        from app.guardrails.nli_groundedness_service import _nli_model

        model_available = _nli_model.load()
    except ImportError:
        model_available = False

    if not model_available and not NLI_SKIP_ON_MODEL_ERROR:
        return ScriptGroundednessVerdict(
            passed=False,
            blocked=True,
            mode=resolved_mode,
            model_available=False,
            reasons=["NLI model unavailable for script groundedness validation."],
            findings=[
                {
                    "layer": "script_guardrail",
                    "check": "groundedness",
                    "severity": "error",
                    "detail": "NLI cross-encoder could not be loaded for script groundedness checks.",
                }
            ],
        )

    per_function: List[FunctionGroundednessResult] = []
    findings: List[Dict[str, Any]] = []
    reasons: List[str] = []
    blocked = False
    pair_budget = SCRIPT_GROUNDEDNESS_MAX_PAIRS

    for trace in traces:
        if pair_budget <= 0:
            break
        entry = matrix_by_id.get(trace.case_id)
        if not entry:
            for matrix_entry in matrix:
                if matrix_entry.test_case_id.lower() == trace.case_id.lower():
                    entry = matrix_entry
                    break
        if not entry:
            continue

        func_node = _code_node_for_trace(tree, trace)
        if not func_node:
            continue

        fn_result = _evaluate_function_groundedness(
            trace=trace,
            entry=entry,
            script=script,
            func_node=func_node,
            mode=resolved_mode,
            model_available=model_available,
        )
        per_function.append(fn_result)
        pair_budget -= max(1, fn_result.claims_total + fn_result.requirements_total)

        if fn_result.contradicted_claims:
            blocked = True
            sample = fn_result.contradicted_claims[0][:120]
            detail = (
                f"{trace.function_name} ({entry.test_case_id}): script claim contradicts "
                f"source test case — '{sample}'"
            )
            findings.append(
                {
                    "layer": "script_guardrail",
                    "check": "groundedness",
                    "severity": "error",
                    "detail": detail,
                }
            )
            reasons.append(detail)

        if resolved_mode == "level3":
            if fn_result.missing_requirements:
                blocked = True
                sample = fn_result.missing_requirements[0][:100]
                detail = (
                    f"{trace.function_name} ({entry.test_case_id}): missing test case "
                    f"step/expected result in script — '{sample}…'"
                )
                findings.append(
                    {
                        "layer": "script_guardrail",
                        "check": "groundedness",
                        "severity": "error",
                        "detail": detail,
                    }
                )
                reasons.append(detail)
        elif resolved_mode == "level2":
            if fn_result.grounded_percent < SCRIPT_GROUNDEDNESS_LEVEL2_BLOCK_FLOOR_PERCENT:
                blocked = True
                detail = (
                    f"{trace.function_name} ({entry.test_case_id}): groundedness "
                    f"{fn_result.grounded_percent}% is below floor "
                    f"{SCRIPT_GROUNDEDNESS_LEVEL2_BLOCK_FLOOR_PERCENT}%"
                )
                findings.append(
                    {
                        "layer": "script_guardrail",
                        "check": "groundedness",
                        "severity": "error",
                        "detail": detail,
                    }
                )
                reasons.append(detail)
            elif fn_result.grounded_percent < SCRIPT_GROUNDEDNESS_LEVEL2_MIN_PERCENT:
                detail = (
                    f"{trace.function_name} ({entry.test_case_id}): groundedness "
                    f"{fn_result.grounded_percent}% is below target "
                    f"{SCRIPT_GROUNDEDNESS_LEVEL2_MIN_PERCENT}% (review recommended)"
                )
                findings.append(
                    {
                        "layer": "script_guardrail",
                        "check": "groundedness",
                        "severity": "warning",
                        "detail": detail,
                    }
                )

    if not model_available and NLI_SKIP_ON_MODEL_ERROR:
        findings.append(
            {
                "layer": "script_guardrail",
                "check": "groundedness",
                "severity": "warning",
                "detail": "NLI model unavailable; used keyword overlap only for script groundedness.",
            }
        )

    return ScriptGroundednessVerdict(
        passed=not blocked,
        blocked=blocked,
        mode=resolved_mode,
        reasons=list(dict.fromkeys(reasons)),
        findings=findings,
        per_function=per_function,
        model_available=model_available,
    )
