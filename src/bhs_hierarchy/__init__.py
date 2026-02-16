"""BHSA clause_atom hierarchy tooling."""

from .graph import (
    ClauseAtomGraph,
    build_graph_for_selection,
    compute_depths,
    validate_selection_scope,
)
from .tf_loader import BhsaApi, load_bhsa
from .viz import RenderOptions, graphviz_available, render, to_dot

__all__ = [
    "BhsaApi",
    "ClauseAtomGraph",
    "RenderOptions",
    "build_graph_for_selection",
    "compute_depths",
    "graphviz_available",
    "load_bhsa",
    "render",
    "to_dot",
    "validate_selection_scope",
]
