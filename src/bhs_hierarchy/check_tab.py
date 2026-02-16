from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .tf_loader import BhsaApi


def mother_global(api: BhsaApi, node: int) -> Optional[int]:
    moms = api.E.mother.f(node) or []
    if not moms:
        return None

    mom = _first_mother(moms)
    if mom == node:
        return None

    code_feature = getattr(api.F, "code", None)
    dist_feature = getattr(api.F, "dist", None)
    code = code_feature.v(node) if code_feature is not None else None
    dist = dist_feature.v(node) if dist_feature is not None else None
    if code == 0 and dist == 0:
        return None

    return mom


def compute_depth_global(api: BhsaApi, node: int, memo: Dict[int, int]) -> int:
    if node in memo:
        return memo[node]

    seen = set()
    current = node
    depth = 0
    while True:
        if current in memo:
            depth += memo[current]
            break
        if current in seen:
            memo[node] = -1
            return -1
        seen.add(current)

        mom = mother_global(api, current)
        if mom is None:
            break
        depth += 1
        current = mom

    memo[node] = depth
    return depth


def tab_agreement(api: BhsaApi, nodes: List[int]) -> Tuple[int, int, int, List[Tuple[int, int, int]]]:
    """
    Returns:
      (total, matched, mismatched, samples[mismatch tuples])
      mismatch tuple = (node, tab, depth)
    """
    memo: Dict[int, int] = {}
    mismatches: List[Tuple[int, int, int]] = []
    matched = 0

    for node in nodes:
        tab = api.F.tab.v(node)
        if tab is None:
            continue
        depth = compute_depth_global(api, node, memo)
        if depth == tab:
            matched += 1
        else:
            mismatches.append((node, tab, depth))

    total = matched + len(mismatches)
    return total, matched, len(mismatches), mismatches[:30]


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
    if isinstance(raw_mothers, (tuple, list, set)):
        for item in raw_mothers:
            if isinstance(item, int):
                return item
            if isinstance(item, str) and item.isdigit():
                return int(item)
    return None
