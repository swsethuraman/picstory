"""F12 · Haze / flat contrast (QUEUE.md item 3).

TAXONOMY.md detection text: "Low-contrast, washed-out distant subjects and
flat skies from atmospheric haze; sharpening does not help."

"Sharpening does not help" is the taxonomy's own signal that this is a
tonal/contrast problem, not a focus problem - so this detector measures
global tonal spread rather than edge sharpness (that is F01's job).
Atmospheric haze characteristically lifts blacks and compresses highlights
toward a narrow mid-gray band, so the luminance histogram's 5th-95th
percentile range is used instead of plain standard deviation: percentile
range is robust to a small saturated highlight (a lamp, a patch of sky)
that would otherwise mask an overall flat, hazy frame.
"""

from __future__ import annotations

import numpy as np

from picstory.detectors.base import register
from picstory.frame import Frame
from picstory.schema import Finding

PERCENTILE_RANGE_THRESHOLD = 110.0  # 0-255; below this reads as "flat"


@register("F12")
def detect(frame: Frame) -> Finding | None:
    luminance = frame.luminance
    p5, p95 = np.percentile(luminance, [5, 95])
    spread = float(p95 - p5)

    if spread >= PERCENTILE_RANGE_THRESHOLD:
        return None

    return Finding(
        taxonomy_id="F12",
        description=(
            f"5th-95th percentile luminance range is {spread:.0f}/255 "
            f"(< {PERCENTILE_RANGE_THRESHOLD:.0f}) - flat, washed-out "
            "contrast consistent with haze."
        ),
    )
