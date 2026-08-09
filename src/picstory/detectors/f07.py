"""F07 · Empty-space overallocation — registry stub.

Claims the F07 registry slot (QUEUE.md item 2). Real detection logic
(featureless-region area share) lands in QUEUE.md item 3; until then this stub raises
DetectorNotImplemented rather than returning a silent negative - a stub
returning nothing is not an implementation (CLAUDE.md).
"""

from __future__ import annotations

from picstory.detectors.base import DetectorNotImplemented, register


@register("F07")
def detect(*_args, **_kwargs):
    raise DetectorNotImplemented(
        "F07: Empty-space overallocation detector not yet implemented (QUEUE.md item 3)"
    )
