# builder-020 — 2026-08-16

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 19/25 builder sessions
  used (this session is the 20th), hard date 2026-08-29.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-005, covers through item 16 plus owner
  rulings up to and including D-009/TAXONOMY.md v1.2). Predates
  builder-019 (item 18) and D-010's ruling — nothing in it names this
  session's scope (item 19).
- `DECISIONS.md`: open count 0 at session start (D-001–D-010 all
  `RULED`).
- Most recent `logs/` entry: `builder-019.md` (item 18, Fixability
  parsing). No code changed between builder-019 and this session's start.
- Branch: the designated branch `claude/epic-meitner-us13ea` was already
  checked out. Local `main`/`origin/main` refs in this clone were stale
  (`3ec4e4a`, PR #5), but `mcp__github__list_branches` confirmed the
  repository's actual `main` is `8fe3d46` — the same commit the
  designated branch already sits on (`git fetch origin main` then
  confirmed `origin/main` at `8fe3d46` too; the earlier stale ref was a
  clone artifact, not a real divergence). The branch already equals
  `main`'s real tip, so no reset/rebase was needed — continued directly
  on it, matching the "already equals origin/main's tip exactly, no
  actual rebase/reset needed" case from builder-019's own session.

## What moved
QUEUE.md item 19, "Small hygiene sweep" — the last item on QUEUE.md, now
that item 18 is done. All four sub-parts:

**19(a) — `f14.py`'s stub message.** Was citing "QUEUE.md item 4," the
original Stage-1 grouping that D-005 (then D-007) moved F14 out of. Now
cites D-007 by name and states the actual reason the stub stands
(location clustering out of scope for the remainder of the experiment),
matching the citation convention D-007's own ruling asked worklogs to
use going forward.

**19(b) — `record_vision_fixtures.py` per-ID split.** Checked against
what builder-012's original complaint actually was: extending the script
to cover F06 re-spent 4 already-recorded calls because the script ran
its whole hardcoded `calls` list unconditionally. builder-019 already
added a `--only ID [ID ...]` filter (visible in the current file, used
this session's own git-log read of `scripts/record_vision_fixtures.py`
before touching anything) that lets a future extension run only the new
ID's calls — `--only F05` is exactly what builder-019 used for its own
F05 addition, live, and it worked (2 calls spent, not 8). That is the
per-ID split QUEUE.md item 19(b) is asking for: recording new fixtures
no longer re-spends on the whole call list. Concluded no further code
change was needed here — restructuring the `calls` list into separate
per-ID functions/files on top of an already-working `--only` filter
would be an abstraction the task doesn't need (CLAUDE.md's "don't design
for hypothetical future requirements"). Verified by re-reading
builder-019's worklog and the script's current `--only` implementation
side by side rather than assuming; leaving this as documentation, not
a code diff.

**19(c) — F02's known-limitation disclosure.** Added a paragraph to
`f02.py`'s module docstring describing the capstone false-positive class
directly: frame `30_IMG_0981`'s stone archway (a dark, out-of-focus
background element the photographer shot through) reads to the
dark+locally-flat heuristic exactly like a lens/grip obstruction — same
pixel signature, no way for the heuristic to tell "obstruction" from
"architecture shot through" apart. Quoted the capstone report's own
recorded finding text (`docs/capstone-vienna-report.md` line 718, "Dark,
low-texture mass along the top edge covering 86%...") rather than
paraphrasing it, and explicitly noted this is a disclosure, not a
threshold change — no evidence exists yet for where a corrected
threshold should sit, per the item's own instruction.

**19(d) — `xfail(strict=True, ...)` marker.** Added
`@pytest.mark.xfail(strict=True, reason="F14 stands stubbed per
DECISIONS.md D-007 ...")` directly above
`test_every_id_has_detector_and_named_test` in
`tests/test_taxonomy_coverage.py`. Verified before adding it that no
test function anywhere under `tests/` has "f14" in its name (`grep -rn
"^def test_.*f14" tests/` — no matches), confirming the guard's
`missing_test = ['F14']` failure is real and current, not stale.
`strict=True` per the item's own reasoning: if F14 is ever implemented
and gets a named test, this marker will XPASS, which `strict=True`
turns into a hard failure — forcing whoever does that work to remove the
marker consciously rather than have it silently start passing.

## Tests
Ran the full suite directly (`uv run pytest -q`) before and after this
session's changes:
- Before: 317 collected, 316 passed, 1 failed
  (`test_every_id_has_detector_and_named_test`).
- After: 317 collected, **316 passed, 1 xfailed** — same test, now
  reporting as the documented expected state instead of a `FAILED` line.
  No other test's outcome changed; no new tests added (this session's
  changes are docstring/message text plus one marker, not new behavior
  to cover).

Also ran `uv run ruff check src/ tests/ scripts/`: 5 pre-existing lint
findings (unused imports in `tests/test_cli_analyze_batch.py`,
`tests/test_frame.py`, `tests/test_vision_detectors.py`, and one script)
— confirmed via `git stash` that all 5 exist identically on the
pre-session tree, so none are from this session. `ruff check` on the
three files this session actually touched
(`tests/test_taxonomy_coverage.py`, `src/picstory/detectors/f14.py`,
`src/picstory/detectors/f02.py`) reports clean. Left the pre-existing
findings untouched — out of scope for this item, and CLAUDE.md's
no-drive-by-cleanup rule applies to files this session isn't otherwise
changing.

## DECISIONS.md
No new entry. Every sub-part of item 19 was specific enough to execute
directly (19(b)'s assessment was a "is this already done" check against
existing code and history, not an open question about the taxonomy or a
ruling). Open count unchanged: 0.

## What's open
QUEUE.md item 19 was the last item on the list — Stage 1 through Stage 5
plus both agent-proposed items are now all implemented, matching the
state builder-015 described mid-experiment ("QUEUE.md fully implemented")
but for the phase-2 items this time. Nothing left on QUEUE.md for the
next BUILDER session to pick up top-down; it should read QUEUE.md fresh
at its own start in case the owner has appended anything since, per the
same convention as builder-015's session.

## Files touched
`src/picstory/detectors/f14.py`, `src/picstory/detectors/f02.py`,
`tests/test_taxonomy_coverage.py`, `logs/builder-020.md` (this file).
