from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Sequence

from graphviz import Digraph
from graphviz.backend import ExecutableNotFound

from .graph import ClauseAtomGraph


@dataclass(frozen=True)
class RenderOptions:
    rankdir: str = "TB"
    max_label_len: int = 70
    show_code: bool = True
    show_tab: bool = False
    fontname: str = "Noto Sans Hebrew"


def graphviz_available() -> bool:
    return shutil.which("dot") is not None


def to_dot(
    g: ClauseAtomGraph,
    *,
    roots: Sequence[int],
    opts: RenderOptions = RenderOptions(),
) -> Digraph:
    dot = Digraph("clause_atom_tree", encoding="utf-8")
    dot.attr(rankdir=opts.rankdir)
    dot.attr("node", shape="box", fontsize="10", fontname=opts.fontname)

    stack = list(roots)
    seen: set[int] = set()

    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)

        pieces = [g.section_label(node), g.typ(node), g.text(node, max_len=opts.max_label_len)]
        if opts.show_tab:
            pieces.insert(2, f"tab={g.tab(node)}")
        label = "\\n".join(pieces)

        if node in roots:
            dot.node(str(node), label=label, peripheries="2")
        else:
            dot.node(str(node), label=label)

        for child in g.children.get(node, []):
            stack.append(child)
            edge_label = ""
            if opts.show_code:
                code = g.code(child)
                if code is not None:
                    edge_label = f"code={code}"
            dot.edge(str(node), str(child), label=edge_label)

    return dot


def render(
    g: ClauseAtomGraph,
    *,
    roots: Sequence[int],
    out_path: Path,
    fmt: str = "svg",
    opts: RenderOptions = RenderOptions(),
) -> Path:
    fmt = fmt.lower()
    if fmt not in {"svg", "png", "pdf", "dot"}:
        raise ValueError("fmt must be one of: svg, png, pdf, dot")

    dot = to_dot(g, roots=roots, opts=opts)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "dot":
        dot_path = out_path.with_suffix(".dot")
        dot_path.write_text(dot.source, encoding="utf-8")
        return dot_path

    if not graphviz_available():
        raise RuntimeError(
            "Graphviz `dot` executable not found. Install Graphviz and ensure `dot` is on PATH."
        )

    stem = out_path.with_suffix("")
    try:
        rendered = dot.render(str(stem), format=fmt, cleanup=True)
    except ExecutableNotFound as exc:
        raise RuntimeError(
            "Graphviz `dot` executable not found. Install Graphviz and ensure `dot` is on PATH."
        ) from exc
    return Path(rendered)
