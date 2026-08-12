"""F14 · Wide-shot monoculture — registry stub, deferred (DECISIONS.md D-007).

Claims the F14 registry slot (QUEUE.md item 2). QUEUE.md item 4 groups F14
with the single-frame API-vision detectors, but its Detection text - "A
location's coverage is all establishing views" - is a property of a set of
frames from one location, not of any single frame: no photo, however wide,
is "monoculture" on its own. Originally deferred by DECISIONS.md D-005
pending Stage 2's batch context; D-007 (ruled 12 Aug 2026, after Stage 2
landed without giving F14 the location-clustering it actually needs) kept
F14 stubbed standing for the remainder of the experiment - its honest
precondition (EXIF GPS parsing + location clustering + a documented no-GPS
fallback) is deliberately out of scope for the remaining session budget.
Reusing the batch as a whole, or F03's near-duplicate groups, as a stand-in
for "a location" was considered and rejected in D-007 as a too-narrow
substitute for the same reason a per-frame proxy already was in D-005. This
stub still raises DetectorNotImplemented rather than returning a silent
negative or a substitute - a stub returning nothing is not an
implementation, and a too-narrow-grouping guess at a batch-level condition
would be the substitute PREDICTION.md names (CLAUDE.md).
"""

from __future__ import annotations

from picstory.detectors.base import DetectorNotImplemented, register


@register("F14")
def detect(*_args, **_kwargs):
    raise DetectorNotImplemented(
        "F14: Wide-shot monoculture detector not yet implemented (QUEUE.md item 4)"
    )
