"""F07 · Empty-space overallocation (QUEUE.md item 3).

TAXONOMY.md detection text: "30-50% of the frame given to featureless area -
blank sky, dead pavement, empty floor - with no compositional role."

Implementation: tile the frame into a coarse grid, mark each tile
"featureless" if its local luminance variance is low (no texture - sky,
smooth pavement, a blank wall), then find the largest single *contiguous*
featureless region. Contiguity matters: a scene can easily have 30%+ of its
pixels individually low-variance while scattered across many small patches
(shadow pockets, out-of-focus background bits) with no single dead zone -
that is not what "30-50% given to featureless area" describes. The area
share is measured against the largest connected block, not the flat-pixel
total.
"""

from __future__ import annotations

import numpy as np

from picstory.detectors._imaging import largest_connected_area
from picstory.detectors.base import register
from picstory.frame import Frame
from picstory.schema import Finding

GRID = 24  # tiles per side (approx) for the featureless-region grid
VARIANCE_THRESHOLD = 45.0  # per-tile luminance variance below this = featureless
MIN_AREA_SHARE = 0.30
MAX_AREA_SHARE = 0.85  # above this the frame is essentially blank, not "overallocated"


def _tile_variances(luminance: np.ndarray, grid: int) -> np.ndarray:
    h, w = luminance.shape
    th, tw = max(1, h // grid), max(1, w // grid)
    h_trim, w_trim = th * (h // th), tw * (w // tw)
    trimmed = luminance[:h_trim, :w_trim]
    tiles = trimmed.reshape(h_trim // th, th, w_trim // tw, tw)
    return tiles.var(axis=(1, 3))


@register("F07")
def detect(frame: Frame) -> Finding | None:
    variances = _tile_variances(frame.luminance, GRID)
    featureless = variances < VARIANCE_THRESHOLD
    if not featureless.any():
        return None

    connected_tiles = largest_connected_area(featureless)
    area_share = connected_tiles / featureless.size
    if not (MIN_AREA_SHARE <= area_share <= MAX_AREA_SHARE):
        return None

    return Finding(
        taxonomy_id="F07",
        description=(
            f"Largest contiguous featureless region covers {area_share:.0%} "
            "of the frame - empty-space overallocation."
        ),
    )
