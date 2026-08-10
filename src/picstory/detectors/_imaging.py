"""Shared pixel-math primitives for the local detectors (QUEUE.md item 3).

Each function here is a general-purpose signal-processing building block
(gradients, sharpness, connected runs) with no taxonomy opinion of its own -
the taxonomy-specific thresholds and interpretation live in the per-ID
detector modules that call these.
"""

from __future__ import annotations

import numpy as np


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
