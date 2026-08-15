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

Resolution note (QUEUE.md item 15f): unlike F02/F08/S03, this detector does
not call `_imaging.downsample` itself - it reads `sharpness_score` straight
off `frame.luminance` at whatever resolution `Frame.rgb` already is (working
resolution, per `frame.WORKING_RESOLUTION_MAX_DIM`), because downsampling
further would erase exactly the fine detail F01 is checking for softness
in. Checked directly against `WORKING_RESOLUTION_MAX_DIM`-scale synthetic
fixtures (`tests/test_frame.py`): variance-of-Laplacian is driven by local
pixel-to-pixel contrast at a texture's own pixel period, not by total image
size, so a fixed-period test pattern scores the same at 200px as at 2000px
(confirmed: ~24000 sharp / ~660 soft at both sizes) and SOFT_THRESHOLD holds
without adjustment. The real limitation this doesn't fix: `load_frame`'s
working-resolution downsample can itself anti-alias away native-resolution
texture finer than ~1-2px at working scale - detail that would have
registered as "sharp" at native resolution may simply not survive the
resize, regardless of whether the original zoom was soft. F01 can therefore
undercount digital-zoom softness on very fine native detail; it has no way
to distinguish "softened by the zoom" from "softened by our own
downsample" once both have happened. Not correctable without the
native-resolution crop escape hatch `frame.Frame.path` documents - not
exercised here, since no case demonstrating the need has arisen yet.
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
