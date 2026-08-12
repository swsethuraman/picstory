# builder-012 — 2026-08-12

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 11/20 builder sessions
  used (this session is the 12th), hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-003, covers through builder-010 / `7136ac1`,
  predates builder-011's item 11). Its two open notes (F09's center-third
  proxy, `r01.py`'s stale QUEUE-item-3 citation) are for whoever next
  touches those specific files; neither is item 12, so neither blocked this
  session.
- `DECISIONS.md`: open count 0 at session start (D-001–D-006 all `RULED`).
  No new entry added this session.
- Most recent `logs/` entry: `builder-011.md` (item 11, CMP), confirmed via
  `git log --oneline -- logs/` (file mtimes are unreliable — this is a
  fresh checkout, everything shares one clone timestamp).
- Branch: designated branch `claude/brave-clarke-rjid8k` already existed on
  `origin`, HEAD (`2402cd5`, PR #15's merge) identical to
  `origin/claude/brave-clarke-rjid8k` — no fresh branch needed, continued
  directly on it. No PR exists yet for this exact branch name
  (`list_pull_requests` with this head returned empty), so the "already
  merged, restart from main" fallback in this session's own operating
  instructions did not apply.

## What moved
QUEUE.md Stage 1–3 (items 1–11) were already done. Item 12 (Stage 4, "the
profile") is next: "Per-user recurrence store across sessions, with
sub-pattern detail (e.g. which edge for F06)." Its `[blocked: D-004]` tag
was already lifted by D-004's ruling ("If Stage 4 arrives during the
experiment ... profile work may proceed on the free assumption").

TAXONOMY.md's output-mapping table is the whole spec here too: "The running
profile | Per-user recurrence of F/S items and their sub-patterns (e.g.
*which* edge the user neglects)." F06 is the taxonomy's only worked example
— its own entry carries a "- **Profile note:**" bullet ("Directional
sub-patterns ... are per-user traits tracked by the profile, not separate
taxonomy items") that no other F/S item has. Read literally, that made two
things the actual scope, not one:

1. **The store itself**: fold F/S recurrence across sessions (CLI
   invocations, not BUILDER agent sessions — a different, unrelated
   meaning of "session") into a persisted profile.
2. **F06's sub-pattern, genuinely**: "which edge" has to come from
   somewhere real. The only real signal available is F06's own vision call
   — so the honest implementation is asking the model to name the edge
   *in the same structured call*, enum-constrained, not regex-scanning its
   free-text rationale for the word "left" or "right" afterward (a
   plausible-substitute pattern PREDICTION.md would call out and CRITIC
   checks for). Doing the second thing properly changed the shape of the
   first: `Finding` needed a `sub_pattern` field, and the shared vision
   call plumbing (`_vision.py`) needed a way to ask for one without every
   *other* judgment-dependent detector accidentally gaining loose,
   unvalidated extra output.

**1. `src/picstory/schema.py`**: added `taxonomy_ids_with_subpattern()`,
parsing each item's `- **Profile note:**` bullet the same verbatim-source-
of-truth way `taxonomy_detection_text`/`_reinforcement_texts`/
`_correction_texts`/`cmp_rubric_text` already do — today returns `{"F06"}`,
parsed rather than hardcoded, so a future TAXONOMY.md amendment adding
another Profile note is picked up with no code change. `Finding` gained an
optional `sub_pattern: str | None` field, validated in `__post_init__`:
non-empty if set, and only settable on an ID `taxonomy_ids_with_subpattern()`
actually names — F01 (no Profile note) raises `SchemaError` if you try. This
is the structural enforcement that keeps "sub-pattern" from becoming a
free-for-all extra field on any finding. `to_dict`/`from_dict` updated;
`schema/analysis.json` mirrored with the new property and its own
docstring pointing back at the Python-side guard.

**2. `src/picstory/detectors/_vision.py`**: new `SubPatternSpec` (frozen
dataclass: `field_name`, `enum_values`, `description`) — an opt-in, closed-
vocabulary extra field a detector can ask the shared vision-call machinery
for. `VisionRequest`/`VisionVerdict` both gained a `sub_pattern` slot
(default `None` — every existing detector's request/verdict shape is
unchanged unless it opts in). `_tool_schema`, `_prompt`,
`_verdict_from_tool_input`, `parse_tool_use_response`, `default_caller`'s
inner `call`, and `judge` all thread an optional `sub_pattern: SubPatternSpec
| None` parameter through — when given, the tool schema gains an
`enum`-constrained property (not in `required`, since the model should omit
it when `detected` is `false`); parsing then enforces "present and one of
the enum values when `detected` is `true`" itself, since JSON Schema alone
can't express "required only conditionally." Every other detector (F04,
F05, F11, F13, F15, S01, S02, S04) calls `judge()` without this argument, so
their tool schemas, prompts, and `VisionRequest`s are byte-for-byte
unchanged — verified by a new parametrized test
(`test_only_f06_requests_a_sub_pattern`) that spies on the actual request
each one sends.

**3. `src/picstory/detectors/f06.py`**: added `EDGE_SUB_PATTERN =
SubPatternSpec(field_name="edge", enum_values=("left", "right", "top",
"bottom", "multiple"), description=...)`, wired into its `judge()` call.
The enum vocabulary reads directly off F06's own TAXONOMY.md text: its
Profile note names "right-third" and "left-edge" as examples; its
Correction text ("Sweep all four edges") is what makes top/bottom the
obvious, taxonomy-consistent completion rather than an invented addition;
`multiple` covers the genuine "more than one edge" case rather than forcing
a false single choice.

**4. `src/picstory/profile.py`** (new): the store. `IdRecurrence`
(`taxonomy_id`, `sessions`, `frames`, `sub_patterns: dict[str, int]`) and
`Profile` (`schema_version`, `sessions_recorded`,
`recurrences: dict[str, IdRecurrence]`), both with `to_dict`/`from_dict`/
JSON round-trip, same shape convention as `schema.py`'s dataclasses.
`default_profile_path()` resolves `PICSTORY_PROFILE_PATH` first, falling
back to `~/.picstory/profile.json` — the same env-var-first, sensible-
default pattern D-006 established for `PICSTORY_VISION_KEY`.
`load_profile`/`save_profile` are the module's only I/O.
`record_session(profile, frame_analyses) -> Profile` is pure (returns a new
`Profile`, never mutates its argument — verified by a dedicated test): one
session increments `sessions` for every F/S ID that appeared on *any* frame
this batch (not once per occurrence), `frames` increments once per
carrying frame, and `sub_patterns` tallies every occurrence of a finding's
`sub_pattern` value. R01 and `unclassified` are excluded — the same
exclusion `ranking.py`'s `score_frame`/`compute_habit` already apply, for
the same reason (R01 is never a per-frame `Finding`; `unclassified` has no
polarity). `top_recurrences`/`summary_lines` give a deterministic display
ordering (sessions desc, then frames desc, then ID ascending) and a
formatted-line helper, mirroring `ranking.share_list_lines`'s precedent of
some formatting logic living in `src/` rather than only in the CLI.

**5. `scripts/analyze_batch.py`**: `main()` now resolves a profile path
(new `--profile-path` flag, defaulting to
`profile.default_profile_path()`), loads whatever's already there, folds
this run's `output.frames` in via `record_session`, and saves the result —
`run_batch_analysis` itself stays pure/untouched (no I/O added to it).
`render_report` gained an `updated_profile` parameter and a `## Profile`
section showing `sessions_recorded` and `profile.summary_lines()`'s output,
including F06's sub-pattern tally when present (e.g. "F06: 3 sessions, 5
frames (right x3, left x1)").

**6. `scripts/record_vision_fixtures.py`**: extended for F06 — a new
`_edge_intrusion_scene()` (the existing lone-monument scene plus a dark,
shoulder-like ellipse bleeding in from the right edge) and 2 more live
calls (`landmark_alone` and `edge_intrusion_right`, both against F06 with
`EDGE_SUB_PATTERN`), on top of the 4 pre-existing F13/S01 calls (6 total).
Ran it by hand this session (`PICSTORY_VISION_KEY` was present and working
— confirmed via the run's own summary line, `key source:
PICSTORY_VISION_KEY`) — same D-006 precedent builder-011 followed for CMP's
fixture. **The live model's own verdict is genuinely useful evidence**: on
`landmark_alone` it correctly said `detected=False`; on
`edge_intrusion_right` it said `detected=True, edge=right` — the actual
right-edge intrusion, not a guessed or hand-picked value. Recorded to
`tests/fixtures/vision/f06_landmark_alone.json` and
`f06_edge_intrusion_right.json`. Running the script also re-recorded the 4
pre-existing F13/S01 fixtures (new live calls, unavoidable side effect of
the script processing its whole `calls` list) — their `detected` verdicts
were unchanged from before, but rather than commit an unrelated diff (new
token IDs, slightly reworded rationale) for calls this session didn't need,
I reverted those 4 files to their previously-committed content via `git
checkout --`. Disclosing this: it means this session made 6 live calls
total, not 2 — 4 of them were spend this session's own scope didn't
strictly need, an avoidable cost from the script's all-or-nothing design
that whoever next extends this script should split per-ID if that matters.

**7. Tests**: `tests/conftest.py` gained a second autouse fixture,
`_isolate_profile_store` — sets `PICSTORY_PROFILE_PATH` to a fresh
`tmp_path` for *every* test, the same session-wide-backstop shape as the
existing live-call-blocking fixture, so no test (this session's or a future
one's) can accidentally read/write a real `~/.picstory/profile.json` on
whatever machine runs the suite. `tests/test_schema.py` gained 6 tests
(`taxonomy_ids_with_subpattern` parses F06's note; `Finding.sub_pattern`
allowed/rejected/blank/default/roundtrip). `tests/test_vision_detectors.py`
gained sub_pattern coverage: F06 wiring (carries the caller's value, `None`
when the caller omits it, the request carries `EDGE_SUB_PATTERN`),
`test_only_f06_requests_a_sub_pattern` (parametrized over the other 8
judgment-dependent IDs, asserting their requests carry none),
`_tool_schema` enum-property tests, `parse_tool_use_response` sub_pattern
extraction/validation tests (extracts when detected, ignored when not,
rejects an invalid or missing value when detected), and 2 new
`...replays_genuine_recorded_f06_edge_sub_pattern` tests replaying this
session's live recordings. `tests/test_profile.py` (new, 21 tests):
construction/validation/roundtrip for `Profile`/`IdRecurrence`,
`default_profile_path`'s env-var/fallback behavior, `load_profile`/
`save_profile` roundtrip via `tmp_path`, `record_session`'s purity and its
session/frame/sub-pattern counting rules (including the
R01/unclassified exclusion — named
`test_record_session_excludes_conditional_rule_and_unclassified` rather
than a name containing the literal substring "r01", specifically to avoid
an accidental match in `test_taxonomy_coverage.py`'s ID-in-function-name
naming guard, which would have looked like new R01 test coverage without
actually testing R01's behavior). `tests/test_cli_analyze_batch.py` gained
3: the `## Profile` section reflects an injected `Profile`, is absent when
none is given, and — the significant one — `main()` run twice against the
same `--profile-path` on two different photo batches shows
`sessions_recorded` go `1` then `2`, i.e. genuine accumulation through a
file, not just in-memory wiring.

## Test count
237 collected: 236 passed, 1 expected fail
(`test_every_id_has_detector_and_named_test`, `missing_test = [F14, R01,
S03]` — unchanged from builder-008 onward; D-005 covers F14/S03, R01 has no
scheduling decision yet; this session touched no per-ID detector besides
F06's existing one). Full suite run directly (`uv run pytest -q`), **1.8s**.
Growth: 188 → 237 (+49: 6 schema, ~16 vision-detector sub_pattern/tool-
schema/parse tests, 21 profile, 3 batch-CLI wiring — see "What moved" for
which cluster each came from; exact per-file counts are in the diff, not
re-derived here since `git diff --stat` already gives them precisely).

## What's open
- REVIEW.md's two outstanding notes from critic-002/critic-003 (F09's
  center-third proxy, R01's stale citation) are still open for whoever next
  touches those specific files — neither was touched this session.
- Only F06 has a documented Profile note today, so it is the only ID the
  profile's `sub_patterns` tally will ever have data for until TAXONOMY.md
  gains another one — this is TAXONOMY.md's own scope, not an
  implementation gap: "Per-user variation mostly is not expansion ...
  profile-layer data, not new taxonomy items" (section U) frames sub-
  patterns as the expected shape of future per-user variation, and this
  session's `taxonomy_ids_with_subpattern()` is built to pick up a new
  Profile note with zero code change when one is added.
- The profile store's location (`~/.picstory/profile.json` by default) is a
  real product decision this session made without a DECISIONS.md entry:
  QUEUE.md item 12 says "per-user recurrence store across sessions" but
  doesn't specify *where* that store lives for a single-user local CLI
  tool. I judged this non-blocking (it's a sensible, overridable default
  for exactly the "local CLI/pipeline" shape D-002 already settled the
  product on, and `PICSTORY_PROFILE_PATH` makes it fully overridable) but
  flagging it for CRITIC in case the reasoning should have been a
  DECISIONS.md entry instead of a judgment call.
- `record_session`'s "one session = one `sessions` increment regardless of
  how many frames in the batch carry the ID" reading is the same recurrence
  semantics `ranking.compute_habit` already uses within one session,
  extended across sessions - not re-derived from a separate spec, since
  TAXONOMY.md's "running profile" row doesn't define "recurrence" any more
  precisely than that. Worth CRITIC checking this reading holds.
- This session's 6 live vision-API calls (2 new F06 + 4 unavoidable
  F13/S01 re-recordings, the latter reverted from the working tree but not
  preventable before they happened) are the only network/spend activity.
- DECISIONS.md open count: 0. No entry opened or closed this session.

## Files touched
`src/picstory/schema.py`, `schema/analysis.json`,
`src/picstory/detectors/_vision.py`, `src/picstory/detectors/f06.py`,
`src/picstory/profile.py` (new), `scripts/analyze_batch.py`,
`scripts/record_vision_fixtures.py`, `tests/fixtures/vision/f06_*.json`
(new, 2), `tests/conftest.py`, `tests/test_schema.py`,
`tests/test_vision_detectors.py`, `tests/test_profile.py` (new),
`tests/test_cli_analyze_batch.py`.
