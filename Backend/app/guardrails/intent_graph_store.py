"""Persist and load intent graphs beside Spec Intelligence datasets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

import networkx as nx

from app.guardrails.intent_graph_builder import GRAPH_VERSION, build_intent_graph
from app.guardrails.intent_graph_schemas import IntentGraph

INTENT_GRAPH_FILENAME = "intent_graph.json"
_GRAPH_CACHE: Dict[str, Tuple[float, IntentGraph]] = {}


def intent_graph_path(dataset_folder: Path) -> Path:
    return Path(dataset_folder).resolve() / INTENT_GRAPH_FILENAME


def _cache_key(folder: Path) -> str:
    return str(folder.resolve())


def _graph_is_stale(folder: Path, path: Path) -> bool:
    if not path.is_file():
        return True
    manifest = folder / "dataset_manifest.json"
    section_files = list(folder.glob("*_section.txt"))
    mtimes = [path.stat().st_mtime]
    if manifest.is_file():
        mtimes.append(manifest.stat().st_mtime)
    for section_file in section_files:
        mtimes.append(section_file.stat().st_mtime)
    for clause_file in folder.glob("*_file.txt"):
        mtimes.append(clause_file.stat().st_mtime)
    return path.stat().st_mtime < max(mtimes)


def invalidate_intent_graph_cache(dataset_folder: Path | str | None = None) -> None:
    if dataset_folder is None:
        _GRAPH_CACHE.clear()
        return
    _GRAPH_CACHE.pop(_cache_key(Path(dataset_folder)), None)


def save_intent_graph(dataset_folder: Path, graph: IntentGraph) -> Path:
    folder = Path(dataset_folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    path = intent_graph_path(folder)
    path.write_text(
        json.dumps(graph.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    mtime = path.stat().st_mtime
    _GRAPH_CACHE[_cache_key(folder)] = (mtime, graph)
    return path


def load_intent_graph_model(dataset_folder: Path, *, build_if_missing: bool = True) -> IntentGraph:
    folder = Path(dataset_folder).resolve()
    path = intent_graph_path(folder)
    key = _cache_key(folder)

    if path.is_file() and not _graph_is_stale(folder, path):
        cached = _GRAPH_CACHE.get(key)
        if cached and cached[0] == path.stat().st_mtime:
            return cached[1]
        data = json.loads(path.read_text(encoding="utf-8"))
        graph = IntentGraph.model_validate(data)
        if graph.version < GRAPH_VERSION:
            graph = build_intent_graph(folder)
            save_intent_graph(folder, graph)
            return graph
        mtime = path.stat().st_mtime
        _GRAPH_CACHE[key] = (mtime, graph)
        return graph

    if not build_if_missing:
        raise FileNotFoundError(f"Intent graph not found or stale: {path}")

    graph = build_intent_graph(folder)
    save_intent_graph(folder, graph)
    return graph


def load_intent_graph_nx(dataset_folder: Path, *, build_if_missing: bool = True) -> nx.DiGraph:
    model = load_intent_graph_model(dataset_folder, build_if_missing=build_if_missing)
    graph = nx.DiGraph()
    for node in model.nodes:
        graph.add_node(node.id, **node.model_dump())
    for edge in model.edges:
        graph.add_edge(edge.source, edge.target, relation=edge.relation)
    return graph


def build_and_save_intent_graph(dataset_folder: Path) -> IntentGraph:
    folder = Path(dataset_folder).resolve()
    invalidate_intent_graph_cache(folder)
    graph = build_intent_graph(folder)
    save_intent_graph(folder, graph)
    return graph
