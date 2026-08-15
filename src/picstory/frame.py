"""Frame loading: decode an image into pixel data + EXIF for detectors.

Local detectors (QUEUE.md item 3) all need the same two things from a photo
- decoded RGB pixels and parsed EXIF tags - so decoding happens once here
rather than once per detector. The detector call signature settled by this
module: `detect(frame: Frame) -> Finding | None`.

QUEUE.md item 15 (the resolution contract): `load_frame` decodes at native
resolution only long enough to read EXIF, then immediately downsamples
pixel data to `WORKING_RESOLUTION_MAX_DIM` on the long edge before building
the `Frame`. On real 48MP iPhone frames, processing and uploading at native
resolution made the capstone run (docs/capstone-vienna-report.md)
effectively non-terminating - multi-MB vision API payloads x ~280 calls,
uncached full-resolution luminance rebuilt for every hash comparison - and
was invisible to every test in this suite because every fixture is <=200px.
Everything downstream of `load_frame`/`load_batch` (every detector,
`detectors._vision._encode_jpeg`, every perceptual hash) may assume
`Frame.rgb`/`Frame.luminance` already sit at working resolution; nothing
needs to re-downsample for that reason. A detector with a demonstrated need
for native-resolution pixel data may still reopen `path` itself and crop
the specific region it needs (see `Frame.path`'s docstring) - that need is
documented per-detector when it arises; the default for every other
detector is working-resolution only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import numpy as np
from PIL import ExifTags, Image

# Long-edge cap (pixels) pixel data is downsampled to immediately after
# decode - see the module docstring for why. ~2000px keeps fine-detail
# detectors (F01) and per-pair pixel hashing (F03/S03/CMP) working on
# meaningfully sharp data while keeping per-frame vision payloads and
# O(n^2) hash comparisons cheap even at 50-photo batch scale. Not a
# per-detector tuning knob: every local/vision detector today either relies
# on this default or downsamples further itself (F02/F08/S03 already do,
# to their own smaller scale, independent of this constant).
WORKING_RESOLUTION_MAX_DIM = 2000


@dataclass
class Frame:
    """A decoded photo: RGB pixels plus flattened EXIF tags, by name.

    `rgb` is decoded at working resolution (`WORKING_RESOLUTION_MAX_DIM`),
    not the source file's native resolution - see the module docstring for
    the contract this establishes for every downstream reader. `path` is
    kept anyway as a lazy escape hatch: a detector with a genuine,
    documented need for native-resolution pixel data (e.g. cropping one
    specific region at full detail) may reopen `path` itself rather than
    this class eagerly holding a full-resolution copy of every frame in a
    batch in memory. No detector needs this today.
    """

    frame_id: str
    path: Path
    rgb: np.ndarray  # (height, width, 3) uint8, at working resolution
    exif: dict
    _hash_cache: dict = field(default_factory=dict, repr=False, compare=False)

    @property
    def height(self) -> int:
        return self.rgb.shape[0]

    @property
    def width(self) -> int:
        return self.rgb.shape[1]

    @cached_property
    def luminance(self) -> np.ndarray:
        """Rec. 601 luma, float64, same (height, width) shape as rgb.

        Cached (QUEUE.md item 15b): a batch run computes this from several
        detectors, F03/S03's grouping, and CMP's re-grouping, all against
        the same frame - without caching, each of those recomputes the same
        conversion from the same `rgb` array every time it's called.
        """
        r = self.rgb[..., 0].astype(np.float64)
        g = self.rgb[..., 1].astype(np.float64)
        b = self.rgb[..., 2].astype(np.float64)
        return 0.299 * r + 0.587 * g + 0.114 * b

    def dhash(self, hash_size: int = 8) -> np.ndarray:
        """Memoized difference hash at `hash_size` (QUEUE.md item 15b).

        F03's near-duplicate runs, S03's subject clusters, and CMP's own
        re-grouping (`scripts/analyze_batch.py`'s `_run_comparisons` calls
        `f03.group_near_duplicates` a second time over the same frames
        `run_batch_analysis` already grouped once for F03 itself) all hash
        every frame at the same `hash_size` (8, in both `f03.py` and
        `subject_clusters.py`) - without this, each call recomputes
        `_imaging.difference_hash`'s PIL resize from scratch. Cached per
        `hash_size` rather than unconditionally, since a caller asking for a
        different size legitimately needs a different hash. Import is local
        to avoid a module-level dependency from this low-level module onto
        the detectors package (frame.py has no other picstory imports).
        """
        cached = self._hash_cache.get(hash_size)
        if cached is None:
            from picstory.detectors._imaging import difference_hash

            cached = difference_hash(self.luminance, hash_size=hash_size)
            self._hash_cache[hash_size] = cached
        return cached


def _flatten_exif(image: Image.Image) -> dict:
    """EXIF tags by human-readable name, including the Exif sub-IFD.

    Pillow exposes top-level tags (Make, Model, Orientation, ...) directly on
    getexif(), but tags like FocalLength and DigitalZoomRatio live in the
    nested "Exif" IFD and need get_ifd() to reach.
    """
    raw = image.getexif()
    tags: dict = {}
    for tag_id, value in raw.items():
        name = ExifTags.TAGS.get(tag_id, tag_id)
        tags[name] = value
    try:
        exif_ifd = raw.get_ifd(ExifTags.IFD.Exif)
    except (KeyError, AttributeError, ValueError):
        exif_ifd = {}
    for tag_id, value in exif_ifd.items():
        name = ExifTags.TAGS.get(tag_id, tag_id)
        tags[name] = value
    return tags


def _downsample_to_working_resolution(image: Image.Image) -> Image.Image:
    """Resize `image` so its long edge is at most `WORKING_RESOLUTION_MAX_DIM`.

    A no-op when the source is already at or under that size (every test
    fixture in this repo is <=200px, so this never fires in the suite -
    exercised instead by `tests/test_frame.py`'s synthetic 8000x6000 case).
    LANCZOS, not the `BOX` resample `_imaging.difference_hash` uses for its
    own shrink: this is a full working-resolution copy every detector reads
    fine detail from, not a coarse hash input.
    """
    long_edge = max(image.width, image.height)
    if long_edge <= WORKING_RESOLUTION_MAX_DIM:
        return image
    scale = WORKING_RESOLUTION_MAX_DIM / long_edge
    new_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def load_frame(path: str | Path, frame_id: str | None = None) -> Frame:
    """Decode an image file into a Frame at working resolution.

    EXIF is read from the original file before any resize - Pillow's resize
    does not reliably carry EXIF through, and even if it did, the metadata
    detectors (F01's DigitalZoomRatio, F03's FocalLength/timestamps) need
    the original capture's values, not anything a resize could touch.
    """
    path = Path(path)
    with Image.open(path) as image:
        exif = _flatten_exif(image)
        rgb = np.array(_downsample_to_working_resolution(image.convert("RGB")))
    return Frame(frame_id=frame_id or path.stem, path=path, rgb=rgb, exif=exif)
