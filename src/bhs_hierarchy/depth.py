from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Set


@dataclass(frozen=True)
class DepthReport:
    """Depth report for a mother forest."""

    depth: Dict[int, int]
    cyclic: Set[int]

    @property
    def depths(self) -> Dict[int, int]:
        return self.depth

    @property
    def cycle_nodes(self) -> Set[int]:
        return self.cyclic


def compute_depths(
    nodes: Iterable[int],
    mother: Mapping[int, Optional[int]],
) -> DepthReport:
    """
    Compute depth in the mother forest.
    - root: mother is None (or self)
    - cycle: depth = -1
    """
    memo: Dict[int, int] = {}
    visiting: Set[int] = set()
    cyclic: Set[int] = set()

    def dfs(node: int) -> int:
        if node in memo:
            return memo[node]
        if node in visiting:
            cyclic.add(node)
            memo[node] = -1
            return -1

        visiting.add(node)
        mom = mother.get(node)

        if mom is None or mom == node or mom not in mother:
            value = 0
        else:
            parent_depth = dfs(mom)
            value = -1 if parent_depth < 0 else parent_depth + 1

        visiting.remove(node)
        memo[node] = value
        return value

    for node in nodes:
        dfs(node)

    cyclic = {node for node, value in memo.items() if value < 0} | cyclic
    return DepthReport(depth=memo, cyclic=cyclic)
