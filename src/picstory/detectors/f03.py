"""F03 · Safety copies (QUEUE.md item 8).

TAXONOMY.md detection text: "2-5 consecutive frames of the same subject
with no change in position, focal length, or angle. Copies, not
variations."

This is a batch property, not a single-frame one - whether a photo is a
"copy" depends on the frames around it, which no single `Frame` carries on
its own. For that reason F03 is excluded from the per-frame sweep
(`scripts/analyze.py`'s `_NOT_PER_FRAME`, the same structural exclusion R01
already has, and for the same reason) and is instead computed once per
batch by `scripts/analyze_batch.py`, which calls this detector with the
real frame list.

The actual grouping logic - perceptual-hash near-duplicate matching, EXIF
focal-length equality, EXIF timestamp adjacency - lives in
`picstory.duplicates.group_near_duplicates`; this module's job is just to
turn "is this frame in a returned group?" into a `Finding`.
"""

from __future__ import annotations

from picstory.detectors.base import register
from picstory.duplicates import group_near_duplicates
from picstory.frame import Frame
from picstory.schema import Finding


@register("F03")
def detect(frame: Frame, *, batch: list[Frame] | None = None) -> Finding | None:
    """Find `frame` in `batch`'s near-duplicate groups.

    Requires `batch` - a single frame cannot be "consecutive" with itself.
    Raises `ValueError`, not `DetectorNotImplemented`, when `batch` is
    missing: the detection logic exists and is real, it simply cannot run
    without the frames around it. This is the same reason F03 never reaches
    this function through the per-frame sweep in the first place.
    """
    if batch is None:
        raise ValueError("F03 requires batch context: call detect(frame, batch=<frames>)")

    for group in group_near_duplicates(batch):
        for position, member in enumerate(group, start=1):
            if member.frame_id == frame.frame_id:
                return Finding(
                    taxonomy_id="F03",
                    description=(
                        f"frame {position} of a {len(group)}-frame safety-copy run "
                        "- consecutive, near-identical framing and focal length; "
                        "copies, not variations."
                    ),
                )
    return None
