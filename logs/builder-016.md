# builder-016 — 2026-08-15

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 15/25 builder sessions
  used (this session is the 16th), hard date 2026-08-22 (stale — see below).
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-004, covers through builder-015 / no code
  changes that session). No open note named this session's scope (F09's
  center-third proxy remains open, untouched, unrelated).
- `DECISIONS.md`: open count 0 at session start (D-001–D-009 all `RULED`,
  D-008a/b/c and D-009 added since critic-004 by the owner, 15 Aug 2026,
  for phase 2). Nothing this session hit an ambiguity needing a new entry.
- Most recent `logs/` entry: `builder-015.md`.
- Branch: `claude/epic-meitner-6ub3v4` had no remote counterpart yet but was
  exactly even with `origin/main` at session start (`e2e085a`, "phase 2
  opens: queue items 15-19..."), which already carries D-008a/b/c, D-009's
  rulings and QUEUE.md Stage 5 (items 15-19).
- `scripts/check_hard_stop.py` printed "OK - 15/25 ... hard date
  2026-08-22" — `MAX_BUILDER_SESSIONS` had been updated to 25 (matches
  CLAUDE.md's current "25 builder worklogs"), but the `HARD_DATE` constant
  it actually compares `today` against was still `date(2026, 8, 22)`, not
  the `29 August 2026` CLAUDE.md's own "Hard stop" section currently
  documents (extended alongside the session count, 15 Aug 2026, per that
  same section). Not a blocking condition today (2026-08-15 is before
  either date), but a real latent bug: a session run between 23-29 Aug
  would have hit an incorrect HALT the owner's own ruling didn't intend.
  Fixed directly this session (`scripts/check_hard_stop.py`'s `HARD_DATE`
  now `date(2026, 8, 29)`, docstring corrected to match) rather than left
  for a future hygiene sweep — this is the script every session's "Start
  here" step depends on for correctness, not scope creep into QUEUE.md's
  own items. No test exercises this script directly (checked: no
  `test_check_hard_stop.py`, no reference to `HARD_DATE`/the literal date
  anywhere under `tests/`), so nothing needed updating for the fix itself;
  re-ran the script after the fix and confirmed the printed date now
  matches CLAUDE.md.

## What moved
QUEUE.md Stage 5, item 15 ("the resolution contract") — the top unblocked
item; items 1-14 are all implemented (confirmed by builder-015), and item
15 was untouched (no downsampling anywhere in `frame.py` at session start,
confirmed directly). Implemented all six sub-parts:

- **(a)** `frame.load_frame` now reads EXIF from the original file, then
  downsamples pixel data to `WORKING_RESOLUTION_MAX_DIM` (2000px long edge,
  new module constant) via PIL LANCZOS before building the `Frame`. Small
  photos (every existing fixture, all <=200px) pass through unchanged — a
  new `tests/test_frame.py` exercises the actual downsample path with a
  synthetic 8000x6000 on-disk JPEG. `batch.load_batch` needed no code
  change (it already delegates to `load_frame`); added one docstring
  sentence noting the contract it inherits.
- **(b)** `Frame.luminance` is now a `functools.cached_property` (was a
  plain `@property`, recomputed on every access). Added `Frame.dhash(
  hash_size)`, memoized per hash_size on a new `_hash_cache` field
  (`compare=False`, so it doesn't affect `Frame` equality) — `f03.py` and
  `subject_clusters.py` (both use `hash_size=8`) now call this instead of
  `_imaging.difference_hash(frame.luminance, ...)` directly, so CMP's own
  re-grouping (`scripts/analyze_batch.py`'s `_run_comparisons` calling
  `group_near_duplicates` a second time over the same batch) reuses the
  first pass's hashes instead of recomputing PIL's resize per call.
- **(c)** `_vision._encode_jpeg` gained its own independent ceiling:
  resize-if-needed to `_MAX_UPLOAD_DIM` (1500px), then a quality-reduction
  loop (85 → 30 in steps of 15) enforcing a hard `_MAX_PAYLOAD_BYTES` (4MB)
  ceiling — explicitly defense in depth per the queue item's own framing,
  not a substitute for (a). Three new direct tests in
  `test_vision_detectors.py` (oversized-frame resize, small-frame passthrough,
  a high-entropy-noise worst case against the byte ceiling).
- **(d)** `Frame.path` is retained; its docstring and the module docstring
  both name it as the lazy native-resolution escape hatch, undocumented as
  "needed" by any specific detector today (none has a demonstrated need).
- **(e)** `tests/test_frame.py` (new file, 7 tests): the 8000x6000 working-
  res-ingestion case named by the queue item, an EXIF-survives-resize case,
  cached-luminance/memoized-dhash identity checks, an F01-at-working-
  resolution regression (below), and a timing-bounded 5-frame, fully
  offline end-to-end (`load_batch` + `run_batch_analysis` on 4000x3000
  synthetic JPEGs, budget 30s). This last one is the test that would have
  caught the capstone regression directly: before (a), it never terminated
  in reasonable time.
- **(f)** F01's docstring now has a "Resolution note" explaining why it
  deliberately does *not* call `_imaging.downsample` itself (would erase
  the fine detail it's checking for softness in, unlike F02/F08/S03), with
  the empirical check that `SOFT_THRESHOLD` holds unchanged at working-
  resolution scale (a new `test_f01_discriminates_sharp_from_soft_at_working_resolution`
  in `test_frame.py`, same checkerboard/box-blur pattern
  `test_local_detectors.py` already uses for F01, run at 2000px instead of
  200px) and a disclosed limitation the fix doesn't cover (native-detail
  finer than the working-resolution downsample's own Nyquist limit can get
  anti-aliased away before F01 ever sees it). Checked F02/F07/F08/F09/F10/
  F12/S03 for the same resolution-sensitivity: F02/F08/S03 already call
  `_imaging.downsample` to their own fixed scale (already
  resolution-independent of whatever `WORKING_RESOLUTION_MAX_DIM` is); F07/
  F09/F10/F12 are grid-fraction or percentile-based (naturally
  resolution-robust) — none of those needed a docstring addition.

**A real finding surfaced while building the item 15e end-to-end test, worth
recording even though it didn't require a DECISIONS.md entry (not an
ambiguity, a measured fact):** an early manual benchmark of
`run_batch_analysis` on 5 large frames (run directly via `python`, not
`pytest`) took 124s and profiled almost entirely to real, live
`api.anthropic.com` network calls — because this sandbox's
`PICSTORY_VISION_KEY` is genuinely live (same as critic-004's finding for
builder-011's sandbox) and a bare script doesn't get `tests/conftest.py`'s
autouse live-call block. That was 46 unintended, spend-cap-metered live
calls from an ad-hoc debug script, not from the test suite or a detector
doing its job — a mistake on my part; I should have blocked
`anthropic.Anthropic` in the benchmark from the start, the same way the
test suite does. Re-run with the calls blocked: `run_batch_analysis` on the
same 5 frames took 5.6s. That 5.6s figure (not 124s) is the real, meaningful
evidence the resolution contract fixes the capstone's non-termination — the
124s number is not a code finding at all, just a reminder to never run
ad-hoc scripts against this sandbox's real key without the same offline
discipline the test suite already enforces.

## DECISIONS.md
No new entries. Every one of item 15's six sub-parts was implementable
without a genuine open question — QUEUE.md item 15's own text was specific
enough to execute directly, and where a judgment call was needed (F01's
threshold: adjust the number, or disclose the calibration is scale-
specific), the evidence pointed cleanly to "disclose, don't change" rather
than leaving it ambiguous. Open count: 0 (unchanged).

## Test count
276 collected: 275 passed, 1 expected fail
(`test_every_id_has_detector_and_named_test`, `missing_test = [F14]` —
unchanged, the documented intended end state of this guard per D-007).
Growth: 266 → 276 (+10: 7 in new `tests/test_frame.py`, 3 in
`tests/test_vision_detectors.py`). Full suite run directly
(`uv run pytest -q`), ~15-17s (up from builder-015's ~4.2s — the new
working-at-scale tests, especially the timing-bounded 5-frame end-to-end,
are the reason; still well within reason for a suite that must stay
offline and fast).

## What's open
- QUEUE.md item 16 (keeper election per D-008a) is next, unblocked, not
  started this session.
- REVIEW.md's F09 center-third-proxy note: still open, still untouched
  (unrelated to this session's scope).
- F14 stays a `DetectorNotImplemented` stub, per D-007's ruling.
- No Anthropic API calls made by any detector this session (item 15's work
  is entirely local: resolution, caching, byte-ceiling logic). The 46
  unintended live calls noted above were from my own ad-hoc benchmark
  script outside the test suite, not from application code — flagged above
  for the record, not a DECISIONS.md item.

## Files touched
`src/picstory/frame.py`, `src/picstory/batch.py`,
`src/picstory/detectors/_vision.py`, `src/picstory/detectors/f01.py`,
`src/picstory/detectors/f03.py`, `src/picstory/detectors/subject_clusters.py`,
`scripts/check_hard_stop.py` (HARD_DATE fix, see start-of-session checks),
`tests/test_frame.py` (new), `tests/test_vision_detectors.py`,
`logs/builder-016.md` (this file).
