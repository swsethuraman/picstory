"""F06 · Edge intrusion (unchosen frame content) — Anthropic API vision-call detector.

Judgment-dependent per QUEUE.md item 4 and CLAUDE.md's API-discipline rule:
the call embeds F06's Detection text verbatim (via
`schema.taxonomy_detection_text`, not a local copy) and returns structured
output naming F06. See `_vision.py` for the shared call/parse plumbing.

F06 is also the QUEUE.md item 12 hook for the running profile: its
TAXONOMY.md entry carries a "Profile note" ("Directional sub-patterns ...
are per-user traits tracked by the profile, not separate taxonomy items"),
so this is the one detector (today) that also asks the model for a closed-
vocabulary `edge` value alongside its yes/no verdict - structured and enum-
constrained in the same tool call, not a free-text rationale a profile
store would have to regex for keywords (see `_vision.SubPatternSpec`).
`schema.Finding.__post_init__` enforces that only IDs with a documented
Profile note (`schema.taxonomy_ids_with_subpattern()`) may carry a
`sub_pattern` at all.
"""

from __future__ import annotations

from picstory.detectors._vision import SubPatternSpec, VisionCaller, judge
from picstory.detectors.base import register
from picstory.frame import Frame
from picstory.schema import Finding, taxonomy_detection_text

TAXONOMY_ID = "F06"

EDGE_SUB_PATTERN = SubPatternSpec(
    field_name="edge",
    enum_values=("left", "right", "top", "bottom", "multiple"),
    description=(
        "which frame edge carries the unchosen content (a stranger's shoulder, a "
        "half-cropped figure, a flag or banner, a label cut mid-word, construction, "
        "a bracket). Use 'multiple' if more than one edge is affected."
    ),
)


@register(TAXONOMY_ID)
def detect(frame: Frame, *, caller: VisionCaller | None = None) -> Finding | None:
    return judge(
        frame,
        TAXONOMY_ID,
        taxonomy_detection_text(TAXONOMY_ID),
        caller=caller,
        sub_pattern=EDGE_SUB_PATTERN,
    )
