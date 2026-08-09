# builder-002 — 2026-08-09

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 1/20 builder sessions used, hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: absent (no CRITIC session has run yet).
- `DECISIONS.md`: open count 2 (D-003, D-004) — below the 5-item halt threshold.
- Most recent `logs/` entry: `builder-001.md` (schema, QUEUE item 1). Its PR #1
  is merged into `main`; this session's branch was already up to date with it.

## What moved
Implemented QUEUE.md Stage 1, item 2 — the detector registry:

- `src/picstory/detectors/base.py` — the registration mechanism only: a
  module-level dict keyed by taxonomy ID, a `register(id)` decorator that
  populates it (raises on duplicate registration), `get(id)`/`registered_ids()`
  for lookup. No detection logic here by design — items 3-4 own that, and
  leaving the detector call signature as `Callable[..., Finding | None]`
  means those items can settle what a detector actually receives without
  touching this module.
- `src/picstory/detectors/{f01..f15,s01..s04,r01}.py` — one module per
  taxonomy ID, each claiming exactly its own registry slot. Per CLAUDE.md's
  explicit warning ("a stub returning nothing is not an implementation"),
  every stub raises `DetectorNotImplemented` naming the QUEUE item that owns
  its real logic (3 for local heuristics, 4 for API-vision items, 8 for
  F03's near-duplicate grouping, which is Stage 2) — none pass silently as
  a negative result.
- `src/picstory/detectors/__init__.py` — imports all 20 submodules for
  their registration side effect, re-exports the registry API.
- `tests/test_detector_registry.py` — 6 tests on the registry mechanism
  itself: registered IDs match `taxonomy_ids()` exactly (no missing, no
  extra/typo'd IDs), unknown-ID lookup raises `KeyError`, duplicate
  registration raises `ValueError`, every current stub raises
  `DetectorNotImplemented` on call, and the package re-exports match the
  base module's objects. Not per-ID named tests (`test_f01_...`) — those
  are QUEUE item 6's job and check detection substance, not registration.

## What is open
- QUEUE items 3-6 (local detectors, API-call detectors, CLI, per-detector
  tests) not started — this session did item 2 only.
- `tests/test_taxonomy_coverage.py::test_every_id_has_detector_and_named_test`
  still fails, expected: `missing_detector` is now empty (every ID appears
  in `src/`), but `missing_test` still lists all 20, since no test function
  names embed an ID yet. Stays red until item 6 lands named tests alongside
  items 3-4's real detector logic — matches the pattern noted in
  `logs/builder-001.md`.
- DECISIONS.md D-003 (taxonomy visibility) and D-004 (pricing) remain open,
  unchanged this session. Neither is blocking.

## Test count
26 collected: 25 passed, 1 failed (the pre-existing coverage guard,
expected per above — 19 schema tests + 1 passing taxonomy-parses test
unchanged from item 1, plus this session's 6 new registry tests, all
passing except the named-test half of the coverage guard).
