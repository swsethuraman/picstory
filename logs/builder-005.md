# builder-005 — 2026-08-10

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 4/20 builder sessions used, hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (`critic-001`) — covers builder-001/002 only; no
  findings requiring action this session (builder-004 already acted on its
  one forward-looking note, S03, via D-005).
- `DECISIONS.md`: open count 4 (D-003, D-004, D-005, D-006) at session
  start — below the 5-item halt threshold. No entry added this session (see
  "On not opening D-007" below); open count unchanged at 4.
- Most recent `logs/` entry: `builder-004.md` (9 of 11 API-vision detectors
  for QUEUE item 4, merged as PR #5 into `main`, `3ec4e4a`).
- Branch: `claude/brave-clarke-ppf7vk` did not exist remotely; created off
  `origin/main` (`3ec4e4a`), which already contained all of builder-004's
  merged work.

## What moved
Implemented QUEUE.md Stage 1, item 5: `scripts/analyze.py`, one photo in,
full analysis out.

- `scripts/analyze.py` — CLI entry point. Loads a `Frame` via
  `frame.load_frame`, runs every *evaluable* detector against it, and
  writes the full breakdown through `scripts/_report.py` (CLAUDE.md output
  discipline: full body to `outputs/reports/`, ≤3 lines to stdout).
  - **R01 excluded from the sweep.** TAXONOMY.md's own text for R01 —
    "triggered by shooting conditions, not detected in frames" — makes it
    a batch/conditional rule, not a per-photo detector; schema.py's `Habit`
    already bars R01 for the identical reason. Running it through the same
    "stub" bucket as F03/F14/S03 would misrepresent a structural exclusion
    as pending per-frame work it will never get. 19 of the 20 IDs are
    evaluated.
  - Each call classifies into exactly one of `detected` / `clean` / `stub`
    (`DetectorNotImplemented`) / `error` (anything else — a vision call
    failing for lack of `ANTHROPIC_API_KEY`, a spend cap, a network
    problem). Per CLAUDE.md's spending rule ("if the cap is hit... treat
    that as a blocked item, log it, move on"), an `error` is recorded and
    does not stop the sweep — the report shows exactly which IDs were
    blocked and why.
  - `pick` and `habit` are left `None` on the `AnalysisOutput`. This is not
    a new call: schema.py's own docstring already says both "are populated
    from Stage 2 onward (QUEUE.md items 9-10)" because both need a batch to
    be meaningful, and that design was in place (uncontested by critic-001)
    before this session. QUEUE.md item 5's line "the habit = the
    highest-priority finding by taxonomy recurrence rules" describes item
    10's cross-batch computation, not something a single Stage 1 photo can
    honestly produce — TAXONOMY.md's per-item "Recurrence in source" text
    is free-form prose ("Nearly every batch", "≥3 batches", "The single
    most frequent finding"), not a machine-checkable ranking; turning it
    into an invented ordinal scale for a one-photo run would be exactly the
    kind of plausible substitute CRITIC is instructed to flag. Not logged
    as a new DECISIONS.md entry (see below) — it's consistent with
    already-settled, reviewed design, not a fresh ambiguity needing a
    ruling.
  - `run_analysis(frame, *, detector_lookup=detectors.get, ids=None)` is
    the testable core; `detector_lookup` is injectable, mirroring
    `_vision.py`'s `VisionCaller` pattern, so tests exercise the CLI's
    dispatch/classification logic without touching the real registry or
    depending on this environment's lack of `ANTHROPIC_API_KEY` (CLAUDE.md:
    the test suite must run offline, always — not just in environments that
    happen to lack a key).
- `tests/test_cli_analyze.py` — 8 new tests: per-status classification
  (detected/clean/stub/error), one error doesn't stop the sweep, output
  findings are detected-only, pick/habit stay `None`, report body contains
  counts and per-ID lines, and two `main()` end-to-end tests (a real tiny
  on-disk JPEG, and a bad path) asserting ≤3 stdout lines and a written
  report file. One test's name deliberately avoids an ID substring
  (`test_evaluable_ids_excludes_the_conditional_batch_rule`, not
  `..._r01`) — an earlier draft named it `..._excludes_r01`, which
  incidentally satisfied `test_taxonomy_coverage.py`'s per-ID name check
  for R01 without R01 having any genuine detector-substance test; renamed
  before committing so the coverage guard's `missing_test` set for R01
  stays honest.

## Bug found and fixed while smoke-testing the CLI (not this session's queue item, but surfaced by it)
Ran `analyze.py` against a real (non-fixture-sized) synthetic photo, per
this project's "test the feature, don't just pass the suite" discipline.
F02 (lens/grip obstruction, landed in builder-003) crashed:
`_local_variance` in `f02.py` trims its input to a multiple of `BLOCK=8`
pixels before tiling, then returns that *trimmed* shape — never padded back
to the original — which the caller then broadcasts against the untrimmed
`dark` mask. Any image whose dimensions aren't exact multiples of 8 (i.e.
almost every real photo) raised a `ValueError`. Every existing F02 test used
200×200 fixtures (200 % 8 == 0), so this path was never exercised.

