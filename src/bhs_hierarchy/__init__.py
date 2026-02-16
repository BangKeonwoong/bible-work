"""BHSA clause_atom hierarchy tooling."""

from .check_tab import compute_depth_global, mother_global, tab_agreement
from .ctt import CttLikeWidths, ctt_lines, make_ctt_like_lines
from .decisions import Decisions, Scope
from .depth import DepthReport, compute_depths
from .graph import (
    ClauseAtomGraph,
    build_graph_for_selection,
    validate_selection_scope,
)
from .tf_loader import BhsaApi, load_bhsa
from .viz import RenderOptions, graphviz_available, render, to_dot

__all__ = [
    "BhsaApi",
    "ClauseAtomGraph",
    "CttLikeWidths",
    "Decisions",
    "DepthReport",
    "RenderOptions",
    "Scope",
    "build_graph_for_selection",
    "compute_depth_global",
    "compute_depths",
    "ctt_lines",
    "graphviz_available",
    "load_bhsa",
    "make_ctt_like_lines",
    "mother_global",
    "render",
    "tab_agreement",
    "to_dot",
    "validate_selection_scope",
]
