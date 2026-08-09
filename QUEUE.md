# QUEUE

BUILDER works top-down, one item per commit where feasible. Items marked `[blocked: D-nnn]` may not start until that decision carries a human ruling — log and skip. Agent additions go at the bottom, flagged `[agent-proposed]`. **Never reorder.**

---

## Stage 1 — the loop, one photo

1. Define the analysis output schema in `src/picstory/schema.py` + `schema/analysis.json`: per-frame findings, each carrying a taxonomy ID **or** `unclassified` + free-text description (TAXONOMY.md §U); the pick; one habit with its taxonomy ID. Version field from day one.
2. Detector registry in `src/picstory/detectors/`: one module per taxonomy ID (F01–F15, S01–S04, R01), registered by ID. Stubs may exist structurally but a stub returning nothing is not an implementation — see item 4 and the coverage/critic guards.
3. Implement the metadata- and pixel-computable detectors locally first: F01 (EXIF focal length vs. optical steps + sharpness), F09/F10 (exposure histogram, face-region vs. background), F02 (dark defocused edge mass), F12 (global contrast), F07 (featureless-region area share), F08 (vertical-line convergence). Local heuristics are preferred wherever they honestly implement the item — cheaper, deterministic, testable offline.
4. Implement the judgment-dependent detectors (F04, F05, F06, F11, F13, F14, F15, S01–S04) as Anthropic API vision calls per the API-discipline rule in CLAUDE.md: prompt embeds the item's Detection text verbatim, structured output by taxonomy ID, responses recorded as test fixtures. A generic "critique this photo" prompt is the substitute PREDICTION.md names — the CRITIC checks for exactly this. If an item still cannot be implemented honestly, that is a DECISIONS.md entry.
5. CLI `scripts/analyze.py`: one photo in → full analysis written to `outputs/reports/` via `_report.py`, three-line stdout. The habit = the highest-priority finding by taxonomy recurrence rules.
6. Per-detector tests in `tests/`, each named for its ID (`test_f01_…`): synthetic/fixture images for local detectors, recorded API responses for model-call detectors. The suite runs offline. Coverage test green means: every ID has a detector and a named test.

## Stage 2 — batching and the shortlist

7. Batch input (5–50 photos); per-frame analysis reusing Stage 1.
8. F03 near-duplicate grouping (perceptual hash + EXIF timestamps/focal length deltas).
9. Ranking + shortlist: the pick, then share-list one-liners drawn from S-item vocabulary; F-findings as disqualifiers.
10. Session habit: most-recurrent F/S item across the batch.

## Stage 3 — three-frame comparison

11. CMP rubric implementation over near-duplicate groups: the three axes + story tiebreaker, exactly as TAXONOMY.md §CMP. Output names the winner and states per-axis differences.

## Stage 4 — the profile

12. `[blocked: D-004]` Per-user recurrence store across sessions, with sub-pattern detail (e.g. which edge for F06).

---

*Agent-proposed additions below this line, flagged `[agent-proposed]`.*
