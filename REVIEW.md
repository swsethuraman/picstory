# REVIEW — critic-004, 2026-08-12

Scope: diff from `f0f11f0` (critic-003) through `db37fe8` (HEAD) — builder-011
(CMP, `b9f6769`), builder-012 (the profile, `fa421af`), builder-013 (R01,
`0eb442f`), builder-014 (S03, `c2d7d24`), builder-015 (no code changes). All
of QUEUE.md Stage 3 (item 11), Stage 4 (item 12), and the two agent-proposed
items (13, 14).

Per CLAUDE.md's CRITIC instruction: for each taxonomy ID / output row, does
the implementation match the actual described behavior, or a plausible
substitute?

## Headline finding

**No plausible-substitute pattern found in this diff.** Four output rows
landed (CMP, the profile, R01, S03) and all four were checked line-by-line
against their TAXONOMY.md text; each is a real, disclosed implementation of
what its text actually says, not an easier stand-in.

## CMP · Three-frame comparison rubric

| Item | Verdict |
|---|---|
| CMP | Matches. `cmp.py`'s prompt embeds `schema.cmp_rubric_text()` — the whole §CMP section, parsed verbatim, not paraphrased — satisfying the API-discipline rule's "embeds the item's Detection text verbatim" for a section that (correctly noted in the module docstring) has no single `- **Detection:**` bullet to extract instead. The tool schema's three axes (`subject_placement`, `edge_amputations`, `incidental_distractions`) are exactly TAXONOMY.md's three named axes, in the same order, all required; `tiebreaker` is optional and separately worded to fire "only if the axes alone do not settle it," matching §CMP's own tiebreaker framing. `winning_frame_id` is a JSON Schema `enum` of the actual frame IDs sent — the model is structurally prevented from naming a frame outside the group, not just asked nicely to. `schema.Comparison` deliberately carries no F/S taxonomy ID field, matching the output-mapping table's "The CMP rubric, exclusively." |

Verified against the one genuine recorded fixture
(`tests/fixtures/cmp/wide_vs_tight_with_walker.json`): the live model's
`winning_frame_id` is `"tight"` and its `tiebreaker` text names the added
walker figure as the deciding story element — an actual exercise of §CMP's
tiebreaker clause by a real call, not a hand-picked value asserting the
rubric works. `tests/test_cmp.py` replays this fixture through
`parse_tool_use_response` (`test_parse_tool_use_response_replays_genuine_recorded_api_call`)
and separately asserts the prompt contains `cmp_rubric_text()` verbatim.

One thing worth naming for whoever next runs this against a real large
batch, carried forward from builder-011's own worklog rather than
independently found here: `compare_group` sends a near-duplicate group's
*entire* run in one call, uncapped — F03's own docstring says its runs
aren't capped at 5 despite TAXONOMY.md's "2-5" examples being descriptive
only. Not exercised in this diff (no large synthetic run was pushed through
`main()`), not a taxonomy-match defect, just an unexercised edge.

## The running profile

| Item | Verdict |
|---|---|
| Running profile | Matches. TAXONOMY.md's output-mapping table: "Per-user recurrence of F/S items and their sub-patterns (e.g. *which* edge the user neglects)." `profile.py`'s `IdRecurrence`/`record_session` implement exactly this — per-ID session/frame counts, `sub_patterns` tallied only for IDs `schema.taxonomy_ids_with_subpattern()` names (today `{"F06"}`, parsed from F06's own "Profile note" bullet, not hardcoded). R01 and `unclassified` correctly excluded, same reasoning `ranking.py` already applies. |
| F06 sub-pattern | Matches, and matches well. The `edge` value is asked for **inside the same structured tool call** as F06's detected/rationale verdict (`_vision.SubPatternSpec`, enum-constrained to `left/right/top/bottom/multiple`), not regex-scraped out of free-text rationale afterward. That second approach is exactly the kind of plausible substitute PREDICTION.md would flag and CLAUDE.md's API-discipline rule exists to prevent, and it was avoided. The enum vocabulary itself reads directly off F06's own text (`right-third`/`left-edge` named in the Profile note; "sweep all four edges" in Correction motivating top/bottom; `multiple` for the genuine multi-edge case) — not invented. `Finding.__post_init__` enforces that only IDs with a documented Profile note may carry a `sub_pattern` at all, so this can't silently spread to other IDs without a TAXONOMY.md amendment. |

Verified two genuine recorded fixtures
(`f06_landmark_alone.json`: `detected=false`;
`f06_edge_intrusion_right.json`: `detected=true, edge="right"`) replay
correctly through `parse_tool_use_response` with `EDGE_SUB_PATTERN` wired
in — the live model's own verdict, not an asserted one. The other eight
judgment-dependent detectors' fixtures remain hand-authored (per D-006, a
prior sandboxed session had no key); this diff is honest about that split
in `test_vision_detectors.py`'s own module docstring rather than presenting
the F06/CMP recordings as if they covered everything.

builder-012's worklog flagged its own read of "recurrence" (one `sessions`
increment per ID per batch run, regardless of how many frames carry it) as
worth CRITIC checking. TAXONOMY.md's output-mapping table doesn't define
"recurrence" more precisely than the phrase itself, and this reading is the
direct cross-session extension of `ranking.compute_habit`'s existing
within-session reading — consistent, not a new interpretation invented for
convenience. No objection.

## R01 · Haze rule

| Item | Verdict |
|---|---|
| R01 | Matches. §R's Trigger text ("Hazy / low-contrast conditions (detected via F12 findings in the batch)") is checked exactly as written — `any(finding.taxonomy_id == "F12" ...)` over the batch's already-computed findings, nothing re-derived from pixels. `Rule` is correctly a distinct dataclass from `Finding`, matching §R's explicit "different object type for the classifier" framing, and fires once per batch (forward-looking session advice), not once per triggering frame. `advice` is `schema.taxonomy_rule_text("R01")` — the Rule bullet parsed verbatim, same single-source-of-truth pattern as Detection/Correction/Reinforcement text elsewhere. |

