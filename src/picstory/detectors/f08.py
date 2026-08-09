"""F08 · Keystoning from tilting up — registry stub.

Claims the F08 registry slot (QUEUE.md item 2). Real detection logic
(vertical-line convergence) lands in QUEUE.md item 3; until then this stub raises
DetectorNotImplemented rather than returning a silent negative - a stub
returning nothing is not an implementation (CLAUDE.md).
"""

from __future__ import annotations

from picstory.detectors.base import DetectorNotImplemented, register


@register("F08")
def detect(*_args, **_kwargs):
    raise DetectorNotImplemented(
        "F08: Keystoning from tilting up detector not yet implemented (QUEUE.md item 3)"
    )
