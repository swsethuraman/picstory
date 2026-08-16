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
_DETECTION_LINE = re.compile(
    r"^### (?P<id>[FSR]\d{2}) ·.*\n(?:^-.*\n)*?^- \*\*Detection:\*\* (?P<text>.+)$",
    re.MULTILINE,
)
_REINFORCEMENT_LINE = re.compile(
    r"^### (?P<id>[FSR]\d{2}) ·.*\n(?:^-.*\n)*?^- \*\*Reinforcement:\*\* (?P<text>.+)$",
    re.MULTILINE,
)
_CORRECTION_LINE = re.compile(
    r"^### (?P<id>[FSR]\d{2}) ·.*\n(?:^-.*\n)*?^- \*\*Correction:\*\* (?P<text>.+)$",
    re.MULTILINE,
)
_RULE_LINE = re.compile(
    r"^### (?P<id>[FSR]\d{2}) ·.*\n(?:^-.*\n)*?^- \*\*Rule:\*\* (?P<text>.+)$",
    re.MULTILINE,
)
_CMP_SECTION = re.compile(
    r"^## CMP — The three-frame comparison rubric\n\n(?P<text>.*?)\n\n---\n",
    re.MULTILINE | re.DOTALL,
)
_PROFILE_NOTE_LINE = re.compile(
    r"^### (?P<id>[FSR]\d{2}) ·.*\n(?:^-.*\n)*?^- \*\*Profile note:\*\* (?P<text>.+)$",
    re.MULTILINE,
)
_FIXABILITY_LINE = re.compile(
    r"^### (?P<id>[FSR]\d{2}) ·.*\n(?:^-.*\n)*?^- \*\*Fixability:\*\* (?P<text>.+)$",
    re.MULTILINE,
)


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


@lru_cache(maxsize=1)
def _detection_texts() -> dict[str, str]:
    text = _TAXONOMY_MD.read_text(encoding="utf-8")
    return {m.group("id"): m.group("text").strip() for m in _DETECTION_LINE.finditer(text)}


def taxonomy_detection_text(taxonomy_id: str) -> str:
    """The exact Detection text for one taxonomy ID, parsed verbatim from TAXONOMY.md.

    Single source of truth (same reasoning as `taxonomy_ids()`): a
    judgment-dependent detector's prompt must embed the item's Detection text
    verbatim (CLAUDE.md's API-discipline rule). Reading it here rather than
    copy-pasting it into each detector module makes verbatim drift structurally
    impossible rather than merely tested for. R01 and CMP have no Detection
    bullet and are not valid inputs.
    """
    try:
        return _detection_texts()[taxonomy_id]
    except KeyError:
        raise SchemaError(f"no Detection text found for taxonomy_id {taxonomy_id!r}") from None


@lru_cache(maxsize=1)
def _reinforcement_texts() -> dict[str, str]:
    text = _TAXONOMY_MD.read_text(encoding="utf-8")
    return {m.group("id"): m.group("text").strip() for m in _REINFORCEMENT_LINE.finditer(text)}


def taxonomy_reinforcement_text(taxonomy_id: str) -> str:
    """The exact Reinforcement text for one S-item, parsed verbatim from TAXONOMY.md.

    Same verbatim-source-of-truth reasoning as `taxonomy_detection_text`
    (QUEUE.md item 9 needs share-list one-liners "drawn from S-item
    vocabulary" - TAXONOMY.md's own output-mapping table names S-items as
    the "why it's share-worthy" one-liners). Reading the Reinforcement bullet
    here rather than paraphrasing it into the ranking module makes drift
    structurally impossible, the same way `taxonomy_detection_text` does for
    detector prompts. Only S-items carry a Reinforcement bullet; F/R items
    raise.
    """
    try:
        return _reinforcement_texts()[taxonomy_id]
    except KeyError:
        raise SchemaError(f"no Reinforcement text found for taxonomy_id {taxonomy_id!r}") from None


@lru_cache(maxsize=1)
def _correction_texts() -> dict[str, str]:
    text = _TAXONOMY_MD.read_text(encoding="utf-8")
    return {m.group("id"): m.group("text").strip() for m in _CORRECTION_LINE.finditer(text)}


def taxonomy_correction_text(taxonomy_id: str) -> str:
    """The exact Correction text for one F-item, parsed verbatim from TAXONOMY.md.

    Same verbatim-source-of-truth reasoning as `taxonomy_reinforcement_text`:
    the habit (QUEUE.md item 10) is "drawn from TAXONOMY.md by ID"
    (PREDICTION.md) and the output-mapping table's "reinforcement counts as
    coaching" line implies the symmetric read for F-items - Correction is
    their coaching text, the same role Reinforcement plays for S-items. Only
    F-items carry a Correction bullet; S/R items raise.
    """
    try:
        return _correction_texts()[taxonomy_id]
    except KeyError:
        raise SchemaError(f"no Correction text found for taxonomy_id {taxonomy_id!r}") from None


