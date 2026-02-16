#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bhs_hierarchy.graph import build_graph_for_selection, compute_depths, validate_selection_scope
from bhs_hierarchy.tf_loader import load_bhsa


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare depth computed from mother edges with BHSA tab values."
    )
    parser.add_argument("--book", required=True, help="Book name, for example Genesis")
    parser.add_argument("--chapter", type=int, default=None, help="Chapter number")
    parser.add_argument("--verse-from", type=int, default=None, help="Start verse")
    parser.add_argument("--verse-to", type=int, default=None, help="End verse")
    parser.add_argument("--version", default="2021", help="BHSA dataset version")
    parser.add_argument(
        "--max-mismatches",
        type=int,
        default=20,
        help="Maximum mismatch rows to print",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_selection_scope(
        book=args.book,
        chapter=args.chapter,
        verse_from=args.verse_from,
        verse_to=args.verse_to,
    )
    api = load_bhsa(version=args.version, silent=True)
    graph = build_graph_for_selection(
        api,
        book=args.book,
        chapter=args.chapter,
        verse_from=args.verse_from,
        verse_to=args.verse_to,
    )
    depths = compute_depths(graph)

    total = len(graph.nodes)
    comparable = 0
    matched = 0
    mismatches: list[tuple[int, int, int]] = []

    for node in graph.nodes:
        tab = graph.tab(node)
        depth = depths.get(node)
        if tab is None or depth is None:
            continue
        comparable += 1
        if tab == depth:
            matched += 1
        else:
            mismatches.append((node, depth, tab))

    print(f"selection_nodes={total}")
    print(f"comparable_nodes={comparable}")
    print(f"matched_nodes={matched}")
    if comparable > 0:
        pct = (matched / comparable) * 100
        print(f"match_rate={pct:.2f}%")
    else:
        print("match_rate=n/a")

    if mismatches:
        print("\nTop mismatches:")
        for node, depth, tab in mismatches[: args.max_mismatches]:
            print(f"node={node}\tdepth={depth}\ttab={tab}\tsection={graph.section_label(node)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
