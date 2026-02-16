from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

from .tf_loader import BhsaApi


@dataclass
class ClauseAtomGraph:
    """Clause atom graph scoped to a selected text span."""

    api: BhsaApi
    nodes: List[int]
    mother: Dict[int, Optional[int]]
    children: Dict[int, List[int]]
    roots: List[int]

    def typ(self, n: int) -> str:
        value = self.api.F.typ.v(n)
        return value if value is not None else "?"

    def code(self, n: int) -> Optional[int]:
        return self.api.F.code.v(n)

    def tab(self, n: int) -> Optional[int]:
        return self.api.F.tab.v(n)

    def section_label(self, n: int) -> str:
        section = self.api.T.sectionFromNode(n)
        if not section:
            return "?:?:?"
        if len(section) >= 3:
            return f"{section[0]} {section[1]}:{section[2]}"
        return ":".join(str(item) for item in section)

    def text(self, n: int, *, max_len: int = 80) -> str:
        text = self.api.T.text(n)
        normalized = " ".join(text.split())
        if len(normalized) <= max_len:
            return normalized
        return f"{normalized[: max_len - 1]}..."


def _node_from_book(api: BhsaApi, book: str) -> int:
    node = api.T.nodeFromSection((book,))
    if node is None:
        raise ValueError(f"Unknown book: {book}")
    return node


def _node_from_chapter(api: BhsaApi, book: str, chapter: int) -> int:
    node = api.T.nodeFromSection((book, chapter))
    if node is None:
        raise ValueError(f"Unknown chapter selection: {book} {chapter}")
    return node


def _node_from_verse(api: BhsaApi, book: str, chapter: int, verse: int) -> int:
    node = api.T.nodeFromSection((book, chapter, verse))
    if node is None:
        raise ValueError(f"Unknown verse selection: {book} {chapter}:{verse}")
    return node


def _clause_atoms_in_node(api: BhsaApi, node: int) -> List[int]:
    return list(api.L.d(node, otype="clause_atom"))


def validate_selection_scope(
    *,
    book: str,
    chapter: Optional[int] = None,
    verse_from: Optional[int] = None,
    verse_to: Optional[int] = None,
) -> None:
    """Validate scope values before TF node lookups."""
    if not book or not book.strip():
        raise ValueError("book is required")
    if chapter is not None and chapter <= 0:
        raise ValueError("chapter must be greater than 0")
    if verse_from is not None and verse_from <= 0:
        raise ValueError("verse_from must be greater than 0")
    if verse_to is not None and verse_to <= 0:
        raise ValueError("verse_to must be greater than 0")

    if chapter is None and (verse_from is not None or verse_to is not None):
        raise ValueError("chapter is required when verse_from/verse_to are provided")
    if verse_to is not None and verse_from is None:
        raise ValueError("verse_from is required when verse_to is provided")
    if verse_from is not None and verse_to is not None and verse_to < verse_from:
        raise ValueError(f"invalid verse range: {verse_from}-{verse_to}")


def build_graph_for_selection(
    api: BhsaApi,
    *,
    book: str,
    chapter: Optional[int] = None,
    verse_from: Optional[int] = None,
    verse_to: Optional[int] = None,
) -> ClauseAtomGraph:
    """Build daughter->mother and mother->children maps for a text selection."""
    validate_selection_scope(
        book=book,
        chapter=chapter,
        verse_from=verse_from,
        verse_to=verse_to,
    )

    if chapter is None:
        anchor = _node_from_book(api, book)
        nodes = _clause_atoms_in_node(api, anchor)
    elif verse_from is None:
        anchor = _node_from_chapter(api, book, chapter)
        nodes = _clause_atoms_in_node(api, anchor)
    else:
        if verse_to is None:
            verse_to = verse_from
        if verse_to < verse_from:
            raise ValueError("verse_to must be greater than or equal to verse_from")
        nodes = []
        for verse in range(verse_from, verse_to + 1):
            v_node = _node_from_verse(api, book, chapter, verse)
            nodes.extend(_clause_atoms_in_node(api, v_node))

    node_set: Set[int] = set(nodes)
    mother: Dict[int, Optional[int]] = {}
    children: Dict[int, List[int]] = {}

    for daughter in nodes:
        moms = api.E.mother.f(daughter) or []
        mom = _first_mother(moms)
        if mom not in node_set:
            mom = None
        mother[daughter] = mom
        if mom is not None:
            children.setdefault(mom, []).append(daughter)

    roots = [node for node in nodes if mother[node] is None]
    return ClauseAtomGraph(api=api, nodes=nodes, mother=mother, children=children, roots=roots)


def _first_mother(raw_mothers: object) -> Optional[int]:
    if raw_mothers is None:
        return None
    if isinstance(raw_mothers, int):
        return raw_mothers
    if isinstance(raw_mothers, str):
        return int(raw_mothers) if raw_mothers.isdigit() else None
    if isinstance(raw_mothers, dict):
        for key in raw_mothers:
            if isinstance(key, int):
                return key
        return None
    if isinstance(raw_mothers, Iterable):
        for item in raw_mothers:
            if isinstance(item, int):
                return item
            if isinstance(item, str) and item.isdigit():
                return int(item)
    return None


def compute_depths(g: ClauseAtomGraph, roots: Optional[List[int]] = None) -> Dict[int, int]:
    """Compute depth from each selected root by BFS."""
    start_roots = roots if roots is not None else g.roots
    depth: Dict[int, int] = {}
    queue: deque[tuple[int, int]] = deque((root, 0) for root in start_roots)

    while queue:
        node, current = queue.popleft()
        previous = depth.get(node)
        if previous is not None and previous <= current:
            continue
        depth[node] = current
        for child in g.children.get(node, []):
            queue.append((child, current + 1))
    return depth