@lru_cache(maxsize=1)
def _rule_texts() -> dict[str, str]:
    text = _TAXONOMY_MD.read_text(encoding="utf-8")
    return {m.group("id"): m.group("text").strip() for m in _RULE_LINE.finditer(text)}


def taxonomy_rule_text(taxonomy_id: str) -> str:
    """The exact Rule text for one R-item, parsed verbatim from TAXONOMY.md.

    Same verbatim-source-of-truth reasoning as `taxonomy_correction_text`/
    `taxonomy_reinforcement_text`. Only R-items carry a `- **Rule:**`
    bullet (TAXONOMY.md §R: "Rules are triggered by shooting conditions,
    not detected in frames ... they generate forward-looking advice");
    F/S items raise.
    """
    try:
        return _rule_texts()[taxonomy_id]
    except KeyError:
        raise SchemaError(f"no Rule text found for taxonomy_id {taxonomy_id!r}") from None


@lru_cache(maxsize=1)
def cmp_rubric_text() -> str:
    """TAXONOMY.md's CMP section, verbatim, in full.

    Same single-source-of-truth reasoning as `taxonomy_detection_text`: QUEUE.md
    item 11 implements "the three axes + story tiebreaker, exactly as
    TAXONOMY.md §CMP," and CLAUDE.md's API-discipline rule requires a
    model-call detector's prompt to embed the item's own text verbatim. CMP has
    no `- **Detection:**` bullet the way F/S items do (it is a rubric, not a
    single-condition check), so the whole section - the three named axes, the
    story tiebreaker, and the "what the output names" closing line - stands in
    for that role; there is no narrower "the detection text" to extract
    instead.
    """
    text = _TAXONOMY_MD.read_text(encoding="utf-8")
    match = _CMP_SECTION.search(text)
    if match is None:
        raise SchemaError("no CMP rubric section found in TAXONOMY.md")
    return match.group("text").strip()


@lru_cache(maxsize=1)
def _fixability_texts() -> dict[str, str]:
    text = _TAXONOMY_MD.read_text(encoding="utf-8")
    return {m.group("id"): m.group("text").strip() for m in _FIXABILITY_LINE.finditer(text)}


def taxonomy_fixability(taxonomy_id: str) -> str:
    """The exact Fixability text for one F-item, parsed verbatim from TAXONOMY.md v1.2.

    Same verbatim-source-of-truth reasoning as `taxonomy_correction_text`
    (QUEUE.md item 18a, DECISIONS.md D-009). Only F-items carry a Fixability
    bullet - v1.2's changelog is explicit that "S-items, R-items and CMP
    intentionally carry no Fixability - strengths need no fix, rules and the
    rubric are not per-frame findings"; S/R items raise.
    """
    try:
        return _fixability_texts()[taxonomy_id]
    except KeyError:
        raise SchemaError(f"no Fixability text found for taxonomy_id {taxonomy_id!r}") from None


_FIXABILITY_CATEGORY = re.compile(r"^(post-fixable|capture-only|conditional)\b")


def taxonomy_fixability_category(taxonomy_id: str) -> str:
    """The Fixability bullet's leading category: post-fixable / capture-only / conditional.

    Every F-item's v1.2 Fixability text opens with exactly one of these three
    words (optionally followed by a parenthetical naming the edit technique,
    e.g. "post-fixable (crop)") before the em-dash explanation. Parsed out of
    `taxonomy_fixability`'s own text rather than a second literal copy, so
    drift between the category and the full text is structurally impossible.
    """
    text = taxonomy_fixability(taxonomy_id)
    match = _FIXABILITY_CATEGORY.match(text)
    if match is None:
        raise SchemaError(
            f"Fixability text for {taxonomy_id!r} does not start with a recognized "
            f"category (post-fixable/capture-only/conditional): {text!r}"
        )
    return match.group(1)


