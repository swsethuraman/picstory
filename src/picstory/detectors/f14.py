"""F14 · Wide-shot monoculture — registry stub, deferred (DECISIONS.md D-005).

Claims the F14 registry slot (QUEUE.md item 2). QUEUE.md item 4 groups F14
with the single-frame API-vision detectors, but its Detection text - "A
location's coverage is all establishing views" - is a property of a set of
frames from one location, not of any single frame: no photo, however wide,
is "monoculture" on its own. Stage 1 (this queue item) processes one photo
at a time, so honestly implementing F14 needs the batch/location grouping
that doesn't exist until Stage 2. See DECISIONS.md D-005. This stub still
raises DetectorNotImplemented rather than returning a silent negative or a
single-frame substitute - a stub returning nothing is not an implementation,
and a per-frame guess at a batch-level condition would be the substitute
PREDICTION.md names (CLAUDE.md).
"""

from __future__ import annotations

from picstory.detectors.base import DetectorNotImplemented, register


@register("F14")
def detect(*_args, **_kwargs):
    raise DetectorNotImplemented(
        "F14: Wide-shot monoculture detector not yet implemented (QUEUE.md item 4)"
    )
