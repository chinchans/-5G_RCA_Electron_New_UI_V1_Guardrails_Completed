"""Pydantic schemas for intent coverage knowledge graphs (LPG-style, in-memory)."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

IntentNodeType = Literal[
    "oran_subsection",
    "procedure",
    "clause",
    "kpi",
    "test_step",
    "category",
]

IntentEdgeRelation = Literal[
    "requires",
    "grounded_in",
    "measures",
    "validates",
    "expects_category",
]


class IntentNode(BaseModel):
    id: str = Field(min_length=1)
    type: IntentNodeType
    label: str = Field(min_length=1)
    mandatory: bool = True
    clause_ids: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class IntentEdge(BaseModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    relation: IntentEdgeRelation


class IntentGraph(BaseModel):
    version: int = 1
    subsection: str = ""
    dataset_folder: str = ""
    nodes: List[IntentNode] = Field(default_factory=list)
    edges: List[IntentEdge] = Field(default_factory=list)


class IntentCoverageMapping(BaseModel):
    test_case_id: str
    title: str = ""
    category: str = ""
    intent_ids: List[str] = Field(default_factory=list)


class IntentCoverageResult(BaseModel):
    available: bool = True
    passed: bool = True
    advisory_only: bool = True
    coverage_percent: float = 100.0
    mandatory_total: int = 0
    mandatory_covered: int = 0
    category_total: int = 0
    categories_covered: int = 0
    uncovered_intents: List[dict] = Field(default_factory=list)
    uncovered_categories: List[dict] = Field(default_factory=list)
    test_case_mappings: List[IntentCoverageMapping] = Field(default_factory=list)
    ungrounded_test_cases: List[str] = Field(default_factory=list)
    scenario_message_coverage: Optional[dict] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return self.model_dump()
