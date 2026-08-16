# critic-006 — 2026-08-16

## Role
CRITIC.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 20/25 builder sessions
  used (unchanged; CRITIC sessions don't count), hard date 2026-08-29.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-005, scope ended at `50a80f8`, before
  QUEUE.md item 17 landed). Superseded by this session's REVIEW.md.
- `DECISIONS.md`: open count 0 at session start (D-001–D-010 all
  `RULED`).
- Most recent `logs/` entry: `builder-020.md` (item 19, the hygiene
  sweep — the last item on QUEUE.md).
- Branch: designated branch `claude/upbeat-volta-vbe1q5`, already even
  with the repo's real tip (`6aa200e`) — confirmed `main` is an ancestor
  of `HEAD` directly rather than trusting the stale local `origin/main`
  ref (which pointed at PR #5, far behind); no reset needed.

## What moved
Read the full diff since critic-005's commit (`3f77028` → `6aa200e`):
QUEUE.md item 17 (habit pervasiveness + ranking S-count tie-break,
D-008c/D-008b, `a1b77f9`), the owner's D-010 ruling and its
QUEUE.md/DECISIONS.md bookkeeping (`231cc1f`, `8b91188`, `93745bb`),
QUEUE.md item 18 (Fixability parsing per D-009, `aa6bd28`), and QUEUE.md
item 19 (the hygiene sweep, `b70ad16`).

Checked item 17 against DECISIONS.md D-008c/D-008b directly: read
`ranking.py`'s `PERVASIVE_THRESHOLD`, `pervasive_ids`, `pervasive_note`,
`compute_habit`'s exclusion logic, and `rank_frames`'s tie-break key.
Independently re-verified the calibration fixture's F02 count (5) against
`docs/capstone-vienna-report.md`'s own `[detected]` lines rather than
trusting the test's transcription. Confirmed the D-010 process itself
worked as CLAUDE.md intends: builder-018 found a mismatch between D-008c's
named expected habit winner (F08) and what the ruling's own mechanism
actually produces on the real capstone counts (S01), logged it as D-010
without closing it, the owner ruled separately, and the test now asserts
the ruled outcome — checked by reading the test and rerunning the suite,
not by trusting either worklog's report of it.

Checked item 18 against D-009's ruling text: `schema.taxonomy_fixability`/
`taxonomy_fixability_category` parsing, the byte-identical guard test
(spot-checked three Fixability categories directly against TAXONOMY.md),
and `resolve_finding_fixability`'s wiring into both CLIs' `render_report`.
Opened the two new F05 fixture files directly to confirm they carry
realistic Anthropic response shape (message/tool-use IDs, per-call token
usage, a `cache_creation` block) rather than being hand-authored, per
D-006's precedent for what counts as a genuine recording.

Checked item 19's four sub-parts directly: `f14.py`'s citation, the
`record_vision_fixtures.py --only` filter (grepped for it, confirmed it
predates and covers this item's ask), F02's docstring quote against the
capstone report's line 718 (exact match), and the `xfail(strict=True,
...)` marker (confirmed the suite now reports `1 xfailed`, not `FAILED`).

**New finding, filed as DECISIONS.md D-011 (open):** re-reading F05's own
Detection text against its new v1.2 Fixability bullet and `f05.py`'s
`GEOMETRY_SUB_PATTERN` surfaced a real tension - Detection's literal
wording ("when the subject drifts off the ultrawide's center") appears to
require an off-center subject, while the `bowing` sub-pattern (both in
TAXONOMY.md's own Fixability bullet and independently restated in
`f05.py`'s sub-pattern description) explicitly covers a centered-subject
case. Verified this is not just a wording ambiguity but an actual
observed model behavior: `tests/fixtures/vision/f05_bowing_ceiling.json`
(a genuine recorded API call, not hand-authored) shows the live model
returning `detected=true, geometry=bowing` with a rationale stating
outright that the subject is centered - the literal opposite of
Detection's stated trigger. Filed with Question/Options/Recommendation,
Ruling left `(pending)` per CLAUDE.md's "CRITIC may add entries and may
not close them." DECISIONS.md open count updated 0 → 1 accordingly (well
under the five-open `HALT.md` threshold).

Wrote `REVIEW.md` (critic-006): items 17-19 and the D-010 process all
checked out as faithful implementations of their governing text; D-011 is
the one genuine open question this session surfaces, not a "no findings"
session.

## What's open
- DECISIONS.md open count: 1 (D-011, filed this session, not ruled).
  D-001–D-010 remain `RULED`.
- F09's center-third proxy — still open, untouched by any diff since
  critic-002.
- F14 stays a documented, standing `DetectorNotImplemented` stub per
  D-007.
- QUEUE.md has no unimplemented items left (builder-020's own read,
  reconfirmed by this session's diff scope) - the next BUILDER session
  should read QUEUE.md fresh in case the owner has appended anything, and
  may be blocked entirely on D-011 if the owner wants F05's prompt
  behavior settled before further F05-adjacent work.

## Test count
317 collected: 316 passed, 1 xfailed (`test_every_id_has_detector_and_named_test`,
F14 - the intended, documented end state per D-007/item 19d). CRITIC made
no code changes; verified by running the suite directly this session
(`uv run pytest -q`, 15.18s) rather than trusting builder-020's report
secondhand - it matches exactly.
