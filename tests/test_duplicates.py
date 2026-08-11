"""Behavior tests for QUEUE.md item 8: F03 near-duplicate grouping.

Covers both `picstory.duplicates` (the grouping engine: perceptual hash,
EXIF focal-length/timestamp deltas) and `picstory.detectors.f03` (turning a
group membership into a `Finding`). Synthetic frames only, built from a
deterministic textured pattern (not solid fills - a dHash over a blank
frame can't distinguish "near duplicate" from "totally different", since
every solid-color frame hashes identically) so distinct "photos" actually
hash differently. Calibration for the constants asserted against here is
recorded in `picstory.duplicates`'s module docstring.

Naming matches tests/test_taxonomy_coverage.py's convention (`test_f03_...`)
for the detector-facing tests, so F03 counts toward that guard's per-ID
test coverage.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from picstory.detectors import f03
from picstory.duplicates import (
    MAX_GROUP_SIZE,
    dhash,
    group_near_duplicates,
    hamming_distance,
)
from picstory.frame import Frame


def _pattern(dx: int = 0, dy: int = 0, noise: float = 0.0, size: int = 64) -> np.ndarray:
    yy, xx = np.mgrid[0:size, 0:size]
    img = ((xx + dx) % 256).astype(np.float64) * 0.5 + ((yy + dy) % 256).astype(np.float64) * 0.5
    img += 80 * np.sin((xx + dx) / 15) * np.cos((yy + dy) / 20)
    img = np.clip(img, 0, 255)
    if noise:
        rng = np.random.default_rng(1)
        img = np.clip(img + rng.normal(0, noise, img.shape), 0, 255)
    return np.stack([img] * 3, axis=-1).astype(np.uint8)


def _frame(
    frame_id: str,
    *,
    dx: int = 0,
    dy: int = 0,
    noise: float = 0.0,
    exif: dict | None = None,
) -> Frame:
    return Frame(
        frame_id=frame_id,
        path=Path("."),
        rgb=_pattern(dx=dx, dy=dy, noise=noise),
        exif=exif or {},
    )


# --- dhash / hamming_distance -----------------------------------------------


def test_dhash_near_identical_frames_have_low_hamming_distance() -> None:
    a = _frame("a")
    b = _frame("b", noise=5)  # sensor-noise-level variation, same composition
    assert hamming_distance(dhash(a), dhash(b)) <= 10


def test_dhash_a_real_reframe_has_high_hamming_distance() -> None:
    a = _frame("a")
    b = _frame("b", dx=150, dy=120)  # a genuinely different composition
    assert hamming_distance(dhash(a), dhash(b)) > 10


# --- group_near_duplicates(): the grouping engine ---------------------------


def test_f03_group_near_duplicates_groups_a_consecutive_run() -> None:
    frames = [_frame("00_a"), _frame("01_b", noise=4), _frame("02_c", noise=2)]
    groups = group_near_duplicates(frames)
    assert [f.frame_id for f in groups[0]] == ["00_a", "01_b", "02_c"]


def test_f03_group_near_duplicates_breaks_on_a_real_reframe() -> None:
    frames = [
        _frame("00_a"),
        _frame("01_b", noise=4),
        _frame("02_c", dx=150, dy=120),  # walked somewhere else
        _frame("03_d", dx=150, dy=120, noise=4),
    ]
    groups = group_near_duplicates(frames)
    assert [[f.frame_id for f in g] for g in groups] == [["00_a", "01_b"], ["02_c", "03_d"]]


def test_f03_group_near_duplicates_does_not_bridge_a_gap() -> None:
    # "consecutive" means adjacent in the batch - a duplicate of frame 0
    # showing up again at frame 2 (with something different at frame 1
    # between them) is not the same run.
    frames = [_frame("00_a"), _frame("01_b", dx=150, dy=120), _frame("02_a_again")]
    groups = group_near_duplicates(frames)
    assert groups == []


def test_f03_group_near_duplicates_caps_a_run_at_max_group_size() -> None:
    frames = [_frame(f"{i:02d}_x", noise=i) for i in range(MAX_GROUP_SIZE + 2)]
    groups = group_near_duplicates(frames)
    assert [len(g) for g in groups] == [MAX_GROUP_SIZE, 2]


def test_f03_group_near_duplicates_lone_frame_forms_no_group() -> None:
    frames = [_frame("00_a"), _frame("01_b", dx=150, dy=120), _frame("02_c", dx=-150, dy=90)]
    assert group_near_duplicates(frames) == []


# --- group_near_duplicates(): focal length / timestamp signals -------------


def test_f03_group_near_duplicates_focal_length_change_breaks_a_visual_match() -> None:
    frames = [
        _frame("00_a", exif={"FocalLength": 24.0}),
        _frame("01_b", exif={"FocalLength": 70.0}),  # zoomed - not a copy
    ]
    assert group_near_duplicates(frames) == []


def test_f03_group_near_duplicates_missing_focal_length_does_not_block_a_match() -> None:
    frames = [_frame("00_a"), _frame("01_b", noise=3)]  # no FocalLength tag at all
    groups = group_near_duplicates(frames)
    assert len(groups) == 1 and len(groups[0]) == 2


def test_f03_group_near_duplicates_large_timestamp_gap_breaks_a_visual_match() -> None:
    frames = [
        _frame("00_a", exif={"DateTimeOriginal": "2026:08:11 10:00:00"}),
        _frame("01_b", exif={"DateTimeOriginal": "2026:08:11 10:05:00"}),  # 5 min later
    ]
    assert group_near_duplicates(frames) == []


def test_f03_group_near_duplicates_close_timestamp_keeps_a_match() -> None:
    frames = [
        _frame("00_a", exif={"DateTimeOriginal": "2026:08:11 10:00:00"}),
        _frame("01_b", noise=2, exif={"DateTimeOriginal": "2026:08:11 10:00:03"}),
    ]
    groups = group_near_duplicates(frames)
    assert len(groups) == 1 and len(groups[0]) == 2


# --- detectors.f03.detect(): Finding wiring ---------------------------------


def test_f03_registered_for_its_taxonomy_id() -> None:
    assert f03.detect.__module__ == "picstory.detectors.f03"


def test_f03_detect_flags_a_frame_inside_a_duplicate_run() -> None:
    batch = [_frame("00_a"), _frame("01_b", noise=4)]
    finding = f03.detect(batch[0], batch=batch)
    assert finding is not None
    assert finding.taxonomy_id == "F03"
    assert "2" in finding.description  # names the run size somewhere


def test_f03_detect_clean_when_no_duplicate_neighbor() -> None:
    batch = [
        _frame("00_a"),
        _frame("01_b", dx=150, dy=120),
        _frame("02_c", dx=-150, dy=90),
    ]
    assert f03.detect(batch[1], batch=batch) is None


def test_f03_detect_requires_batch_context() -> None:
    with pytest.raises(ValueError):
        f03.detect(_frame("00_a"))
