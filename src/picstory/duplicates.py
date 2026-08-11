"""Near-duplicate grouping across a batch (QUEUE.md Stage 2, item 8).

TAXONOMY.md's F03 detection text: "2-5 consecutive frames of the same
subject with no change in position, focal length, or angle. Copies, not
variations." That is a property of a *run* of frames, not of any single
photo - this module is the batch-level grouping engine F03's detector
(`picstory.detectors.f03`) is built on, per QUEUE.md item 8's own framing
("F03 near-duplicate grouping (perceptual hash + EXIF timestamps/focal
length deltas)"). Three signals, all against the immediate predecessor only
("consecutive", not "similar to anything earlier in the batch"):

1. Perceptual hash (dHash) Hamming distance - a proxy for "no change in
   position or angle". A real reframe (walk a few feet, tilt the camera)
   moves enough pixels around to push the hash distance up; sensor noise,
   recompression, or a handheld micro-shake does not. Calibrated against
   synthetic frames (see tests/test_duplicates.py): near-identical frames
   land at Hamming distance 0-7 out of 64 bits, a real reframe or a
   different scene lands at 29+.
2. EXIF `FocalLength` equality - the literal "no change in focal length"
   clause. Only rejects a match on an affirmative delta; if either frame is
   missing the tag, this signal can't be evaluated and does not sink an
   otherwise-matching pair (same "absence isn't evidence" reasoning as
   f01.py's DigitalZoomRatio handling).
3. EXIF timestamp adjacency - the literal "consecutive" clause. Same
   missing-tag handling as (2).

A run breaks the moment one frame fails any of the three checks against its
predecessor, and is capped at 5 frames (TAXONOMY.md's stated upper bound) -
a 6th consecutive near-duplicate starts a new run rather than growing the
first one past what the taxonomy item describes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from PIL import Image

from picstory.frame import Frame

HASH_SIZE = 8  # dHash -> HASH_SIZE x HASH_SIZE = 64 bits
MAX_HAMMING_DISTANCE = 10  # of 64 bits; see calibration note above
MAX_FOCAL_LENGTH_DELTA_MM = 0.5
MAX_TIMESTAMP_GAP_SECONDS = 10.0
MIN_GROUP_SIZE = 2
MAX_GROUP_SIZE = 5

_EXIF_TIMESTAMP_FORMAT = "%Y:%m:%d %H:%M:%S"


def dhash(frame: Frame) -> int:
    """Perceptual difference-hash of a frame's pixels, as a HASH_SIZE**2-bit int."""
    gray = (
        Image.fromarray(frame.rgb)
        .convert("L")
        .resize((HASH_SIZE + 1, HASH_SIZE), Image.BILINEAR)
    )
    pixels = np.asarray(gray, dtype=np.int16)
    bits = (pixels[:, 1:] > pixels[:, :-1]).flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def _focal_length_mm(frame: Frame) -> float | None:
    value = frame.exif.get("FocalLength")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _timestamp_seconds(frame: Frame) -> float | None:
    for tag in ("DateTimeOriginal", "DateTime"):
        value = frame.exif.get(tag)
        if not value:
            continue
        try:
            return datetime.strptime(str(value), _EXIF_TIMESTAMP_FORMAT).timestamp()
        except ValueError:
            continue
    return None


@dataclass(frozen=True)
class _MatchSignals:
    hamming_distance: int
    focal_length_delta_mm: float | None
    timestamp_gap_seconds: float | None


def _consecutive_match(prev: Frame, curr: Frame) -> _MatchSignals | None:
    """Whether `curr` continues a safety-copy run started at `prev`, or None."""
    distance = hamming_distance(dhash(prev), dhash(curr))
    if distance > MAX_HAMMING_DISTANCE:
        return None

    fl_prev, fl_curr = _focal_length_mm(prev), _focal_length_mm(curr)
    focal_delta = None
    if fl_prev is not None and fl_curr is not None:
        focal_delta = abs(fl_prev - fl_curr)
        if focal_delta > MAX_FOCAL_LENGTH_DELTA_MM:
            return None

    ts_prev, ts_curr = _timestamp_seconds(prev), _timestamp_seconds(curr)
    gap = None
    if ts_prev is not None and ts_curr is not None:
        gap = abs(ts_curr - ts_prev)
        if gap > MAX_TIMESTAMP_GAP_SECONDS:
            return None

    return _MatchSignals(distance, focal_delta, gap)


def group_near_duplicates(frames: list[Frame]) -> list[list[Frame]]:
    """Runs of 2-5 consecutive near-duplicate frames, in batch order.

    Only runs of `MIN_GROUP_SIZE` or more are returned - a single frame with
    no near-duplicate neighbor is not a "copy" of anything. Frames not in
    any returned group are not near-duplicates of their neighbors.
    """
    groups: list[list[Frame]] = []
    current: list[Frame] = []
    for frame in frames:
        continues_run = (
            current
            and len(current) < MAX_GROUP_SIZE
            and _consecutive_match(current[-1], frame) is not None
        )
        if continues_run:
            current.append(frame)
        else:
            if len(current) >= MIN_GROUP_SIZE:
                groups.append(current)
            current = [frame]
    if len(current) >= MIN_GROUP_SIZE:
        groups.append(current)
    return groups
