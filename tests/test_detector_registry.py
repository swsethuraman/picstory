"""Detector registry tests (QUEUE.md Stage 1, item 2).

Checks the registration mechanism itself: every taxonomy ID has exactly one
registered detector slot, unknown IDs are rejected, and duplicate
registration is rejected. Does not check detection substance - stubs raise
DetectorNotImplemented at this stage, which is expected until QUEUE.md
items 3-4 land real logic. Per-ID named tests of real detector behavior are
QUEUE.md item 6.
"""

from __future__ import annotations

import pytest

from picstory import detectors
from picstory.detectors.base import DetectorNotImplemented, get, register, registered_ids
from picstory.schema import taxonomy_ids


def test_registry_covers_every_taxonomy_id() -> None:
    assert registered_ids() == taxonomy_ids()


def test_registry_has_no_extra_ids() -> None:
    # Symmetric with the above, but fails loudly and specifically if a
    # detector module registers an ID that isn't in the frozen taxonomy
    # (typo, or an ID invented outside TAXONOMY.md).
    extra = registered_ids() - taxonomy_ids()
    assert not extra, f"registered detector IDs not in TAXONOMY.md: {extra}"


def test_unknown_id_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        get("F99")


def test_duplicate_registration_rejected() -> None:
    # register() mutates module-level state, so this must clean up after
    # itself - otherwise the probe ID leaks into every later test in this
    # process (registered_ids(), the unimplemented-stub sweep, ...).
    from picstory.detectors import base as base_module

    @register("__test_dup__")
    def first(*_a, **_k):
        return None

    try:
        with pytest.raises(ValueError):

            @register("__test_dup__")
            def second(*_a, **_k):
                return None
    finally:
        del base_module._REGISTRY["__test_dup__"]


# QUEUE.md item 3 (local metadata/pixel detectors) has landed real logic for
# seven IDs (tests/test_local_detectors.py), item 4 (API-vision detectors)
# for nine more (tests/test_vision_detectors.py), item 8 for F03
# (tests/test_f03_safety_copies.py - a batch-level detector, so it is
# exercised there rather than through this file's zero-arg stub-call
# pattern below), item 13 for R01 (tests/test_r01_haze_rule.py - also
# batch-level, also exercised there rather than here), and (this session,
# DECISIONS.md D-007) for S03 (tests/test_s03_tight_framing.py - also
# batch-level). Remaining stub: F14 stays deferred per D-007's ruling,
# standing for the remainder of the experiment - its honest precondition
# (EXIF GPS location clustering) is deliberately out of scope. Unlike every
# ID above it, this is the documented, intended end state of this guard for
# this experiment, not a "land it later" placeholder.
_STILL_STUBBED = frozenset({"F14"})


def test_unimplemented_stub_raises_not_implemented() -> None:
    # Pins the "loud stub" contract (base.py) - a stub must raise rather
    # than silently returning a fake negative result - for every ID that
    # hasn't had real detection logic land yet.
    assert _STILL_STUBBED <= registered_ids()
    for taxonomy_id in _STILL_STUBBED:
        detector = get(taxonomy_id)
        with pytest.raises(DetectorNotImplemented):
            detector()


def test_detectors_package_exposes_registry_api() -> None:
    assert detectors.get is get
    assert detectors.registered_ids is registered_ids
