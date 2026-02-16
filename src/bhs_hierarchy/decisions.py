from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

import yaml

from .graph import validate_selection_scope


@dataclass(frozen=True)
class Scope:
    book: str
    chapter: Optional[int] = None
    verse_from: Optional[int] = None
    verse_to: Optional[int] = None

    def __post_init__(self) -> None:
        validate_selection_scope(
            book=self.book,
            chapter=self.chapter,
            verse_from=self.verse_from,
            verse_to=self.verse_to,
        )

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"book": self.book}
        if self.chapter is not None:
            data["chapter"] = int(self.chapter)
        if self.verse_from is not None:
            data["verse_from"] = int(self.verse_from)
        if self.verse_to is not None:
            data["verse_to"] = int(self.verse_to)
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Scope":
        return Scope(
            book=str(data.get("book")),
            chapter=(int(data["chapter"]) if data.get("chapter") is not None else None),
            verse_from=(int(data["verse_from"]) if data.get("verse_from") is not None else None),
            verse_to=(int(data["verse_to"]) if data.get("verse_to") is not None else None),
        )


@dataclass
class Decisions:
    scope: Scope
    roots: List[int] = field(default_factory=list)
    overrides: Dict[int, Optional[int]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": self.scope.to_dict(),
            "roots": [int(item) for item in self.roots],
            "overrides": {
                str(int(node)): (None if mom is None else int(mom))
                for node, mom in self.overrides.items()
            },
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Decisions":
        scope = Scope.from_dict(data.get("scope") or {})
        roots = [int(item) for item in (data.get("roots") or [])]
        overrides_raw = data.get("overrides") or {}
        overrides: Dict[int, Optional[int]] = {}
        for node, mom in overrides_raw.items():
            key = int(node)
            overrides[key] = None if mom is None else int(mom)
        return Decisions(scope=scope, roots=roots, overrides=overrides)

    @staticmethod
    def load(path: Path) -> "Decisions":
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(text) or {}
        else:
            data = json.loads(text)
        return Decisions.from_dict(data)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() in {".yaml", ".yml"}:
            path.write_text(
                yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            return

        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
