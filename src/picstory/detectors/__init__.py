"""Detector registry (QUEUE.md Stage 1, item 2).

One module per taxonomy ID (F01-F15, S01-S04, R01), each registering itself
by ID via `base.register`. Importing this package imports every submodule
for its registration side effect, then exposes the registry lookups.

Modules under here may currently be structural stubs - they claim their ID's
registry slot and raise `DetectorNotImplemented` rather than returning a
result. Real detection logic (local heuristics, then Anthropic API vision
calls) lands in QUEUE.md items 3-4. A stub is a claimed slot, not an
implementation (CLAUDE.md) - `test_taxonomy_coverage.py` and the CRITIC are
what separate the two.
"""

from __future__ import annotations

from picstory.detectors import (  # noqa: F401 - imported for registration side effects
    f01,
    f02,
    f03,
    f04,
    f05,
    f06,
    f07,
    f08,
    f09,
    f10,
    f11,
    f12,
    f13,
    f14,
    f15,
    r01,
    s01,
    s02,
    s03,
    s04,
)
from picstory.detectors.base import DetectorNotImplemented, get, registered_ids

__all__ = ["DetectorNotImplemented", "get", "registered_ids"]