`r01.py`'s previously-flagged stale citation ("real detection logic ...
lands in QUEUE.md item 3", open since critic-002) is gone — the whole
module was replaced by this diff, confirmed by reading the file directly.
Closing that note.

## S03 · Tight framing

| Item | Verdict |
|---|---|
| S03 | Matches D-007's ruling, which is the operative spec here (D-007 modified TAXONOMY.md's own "batch-mates" reading into a scoped, implementable form; this diff is checked against that ruling's text, not re-litigated). |

D-007's ruling named two required properties for the grouping and both are
met, checked directly in `subject_clusters.py`:
- **Looser threshold than F03's.** `HASH_DISTANCE_THRESHOLD = 15` vs. F03's
  `6` — confirmed by reading `f03.py`'s own constant, not taken on faith
  from the docstring's claim.
- **No focal-length/timestamp gate.** `group_subject_clusters` computes
  pairwise Hamming distance from `difference_hash` alone; no EXIF field is
  read anywhere in the module. F03's `group_near_duplicates`, by contrast,
  does gate on both — confirmed by reading both functions side by side.
- **Non-adjacent frames can cluster.** The function compares every pair
  (`for i in range(n): for j in range(i+1, n)`), not just consecutive
  frames — genuinely different from F03's adjacency-only scan, which is the
  distinction D-007's ruling required ("batch-mates" isn't an adjacency
  relationship the way a burst is).

`s03.py`'s `_framing_tightness` (via `_imaging.sharp_area_fraction`, new
this diff) is a disclosed proxy for "tightest frame of a subject" — no
subject/face segmentation exists locally, so it leans on sharp-area share
as a stand-in, the same disclosure standard already accepted for F09's
center-third proxy in critic-002 and F03's dHash-as-pose proxy in
critic-003. Not a hidden substitute: the module docstring states the
proxy and its rationale plainly, and `_imaging.py`'s own docstring names
where it breaks down (subject nearly filling the frame, no flat-background
baseline left).

One transitivity caveat is disclosed in `subject_clusters.py`'s own
docstring (any-pair union-find chaining could pull an unrelated frame into
a cluster through an intermediate one) — the same class of caveat
critic-003 flagged for F03's pairwise-consecutive version, one layer more
exposed here since non-adjacency widens the chaining surface. Correctly
self-flagged rather than left implicit; nothing in this session's own test
fixture triggers it, and it's a tuning note, not a substitute-detection
finding.

## Testing infrastructure: the live-call leak (worth flagging, not a taxonomy defect, but real)

builder-011 discovered that every `uv run pytest` since at least builder-007
had been silently making live, spend-cap-metered calls to
`api.anthropic.com` through `main()`'s end-to-end smoke tests, because this
sandbox's `PICSTORY_VISION_KEY` actually works (unlike the no-key sandbox
D-006 diagnosed) and those specific tests deliberately exercise the real,
unfaked detector registry. This is a genuine violation of CLAUDE.md's
explicit rule ("the test suite must run offline ... tests never make live
calls") that predates this diff and went unnoticed by builder-007 through
critic-003 — the ~180–200s per-run cost every one of those sessions
reported and none diagnosed was this. No prior CRITIC session flagged it
(checked all three prior REVIEW.mds for "offline"/"live"/"network" — no
hits); this diff is the first to catch it.

The fix (`tests/conftest.py`'s `_block_live_anthropic_calls`, autouse,
session-wide) is correct and verified directly this session: ran the full
suite with this sandbox's own working `PICSTORY_VISION_KEY` still set in
the environment (confirmed present via `env`) and got 265 passed / 1
expected fail in 3.4s — no network I/O, no 401 round-trip delay, consistent
with the fixture patching `anthropic.Anthropic` itself rather than merely
unsetting a key. The one open design question builder-011's own worklog
raised (global client-patch backstop vs. per-test fake-injection
discipline) is a testing-infrastructure judgment call, not a
taxonomy question — the backstop is safer given the discovered real-spend
cost of leaving it to per-test discipline, and it demonstrably does not
interfere with the two tests that need the real `default_caller()` code
path (they re-patch locally, verified by reading `test_vision_detectors.py`
directly). No objection to the fix; flagging here only because it is a real
finding about the diff, not a new one being raised.

## DECISIONS.md

Not adding an entry this session. Open count unchanged at 0 (D-001–D-007
all `RULED`). D-007's split ruling (S03 implemented per its modified-(a),
F14 stands stubbed per its (c)) is followed exactly as written in this
diff — checked directly against the ruling text above, not assumed.

## Still open from critic-002/critic-003, untouched by this diff

- F09's center-third subject proxy (`src/picstory/detectors/f09.py`) —
  still not touched. Continues to be an accepted, disclosed proxy (same
  standard applied to F03/S03 above), not a new finding.

## Resolved by this diff

- R01's stale QUEUE-item-3 citation (open since critic-002, carried through
  critic-003) — gone, confirmed above.

## Test suite

266 collected: 265 passed, 1 expected fail
(`test_every_id_has_detector_and_named_test`, `missing_test = [F14]` — the
documented, intended end state of this guard per D-007's ruling, not an
open gap). Verified by running the suite directly this session
(`uv run pytest -q`, 3.4s, this sandbox's own `PICSTORY_VISION_KEY` present
in the environment throughout — the fast, clean run is itself evidence
`tests/conftest.py`'s live-call block above is working, not just claimed).
