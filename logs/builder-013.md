# builder-013 — 2026-08-12

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 12/20 builder sessions
  used (this session is the 13th), hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-003, covers through builder-010 / `7136ac1`,
  predates builder-011 and builder-012). Its two open notes were: F09's
  center-third proxy (untouched this session), and `r01.py`'s stale
  citation ("real detection logic ... lands in QUEUE.md item 3") - this
  session's R01 work resolves that note by replacing the module the stale
  citation lived in; see "What moved."
- `DECISIONS.md`: open count 0 at session start (D-001-D-006 all `RULED`).
  This session opens D-007 (see below) - open count 1 at session end.
- Most recent `logs/` entry: `builder-012.md` (item 12, the profile),
  confirmed via `git log --oneline -- logs/`.
- Branch: designated branch `claude/brave-clarke-5laj60` already existed on
  `origin`, HEAD (`82e9547`, PR #16's merge) matched `origin/main` - no
  fresh branch needed, continued directly on it. No open PR for this exact
  branch name.

## What moved
QUEUE.md items 1-12 (all of Stage 1-4) were already done as of builder-012.
Re-checking the taxonomy against the actual registered detectors
(`src/picstory/detectors/`) rather than trusting "QUEUE.md is empty ⇒
nothing left": R01, F14, and S03 are still `DetectorNotImplemented` stubs -
`missing_test = [F14, R01, S03]` has been the coverage guard's stated
expected-fail set since builder-008, unchanged through builder-012. QUEUE.md
never actually had a line item scheduling R01 (its own stub docstring's
citation, "lands in QUEUE.md item 3," was flagged as stale/wrong by
critic-002 and critic-003 - item 3 never named R01). F14/S03 were
deliberately deferred by D-005 "until Stage 2 lands, then implemented
properly against the batch" - Stage 2 (items 7-10) landed at builder-010.

Read TAXONOMY.md §R directly rather than trusting the stale stub comment:
"Trigger: Hazy / low-contrast conditions (detected via F12 findings in the
batch). Rule: Shoot tighter." Unlike F14/S03, this has no batch-grouping
ambiguity - it is a simple "did F12 fire anywhere in this batch" check over
already-computed findings. Added QUEUE.md item 13 (`[agent-proposed]`) for
it and implemented it this session:

1. **`src/picstory/schema.py`**: added `_RULE_LINE`/`_rule_texts()`/
   `taxonomy_rule_text()`, parsing each R-item's `- **Rule:**` bullet
   verbatim - same single-source-of-truth pattern as
   `taxonomy_correction_text`/`taxonomy_reinforcement_text`. Added `Rule`
   (new dataclass: `taxonomy_id`, `advice`), validated to require an R-item
   ID and non-empty advice. Deliberately a *different* object type from
   `Finding`, not a reused one - TAXONOMY.md §R is explicit that rules are
   "triggered by shooting conditions, not detected in frames" and are a
   "different object type for the classifier," and `ranking.py`'s own
   docstring already asserted "R01 findings cannot occur per-frame." Gave
   `AnalysisOutput` a `rules: list[Rule]` field (default empty, mirroring
   `comparisons`), threaded through `to_dict`/`from_dict`. Mirrored in
   `schema/analysis.json` (`$defs.rule`, `properties.rules`).
2. **`src/picstory/detectors/r01.py`**: replaced the stub. `detect()` now
   takes `list[FrameAnalysis]` (not a `Frame` - R01's trigger is a property
   of already-computed findings, not something to re-derive from pixels),
   checks whether any frame carries an F12 finding (`TRIGGER_ID = "F12"`,
   hardcoded from TAXONOMY.md's own Trigger text the same way F03 hardcodes
   its threshold from its own Detection text), and returns one `Rule` if so
   - once per batch, not once per triggering frame, since this is
   forward-looking session advice, not a per-frame tally. Still registered
   under `"R01"` via `@register`, so the registry/coverage machinery is
   unchanged.
