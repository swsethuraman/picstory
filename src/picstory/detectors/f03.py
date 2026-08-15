"""F03 · Safety copies (QUEUE.md item 8).

TAXONOMY.md detection text: "2-5 consecutive frames of the same subject with
no change in position, focal length, or angle. Copies, not variations."

That is a property of a *run* of frames, not of any one photo - the same
shape of gap D-005 originally identified for F14/S03 (S03 now implemented
separately, per D-007 - see `detectors.s03`), except here batch context now
exists (QUEUE.md item 7's `picstory.batch.load_batch`), so it gets
implemented for real rather than staying a deferred stub. `detect()` below
therefore does not use the one-frame `detect(frame) -> Finding | None`
shape every other ID uses; it takes the whole ordered batch. Wiring that
into the per-frame sweep lives in scripts/analyze.py (which excludes F03
from `evaluable_ids()` the same way it excludes R01) and
scripts/analyze_batch.py (which calls this directly once per batch).

Three independent, per-item-named signals decide whether two *consecutive*
frames (`frames[i-1]`, `frames[i]`) are "the same subject with no change,"
each corresponding to one clause of the Detection text:

1. "no change in position ... or angle": approximated by structural
   similarity via a difference hash (`_imaging.difference_hash`) over the
   whole frame. There is no camera-pose or depth data available to measure
   position/angle directly - this is a documented proxy, same disclosure
   F09 already uses for "subject" (REVIEW.md, critic-002) - but it is the
   right *kind* of proxy: a low dHash distance means the pixels barely
   moved, which is what "no change in position or angle" looks like in a
   photo, not a looser stand-in for "photos of the same general place."
2. "no change in focal length": read directly from EXIF `FocalLength` - the
   literal metadata signal, same pattern as F01's `DigitalZoomRatio` check.
3. Implicit in "consecutive frames" for a burst/reshoot: EXIF
   `DateTimeOriginal`/`DateTime` timestamps should be close together. This
   is the third signal QUEUE.md item 8 names ("EXIF timestamps").

Signals 2 and 3 only block a match when *both* frames carry the relevant
EXIF tag - if either is missing, that check is skipped rather than treated
as a mismatch (same reasoning as F01: missing metadata means "can't
evaluate," not "assume the opposite"). Signal 1 always applies; it is the
one directly-computable-from-pixels reading of "same subject."

Grouping does not cap runs at 5 frames even though the Detection text says
"2-5": TAXONOMY.md's own examples ("Rathaus tower x3, Stephansdom portrait
setup x5") read as the *typical* size of what happens in practice, not a
hard boundary on what counts - a run of 6 identical frames is still
"copies, not variations." (Same treatment critic-002 gave F02's "typically
consistent across consecutive frames.")
"""

from __future__ import annotations

from datetime import datetime

from picstory.detectors._imaging import hamming_distance
from picstory.detectors.base import register
from picstory.frame import Frame
from picstory.schema import Finding

HASH_SIZE = 8
# Out of HASH_SIZE * HASH_SIZE = 64 bits. Calibrated against
# tests/test_f03_safety_copies.py's textured fixture: an identical frame
# scores 0; the same frame with sigma-8 pixel noise added (well above
# ordinary sensor noise) still scores ~2; a subject moved 10% of the frame
# width scores 8; this threshold sits comfortably between the two.
HASH_DISTANCE_THRESHOLD = 6
FOCAL_LENGTH_TOLERANCE_MM = 0.5
TIMESTAMP_GAP_SECONDS = 30.0
_EXIF_TIMESTAMP_FORMAT = "%Y:%m:%d %H:%M:%S"


def _frame_hash(frame: Frame):
    # QUEUE.md item 15b: memoized on the Frame itself, so CMP's own
    # re-grouping (scripts/analyze_batch.py's `_run_comparisons` calls
    # `group_near_duplicates` a second time over the same frames) reuses
    # this batch's already-computed hashes instead of recomputing them.
    return frame.dhash(hash_size=HASH_SIZE)


def _focal_length_mm(frame: Frame) -> float | None:
    value = frame.exif.get("FocalLength")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _timestamp_seconds(frame: Frame) -> float | None:
    raw = frame.exif.get("DateTimeOriginal") or frame.exif.get("DateTime")
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw), _EXIF_TIMESTAMP_FORMAT).timestamp()
    except ValueError:
        return None


def _is_safety_copy_pair(prev: Frame, curr: Frame) -> bool:
    if hamming_distance(_frame_hash(prev), _frame_hash(curr)) > HASH_DISTANCE_THRESHOLD:
        return False

    focal_prev, focal_curr = _focal_length_mm(prev), _focal_length_mm(curr)
    if (
        focal_prev is not None
        and focal_curr is not None
        and abs(focal_prev - focal_curr) > FOCAL_LENGTH_TOLERANCE_MM
    ):
        return False

    time_prev, time_curr = _timestamp_seconds(prev), _timestamp_seconds(curr)
    if (
        time_prev is not None
        and time_curr is not None
        and abs(time_prev - time_curr) > TIMESTAMP_GAP_SECONDS
    ):
        return False

    return True


def group_near_duplicates(frames: list[Frame]) -> list[list[str]]:
    """Runs of >=2 consecutive frames judged "copies, not variations."

    `frames` is assumed ordered as the batch was captured/supplied
    (`picstory.batch.load_batch` preserves caller order) - "consecutive" is
    read as adjacency in this list, not EXIF timestamp order, since that is
    the only ordering the caller actually controls or guarantees.

    Returns each run as a list of `frame_id`s in order; frames not part of
    any qualifying run are simply absent, not returned as singleton groups.
    """
    groups: list[list[str]] = []
    current: list[str] = []
    for i in range(1, len(frames)):
        prev, curr = frames[i - 1], frames[i]
        if _is_safety_copy_pair(prev, curr):
            if not current:
                current = [prev.frame_id]
            current.append(curr.frame_id)
        else:
            if len(current) >= 2:
                groups.append(current)
            current = []
    if len(current) >= 2:
        groups.append(current)
    return groups


@register("F03")
def detect(frames: list[Frame]) -> dict[str, Finding]:
    """Batch-level detector: takes the whole ordered batch, not one Frame.

    Within each detected run, the first frame is the "kept" shot and is not
    flagged - TAXONOMY.md's correction text ("One frame, then deliberately
    change something") frames the first frame as the fine one; the problem
    is the excess copies after it. Returns `{frame_id: Finding}` only for
    those excess frames; frames with no finding (including every run's
    first frame) are simply absent from the returned mapping.
    """
    findings: dict[str, Finding] = {}
    for group in group_near_duplicates(frames):
        keeper, *copies = group
        for frame_id in copies:
            findings[frame_id] = Finding(
                taxonomy_id="F03",
                description=(
                    f"safety copy of {keeper!r} - {len(group)} consecutive frames "
                    "with no change in position, focal length, or angle"
                ),
            )
    return findings
