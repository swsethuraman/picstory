"""Behavior tests for S03 (DECISIONS.md D-007): tight framing.

Like F03, S03 is batch-level - `picstory.detectors.s03.detect(frames)` takes
an ordered list of Frames, not one Frame - so these tests build small
synthetic batches rather than single frames (test_local_detectors.py's
pattern doesn't apply here). Two independent pieces get their own fixture
style, matching how each is actually computed:

- `subject_clusters.group_subject_clusters`: reuses F03's own checkerboard +
  moving-block scene generator (`_scene`, copied from
  test_f03_safety_copies.py) so this threshold is calibrated directly
  against F03's, per subject_clusters.py's own docstring reasoning.
- `s03.detect`'s framing-tightness ranking: a flat background with a single
  textured "subject" block of varying size, since `_imaging.sharp_area_fraction`
  is a contiguous-in-focus-area measure, not a structural-similarity one -
  F03's checkerboard scene has no well-behaved "bigger sharp region"
  gradient to rank frames by.

Naming matches tests/test_taxonomy_coverage.py's convention (`test_s03_...`)
so these count toward that guard's per-ID test coverage.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from picstory import detectors
from picstory.detectors import s03, subject_clusters
from picstory.frame import Frame


def _scene(offset: int = 0, size: int = 200, block: int = 8) -> np.ndarray:
    """A textured checkerboard with a bright "subject" block at `offset` (copied from F03's own)."""
    yy, xx = np.mgrid[0:size, 0:size]
    gray = (((xx // block) + (yy // block)) % 2 * 180 + 30).astype(np.float64)
    x0 = 40 + offset
    gray[80:160, x0 : x0 + 60] = 255.0
    return gray


def _frame(gray: np.ndarray, frame_id: str, exif: dict | None = None) -> Frame:
    rgb = np.stack([gray, gray, gray], axis=-1).astype(np.uint8)
    return Frame(frame_id=frame_id, path=Path("."), rgb=rgb, exif=exif or {})


def _tight_scene(subject_size: int, size: int = 200, bg: float = 100.0) -> np.ndarray:
    """A flat background with a single finely-textured (sharp) square "subject."

    Larger `subject_size` reads as a tighter frame - more of the composition
    given to the in-focus subject, less flat background left around it -
    the case `_imaging.sharp_area_fraction` is meant to rank.
    """
    gray = np.full((size, size), bg, dtype=np.float64)
    x0 = y0 = size // 2 - subject_size // 2
    syy, sxx = np.mgrid[0:subject_size, 0:subject_size]
    gray[y0 : y0 + subject_size, x0 : x0 + subject_size] = (
        ((sxx // 2) + (syy // 2)) % 2 * 200 + 20
    ).astype(np.float64)
    return gray


# --- group_subject_clusters(): looser than F03, no EXIF gates --------------


def test_s03_subject_clusters_admits_a_shift_f03_would_reject() -> None:
    # offset=30 (15% of frame width) scores 14 on the dHash Hamming distance
    # - already above F03's own HASH_DISTANCE_THRESHOLD (6), so F03 would
    # call this "a real variation," not a copy. S03 wants exactly this case:
    # a different attempt/angle at the same subject.
    frames = [_frame(_scene(0), "00_a"), _frame(_scene(30), "01_b")]

    groups = subject_clusters.group_subject_clusters(frames)

    assert groups == [["00_a", "01_b"]]


def test_s03_subject_clusters_rejects_a_clearly_different_scene() -> None:
    # offset=100 (50% of frame width) scores 20 - well past
    # HASH_DISTANCE_THRESHOLD (15), a clearly different composition rather
    # than another attempt at the same shot.
    frames = [_frame(_scene(0), "00_a"), _frame(_scene(100), "01_b")]

    assert subject_clusters.group_subject_clusters(frames) == []


def test_s03_subject_clusters_no_chaining_through_an_intermediate_frame() -> None:
    # 0-30 clusters (14) and 30-100 sits just above threshold (16 > 15), so
    # this must not transitively chain 0 and 100 together through 30 -
    # exactly the chain-similarity risk subject_clusters.py's docstring
    # discloses (and critic-003 flagged for F03's own pairwise grouping).
    frames = [_frame(_scene(0), "00_a"), _frame(_scene(30), "01_b"), _frame(_scene(100), "02_c")]

    groups = subject_clusters.group_subject_clusters(frames)

    assert groups == [["00_a", "01_b"]]


def test_s03_subject_clusters_ignores_focal_length_unlike_f03() -> None:
    base = _scene(0)
    frames = [
        _frame(base, "00_a", exif={"FocalLength": 24.0}),
        _frame(base, "01_b", exif={"FocalLength": 85.0}),
    ]

    assert subject_clusters.group_subject_clusters(frames) == [["00_a", "01_b"]]


def test_s03_subject_clusters_ignores_timestamp_gap_unlike_f03() -> None:
    base = _scene(0)
    frames = [
        _frame(base, "00_a", exif={"DateTimeOriginal": "2026:08:11 10:00:00"}),
        _frame(base, "01_b", exif={"DateTimeOriginal": "2026:08:11 14:30:00"}),
    ]

    assert subject_clusters.group_subject_clusters(frames) == [["00_a", "01_b"]]


def test_s03_subject_clusters_no_group_below_two_frames() -> None:
    assert subject_clusters.group_subject_clusters([_frame(_scene(0), "00_a")]) == []


def test_s03_subject_clusters_non_adjacent_frames_can_still_cluster() -> None:
    # Unlike F03's pairwise-*consecutive* grouping, a subject cluster is not
    # restricted to adjacency: an unrelated frame shot in between two
    # attempts at the same subject must not break the pairing.
    frames = [
        _frame(_scene(0), "00_a"),
        _frame(_scene(100), "01_between"),
        _frame(_scene(30), "02_c"),
    ]

    groups = subject_clusters.group_subject_clusters(frames)

    assert groups == [["00_a", "02_c"]]


# --- detect(): tightest frame in each cluster gets the Finding -------------


def test_s03_tight_framing_winner_is_the_largest_sharp_area_in_its_cluster() -> None:
    frames = [
        _frame(_tight_scene(40), "00_loose"),
        _frame(_tight_scene(90), "01_tight"),
    ]

    findings = s03.detect(frames)

    assert set(findings) == {"01_tight"}
    finding = findings["01_tight"]
    assert finding.taxonomy_id == "S03"
    assert "2 batch-mates" in finding.description


def test_s03_tight_framing_ranks_three_way_cluster_correctly() -> None:
    frames = [
        _frame(_tight_scene(40), "00_loose"),
        _frame(_tight_scene(110), "01_tightest"),
        _frame(_tight_scene(90), "02_mid"),
    ]

    findings = s03.detect(frames)

    assert set(findings) == {"01_tightest"}


def test_s03_tight_framing_no_finding_for_a_frame_with_no_batch_mate() -> None:
    frames = [_frame(_tight_scene(90), "00_a"), _frame(_scene(100), "01_unrelated")]

    assert s03.detect(frames) == {}


def test_s03_tight_framing_empty_batch() -> None:
    assert s03.detect([]) == {}


# --- registration ------------------------------------------------------


def test_s03_tight_framing_registered_in_detector_registry() -> None:
    assert detectors.get("S03") is s03.detect
