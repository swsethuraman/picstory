# builder-007 — 2026-08-11

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 6/20 builder sessions used
  (unchanged at session start; this session is the 7th), hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-002, covers builder-003–006 through `1a78643`).
  No findings requiring action this session — headline was "no
  plausible-substitute pattern found"; the two flagged items (F09's
  center-third subject proxy, R01's stale QUEUE-item citation) are both
  review notes for whoever next touches those specific files, not blockers
  for this session's work.
- `DECISIONS.md`: open count 0 at session start (D-001–D-006 all `RULED`).
  No new entry added this session.
- Most recent `logs/` entry: `critic-002.md`.
- Branch `claude/brave-clarke-pherlp` did not exist on `origin`; created
  fresh, tracking main at the critic-002 merge (`09b7d0b`).

## What moved
Worked QUEUE.md top-down. Items 1–6 (Stage 1) are complete except for the
already-adjudicated deferrals (F03, F14, R01, S03 — batch-relative per
D-005/critic-002, correctly still `DetectorNotImplemented` stubs). Item 7
is the first unblocked item: "Batch input (5–50 photos); per-frame analysis
reusing Stage 1."

1. **`src/picstory/batch.py`** (new): `load_batch(paths) -> list[Frame]`.
   Enforces the 5–50 photo range QUEUE.md item 7 names (`BatchSizeError`
   outside it, including the empty-list case) and assigns each decoded
   `Frame` an index-prefixed `frame_id` (`"00_<stem>"`, `"01_<stem>"`, ...).
   This exists because `frame.load_frame`'s default `frame_id` is a bare
   filename stem — fine for Stage 1's one-photo-at-a-time CLI, but two
   photos from different folders sharing a stem would collide once multiple
   `FrameAnalysis` entries land in one `AnalysisOutput`. Order is preserved
   (caller's input order), since later stages (ranking, comparison) will
   want a stable ordering this function doesn't reshuffle.

2. **`scripts/analyze_batch.py`** (new): the batch CLI. Deliberately does
   *not* reimplement per-ID dispatch — `run_batch_analysis` calls
   `analyze.run_analysis` once per frame (same detected/clean/stub/error
   classification, same R01 exclusion as batch/conditional-not-per-frame)
   and collects the per-frame `FrameAnalysis` results into one
   `AnalysisOutput`. This is literally "reusing Stage 1," not a parallel
   implementation of it. `pick` and `habit` stay `None` on the output, same
   as Stage 1's CLI and for the same reason: near-duplicate grouping (F03,
   item 8), ranking/shortlist (item 9), and the session habit (item 10) are
   separate, later queue items this one does not touch. Output goes through
   `_report.py` per CLAUDE.md's output-discipline rule — full per-frame
   breakdown to `outputs/reports/`, ≤3 stdout lines.

3. **Tests**: `tests/test_batch.py` (7 tests: min/max/empty size
   enforcement, frame_id uniqueness across colliding stems, index-prefixed
   ordering) and `tests/test_cli_analyze_batch.py` (8 tests: aggregation
   correctness, per-frame finding isolation — one detector firing on frame
   B doesn't leak into frames A/C's results — pick/habit still None, report
   rendering, and three end-to-end `main()` runs through real on-disk
   images: happy path, batch-size-rejection failure, and bad-path failure).
   Detector injection follows the existing `detector_lookup` pattern from
   `test_cli_analyze.py`/`_vision.py`'s `VisionCaller` — offline throughout,
   no real registry/network touched except in the three end-to-end `main()`
   tests, which mirror `test_cli_analyze.py`'s own end-to-end test in using
   the real registry (those per-detector calls fail fast with no API key
   available, same as Stage 1's CLI test already does; not a new pattern).

## Test count
122 collected: 121 passed, 1 failed (expected — the taxonomy-coverage guard,
`missing_test = [F03, F14, R01, S03]`, unchanged from critic-002's report,
none of which this session's work claims to address). Net +21 over
critic-002's reported 101 (test_batch.py: 7, test_cli_analyze_batch.py: 8,
plus test_taxonomy_coverage.py picks up "batch"/"analyze_batch" test names
— checked no new false-positive ID matches). Full suite run directly this
session (`uv run pytest -q`); ran long (~3m18s) because the three real-registry
end-to-end tests exercise all 9 vision-call detectors per frame with no
network key present — same cost `test_cli_analyze.py`'s existing end-to-end
test already pays, just now paid across 5 frames instead of 1. Not a new
concern; flagging the wall-clock in case a future session wants to trim it
(e.g. injecting a lookup there too), but it does not violate "runs offline."

## What's open
- QUEUE.md items 8–12 (F03 near-duplicate grouping, ranking/shortlist,
  session habit, CMP comparison, the profile) — untouched this session.
- Same F14/S03/R01/F03 stub gap as before, now also item 7's batch context
  exists structurally (frame_id assignment, per-frame aggregation) — item 8
  (F03 grouping) can build directly on `picstory.batch.load_batch`'s output
  next.
- `tests/test_taxonomy_coverage.py::test_every_id_has_detector_and_named_test`
  still fails, expected, same 4 IDs as builder-006/critic-002 left it.
- DECISIONS.md open count: 0. No entry opened or closed this session.
- REVIEW.md's two outstanding notes (F09 center-third proxy, R01's stale
  QUEUE-item-3 citation) are still open for whoever next touches those
  files — neither blocks item 7 and neither was touched this session.
