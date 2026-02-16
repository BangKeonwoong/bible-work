from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .depth import compute_depths
from .graph import ClauseAtomGraph


def _abbr_book(book: str) -> str:
    return book[:4].upper().ljust(4)


def verse_label(graph: ClauseAtomGraph, node: int) -> str:
    section = graph.api.T.sectionFromNode(node)
    if not section or len(section) < 3:
        return "???? ??,??"
    book, chapter, verse = section[:3]
    return f"{_abbr_book(str(book))} {int(chapter):02d},{int(verse):02d}"


def pgn_predicate(graph: ClauseAtomGraph, clause_atom: int) -> str:
    for word in graph.api.L.d(clause_atom, otype="word"):
        if graph.api.F.sp.v(word) != "verb":
            continue
        ps = graph.api.F.ps.v(word)
        nu = graph.api.F.nu.v(word)
        gn = graph.api.F.gn.v(word)
        if ps and nu and gn:
            person = str(ps)[-1]
            number = {"sg": "s", "pl": "p", "du": "d"}.get(str(nu), str(nu)[:1])
            return f"{person}{gn}{number}"
        text = f"{ps or ''}{gn or ''}{nu or ''}"
        return text[:6]
    return ""


def mother_indicator(
    graph: ClauseAtomGraph,
    node: int,
    mother: Dict[int, Optional[int]],
) -> str:
    if mother.get(node) is None:
        return "[R]"
    code = graph.api.F.code.v(node)
    if code == 999:
        return "[Q]"
    mom = mother.get(node)
    if mom is None:
        return "[R]"
    return graph.api.F.typ.v(mom) or "?"


def text_type(graph: ClauseAtomGraph, node: int) -> str:
    return graph.api.F.txt.v(node) or ""


def pargr(graph: ClauseAtomGraph, node: int) -> str:
    value = graph.api.F.pargr.v(node)
    return str(value) if value is not None else ""


def number(graph: ClauseAtomGraph, node: int) -> str:
    value = graph.api.F.number.v(node)
    return str(value) if value is not None else ""


@dataclass(frozen=True)
class CttLikeWidths:
    verse: int = 11
    pgn: int = 6
    typ: int = 6
    mother: int = 7
    txt: int = 5
    pargr: int = 10
    num: int = 8
    tab: int = 8


def make_ctt_like_lines(
    graph: ClauseAtomGraph,
    *,
    only_subtree_from_roots: Optional[List[int]] = None,
    widths: CttLikeWidths = CttLikeWidths(),
) -> List[str]:
    report = compute_depths(graph.nodes, graph.mother)
    depth = report.depth
    mother = graph.mother

    allowed: Optional[Set[int]] = None
    if only_subtree_from_roots:
        allowed = set()
        stack = list(only_subtree_from_roots)
        while stack:
            node = stack.pop()
            if node in allowed:
                continue
            allowed.add(node)
            stack.extend(graph.children.get(node, []))

    lines: List[str] = []
    header = (
        f"{'VERSE'.ljust(widths.verse)}"
        f"{'PGN'.ljust(widths.pgn)}"
        f"{'TYP'.ljust(widths.typ)}"
        f"{'MOTHER'.ljust(widths.mother)}"
        f"{'TXT'.ljust(widths.txt)}"
        f"{'PARGR'.ljust(widths.pargr)}"
        f"{'NUM'.ljust(widths.num)}"
        f"{'TAB'.ljust(widths.tab)}"
        "HIERARCHY"
    )
    lines.append(header)

    for node in graph.nodes:
        if allowed is not None and node not in allowed:
            continue

        value = depth.get(node, 0)
        tab_str = "!!" if value < 0 else str(value)
        row = (
            f"{verse_label(graph, node).ljust(widths.verse)}"
            f"{pgn_predicate(graph, node).ljust(widths.pgn)}"
            f"{(graph.typ(node) or '').ljust(widths.typ)}"
            f"{mother_indicator(graph, node, mother).ljust(widths.mother)}"
            f"{text_type(graph, node).ljust(widths.txt)}"
            f"{pargr(graph, node).ljust(widths.pargr)}"
            f"{number(graph, node).ljust(widths.num)}"
            f"{tab_str.ljust(widths.tab)}"
        )

        indent = "" if value < 0 else ("  " * value)
        body = indent + graph.text(node, max_len=240)
        lines.append(row + body)

    return lines


def ctt_lines(
    graph: ClauseAtomGraph,
    *,
    subtree_roots: Optional[List[int]] = None,
) -> List[str]:
    return make_ctt_like_lines(graph, only_subtree_from_roots=subtree_roots)
