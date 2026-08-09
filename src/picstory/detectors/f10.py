"""F10 · Blown highlights — registry stub.

Claims the F10 registry slot (QUEUE.md item 2). Real detection logic
(exposure histogram, face-region vs background) lands in QUEUE.md item 3; until then this stub raises
DetectorNotImplemented rather than returning a silent negative - a stub
returning nothing is not an implementation (CLAUDE.md).
"""

from __future__ import annotations

from picstory.detectors.base import DetectorNotImplemented, register


@register("F10")
def detect(*_args, **_kwargs):
    raise DetectorNotImplemented(
        "F10: Blown highlights detector not yet implemented (QUEUE.md item 3)"
    )
