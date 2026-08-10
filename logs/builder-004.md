# builder-004 — 2026-08-10

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 3/20 builder sessions used, hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (`critic-001`) — no findings requiring action on prior
  work; flagged S03 as a forward-looking watch item for when item 4 landed
  (see below - acted on this session).
- `DECISIONS.md`: open count 2 (D-003, D-004) at session start — below the
  5-item halt threshold. Two entries added this session (D-005, D-006); open
  count now 4, still below threshold.
- Most recent `logs/` entry: `builder-003.md` (local detectors, QUEUE item 3,
  merged as PR #4 into `main`, `12a7d17`).
- Branch: `claude/brave-clarke-epzt97` was already even with `origin/main`
  (contained all of builder-003's merged work, nothing to restart).

## What moved
Implemented QUEUE.md Stage 1, item 4 for 9 of its 11 listed IDs — the
Anthropic API vision-call detectors: F04, F05, F06, F11, F13, F15, S01, S02,
S04. F14 and S03 are deferred; see "What's open" below.

- `src/picstory/schema.py` — added `taxonomy_detection_text(id)`, parsed
  verbatim from TAXONOMY.md's `- **Detection:**` bullets, same pattern as
  the existing `taxonomy_ids()`. Per-ID modules call this rather than
  hardcoding their own copy of the Detection text, so verbatim drift
  (CLAUDE.md's API-discipline rule) is structurally impossible rather than
  merely tested for.
- `src/picstory/detectors/_vision.py` — shared plumbing for all judgment-
  dependent detectors: builds the Anthropic Messages API request (image +
  prompt wrapping the item's Detection text), forces a `report_taxonomy_finding`
  tool call as structured output (fields: `taxonomy_id`, `detected`,
  `rationale`), parses the response, and raises `VisionCallError` if the
  structured output doesn't name the requested ID or is otherwise malformed.
  The call boundary (`VisionCaller`) is injected via `judge(..., caller=...)`;
  production code gets `default_caller()` (real `anthropic` SDK client,
  `ANTHROPIC_API_KEY` from env per D-001's amendment), tests always inject a
  fake. Model: `claude-sonnet-5` — a bounded-cost per-frame judgment call
  under the owner's spend cap, not the flagship tier.
- Nine per-ID modules (`f04.py`, `f05.py`, `f06.py`, `f11.py`, `f13.py`,
  `f15.py`, `s01.py`, `s02.py`, `s04.py`), each ~15 lines: register the ID,
  call `_vision.judge(frame, ID, taxonomy_detection_text(ID), caller=caller)`.
  No per-item detection logic lives in these modules beyond their ID and the
  (structurally-guaranteed-verbatim) Detection text - that's deliberate; the
  actual judgment is the model's, per CLAUDE.md's design for this class of
  detector.
- `pyproject.toml` / `uv.lock` — added `anthropic>=0.121.0` (a `uv add`,
  package install, allowed under CLAUDE.md's network rule).
- `tests/test_vision_detectors.py` — 43 tests collected (pytest expands the
  parametrized ones per-ID). Per-ID positive/negative pairs for all 9 IDs
  via an injected spy caller (`test_f04_...` through `test_s04_...`, 18
  tests, matching the coverage guard's naming convention); two parametrized
  checks × 9 IDs (18 tests) - one confirming each module actually sent
  `schema.taxonomy_detection_text(ID)` to the caller (not a paraphrase, not
  empty), one confirming each module's `TAXONOMY_ID` matches its registered
  ID; a `judge()`-level guard test for a caller answering the wrong ID; and
  6 direct tests of `_vision.parse_tool_use_response` against hand-built
  objects shaped like the real Anthropic SDK's tool_use response (valid
  verdict, a leading text block before the tool_use block, missing tool_use
  block, mismatched taxonomy_id, missing `detected`, empty `rationale`) —
  see the fixture note below.
- `tests/test_detector_registry.py` — shrank `_STILL_STUBBED` from the 13
  IDs pending item 4/item 8 to `{F03, F14, R01, S03}`: F03 is Stage 2 item 8,
  R01 isn't scheduled yet, F14/S03 are deferred (see below).

## Fixture gap: no ANTHROPIC_API_KEY in this session (logged as D-006)
CLAUDE.md's API-discipline rule calls for the test suite to run offline
against *recorded* API responses. This session's environment has no
`ANTHROPIC_API_KEY` (checked `env` for any `*_API_KEY`/`*_TOKEN`/`*_SECRET`
variable - none for Anthropic exists) and no way to reach api.anthropic.com
directly even with one (`curl`/`wget`/`WebFetch`/`WebSearch` are denied in
`.claude/settings.json`). So no live call was possible to record a genuine
fixture from. `tests/test_vision_detectors.py`'s response-shaped fixtures
are hand-authored to match the documented Anthropic Messages API tool_use
structure, not recordings — the file's docstring says this explicitly, and
so does DECISIONS.md D-006, which lays out three options for the owner (key
access for agent sessions; owner records a real round and commits it; accept
the gap for now). This is flagged rather than silently building genuinely
fake data and calling it a recorded fixture — the parsing logic
(`parse_tool_use_response`) is genuinely exercised by these fixtures; what's
unverified is that a live Claude call, given these exact prompts and images,
actually returns output in the expected shape with sensible verdicts.

## What's open — F14 and S03 deferred (DECISIONS.md D-005)
QUEUE.md item 4 groups F14 (Wide-shot monoculture) and S03 (Tight framing)
with the other single-frame vision detectors, but both items' Detection text
names a property of a *set* of frames, not of any single photo: F14 is "a
location's coverage is all establishing views"; S03 is "the tightest frame
of a subject among its batch-mates," explicitly relative. Stage 1 processes
one photo at a time - there is no batch to compare against yet. A
single-frame vision call answering "does this look tightly framed?" or
"does this look like an establishing shot?" would be judging a different,
easier question than the one TAXONOMY.md poses for these IDs - exactly the
plausible-substitute failure PREDICTION.md predicts and CRITIC is
instructed to check for. critic-001 flagged this specifically for S03 as a
forward-looking watch item before item 4 was implemented; this session
extends the same reasoning to F14 and logs both as DECISIONS.md D-005
rather than shipping a substitute. Their registry stubs are unchanged (still
`DetectorNotImplemented`) - implementing them properly is Stage 2 work, once
QUEUE.md items 7-9 (batching, near-duplicate grouping, ranking) give
detectors batch/location context.

## Other open items
- QUEUE item 5 (CLI) and the remainder of item 6 (F03/R01 tests, once those
  land) not started.
- `tests/test_taxonomy_coverage.py::test_every_id_has_detector_and_named_test`
  still fails, expected: `missing_test` is now `[F03, F14, R01, S03]`, down
  from the 13 it listed after builder-003.
- DECISIONS.md open count: 4 (D-003, D-004, D-005, D-006) — below the
  5-item halt threshold, but one more open item would trigger it. The next
  session (BUILDER or CRITIC) should weigh whether to prioritize getting a
  human ruling on any of the four before opening a fifth.

## Test count
87 collected: 86 passed, 1 failed (the coverage guard, expected — down to 4
missing IDs from 13, was 13 after builder-003). By file: 18 test_schema.py +
6 test_detector_registry.py + 18 test_local_detectors.py + 2
test_taxonomy_coverage.py (all pre-existing, unchanged behavior save for
`_STILL_STUBBED`'s shrink) + 43 new in `tests/test_vision_detectors.py`.
