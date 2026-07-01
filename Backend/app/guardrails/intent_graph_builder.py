"""Build labeled property graphs from Spec Intelligence dataset folders."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.guardrails.intent_graph_schemas import IntentEdge, IntentGraph, IntentNode

GRAPH_VERSION = 2

CLAUSE_FILE_RE = re.compile(r"^(\d+(?:_\d+)+)_file\.txt$", re.IGNORECASE)
CLAUSE_ON_LINE_RE = re.compile(
    r"(?:3GPP\s+TS\s+[\d.]+\s*(?:\[\d+\])?\s*,?\s*)?(?:Clause|clause)\s+([\d.]+)",
    re.IGNORECASE,
)

# Most specific line patterns first — one procedure per spec line.
LINE_PROCEDURE_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("5g_nsa_detach", re.compile(r"\b5g\s+nsa\s+detach\b", re.IGNORECASE)),
    ("5g_nsa_attach", re.compile(r"\b5g\s+nsa\s+attach\b", re.IGNORECASE)),
    ("lte_detach", re.compile(r"\blte\s+detach\b", re.IGNORECASE)),
    ("lte_attach", re.compile(r"\blte\s+attach\b", re.IGNORECASE)),
]

PROCEDURE_META: Dict[str, Tuple[str, List[str]]] = {
    "lte_attach": ("LTE Attach", ["lte attach", "e-utran initial attach"]),
    "lte_detach": ("LTE Detach", ["lte detach", "ue-initiated detach procedure for e-utran"]),
    "5g_nsa_attach": ("5G NSA Attach", ["5g nsa attach", "secondary node addition", "en-dc"]),
    "5g_nsa_detach": ("5G NSA Detach", ["5g nsa detach", "secondary node release"]),
}

KPI_META: Dict[str, Tuple[str, List[str]]] = {
    "attach_success_rate": (
        "Attach success rate",
        ["attach success rate", "attach success", "attach request and attach complete"],
    ),
    "detach_success_rate": (
        "Detach success rate",
        ["detach success rate", "detach success", "detach request and detach accept"],
    ),
    "attach_latency": (
        "Attach latency",
        ["attach latency", "maximum latency", "minimum latency", "average latency"],
    ),
    "sn_addition_success_rate": (
        "Secondary node addition success rate",
        ["secondary node addition success rate", "secondary node addition", "sgnb addition"],
    ),
    "sn_release_success_rate": (
        "Secondary node release success rate",
        ["secondary node release success rate", "secondary node release", "sgnb release"],
    ),
}

# Accurate procedure → KPI mapping (no cross-linking attach KPIs to detach).
KPI_PROCEDURE_SLUGS: Dict[str, Tuple[str, ...]] = {
    "attach_success_rate": ("lte_attach", "5g_nsa_attach"),
    "detach_success_rate": ("lte_detach", "5g_nsa_detach"),
    "attach_latency": ("lte_attach", "5g_nsa_attach"),
    "sn_addition_success_rate": ("5g_nsa_attach",),
    "sn_release_success_rate": ("5g_nsa_detach",),
}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "unknown"


def _dedupe_keywords(*items: str) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for item in items:
        token = item.strip().lower()
        if token and token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered


def _clause_id_from_filename(name: str) -> Optional[str]:
    match = CLAUSE_FILE_RE.match(name)
    if not match:
        return None
    return match.group(1).replace("_", ".")


def _find_section_file(folder: Path) -> Optional[Path]:
    matches = sorted(folder.glob("*_section.txt"))
    return matches[0] if matches else None


def _subsection_title(folder: Path, section_text: str) -> str:
    manifest = folder / "dataset_manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            subsection = data.get("metadata", {}).get("subsection")
            if subsection:
                return subsection
        except (json.JSONDecodeError, OSError):
            pass
    first_line = section_text.splitlines()[0].strip() if section_text else ""
    return first_line or folder.name


def _extract_procedure_clause_refs(section_text: str) -> Dict[str, Set[str]]:
    """Map canonical spec applicability lines to one procedure and its clause IDs."""
    refs: Dict[str, Set[str]] = {}
    in_applicability = False
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("test description"):
            in_applicability = True
            continue
        if in_applicability and stripped.lower().startswith("test setup"):
            break
        if not in_applicability:
            continue

        clause_ids = set(CLAUSE_ON_LINE_RE.findall(line))
        if not clause_ids:
            continue
        for proc_slug, pattern in LINE_PROCEDURE_PATTERNS:
            if pattern.search(line):
                refs.setdefault(proc_slug, set()).update(clause_ids)
                break
    return refs


def _procedure_active(proc_slug: str, section_lower: str, proc_clause_refs: Dict[str, Set[str]]) -> bool:
    if proc_slug in proc_clause_refs:
        return True
    _label, hints = PROCEDURE_META[proc_slug]
    return any(hint in section_lower for hint in hints)


def _kpi_mentioned(section_lower: str, keywords: List[str]) -> bool:
    return any(keyword in section_lower for keyword in keywords)


def build_intent_graph(dataset_folder: Path) -> IntentGraph:
    folder = Path(dataset_folder).resolve()
    section_path = _find_section_file(folder)
    section_text = _read_text(section_path) if section_path else ""
    section_lower = section_text.lower()
    subsection = _subsection_title(folder, section_text)

    nodes: List[IntentNode] = []
    edges: List[IntentEdge] = []
    node_ids: Set[str] = set()
    edge_keys: Set[Tuple[str, str, str]] = set()

    def add_node(node: IntentNode) -> None:
        if node.id in node_ids:
            return
        nodes.append(node)
        node_ids.add(node.id)

    def add_edge(source: str, target: str, relation: str) -> None:
        key = (source, target, relation)
        if key in edge_keys or source not in node_ids or target not in node_ids:
            return
        edge_keys.add(key)
        edges.append(IntentEdge(source=source, target=target, relation=relation))  # type: ignore[arg-type]

    subsection_id = f"subsection:{_slug(subsection)}"
    add_node(
        IntentNode(
            id=subsection_id,
            type="oran_subsection",
            label=subsection,
            mandatory=False,
            keywords=[subsection.lower()],
        )
    )

    clause_nodes: Dict[str, str] = {}
    for clause_path in sorted(folder.glob("*_file.txt")):
        clause_id = _clause_id_from_filename(clause_path.name)
        if not clause_id:
            continue
        node_id = f"clause:{clause_id.replace('.', '_')}"
        clause_nodes[clause_id] = node_id
        preview = _read_text(clause_path)[:200].strip().replace("\n", " ")
        add_node(
            IntentNode(
                id=node_id,
                type="clause",
                label=f"Clause {clause_id}",
                mandatory=False,
                clause_ids=[clause_id],
                references=[preview] if preview else [],
                keywords=_dedupe_keywords(clause_id, f"clause {clause_id}"),
            )
        )

    proc_clause_refs = _extract_procedure_clause_refs(section_text)
    active_procedure_slugs: List[str] = []

    for proc_slug, (proc_label, hints) in PROCEDURE_META.items():
        if not _procedure_active(proc_slug, section_lower, proc_clause_refs):
            continue
        proc_id = f"procedure:{proc_slug}"
        active_procedure_slugs.append(proc_slug)
        linked = sorted(proc_clause_refs.get(proc_slug, set()))
        add_node(
            IntentNode(
                id=proc_id,
                type="procedure",
                label=proc_label,
                mandatory=True,
                clause_ids=linked,
                keywords=_dedupe_keywords(proc_label, proc_slug.replace("_", " "), *hints),
            )
        )
        add_edge(subsection_id, proc_id, "requires")
        for clause_id in linked:
            clause_node_id = clause_nodes.get(clause_id)
            if clause_node_id:
                add_edge(proc_id, clause_node_id, "grounded_in")

    for kpi_slug, (kpi_label, keywords) in KPI_META.items():
        if not _kpi_mentioned(section_lower, keywords):
            continue
        kpi_id = f"kpi:{kpi_slug}"
        add_node(
            IntentNode(
                id=kpi_id,
                type="kpi",
                label=kpi_label,
                mandatory=True,
                keywords=_dedupe_keywords(kpi_label, *keywords),
            )
        )
        for proc_slug in KPI_PROCEDURE_SLUGS.get(kpi_slug, ()):
            if proc_slug in active_procedure_slugs:
                add_edge(f"procedure:{proc_slug}", kpi_id, "measures")

    return IntentGraph(
        version=GRAPH_VERSION,
        subsection=subsection,
        dataset_folder=str(folder),
        nodes=nodes,
        edges=edges,
    )
