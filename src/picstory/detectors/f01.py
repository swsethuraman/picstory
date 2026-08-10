"""F01 · Digital-zoom softness (QUEUE.md item 3).

TAXONOMY.md detection text: "Fine detail (stonework, texture, edges) visibly
soft in tight frames; focal length metadata or rendering consistent with
digital zoom beyond the device's optical steps."

Two signals, both required, mirroring that "focal length metadata AND
softness" reading (metadata alone doesn't mean the shot came out soft;
softness alone doesn't mean it came from zoom - could be motion blur, missed
focus, or an intentionally soft look):

1. Metadata: the EXIF `DigitalZoomRatio` tag (written by the camera/phone
   itself when it upsamples past the last optical step) is present and > 1.0.
   This is the literal metadata signal the taxonomy item names - not a
   focal-length-vs-device-database guess, which would need a lens database
   this project doesn't have.
2. Rendering: variance of the Laplacian (a standard sharpness proxy - see
   `_imaging.sharpness_score`) over the frame is below `SOFT_THRESHOLD`,
   i.e. fine detail is in fact rendering soft.

If `DigitalZoomRatio` is absent from EXIF, the metadata signal can't be
evaluated at all - this detector returns no finding rather than guessing
from softness alone, since a soft photo with no zoom metadata is equally
consistent with several other failure modes this taxonomy tracks separately.
"""

from __future__ import annotations

from picstory.detectors._imaging import sharpness_score
from picstory.detectors.base import register
from picstory.frame import Frame
from picstory.schema import Finding

# Calibrated against _imaging.sharpness_score on synthetic fixtures: a sharp
# high-frequency checkerboard scores ~3.9e4, the same pattern box-blurred
# scores ~8, natural-detail noise ~8e3, its blurred counterpart ~0.01. This
# threshold sits far below "has detail" and well above "blurred," so it is
# not sensitive to the exact choice within that gap.
SOFT_THRESHOLD = 150.0


@register("F01")
def detect(frame: Frame) -> Finding | None:
    zoom_ratio = frame.exif.get("DigitalZoomRatio")
    if zoom_ratio is None:
        return None
    try:
        zoom_ratio = float(zoom_ratio)
    except (TypeError, ValueError):
        return None
    if zoom_ratio <= 1.0:
        return None

    score = sharpness_score(frame.luminance)
    if score >= SOFT_THRESHOLD:
        return None

    return Finding(
        taxonomy_id="F01",
        description=(
            f"DigitalZoomRatio={zoom_ratio:.2f} with sharpness score "
            f"{score:.1f} (< {SOFT_THRESHOLD:.0f}) - soft detail consistent "
            "with digital zoom beyond the optical steps."
        ),
    )
