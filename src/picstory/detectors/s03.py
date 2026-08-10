"""S03 · Tight framing — registry stub, deferred (DECISIONS.md D-005).

Claims the S03 registry slot (QUEUE.md item 2). QUEUE.md item 4 groups S03
with the single-frame API-vision detectors, but its Detection text -
"the tightest frame of a subject among its batch-mates" - is explicitly
relative: undecidable from one frame with no batch-mates to compare against.
Stage 1 (this queue item) processes one photo at a time, so honestly
implementing S03 needs the batch grouping that doesn't exist until Stage 2.
See DECISIONS.md D-005 (flagged as a forward-looking watch item by
critic-001, now acted on). This stub still raises DetectorNotImplemented
rather than returning a silent negative or a single-frame substitute (e.g. a
vague "is this tightly framed?" vision call) - a stub returning nothing is
not an implementation, and a substitute for the actual relative comparison
is exactly the failure mode PREDICTION.md names (CLAUDE.md).
"""

from __future__ import annotations

from picstory.detectors.base import DetectorNotImplemented, register


@register("S03")
def detect(*_args, **_kwargs):
    raise DetectorNotImplemented(
        "S03: Tight framing detector not yet implemented (QUEUE.md item 4)"
    )
