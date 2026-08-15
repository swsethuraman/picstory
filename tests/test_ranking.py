"""Tests for src/picstory/ranking.py (QUEUE.md Stage 2, item 9)."""

from __future__ import annotations

from picstory.ranking import (
    PERVASIVE_THRESHOLD,
    build_pick,
    compute_habit,
    pervasive_ids,
    pervasive_note,
    rank_frames,
    score_frame,
    share_list_lines,
)
from picstory.schema import (
    Finding,
    FrameAnalysis,
    taxonomy_correction_text,
    taxonomy_reinforcement_text,
)


def _fa(frame_id: str, *taxonomy_ids: str) -> FrameAnalysis:
    return FrameAnalysis(
        frame_id=frame_id,
        findings=[Finding(taxonomy_id=tid, description="x" if tid == "unclassified" else None) for tid in taxonomy_ids],
    )


# --- score_frame -------------------------------------------------------


def test_score_frame_counts_s_items_for_and_f_items_against() -> None:
    assert score_frame(_fa("a", "S01", "S02")) == 2
    assert score_frame(_fa("a", "F06", "F07")) == -2
    assert score_frame(_fa("a", "S01", "F06")) == 0


def test_score_frame_ignores_unclassified_and_r_items() -> None:
    # R01 cannot occur as a real per-frame Finding (it's a batch/conditional
    # trigger - see scripts/analyze.py's module docstring), but the schema
    # does not forbid constructing one; score_frame must not treat it as
    # either polarity if it somehow appears.
    assert score_frame(_fa("a", "unclassified", "R01")) == 0


def test_score_frame_clean_frame_is_zero() -> None:
    assert score_frame(_fa("a")) == 0


# --- rank_frames ---------------------------------------------------------


def test_rank_frames_orders_best_score_first() -> None:
    strong = _fa("strong", "S01", "S02")
    weak = _fa("weak", "F06")
    clean = _fa("clean")

    ranked = rank_frames([weak, clean, strong])

    assert [fa.frame_id for fa in ranked] == ["strong", "clean", "weak"]


def test_rank_frames_ties_keep_original_batch_order() -> None:
    a = _fa("00_a", "F06")
    b = _fa("01_b", "F07")
    c = _fa("02_c", "F08")

    ranked = rank_frames([a, b, c])

    assert [fa.frame_id for fa in ranked] == ["00_a", "01_b", "02_c"]


def test_rank_frames_empty_list() -> None:
    assert rank_frames([]) == []


def test_rank_frames_s_count_breaks_score_ties() -> None:
    """DECISIONS.md D-008b: at equal score, more named S-item strengths wins
    outright - not the luck of batch order. The capstone tie (0967 over
    0969) put the S-bearing frame first anyway; this fixture puts it
    *second* in batch order deliberately, so a batch-order-only tie-break
    would (wrongly) pick the clean frame first, and only the S-count rule
    can produce the correct winner.
    """
    clean = _fa("clean")  # score 0, 0 S-items - listed first in the batch
    strength_and_flaw = _fa("strength_and_flaw", "S03", "F08")  # score 0, 1 S-item

    ranked = rank_frames([clean, strength_and_flaw])

    assert [fa.frame_id for fa in ranked] == ["strength_and_flaw", "clean"]


def test_rank_frames_genuine_tie_on_score_and_s_count_keeps_batch_order() -> None:
    a = _fa("00_a", "S01")
    b = _fa("01_b", "S02")

    ranked = rank_frames([a, b])

    assert [fa.frame_id for fa in ranked] == ["00_a", "01_b"]


# --- build_pick ------------------------------------------------------------


def test_build_pick_empty_batch_is_none() -> None:
    assert build_pick([]) is None


def test_build_pick_selects_top_ranked_frame() -> None:
    strong = _fa("strong", "S01")
    weak = _fa("weak", "F06")

    pick = build_pick([weak, strong])

    assert pick.frame_id == "strong"
    assert pick.reasons == ["S01"]
    assert pick.disqualifiers == []


