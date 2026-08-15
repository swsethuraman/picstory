# builder-017 — 2026-08-15

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 16/25 builder sessions
  used (this session is the 17th), hard date 2026-08-29 (matches CLAUDE.md's
  current text; builder-016 already fixed the stale `HARD_DATE` constant).
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-004, covers through builder-015; predates
  builder-016's item 15 work, nothing in it names this session's scope).
- `DECISIONS.md`: open count 0 at session start (D-001–D-009 all `RULED`).
  Nothing this session hit an ambiguity needing a new entry.
- Most recent `logs/` entry: `builder-016.md` (item 15, the resolution
  contract).
- Branch: `claude/epic-meitner-8bq3cs`, clean working tree at session start,
  even with `origin/main` at `874a7ce` (merge of builder-016's PR #21).

## What moved
QUEUE.md Stage 5, item 16 ("Keeper election per D-008a") — the top
unblocked item; item 15 landed in builder-016, items 1–14 were already
implemented. Implemented against D-008a's ruling text directly:

- **`src/picstory/detectors/f03.py`:** split Finding-construction out of
  `detect()` into a new `build_findings(groups, keeper_by_group=None)`,
  plus a `_keeper_for_group` helper. `keeper_by_group` is keyed by a run's
  frame_ids as a tuple; a run present in the mapping uses CMP's named
  winner as keeper (undisclosed — a genuine election, not a proxy); a run
  absent from the mapping (including when the mapping is `None` entirely)
  falls back to first-frame election, and that Finding's description now
  says so explicitly (`"... (keeper fallback-elected: position 1 - CMP did
  not rule on this run)"`) — D-008a's required disclosure. `detect(frames)`
  keeps its original one-argument shape (`keeper_by_group` defaults to
  `None`, i.e. full fallback), so `detectors.get("F03") is f03.detect`
  (the registry identity test) and every existing single-arg caller are
  unchanged; `detect(frames, keeper_by_group=...)` is the CMP-informed path.
- **`scripts/analyze_batch.py`:** reordered `run_batch_analysis` so CMP
  (`_run_comparisons`) runs *before* F03's findings are merged — reversing
  the previous F03-then-CMP order, per D-008a's explicit sequencing
  requirement. `_run_comparisons` now also returns `keeper_by_group`
  (`{tuple(group_ids): winner_frame_id}`, populated only for groups CMP
  actually judged — a failed comparison leaves its group absent, same as
  before for `comparisons`/`comparison_runs`). `_run_batch_level_findings`
  gained an `extra_kwargs` parameter (forwarded to the looked-up `detect`
  call); F03's call site passes `extra_kwargs={"keeper_by_group":
  keeper_by_group}`, S03's call site passes none — S03 is untouched by any
  of this, exactly as D-008a scopes it (F03/CMP only).
- Module docstrings in both files updated to describe the new order and the
  keeper-election contract, not just the code.

**Tests** (7 new, all passing):
- `tests/test_f03_safety_copies.py` (+4): `build_findings` honors a
  CMP-elected keeper over position 1; falls back to first-frame and
  discloses it for a group missing from the mapping; `None` and `{}`
  mappings behave identically; `detect(frames)` with no keeper context at
  all is full-fallback and discloses it on every run (not just the ones
  that happen to differ from position 1).
- `tests/test_cli_analyze_batch.py` (+3, in a new "CMP elects the F03
  keeper" section): CMP's winner becomes the keeper and the loser gets the
  Finding naming it; the capstone's own overturn case
  (`docs/capstone-vienna-report.md`'s group `['10_IMG_0961',
  '11_IMG_0962']`, winner `'11_IMG_0962'` — position 2, not position 1)
  reproduced directly as the regression D-008a's ruling asked for; a CMP
  failure (`RuntimeError`) still elects a keeper via fallback, and the
  resulting Finding discloses `"fallback-elected"`.
- Every existing F03 test fake in `test_cli_analyze_batch.py`
  (`_no_f03_findings`, three `f03_findings` variants, `f03_stub`,
  `f03_broken`) updated to accept `**_kwargs` — the production call site
  now always passes `keeper_by_group` as a kwarg to whatever `detector_lookup`
  resolves for `"F03"`, so every double standing in for it must accept it,
  even tests that don't care about the election itself. Module docstring
  notes this explicitly so it doesn't read as unexplained churn.

Checked for anything D-008a's ruling named that this diff doesn't cover:
"the copy Finding's description should name the elected keeper (it already
names a keeper today; only the election changes)" — true before and after,
confirmed directly (the f-string still embeds `keeper!r}`). Nothing else in
the ruling's bullet list was left undone.

## DECISIONS.md
No new entries. D-008a's ruling text was specific enough (sequencing
requirement, fallback semantics, disclosure standard, required test
coverage all stated explicitly) to implement directly with no genuine open
question. Open count: 0 (unchanged).

## Test count
283 collected: 282 passed, 1 failed
(`test_every_id_has_detector_and_named_test`, `missing_test = [F14]`).
Confirmed via `git stash` that this failure predates this session's diff —
it fails identically on a clean `874a7ce` checkout, with no `xfail` marker
anywhere in the test file or config despite prior worklogs (builder-016,
critic-004) describing it as "1 expected fail." It is genuinely the
documented, intended end state of the coverage guard per D-007's ruling
(F14 stands stubbed for the remainder of the experiment) — not a
regression, not this session's to fix — but it is a hard pytest `FAILED`,
not a passing `xfail`, and every prior worklog's phrasing has slightly
overstated that. Flagging precisely rather than repeating the same
rounding: growth this session is 276 → 283 (+7), all new, all green.
Full suite run directly (`uv run pytest -q`), ~17s, consistent with
builder-016's post-item-15 timing.

## What's open
- QUEUE.md item 17 (habit/ranking calibration per D-008c/D-008b) is next,
  unblocked, not started this session.
- `test_every_id_has_detector_and_named_test` is a hard `FAILED` in every
  `pytest -q` run, not an `xfail` — see Test count above. Not a defect to
  fix (D-007 intends `missing_test = [F14]` to stand), but worth a future
  session marking it `xfail(strict=True, reason=...)` so the suite's own
  summary line stops reading as a real failure when it isn't one. Noting
  here rather than fixing unprompted — item 17 is next in QUEUE.md and this
  is test-infrastructure polish, not blocking.
- F14 stays a `DetectorNotImplemented` stub, per D-007's ruling.
- REVIEW.md's F09 center-third-proxy note: still open, still untouched
  (unrelated to this session's scope).
- No Anthropic API calls made by any detector this session (item 16's work
  is entirely local: reordering, keeper-election bookkeeping, no network).

## Files touched
`src/picstory/detectors/f03.py`, `scripts/analyze_batch.py`,
`tests/test_f03_safety_copies.py`, `tests/test_cli_analyze_batch.py`,
`logs/builder-017.md` (this file).
