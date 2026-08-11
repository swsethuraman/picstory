# builder-010 — 2026-08-11

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 9/20 builder sessions used
  (this session is the 10th), hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-002, covers builder-003–006). Its two open
  notes (F09's center-third proxy, `r01.py`'s stale QUEUE-item-3 citation)
  are for whoever next touches those specific files; neither is item 10, so
  neither blocked this session.
- `DECISIONS.md`: open count 0 at session start (D-001–D-006 all `RULED`).
  No new entry added this session.
- Most recent `logs/` entry: `builder-009.md` (item 9: ranking + shortlist).
- Branch: the designated branch `claude/brave-clarke-5x936h` did not exist
  on the remote (builder-009's branch/PR #12 was already merged to `main`
  and its remote branch deleted, same situation builder-009 itself
  documented for its predecessor). Per the session's branch-restart
  instructions, created `claude/brave-clarke-5x936h` fresh from
  `origin/main` (`0be95c5`, PR #12's merge commit) rather than stacking on
  already-merged history. Note: my first `git fetch origin main
  claude/brave-clarke-5x936h` failed *atomically* (whole fetch aborted,
  including `main`) because the branch ref didn't exist yet — worth knowing
  for future sessions: fetch `main` in its own call, not bundled with a
  possibly-nonexistent designated branch.

## What moved
QUEUE.md Stage 1 (items 1–6) and Stage 2 items 7–9 were already done. Item
10 is next and unblocked: "Session habit: most-recurrent F/S item across the
batch."

TAXONOMY.md's own output-mapping table is the spec: "Whichever F- or S-item
recurs most in the batch; reinforcement counts as coaching." `schema.Habit`
(taxonomy_id + description) has existed, unpopulated, since item 1.

1. **`src/picstory/schema.py`**: added `taxonomy_correction_text(id)`,
   mirroring `taxonomy_detection_text`/`taxonomy_reinforcement_text` —
   parses each F-item's `- **Correction:**` bullet verbatim from the frozen
   TAXONOMY.md. Needed because the output-mapping table's "reinforcement
   counts as coaching" line only states the S-item half explicitly; the
   symmetric read is that Correction is F-items' equivalent coaching text
   (S-items have Reinforcement, F-items have Correction — TAXONOMY.md's own
   field structure, confirmed by inspection of every F01–F15 and S01–S04
   entry). Raises `SchemaError` for S/R items, same pattern as the existing
   two text-lookup functions.

2. **`src/picstory/ranking.py`**: added `compute_habit(frame_analyses)` —
   counts, per taxonomy ID, how many distinct frames in the batch carry that
   ID (reusing the existing `_ids_with_prefix` helper, so a frame
   structurally can't inflate one ID's count past 1); R01 (never a
   per-frame `Finding`) and `unclassified` (no polarity, no coaching text in
   TAXONOMY.md) are excluded — same exclusion `score_frame` already applies.
   The winning ID's `Habit.description` is its Correction text if it's an
   F-item, its Reinforcement text if S — both read verbatim via `schema.py`,
   same verbatim-source-of-truth reasoning `share_list_lines` already uses.
   Ties break by ascending taxonomy ID: TAXONOMY.md doesn't specify a
   tie-break and a genuine count-tie is possible, so this session made that
   choice explicit and documented (`max(sorted(counts), key=counts.get)`)
   rather than leaving it to dict/insertion order. `None` for a batch with
   no F/S finding anywhere.

3. **`scripts/analyze_batch.py`**: `run_batch_analysis` now also calls
   `ranking.compute_habit` on the batch's final per-frame findings (after
   the per-frame sweep *and* F03's merge — tested directly, so an F03 safety
   -copy finding can win the habit the same way it already counts toward a
   frame's pick-score). `render_report`'s "habit: None - not computed by
   this queue item" placeholder line is replaced with the real
   `taxonomy_id — description` (or an explicit "nothing recurred" message
   for `None`).

4. **Tests**: `tests/test_schema.py` gained 3 tests for
   `taxonomy_correction_text` (hand-transcribed verbatim check against F01
   and F06, S/R-item `SchemaError`, distinctness from Detection text).
   `tests/test_ranking.py` gained 7 tests for `compute_habit` (empty batch,
   nothing-recurs, F-item win with Correction text, S-item win with
   Reinforcement text, frame-count vs. raw-finding-count, the documented
   ascending-ID tie-break, unclassified/R01 exclusion).
   `tests/test_cli_analyze_batch.py`: replaced the old "habit stays None"
   test (habit is no longer unimplemented) with a habit-is-None-when-
   nothing-recurs test plus two new ones (most-recurrent F-item wins with
   Correction text; F03's batch-merged finding counts toward the habit);
   updated `render_report`'s assertion for the new habit line (the fixture
   in that test happens to put F06 on both frames, so it now genuinely
   surfaces as the habit rather than staying `None`).

## Test count
166 collected: 165 passed, 1 expected fail
(`test_taxonomy_coverage.py::test_every_id_has_detector_and_named_test`,
`missing_test = [F14, R01, S03]` — unchanged from builder-009, since this
session touched no detector; D-005 covers F14/S03, R01 has no scheduling
decision yet). Full suite run directly (`uv run pytest -q`, 194s — same
vision-detector-no-network-key cost prior sessions noted, unaffected by this
session's work since ranking/habit computation makes no network calls).

## What's open
- QUEUE.md items 11–12 (three-frame comparison, the profile) — untouched
  this session. Item 11 (CMP rubric over near-duplicate groups) is next.
- `tests/test_taxonomy_coverage.py::test_every_id_has_detector_and_named_test`
  still fails, expected: F14, R01, S03 remain undeferred/unscheduled stubs
  (D-005 for F14/S03; R01 has no scheduling decision yet — REVIEW.md's
  critic-002 flagged `r01.py`'s stale citation but that's a comment fix, not
  a scheduling ruling).
- REVIEW.md's two outstanding notes from critic-002 (F09 center-third proxy,
  R01's stale citation) are still open for whoever next touches those
  specific files — neither was touched this session.
- The Correction-vs-Reinforcement coaching-text split for `compute_habit`
  and its ascending-ID tie-break (see item 2 above) are design calls this
  session made and documented in `ranking.py`'s docstring — not
  DECISIONS.md entries, since neither is a taxonomy-unimplementability
  question, but flagged here for CRITIC to check the reading directly
  against TAXONOMY.md's output-mapping table and field structure.
- DECISIONS.md open count: 0. No entry opened or closed this session.
