"""Behavior tests for F03 (QUEUE.md item 8): near-duplicate grouping.

Unlike every other local detector (test_local_detectors.py), F03 is
batch-level - `picstory.detectors.f03.detect(frames)` takes an ordered list
of Frames, not one Frame - so these tests build small synthetic batches
rather than single frames. Fixtures use a textured (checkerboard + bright
block) synthetic scene rather than a flat one: a flat scene makes the
difference-hash comparison pathologically sensitive to tiny per-pixel noise
(most adjacent-pixel deltas sit at exactly zero), which a real photo never
is. Textured fixtures keep the noise-robustness checks meaningful.

Naming matches tests/test_taxonomy_coverage.py's convention (`test_f03_...`)
so these count toward that guard's per-ID test coverage.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from picstory import detectors
from picstory.detectors import f03
from picstory.frame import Frame


def _scene(offset: int = 0, size: int = 200, block: int = 8) -> np.ndarray:
    """A textured checkerboard with a bright "subject" block at `offset`."""
    yy, xx = np.mgrid[0:size, 0:size]
    gray = (((xx // block) + (yy // block)) % 2 * 180 + 30).astype(np.float64)
    x0 = 40 + offset
    gray[80:160, x0 : x0 + 60] = 255.0
    return gray


def _frame(gray: np.ndarray, frame_id: str, exif: dict | None = None) -> Frame:
    rgb = np.stack([gray, gray, gray], axis=-1).astype(np.uint8)
    return Frame(frame_id=frame_id, path=Path("."), rgb=rgb, exif=exif or {})


def _noisy(gray: np.ndarray, sigma: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.clip(gray + rng.normal(0, sigma, size=gray.shape), 0, 255)


# --- group_near_duplicates(): the grouping algorithm -----------------------


def test_f03_safety_copies_groups_consecutive_near_identical_frames() -> None:
    base = _scene(0)
    frames = [
        _frame(base, "00_a"),
        _frame(_noisy(base, sigma=2, seed=1), "01_b"),
        _frame(_noisy(base, sigma=2, seed=2), "02_c"),
        _frame(_scene(offset=120), "03_d"),  # subject moved - a real variation
    ]

    groups = f03.group_near_duplicates(frames)

    assert groups == [["00_a", "01_b", "02_c"]]


def test_f03_safety_copies_clean_when_subject_moves_every_frame() -> None:
    frames = [
        _frame(_scene(offset=off), f"{i:02d}_x")
        for i, off in enumerate((0, 60, 120))
    ]

    assert f03.group_near_duplicates(frames) == []


def test_f03_safety_copies_focal_length_change_breaks_the_run() -> None:
    base = _scene(0)
    frames = [
        _frame(base, "00_a", exif={"FocalLength": 24.0}),
        _frame(base, "01_b", exif={"FocalLength": 50.0}),
    ]

    assert f03.group_near_duplicates(frames) == []


def test_f03_safety_copies_missing_focal_length_does_not_block_grouping() -> None:
    base = _scene(0)
    frames = [
        _frame(base, "00_a", exif={"FocalLength": 24.0}),
        _frame(base, "01_b", exif={}),  # no FocalLength tag at all
    ]

    assert f03.group_near_duplicates(frames) == [["00_a", "01_b"]]


def test_f03_safety_copies_timestamp_gap_breaks_the_run() -> None:
    base = _scene(0)
    frames = [
        _frame(base, "00_a", exif={"DateTimeOriginal": "2026:08:11 10:00:00"}),
        _frame(base, "01_b", exif={"DateTimeOriginal": "2026:08:11 10:05:00"}),
    ]

    assert f03.group_near_duplicates(frames) == []


def test_f03_safety_copies_close_timestamps_do_not_block_grouping() -> None:
    base = _scene(0)
    frames = [
        _frame(base, "00_a", exif={"DateTimeOriginal": "2026:08:11 10:00:00"}),
        _frame(base, "01_b", exif={"DateTimeOriginal": "2026:08:11 10:00:05"}),
    ]

    assert f03.group_near_duplicates(frames) == [["00_a", "01_b"]]


def test_f03_safety_copies_no_group_below_two_frames() -> None:
    # A single qualifying pair is a group of 2, but one frame alone (or a
    # batch where nothing ever qualifies) must never surface a group.
    assert f03.group_near_duplicates([_frame(_scene(0), "00_a")]) == []


# --- detect(): keeper is unflagged, copies get the Finding -----------------


def test_f03_safety_copies_only_flags_non_keeper_frames() -> None:
    base = _scene(0)
    frames = [
        _frame(base, "00_a"),
        _frame(_noisy(base, sigma=2, seed=1), "01_b"),
        _frame(_noisy(base, sigma=2, seed=2), "02_c"),
        _frame(_scene(offset=120), "03_d"),
    ]

    findings = f03.detect(frames)

    assert set(findings) == {"01_b", "02_c"}
    assert "03_d" not in findings and "00_a" not in findings
    for finding in findings.values():
        assert finding.taxonomy_id == "F03"
        assert "00_a" in finding.description


def test_f03_safety_copies_empty_when_no_duplicates() -> None:
    frames = [
        _frame(_scene(offset=off), f"{i:02d}_x")
        for i, off in enumerate((0, 60, 120))
    ]
    assert f03.detect(frames) == {}


# --- registration ------------------------------------------------------


def test_f03_safety_copies_registered_in_detector_registry() -> None:
    assert detectors.get("F03") is f03.detect
