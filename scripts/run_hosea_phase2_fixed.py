#!/usr/bin/env python3
"""Run the Phase 2 analyzer with the BHSA mother edge correctly exposed.

The initial analyzer treated ``mother`` as a node feature. In BHSA it is an
edge feature, so this wrapper replaces only that lookup and then validates that
the resulting baseline is a genuine hierarchy rather than 836 artificial roots.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).with_name("analyze_hosea_x_fronting.py")
spec = importlib.util.spec_from_file_location("hosea_phase2_base", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {SCRIPT}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
base_fs = module.fs


def edge_aware_fs(api: Any, name: str, node: int, default: Any = "") -> Any:
    if name != "mother":
        return base_fs(api, name, node, default)
    raw = api.E.mother.f(node) or []
    if isinstance(raw, (int, str)):
        raw = [raw]
    mother = 0
    for value in raw:
        mother = module.inode(value)
        if mother:
            break
    code = base_fs(api, "code", node, None)
    dist = base_fs(api, "dist", node, None)
    if mother == node or (code == 0 and dist == 0):
        return 0
    return mother


module.fs = edge_aware_fs
module.main()

out_dir = Path("out/hosea-x")
if "--out-dir" in sys.argv:
    out_dir = Path(sys.argv[sys.argv.index("--out-dir") + 1])
validation = json.loads((out_dir / "validation.json").read_text(encoding="utf-8"))
roots = int(validation["baseline_root_count"])
if not 1 < roots < 200:
    raise RuntimeError(f"Invalid BHSA mother extraction: baseline_root_count={roots}")
print(f"Validated edge-based BHSA hierarchy: {roots} baseline roots")
