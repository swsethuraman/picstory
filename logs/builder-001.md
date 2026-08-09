# builder-001 — 2026-08-09

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 0/20 builder sessions used, hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: absent (no CRITIC session has run yet).
- `DECISIONS.md`: open count 2 (D-003, D-004) — below the 5-item halt threshold.
- Most recent `logs/` entries: `setup-2026-08-09.md`, `setup-2026-08-09b.md` (human setup, counts toward nothing).

## What moved
Implemented QUEUE.md Stage 1, item 1 — the analysis output schema:

- `src/picstory/schema.py` — dataclasses `Finding`, `FrameAnalysis`, `Pick`,
  `Habit`, `AnalysisOutput`.
  - `Finding.taxonomy_id` must be one of the 20 IDs frozen in TAXONOMY.md or
    `"unclassified"` (section U); `unclassified` findings require a
    non-empty free-text description, classified findings don't.
  - `Pick.reasons` must be S-item IDs, `Pick.disqualifiers` must be F-item
    IDs (matches how TAXONOMY.md says the pick/share-list is built).
  - `Habit.taxonomy_id` must be an F- or S-item (R01 is a conditional rule,
    not a recurring habit, per TAXONOMY.md §R).
  - `schema_version` field from day one (`"1.0"`); `AnalysisOutput` rejects
    any other value.
  - `pick` and `habit` are optional on `AnalysisOutput` — Stage 1 runs one
    photo at a time, both need a batch to be meaningful (Stage 2, QUEUE
    items 9-10).
  - `taxonomy_ids()` parses TAXONOMY.md directly (single source of truth)
    instead of duplicating the ID list in Python.
- `schema/analysis.json` — JSON Schema mirror of the above, for external
  validation/documentation. Its ID enum is statically written (JSON can't
  parse TAXONOMY.md at authoring time) but guarded against drift by a test
  that compares it to `taxonomy_ids()`.
- `tests/test_schema.py` — 19 tests: valid/invalid findings, unclassified
  description requirement, pick/habit ID-class validation, version
  rejection, JSON round-trip, and the schema-file drift guard.

Committed as `fae7457`. Pushed to `claude/determined-curie-2z83ie`. Opened
PR #1 (`https://github.com/swsethuraman/picstory/pull/1`), titled
`builder-001` per instructions.

## What is open
- QUEUE items 2-6 (detector registry, local detectors, API-call detectors,
  CLI, per-detector tests) are not started. This session did item 1 only —
  "one item per commit where feasible."
- DECISIONS.md D-003 (taxonomy visibility) and D-004 (pricing) remain open,
  unchanged this session. Neither is blocking.
- `tests/test_taxonomy_coverage.py::test_every_id_has_detector_and_named_test`
  still fails: no detectors exist under `src/` yet. This is expected at
  this stage, not a regression — CLAUDE.md forbids satisfying it with stub
  detectors ("a stub returning nothing is not an implementation"), so it
  stays red until QUEUE items 2-4 land real detector logic.

## Test count
19 passed (new, `tests/test_schema.py`), 1 failed (pre-existing coverage
guard, expected per above), 20 collected total.
