# builder-006 — 2026-08-10

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 5/20 builder sessions used, hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (`critic-001`) — covers builder-001/002 only, no
  findings requiring action this session.
- `DECISIONS.md`: open count 0 at session start (D-001–D-006 all `RULED`,
  including D-003 through D-006 ruled since builder-005). No new entry added
  this session.
- Most recent `logs/` entry: `builder-005.md` (QUEUE item 5, `scripts/analyze.py`).
- Branch `claude/brave-clarke-uzsp4w` already existed on `origin`, at
  `08ee5bb` ("rule D-003 through D-006; open count to 0"), even with itself
  — nothing to fast-forward.

## What moved
D-006's ruling (10 Aug 2026, owner) named specific next steps for "the next
BUILDER session" — this session — rather than a QUEUE.md line item, so it
took priority: it's a live human instruction, not open work waiting for one.

1. **Which env var is actually visible, as the ruling asked to confirm:**
   checked `env` for both names. `PICSTORY_VISION_KEY` is present.
   `ANTHROPIC_API_KEY` is absent. This matches the ruling's platform-filtering
   theory for the reserved name.

2. **`_vision.default_caller()`** (`src/picstory/detectors/_vision.py`) now
   resolves `PICSTORY_VISION_KEY` first, falling back to `ANTHROPIC_API_KEY`,
   and passes the result explicitly to `anthropic.Anthropic(api_key=...)`
   instead of relying on the SDK's own (ANTHROPIC_API_KEY-only) env lookup.
   Two new offline unit tests patch `anthropic.Anthropic` itself so
   `default_caller()`'s real resolution code runs end-to-end without a
   network call: `test_default_caller_prefers_picstory_vision_key`,
   `test_default_caller_falls_back_to_anthropic_api_key`.

3. **4 live calls made**, per the ruling's "make a small number of live
   calls" — `scripts/record_vision_fixtures.py` (new; kept in the repo as a
   reusable recorder, not a one-shot throwaway, since D-006 already
   anticipated this might need repeating). No photos exist in this repo, so
   the script draws two synthetic scenes with Pillow (a lone monument; the
   same monument plus a small dark human-silhouette shape at its base) and
   calls the real API against both for two taxonomy IDs (F13, S01) — enough
   variation to see the model actually discriminate, not just echo one
   canned shape. All 4 succeeded via `PICSTORY_VISION_KEY`; raw responses
   saved to `tests/fixtures/vision/{f13,s01}_landmark_{alone,with_figure}.json`
   via `response.model_dump(mode="json")`.

   Verdicts, for the record (not asserted as "correct," just genuinely
   returned by the live model — see next point on why F13 came back
   `True` twice):
   - F13 on the monument alone: `detected=True` — "no people, vehicles, or
     other reference objects to indicate its actual scale."
   - F13 on the monument + silhouette: `detected=True` — the model read the
     drawn silhouette as "a small, ambiguous dark figure... that doesn't
     clearly establish scale," not a real figure.
   - S01 on both: `detected=False` — same reasoning in reverse: "a simple
     abstract icon (a dark circle on a rectangle), not an actual person."
   This is a real, useful result even though F13 didn't flip between the two
   images as designed: it shows the model isn't rubber-stamping a drawn
   shape as "a person" just because that's what the test intended it to be
   read as — exactly the kind of judgment-dependent discrimination these
   detectors exist for. A future session recording more fixtures should use
   a photographic (or more clearly figurative) foreground element if it
   wants a case that actually flips `detected`.

4. **Replaced the hand-authored "valid verdict" happy-path test** in
   `tests/test_vision_detectors.py`
   (`test_parse_tool_use_response_extracts_valid_verdict`) with 4
   parametrized tests that load the recorded fixtures above and replay them
   through the real `parse_tool_use_response` —
   `test_parse_tool_use_response_replays_genuine_recorded_api_call`. This is
   the specific gap D-006 named: `parse_tool_use_response` is now backed by
   evidence a real Claude response, prompted with these exact Detection
   texts and images, comes back in the shape the code expects.

   The remaining `_FakeToolUseBlock`/`_FakeResponse`-based tests
   (`ignores_leading_text_block`, `raises_when_no_tool_use_block`,
   `raises_on_taxonomy_id_mismatch`, `raises_on_missing_detected_field`,
   `raises_on_empty_rationale`) stay hand-authored, on purpose: this
   module's `tool_choice` forces the tool call, so a real API response
   cannot come back malformed in any of these ways — there is no live
   equivalent to record for them. Module docstring rewritten to say this
   plainly (previously it also mis-cited D-005 as the tracking entry for
   this gap; it was D-006).

## Test count
101 collected: 100 passed, 1 failed (the coverage guard, expected and
unchanged in substance — `missing_test` still `[F03, F14, R01, S03]`, Stage
2 work per D-005). Net +5 over builder-005's 96 (43 -> 46 in
`test_vision_detectors.py`: -1 replaced happy-path test, +4 recorded-fixture
replays, +2 `default_caller` key-resolution tests = net +5; other files
unchanged).

## What's open
- Same Stage 2/3/4 backlog as builder-005 (QUEUE items 4's F14/S03, 7-12) —
  untouched this session; this session was D-006 follow-through, not a
  QUEUE.md line item.
- `tests/test_taxonomy_coverage.py::test_every_id_has_detector_and_named_test`
  still fails, expected, same 4 IDs as builder-005 left it.
- DECISIONS.md open count: 0. No entry opened or closed this session (only
  the human rules; this session just carried out D-006's ruling).
- The 4 recorded fixtures only exercise F13 and S01, out of the 9
  API-vision detectors landed in QUEUE item 4. The other 7
  (F04, F05, F06, F11, F15, S02, S04) still have no genuine recorded-response
  evidence, only the necessarily-synthetic malformed-shape tests apply to
  all of them equally. Re-running `scripts/record_vision_fixtures.py` with a
  broader `calls` list would extend coverage; left as-is this session to
  keep "a small number of live calls" small, per the ruling's own wording.
