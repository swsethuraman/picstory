"""Analysis output schema (QUEUE.md Stage 1, item 1).

Defines the shape every detector and the CLI conform to: per-frame findings,
each carrying a taxonomy ID or `unclassified` + free-text description
(TAXONOMY.md section U); the pick; one habit. See schema/analysis.json for
the machine-checkable mirror of this shape, kept in sync by
tests/test_schema.py.

`pick` and `habit` are optional on AnalysisOutput because Stage 1 runs one
photo at a time - both need a batch to be meaningful and are populated from
Stage 2 onward (QUEUE.md items 9-10).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

SCHEMA_VERSION = "1.0"
UNCLASSIFIED = "unclassified"

_ROOT = Path(__file__).resolve().parents[2]
_TAXONOMY_MD = _ROOT / "TAXONOMY.md"
_ID_HEADING = re.compile(r"^### ([FSR]\d{2})\b", re.MULTILINE)


class SchemaError(ValueError):
    """Raised when analysis output data does not conform to this schema."""


@lru_cache(maxsize=1)
def taxonomy_ids() -> frozenset[str]:
    """The closed set of valid taxonomy IDs, parsed from the frozen TAXONOMY.md.

    Single source of truth: TAXONOMY.md is frozen (CLAUDE.md), so this reads
    it rather than hardcoding the ID list a second time in Python.
    """
    text = _TAXONOMY_MD.read_text(encoding="utf-8")
    return frozenset(_ID_HEADING.findall(text))


@dataclass
class Finding:
    """One per-frame observation: a taxonomy ID, or `unclassified` + description."""

    taxonomy_id: str
    description: str | None = None

    def __post_init__(self) -> None:
        valid = taxonomy_ids() | {UNCLASSIFIED}
        if self.taxonomy_id not in valid:
            raise SchemaError(
                f"taxonomy_id {self.taxonomy_id!r} is not in the frozen taxonomy "
                f"and is not {UNCLASSIFIED!r}"
            )
        if self.taxonomy_id == UNCLASSIFIED and not (
            self.description and self.description.strip()
        ):
            raise SchemaError(f"{UNCLASSIFIED!r} findings require a non-empty description")

    def to_dict(self) -> dict:
        return {"taxonomy_id": self.taxonomy_id, "description": self.description}

    @classmethod
    def from_dict(cls, data: dict) -> Finding:
        return cls(taxonomy_id=data["taxonomy_id"], description=data.get("description"))


@dataclass
class FrameAnalysis:
    """All findings for one photo."""

    frame_id: str
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"frame_id": self.frame_id, "findings": [f.to_dict() for f in self.findings]}

    @classmethod
    def from_dict(cls, data: dict) -> FrameAnalysis:
        return cls(
            frame_id=data["frame_id"],
            findings=[Finding.from_dict(f) for f in data.get("findings", [])],
        )


@dataclass
class Pick:
    """The shortlist pick: which frame, S-item reasons, F-item disqualifiers weighed."""

    frame_id: str
    reasons: list[str] = field(default_factory=list)
    disqualifiers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        valid = taxonomy_ids()
        for rid in self.reasons:
            if rid not in valid or not rid.startswith("S"):
                raise SchemaError(f"pick reason {rid!r} must be an S-item taxonomy ID")
        for did in self.disqualifiers:
            if did not in valid or not did.startswith("F"):
                raise SchemaError(f"pick disqualifier {did!r} must be an F-item taxonomy ID")

    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "reasons": self.reasons,
            "disqualifiers": self.disqualifiers,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Pick:
        return cls(
            frame_id=data["frame_id"],
            reasons=data.get("reasons", []),
            disqualifiers=data.get("disqualifiers", []),
        )


@dataclass
class Habit:
    """The one habit surfaced this session: the most-recurrent F/S item, by ID."""

    taxonomy_id: str
    description: str

    def __post_init__(self) -> None:
        valid = taxonomy_ids()
        if self.taxonomy_id not in valid or self.taxonomy_id.startswith("R"):
            raise SchemaError(f"habit taxonomy_id {self.taxonomy_id!r} must be an F- or S-item ID")
        if not self.description or not self.description.strip():
            raise SchemaError("habit requires a non-empty description")

    def to_dict(self) -> dict:
        return {"taxonomy_id": self.taxonomy_id, "description": self.description}

    @classmethod
    def from_dict(cls, data: dict) -> Habit:
        return cls(taxonomy_id=data["taxonomy_id"], description=data["description"])


@dataclass
class AnalysisOutput:
    """Top-level output of an analysis run: version, frames, pick, habit."""

    schema_version: str = SCHEMA_VERSION
    frames: list[FrameAnalysis] = field(default_factory=list)
    pick: Pick | None = None
    habit: Habit | None = None

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise SchemaError(
                f"schema_version {self.schema_version!r} does not match current {SCHEMA_VERSION!r}"
            )
        frame_ids = {f.frame_id for f in self.frames}
        if self.pick is not None and self.pick.frame_id not in frame_ids:
            raise SchemaError(f"pick.frame_id {self.pick.frame_id!r} is not among analyzed frames")

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "frames": [f.to_dict() for f in self.frames],
            "pick": self.pick.to_dict() if self.pick is not None else None,
            "habit": self.habit.to_dict() if self.habit is not None else None,
        }

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), indent=2, **kwargs)

    @classmethod
    def from_dict(cls, data: dict) -> AnalysisOutput:
        return cls(
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            frames=[FrameAnalysis.from_dict(f) for f in data.get("frames", [])],
            pick=Pick.from_dict(data["pick"]) if data.get("pick") else None,
            habit=Habit.from_dict(data["habit"]) if data.get("habit") else None,
        )

    @classmethod
    def from_json(cls, text: str) -> AnalysisOutput:
        return cls.from_dict(json.loads(text))
