# builder-008 — 2026-08-11

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK - 7/20 builder sessions used
  (unchanged at session start; this session is the 8th), hard date
  2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-002, covers builder-003-006 through
  `1a78643`, predates builder-007). Headline: "no plausible-substitute
  pattern found." Its two flagged items (F09's center-third subject proxy,
  R01's stale QUEUE-item-3 citation) are notes for whoever next touches
  those specific files - neither is F03, so neither blocks this session.
- `DECISIONS.md`: open count 0 at session start (D-001-D-006 all `RULED`).
  No new entry added this session.
- Most recent `logs/` entry: `builder-007.md` (item 7, batch input).
- Branch `claude/brave-clarke-96g22b` was already up to date with
  `origin/main` (`f948387`, builder-007's merge) at session start; worked
  directly on it per this session's assigned branch.

## What moved
QUEUE.md item 8: "F03 near-duplicate grouping (perceptual hash + EXIF
timestamps/focal length deltas)." First unblocked item - items 1-7 done,
item 8 was next.

TAXONOMY.md's F03 Detection text ("2-5 consecutive frames of the same
subject with no change in position, focal length, or angle. Copies, not
variations.") names a property of a *run* of frames, not of any single
photo - the same shape of gap D-005 named for F14/S03, except F03 was
never misrouted into Stage 1 the way those two were; QUEUE.md always
placed it here, in Stage 2, once batch context (item 7) exists. So this
session is the first real implementation, not a deferral.

1. **`src/picstory/duplicates.py`** (new): the grouping engine.
   `group_near_duplicates(frames) -> list[list[Frame]]` walks the batch in
   order and matches each frame against only its immediate predecessor
   ("consecutive," not "similar to anything earlier in the batch") on three
   signals: a dHash perceptual-hash Hamming distance (proxy for "no change
   in position or angle" - calibrated against synthetic frames at
   distance 0-7 for near-identical vs. 29+ for a real reframe, see the
   module docstring), EXIF `FocalLength` equality (the literal "no change
   in focal length" clause), and EXIF timestamp adjacency (the literal
   "consecutive" clause). Missing EXIF tags don't sink an otherwise-matching
   pair - same "absence isn't evidence" rule F01 already uses for
   `DigitalZoomRatio`. Runs cap at 5 frames (TAXONOMY.md's stated upper
   bound); a run needs at least 2 frames to be returned at all (a single
   frame isn't a "copy" of anything).

2. **`src/picstory/detectors/f03.py`** (real implementation, replacing the
   stub): `detect(frame, *, batch=None)` looks `frame` up in
   `group_near_duplicates(batch)`'s groups and returns a `Finding` naming
   the run size when it's in one. Requires `batch` - raises `ValueError`
   (not `DetectorNotImplemented`) when it's missing, since the logic is
   real and simply cannot run without the frames around it. This is a
   different signature from every other detector (`detect(frame)`), which
   is why:

3. **`scripts/analyze.py`**: F03 joins R01 in `_NOT_PER_FRAME` -
   structurally excluded from the per-frame sweep, for the same reason R01
   already is (needs context this one-photo-at-a-time module never has).
   Also factored the detected/clean/stub/error classification out of
   `run_analysis`'s loop body into a new `classify_call()` helper, so
   `analyze_batch.py` can reuse the exact same rules for F03's differently-
   shaped call instead of re-deriving them.

4. **`scripts/analyze_batch.py`**: added `_merge_f03()`, which runs after
   the per-frame sweep and calls F03 once per frame against the real batch
   (`detect(frame, batch=frames)`), using `classify_call()` so F03 shows up
   in a batch report exactly like any other ID. `run_batch_analysis()`
   always strips "F03" out of whatever `ids` it's given before the
   per-frame sweep, so passing it explicitly can't double-report it through
   `run_analysis`'s single-frame call (which would hit the real
   `ValueError` and misclassify a working detector as "error").

5. **Tests**: `tests/test_duplicates.py` (15 tests, new) covers the
   grouping engine directly - consecutive runs, a real reframe breaking a
   run, a gap not bridging two separated duplicates, the 5-frame cap,
   focal-length and timestamp deltas breaking an otherwise-visual match,
   missing-tag tolerance - and the detector wiring (`detect()` flags a
   frame in a run, returns `None` outside one, raises `ValueError` without
   `batch`). Updated three existing test files for the new exclusion/merge
   behavior: `test_cli_analyze.py` (evaluable_ids() now excludes F03 too,
   18 not 19 IDs), `test_cli_analyze_batch.py` (fake lookups need an "F03"
   entry now that `_merge_f03` always calls it; added tests for the
   real-batch-per-call and ids-override-stripping behavior), and
   `test_detector_registry.py` (F03 removed from `_STILL_STUBBED`, added a
   test pinning that its registry-level call raises `ValueError` not
   `DetectorNotImplemented`).

## Test count
133 collected: 132 passed, 1 expected fail
(`test_every_id_has_detector_and_named_test`, `missing_test = ['F14',
'R01', 'S03']` - F03 dropped off this list, the other three unchanged from
builder-007/critic-002 and still correctly deferred per D-005/R01's
own-item status). Full suite run directly this session
(`uv run pytest -q`, ~3m13s - same real-registry-without-a-key cost prior
sessions' end-to-end tests already pay, unchanged by this session's work).

## What's open
- QUEUE.md items 9-12 (ranking/shortlist, session habit, CMP comparison,
  the profile) - untouched this session.
- Same F14/S03/R01 stub gap as before (D-005 for F14/S03; R01 not yet
  scheduled). F03 is no longer in that group.
- REVIEW.md's two outstanding notes (F09 center-third proxy, R01's stale
  QUEUE-item-3 citation, both from critic-002) are still open for whoever
  next touches those specific files - neither was touched this session.
- DECISIONS.md open count: 0. No entry opened or closed this session - F03
  turned out to be fully implementable with the batch context item 7 gave
  it, no ambiguity needing a ruling.
- Item 9 ("ranking + shortlist... F-findings as disqualifiers") can now
  draw on real F03 findings from a batch run, not just a stub.