def test_build_pick_names_the_winner_s_own_remaining_disqualifiers() -> None:
    """A frame can win the batch and still carry F-item findings of its own -
    Pick.disqualifiers discloses those rather than hiding them (same
    disclosure standard as F09's documented proxy, R01's stale-citation
    flag): it names what's still wrong with *this* frame, not what ranked
    other frames lower."""
    only_option = _fa("only", "S01", "F06")

    pick = build_pick([only_option])

    assert pick.frame_id == "only"
    assert pick.reasons == ["S01"]
    assert pick.disqualifiers == ["F06"]


def test_build_pick_ignores_unclassified_findings() -> None:
    pick = build_pick([_fa("a", "unclassified")])
    assert pick.reasons == []
    assert pick.disqualifiers == []


def test_build_pick_reasons_and_disqualifiers_are_sorted_and_deduped() -> None:
    fa = FrameAnalysis(
        frame_id="a",
        findings=[
            Finding(taxonomy_id="S02"),
            Finding(taxonomy_id="S01"),
            Finding(taxonomy_id="S01"),  # structurally can't happen twice, but must not double-count
        ],
    )
    pick = build_pick([fa])
    assert pick.reasons == ["S01", "S02"]


# --- share_list_lines --------------------------------------------------


def test_share_list_lines_uses_verbatim_reinforcement_text() -> None:
    pick = build_pick([_fa("a", "S01", "S02")])

    lines = share_list_lines(pick)

    assert lines == [
        f"S01 — {taxonomy_reinforcement_text('S01')}",
        f"S02 — {taxonomy_reinforcement_text('S02')}",
    ]


def test_share_list_lines_empty_when_no_s_item_reasons() -> None:
    pick = build_pick([_fa("a", "F06")])
    assert share_list_lines(pick) == []


# --- compute_habit -------------------------------------------------------


def test_compute_habit_empty_batch_is_none() -> None:
    assert compute_habit([]) is None


def test_compute_habit_none_when_no_f_or_s_finding_recurs() -> None:
    assert compute_habit([_fa("a"), _fa("b", "unclassified"), _fa("c", "R01")]) is None


def test_compute_habit_picks_most_recurrent_f_item_with_correction_text() -> None:
    habit = compute_habit([_fa("a", "F06"), _fa("b", "F06"), _fa("c", "F07")])
    assert habit.taxonomy_id == "F06"
    assert habit.description == taxonomy_correction_text("F06")


def test_compute_habit_picks_most_recurrent_s_item_with_reinforcement_text() -> None:
    habit = compute_habit([_fa("a", "S01"), _fa("b", "S01"), _fa("c", "S02")])
    assert habit.taxonomy_id == "S01"
    assert habit.description == taxonomy_reinforcement_text("S01")


def test_compute_habit_counts_frames_not_raw_findings() -> None:
    # F06 appears on 2 distinct frames, F07 on 1 - F06 wins even though a
    # frame structurally carries at most one Finding per ID (no way to
    # inflate a single frame's count for one ID). A third, clean frame
    # keeps F06 at 2/3 (not more than PERVASIVE_THRESHOLD) so the count
    # itself, not pervasiveness exclusion, is what this test exercises.
    habit = compute_habit([_fa("a", "F06"), _fa("b", "F06", "F07"), _fa("c")])
    assert habit.taxonomy_id == "F06"


def test_compute_habit_ties_break_by_ascending_taxonomy_id() -> None:
    habit = compute_habit([_fa("a", "F07"), _fa("b", "F06")])
    assert habit.taxonomy_id == "F06"


def test_compute_habit_ignores_unclassified_and_r_items() -> None:
    # Two clean frames keep F06 at 1/3 (not pervasive) - see the comment on
    # test_compute_habit_counts_frames_not_raw_findings above.
    habit = compute_habit([_fa("a", "F06", "unclassified", "R01"), _fa("b"), _fa("c")])
    assert habit.taxonomy_id == "F06"