@lru_cache(maxsize=1)
def taxonomy_ids_with_subpattern() -> frozenset[str]:
    """IDs TAXONOMY.md documents as carrying a closed-vocabulary sub-pattern field.

    Two distinct sources, both parsed rather than hardcoded (same reasoning
    as every other `taxonomy_*_text` helper): a `- **Profile note:**` bullet
    (the profile-layer case - F06's "which edge," TAXONOMY.md's output-
    mapping table: "The running profile | Per-user recurrence of F/S items
    and their sub-patterns"), and a `- **Fixability:**` bullet whose category
    is `conditional` (the fixability-layer case v1.2/D-009 added - F05's
    `bowing`/`off_center_drift` decides which of post-fixable/capture-only
    actually applies to a given finding). Both share the same
    `Finding.sub_pattern` field and the same enum-constrained `SubPatternSpec`
    call mechanism (`_vision.py`) - a sub-pattern is closed-vocabulary detail
    the model names alongside its verdict, regardless of which downstream
    consumer (the profile store, or fixability resolution) reads it. Today:
    F06 (Profile note) ∪ F05 (conditional Fixability) = `{"F05", "F06"}`.
    """
    text = _TAXONOMY_MD.read_text(encoding="utf-8")
    profile_note_ids = frozenset(m.group("id") for m in _PROFILE_NOTE_LINE.finditer(text))
    conditional_ids = frozenset(
        tid for tid in _fixability_texts() if taxonomy_fixability_category(tid) == "conditional"
    )
    return profile_note_ids | conditional_ids


CONDITIONAL_FIXABILITY_RESOLUTION: dict[str, dict[str, str]] = {
    "F05": {"bowing": "post-fixable", "off_center_drift": "capture-only"},
}
"""Per-ID, per-sub_pattern-value resolution for `conditional` Fixability
(QUEUE.md item 18c, DECISIONS.md D-009's ruling, TAXONOMY.md v1.2). Not
parsed from TAXONOMY.md: the mapping from a closed-vocabulary sub-pattern
value to post-fixable/capture-only lives in the Fixability bullet's own
prose explanation ("`bowing` ... is post-fixable ...; `off_center_drift` ...
is capture-only"), not a second structured bullet to regex for. Hand-
transcribed here instead - `tests/test_schema.py`'s
`test_conditional_fixability_resolution_is_complete` guards that every
`conditional`-category ID has an entry here and vice versa, so a future
TAXONOMY.md amendment adding a second conditional item fails loudly instead
of silently resolving to nothing.
"""


def resolve_finding_fixability(finding: Finding) -> str | None:
    """One word ("post-fixable" or "capture-only") for `finding`, or `None`.

    QUEUE.md item 18(d): "the Finding-level fixability surfaced in
    analyze_batch's report ... so the Check surface has its input when it
    arrives." Only F-items carry a Fixability bullet - S-items and
    `unclassified` return `None` (v1.2's changelog: S-items/R-items/CMP
    "intentionally carry no Fixability"). A `conditional` category (F05
    today) is resolved per-finding via its `sub_pattern` against
    `CONDITIONAL_FIXABILITY_RESOLUTION` - raises if a conditional finding
    lacks a resolvable sub_pattern rather than guessing; in production this
    cannot happen because `_vision.judge`'s `SubPatternSpec` mechanism
    requires the sub-pattern field whenever `detected` is true.
    """
    if not finding.taxonomy_id.startswith("F"):
        return None
    category = taxonomy_fixability_category(finding.taxonomy_id)
    if category != "conditional":
        return category
    resolution = CONDITIONAL_FIXABILITY_RESOLUTION.get(finding.taxonomy_id, {})
    resolved = resolution.get(finding.sub_pattern or "")
    if resolved is None:
        raise SchemaError(
            f"conditional Fixability for {finding.taxonomy_id!r} could not be resolved: "
            f"sub_pattern={finding.sub_pattern!r} is not in {sorted(resolution)}"
        )
    return resolved


