# critic-004 — 2026-08-12

## Role
CRITIC.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 15/20 builder sessions
  used (unchanged; CRITIC sessions don't count), hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-003, covers through `7136ac1` / builder-010).
  Superseded by this session's REVIEW.md.
- `DECISIONS.md`: open count 0 at session start (D-001–D-007 all `RULED`,
  D-007 ruled 12 Aug 2026, same day, before this session started).
- Most recent `logs/` entry: `builder-015.md` (no code changes — QUEUE.md
  fully implemented, no unblocked item found this session).
- Branch: designated branch `claude/wizardly-pascal-n86v09` — continuing
  directly on it for this CRITIC session's commit.

## What moved
Read the full diff since critic-003's commit (`f0f11f0` → `db37fe8`):
builder-011 (CMP, `b9f6769`), builder-012 (the profile, `fa421af`),
builder-013 (R01, `0eb442f`), builder-014 (S03, `c2d7d24`), builder-015 (no
code changes). This covers QUEUE.md Stage 3 (item 11), Stage 4 (item 12),
and both agent-proposed items (13, 14) — everything landed since the last
CRITIC pass.

Read TAXONOMY.md's CMP section, R01 section, S03's Detection text, F06's
Profile note, and the output-mapping table directly, then checked each
against its implementation line by line: `cmp.py`/`schema.cmp_rubric_text`,
`detectors/r01.py`, `detectors/s03.py` + `detectors/subject_clusters.py`,
`profile.py` + `_vision.py`'s `SubPatternSpec`/`detectors/f06.py`. Compared
`subject_clusters.py`'s constants and pair-comparison logic directly against
`f03.py`'s to confirm D-007's ruling ("looser threshold, no focal-
length/timestamp gate, non-adjacent pairs allowed") was actually followed,
not just asserted in a docstring. Read the two genuine recorded fixtures
(`tests/fixtures/cmp/wide_vs_tight_with_walker.json`,
`tests/fixtures/vision/f06_edge_intrusion_right.json`) and confirmed both
are wired into replay tests, not sitting unused.

Also verified builder-011's own flagged discovery: that `tests/conftest.py`
genuinely blocks live Anthropic calls during the test suite (a real,
previously-unnoticed violation of CLAUDE.md's "tests never make live calls"
rule that predates this diff, present since at least builder-007, and
uncaught by critic-001 through critic-003). Ran the full suite directly with
this sandbox's own working `PICSTORY_VISION_KEY` present in the environment
— 265 passed / 1 expected fail in 3.4s confirms the block works (a live-call
leak would have shown as ~180s+, the exact symptom three prior builder
worklogs reported without diagnosing).

Wrote `REVIEW.md` (critic-004): no plausible-substitute pattern found. CMP,
the profile (including F06's sub-pattern, asked for inside the same
structured call rather than parsed from free text afterward), R01, and S03
(per D-007's specific ruling) each checked out as real, disclosed
implementations of what their TAXONOMY.md text says. R01's stale
QUEUE-item-3 citation (open since critic-002) is resolved — the module was
replaced this diff. F09's center-third proxy remains the one standing open
note, unchanged, not touched by this diff.

## What's open
- DECISIONS.md open count: 0. No entry added or closed (CRITIC may add,
  never close; nothing found rose to that bar this session).
- F09's center-third proxy (`src/picstory/detectors/f09.py`) — still open,
  still untouched by any diff since critic-002. Not blocking; disclosed
  proxy, same standard applied to F03/S03.
- QUEUE.md has no further items past 14 (confirmed by builder-015 last
  session); nothing for a next BUILDER session to take unless a new gap is
  found or a human adds one.
- F14 stays a documented, standing `DetectorNotImplemented` stub per D-007
  — not an open question, the ruled end state for the remainder of the
  experiment.

## Test count
266 collected: 265 passed, 1 expected fail
(`test_every_id_has_detector_and_named_test`, `missing_test = [F14]` —
D-007's documented, intended end state). CRITIC made no code changes, so
this is unchanged from builder-015's own reported count; verified by
running the suite directly this session (`uv run pytest -q`, 3.4s) rather
than trusting the worklog secondhand — see REVIEW.md's testing-
infrastructure section for why this run's speed is itself confirming
evidence, not just a number.
