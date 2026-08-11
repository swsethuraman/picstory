# builder-009 — 2026-08-11

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 8/20 builder sessions used
  (this session is the 9th), hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-002, covers builder-003–006, predates
  builder-007/008's items 7-8). Its two open notes (F09's center-third
  proxy, `r01.py`'s stale QUEUE-item-3 citation) are for whoever next
  touches those specific files; neither is item 9, so neither blocked this
  session.
- `DECISIONS.md`: open count 0 at session start (D-001–D-006 all `RULED`).
  No new entry added this session.
- Most recent `logs/` entry: `builder-008.md` (item 8: F03 near-duplicate
  grouping).
- Branch: the designated branch's prior PR (#10, builder-008's item-8 work)
  was already merged to `main` and the remote branch deleted. Per the
  session's branch-restart instructions, recreated
  `claude/brave-clarke-57ny9m` from `origin/main` (fast-forward, no rebase
  needed — the branch's own history was already fully in `main`) rather
  than stacking on top of already-merged commits.

## What moved
QUEUE.md Stage 1 (items 1–6) and Stage 2 items 7-8 were already done. Item 9
is next and unblocked: "Ranking + shortlist: the pick, then share-list
one-liners drawn from S-item vocabulary; F-findings as disqualifiers."

TAXONOMY.md's own output-mapping table ("The pick (and the share list) |
Strengths (S-items) as the 'why it's share-worthy' one-liners; failure modes
as disqualifiers") is the entire spec here — there is no separate scoring
rubric to invent, only that sentence to implement literally.

1. **`src/picstory/schema.py`**: added `taxonomy_reinforcement_text(id)`,
   mirroring the existing `taxonomy_detection_text(id)` — parses each
   S-item's `- **Reinforcement:**` bullet verbatim from the frozen
   TAXONOMY.md (same single-source-of-truth reasoning CLAUDE.md's
   API-discipline rule already applies to Detection text: the share-list
   one-liners must be "drawn from S-item vocabulary," not a paraphrase that
   could drift). F/R items have no Reinforcement bullet and raise
   `SchemaError`.

2. **`src/picstory/ranking.py`** (new): `score_frame` = count(S-item
   findings) − count(F-item findings) on one `FrameAnalysis`; `rank_frames`
   sorts a batch best-first (Python's `sorted(..., reverse=True)` is stable,
   so ties keep the batch's original order — documented and tested);
   `build_pick` takes the top-ranked frame and returns a `Pick` with
   `reasons` = that frame's own S-item IDs and `disqualifiers` = that
   frame's own F-item IDs; `share_list_lines` pairs each reason with its
   verbatim Reinforcement text.

   One reading call worth flagging explicitly: `Pick.disqualifiers` names
   the *picked* frame's own remaining F-item findings, not the F-items that
   ranked other frames lower. `schema.py`'s `Pick` dataclass (item 1,
   CRITIC-cleared in critic-002) ties `disqualifiers` to a single
   `frame_id`, which reads most literally as "what's still wrong with this
   frame" — and disclosing a winner's remaining flaws rather than
   laundering them matches the disclosure standard already set elsewhere
   (F09's center-third proxy note, F03's dHash-proxy note, R01's stale-cite
   flag in REVIEW.md). Documented at length in `ranking.py`'s module
   docstring so CRITIC can check the reading against TAXONOMY.md directly
   rather than trusting this summary.

   R01 findings can't occur per-frame in practice (batch/conditional
   trigger, not a `Finding.taxonomy_id` any detector emits — see
   `scripts/analyze.py`), and `unclassified` findings carry no polarity;
   both are excluded from scoring rather than guessed at.

   No new `AnalysisOutput` schema field for "the shortlist" itself —
   `Pick` has existed, unpopulated, on the schema since item 1, so item 9's
   job is computing it, not adding surface. The full ranked order
   (PREDICTION.md's "ranked shortlist") is exposed via `rank_frames` and
   rendered in the CLI report instead of persisted on the output.

3. **`scripts/analyze_batch.py`**: `run_batch_analysis` now calls
   `ranking.build_pick` on the batch's final per-frame findings — after the
   per-frame sweep *and* F03's merge, so a safety-copy finding counts
   against its frame's score exactly like any other F-item (tested
   directly). `render_report` gained a "## Shortlist" section (ranked
   frame_ids with scores) and a "## Pick" section (frame_id, disqualifiers,
   share-list one-liners); `habit: None` note kept as-is since item 10 is
   still untouched.

4. **Tests**: `tests/test_ranking.py` (new, 12 tests) exercises
   `score_frame`/`rank_frames`/`build_pick`/`share_list_lines` directly —
   S-for/F-against scoring, unclassified/R01 exclusion, tie-order
   stability, empty-batch `None`, the winner's-own-disqualifiers reading,
   dedup, and verbatim Reinforcement text (not a paraphrase — asserted
   against `taxonomy_reinforcement_text` directly, same pattern
   `test_vision_detectors.py` uses for Detection text). `tests/test_schema.py`
   gained 3 tests for `taxonomy_reinforcement_text` (hand-transcribed
   verbatim check against two S-items, F/R-item `SchemaError`, distinctness
   from Detection text). `tests/test_cli_analyze_batch.py`: updated the old
   "pick and habit both stay None" test (now habit-only, since pick is
   computed) and added three new tests for the batch-level wiring (highest-
   scorer wins, F03's merge counts toward the pick's own disqualifiers,
   ties keep batch order); updated `render_report`'s assertions for the new
   shortlist/pick sections.

## Test count
147 collected: 146 passed, 1 expected fail
(`test_taxonomy_coverage.py::test_every_id_has_detector_and_named_test`,
`missing_test = [F14, R01, S03]` — unchanged from builder-008, since this
session touched no detector). Full suite run directly
(`uv run pytest -q`, 194s — same vision-detector-no-network-key cost prior
sessions noted, unaffected by this session's work since ranking makes no
network calls).

## What's open
- QUEUE.md items 10–12 (session habit, CMP comparison, the profile) —
  untouched this session. Item 10 (most-recurrent F/S item across the
  batch) is next and can reuse `ranking`'s per-frame ID extraction.
- `tests/test_taxonomy_coverage.py::test_every_id_has_detector_and_named_test`
  still fails, expected: F14, R01, S03 remain undeferred/unscheduled stubs
  (D-005 for F14/S03; R01 has no scheduling decision yet).
- REVIEW.md's two outstanding notes from critic-002 (F09 center-third
  proxy, R01's stale citation) are still open for whoever next touches
  those specific files — neither was touched this session.
- The `Pick.disqualifiers`-names-the-winner's-own-flaws reading (see item 2
  above) is a design call this session made and documented, not a
  DECISIONS.md entry — it doesn't block anything, but it's the one place
  in this session's work where TAXONOMY.md's wording underdetermines the
  implementation, so it's flagged here for CRITIC to check directly against
  ranking.py's docstring and TAXONOMY.md's output-mapping table.
- DECISIONS.md open count: 0. No entry opened or closed this session.