3. **`scripts/analyze_batch.py`**: new `_run_r01(frame_analyses,
   detector_lookup)` helper, called in `run_batch_analysis` right after
   ranking/habit (same final findings, F03's merge included). No
   stub/error classification for it (unlike F03/CMP) - R01 has no network
   or spend dependency, so there is no legitimate "blocked, log it, move
   on" case to handle; `detector_lookup` is still threaded through for test
   injection, matching every other ID's pattern. `run_batch_analysis`'s
   return signature is unchanged (still a 3-tuple) - the rule lands on
   `AnalysisOutput.rules` directly rather than needing a parallel
   "RuleRun" tracking structure the way `ComparisonRun` exists for CMP.
   `render_report` gained a `## Rules` section: the triggered rule's ID and
   advice, or an explicit "no rule triggered - no F12 finding in this
   batch" line when none fired.
4. **Tests**: `tests/test_schema.py` gained 8 (`taxonomy_rule_text`
   verbatim/missing-for-F-and-S, `Rule` construction/validation/roundtrip,
   `AnalysisOutput.rules` default-empty/roundtrip).
   `tests/test_r01_haze_rule.py` (new, 5): triggers on F12 anywhere in the
   batch, `None` when absent, `None` for an empty batch, fires exactly once
   regardless of how many frames carry F12, and is the actual registered
   detector. `tests/test_cli_analyze_batch.py` gained 5: no-rule and
   triggered-rule wiring through `run_batch_analysis` (including one test
   using the real registered `r01.detect` rather than a stub, to pin that
   `_run_r01` actually receives the per-frame sweep's F12 finding and not
   just whatever a fake returns), one exercising the real default
   `detector_lookup` end-to-end (an all-zero-pixel synthetic frame is
   itself flat/hazy by F12's own luminance-spread metric, so this
   genuinely triggers R01 through the real F12 detector rather than a
   contrived double), and two `render_report` assertions (absent-rule line,
   present-rule line). `tests/test_detector_registry.py`'s `_STILL_STUBBED`
   set updated from `{F14, R01, S03}` to `{F14, S03}` (R01's zero-arg
   `detector()` stub-call pattern no longer applies - it now takes
   `frame_analyses` and doesn't raise `DetectorNotImplemented`).

## DECISIONS.md — opened D-007, not closed
While confirming R01 was genuinely unblocked, re-checked whether F14/S03
were too: D-005's deferral was conditioned on "Stage 2 lands," and Stage 2
(items 7-10) landed three sessions ago (builder-010), but every session
since (builder-010 through builder-012, this session's own start-of-session
check included) has kept logging "D-005 covers F14/S03" as if the
precondition were still open. Checking what Stage 2 actually built: F03's
`group_near_duplicates` groups on "no change in position, focal length, or
angle" (near-identical consecutive frames - "copies, not variations"), which
is a narrower relation than either F14 needs ("a location's coverage" - all
frames from one location) or S03 needs ("batch-mates" of a subject, which
TAXONOMY.md's own S03 example implies spans more than one near-duplicate
burst). No location metadata reader, location-clustering, or broader
subject-clustering exists anywhere in `src/`. Implementing either against
F03's groups (the only grouping that exists) would answer a materially
easier question than the Detection text poses - the same
plausible-substitute shape D-005 already rejected for a per-frame proxy, one
layer up (a too-narrow group, not no group). Filed as D-007 rather than
guessed at or silently deferred again: options are (a) build real
location/subject-clustering signals, (b) reuse F03's groups as a disclosed,
narrower-than-intended proxy, (c) leave both stubbed until (a) is
deliberately scoped as its own QUEUE item. Recommended (c) - logged and
skipped per CLAUDE.md ("BUILDER logs and skips... nothing answers its own
decision"). DECISIONS.md open count: 0 → 1.

## Test count
254 collected: 253 passed, 1 expected fail
(`test_every_id_has_detector_and_named_test`, `missing_test = [F14, S03]` -
down from `[F14, R01, S03]`; D-007 (this session) now covers F14/S03's
remaining gap in place of D-005's since-satisfied "wait for Stage 2"
condition). Full suite run directly (`uv run pytest -q`), ~1.7s - no
network-dependent tests touched this session (R01 is purely local; no live
Anthropic calls made). Growth: 237 → 254 (+17: 8 schema, 5 r01 detector
behavior, 5 batch-CLI wiring/report - see "What moved" for which cluster
each came from).

## What's open
- REVIEW.md's F09 center-third-proxy note: still open, still untouched.
- DECISIONS.md D-007 (F14/S03 grouping): open, needs a human ruling before
  either ID can move past its current stub.
- `r01.py`'s previously-flagged stale citation (REVIEW.md, three
  consecutive reviews) is resolved as a side effect of this session's
  rewrite - the module no longer references "QUEUE.md item 3" at all.
- This session made no Anthropic API calls (R01 has no vision/network
  dependency) - no fixture files touched.
- DECISIONS.md open count: 1 (D-007, opened this session).

## Files touched
`QUEUE.md`, `DECISIONS.md`, `src/picstory/schema.py`, `schema/analysis.json`,
`src/picstory/detectors/r01.py`, `scripts/analyze_batch.py`,
`tests/test_schema.py`, `tests/test_r01_haze_rule.py` (new),
`tests/test_cli_analyze_batch.py`, `tests/test_detector_registry.py`.
