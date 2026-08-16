# builder-019 — 2026-08-16

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 18/25 builder sessions
  used (this session is the 19th), hard date 2026-08-29.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-005, covers through builder-017 plus owner
  commits up to and including TAXONOMY.md v1.2/D-008a-c/D-009's rulings).
  Predates builder-018 (item 17) and the owner's D-010 ruling commits —
  nothing in it names this session's scope (item 18).
- `DECISIONS.md`: open count 0 at session start. D-010 (filed open by
  builder-018) has since been `RULED` by the owner (accept S01-as-habit;
  item 17(a)'s "F08 must win" claim withdrawn) — visible in QUEUE.md's own
  text as a superseded note, and in the git log (`231cc1f`, `8b91188`,
  `93745bb`).
- Most recent `logs/` entry: `builder-018.md` (item 17, habit
  pervasiveness + ranking S-count tie-break). Since then: critic-005
  (review, no code), and three owner commits ruling D-010 and updating
  QUEUE.md/DECISIONS.md text accordingly. No code changed between
  builder-018 and this session's start.
- Branch `claude/epic-meitner-ncpm3q` — found already pointing at the same
  commit as `origin/main` (`93745bb`) at session start: the prior PR for
  this branch had merged. Per the branch-restart instructions, treated
  this as a fresh start from the latest default branch — since the branch
  already equaled `origin/main`'s tip exactly, no actual rebase/reset was
  needed; continued directly on it.

## What moved
QUEUE.md item 18, "Fixability parsing per D-009" — the top unblocked item
now that TAXONOMY.md v1.2 has landed and item 17 is done. All four
sub-parts, implemented against D-009's ruling text directly:

**18(a) — `schema.taxonomy_fixability(id)`.** Same verbatim-parse pattern
as `taxonomy_detection_text`/`taxonomy_correction_text`/etc.: a new
`_FIXABILITY_LINE` regex, cached `_fixability_texts()`, and
`taxonomy_fixability(id)` (raises for S/R items — v1.2's changelog is
explicit they carry none). Added `taxonomy_fixability_category(id)`
alongside it, parsing just the leading `post-fixable`/`capture-only`/
`conditional` word out of that same text (no second copy to drift).

**18(b) — byte-identical guard.** `test_v1_2_preserves_every_previously_
parsed_text_byte_identical` in `tests/test_schema.py`: hand-transcribed
every Detection text (all 20 F/S items), every Correction text (all 15
F items), every Reinforcement text (all 4 S items), R01's Rule, and F06's
Profile note — not a sample, the full set D-009(b) named — asserted
against the live parser output. All transcriptions matched on the first
run (verified by actually running the test, not assumed); this is
evidence v1.2 changed nothing but the new Fixability bullets, not just a
restatement of the requirement. Also added
`test_taxonomy_fixability_matches_taxonomy_md_verbatim` (all 15 Fixability
bullets, same treatment).

**18(c) — F05's conditional fixability via `SubPatternSpec`.**
`f05.py` gained `GEOMETRY_SUB_PATTERN` (`bowing` / `off_center_drift`),
wired into `judge()` exactly as F06 wires `EDGE_SUB_PATTERN`. This required
extending `schema.taxonomy_ids_with_subpattern()` beyond its previous
"Profile note bullet" source to also include IDs whose Fixability category
is `conditional` (today: F05 ∪ F06 = `{"F05", "F06"}`) — both are the same
`Finding.sub_pattern` mechanism serving two different downstream consumers
(profile recurrence vs. fixability resolution), documented as such in both
`schema.taxonomy_ids_with_subpattern`'s and `Finding.sub_pattern`'s
docstrings. Added `CONDITIONAL_FIXABILITY_RESOLUTION` (hand-transcribed
from the Fixability bullet's own prose, since that mapping isn't a second
structured bullet to regex for) and `resolve_finding_fixability(finding)`,
guarded by `test_conditional_fixability_resolution_is_complete` so a future
conditional item can't silently fall through.

Per D-006's precedent (a session with `PICSTORY_VISION_KEY` visible in
`env` may make a small number of live calls and record genuine fixtures):
made 4 live calls this session (not the 2 first planned) —
`scripts/record_vision_fixtures.py` gained a `--only ID` filter first
(so extending it doesn't re-spend on the 6 calls already recorded there),
then two new drawn scenes for F05's `geometry` sub-pattern. The first
`off_center_drift` scene (a pure horizontal shift of an otherwise
undistorted grid) was recorded and the live model correctly answered
`detected=False` — right call, wrong scene: F05's Detection text requires
curved/skewed lines, and a plain shift has neither. Rather than force a
positive result out of that recording, redesigned the scene to add real
shear (a keystoned grid with the medallion subject off the frame's true
center) and made two fresh calls (`--only F05`): the live model returned
`geometry=bowing` (detected=True) on the symmetric-bulge scene and
`geometry=off_center_drift` (detected=True) on the sheared scene — both
matching the intended label, genuinely, not hand-picked. All four raw
responses are under `tests/fixtures/vision/` (the superseded negative
result's fixture file was overwritten by the second, positive recording
under the same filename, not kept as a separate artifact — the earlier
`report()` output naming it is the record of what happened, per
`outputs/reports/`, which is gitignored). Replayed through
`parse_tool_use_response` in
`test_parse_tool_use_response_replays_genuine_recorded_f05_geometry_sub_pattern`,
same pattern as F06's equivalent test.

**18(d) — per-finding fixability in `analyze_batch`'s report.**
`DetectorRun` (shared by `analyze.py` and `analyze_batch.py`) gained a
`fixability: str | None = None` field. Computing it directly via
`resolve_finding_fixability` at `DetectorRun`-construction time crashed one
pre-existing test (`test_render_report_includes_pervasive_note_...`) that
hand-builds an F05 `Finding` without a `sub_pattern` (legal per
`schema.Finding` — `sub_pattern` is optional there) — a real design gap:
`resolve_finding_fixability`'s raise-on-unresolved-conditional is correct
as a schema-level invariant (a genuine F05 vision call can never produce
this shape, per `_vision.judge`'s `SubPatternSpec` enforcement) but too
strict as an unconditional call inside CLI report-building, which should
degrade like every other per-finding issue in this codebase rather than
crash the batch. Added `analyze._fixability_or_disclosed_gap`, a thin
wrapper that catches `SchemaError` and returns a disclosed
`"unresolved (...)"` string instead of propagating — used at both
`DetectorRun` construction sites. `render_report` in both `analyze.py` and
`analyze_batch.py` now prints `(fixability: <word>)` alongside each
detected finding's description when non-None.

## Tests
296 → 317 collected (+21, all new, all green except the one pre-existing,
intended F14 failure — see below). New coverage:
- `tests/test_schema.py`: Fixability text/category parsing (all 15 F
  items), the byte-identical v1.1→v1.2 guard (comprehensive, described
  above), `taxonomy_ids_with_subpattern` extended to F05, the conditional-
  resolution completeness guard, `resolve_finding_fixability` (post-fixable/
  capture-only/conditional-resolved/conditional-unresolved-raises/None for
  S-items and unclassified).
- `tests/test_vision_detectors.py`: F05's `GEOMETRY_SUB_PATTERN` wiring
  (carries from caller, defaults to `None`, request carries the spec
  object), the "only F05/F06 request a sub_pattern" parametrized guard
  (renamed from F06-only), `_tool_schema` enum-constrained property for
  `geometry`, and the two genuine recorded-fixture replay tests.
- `tests/test_cli_analyze.py` / `tests/test_cli_analyze_batch.py`:
  `DetectorRun.fixability` for detected/clean/stub/error/S-item/conditional-
  resolved/conditional-unresolved-disclosed cases, plus `render_report`
  assertions that the `(fixability: ...)` suffix actually lands in the
  rendered body (both the per-frame sweep path and F03's batch-level merge
  path).

Full suite run directly (`uv run pytest -q`): **317 collected, 316 passed,
1 failed** (`test_every_id_has_detector_and_named_test`,
`missing_test = ['F14']` — pre-existing, untouched by this session,
documented end state per D-007; QUEUE.md item 19(d) is the still-open
follow-up to mark it `xfail`, not this session's scope).

## DECISIONS.md
No new entry. D-009's ruling text was specific enough (Fixability values
per item, the `SubPatternSpec` mechanism named explicitly for F05, the
byte-identical requirement spelled out) to execute without a fresh
question — the one design gap found (`resolve_finding_fixability`'s strict
raise vs. CLI-layer non-fatal handling) was a straightforward "log it,
move on" application of CLAUDE.md's existing spending rule, not a genuine
open question about the taxonomy or the ruling. Open count unchanged: 0.

## What's open
- QUEUE.md item 19, the hygiene sweep — untouched this session except
  incidentally: 19(b) (splitting `record_vision_fixtures.py` per-ID) is
  now partially addressed by this session's `--only` filter, but the
  fuller split QUEUE.md describes is still not done. 19(a), (c), (d)
  untouched.
- `test_every_id_has_detector_and_named_test` still hard-fails on F14 —
  item 19(d)'s `xfail(strict=True, ...)` marker is still not implemented
  in code.

## Files touched
`src/picstory/schema.py`, `src/picstory/detectors/f05.py`,
`scripts/analyze.py`, `scripts/analyze_batch.py`,
`scripts/record_vision_fixtures.py`, `tests/test_schema.py`,
`tests/test_vision_detectors.py`, `tests/test_cli_analyze.py`,
`tests/test_cli_analyze_batch.py`,
`tests/fixtures/vision/f05_bowing_ceiling.json` (new),
`tests/fixtures/vision/f05_off_center_drift_ceiling.json` (new),
`logs/builder-019.md` (this file).
