"""S03 · Tight framing (DECISIONS.md D-007, replacing the D-005 stub).

TAXONOMY.md detection text: "The tightest frame of a subject among its
batch-mates." Explicitly relative - not decidable from one frame, the same
shape of gap D-005 originally identified and D-007 has now resolved for
this ID specifically (F14 stays stubbed; see `detectors.f14`). Like F03,
this does not fit the one-frame `detect(frame) -> Finding | None` shape;
`detect()` below takes the whole ordered batch. Wiring into the batch
pipeline lives in scripts/analyze_batch.py (mirroring F03's split there) and
scripts/analyze.py excludes S03 from the per-frame sweep the same way it
already excludes F03/R01.

Two independent pieces, per D-007's ruling:

1. "batch-mates" - which frames are of the same subject at all -
   `detectors.subject_clusters.group_subject_clusters`: a wider, disclosed
   perceptual-similarity grouping than F03's near-duplicate runs (see that
   module's docstring for why F03's own grouping would be a too-narrow
   substitute here, per D-007's own reasoning).
2. "the tightest frame" - among a cluster's batch-mates, which one - scored
   here via `_imaging.sharp_area_fraction`: the area share of the largest
   contiguous in-focus (sharp) region, as a proxy for how much of the frame
   the subject fills. No face/subject detector exists locally (the same gap
   F09's center-third proxy discloses), so this leans on the ordinary
   photographic convention that the subject is the sharp part of a
   deliberately composed frame - a tighter frame has less blurred/flat
   background left around it and more of the frame occupied by the in-focus
   subject. Disclosed proxy, not real segmentation; see
   `_imaging.sharp_area_fraction`'s own docstring for its failure modes.
"""

from __future__ import annotations

from picstory.detectors._imaging import downsample, sharp_area_fraction
from picstory.detectors.base import register
from picstory.detectors.subject_clusters import group_subject_clusters
from picstory.frame import Frame
from picstory.schema import Finding

MAX_DIM = 300
GRID = 16
RELATIVE_THRESHOLD = 1.5
MIN_ENERGY_FLOOR = 16.0


def _framing_tightness(frame: Frame) -> float:
    luminance = downsample(frame.luminance, max_dim=MAX_DIM)
    return sharp_area_fraction(
        luminance,
        grid=GRID,
        relative_threshold=RELATIVE_THRESHOLD,
        min_energy_floor=MIN_ENERGY_FLOOR,
    )


@register("S03")
def detect(frames: list[Frame]) -> dict[str, Finding]:
    """Batch-level detector: takes the whole ordered batch, not one Frame.

    Within each subject cluster (>=2 frames; a frame with no batch-mate has
    nothing to be "tightest among"), the frame with the highest framing-
    tightness score wins one S03 Finding. Ties keep the cluster's batch
    order (`max` returns the first maximal element on a tie, the same
    tie-break convention `ranking.rank_frames` documents for its own stable
    sort). Returns `{frame_id: Finding}` only for winners; every other frame
    (including every cluster's non-winners and every singleton) is simply
    absent, matching F03's "absent, not a negative Finding" convention.
    """
    by_id = {frame.frame_id: frame for frame in frames}
    findings: dict[str, Finding] = {}
    for group in group_subject_clusters(frames):
        tightness = {frame_id: _framing_tightness(by_id[frame_id]) for frame_id in group}
        winner_id = max(group, key=lambda frame_id: tightness[frame_id])
        findings[winner_id] = Finding(
            taxonomy_id="S03",
            description=(
                f"tightest framing among {len(group)} batch-mates of the same subject "
                f"(sharp-area share {tightness[winner_id]:.0%})"
            ),
        )
    return findings
