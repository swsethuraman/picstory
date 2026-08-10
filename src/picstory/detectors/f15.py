"""F15 · Subject/landmark competition — Anthropic API vision-call detector.

Judgment-dependent per QUEUE.md item 4 and CLAUDE.md's API-discipline rule:
the call embeds F15's Detection text verbatim (via
`schema.taxonomy_detection_text`, not a local copy) and returns structured
output naming F15. See `_vision.py` for the shared call/parse plumbing.
"""

from __future__ import annotations

from picstory.detectors._vision import VisionCaller, judge
from picstory.detectors.base import register
from picstory.frame import Frame
from picstory.schema import Finding, taxonomy_detection_text

TAXONOMY_ID = "F15"


@register(TAXONOMY_ID)
def detect(frame: Frame, *, caller: VisionCaller | None = None) -> Finding | None:
    return judge(frame, TAXONOMY_ID, taxonomy_detection_text(TAXONOMY_ID), caller=caller)
