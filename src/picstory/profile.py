"""Per-user recurrence store across sessions (QUEUE.md Stage 4, item 12).

TAXONOMY.md's output-mapping table: "The running profile | Per-user
recurrence of F/S items and their sub-patterns (e.g. *which* edge the user
neglects)." Two things this module owns:

- Recurrence: across every session (CLI batch run) ever recorded, how many
  sessions and how many frames carried each F/S taxonomy ID. R01 (never a
  per-frame `Finding` - see scripts/analyze.py's module docstring) and
  `unclassified` (no polarity) are excluded, the same exclusion
  `ranking.py`'s `score_frame`/`compute_habit` already apply.
- Sub-pattern tally: for the taxonomy IDs TAXONOMY.md documents as having a
  profile-layer sub-pattern (`schema.taxonomy_ids_with_subpattern()` -
  today, F06's "Profile note" alone), how often each closed-vocabulary
  value (e.g. F06's `edge`) recurred. Only values `Finding.sub_pattern`
  itself already validated are folded in here - this module trusts, rather
  than re-checks, that upstream vocabulary discipline.

"Session" here means one invocation of the CLI on a user's machine (one
`analyze_batch.py` run), not a BUILDER/CRITIC agent session - a different,
unrelated meaning of the word already used elsewhere (CLAUDE.md's ROLES).

Storage: a JSON file, loaded before and saved after each batch run.
Location resolves from `PICSTORY_PROFILE_PATH` if set, else
`~/.picstory/profile.json` - the same env-var-first, sensible-default
pattern D-006 established for `PICSTORY_VISION_KEY`. `load_profile`/
`save_profile` are the only I/O in this module; `record_session` is pure
(returns a new `Profile`, does not mutate its argument) so it is testable
without touching a filesystem at all.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from picstory.schema import FrameAnalysis

PROFILE_SCHEMA_VERSION = "1.0"


class ProfileError(ValueError):
    """Raised when profile store data does not conform to this module's shape."""


@dataclass
class IdRecurrence:
    """One taxonomy ID's running tally: how many sessions/frames, and sub-pattern detail."""

    taxonomy_id: str
    sessions: int = 0
    frames: int = 0
    sub_patterns: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "taxonomy_id": self.taxonomy_id,
            "sessions": self.sessions,
            "frames": self.frames,
            "sub_patterns": dict(self.sub_patterns),
        }

    @classmethod
    def from_dict(cls, data: dict) -> IdRecurrence:
        return cls(
            taxonomy_id=data["taxonomy_id"],
            sessions=data.get("sessions", 0),
            frames=data.get("frames", 0),
            sub_patterns=dict(data.get("sub_patterns", {})),
        )


@dataclass
class Profile:
    """The running profile: every session recorded so far, folded into per-ID recurrence."""

    schema_version: str = PROFILE_SCHEMA_VERSION
    sessions_recorded: int = 0
    recurrences: dict[str, IdRecurrence] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.schema_version != PROFILE_SCHEMA_VERSION:
            raise ProfileError(
                f"profile schema_version {self.schema_version!r} does not match "
                f"current {PROFILE_SCHEMA_VERSION!r}"
            )
        for taxonomy_id, recurrence in self.recurrences.items():
            if taxonomy_id != recurrence.taxonomy_id:
                raise ProfileError(
                    f"recurrences key {taxonomy_id!r} does not match its own "
                    f"IdRecurrence.taxonomy_id {recurrence.taxonomy_id!r}"
                )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "sessions_recorded": self.sessions_recorded,
            "recurrences": {tid: rec.to_dict() for tid, rec in self.recurrences.items()},
        }

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, **kwargs)

    @classmethod
    def from_dict(cls, data: dict) -> Profile:
        return cls(
            schema_version=data.get("schema_version", PROFILE_SCHEMA_VERSION),
            sessions_recorded=data.get("sessions_recorded", 0),
            recurrences={
                tid: IdRecurrence.from_dict(rec) for tid, rec in data.get("recurrences", {}).items()
            },
        )

    @classmethod
    def from_json(cls, text: str) -> Profile:
        return cls.from_dict(json.loads(text))


