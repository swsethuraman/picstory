"""Regression tests for QUEUE.md item 15, the resolution contract.

`test_local_detectors.py`/`test_f03_safety_copies.py`/etc. all build `Frame`
objects directly from small (<=200px) synthetic arrays, never through
`load_frame` at a size anywhere near a real photo's - which is exactly why
266 green tests never caught the capstone's non-terminating full-resolution
run (see `frame.py`'s module docstring). These tests exercise `load_frame`
itself at a realistic (well above `WORKING_RESOLUTION_MAX_DIM`) scale.
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from PIL import Image

from picstory import detectors
from picstory.frame import WORKING_RESOLUTION_MAX_DIM, Frame, load_frame


def _write_large_photo(path, width: int, height: int) -> None:
    """A large but cheap-to-encode synthetic photo (gradient, not noise)."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    arr[:, :, 0] = np.linspace(0, 255, width, dtype=np.uint8)[None, :]
    arr[:, :, 1] = np.linspace(0, 255, height, dtype=np.uint8)[:, None]
    arr[:, :, 2] = 96
    exif = Image.Exif()
    exif[271] = "TestCam"  # 271 = "Make", a top-level IFD tag
    Image.fromarray(arr).save(path, quality=85, exif=exif)


# --- load_frame(): the working-resolution contract (item 15a) -------------


def test_load_frame_downsamples_an_8000x6000_photo_to_working_resolution(tmp_path) -> None:
    path = tmp_path / "native.jpg"
    _write_large_photo(path, width=8000, height=6000)

    frame = load_frame(path)

    assert max(frame.width, frame.height) == WORKING_RESOLUTION_MAX_DIM
    # 8000x6000 is 4:3 - the downsample preserves aspect ratio exactly.
    assert frame.width == WORKING_RESOLUTION_MAX_DIM
    assert frame.height == round(6000 * (WORKING_RESOLUTION_MAX_DIM / 8000))


def test_load_frame_leaves_a_small_photo_alone(tmp_path) -> None:
    path = tmp_path / "small.jpg"
    _write_large_photo(path, width=400, height=300)

    frame = load_frame(path)

    assert (frame.width, frame.height) == (400, 300)


def test_load_frame_reads_exif_from_the_original_before_resizing(tmp_path) -> None:
    path = tmp_path / "native.jpg"
    _write_large_photo(path, width=8000, height=6000)

    frame = load_frame(path)

    # Confirms EXIF is read off the original file, not lost/altered by the
    # working-resolution resize (frame.py's docstring: "EXIF is read from
    # the original file before any resize").
    assert frame.exif.get("Make") == "TestCam"
    assert max(frame.width, frame.height) == WORKING_RESOLUTION_MAX_DIM


# --- Frame: cached luminance / memoized hashes (item 15b) ------------------


def _frame(width: int = 2000, height: int = 1500) -> Frame:
    from pathlib import Path

    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[:, :, 0] = np.linspace(0, 255, width, dtype=np.uint8)[None, :]
    return Frame(frame_id="t", path=Path("."), rgb=rgb, exif={})


def test_luminance_is_cached_across_accesses() -> None:
    frame = _frame()
    first = frame.luminance
    second = frame.luminance
    assert first is second  # same array object, not recomputed


def test_dhash_is_memoized_per_hash_size() -> None:
    frame = _frame()
    first = frame.dhash(hash_size=8)
    second = frame.dhash(hash_size=8)
    assert first is second  # cached, not recomputed

    other_size = frame.dhash(hash_size=4)
    assert other_size is not first
    assert other_size.shape != first.shape


# --- F01's SOFT_THRESHOLD holds at working resolution (item 15f) ----------
# Same synthetic-pattern shape test_local_detectors.py already uses for F01
# at 200px (checkerboard vs. box-blurred checkerboard), reused at
# WORKING_RESOLUTION_MAX_DIM scale - the evidence f01.py's own "Resolution
# note" docstring cites for SOFT_THRESHOLD holding without adjustment.


def _checkerboard(size: int, block: int = 8) -> np.ndarray:
    yy, xx = np.mgrid[0:size, 0:size]
    return (((xx // block) + (yy // block)) % 2 * 255).astype(np.float64)


def _box_blur(img: np.ndarray, k: int = 5, iters: int = 8) -> np.ndarray:
    out = img.astype(np.float64)
    pad = k // 2
    for _ in range(iters):
        padded = np.pad(out, pad, mode="edge")
        acc = np.zeros_like(out)
        for dy in range(k):
            for dx in range(k):
                acc += padded[dy : dy + out.shape[0], dx : dx + out.shape[1]]
        out = acc / (k * k)
    return out


def _rgb3(gray: np.ndarray) -> np.ndarray:
    return np.stack([gray, gray, gray], axis=-1)


def _f01_frame(gray: np.ndarray) -> Frame:
    from pathlib import Path

    return Frame(
        frame_id="t",
        path=Path("."),
        rgb=_rgb3(gray).astype(np.uint8),
        exif={"DigitalZoomRatio": 2.5},
    )


def test_f01_discriminates_sharp_from_soft_at_working_resolution() -> None:
    size = WORKING_RESOLUTION_MAX_DIM
    sharp = _checkerboard(size)
    soft = _box_blur(_checkerboard(size))

    detect = detectors.get("F01")
    assert detect(_f01_frame(sharp)) is None  # sharp, no finding
    finding = detect(_f01_frame(soft))
    assert finding is not None
    assert finding.taxonomy_id == "F01"


# --- End-to-end: a realistic-scale batch stays fast (item 15e) ------------


def test_five_large_frames_load_and_analyze_within_a_time_budget(tmp_path) -> None:
    """A timing-bounded, offline, 5-frame end-to-end run at realistic scale.

    This is the regression the capstone actually hit: real iPhone frames
    (~4000-8000px) made the pipeline effectively non-terminating (docs/
    capstone-vienna-report.md), invisible to every other test because every
    other fixture is <=200px. `tests/conftest.py`'s autouse
    `_block_live_anthropic_calls` fixture keeps this offline (CLAUDE.md: the
    suite never makes live calls) - the budget below covers local decode/
    downsample/hash/detect work only, not real network latency.
    """
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import analyze_batch  # noqa: E402 - path-dependent import, mirrors other test files
    from picstory.batch import load_batch  # noqa: E402

    paths = []
    for i in range(5):
        path = tmp_path / f"photo{i}.jpg"
        # Distinct per-frame content (index-shifted gradient) so this isn't
        # trivially one giant near-duplicate run - closer to a real batch.
        arr = np.zeros((3000, 4000, 3), dtype=np.uint8)
        arr[:, :, 0] = np.roll(np.linspace(0, 255, 4000, dtype=np.uint8), i * 200)[None, :]
        arr[:, :, 1] = np.linspace(0, 255, 3000, dtype=np.uint8)[:, None]
        arr[:, :, 2] = 64 + i * 20
        Image.fromarray(arr).save(path, quality=85)
        paths.append(path)

    started = time.monotonic()
    frames = load_batch(paths)
    for frame in frames:
        assert max(frame.width, frame.height) == WORKING_RESOLUTION_MAX_DIM

    output, runs_by_frame, comparison_runs = analyze_batch.run_batch_analysis(frames)
    elapsed = time.monotonic() - started

    assert len(output.frames) == 5
    assert elapsed < 30.0, (
        f"5-frame batch at realistic scale took {elapsed:.1f}s - the capstone's "
        "non-terminating run (docs/capstone-vienna-report.md) looked exactly "
        "like this before the resolution contract (QUEUE.md item 15)"
    )
