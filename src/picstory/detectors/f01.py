"""F01 · Digital-zoom softness — registry stub.

Claims the F01 registry slot (QUEUE.md item 2). Real detection logic
(EXIF focal length vs optical steps + sharpness) lands in QUEUE.md item 3; until then this stub raises
DetectorNotImplemented rather than returning a silent negative - a stub
returning nothing is not an implementation (CLAUDE.md).
"""

from __future__ import annotations

from picstory.detectors.base import DetectorNotImplemented, register


@register("F01")
def detect(*_args, **_kwargs):
    raise DetectorNotImplemented(
        "F01: Digital-zoom softness detector not yet implemented (QUEUE.md item 3)"
    )
