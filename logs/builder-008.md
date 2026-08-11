# builder-008 — 2026-08-11

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 7/20 builder sessions used
  (this session is the 8th), hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-002, covers builder-003–006 through `1a78643`,
  predates builder-007's item 7 work). Headline was "no plausible-substitute
  pattern found"; its two flagged notes (F09's center-third proxy, R01's
  stale QUEUE-item-3 citation) are both for whoever next touches those
  specific files — neither is item 8, so neither blocked this session.
- `DECISIONS.md`: open count 0 at session start (D-001–D-006 all `RULED`).
  No new entry added this session.
- Most recent `logs/` entry: `builder-007.md` (item 7: batch input CLI).
- Branch `claude/brave-clarke-d0bj0u` already existed on `origin`, in sync
  with `main` at the PR #9 merge (`f948387`, builder-007's work) — no fresh
  branch needed, continued directly on it.

## What moved
QUEUE.md Stage 1 (items 1–6) and item 7 (batch input) were already done.
Item 8 is the next unblocked item: "F03 near-duplicate grouping (perceptual
hash + EXIF timestamps/focal length deltas)."

F03's Detection text ("2–5 consecutive frames of the same subject with no
change in position, focal length, or angle. Copies, not variations.") names
a property of a *run* of frames, not any single photo — the same shape of
gap DECISIONS.md's D-005 identified for F14/S03. Unlike those two, batch
context now exists (item 7's `picstory.batch.load_batch`), so F03 gets
implemented for real this session rather than staying a deferred stub.

1. **`src/picstory/detectors/_imaging.py`**: added `difference_hash`
   (dHash via PIL's box-resampling resize to a `hash_size` x `hash_size`
   bit grid — box resampling specifically, not nearest-neighbor, because an
   early nearest-neighbor version was pathologically sensitive to ordinary
   pixel noise; verified this with a throwaway numpy script before settling
   on PIL's BOX filter) and `hamming_distance`.

2. **`src/picstory/detectors/f03.py`** (was a stub since builder-002):
   `group_near_duplicates(frames)` walks consecutive pairs and requires (a)
   a difference-hash distance ≤6/64 bits — the proxy for "no change in
   position/angle," disclosed as a proxy the same way REVIEW.md flagged
   F09's center-third subject approximation, since there's no camera-pose
   data to check position/angle directly; (b) EXIF `FocalLength` delta
   ≤0.5mm *when both frames have the tag*; (c) EXIF timestamp delta ≤30s
   *when both frames have a timestamp*. (b) and (c) are non-blocking when
   metadata is missing on either side — same "can't evaluate ≠ assume the
   opposite" reasoning F01 already uses for `DigitalZoomRatio`. Grouping
   does not cap runs at 5 despite the Detection text's "2–5": read that as
   describing the typical size in the source examples (Rathaus x3,
   Stephansdom x5), not a hard boundary — same treatment critic-002 gave
   F02's "typically consistent across consecutive frames." `detect(frames)`
   wraps this: the first frame in a run is the kept shot (TAXONOMY.md's
   correction text frames it that way — "One frame, then deliberately
   change something"), the rest get the F03 `Finding`.

3. **`scripts/analyze.py`**: F03 joins R01 in `_NOT_PER_FRAME`
   (`evaluable_ids()` now excludes both), but documented as a *different*
   reason from R01's — R01 is a batch/conditional trigger; F03's real
   `detect()` takes a whole batch and structurally cannot run through this
   module's one-frame-in dispatch loop at all, not even to report "clean."

4. **`scripts/analyze_batch.py`**: `run_batch_analysis` now runs F03 once
   per batch, after the per-frame sweep, via the same injected
   `detector_lookup` tests already use — classified detected/clean/stub/
   error exactly like every other ID (`_run_f03` mirrors
   `analyze.run_analysis`'s per-ID try/except), and merges any findings
   into their frame's `FrameAnalysis.findings`. `ids` still governs only
   the per-frame sweep; F03 always runs regardless, since it isn't part of
   that sweep.

5. **Tests**: `tests/test_f03_safety_copies.py` (10 tests) exercises
   `group_near_duplicates`/`detect` directly — grouping consecutive
   near-identical frames, a moved-subject frame *not* joining the group, a
   focal-length change breaking an otherwise-matching pair, a missing
   focal-length tag *not* blocking a match, a timestamp gap breaking a
   pair, close timestamps not blocking one, only non-keeper frames getting
   the Finding, registry wiring. Fixtures use a textured checkerboard-plus-
   bright-block scene, not a flat one — an early version with a flat scene
   made the noise-robustness check flaky (most adjacent-pixel deltas sit at
   exactly zero on a flat image, so tiny noise flips many hash bits; a real
   photo is never that flat). `tests/test_cli_analyze.py` and
   `tests/test_cli_analyze_batch.py` got new/updated tests for the CLI
   wiring (F03's exclusion from the per-frame sweep, its merge into
   `FrameAnalysis.findings`, its stub/error classification path).
   `tests/test_detector_registry.py`'s `_STILL_STUBBED` set dropped "F03"
   (it's no longer a zero-arg-callable stub, so the old generic
   `detector()` stub-call test would have started asserting the wrong
   thing about it).

## Test count
128 collected: 127 passed, 1 failed (expected — `test_taxonomy_coverage.py`'s
guard, `missing_test = [F14, R01, S03]`, down from `[F03, F14, R01, S03]`
since F03 now has genuine detector-substance test coverage naming it). Full
suite run directly this session (`uv run pytest -q`, ~3m20s — same
vision-detector-no-network-key cost builder-007 already noted, unaffected
by this session's work since F03 makes no network calls at all).

Caught and fixed two bugs in my own first draft before landing this: an
existing `test_cli_analyze_batch.py` assertion that didn't yet know about
F03's now-unconditional per-batch run, and a `NameError` (wrong variable
name) in a new test I wrote — both surfaced by actually running the suite,
not just reading the diff.

## What's open
- QUEUE.md items 9–12 (ranking/shortlist, session habit, CMP comparison,
  the profile) — untouched this session. Item 9 (ranking + shortlist,
  F-findings as disqualifiers) is next and can now draw on F03's real
  groups, not just a stub.
- `tests/test_taxonomy_coverage.py::test_every_id_has_detector_and_named_test`
  still fails, expected: F14, R01, S03 remain undeferred/unscheduled stubs
  (D-005 for F14/S03; R01 has no scheduling decision yet — REVIEW.md's
  still-open note about `r01.py`'s stale QUEUE-item-3 citation is unchanged
  by this session, since this session didn't touch r01.py).
- REVIEW.md's two outstanding notes from critic-002 (F09 center-third
  proxy, R01's stale citation) are still open for whoever next touches
  those specific files — neither was touched this session.
- DECISIONS.md open count: 0. No entry opened or closed this session.