def default_profile_path() -> Path:
    """Where the running profile lives: `PICSTORY_PROFILE_PATH` if set, else `~/.picstory/profile.json`."""
    override = os.environ.get("PICSTORY_PROFILE_PATH")
    if override:
        return Path(override)
    return Path.home() / ".picstory" / "profile.json"


def load_profile(path: Path) -> Profile:
    """The profile at `path`, or a fresh empty one if nothing has been recorded there yet."""
    if not path.exists():
        return Profile()
    return Profile.from_json(path.read_text(encoding="utf-8"))


def save_profile(profile: Profile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(profile.to_json(), encoding="utf-8")


def _recurring_ids(frame_analysis: FrameAnalysis) -> list:
    """This frame's F/S findings, R01/unclassified excluded (same as ranking.py's `_ids_with_prefix`)."""
    return [
        finding
        for finding in frame_analysis.findings
        if finding.taxonomy_id.startswith("F") or finding.taxonomy_id.startswith("S")
    ]


def record_session(profile: Profile, frame_analyses: list[FrameAnalysis]) -> Profile:
    """Fold one session's (batch run's) F/S findings into the running profile.

    Pure: returns a new `Profile`, does not mutate `profile`. A taxonomy ID
    counts one `sessions` increment if it appeared on at least one frame
    this session (regardless of how many), and one `frames` increment per
    frame that carried it - the same "count per distinct frame" reading
    `ranking.compute_habit` already uses for a single session's habit, now
    accumulated across sessions. Sub-pattern values are tallied per
    occurrence (not deduped per session), since a batch of many frames
    genuinely gives more sub-pattern evidence than one.
    """
    recurrences = {
        tid: IdRecurrence(
            taxonomy_id=rec.taxonomy_id,
            sessions=rec.sessions,
            frames=rec.frames,
            sub_patterns=dict(rec.sub_patterns),
        )
        for tid, rec in profile.recurrences.items()
    }
    ids_seen_this_session: set[str] = set()
    for frame_analysis in frame_analyses:
        for finding in _recurring_ids(frame_analysis):
            tid = finding.taxonomy_id
            rec = recurrences.setdefault(tid, IdRecurrence(taxonomy_id=tid))
            rec.frames += 1
            ids_seen_this_session.add(tid)
            if finding.sub_pattern:
                rec.sub_patterns[finding.sub_pattern] = rec.sub_patterns.get(finding.sub_pattern, 0) + 1
    for tid in ids_seen_this_session:
        recurrences[tid].sessions += 1
    return Profile(sessions_recorded=profile.sessions_recorded + 1, recurrences=recurrences)


def top_recurrences(profile: Profile) -> list[IdRecurrence]:
    """Every recorded ID, most-recurrent first: sessions desc, then frames desc, then ID ascending."""
    return sorted(profile.recurrences.values(), key=lambda rec: (-rec.sessions, -rec.frames, rec.taxonomy_id))


def summary_lines(profile: Profile) -> list[str]:
    """One line per recorded ID, most-recurrent first - for CLI/report display."""
    lines = []
    for rec in top_recurrences(profile):
        detail = ""
        if rec.sub_patterns:
            parts = ", ".join(
                f"{value} x{count}"
                for value, count in sorted(rec.sub_patterns.items(), key=lambda kv: (-kv[1], kv[0]))
            )
            detail = f" ({parts})"
        plural_sessions = "session" if rec.sessions == 1 else "sessions"
        plural_frames = "frame" if rec.frames == 1 else "frames"
        lines.append(
            f"{rec.taxonomy_id}: {rec.sessions} {plural_sessions}, {rec.frames} {plural_frames}{detail}"
        )
    return lines
