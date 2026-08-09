"""R01 · Haze rule — registry stub.

Claims the R01 registry slot (QUEUE.md item 2). Real detection logic
(conditional rule triggered by F12 findings in a batch, not a per-frame detector) lands in QUEUE.md item 3; until then this stub raises
DetectorNotImplemented rather than returning a silent negative - a stub
returning nothing is not an implementation (CLAUDE.md).
"""

from __future__ import annotations

from picstory.detectors.base import DetectorNotImplemented, register


@register("R01")
def detect(*_args, **_kwargs):
    raise DetectorNotImplemented(
        "R01: Haze rule detector not yet implemented (QUEUE.md item 3)"
    )
