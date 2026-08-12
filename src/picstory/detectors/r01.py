"""R01 · Haze rule (QUEUE.md item 13).

TAXONOMY.md §R: "Trigger: Hazy / low-contrast conditions (detected via F12
findings in the batch). Rule: Shoot tighter." This is not a per-frame
`Finding` - TAXONOMY.md is explicit that rules are "triggered by shooting
conditions, not detected in frames," a "different object type for the
classifier" (see `schema.Rule`, `ranking.py`'s docstring, and
`scripts/analyze.py`'s R01 exclusion note, all of which already treat R01
this way). So `detect()` here does not take a `Frame` the way every F/S
detector does; it takes the batch's already-computed `FrameAnalysis` list
(after the per-frame sweep and F03's merge, same point CMP runs at in
`scripts/analyze_batch.py`) and checks whether F12 was found on any frame -
the literal trigger condition TAXONOMY.md names, not a re-derivation of F12
itself.

Returns a `Rule` once per batch (not once per triggering frame - R01 is
forward-looking advice for the session, not a per-frame tally); `None` when
no frame in the batch carries an F12 finding.
"""

from __future__ import annotations

from picstory.detectors.base import register
from picstory.schema import FrameAnalysis, Rule, taxonomy_rule_text

# TAXONOMY.md §R01's Trigger text names F12 by ID: "detected via F12
# findings in the batch." Hardcoded here the same way other detectors
# hardcode a threshold extracted from their own Detection text (e.g. F03's
# HASH_DISTANCE_THRESHOLD) - the taxonomy prose is the source for *what* the
# condition is, not something re-parsed out of free text at runtime.
TRIGGER_ID = "F12"


@register("R01")
def detect(frame_analyses: list[FrameAnalysis]) -> Rule | None:
    triggered = any(
        finding.taxonomy_id == TRIGGER_ID
        for frame_analysis in frame_analyses
        for finding in frame_analysis.findings
    )
    if not triggered:
        return None
    return Rule(taxonomy_id="R01", advice=taxonomy_rule_text("R01"))
