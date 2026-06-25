"""Pydantic schemas for Specification Intelligence extraction output."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ExtractionMetadata(BaseModel):
    source_file_id: str = Field(min_length=1)
    source_document_path: str = Field(min_length=1)
    section: str = Field(min_length=1)
    subsection: str = Field(min_length=1)
    safe_subsection: str = Field(min_length=1)
    dataset_folder: str = Field(min_length=1)


class GraphNode(BaseModel):
    id: str = Field(min_length=1)


class GraphEdge(BaseModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)


class KnowledgeGraph(BaseModel):
    directed: bool = True
    multigraph: bool = False
    nodes: List[GraphNode] = Field(min_length=1)
    edges: List[GraphEdge] = Field(default_factory=list)

    @field_validator("nodes")
    @classmethod
    def must_include_start(cls, nodes: List[GraphNode]) -> List[GraphNode]:
        if not any(n.id == "start" for n in nodes):
            raise ValueError("Knowledge graph must include a 'start' node")
        return nodes


class ReferenceEntry(BaseModel):
    reference: str = Field(min_length=1)
    clauses: List[str] = Field(default_factory=list)
    source_file: Optional[str] = None
    status: Literal["present", "missing"] = "missing"


class ClauseFileEntry(BaseModel):
    clause_id: str = Field(min_length=1)
    file_path: str = Field(min_length=1)
    source_reference: Optional[str] = None
    content: str = Field(min_length=1)
    traceable: bool = False


class SpecIntelDatasetOutput(BaseModel):
    """Validated shape of a Specification Intelligence dataset extraction."""

    metadata: ExtractionMetadata
    section_text: str = Field(min_length=1)
    references: List[ReferenceEntry] = Field(default_factory=list)
    clauses: List[str] = Field(default_factory=list)
    present_references: List[str] = Field(default_factory=list)
    missing_references: List[str] = Field(default_factory=list)
    ref_clause_map: dict[str, List[str]] = Field(default_factory=dict)
    graph: KnowledgeGraph
    total_content: str = Field(min_length=1)
    recursive_extraction_text: Optional[str] = None
    clause_files: List[ClauseFileEntry] = Field(default_factory=list)
    graph_json_path: Optional[str] = None
