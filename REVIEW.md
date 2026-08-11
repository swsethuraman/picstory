# REVIEW — critic-003, 2026-08-11

Scope: diff from `58aec58` (critic-002, HEAD at the time `1a78643`) through
`7136ac1` (HEAD now) — builder-007 (batch input, `564c191`), builder-008 (F03
near-duplicate grouping, `2fb84bf`), builder-009 (ranking + shortlist,
`a0f6f75`), and builder-010 (session habit, `09e8392`). QUEUE.md Stage 2 in
full (items 7–10).

Per CLAUDE.md's CRITIC instruction: for each taxonomy ID, does the detector
implement the actual described failure, or a plausible substitute?

## Headline finding

**No plausible-substitute pattern found.** This diff lands one real
taxonomy-ID detector (F03) plus the output-assembly logic (ranking, pick,
share list, habit) that TAXONOMY.md's own output-mapping table specifies.
Checked line-by-line against that table and against F03's Detection text.

## F03 · Safety copies

| ID | Kind | Verdict |
|---|---|---|
| F03 | batch-level (local) | Matches, with one disclosed proxy limitation. Detection text: "2-5 consecutive frames of the same subject with no change in position, focal length, or angle." The implementation checks all three named signals independently — EXIF `FocalLength` for the literal metadata clause, EXIF timestamp closeness for "consecutive," and a whole-frame difference-hash for "no change in position or angle." The hash is a disclosed proxy (no camera-pose data exists to check position/angle directly), same disclosure pattern already accepted for F09's center-third subject proxy — not a hidden substitute. `group_near_duplicates`'s threshold (6/64 bits) is empirically grounded in the module's own comment and exercised by `tests/test_f03_safety_copies.py`'s discriminating cases: identical frames score 0, sigma-8-noise frames score ~2, a subject moved 10% of frame width scores 8. Tests assert the actual discriminating cases (moved-subject frame breaking a run, focal-length change breaking a run, missing EXIF *not* blocking a match, timestamp gap breaking a run) rather than only the happy path. The "2-5" ceiling is correctly read as descriptive (TAXONOMY.md's own examples give "x3," "x5") rather than a hard cap, consistent with critic-002's precedent for F02's "typically." |

One minor, non-blocking proxy caveat worth naming for whoever next tunes
F03: the difference-hash check is pairwise-consecutive (frame *i* vs. frame
*i+1*), so a slow pan across many frames — each adjacent pair within
threshold, but frame 1 clearly different from frame 5 — could chain into one
over-long "run" the way transitive-similarity chaining always can. Nothing
in the source material (travel bursts of a static subject) obviously
triggers this, and it's the same class of disclosed-proxy limitation as
F09's center-third approximation — flagging for awareness, not as an
undisclosed substitute.

## Ranking, pick, share list, habit (TAXONOMY.md's output-mapping table)

This is not a per-ID detector, but CLAUDE.md's "design constraint that
governs everything" makes the output-mapping table itself something CRITIC
should check the implementation against — and builder-009/builder-010 both
explicitly flagged one reading in their worklogs for CRITIC to verify
rather than asserting it settled themselves.

- **`Pick.disqualifiers` names the winner's own remaining F-items, not an
  exclusion filter.** Verified against `schema.py`'s `Pick` dataclass
  (Stage 1, already CRITIC-cleared in critic-001/002): its docstring reads
  "F-item disqualifiers **weighed**" — not "excluded" or "eliminated." A
  frame can win the pick with F-item findings still attached, disclosed
  rather than hidden. `ranking.score_frame`'s `count(S) - count(F)` formula
  is the literal arithmetic reading of TAXONOMY.md's own sentence
  ("Strengths... as the... one-liners; failure modes as disqualifiers") —
  there is genuinely no separate scoring rubric elsewhere in TAXONOMY.md to
  implement instead. This reading is consistent with the pre-existing
  schema, not a new interpretation invented to dodge the taxonomy's intent.
  Verdict: matches, on the only textually-grounded reading available.
- **Share-list one-liners** are each S-item ID paired with its
  Reinforcement text, parsed verbatim from TAXONOMY.md via the new
  `schema.taxonomy_reinforcement_text` (mirrors `taxonomy_detection_text`'s
  established verbatim-source pattern). `tests/test_schema.py` checks two
  S-items' Reinforcement text against hand-transcribed strings from
  TAXONOMY.md directly (verified by reading TAXONOMY.md myself: S01 and S04
  match exactly) — not a paraphrase that could drift.
- **The habit** (`ranking.compute_habit`) is "whichever F- or S-item recurs
  most in the batch," counted per distinct frame carrying the ID, with an
  explicit, tested, documented ascending-ID tie-break TAXONOMY.md itself
  doesn't specify. Its coaching text is Correction (new
  `schema.taxonomy_correction_text`, F-items) or Reinforcement (S-items) —
  the symmetric read of the output-mapping table's "reinforcement counts as
  coaching" line. Verified F01 and F06 Correction text against TAXONOMY.md
  directly; both match verbatim. R01 and `unclassified` are correctly
  excluded (neither has a polarity or coaching text in TAXONOMY.md).

No vocabulary violation anywhere in this diff: every disqualifier, reason,
and habit is a taxonomy ID or its verbatim TAXONOMY.md text, never invented
language.

## Worth flagging, not a taxonomy-match defect

**builder-010's worklog reports the wrong test count.** Its "Test count"
section states "166 collected: 165 passed, 1 expected fail." Running the
suite directly against HEAD (`uv run pytest -q`, no code differs between
`09e8392` and HEAD's merge commit) collects **159** tests: 158 passed, 1
expected fail (`test_every_id_has_detector_and_named_test`,
`missing_test = [F14, R01, S03]` — same as every session since builder-008,
correctly still open). The actual number reconciles cleanly with the diff
(147 after builder-009 + 12 new test functions in builder-010's own commit
= 159); the suite itself is intact and nothing is missing or silently
dropped. This looks like a plain transcription error in the worklog rather
than any code or coverage problem, but CLAUDE.md requires every worklog to
state "test count" and a wrong number undermines the one artifact future
sessions use to sanity-check "did the suite grow the way this session
claims" without re-running it themselves. Flagging so the next BUILDER
session double-checks its own reported count against a direct run before
committing the worklog.

## DECISIONS.md

Not adding an entry this session. Open count unchanged at 0 (D-001–D-006
all `RULED`). Nothing in this diff rises to "unimplementable item" — the
F03 chain-transitivity note and the test-count discrepancy above are both
disclosed/inspectable, not blocking ambiguities needing a human ruling.

## Still open from critic-002, untouched by this diff

- F09's center-third subject proxy (`src/picstory/detectors/f09.py`) —
  still not touched.
- `src/picstory/detectors/r01.py`'s stale citation ("real detection logic
  ... lands in QUEUE.md item 3") — still wrong, still not touched. This is
  now the third consecutive REVIEW.md to carry this note forward
  untouched. Still not opening a DECISIONS.md entry (it's a one-line stale
  comment, not an ambiguity needing a ruling), but the next session that
  implements R01 should not trust this citation.

## Test suite

159 collected, 158 passed, 1 expected fail
(`test_every_id_has_detector_and_named_test`, `missing_test = [F14, R01,
S03]` — D-005 covers F14/S03; R01 has no scheduling decision yet). Verified
by running the suite directly this session (`uv run pytest -q`, ~182s —
consistent with prior sessions' reported vision-detector-no-network-call
cost), not by trusting either worklog's stated number.
