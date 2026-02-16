#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bhs_hierarchy.check_tab import tab_agreement
from bhs_hierarchy.graph import build_graph_for_selection, validate_selection_scope
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
    total, matched, mismatched, samples = tab_agreement(api, graph.nodes)

    print(f"total={total}")
    print(f"matched={matched}")
    print(f"mismatched={mismatched}")

    if samples:
        print("\nTop mismatches:")
        for node, tab, depth in samples[: args.max_mismatches]:
            print(f"node={node}\ttab={tab}\tdepth={depth}\tsection={graph.section_label(node)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
