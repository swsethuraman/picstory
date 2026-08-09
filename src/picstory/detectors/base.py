"""Detector registration mechanism (QUEUE.md Stage 1, item 2).

A detector is a callable registered against exactly one taxonomy ID. This
module only provides the registry itself - the mapping and the decorator
that populates it. It carries no detection logic; that is items 3 (local
heuristics) and 4 (Anthropic API vision calls) in QUEUE.md.

The input/output shape a detector callable takes is deliberately left open
here (`DetectFn = Callable[..., Finding | None]`) so items 3-4 can settle
what a detector actually receives (image data, EXIF, a decoded frame...)
without this module needing to change.
"""

from __future__ import annotations

from typing import Callable

from picstory.schema import Finding

DetectFn = Callable[..., "Finding | None"]

_REGISTRY: dict[str, DetectFn] = {}


class DetectorNotImplemented(NotImplementedError):
    """Raised by a registered stub that has claimed an ID but does no detection yet.

    Distinct from a detector silently returning None - CLAUDE.md is explicit
    that "a stub returning nothing is not an implementation." A stub in this
    registry must say so loudly, not pass as a real (always-negative) result.
    """


def register(taxonomy_id: str) -> Callable[[DetectFn], DetectFn]:
    """Decorator: register `fn` as the detector for `taxonomy_id`.

    Raises if the ID is already registered - one module per taxonomy ID
    (QUEUE.md item 2), never two competing detectors for the same finding.
    """

    def wrap(fn: DetectFn) -> DetectFn:
        if taxonomy_id in _REGISTRY:
            raise ValueError(
                f"detector for {taxonomy_id!r} already registered "
                f"(by {_REGISTRY[taxonomy_id].__module__})"
            )
        _REGISTRY[taxonomy_id] = fn
        return fn

    return wrap


def get(taxonomy_id: str) -> DetectFn:
    """Look up the detector registered for `taxonomy_id`."""
    try:
        return _REGISTRY[taxonomy_id]
    except KeyError:
        raise KeyError(f"no detector registered for {taxonomy_id!r}") from None


def registered_ids() -> frozenset[str]:
    """The set of taxonomy IDs with a registered detector (stub or real)."""
    return frozenset(_REGISTRY)
