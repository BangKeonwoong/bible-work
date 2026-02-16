from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich import print

from .check_tab import tab_agreement
from .ctt import make_ctt_like_lines
from .decisions import Decisions, Scope
from .graph import build_graph_for_selection
from .tf_loader import load_bhsa
from .viz import RenderOptions, render

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


def _scope_from_args(
    *,
    book: Optional[str],
    chapter: Optional[int],
    verse_from: Optional[int],
    verse_to: Optional[int],
    decisions: Optional[Decisions],
) -> Scope:
    if decisions is not None:
        if any(value is not None for value in [book, chapter, verse_from, verse_to]):
            print("[yellow]Ignoring explicit scope options because decisions file has scope.[/yellow]")
        return decisions.scope

    if book is None:
        raise ValueError("book is required unless --decisions is provided")
    return Scope(book=book, chapter=chapter, verse_from=verse_from, verse_to=verse_to)


@app.command()
def roots(
    book: str = typer.Option(..., help="Book name, for example Genesis"),
    chapter: Optional[int] = typer.Option(None, help="Chapter number"),
    verse_from: Optional[int] = typer.Option(None, help="Start verse (inclusive)"),
    verse_to: Optional[int] = typer.Option(None, help="End verse (inclusive)"),
    version: str = typer.Option("2021", help="BHSA dataset version"),
) -> None:
    """List root clause_atom candidates within a selection."""
    try:
        api = load_bhsa(version=version, silent=True)
        graph = build_graph_for_selection(
            api,
            book=book,
            chapter=chapter,
            verse_from=verse_from,
            verse_to=verse_to,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    if not graph.roots:
        print("[red]No roots found in this selection.[/red]")
        raise typer.Exit(code=1)

    print(f"[bold]Roots inside selection:[/bold] {len(graph.roots)}")
    for idx, root in enumerate(graph.roots[:50]):
        print(
            f"[cyan][{idx}][/cyan] node={root} {graph.section_label(root)}"
            f" {graph.typ(root)}  {graph.text(root)}"
        )
    if len(graph.roots) > 50:
        print(f"[yellow]... ({len(graph.roots) - 50} more roots omitted)[/yellow]")


@app.command()
def draw(
    book: Optional[str] = typer.Option(None, help="Book name, for example Genesis"),
    chapter: Optional[int] = typer.Option(None, help="Chapter number"),
    verse_from: Optional[int] = typer.Option(None, help="Start verse (inclusive)"),
    verse_to: Optional[int] = typer.Option(None, help="End verse (inclusive)"),
    root_index: Optional[int] = typer.Option(None, help="Index from root candidates"),
    decisions: Optional[Path] = typer.Option(None, help="Decisions file (.yaml/.yml/.json)"),
    out: Path = typer.Option(Path("out/tree.svg"), help="Output path"),
    fmt: str = typer.Option("svg", help="svg|png|pdf|dot"),
    version: str = typer.Option("2021", help="BHSA dataset version"),
) -> None:
    """Render one root subtree as SVG/PNG/PDF/DOT."""
    try:
        dec = Decisions.load(decisions) if decisions else None
        scope = _scope_from_args(
            book=book,
            chapter=chapter,
            verse_from=verse_from,
            verse_to=verse_to,
            decisions=dec,
        )
        api = load_bhsa(version=version, silent=True)
        graph = build_graph_for_selection(
            api,
            book=scope.book,
            chapter=scope.chapter,
            verse_from=scope.verse_from,
            verse_to=scope.verse_to,
            overrides=(dec.overrides if dec else None),
        )
    except (RuntimeError, ValueError) as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    node_set = set(graph.nodes)
    root_candidates = dec.roots if (dec and dec.roots) else graph.roots
    root_candidates = [node for node in root_candidates if node in node_set]
    if not root_candidates:
        print("[red]No roots found.[/red]")
        raise typer.Exit(code=1)

    if root_index is None:
        if dec and dec.roots:
            root_index = 0
            print("[yellow]No root_index provided; using first decisions root.[/yellow]")
        else:
            print("[bold]Pick a root:[/bold]")
            for idx, root in enumerate(root_candidates[:30]):
                print(
                    f"[cyan][{idx}][/cyan] node={root} {graph.section_label(root)}"
                    f" {graph.typ(root)}  {graph.text(root)}"
                )
            root_index = typer.prompt("root_index", type=int)

    if root_index < 0 or root_index >= len(root_candidates):
        print("[red]Invalid root_index.[/red]")
        raise typer.Exit(code=1)

    root = root_candidates[root_index]
    try:
        rendered = render(
            graph,
            roots=[root],
            out_path=out,
            fmt=fmt,
            opts=RenderOptions(show_code=True, show_tab=False),
        )
    except (RuntimeError, ValueError) as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    print(f"[green]Rendered:[/green] {rendered}")


@app.command("check-tab")
def check_tab(
    book: str = typer.Option(...),
    chapter: Optional[int] = typer.Option(None),
    verse_from: Optional[int] = typer.Option(None),
    verse_to: Optional[int] = typer.Option(None),
    version: str = typer.Option("2021"),
) -> None:
    try:
        api = load_bhsa(version=version, silent=True)
        graph = build_graph_for_selection(
            api,
            book=book,
            chapter=chapter,
            verse_from=verse_from,
            verse_to=verse_to,
        )
        total, matched, mismatched, samples = tab_agreement(api, graph.nodes)
    except (RuntimeError, ValueError) as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    print(f"[bold]tab agreement[/bold] total={total} matched={matched} mismatched={mismatched}")
    if samples:
        print("[bold]mismatch samples (node, tab, depth):[/bold]")
        for node, tab, depth in samples:
            print(f"- {node} tab={tab} depth={depth}  {graph.section_label(node)} {graph.typ(node)}  {graph.text(node)}")


@app.command("init-decisions")
def init_decisions(
    book: str = typer.Option(...),
    chapter: Optional[int] = typer.Option(None),
    verse_from: Optional[int] = typer.Option(None),
    verse_to: Optional[int] = typer.Option(None),
    out: Path = typer.Option(Path("decisions/selection.yaml")),
    root_index: list[int] = typer.Option([], "--root-index"),
    version: str = typer.Option("2021"),
) -> None:
    try:
        api = load_bhsa(version=version, silent=True)
        graph = build_graph_for_selection(
            api,
            book=book,
            chapter=chapter,
            verse_from=verse_from,
            verse_to=verse_to,
        )
        selected_roots = []
        for idx in root_index:
            if 0 <= idx < len(graph.roots):
                selected_roots.append(graph.roots[idx])
        dec = Decisions(
            scope=Scope(book=book, chapter=chapter, verse_from=verse_from, verse_to=verse_to),
            roots=selected_roots,
            overrides={},
        )
        dec.save(out)
    except (RuntimeError, ValueError) as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    print(f"[green]Wrote decisions:[/green] {out}")


@app.command()
def ctt(
    book: Optional[str] = typer.Option(None),
    chapter: Optional[int] = typer.Option(None),
    verse_from: Optional[int] = typer.Option(None),
    verse_to: Optional[int] = typer.Option(None),
    decisions: Optional[Path] = typer.Option(None),
    out: Path = typer.Option(Path("out/selection.ctt.txt")),
    subtree: bool = typer.Option(False, help="Output only subtree from selected roots"),
    version: str = typer.Option("2021"),
) -> None:
    try:
        dec = Decisions.load(decisions) if decisions else None
        scope = _scope_from_args(
            book=book,
            chapter=chapter,
            verse_from=verse_from,
            verse_to=verse_to,
            decisions=dec,
        )
        api = load_bhsa(version=version, silent=True)
        graph = build_graph_for_selection(
            api,
            book=scope.book,
            chapter=scope.chapter,
            verse_from=scope.verse_from,
            verse_to=scope.verse_to,
            overrides=(dec.overrides if dec else None),
        )
        node_set = set(graph.nodes)
        roots = dec.roots if (dec and dec.roots) else graph.roots
        roots = [node for node in roots if node in node_set]
        subtree_roots = roots if subtree else None
        lines = make_ctt_like_lines(graph, only_subtree_from_roots=subtree_roots)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except (RuntimeError, ValueError) as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    print(f"[green]Wrote CTT-like:[/green] {out}")


if __name__ == "__main__":
    app()