def test_compute_habit_excludes_pervasive_id_even_when_it_is_the_raw_count_winner() -> None:
    """DECISIONS.md D-008c: an ID firing on more than PERVASIVE_THRESHOLD of
    the batch is a fact about the batch's conditions/equipment, not a
    per-frame choice, and sits out habit selection even though raw count
    alone would make it the obvious winner."""
    frames = [_fa("a", "F05"), _fa("b", "F05"), _fa("c", "F05"), _fa("d", "F08")]
    # F05 fires on 3/4 = 0.75 > 2/3: pervasive. F08 fires on 1/4: not.

    assert pervasive_ids(frames) == ["F05"]
    habit = compute_habit(frames)
    assert habit.taxonomy_id == "F08"


def test_compute_habit_none_when_every_recurring_id_is_pervasive() -> None:
    frames = [_fa("a", "F05"), _fa("b", "F05"), _fa("c", "F05")]
    assert compute_habit(frames) is None


# --- pervasive_ids / pervasive_note (DECISIONS.md D-008c) -----------------


def test_pervasive_threshold_is_two_thirds() -> None:
    assert PERVASIVE_THRESHOLD == 2 / 3


def test_pervasive_ids_empty_batch() -> None:
    assert pervasive_ids([]) == []


def test_pervasive_ids_none_when_nothing_clears_the_threshold() -> None:
    # F06 on 2/3 of the batch is exactly the threshold, not *more than* it.
    frames = [_fa("a", "F06"), _fa("b", "F06"), _fa("c")]
    assert pervasive_ids(frames) == []


def test_pervasive_ids_sorted_by_taxonomy_id() -> None:
    frames = [_fa("a", "S02", "F05"), _fa("b", "S02", "F05")]
    assert pervasive_ids(frames) == ["F05", "S02"]


def test_pervasive_note_none_when_nothing_pervasive() -> None:
    assert pervasive_note([_fa("a", "F06"), _fa("b"), _fa("c")]) is None


def test_pervasive_note_names_the_pervasive_ids_on_one_line() -> None:
    frames = [_fa("a", "F05"), _fa("b", "F05")]
    note = pervasive_note(frames)
    assert note is not None
    assert "\n" not in note
    assert "F05" in note


def test_capstone_calibration_pervasiveness_and_actual_habit_winner() -> None:
    """DECISIONS.md D-008c's calibration fixture, built from the capstone
    report's own per-ID frame counts (docs/capstone-vienna-report.md;
    QUEUE.md item 17's instruction: "build the fixture from
    docs/capstone-vienna-report.md's counts"). Counts below were counted
    directly from the report's `[detected]` lines and sum to the report's
    own header total (150 detections across 31 frames) - not eyeballed.

    F05/F06/F11 do classify pervasive, exactly as D-008c's ruling requires.
    But the ruling's text also names the expected habit winner as F08 -
    checked against these same counts, that does not hold: S01 fires on
    20/31 frames (64.5%), *under* PERVASIVE_THRESHOLD (66.7%), so S01 stays
    eligible and outranks F08 (13 frames). This is a genuine mismatch
    between the ruling's stated expected outcome and the evidence it cites,
    not a bug in this mechanism - logged as DECISIONS.md D-010 rather than
    silently forced to F08. This test asserts what the ruling's own,
    faithfully-implemented mechanism actually produces on the real data.
    """
    counts = {
        "F05": 28,
        "F06": 27,
        "F11": 25,
        "S01": 20,
        "F08": 13,
        "F15": 13,
        "S03": 9,
        "F04": 6,
        "F02": 5,
        "F03": 3,
        "F07": 1,
    }
    assert sum(counts.values()) == 150  # the report's own header total
    frames = [_fa(f"{i:02d}") for i in range(31)]
    for taxonomy_id, count in counts.items():
        for frame in frames[:count]:
            frame.findings.append(Finding(taxonomy_id=taxonomy_id))

    assert pervasive_ids(frames) == ["F05", "F06", "F11"]

    habit = compute_habit(frames)
    assert habit.taxonomy_id == "S01"