Fixed: `_local_variance` now edge-pads its tiled-variance output back to the
input's own shape before returning (no-op when dimensions already divide
evenly — the existing 200×200 tests are byte-for-byte unaffected). Added
`test_f02_lens_grip_obstruction_handles_dimensions_not_divisible_by_block`
(203×203) as a regression test. Fixed rather than logged-and-skipped: this
is a run-time correctness bug in already-merged code, not a taxonomy
ambiguity or an unimplementable item — nothing for DECISIONS.md, just a bug
with a small, contained fix, caught by actually exercising this session's
own deliverable end-to-end.

## `outputs/` gitignored
`scripts/_report.py` writes timestamped report files there on every run;
this is the first script (`analyze.py`) that actually calls `report()` with
real content (`check_hard_stop.py` prints directly and never wrote
anything there). Confirmed via `git log --all -- outputs/` that the
directory was never tracked. Added `outputs/` to `.gitignore` — generated
per-run artifacts, not source; committing every run's report would be
build-output noise, the same reasoning that already excludes
`__pycache__/`, `.pytest_cache/`.

## On not opening D-007
Considered logging a DECISIONS.md entry for the pick/habit-is-None choice
above, since it's a case where QUEUE.md's terse item-5 gloss ("the habit =
...") reads differently from what got built. Decided against it: a
DECISIONS.md entry is for a genuine open question needing a human ruling
between real options (see D-005's shape). Here there's only one honest
option available at Stage 1 — schema.py already made this call, in code
that critic-001 reviewed and found no drift in — so re-litigating it as a
new open decision would just be re-asking a question this codebase already
answered, and would have pushed the open count to 5 and halted the run for
no new information. If a future session (or the human) disagrees with
schema.py's own documented design, that's a reason to revisit item 1, not
a reason this session should invent a fifth open item.

## What's open
- QUEUE item 4's two deferred IDs (F14, S03) and item 8 (F03 grouping) are
  still Stage 2 work — untouched this session, per D-005's existing plan.
- R01 (Stage boundary unclear — DECISIONS.md doesn't currently need an
  entry for this either; it's simply not yet scheduled in any QUEUE.md
  item, same as builder-004 left it) remains a stub.
- `tests/test_taxonomy_coverage.py::test_every_id_has_detector_and_named_test`
  still fails, expected and unchanged from builder-004: `missing_test` is
  `[F03, F14, R01, S03]`.
- DECISIONS.md open count: 4 (D-003, D-004, D-005, D-006), unchanged —
  below the 5-item halt threshold. All four still await a human ruling.
- QUEUE.md item 6 (remaining per-detector tests for F03/R01, once those
  detectors land) not started; items 7-12 (Stage 2-4) not started.

## Test count
96 collected: 95 passed, 1 failed (the coverage guard, expected and
unchanged in substance from builder-004 — same 4 IDs). By file: 18
test_schema.py + 6 test_detector_registry.py + 19 test_local_detectors.py
(18 pre-existing +1 new F02 regression) + 2 test_taxonomy_coverage.py + 43
test_vision_detectors.py (all pre-existing, unchanged) + 8 new in
tests/test_cli_analyze.py.
