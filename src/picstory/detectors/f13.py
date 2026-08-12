"""F13 · Missing human scale — Anthropic API vision-call detector.

Judgment-dependent per QUEUE.md item 4 and CLAUDE.md's API-discipline rule:
the call embeds F13's Detection text verbatim (via
`schema.taxonomy_detection_text`, not a local copy) and returns structured
output naming F13. See `_vision.py` for the shared call/parse plumbing.

Detection text: "Large subject with nothing indicating its size; the set
reads as 'one idea repeated,' a record rather than an experience." The
operative condition - no scale reference for a large subject - is decidable
from one frame; "the set reads as..." is the batch-level consequence of the
same per-frame gap recurring, not a separate multi-frame precondition
(unlike F14, still deferred - see DECISIONS.md D-007).
"""

from __future__ import annotations

from picstory.detectors._vision import VisionCaller, judge
from picstory.detectors.base import register
from picstory.frame import Frame
from picstory.schema import Finding, taxonomy_detection_text

TAXONOMY_ID = "F13"


@register(TAXONOMY_ID)
def detect(frame: Frame, *, caller: VisionCaller | None = None) -> Finding | None:
    return judge(frame, TAXONOMY_ID, taxonomy_detection_text(TAXONOMY_ID), caller=caller)
