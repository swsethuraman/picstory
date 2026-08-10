"""Behavior tests for the QUEUE.md item 3 local detectors: F01, F02, F07,
F08, F09, F10, F12.

Each ID gets a positive case (the described failure is present, a Finding
comes back naming that ID) and a negative case (a clean frame, None comes
back) built from synthetic pixel arrays - no real photos needed for pixel-
computable, deterministic detectors. F01 additionally checks the EXIF
extraction path end-to-end through a real (tiny, in-memory-written) image
file, since that wiring (frame.load_frame -> Frame.exif) isn't otherwise
exercised by pure-array tests.

Naming matches tests/test_taxonomy_coverage.py's convention
(`test_<id>_...`) so these count toward that guard's per-ID test coverage.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from PIL import Image

from pathlib import Path

from picstory import detectors
from picstory.frame import Frame, load_frame


def _frame(rgb: np.ndarray, exif: dict | None = None, frame_id: str = "t") -> Frame:
    return Frame(frame_id=frame_id, path=Path("."), rgb=rgb.astype(np.uint8), exif=exif or {})


def _checkerboard_gray(size: int = 200, block: int = 8) -> np.ndarray:
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


def _uniform_noise(size: int = 200, mean: float = 140.0, spread: float = 60.0) -> np.ndarray:
    rng = np.random.default_rng(1)
    val = np.clip(rng.normal(mean, spread, size=(size, size)), 0, 255)
    return np.stack([val, val, val], axis=-1).astype(np.uint8)


# --- F01: digital-zoom softness ---------------------------------------


def test_f01_digital_zoom_softness_flags_soft_zoomed_frame() -> None:
    soft = _box_blur(_checkerboard_gray())
    frame = _frame(_rgb3(soft), exif={"DigitalZoomRatio": 2.5})
    finding = detectors.get("F01")(frame)
    assert finding is not None
    assert finding.taxonomy_id == "F01"


def test_f01_digital_zoom_softness_clean_when_no_zoom_metadata() -> None:
    soft = _box_blur(_checkerboard_gray())
    frame = _frame(_rgb3(soft), exif={})
    assert detectors.get("F01")(frame) is None


def test_f01_digital_zoom_softness_clean_when_sharp() -> None:
    frame = _frame(_rgb3(_checkerboard_gray()), exif={"DigitalZoomRatio": 2.5})
    assert detectors.get("F01")(frame) is None


def test_f01_digital_zoom_softness_reads_exif_from_real_file(tmp_path) -> None:
    path = tmp_path / "zoomed.jpg"
    soft = _box_blur(_checkerboard_gray()).astype(np.uint8)
    Image.fromarray(_rgb3(soft).astype(np.uint8)).save(
        path, exif=Image.Exif()  # no DigitalZoomRatio tag on this path
    )
    frame = load_frame(path)
    assert frame.exif.get("DigitalZoomRatio") is None
    assert detectors.get("F01")(frame) is None


# --- F02: lens / grip obstruction ---------------------------------------


def _rgb3(gray: np.ndarray) -> np.ndarray:
    return np.stack([gray, gray, gray], axis=-1)


def test_f02_lens_grip_obstruction_flags_dark_flat_edge_mass() -> None:
    gray = _uniform_noise(mean=170, spread=50)[..., 0]
    gray[:, -30:] = 20  # dark, flat mass along the right edge
    finding = detectors.get("F02")(_frame(_rgb3(gray)))
    assert finding is not None
    assert finding.taxonomy_id == "F02"
    assert "right" in finding.description


def test_f02_lens_grip_obstruction_clean_on_uniformly_detailed_frame() -> None:
    gray = _uniform_noise(mean=140, spread=60)[..., 0]
    assert detectors.get("F02")(_frame(_rgb3(gray))) is None


def test_f02_lens_grip_obstruction_handles_dimensions_not_divisible_by_block() -> None:
    # Regression: real photo dimensions are rarely exact multiples of the
    # local-variance BLOCK size (8). _local_variance used to return an
    # array trimmed to the nearest multiple, which broadcast-errored
    # against the untrimmed `dark` mask for any such size - e.g. 300x300
    # (300 % 8 == 4). Every prior test used 200x200 (200 % 8 == 0), which
    # never exercised this path. Regression, not a detection-outcome test:
    # this only asserts the detector runs to completion.
    gray = _uniform_noise(size=203, mean=170, spread=50)[..., 0]
    gray[:, -30:] = 20  # dark, flat mass along the right edge
    finding = detectors.get("F02")(_frame(_rgb3(gray)))
    assert finding is not None
    assert finding.taxonomy_id == "F02"


# --- F07: empty-space overallocation ------------------------------------


def test_f07_empty_space_overallocation_flags_large_flat_block() -> None:
    gray = _uniform_noise(size=200, mean=140, spread=60)[..., 0]
    gray[:90, :] = 210  # top ~40% of rows: flat "sky"
    finding = detectors.get("F07")(_frame(_rgb3(gray)))
    assert finding is not None
    assert finding.taxonomy_id == "F07"


def test_f07_empty_space_overallocation_clean_on_fully_textured_frame() -> None:
    gray = _uniform_noise(size=200, mean=140, spread=60)[..., 0]
    assert detectors.get("F07")(_frame(_rgb3(gray))) is None


# --- F08: keystoning from tilting up -------------------------------------


def _two_edge_image(angle_left_deg: float, angle_right_deg: float, size: int = 300) -> np.ndarray:
    y = np.arange(size).reshape(-1, 1).astype(np.float64)
    x = np.arange(size).reshape(1, -1).astype(np.float64)
    cy = size / 2
    img = np.full((size, size), 180.0)
    for cx_line, angle in ((size * 0.25, angle_left_deg), (size * 0.75, angle_right_deg)):
        theta = math.radians(angle)
        boundary_x = cx_line + (y - cy) * math.tan(theta)
        img = img + (255 / (1 + np.exp(-(x - boundary_x))) - 127.5) * 0.5
    return np.clip(img, 0, 255).astype(np.uint8)


def test_f08_keystoning_flags_converging_verticals() -> None:
    gray = _two_edge_image(angle_left_deg=-15, angle_right_deg=15)
    finding = detectors.get("F08")(_frame(_rgb3(gray)))
    assert finding is not None
    assert finding.taxonomy_id == "F08"


def test_f08_keystoning_clean_on_parallel_verticals() -> None:
    gray = _two_edge_image(angle_left_deg=0, angle_right_deg=0)
    assert detectors.get("F08")(_frame(_rgb3(gray))) is None


def test_f08_keystoning_clean_on_uniform_roll_not_convergence() -> None:
    # Both lines tilt the same direction by the same amount - a level/roll
    # problem, not perspective convergence. Must not be flagged as F08.
    gray = _two_edge_image(angle_left_deg=10, angle_right_deg=10)
    assert detectors.get("F08")(_frame(_rgb3(gray))) is None


# --- F09: underexposed subject -------------------------------------------


def test_f09_underexposed_subject_flags_dark_center_bright_background() -> None:
    gray = np.full((180, 180), 220.0)
    gray[60:120, 60:120] = 40.0  # dark center third against a bright background
    finding = detectors.get("F09")(_frame(_rgb3(gray)))
    assert finding is not None
    assert finding.taxonomy_id == "F09"


def test_f09_underexposed_subject_clean_on_evenly_lit_frame() -> None:
    gray = np.full((180, 180), 150.0)
    assert detectors.get("F09")(_frame(_rgb3(gray))) is None


# --- F10: blown highlights -------------------------------------------


def test_f10_blown_highlights_flags_contiguous_clipped_blob() -> None:
    gray = np.full((200, 200), 120, dtype=np.uint8)
    gray[:60, :60] = 255  # a contiguous blown-out corner (a window, a lamp)
    finding = detectors.get("F10")(_frame(_rgb3(gray)))
    assert finding is not None
    assert finding.taxonomy_id == "F10"


def test_f10_blown_highlights_clean_on_scattered_specular_glints() -> None:
    gray = np.full((200, 200), 120, dtype=np.uint8)
    rng = np.random.default_rng(2)
    ys = rng.integers(0, 200, size=15)
    xs = rng.integers(0, 200, size=15)
    gray[ys, xs] = 255  # isolated glints, not a blob
    assert detectors.get("F10")(_frame(_rgb3(gray))) is None


# --- F12: haze / flat contrast -------------------------------------------


def test_f12_haze_flat_contrast_flags_narrow_luminance_range() -> None:
    gray = np.clip(np.random.default_rng(3).normal(150, 8, size=(150, 150)), 0, 255)
    assert detectors.get("F12")(_frame(_rgb3(gray))) is not None


def test_f12_haze_flat_contrast_clean_on_full_range_frame() -> None:
    gray = np.zeros((150, 150))
    gray[:, :75] = 10
    gray[:, 75:] = 245
    assert detectors.get("F12")(_frame(_rgb3(gray))) is None


def test_all_local_detector_ids_are_registered() -> None:
    for taxonomy_id in ("F01", "F02", "F07", "F08", "F09", "F10", "F12"):
        assert taxonomy_id in detectors.registered_ids()
        with pytest.raises(TypeError):
            # These now require a Frame argument - calling with none is a
            # TypeError, not the old DetectorNotImplemented stub signal.
            detectors.get(taxonomy_id)()
