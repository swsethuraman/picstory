"""Shared pixel-math primitives for the local detectors (QUEUE.md item 3).

Each function here is a general-purpose signal-processing building block
(gradients, sharpness, connected runs) with no taxonomy opinion of its own -
the taxonomy-specific thresholds and interpretation live in the per-ID
detector modules that call these.
"""

from __future__ import annotations

import numpy as np
from PIL import Image


def sobel_gradients(luminance: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Horizontal/vertical Sobel gradients of a 2-D luminance array."""
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
    ky = kx.T
    padded = np.pad(luminance, 1, mode="edge")
    gx = np.zeros_like(luminance, dtype=np.float64)
    gy = np.zeros_like(luminance, dtype=np.float64)
    for dy in range(3):
        for dx in range(3):
            if kx[dy, dx] == 0 and ky[dy, dx] == 0:
                continue
            window = padded[dy : dy + luminance.shape[0], dx : dx + luminance.shape[1]]
            gx += kx[dy, dx] * window
            gy += ky[dy, dx] * window
    return gx, gy


def laplacian(luminance: np.ndarray) -> np.ndarray:
    """Discrete Laplacian (edge/high-frequency response) of a 2-D array."""
    padded = np.pad(luminance, 1, mode="edge")
    center = padded[1:-1, 1:-1]
    up = padded[:-2, 1:-1]
    down = padded[2:, 1:-1]
    left = padded[1:-1, :-2]
    right = padded[1:-1, 2:]
    return (up + down + left + right - 4 * center).astype(np.float64)


def sharpness_score(luminance: np.ndarray) -> float:
    """Variance of the Laplacian - low values mean soft/blurred content."""
    return float(np.var(laplacian(luminance)))


def longest_true_run(mask: np.ndarray) -> int:
    """Length of the longest run of consecutive True values in a 1-D bool array."""
    if mask.size == 0:
        return 0
    padded = np.concatenate(([False], mask, [False]))
    edges = np.diff(padded.astype(np.int8))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    if starts.size == 0:
        return 0
    return int(np.max(ends - starts))


def downsample(luminance: np.ndarray, max_dim: int = 400) -> np.ndarray:
    """Block-average downsample so O(n^2) analyses stay cheap on real photos."""
    h, w = luminance.shape
    scale = max(1, int(np.ceil(max(h, w) / max_dim)))
    if scale == 1:
        return luminance
    h_trim = h - (h % scale)
    w_trim = w - (w % scale)
    trimmed = luminance[:h_trim, :w_trim]
    reshaped = trimmed.reshape(h_trim // scale, scale, w_trim // scale, scale)
    return reshaped.mean(axis=(1, 3))


def difference_hash(luminance: np.ndarray, hash_size: int = 8) -> np.ndarray:
    """Difference hash (dHash): a `hash_size` x `hash_size` bool array.

    Standard dHash: shrink to (hash_size+1) columns by hash_size rows, then
    each bit is "does luminance increase left-to-right" for one pixel pair.
    Robust to small resizes/re-encodes, sensitive to real changes in
    composition (a moved subject, a reframed shot) - which is what makes it
    a usable proxy for "same position/angle" between two frames, not just
    "same average brightness."

    The shrink uses PIL's box resampling (area averaging over each output
    pixel's source block), not nearest-neighbor sampling - critical here,
    since sampling single pixels from a full-resolution photo would let
    ordinary sensor noise flip individual comparison bits; averaging a whole
    block per output pixel suppresses that the same way `downsample` does
    for the other local detectors.
    """
    small_image = Image.fromarray(np.clip(luminance, 0, 255).astype(np.uint8)).resize(
        (hash_size + 1, hash_size), Image.Resampling.BOX
    )
    small = np.asarray(small_image, dtype=np.float64)
    return small[:, 1:] > small[:, :-1]


def hamming_distance(a: np.ndarray, b: np.ndarray) -> int:
    """Count of differing bits between two equal-shaped bool arrays."""
    return int(np.count_nonzero(a != b))


def sharp_area_fraction(
    luminance: np.ndarray,
    grid: int = 16,
    relative_threshold: float = 1.5,
    min_energy_floor: float = 16.0,
) -> float:
    """Area share of the largest connected "sharp" (in-focus) tile blob.

    Tiles `luminance` into a `grid` x `grid` grid and scores each tile by its
    mean squared Laplacian ("energy") - the same high-pass Laplacian
    `sharpness_score` already uses globally (a variance-of-Laplacian
    sharpness measure), localized per tile the way `_local_variance` in
    f02.py localizes plain luminance variance. A tile counts as "sharp" if
    its energy exceeds `relative_threshold` x the grid's own median tile
    energy - relative to each image's own sharpness distribution, not an
    absolute level, since photos vary hugely in overall sharpness/ISO noise.
    `min_energy_floor` guards the case where most of the grid is genuinely
    flat (median at or near zero, e.g. a plain sky or a synthetic flat test
    fixture): without it, any nonzero tile - including ordinary rounding
    noise - would clear a relative threshold computed against a
    near-zero baseline.

    Returns the largest 4-connected sharp region's tile count as a fraction
    of the whole grid; 0.0 if no tile is sharp (including an entirely flat
    image). This is a proxy for how much of the frame the in-focus subject
    fills, not a real subject segmentation - like every other disclosed
    local proxy in this package (F09's center-third, F03's dHash-as-pose),
    it can misread a scene where the background is itself sharp/textured
    and the subject is soft. It also breaks down at the extreme where the
    subject fills nearly the whole frame (no flat-background majority left
    to set a low baseline against, so the relative threshold rises and the
    reported share can drop rather than saturate) - a known proxy limit,
    not a case this function tries to correct for, the same kind of
    disclosed edge F07 handles with an explicit upper bound instead.
    """
    lap = laplacian(luminance)
    energy = lap * lap
    h, w = energy.shape
    th, tw = max(1, h // grid), max(1, w // grid)
    h_trim, w_trim = th * (h // th), tw * (w // tw)
    trimmed = energy[:h_trim, :w_trim]
    if trimmed.size == 0:
        return 0.0
    tiles = trimmed.reshape(h_trim // th, th, w_trim // tw, tw)
    tile_energy = tiles.mean(axis=(1, 3))
    threshold = max(relative_threshold * float(np.median(tile_energy)), min_energy_floor)
    sharp = tile_energy > threshold
    if not sharp.any():
        return 0.0
    return largest_connected_area(sharp) / sharp.size


def largest_connected_area(mask: np.ndarray) -> int:
    """Pixel count of the largest 4-connected True region in a 2-D bool array."""
    visited = np.zeros_like(mask, dtype=bool)
    h, w = mask.shape
    best = 0
    for i in range(h):
        for j in range(w):
            if not mask[i, j] or visited[i, j]:
                continue
            stack = [(i, j)]
            visited[i, j] = True
            size = 0
            while stack:
                y, x = stack.pop()
                size += 1
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((ny, nx))
            best = max(best, size)
    return best
