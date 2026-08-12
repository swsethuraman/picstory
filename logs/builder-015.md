# builder-015 — 2026-08-12

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 14/20 builder sessions
  used (this session is the 15th), hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-003, covers through builder-010 / `7136ac1`,
  predates builder-011 through builder-014). Its two open notes (F09's
  center-third proxy, `r01.py`'s stale citation — the latter already
  resolved by builder-013 per builder-014's confirmation) name no action
  for this session; neither file was touched.
- `DECISIONS.md`: open count 0 at session start (D-001–D-007 all `RULED`).
  No new entry opened or closed this session.
- Most recent `logs/` entry: `builder-014.md` (item 14, S03), confirmed via
  file listing.
- Branch: designated branch `claude/brave-clarke-2qavge` had no remote
  counterpart (`git fetch origin claude/brave-clarke-2qavge` — "couldn't
  find remote ref"). Checked out locally already at `e853b8c`, which
  `git fetch origin main` confirmed is exactly `origin/main` (0 commits
  each direction) — i.e. this branch already carries all merged work
  through builder-014/PR #18, with nothing of its own yet.

## What moved
Nothing implemented this session. QUEUE.md was read top-down: items 1–14
are all done and merged into `main` (verified directly, not assumed from
worklogs alone):

- Every taxonomy ID except F14 has a real (non-stub) detector under
  `src/picstory/detectors/` — checked by grepping for
  `DetectorNotImplemented` across the module: F14 (`f14.py`) is the only
  hit outside the registry's own base-class definition and docstrings.
  F14 stays stubbed by D-007's explicit "standing for the remainder of the
  experiment" ruling — its precondition (location clustering) is
  out-of-scope, and D-007 forecloses both a batch-as-location and an
  F03-groups-as-location substitute. Not touched.
- `src/picstory/cmp.py` (CMP rubric, item 11) and `src/picstory/profile.py`
  (the running profile, item 12) both exist and are wired into
  `scripts/analyze_batch.py`.
- `src/picstory/detectors/r01.py` (item 13, agent-proposed) and
  `src/picstory/detectors/s03.py` + `subject_clusters.py` (item 14,
  agent-proposed) are both real implementations, not stubs.
- QUEUE.md's own text ends at item 14 with no further entries, agent-
  proposed or otherwise.

TAXONOMY.md's four output-mapping rows (the pick/share-list, the habit,
the three-frame comparison, the running profile) each have a real,
non-stub implementation behind them. I looked for a legitimate gap worth
proposing as a new `[agent-proposed]` QUEUE item — the kind of check that
turned up R01 and S03 in prior sessions — and did not find one: every
F/S/R item and every output row traces to real code, and the one
remaining stub (F14) is closed by an explicit, standing human ruling
rather than an open gap. Inventing a new item without a genuine unmet
taxonomy obligation would be scope not asked for, so this session made no
code changes.

Ran the full suite directly to confirm the baseline is exactly what
builder-014 reported, not stale or silently regressed (see "Test count").

## DECISIONS.md
No new entries. Nothing this session hit an ambiguity needing a human
ruling — there was no implementation work to hit one during. Open count:
0 (unchanged).

## Test count
266 collected: 265 passed, 1 expected fail
(`test_every_id_has_detector_and_named_test`, `missing_test = [F14]` —
unchanged from builder-014, the documented intended end state of this
guard per D-007). Full suite run directly (`uv run pytest -q`), ~4.2s.
Growth: 266 → 266 (+0 — no code or tests changed this session).

## What's open
- REVIEW.md's F09 center-third-proxy note: still open, still untouched
  (unrelated to this session's scope).
- F14 stays a `DetectorNotImplemented` stub, per D-007's ruling, standing
  for the remainder of the experiment.
- QUEUE.md has no further unblocked (or blocked) items past 14 for the
  next BUILDER session to take. Absent a new agent-proposed gap or a fresh
  human-added QUEUE item, the next BUILDER session will likely find the
  same state this one did.
- DECISIONS.md open count: 0.
- No Anthropic API calls made this session (no detector work happened).

## Files touched
`logs/builder-015.md` (this file) only.
