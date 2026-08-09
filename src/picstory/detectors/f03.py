"""F03 · Safety copies — registry stub.

Claims the F03 registry slot (QUEUE.md item 2). Real detection logic
(near-duplicate grouping across consecutive frames) lands in QUEUE.md item 8; until then this stub raises
DetectorNotImplemented rather than returning a silent negative - a stub
returning nothing is not an implementation (CLAUDE.md).
"""

from __future__ import annotations

from picstory.detectors.base import DetectorNotImplemented, register


@register("F03")
def detect(*_args, **_kwargs):
    raise DetectorNotImplemented(
        "F03: Safety copies detector not yet implemented (QUEUE.md item 8)"
    )
