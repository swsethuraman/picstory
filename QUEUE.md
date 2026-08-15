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

## Stage 5 — phase 2: real-photo hardening (owner-added, 15 Aug 2026)

*Context for these items: the experiment's capstone run (docs/capstone-vienna-report.md, PICSTORY_SCORECARD.md §4) analyzed 31 real iPhone photos and surfaced findings no synthetic fixture could. D-008a/b/c and D-009 carry the rulings these items implement. The autonomous phase's rules (CLAUDE.md) remain in force unchanged.*

15. **The resolution contract.** The pipeline currently processes and uploads frames at native resolution — no downsampling exists anywhere between `load_frame` and the API payload or the hash path. On real 48MP iPhone frames this made the capstone run effectively non-terminating (multi-MB payloads per vision call ×~280 calls; uncached full-resolution luminance rebuilt for every hash comparison) and was invisible to all 266 tests because every fixture is ≤200px. Implement: (a) `load_frame`/`load_batch` decode, read EXIF from the *original* file, then immediately downsample to a working resolution (~2000px long edge), documented in `frame.py` as a contract downstream code may rely on; (b) `Frame.luminance` cached; perceptual hashes memoized per frame (F03, subject clusters, and CMP's re-grouping currently rehash the same frames repeatedly); (c) `_vision._encode_jpeg` independently enforces its own payload ceiling (resize-if-needed ~1500px, quality ~85, hard byte cap) — defense in depth, not a substitute for (a); (d) `Frame` retains `path`, and the docstring documents the lazy full-resolution-crop escape hatch: a detector with a demonstrated need may load a native-res crop of a specific region, need documented per-detector, default is working-res only; (e) regression tests at realistic scale: a synthetic 8000×6000 frame asserts working-res ingestion, and a timing-bounded 5-frame end-to-end (offline, per conftest's live-call block) that would have caught this; (f) F01's sharpness threshold recalibrated at working res, docstring noting the calibration is resolution-specific — and any other detector whose fidelity changes at working res states it in its docstring (same disclosure standard as F09's proxy). If a detector genuinely cannot work at working res, that is a DECISIONS.md entry, not a silent regression.

16. **Keeper election per D-008a.** `run_batch_analysis` reordered: CMP judges each near-duplicate run *before* F03 Findings merge; CMP's winner is the keeper; the losing frames get the safety-copy Finding naming the elected keeper. When CMP cannot rule on a run (vision-call error, spend cap, any failure), the first-frame convention applies as the disclosed fallback and the Finding's description says so. Tests cover both paths, including a CMP-overturns-position-1 case per the capstone evidence. Full requirements in D-008a's ruling — implement against that text.

17. **Habit and ranking calibration per D-008c and D-008b.** (a) Habit selector: batch-pervasiveness exclusion — an ID firing on more than 2/3 of the batch's frames (named, documented constant) is pervasive and sits out habit selection; habit is the most recurrent non-pervasive F/S ID, existing tie-break unchanged; pervasive findings surface as a single one-line session note in the report, distinct from the habit. Calibration fixture: on the capstone batch's finding pattern, F05/F06/F11 must classify pervasive and F08 must win the habit (build the fixture from docs/capstone-vienna-report.md's counts — synthetic findings, no API calls). (b) Ranking: at equal `count(S) − count(F)`, higher `count(S)` ranks first; batch order remains the final documented tie-breaker; regression test encodes the capstone tie (a frame with one S and one F must outrank a findings-free frame at equal score — 0967 over 0969). Full reasoning in D-008c and D-008b — implement against those texts.

18. `[blocked: owner's TAXONOMY.md v1.2 commit]` **Fixability parsing per D-009.** After the owner commits TAXONOMY.md v1.2 (adds `- **Fixability:**` bullets; changes no existing text — the amendment is owner work, and TAXONOMY.md remains agent-read-only): (a) `schema.taxonomy_fixability(id)` parsing the new bullet verbatim, same single-source pattern as the other text helpers; (b) a guard test asserting every previously-parsed text (Detection, Correction, Reinforcement, Rule, Profile-note, CMP rubric) is byte-identical across the version bump; (c) F05's `conditional` fixability wired via the existing `SubPatternSpec` mechanism — closed-vocabulary sub-pattern (`bowing` / `off_center_drift`) in the same structured call, exactly as F06 does for edges — with a recorded fixture if a live call is feasible, hand-authored shape disclosed otherwise per D-006's precedent; (d) the Finding-level fixability surfaced in `analyze_batch`'s report (one word per finding), so the Check surface has its input when it arrives. Where a Fixability bullet is missing or ambiguous for an item, that is a question logged to DECISIONS.md, not a guess.

19. **Small hygiene sweep** (one session, alongside whichever item above leaves room, or alone): (a) `f14.py`'s stub message still cites "QUEUE.md item 4" — should cite D-007's ruling as the reason it stands; (b) `scripts/record_vision_fixtures.py` split per-ID so recording new fixtures doesn't re-spend on the whole call list (builder-012's own disclosed suggestion); (c) the F02 false-positive class from the capstone (a stone arch shot *through*, read as a grip obstruction — frame 30_IMG_0981) noted in `f02.py`'s docstring as a known limitation of the dark+flat edge heuristic, with the capstone frame's description as the example; not a threshold change without evidence, a disclosure; (d) mark `test_every_id_has_detector_and_named_test` as `xfail(strict=True, reason="F14 stubbed per D-007")` per builder-017's note — the guard's red is the documented, intended end state, and the suite's summary line should say so rather than report it as a failure; `strict=True` so an eventual F14 implementation forces the marker's conscious removal.
