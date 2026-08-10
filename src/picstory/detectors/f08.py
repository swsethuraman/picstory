"""F08 · Keystoning from tilting up (QUEUE.md item 3).

TAXONOMY.md detection text: "Vertical structures visibly leaning; parallel
lines converging upward; worst on tight crops of tall subjects shot from
below."

Keystoning's signature is specifically *convergence*, not just tilt: a line
left of center leans toward the frame's vertical centerline as it goes up,
and a line right of center leans the opposite way, toward the same
centerline - i.e. each edge's lean angle depends on its horizontal position.
A rotated/unlevel camera (roll) also tilts every vertical line, but by the
*same* angle regardless of x-position - that is a level problem, not
keystoning, and this detector is built to tell the two apart:

1. Sobel gradients -> per-pixel edge orientation, expressed as the edge's
   tilt from true vertical (0 deg = vertical, signed).
2. Keep near-vertical edge pixels only (|tilt| < NEAR_VERTICAL_LIMIT_DEG),
   dropping mostly-horizontal edges (window ledges, horizon, etc).
3. Linear regression of tilt angle against normalized x-position
   (-1 at the left edge, +1 at the right). A uniform lean (roll) gives a
   near-zero slope with a nonzero intercept; convergence gives a positive
   slope (see module docstring sign convention below) with the intercept
   near the lean at the center column.

Sign convention pinned by `frame/f08` calibration script: with this
gradient-to-tangent formula, a boundary whose top sits left of its bottom
reads as a *positive* angle. Two lines converging toward a point above
frame-center (true keystoning) therefore produce a *positive* regression
slope: the left line's top leans right/toward-center (negative angle) and
the right line's top leans left/toward-center (positive angle), so angle
increases with x. A negative slope is the opposite pattern (divergence /
reverse keystoning) and is not flagged - it is not what F08 describes.
"""

from __future__ import annotations

import numpy as np

from picstory.detectors._imaging import downsample, sobel_gradients
from picstory.detectors.base import register
from picstory.frame import Frame
from picstory.schema import Finding

NEAR_VERTICAL_LIMIT_DEG = 40.0
MIN_EDGE_PIXELS = 200
SLOPE_THRESHOLD = 8.0  # degrees of tilt per unit normalized x (center to edge)
MIN_CORRELATION = 0.3  # |r| - guards against a noisy few-point regression


def _wrap_to_90(angle_deg: np.ndarray) -> np.ndarray:
    return ((angle_deg + 90.0) % 180.0) - 90.0


@register("F08")
def detect(frame: Frame) -> Finding | None:
    luminance = downsample(frame.luminance, max_dim=400)
    height, width = luminance.shape
    gx, gy = sobel_gradients(luminance)
    magnitude = np.sqrt(gx**2 + gy**2)

    if magnitude.max() <= 0:
        return None
    strong = magnitude > (magnitude.max() * 0.3)
    if strong.sum() < MIN_EDGE_PIXELS:
        return None

    ys, xs = np.nonzero(strong)
    tangent_x = -gy[strong]
    tangent_y = gx[strong]
    tilt = _wrap_to_90(np.degrees(np.arctan2(tangent_x, tangent_y)))

    near_vertical = np.abs(tilt) < NEAR_VERTICAL_LIMIT_DEG
    if near_vertical.sum() < MIN_EDGE_PIXELS:
        return None

    x_norm = (xs[near_vertical] - width / 2) / (width / 2)
    angle = tilt[near_vertical]

    correlation = np.corrcoef(x_norm, angle)[0, 1] if np.std(x_norm) > 0 else 0.0
    design = np.vstack([x_norm, np.ones_like(x_norm)]).T
    slope, intercept = np.linalg.lstsq(design, angle, rcond=None)[0]

    if slope < SLOPE_THRESHOLD or correlation < MIN_CORRELATION:
        return None

    return Finding(
        taxonomy_id="F08",
        description=(
            f"Near-vertical edges converge with tilt-vs-position slope "
            f"{slope:.1f} deg (r={correlation:.2f}, center tilt "
            f"{intercept:.1f} deg) - consistent with keystoning from "
            "tilting the camera up."
        ),
    )
