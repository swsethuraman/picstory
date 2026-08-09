"""F02 · Lens / grip obstruction — registry stub.

Claims the F02 registry slot (QUEUE.md item 2). Real detection logic
(dark defocused edge mass) lands in QUEUE.md item 3; until then this stub raises
DetectorNotImplemented rather than returning a silent negative - a stub
returning nothing is not an implementation (CLAUDE.md).
"""

from __future__ import annotations

from picstory.detectors.base import DetectorNotImplemented, register


@register("F02")
def detect(*_args, **_kwargs):
    raise DetectorNotImplemented(
        "F02: Lens / grip obstruction detector not yet implemented (QUEUE.md item 3)"
    )
