"""Frame loading: decode an image into pixel data + EXIF for detectors.

Local detectors (QUEUE.md item 3) all need the same two things from a photo
- decoded RGB pixels and parsed EXIF tags - so decoding happens once here
rather than once per detector. The detector call signature settled by this
module: `detect(frame: Frame) -> Finding | None`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import ExifTags, Image


@dataclass
class Frame:
    """A decoded photo: RGB pixels plus flattened EXIF tags, by name."""

    frame_id: str
    path: Path
    rgb: np.ndarray  # (height, width, 3) uint8
    exif: dict

    @property
    def height(self) -> int:
        return self.rgb.shape[0]

    @property
    def width(self) -> int:
        return self.rgb.shape[1]

    @property
    def luminance(self) -> np.ndarray:
        """Rec. 601 luma, float64, same (height, width) shape as rgb."""
        r = self.rgb[..., 0].astype(np.float64)
        g = self.rgb[..., 1].astype(np.float64)
        b = self.rgb[..., 2].astype(np.float64)
        return 0.299 * r + 0.587 * g + 0.114 * b


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


def load_frame(path: str | Path, frame_id: str | None = None) -> Frame:
    """Decode an image file into a Frame."""
    path = Path(path)
    with Image.open(path) as image:
        exif = _flatten_exif(image)
        rgb = np.array(image.convert("RGB"))
    return Frame(frame_id=frame_id or path.stem, path=path, rgb=rgb, exif=exif)
