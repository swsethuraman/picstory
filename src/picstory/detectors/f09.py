"""F09 · Underexposed subject (QUEUE.md item 3).

TAXONOMY.md detection text: "Person in the foreground a stop or more dark,
or unintentionally silhouetted, because metering favored a brighter
background (lit landmark, sky, window)."

No face detector is available locally, so "the subject" is approximated by
the center third of the frame (where a foreground person is composed in the
large majority of the source material's portrait shots) and "the
background" by the outer border ring. Luminance is converted to an
approximate linear-light scale (gamma 2.2) before comparing, since a "stop"
is a linear-light doubling, not a linear step in 8-bit gamma-encoded pixel
values. A finding requires both:

1. The background reads at least one stop brighter than the center
   (log2(background_linear / center_linear) >= STOP_THRESHOLD) - the
   "metering favored a brighter background" mechanism.
2. The center itself is actually dark in absolute terms - otherwise a
   brighter-still background (e.g. a sunny window behind a well-lit face)
   would trip this on a correctly exposed subject.
"""

from __future__ import annotations

import numpy as np

from picstory.detectors.base import register
from picstory.frame import Frame
from picstory.schema import Finding

CENTER_FRACTION = 1 / 3
STOP_THRESHOLD = 1.0
DARK_SUBJECT_LUMINANCE = 110.0  # 0-255
GAMMA = 2.2


def _to_linear(luminance_255: np.ndarray) -> np.ndarray:
    return (luminance_255 / 255.0) ** GAMMA


@register("F09")
def detect(frame: Frame) -> Finding | None:
    luminance = frame.luminance
    h, w = luminance.shape

    ch0, ch1 = int(h * (0.5 - CENTER_FRACTION / 2)), int(h * (0.5 + CENTER_FRACTION / 2))
    cw0, cw1 = int(w * (0.5 - CENTER_FRACTION / 2)), int(w * (0.5 + CENTER_FRACTION / 2))
    center = luminance[ch0:ch1, cw0:cw1]

    border_mask = np.ones_like(luminance, dtype=bool)
    border_mask[ch0:ch1, cw0:cw1] = False
    background = luminance[border_mask]

    if center.size == 0 or background.size == 0:
        return None

    center_mean = float(center.mean())
    background_mean = float(background.mean())

    if center_mean >= DARK_SUBJECT_LUMINANCE:
        return None

    center_linear = _to_linear(np.array(center_mean))
    background_linear = _to_linear(np.array(background_mean))
    eps = 1e-6
    stops = float(np.log2((background_linear + eps) / (center_linear + eps)))

    if stops < STOP_THRESHOLD:
        return None

    return Finding(
        taxonomy_id="F09",
        description=(
            f"Center region {stops:.1f} stops darker than the surrounding "
            f"frame (center luminance {center_mean:.0f}/255, background "
            f"{background_mean:.0f}/255) - underexposed subject against a "
            "brighter background."
        ),
    )
