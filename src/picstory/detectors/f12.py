"""F12 · Haze / flat contrast — registry stub.

Claims the F12 registry slot (QUEUE.md item 2). Real detection logic
(global contrast) lands in QUEUE.md item 3; until then this stub raises
DetectorNotImplemented rather than returning a silent negative - a stub
returning nothing is not an implementation (CLAUDE.md).
"""

from __future__ import annotations

from picstory.detectors.base import DetectorNotImplemented, register


@register("F12")
def detect(*_args, **_kwargs):
    raise DetectorNotImplemented(
        "F12: Haze / flat contrast detector not yet implemented (QUEUE.md item 3)"
    )
