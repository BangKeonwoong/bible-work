from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich import print

from .graph import build_graph_for_selection
from .tf_loader import load_bhsa
from .viz import RenderOptions, render

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


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
    book: str = typer.Option(..., help="Book name, for example Genesis"),
    chapter: Optional[int] = typer.Option(None, help="Chapter number"),
    verse_from: Optional[int] = typer.Option(None, help="Start verse (inclusive)"),
    verse_to: Optional[int] = typer.Option(None, help="End verse (inclusive)"),
    root_index: Optional[int] = typer.Option(None, help="Index from the roots command"),
    out: Path = typer.Option(Path("out/tree.svg"), help="Output path"),
    fmt: str = typer.Option("svg", help="svg|png|pdf"),
    version: str = typer.Option("2021", help="BHSA dataset version"),
) -> None:
    """Render one root subtree as SVG/PNG/PDF."""
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
        print("[red]No roots found.[/red]")
        raise typer.Exit(code=1)

    if root_index is None:
        print("[bold]Pick a root:[/bold]")
        for idx, root in enumerate(graph.roots[:30]):
            print(
                f"[cyan][{idx}][/cyan] node={root} {graph.section_label(root)}"
                f" {graph.typ(root)}  {graph.text(root)}"
            )
        root_index = typer.prompt("root_index", type=int)

    if root_index < 0 or root_index >= len(graph.roots):
        print("[red]Invalid root_index.[/red]")
        raise typer.Exit(code=1)

    root = graph.roots[root_index]
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


if __name__ == "__main__":
    app()
