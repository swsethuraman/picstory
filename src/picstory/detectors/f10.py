"""F10 · Blown highlights (QUEUE.md item 3).

TAXONOMY.md detection text: "Highlights clipped to pure white with no
recoverable detail - light sources, lit glass, bright sky reading as
featureless blobs."

Two conditions distinguish real clipping from ordinary bright pixels:

1. Clipped: near-255 in all three channels (per-channel, not just
   luminance - a saturated red channel with detail in green/blue is not
   "pure white with no recoverable detail").
2. A blob, not scattered highlights: real clipped light sources/sky/glass
   occupy a contiguous area. A handful of scattered near-white specular
   glints (chrome, water, jewelry) would pass a bare area-fraction test but
   are not "featureless blobs" - so this checks the largest *connected*
   clipped region, the same contiguity approach as F07's featureless-area
   check.
"""

from __future__ import annotations

import numpy as np

from picstory.detectors._imaging import largest_connected_area
from picstory.detectors.base import register
from picstory.frame import Frame
from picstory.schema import Finding

CLIP_LEVEL = 250  # per-channel, 0-255
GRID = 32  # tiles per side for the connected-blob check
MIN_BLOB_AREA_SHARE = 0.02


def _clipped_tile_mask(rgb: np.ndarray, grid: int) -> np.ndarray:
    clipped_pixels = np.all(rgb >= CLIP_LEVEL, axis=-1)
    h, w = clipped_pixels.shape
    th, tw = max(1, h // grid), max(1, w // grid)
    h_trim, w_trim = th * (h // th), tw * (w // tw)
    trimmed = clipped_pixels[:h_trim, :w_trim]
    tiles = trimmed.reshape(h_trim // th, th, w_trim // tw, tw)
    # A tile counts as "clipped" if most of it is clipped, so a handful of
    # scattered bright pixels crossing a tile boundary doesn't inflate area.
    return tiles.mean(axis=(1, 3)) > 0.5


@register("F10")
def detect(frame: Frame) -> Finding | None:
    tile_mask = _clipped_tile_mask(frame.rgb, GRID)
    if not tile_mask.any():
        return None

    connected_tiles = largest_connected_area(tile_mask)
    area_share = connected_tiles / tile_mask.size
    if area_share < MIN_BLOB_AREA_SHARE:
        return None

    return Finding(
        taxonomy_id="F10",
        description=(
            f"Contiguous clipped-highlight blob covers {area_share:.1%} of "
            "the frame - blown highlights with no recoverable detail."
        ),
    )
