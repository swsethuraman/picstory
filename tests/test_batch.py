"""Behavior tests for picstory.batch (QUEUE.md Stage 2, item 7).

Covers the 5-50 photo range enforcement and the batch-unique frame_id
assignment `load_batch` adds on top of Stage 1's `load_frame`.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from picstory.batch import MAX_BATCH_SIZE, MIN_BATCH_SIZE, BatchSizeError, load_batch


def _write_photo(path, fill: int = 128) -> None:
    Image.fromarray(np.full((8, 8, 3), fill, dtype="uint8")).save(path)


def _photos(tmp_path, n: int, *, same_stem: bool = False) -> list:
    paths = []
    for i in range(n):
        if same_stem:
            folder = tmp_path / f"dir{i}"
            folder.mkdir()
            path = folder / "img.jpg"
        else:
            path = tmp_path / f"img{i}.jpg"
        _write_photo(path)
        paths.append(path)
    return paths


# --- batch size enforcement ------------------------------------------------


def test_load_batch_rejects_below_min(tmp_path) -> None:
    paths = _photos(tmp_path, MIN_BATCH_SIZE - 1)
    with pytest.raises(BatchSizeError):
        load_batch(paths)


def test_load_batch_rejects_above_max(tmp_path) -> None:
    paths = _photos(tmp_path, MAX_BATCH_SIZE + 1)
    with pytest.raises(BatchSizeError):
        load_batch(paths)


def test_load_batch_accepts_min_size(tmp_path) -> None:
    paths = _photos(tmp_path, MIN_BATCH_SIZE)
    frames = load_batch(paths)
    assert len(frames) == MIN_BATCH_SIZE


def test_load_batch_accepts_max_size(tmp_path) -> None:
    paths = _photos(tmp_path, MAX_BATCH_SIZE)
    frames = load_batch(paths)
    assert len(frames) == MAX_BATCH_SIZE


def test_load_batch_rejects_empty_batch(tmp_path) -> None:
    with pytest.raises(BatchSizeError):
        load_batch([])


# --- frame_id uniqueness ----------------------------------------------------


def test_load_batch_assigns_unique_frame_ids_for_colliding_stems(tmp_path) -> None:
    paths = _photos(tmp_path, MIN_BATCH_SIZE, same_stem=True)
    frames = load_batch(paths)
    frame_ids = [f.frame_id for f in frames]
    assert len(frame_ids) == len(set(frame_ids))


def test_load_batch_frame_ids_are_index_prefixed_in_input_order(tmp_path) -> None:
    paths = _photos(tmp_path, MIN_BATCH_SIZE)
    frames = load_batch(paths)
    assert [f.frame_id for f in frames] == [f"{i:02d}_img{i}" for i in range(MIN_BATCH_SIZE)]
