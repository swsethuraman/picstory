"""S04 · Restraint composition — registry stub.

Claims the S04 registry slot (QUEUE.md item 2). Real detection logic
(vision model call per API-discipline rule) lands in QUEUE.md item 4; until then this stub raises
DetectorNotImplemented rather than returning a silent negative - a stub
returning nothing is not an implementation (CLAUDE.md).
"""

from __future__ import annotations

from picstory.detectors.base import DetectorNotImplemented, register


@register("S04")
def detect(*_args, **_kwargs):
    raise DetectorNotImplemented(
        "S04: Restraint composition detector not yet implemented (QUEUE.md item 4)"
    )
