"""Ranking + shortlist (QUEUE.md Stage 2, item 9) and the session habit (item 10).

TAXONOMY.md's output-mapping table settles the vocabulary this module is
allowed to use, before any ranking logic gets written: "The pick (and the
share list) draws on Strengths (S-items) as the 'why it's share-worthy'
one-liners; failure modes as disqualifiers." That sentence is the entire
spec for what "ranking" means here - there is no separate scoring rubric in
TAXONOMY.md to implement, only this one mapping. So:

- A frame's score is `count(S-item findings) - count(F-item findings)` -
  the direct arithmetic reading of "S-items count for you, F-items count
  against you." R01 findings cannot occur per-frame (it is a
  batch/conditional trigger, never a per-frame `Finding.taxonomy_id` - see
  scripts/analyze.py's module docstring) and `unclassified` findings map to
  neither polarity, so both are excluded from scoring rather than guessed
  at.
- The shortlist is every analyzed frame in score order, best first, ties
  broken by keeping the batch's original order (Python's `sorted` is
  stable even under `reverse=True` - equal-score frames are not
  reordered). This is PREDICTION.md's "ranked shortlist," surfaced by the
  CLI report rather than added as new `AnalysisOutput` schema surface: item
  9 asks for the pick (a schema field that has existed, unpopulated, since
  item 1) and share-list one-liners, not a persisted ranking artifact.
- The pick is the shortlist's top frame. Its `Pick.reasons` are the S-item
  IDs it was actually found to carry, and its `Pick.disqualifiers` are the
  F-item IDs it was actually found to carry - not the F-items that ranked
  *other* frames lower. This reads `Pick` (schema.py, item 1, CRITIC-cleared
  in critic-002) literally: the dataclass ties `disqualifiers` to one
  `frame_id`, so it names what's still wrong with *that* frame, not a
  comparison against alternatives. A pick with disclosed disqualifiers
  (rather than a silently laundered "best of a bad batch") matches the
  disclosure standard the rest of the codebase already holds itself to -
  F09's documented center-third proxy, R01's stale-citation flag in
  REVIEW.md, F03's documented dHash proxy for "position/angle."
- Share-list one-liners are each reason's taxonomy ID paired with its
  Reinforcement text, read verbatim from TAXONOMY.md via
  `schema.taxonomy_reinforcement_text` - the "drawn from S-item vocabulary"
  requirement read the same way CLAUDE.md's API-discipline rule reads
  "embeds the item's Detection text": from the frozen source, not a
  hand-copied paraphrase that could drift.
- The habit (item 10) is "whichever F- or S-item recurs most in the batch"
  (same table), counted by number of frames carrying that ID, R01/
  unclassified excluded (see `compute_habit`'s own docstring for the
  reasoning, including its Correction-vs-Reinforcement coaching-text split
  and its documented tie-break).

QUEUE.md item 17 (DECISIONS.md D-008b/D-008c) calibrates both mechanisms
against the capstone batch (docs/capstone-vienna-report.md):

- D-008c: raw-count habit selection is always captured by whichever
  equipment/condition ID fires on nearly every frame (F05/F06/F11 on the
  capstone batch), which is a fact about the lens or the light, not the
  user. `compute_habit` now excludes any ID that is *pervasive* -
  `pervasive_ids`/`PERVASIVE_THRESHOLD` - from habit selection; the habit
  is the most-recurrent *non-pervasive* F/S ID. Pervasive IDs are not
  discarded - `pervasive_note` surfaces them as one disclosed report line,
  distinct from the habit.
- D-008b: at equal `score_frame`, `rank_frames` now breaks the tie toward
  the frame with more named S-item strengths before falling back to batch
  order - "something right" outranks "merely nothing wrong" at equal net
  score, rather than winning by the luck of position.
"""

from __future__ import annotations

from picstory.schema import (
    FrameAnalysis,
    Habit,
    Pick,
    taxonomy_correction_text,
    taxonomy_reinforcement_text,
)


def _ids_with_prefix(frame_analysis: FrameAnalysis, prefix: str) -> list[str]:
    """Unique taxonomy IDs of one polarity present on a frame, in ID order.

    Structurally a frame can carry at most one `Finding` per ID (one
    detector, called once, per ID) - the `set` here is defensive, not load-
    bearing. `sorted` gives a deterministic reading order independent of
    detector-dispatch order (F03's batch-level finding is appended after
    the per-frame sweep in scripts/analyze_batch.py, so raw finding order is
    not itself sorted).
    """
    return sorted({f.taxonomy_id for f in frame_analysis.findings if f.taxonomy_id.startswith(prefix)})


def score_frame(frame_analysis: FrameAnalysis) -> int:
    """S-item findings count for a frame; F-item findings count against it."""
    return len(_ids_with_prefix(frame_analysis, "S")) - len(_ids_with_prefix(frame_analysis, "F"))


def rank_frames(frame_analyses: list[FrameAnalysis]) -> list[FrameAnalysis]:
    """The shortlist: every frame, best-scoring first.

    DECISIONS.md D-008b: at equal `score_frame`, the frame with more named
    S-item strengths ranks first - a frame with something *right* beats a
    frame with merely nothing wrong, rather than the two being an
    indistinguishable tie broken only by position. Only a genuine tie on
    both score and S-count keeps the batch's original order (Python's
    `sorted` is stable even under `reverse=True`).
    """
    return sorted(
        frame_analyses,
        key=lambda fa: (score_frame(fa), len(_ids_with_prefix(fa, "S"))),
        reverse=True,
    )


