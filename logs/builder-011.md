# builder-011 — 2026-08-12

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 10/20 builder sessions
  used (this session is the 11th), hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-003, covers through builder-010 / `7136ac1`).
  Its two open notes (F09's center-third proxy, `r01.py`'s stale
  QUEUE-item-3 citation) are for whoever next touches those specific files;
  neither is item 11, so neither blocked this session.
- `DECISIONS.md`: open count 0 at session start (D-001–D-006 all `RULED`).
  No new entry added this session.
- Most recent `logs/` entry: `critic-003.md`, over `builder-010.md` (item
  10: session habit).
- Branch: designated branch `claude/brave-clarke-e099s6` already existed on
  `origin`, HEAD (`fff23fb`) identical to `origin/main` (PR #14's merge,
  critic-003) — no fresh branch needed, continued directly on it.

## What moved
QUEUE.md Stage 1 (items 1–6) and Stage 2 (items 7–10) were already done.
Item 11 is next and unblocked: "CMP rubric implementation over
near-duplicate groups: the three axes + story tiebreaker, exactly as
TAXONOMY.md §CMP. Output names the winner and states per-axis differences."

**Before touching item 11, a discovery that changed how the rest of the
session ran.** While reasoning about how CMP's vision call should be
test-injected (mirroring `_vision.judge`'s `caller` pattern), I checked
whether the existing `main()` end-to-end smoke tests
(`test_cli_analyze.py`/`test_cli_analyze_batch.py`'s
`test_main_writes_report_and_prints_at_most_three_lines`) actually honor
CLAUDE.md's "the test suite must run offline ... tests never make live
calls" rule. They don't call `detector_lookup`/`caller` overrides at all —
`main()` uses the real registry on purpose (it's testing production wiring)
— and this session's sandbox has a genuinely working `PICSTORY_VISION_KEY`
(confirmed directly: `anthropic.Anthropic(...).messages.create(...)`
succeeded end-to-end from the shell in 2.5s, unlike the no-key sandbox
D-006 diagnosed). So every `uv run pytest` in this and presumably recent
prior sessions was silently making real, spend-cap-metered live calls to
`api.anthropic.com` — 9 judgment-dependent detectors × 1–5 frames per
`main()` test, ~194s of the full-suite runtime builder-010/critic-003 both
already noted without diagnosing the cause. No prior CRITIC session flagged
this (checked all three critic logs for "offline"/"live call"/"network" —
no hits). Wiring CMP the same way `_vision.judge` is wired would have added
one more live call on top of these on every test run.

Fixed with `tests/conftest.py`: an autouse fixture patches
`anthropic.Anthropic` itself to a client whose `.messages.create` raises
immediately (no network I/O, not even a doomed 401 round-trip) for the
whole test session. Verified this doesn't break the two D-006
key-resolution tests in `test_vision_detectors.py`, which patch
`anthropic.Anthropic` themselves within the test body (later `monkeypatch`
call on the same fixture instance simply overrides mine for that test,
restored correctly either way). Confirmed the fix: the two `main()` smoke
tests went from a 60s+ timeout (`test_cli_analyze_batch.py`'s alone didn't
finish inside 60s) to both passing in under 1s combined, and the full suite
from ~180–200s (three prior sessions' own reported number) to ~1.4s. This
is in scope for item 11 rather than a tangent: it's the same live-call
surface CMP's own wiring sits on, discovered while designing that wiring,
and left unfixed it would have made a real, previously-undetected spend
problem measurably worse rather than just not-better.

**Item 11 itself:**

1. **`src/picstory/schema.py`**: added `cmp_rubric_text()`, parsing
   TAXONOMY.md's `## CMP` section verbatim (intro paragraph, the three
   named axes, the tiebreaker, and the "what the output names" closing
   line) — same single-source-of-truth reasoning as
   `taxonomy_detection_text`, extended to CMP: it has no `- **Detection:**`
   bullet the way F/S items do, so the whole section stands in for that
   role in the API-discipline rule (CLAUDE.md: "embeds the item's Detection
   text verbatim"). Added `Comparison` (group, winner_frame_id, three axis
   strings, optional tiebreaker) with validation (≥2 frames, winner must be
   in group, axis text non-empty) — deliberately carries no F/S taxonomy
   IDs, since TAXONOMY.md's own output-mapping table says the comparison
   draws on "The CMP rubric, exclusively." Wired `comparisons: list[Comparison]`
   into `AnalysisOutput`, validated against known `frame_id`s the same way
   `pick.frame_id` already is.
2. **`schema/analysis.json`**: mirrored `comparisons` + `$defs.comparison`.
3. **`src/picstory/cmp.py`** (new): multi-image comparison call/parse
   plumbing, parallel to `detectors._vision` but shaped for N images in one
   call instead of one — this is judgment across multiple frames at once
   ("which frame cuts what," relative to each other), not a single-frame
   question the way F04–F15/S01–S04 are. `_tool_schema`'s
   `winning_frame_id` is an `enum` of the actual frame_ids sent, so the
   model structurally cannot name a frame that wasn't in the call.
   `compare_group(frames, caller=None)` defaults to the live API
   (`default_caller()`, same `PICSTORY_VISION_KEY`-first resolution as
   `_vision.default_caller`); every test injects a fake. Reuses
   `_vision.MODEL`/`_vision._encode_jpeg` directly — precedent already set
   by `scripts/record_vision_fixtures.py` reaching into `_vision`'s private
   helpers.
4. **`scripts/analyze_batch.py`**: `run_batch_analysis` now also calls
   `detectors.f03.group_near_duplicates(frames)` directly (the real, pure
   grouping function — not through F03's registered `detect()`, which
   returns per-frame Findings, not groups) and runs `cmp.compare_group`
   (injectable as `cmp_compare`, defaulting real — same pattern as
   `detector_lookup`) once per group. A failing comparison is caught and
   logged as `ComparisonRun("error", ...)`, not fatal to the batch — same
   treatment `_run_f03` already gives a broken F03 call, and the same
   reading of CLAUDE.md's spending rule ("if the cap is hit ... log it,
   move on"). `run_batch_analysis` now returns a 3-tuple
   (`output, runs_by_frame, comparison_runs`); `render_report` gained a
   `## Comparisons` section. Updated all 13 existing call sites in
   `tests/test_cli_analyze_batch.py` for the new return shape, and gave
   that file's `_frame()` helper a distinct EXIF `FocalLength` per call
   (defeats F03's own pairwise focal-length check deterministically,
   regardless of pixel content) so none of the pre-existing tests'
   identical zero-pixel frames accidentally form a near-duplicate group and
   exercise the real `cmp_compare` default.
5. **Recorded a genuine CMP fixture**, same precedent as D-006/
   `scripts/record_vision_fixtures.py`: `scripts/record_cmp_fixture.py`
   (new, one-off, run by hand — not by pytest) draws two synthetic
   near-duplicate scenes (a wide, empty monument shot; a tighter crop with
   a mid-stride walker added) and makes one live CMP call. Recorded to
   `tests/fixtures/cmp/wide_vs_tight_with_walker.json`. The live model's
   own verdict actually used the tiebreaker (walker as story element,
   `winner: tight`) — a genuine exercise of that rubric clause, not a
   hand-authored guess at what a model would say.
6. **Tests**: `tests/test_schema.py` gained 10 (CMP rubric text — verbatim
   substrings for the axes/tiebreaker, section-boundary guard; `Comparison`
   validation; `AnalysisOutput.comparisons` roundtrip/validation).
   `tests/test_cmp.py` (new, 14): `compare_group` wiring/request shape,
   tool-schema `enum` constraint, prompt embeds the rubric verbatim,
   `parse_tool_use_response` against hand-built malformed shapes (mirrors
   `test_vision_detectors.py`'s reasoning: a real, schema-enforced call
   can't produce these) and against the one genuine recorded call above.
   `tests/test_cli_analyze_batch.py` gained 5 (no-groups-means-no-call,
   a real group triggers `cmp_compare` with the right frames, a failed
   comparison is logged not fatal, both surfaced in `render_report`).

## Test count
188 collected: 187 passed, 1 expected fail
(`test_taxonomy_coverage.py::test_every_id_has_detector_and_named_test`,
`missing_test = [F14, R01, S03]` — unchanged from builder-008 onward; D-005
covers F14/S03, R01 has no scheduling decision yet; this session touched no
detector). Full suite run directly (`uv run pytest -q`), **1.4s** — down
from the ~180–200s every prior session reported, because `tests/conftest.py`
now actually blocks the live calls those runs were silently making (see
above). Growth: 159 → 188 (+29: 10 schema, 14 cmp, 5 batch-wiring).

## What's open
- QUEUE.md item 12 (the profile) is next; its `[blocked: D-004]` tag was
  already lifted by D-004's ruling ("If Stage 4 arrives during the
  experiment ... profile work may proceed on the free assumption").
- REVIEW.md's two outstanding notes from critic-002/critic-003 (F09's
  center-third proxy, R01's stale citation) are still open for whoever next
  touches those specific files — neither was touched this session.
- `tests/conftest.py`'s live-call fix is scoped to *this repo's* test
  suite. It does not change `main()`'s own production behavior (still
  defaults to the real registry, correctly) — only what happens when tests
  invoke `main()` without overriding it. Worth CRITIC verifying the
  reasoning holds: is patching `anthropic.Anthropic` globally the right
  backstop, or should individual tests have been made to inject fakes
  instead (more verbose, but doesn't rely on a global fixture staying in
  sync with the SDK's client shape)? I judged the global fixture safer
  given the discovered real-spend cost of leaving it to per-test
  discipline, but this is a testing-infrastructure judgment call, not a
  taxonomy question, so it's flagged here rather than as a DECISIONS.md
  entry.
- CMP's `compare_group` is a single call per near-duplicate group (whole
  group in one prompt), not pairwise — TAXONOMY.md's own framing ("the
  three-frame comparison") and the "2-5" example sizes in F03 suggested
  groups are usually small, but a very large safety-copy run (F03 doesn't
  cap at 5, see f03.py's own docstring) would mean a lot of images in one
  call. Not observed in practice this session (no real multi-photo batch
  run through `main()` with a large duplicate run), flagged for whoever
  next runs this against a real batch.
- DECISIONS.md open count: 0. No entry opened or closed this session.

## Files touched
`tests/conftest.py` (new), `src/picstory/schema.py`, `schema/analysis.json`,
`src/picstory/cmp.py` (new), `scripts/analyze_batch.py`,
`scripts/record_cmp_fixture.py` (new), `tests/fixtures/cmp/` (new),
`tests/test_schema.py`, `tests/test_cmp.py` (new),
`tests/test_cli_analyze_batch.py`.
