"""Ranking + shortlist (QUEUE.md Stage 2, item 9).

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
"""

from __future__ import annotations

from picstory.schema import FrameAnalysis, Pick, taxonomy_reinforcement_text


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
    """The shortlist: every frame, best-scoring first. Ties keep batch order."""
    return sorted(frame_analyses, key=score_frame, reverse=True)


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