def build_pick(frame_analyses: list[FrameAnalysis]) -> Pick | None:
    """The shortlist's top frame, with its own S-item reasons and F-item disqualifiers.

    `None` for an empty batch - there is no frame to name as `frame_id`, and
    `AnalysisOutput.pick` requires one that is actually among `frames`.
    """
    if not frame_analyses:
        return None
    winner = rank_frames(frame_analyses)[0]
    return Pick(
        frame_id=winner.frame_id,
        reasons=_ids_with_prefix(winner, "S"),
        disqualifiers=_ids_with_prefix(winner, "F"),
    )


def share_list_lines(pick: Pick) -> list[str]:
    """One share-list one-liner per S-item reason, in TAXONOMY.md's own Reinforcement wording."""
    return [f"{taxonomy_id} — {taxonomy_reinforcement_text(taxonomy_id)}" for taxonomy_id in pick.reasons]


PERVASIVE_THRESHOLD = 2 / 3
"""DECISIONS.md D-008c: an F/S item firing on more than this share of the
batch's frames describes the batch's shooting conditions or equipment (the
lens, the light), not a per-frame choice by the user, and is excluded from
habit selection by `compute_habit`. Calibrated against the capstone batch
(docs/capstone-vienna-report.md, 31 frames): F05 (28), F06 (27), and F11
(25) all clear it (>20.67 frames) and are excluded; the ruling's own
recommendation named this exact fraction (">2/3"), not a value tuned to hit
a particular outcome.
"""


def _id_counts(frame_analyses: list[FrameAnalysis]) -> dict[str, int]:
    """Per-ID frame counts across F/S items only (R01/unclassified excluded).

    Shared by `compute_habit` and `pervasive_ids` so both read "how many
    frames carry this ID" the same way - one count per distinct frame, not
    a raw finding count (see `_ids_with_prefix`'s docstring: a frame
    structurally carries at most one `Finding` per ID).
    """
    counts: dict[str, int] = {}
    for frame_analysis in frame_analyses:
        for taxonomy_id in _ids_with_prefix(frame_analysis, "F") + _ids_with_prefix(frame_analysis, "S"):
            counts[taxonomy_id] = counts.get(taxonomy_id, 0) + 1
    return counts


def pervasive_ids(frame_analyses: list[FrameAnalysis]) -> list[str]:
    """F/S items firing on more than `PERVASIVE_THRESHOLD` of the batch's frames.

    Sorted by taxonomy ID (ascending) for deterministic reporting, same
    convention as `_ids_with_prefix`. Empty for an empty batch - there is no
    frame count to take a share of.
    """
    total = len(frame_analyses)
    if total == 0:
        return []
    return sorted(tid for tid, count in _id_counts(frame_analyses).items() if count / total > PERVASIVE_THRESHOLD)


def pervasive_note(frame_analyses: list[FrameAnalysis]) -> str | None:
    """One-line, disclosed session note for this batch's pervasive F/S items, or `None`.

    DECISIONS.md D-008c's ruling: pervasive findings are not discarded once
    excluded from habit selection - they surface as "a separate one-line
    session note ... distinct from the habit" (one line, not a list, per
    the product spec). `None` when nothing clears the threshold, so callers
    can skip the line entirely rather than print an empty one.
    """
    ids = pervasive_ids(frame_analyses)
    if not ids:
        return None
    return f"This batch, throughout (excluded from habit selection): {', '.join(ids)}"


def compute_habit(frame_analyses: list[FrameAnalysis]) -> Habit | None:
    """The session habit: the most-recurrent *non-pervasive* F- or S-item.

    TAXONOMY.md's output-mapping table: "Whichever F- or S-item recurs most
    in the batch; reinforcement counts as coaching." DECISIONS.md D-008c
    narrows "recurs most" to exclude `pervasive_ids` first - raw count alone
    is always captured by whichever ID describes the batch's equipment or
    conditions (a fact about the lens, not the user), which the capstone
    batch demonstrated directly (F05 at 28/31 topped every prior raw-count
    run). Recurrence is still counted per distinct frame carrying the ID,
    not a raw finding count (see `_id_counts`'s docstring). R01 (never a
    per-frame `Finding` - see scripts/analyze.py's module docstring) and
    `unclassified` (neither polarity, no coaching text in TAXONOMY.md) are
    excluded, the same exclusion `score_frame` already applies to.

    "Reinforcement counts as coaching" reads as the symmetric statement for
    S-items that F-items already get from their own Correction bullet -
    Habit.description is the winning ID's Correction text if it's an
    F-item, its Reinforcement text if it's an S-item, both read verbatim via
    `schema.py` (same single-source-of-truth reasoning as `share_list_lines`
    uses for Reinforcement text).

    Ties break by taxonomy ID (ascending), unchanged from before this
    exclusion - TAXONOMY.md does not specify a tie-break for "recurs most"
    under a genuine tie; this makes the choice deterministic and documented
    rather than leaving it to dict iteration order.

    `None` when every F/S item that fired is pervasive, or nothing fired at
    all - either way nothing non-pervasive recurs, so there is nothing to
    name a habit from (pervasive IDs still reach the report via
    `pervasive_note`, just not as the habit).
    """
    counts = _id_counts(frame_analyses)
    excluded = set(pervasive_ids(frame_analyses))
    eligible = {tid: count for tid, count in counts.items() if tid not in excluded}
    if not eligible:
        return None
    winner = max(sorted(eligible), key=eligible.get)
    description = (
        taxonomy_correction_text(winner) if winner.startswith("F") else taxonomy_reinforcement_text(winner)
    )
    return Habit(taxonomy_id=winner, description=description)
