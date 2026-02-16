from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from tf.app import use


@dataclass(frozen=True)
class BhsaApi:
    """Light wrapper around TF API handles used by this project."""

    A: Any
    F: Any
    E: Any
    T: Any
    L: Any
    N: Any


@lru_cache(maxsize=4)
def load_bhsa(version: str = "2021", silent: bool = True) -> BhsaApi:
    """Load BHSA dataset through Text-Fabric."""
    A = use("ETCBC/bhsa", version=version, silent=silent)
    api = A.api
    return BhsaApi(A=A, F=api.F, E=api.E, T=api.T, L=api.L, N=api.N)
