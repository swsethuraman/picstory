"""F02 · Lens / grip obstruction (QUEUE.md item 3).

TAXONOMY.md detection text: "Dark, out-of-focus mass along a frame edge,
typically consistent across consecutive frames; a finger, case edge, or
strap."

Single-frame version (the "consistent across consecutive frames" half is a
batch-level cross-check, out of scope until Stage 2 has multiple frames to
compare): for each of the four edge strips (10% of the shorter side deep),
find pixels that are both dark (low luminance) and locally low-contrast
(low local variance - an obstruction pressed against or very near the lens
has no in-focus texture, unlike a dark but sharp subject like a shadowed
doorway). If a contiguous run of such pixels covers a large share of that
edge's length, that is the "mass along an edge" the taxonomy names.
"""

from __future__ import annotations

import numpy as np

from picstory.detectors._imaging import downsample, longest_true_run
from picstory.detectors.base import register
from picstory.frame import Frame
from picstory.schema import Finding

DARK_THRESHOLD = 70.0  # luminance 0-255
LOCAL_VARIANCE_THRESHOLD = 60.0  # out-of-focus: little local texture
EDGE_DEPTH_FRACTION = 0.10
RUN_COVERAGE_THRESHOLD = 0.25  # contiguous run must cover >=25% of edge length
BLOCK = 8  # local-variance window, in downsampled pixels


def _local_variance(luminance: np.ndarray) -> np.ndarray:
    """Variance within BLOCK x BLOCK tiles, broadcast back to pixel shape.

    `luminance`'s dimensions are real-photo dimensions, not guaranteed
    multiples of BLOCK. The leftover <BLOCK-pixel strip at the bottom/right
    (if any) is edge-padded from the nearest full tile's variance, so the
    output always matches `luminance`'s own shape - callers combine this
    with other full-shape arrays (e.g. `dark`) and a shape mismatch there
    would broadcast-error rather than misdetect.
    """
    h, w = luminance.shape
    h_trim, w_trim = h - (h % BLOCK), w - (w % BLOCK)
    trimmed = luminance[:h_trim, :w_trim]
    tiles = trimmed.reshape(h_trim // BLOCK, BLOCK, w_trim // BLOCK, BLOCK)
    tile_var = tiles.var(axis=(1, 3))
    variance = np.repeat(np.repeat(tile_var, BLOCK, axis=0), BLOCK, axis=1)
    pad_h, pad_w = h - h_trim, w - w_trim
    if pad_h or pad_w:
        variance = np.pad(variance, ((0, pad_h), (0, pad_w)), mode="edge")
    return variance


def _edge_obstruction_run(dark_and_flat: np.ndarray, edge: str) -> float:
    """Longest contiguous obstructed run along `edge`, as a fraction of its length."""
    depth = max(1, int(round(min(dark_and_flat.shape) * EDGE_DEPTH_FRACTION)))
    if edge == "top":
        strip = dark_and_flat[:depth, :]
    elif edge == "bottom":
        strip = dark_and_flat[-depth:, :]
    elif edge == "left":
        strip = dark_and_flat[:, :depth]
    else:  # right
        strip = dark_and_flat[:, -depth:]

    # A position along the edge is "obstructed" if most of the strip's depth
    # there is dark+flat.
    depth_axis = 0 if edge in ("top", "bottom") else 1
    obstructed_line = strip.mean(axis=depth_axis) > 0.5
    run = longest_true_run(obstructed_line)
    return run / obstructed_line.size if obstructed_line.size else 0.0


@register("F02")
def detect(frame: Frame) -> Finding | None:
    luminance = downsample(frame.luminance, max_dim=300)
    dark = luminance < DARK_THRESHOLD
    flat = _local_variance(luminance) < LOCAL_VARIANCE_THRESHOLD
    dark_and_flat = dark & flat

    coverage_by_edge = {
        edge: _edge_obstruction_run(dark_and_flat, edge)
        for edge in ("top", "bottom", "left", "right")
    }
    worst_edge, worst_coverage = max(coverage_by_edge.items(), key=lambda kv: kv[1])
    if worst_coverage < RUN_COVERAGE_THRESHOLD:
        return None

    return Finding(
        taxonomy_id="F02",
        description=(
            f"Dark, low-texture mass along the {worst_edge} edge covering "
            f"{worst_coverage:.0%} of that edge's length - consistent with a "
            "lens/grip obstruction."
        ),
    )
