"""Behavior tests for R01 (QUEUE.md item 13): the haze rule.

Unlike every F/S detector, R01's `detect()` takes the batch's already-
computed `FrameAnalysis` list (not a `Frame`, and not raw findings from a
single frame) and returns a `schema.Rule` or `None` - see
`picstory.detectors.r01`'s module docstring for why. Naming matches
tests/test_taxonomy_coverage.py's convention (`test_r01_...`).
"""

from __future__ import annotations

from picstory.detectors import r01
from picstory.detectors.base import get
from picstory.schema import Finding, FrameAnalysis, Rule, taxonomy_rule_text


def _fa(frame_id: str, *ids: str) -> FrameAnalysis:
    return FrameAnalysis(
        frame_id=frame_id,
        findings=[Finding(taxonomy_id=i, description=None if i != "unclassified" else "x") for i in ids],
    )


def test_r01_haze_rule_triggers_when_f12_present_anywhere_in_batch() -> None:
    frame_analyses = [_fa("00_a", "S01"), _fa("01_b", "F12"), _fa("02_c")]

    rule = r01.detect(frame_analyses)

    assert rule == Rule(taxonomy_id="R01", advice=taxonomy_rule_text("R01"))


def test_r01_haze_rule_none_when_no_f12_in_batch() -> None:
    frame_analyses = [_fa("00_a", "S01"), _fa("01_b", "F06"), _fa("02_c")]

    assert r01.detect(frame_analyses) is None


def test_r01_haze_rule_none_for_empty_batch() -> None:
    assert r01.detect([]) is None


def test_r01_haze_rule_fires_once_regardless_of_how_many_frames_carry_f12() -> None:
    # Forward-looking session advice, not a per-frame tally - one F12 or
    # five F12s both produce exactly one Rule.
    frame_analyses = [_fa("00_a", "F12"), _fa("01_b", "F12"), _fa("02_c", "F12")]

    rule = r01.detect(frame_analyses)

    assert rule is not None
    assert rule.taxonomy_id == "R01"


def test_r01_haze_rule_registered_in_detector_registry() -> None:
    assert get("R01") is r01.detect
