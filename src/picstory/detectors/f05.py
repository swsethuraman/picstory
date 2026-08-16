"""F05 · Ultrawide geometric distortion — Anthropic API vision-call detector.

Judgment-dependent per QUEUE.md item 4 and CLAUDE.md's API-discipline rule:
the call embeds F05's Detection text verbatim (via
`schema.taxonomy_detection_text`, not a local copy) and returns structured
output naming F05. See `_vision.py` for the shared call/parse plumbing.

QUEUE.md item 18(c) (DECISIONS.md D-009): F05's Fixability is `conditional`
per TAXONOMY.md v1.2 - `bowing` (curved/skewed lines, subject centered) is
post-fixable via lens/geometry correction; `off_center_drift` (the subject
itself placed off the ultrawide's center) is capture-only. Wired the same
way F06 wires its `edge` Profile-note sub-pattern: a `SubPatternSpec` adds
one enum-constrained field to the same structured tool call, so the model
names which case applies in the same request that makes the yes/no verdict,
not a second call or a free-text guess. `schema.resolve_finding_fixability`
reads the resulting `Finding.sub_pattern` against
`schema.CONDITIONAL_FIXABILITY_RESOLUTION` to produce the one-word
fixability the Check surface will eventually need (D-009).
"""

from __future__ import annotations

from picstory.detectors._vision import SubPatternSpec, VisionCaller, judge
from picstory.detectors.base import register
from picstory.frame import Frame
from picstory.schema import Finding, taxonomy_detection_text

TAXONOMY_ID = "F05"

GEOMETRY_SUB_PATTERN = SubPatternSpec(
    field_name="geometry",
    enum_values=("bowing", "off_center_drift"),
    description=(
        "which distortion pattern is present: 'bowing' if ceiling/architectural "
        "lines curve or skew while the subject itself is centered in the frame "
        "(a lens artifact, correctable in edit); 'off_center_drift' if the "
        "subject is placed off the ultrawide's optical center and that "
        "placement is what is driving the distortion (not fixable by cropping "
        "or straightening)."
    ),
)


@register(TAXONOMY_ID)
def detect(frame: Frame, *, caller: VisionCaller | None = None) -> Finding | None:
    return judge(
        frame,
        TAXONOMY_ID,
        taxonomy_detection_text(TAXONOMY_ID),
        caller=caller,
        sub_pattern=GEOMETRY_SUB_PATTERN,
    )
