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

13. `[agent-proposed]` R01 (Haze rule): implement as a real batch-level
    conditional rule, replacing its `DetectorNotImplemented` stub. TAXONOMY.md
    §R: "Trigger: Hazy / low-contrast conditions (detected via F12 findings in
    the batch). Rule: Shoot tighter." Not a per-frame `Finding` (already
    excluded from the per-frame sweep in `scripts/analyze.py` and from
    `ranking.py`'s scoring/habit — see both modules' docstrings); needs its
    own `AnalysisOutput` object type ("different object type for the
    classifier," TAXONOMY.md §R) emitted once per batch when triggered.
    Unblocked as of builder-012 (Stage 2's batch context, item 7, has existed
    since builder-007 with nothing left gating this one). No DECISIONS.md
    entry needed — unlike F14/S03 (D-005), R01's trigger condition (F12
    present in the batch) is unambiguous from TAXONOMY.md's own text.

14. `[agent-proposed]` S03 (Tight framing): implement as a real batch-level
    detector per DECISIONS.md D-007's ruling (modified option (a), scoped
    small), replacing its `DetectorNotImplemented` stub. Two pieces: (1)
    `detectors.subject_clusters.group_subject_clusters` — a wider,
    separately-calibrated perceptual-similarity grouping than F03's
    near-duplicate runs (looser Hamming threshold, no focal-length/timestamp
    gate, non-adjacent pairs allowed to cluster), giving "batch-mates" its
    own honest meaning distinct from F03's "copies, not variations"; (2)
    `detectors.s03.detect`, which picks the highest framing-tightness frame
    in each cluster via a new local proxy (`_imaging.sharp_area_fraction`:
    largest contiguous in-focus tile-blob, disclosed the same way F09's
    center-third and F03's dHash-as-pose already are). Excluded from the
    per-frame sweep (`scripts/analyze.py`) and wired into the batch pipeline
    (`scripts/analyze_batch.py`) the same way F03 already is. F14 is not
    addressed here — D-007 ruled it stays stubbed for the remainder of the
    experiment (its honest precondition, location clustering, is out of
    scope). No further DECISIONS.md entry needed — D-007 already carries the
    ruling this item implements.
