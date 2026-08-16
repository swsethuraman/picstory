# critic-005 — 2026-08-16

## Role
CRITIC.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 17/25 builder sessions
  used (unchanged; CRITIC sessions don't count), hard date 2026-08-29.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-004, covers through `db37fe8` / builder-015,
  no code changes that session). Superseded by this session's REVIEW.md.
- `DECISIONS.md`: open count 0 at session start (D-001–D-009 all `RULED`;
  D-008a/b/c and D-009 added by the owner, 15 Aug 2026, since critic-004).
- Most recent `logs/` entry: `builder-017.md` (item 16, keeper election).
- Branch: designated branch `claude/upbeat-volta-9l2wss`, even with
  `origin/main` at `50a80f8` at session start.

## What moved
Read the full diff since critic-004's commit (`97f59e7` → `50a80f8`):
builder-016 (item 15, the resolution contract, `98609a2`), builder-017
(item 16, keeper election per D-008a, `4a6d1c5`), and the owner commits in
the same range — D-008a/b/c and D-009 rulings (`7862d5a`), Stage 5 opening
plus the hard-stop extension (`e2e085a`), the scorecard (`f2d6d06`), and
TAXONOMY.md v1.2 plus a QUEUE.md item 19(d) text addition (`50a80f8`).

Checked item 15's six sub-parts directly against `frame.py`/`_vision.py`/
`f01.py`'s own claims rather than the worklog's summary of them: read the
actual call order in `load_frame` (EXIF before downsample) and in
`_vision.judge()` (confirmed `_encode_jpeg` runs before the caller is
invoked, so the item-15e end-to-end test exercises the upload-ceiling path
even though `conftest.py` blocks the live call that would follow it — not
assumed from the docstring, traced directly). Grepped `src/picstory/detectors/`
for other reads of `Frame.path` (none) and for `_imaging.downsample` calls
across F02/F07/F08/F09/F10/F12/S03 to confirm builder-016's claim that only
F01 needed a new resolution-sensitivity disclosure.

Checked item 16 against DECISIONS.md D-008a's ruling text line by line:
reordering in `run_batch_analysis`, `f03.build_findings`/`_keeper_for_group`'s
fallback-and-disclose behavior, and the exact disclosure string, each
verified by reading the code and its three fallback-path tests directly
(not just the CMP-elected-keeper happy path). Cross-checked
`test_run_batch_analysis_cmp_overturns_position_1`'s cited frame IDs and
winner against `docs/capstone-vienna-report.md`'s own text rather than
trusting the test's docstring citation — matches.

Checked TAXONOMY.md's v1.2 diff directly, line by line: every hunk is a pure
addition (`- **Fixability:**` bullets), no existing Detection/Correction/
Reinforcement/Rule/Profile-note text has a single character changed. Owner
commit (git author is the human), consistent with D-009's ruling that the
owner may version the taxonomy; not a standing-rule violation by an agent
session.

Wrote `REVIEW.md` (critic-005): no plausible-substitute pattern found.
Item 15 (infrastructure, no taxonomy ID of its own) and item 16 (F03/CMP
orchestration) both checked out as real implementations of what their
governing text says, each with real, verified test coverage rather than
asserted coverage. One assumption worth naming (not a bug today): F03's
keeper-election trusts CMP's `winner_frame_id` without re-validating group
membership locally, safe only because CMP's own schema enum-constrains that
field — re-confirmed unchanged this session, flagged in REVIEW.md so it's
legible if that upstream guarantee ever moves.

## What's open
- DECISIONS.md open count: 0. No entry added or closed — nothing in this
  diff rose to a genuine open question; item 15/16 were both specific
  enough in QUEUE.md/D-008a to execute and review without one.
- QUEUE.md item 18 is still marked `[blocked: owner's TAXONOMY.md v1.2
  commit]`, but that commit is now part of this same diff (`50a80f8`'s
  range). The bracket text wasn't updated. Flagged in REVIEW.md as an
  operational note for the next BUILDER session, not a DECISIONS.md item —
  QUEUE.md isn't frozen the way TAXONOMY.md is, and editing it is
  BUILDER's role, not CRITIC's.
- QUEUE.md item 19(d) (the `xfail(strict=True, ...)` marker for
  `test_every_id_has_detector_and_named_test`) has its text added to
  QUEUE.md by the owner but no code change yet — `grep`ed `tests/` for
  `xfail`, found none. The guard is still a hard `FAILED`, not an `xfail`,
  exactly as builder-017's worklog precisely (not loosely) described it.
- F09's center-third proxy — still open, still untouched by any diff since
  critic-002.
- F14 stays a documented, standing `DetectorNotImplemented` stub per D-007.

## Test count
283 collected: 282 passed, 1 failed
(`test_every_id_has_detector_and_named_test`, `missing_test = ['F14']` —
D-007's documented, intended end state; still a hard `FAILED`, not an
`xfail`, until QUEUE item 19(d) lands). CRITIC made no code changes, so this
is unchanged from builder-017's own reported count; verified by running the
suite directly this session (`uv run pytest -q`, 15.06s) rather than
trusting either worklog secondhand.
