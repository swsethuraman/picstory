"""Batch input loading (QUEUE.md Stage 2, item 7).

Stage 1 (`picstory.frame.load_frame`) decodes one photo at a time and lets
its default `frame_id` fall back to the bare filename stem - fine for a
single photo, but two files with the same stem from different folders would
collide once multiple photos share one `AnalysisOutput`. This module is the
batch-sized wrapper: it enforces the 5-50 photo range QUEUE.md item 7 names
("Batch input (5-50 photos)") and assigns each decoded `Frame` an
index-prefixed `frame_id` that stays unique across the whole batch
regardless of source filenames.

Per-frame *analysis* (the rest of item 7 - "per-frame analysis reusing Stage
1") is `scripts/analyze_batch.py`'s job, built directly on top of
`analyze.run_analysis` rather than duplicating its per-ID dispatch here.
Near-duplicate grouping (F03, item 8), ranking/shortlist (item 9), and the
session habit (item 10) are later queue items and are out of scope for this
module.

QUEUE.md item 15 (the resolution contract): each `Frame` this returns is
already decoded at working resolution - `load_frame` (`frame.py`) owns that
downsample, this module just calls it once per path in order.
"""

from __future__ import annotations

from pathlib import Path

from picstory.frame import Frame, load_frame

MIN_BATCH_SIZE = 5
MAX_BATCH_SIZE = 50


class BatchSizeError(ValueError):
    """Raised when a batch's photo count falls outside [MIN_BATCH_SIZE, MAX_BATCH_SIZE]."""


def load_batch(paths: list[str | Path]) -> list[Frame]:
    """Decode 5-50 photos into Frames, each with a batch-unique frame_id.

    Order is preserved (index 0 is `paths[0]`, etc.) since Stage 3's
    comparison and Stage 2's ranking will want a stable, caller-controlled
    ordering rather than one this function reshuffles.
    """
    resolved = [Path(p) for p in paths]
    if not (MIN_BATCH_SIZE <= len(resolved) <= MAX_BATCH_SIZE):
        raise BatchSizeError(
            f"batch must have {MIN_BATCH_SIZE}-{MAX_BATCH_SIZE} photos, got {len(resolved)}"
        )
    return [
        load_frame(path, frame_id=f"{i:02d}_{path.stem}")
        for i, path in enumerate(resolved)
    ]
