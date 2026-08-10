"""S04 · Restraint composition — Anthropic API vision-call detector.

Judgment-dependent per QUEUE.md item 4 and CLAUDE.md's API-discipline rule:
the call embeds S04's Detection text verbatim (via
`schema.taxonomy_detection_text`, not a local copy) and returns structured
output naming S04. See `_vision.py` for the shared call/parse plumbing.
"""

from __future__ import annotations

from picstory.detectors._vision import VisionCaller, judge
from picstory.detectors.base import register
from picstory.frame import Frame
from picstory.schema import Finding, taxonomy_detection_text

TAXONOMY_ID = "S04"


@register(TAXONOMY_ID)
def detect(frame: Frame, *, caller: VisionCaller | None = None) -> Finding | None:
    return judge(frame, TAXONOMY_ID, taxonomy_detection_text(TAXONOMY_ID), caller=caller)
