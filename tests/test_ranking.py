"""Tests for src/picstory/ranking.py (QUEUE.md Stage 2, item 9)."""

from __future__ import annotations

from picstory.ranking import build_pick, rank_frames, score_frame, share_list_lines
from picstory.schema import Finding, FrameAnalysis, taxonomy_reinforcement_text


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