@dataclass
class Finding:
    """One per-frame observation: a taxonomy ID, or `unclassified` + description.

    `sub_pattern` is optional, closed-vocabulary detail - only valid on IDs
    in `taxonomy_ids_with_subpattern()`; never a free-standing classification
    of its own. Two distinct consumers read it today: profile-layer recurrence
    (TAXONOMY.md's "running profile" row - F06's "which edge") and fixability
    resolution (`resolve_finding_fixability`, QUEUE.md item 18c - F05's
    `bowing`/`off_center_drift`). Which consumer applies is determined by the
    finding's own `taxonomy_id`, not by anything on this field.
    """

    taxonomy_id: str
    description: str | None = None
    sub_pattern: str | None = None

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
        if self.sub_pattern is not None:
            if not self.sub_pattern.strip():
                raise SchemaError("Finding.sub_pattern, if set, must be non-empty")
            allowed = taxonomy_ids_with_subpattern()
            if self.taxonomy_id not in allowed:
                raise SchemaError(
                    f"taxonomy_id {self.taxonomy_id!r} has no TAXONOMY.md Profile note "
                    f"documenting a sub-pattern; only {sorted(allowed)} may set sub_pattern"
                )

    def to_dict(self) -> dict:
        return {
            "taxonomy_id": self.taxonomy_id,
            "description": self.description,
            "sub_pattern": self.sub_pattern,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Finding:
        return cls(
            taxonomy_id=data["taxonomy_id"],
            description=data.get("description"),
            sub_pattern=data.get("sub_pattern"),
        )


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
class Comparison:
    """One three-frame comparison over a near-duplicate group (TAXONOMY.md §CMP).

    Draws exclusively on the CMP rubric's own vocabulary, per TAXONOMY.md's
    output-mapping table ("Three-frame comparison | The CMP rubric,
    exclusively") - deliberately no F/S taxonomy IDs anywhere on this
    dataclass, unlike `Pick`/`Habit`.
    """

    group: list[str]
    winner_frame_id: str
    subject_placement: str
    edge_amputations: str
    incidental_distractions: str
    tiebreaker: str | None = None

    def __post_init__(self) -> None:
        if len(self.group) < 2:
            raise SchemaError("a comparison group must have at least 2 frames")
        if self.winner_frame_id not in self.group:
            raise SchemaError(
                f"winner_frame_id {self.winner_frame_id!r} is not among the compared group {self.group!r}"
            )
        for axis_name, value in (
            ("subject_placement", self.subject_placement),
            ("edge_amputations", self.edge_amputations),
            ("incidental_distractions", self.incidental_distractions),
        ):
            if not value or not value.strip():
                raise SchemaError(f"comparison {axis_name} must be a non-empty description")

    def to_dict(self) -> dict:
        return {
            "group": self.group,
            "winner_frame_id": self.winner_frame_id,
            "subject_placement": self.subject_placement,
            "edge_amputations": self.edge_amputations,
            "incidental_distractions": self.incidental_distractions,
            "tiebreaker": self.tiebreaker,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Comparison:
        return cls(
            group=list(data["group"]),
            winner_frame_id=data["winner_frame_id"],
            subject_placement=data["subject_placement"],
            edge_amputations=data["edge_amputations"],
            incidental_distractions=data["incidental_distractions"],
            tiebreaker=data.get("tiebreaker"),
        )


@dataclass
class Rule:
    """One triggered conditional rule (TAXONOMY.md §R): forward-looking advice, not a per-frame finding.

    A different object type from `Finding` on purpose - TAXONOMY.md is
    explicit that rules are "triggered by shooting conditions, not detected
    in frames" and are a "different object type for the classifier." R01 is
    the only R-item today; `advice` is its Rule text, read verbatim (same
    single-source-of-truth reasoning as `Habit.description`).
    """

    taxonomy_id: str
    advice: str

    def __post_init__(self) -> None:
        valid = taxonomy_ids()
        if self.taxonomy_id not in valid or not self.taxonomy_id.startswith("R"):
            raise SchemaError(f"rule taxonomy_id {self.taxonomy_id!r} must be an R-item ID")
        if not self.advice or not self.advice.strip():
            raise SchemaError("rule requires non-empty advice")

    def to_dict(self) -> dict:
        return {"taxonomy_id": self.taxonomy_id, "advice": self.advice}

    @classmethod
    def from_dict(cls, data: dict) -> Rule:
        return cls(taxonomy_id=data["taxonomy_id"], advice=data["advice"])


@dataclass
class AnalysisOutput:
    """Top-level output of an analysis run: version, frames, pick, habit, comparisons."""

    schema_version: str = SCHEMA_VERSION
    frames: list[FrameAnalysis] = field(default_factory=list)
    pick: Pick | None = None
    habit: Habit | None = None
    comparisons: list[Comparison] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise SchemaError(
                f"schema_version {self.schema_version!r} does not match current {SCHEMA_VERSION!r}"
            )
        frame_ids = {f.frame_id for f in self.frames}
        if self.pick is not None and self.pick.frame_id not in frame_ids:
            raise SchemaError(f"pick.frame_id {self.pick.frame_id!r} is not among analyzed frames")
        for comparison in self.comparisons:
            unknown = [fid for fid in comparison.group if fid not in frame_ids]
            if unknown:
                raise SchemaError(f"comparison group references unknown frame_id(s) {unknown!r}")

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "frames": [f.to_dict() for f in self.frames],
            "pick": self.pick.to_dict() if self.pick is not None else None,
            "habit": self.habit.to_dict() if self.habit is not None else None,
            "comparisons": [c.to_dict() for c in self.comparisons],
            "rules": [r.to_dict() for r in self.rules],
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
            comparisons=[Comparison.from_dict(c) for c in data.get("comparisons", [])],
            rules=[Rule.from_dict(r) for r in data.get("rules", [])],
        )

    @classmethod
    def from_json(cls, text: str) -> AnalysisOutput:
        return cls.from_dict(json.loads(text))
