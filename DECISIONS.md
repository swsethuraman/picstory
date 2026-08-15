# DECISIONS

D-nnn format, stable IDs. BUILDER writes here when blocked (question, options, recommendation, reasoning) and moves on. CRITIC may add entries and may not close them. Only the human writes rulings; rulings are appended, never rewritten. **At five open decisions, both routines halt and write HALT.md.**

Open count: 1

---

## D-001 · Where does inference run? — **RULED**
- **Question:** Cloud API or on-device/local for photo analysis?
- **Options:** (a) Cloud API. (b) Local. (c) Cloud now, local later.
- **Ruling (9 Aug 2026, setup):** Local-only by construction of the no-spend/no-network standing rule.
- **Ruling amended (9 Aug 2026, by owner, pre-launch):** Anthropic API calls are allowed, bounded by a spend cap set in the owner's Anthropic console. Judgment-dependent detectors (F04–F06, F11, F13–F15, S01–S04) may use vision model calls, subject to the API-discipline rule in CLAUDE.md: the prompt embeds the item's Detection text, output is structured by taxonomy ID, tests run offline on recorded fixtures. Computable items should still prefer local heuristics — cheaper, deterministic, testable. Cloud-vs-local for the *shipped product* (the privacy question) remains deferred to after the experiment.

## D-002 · Web or native? — **RULED (setup session)**
- **Question:** Platform for v1.
- **Options:** (a) Web. (b) iOS native.
- **Ruling (9 Aug 2026):** Neither, for the experiment. The deliverable is a local CLI/pipeline (batch in, analysis out). Packaging as web or native is a post-experiment product decision and out of scope for the autonomous phase. Re-open after scoring.

## D-003 · Does the taxonomy get shown to users? — **RULED**
- **Question:** Is the closed list a visible teaching asset or hidden machinery?
- **Options:** (a) Fully public. (b) Fully hidden. (c) Item names surface in findings ("Edge intrusion — F06"); the full list stays unpublished.
- **Recommendation:** (c). Named findings make the coaching feel diagnostic; recurring names make the profile legible. Not blocking for the experiment (output is for the owner), so left open without cost.
- **Ruling (10 Aug 2026, owner):** (c). Item names surface in findings ("Edge intrusion — F06"); the full list stays unpublished.

## D-004 · Free, subscription, or one-off? — **RULED**
- **Question:** Pricing model.
- **Options:** (a) Free. (b) Subscription. (c) One-off.
- **Recommendation:** Defer; free for the ten-person test. Gates only the profile (Stage 4, queue item 12), which is `[blocked: D-004]` accordingly.
- **Ruling (10 Aug 2026, owner):** Free for the ten-person test; revisit before any wider release. If Stage 4 (queue item 12) arrives during the experiment, its `[blocked: D-004]` tag is lifted — profile work may proceed on the free assumption.

## D-005 · F14 and S03: their Detection text isn't a single-frame property — **RULED**
- **Question:** QUEUE.md item 4 (builder-004 session) groups F14 (Wide-shot
  monoculture) and S03 (Tight framing) with the other single-frame
  Anthropic-API-vision detectors. Both items' Detection text in TAXONOMY.md
  names a property of a *set* of frames, not of any one photo: F14 is "a
  location's coverage is all establishing views" (a claim about every frame
  from a location); S03 is "the tightest frame of a subject among its
  batch-mates" (explicitly relative to other frames in the batch). Stage 1
  (where item 4 sits) processes one photo at a time - there is no batch to
  compare against yet. Implementing either as a single-frame vision call
  ("does this look tightly framed?", "does this look like an establishing
  shot?") would answer a different, easier question than the one TAXONOMY.md
  actually poses, and would be exactly the kind of plausible substitute
  CRITIC is instructed to flag and PREDICTION.md predicts ("the
  judgement-dependent ones get ... a model call with a vague prompt"). This
  was flagged as a forward-looking watch item for S03 by critic-001 before
  item 4 was implemented; this session's read extends the same reasoning to
  F14.
- **Options:** (a) Leave both as `DetectorNotImplemented` stubs until Stage
  2 (QUEUE.md items 7-9: batching, near-duplicate grouping, ranking) gives
  detectors batch/location context, then implement them properly against
  the batch - the approach taken this session. (b) Implement single-frame
  proxies now (e.g. a per-frame "shot type" classifier for F14, a per-frame
  "framing tightness" score for S03) explicitly labeled as partial/proxy
  detectors, with the real batch-level comparison landing in Stage 2. (c)
  Reword the two Detection texts to be single-frame-decidable - not
  available per CLAUDE.md/TAXONOMY.md: the taxonomy is frozen and
  unimplementable items are a DECISIONS.md entry, never a quiet reword.
- **Recommendation:** (a). A per-frame proxy under either item's real ID
  would misclassify single photos with that ID's label based on a check the
  taxonomy doesn't actually describe - worse than a stub that visibly says
  "not yet implemented." Both stay registered stubs (unchanged from the
  QUEUE-item-2 registration) until Stage 2 lands; this is a sequencing gap
  in QUEUE.md's staging, not a taxonomy defect, so no TAXONOMY.md edit is
  implied either way.
- **Ruling (10 Aug 2026, owner):** (a). Deferral approved — F14 and S03 are
  batch-relative by their Detection text and get implemented in Stage 2
  (items 7–9) when batch context exists. Single-frame proxies under their
  real IDs are rejected, per the reasoning above.

## D-006 · No ANTHROPIC_API_KEY in BUILDER sessions — how do item 4's detectors get genuine recorded test fixtures? — **RULED**
- **Question:** CLAUDE.md's API-discipline rule requires the test suite to
  run offline against "recorded" Anthropic API responses. This session's
  sandboxed BUILDER environment has no `ANTHROPIC_API_KEY` (checked `env`
  for any `*_API_KEY`/`*_TOKEN`/`*_SECRET` variable; none named Anthropic
  exists) and no direct network tool that could reach api.anthropic.com
  even if a key were present (curl/wget/WebFetch/WebSearch are denied in
  `.claude/settings.json`). So the nine detectors landed this session
  (`tests/test_vision_detectors.py`) are tested against hand-authored
  fixture objects shaped like the documented Anthropic Messages API
  tool_use response - not actual recordings of a live call, because none
  was possible to make. The parsing logic (`_vision.parse_tool_use_response`)
  is genuinely exercised by these fixtures; what's missing is evidence that
  a real Claude response, prompted with these exact Detection texts and
  images, actually comes back in the shape the code expects and with
  sensible verdicts.
- **Options:** (a) Grant a scoped `ANTHROPIC_API_KEY` to future BUILDER
  sessions (under the existing owner spend cap) so a session can make a
  small number of real calls, save the raw responses under
  `tests/fixtures/vision/`, and swap them in for the current hand-authored
  ones. (b) Owner runs `scripts/analyze.py` (once it exists, QUEUE.md item
  5) locally against a few real photos, and commits the recorded
  request/response pairs as fixtures for agent sessions to use from then
  on - no key ever reaches an agent session. (c) Leave the hand-authored
  fixtures as the standing test double indefinitely; accept that the test
  suite verifies parsing/wiring correctness but not real-model behavior.
- **Recommendation:** (b). Keeps the "no untrusted-session network/spend"
  boundary intact (agent BUILDER sessions still never touch
  api.anthropic.com or hold a key) while still getting genuine recorded
  fixtures into the repo for CRITIC and future sessions to check against.
  (a) is reasonable too if the owner is comfortable scoping a key to agent
  sessions specifically. (c) is the fallback if neither is worth the
  owner's time before the hard stop - not a taxonomy/implementation defect,
  just leaves this gap open.
- **Ruling (10 Aug 2026, owner):** Modified (a). Root cause of the missing
  key is suspected to be the platform filtering the reserved name
  `ANTHROPIC_API_KEY` from cloud sessions; the same key is now also
  provided in the session environment as `PICSTORY_VISION_KEY` (spend cap
  unchanged, set in the owner's console). Next BUILDER session: update
  `_vision.default_caller()` to read `PICSTORY_VISION_KEY` first, falling
  back to `ANTHROPIC_API_KEY`; then make a small number of live calls,
  save the raw responses under `tests/fixtures/vision/`, and replace the
  hand-authored fixture shapes with the recordings. The worklog should
  state which of the two variable names was actually visible in `env`
  (this settles the filtering question). Hand-authored shapes remain
  acceptable until a live call succeeds. If neither variable is visible in
  the session, fall back to option (b): the owner records fixtures locally.

## D-007 · F14/S03: what grouping do "a location" and "batch-mates" actually mean? — **RULED**
- **Question:** D-005 deferred F14 (Wide-shot monoculture) and S03 (Tight
  framing) "until Stage 2 lands, then implement them properly against the
  batch." Stage 2 (QUEUE.md items 7-10: batch input, F03 near-duplicate
  grouping, ranking/shortlist, session habit) landed by builder-010, and
  this session (builder-013) added item 13, R01, using that same batch
  context. Checking what Stage 2 actually gave F14/S03 to use: nothing
  matching either item's Detection text. F14's Detection text is "a
  location's **coverage** is all establishing views" - a per-location
  property, requiring frames to be grouped by *location*. S03's is "the
  tightest frame of a subject **among its batch-mates**" - requiring frames
  to be grouped by *subject*. Neither grouping exists anywhere in this
  codebase: there is no GPS/location metadata reader, no location-clustering
  logic, and no subject-identity grouping broader than F03's
  `group_near_duplicates` (which groups on "no change in position, focal
  length, or angle" - i.e. near-identical consecutive frames, deliberately
  the *narrow* case TAXONOMY.md calls "copies, not variations," not the
  broader "same subject, different angles/distances across the location"
  reading either F14's "coverage" or S03's "batch-mates" would need). Using
  F03's groups for either would answer a materially easier question ("does
  the tightest of this *safety-copy burst* win" instead of "does the
  tightest frame *of this subject anywhere in the batch* win") - the same
  plausible-substitute shape D-005 already rejected for a per-frame proxy,
  just one layer up: a too-narrow *group definition* rather than no group at
  all.
- **Options:** (a) Implement a real location-clustering signal for F14
  (EXIF GPS lat/long if present, falling back to a documented no-GPS
  behavior) and a real subject-clustering signal for S03 broader than F03's
  near-duplicate hash (e.g. all frames sharing a location cluster, or a
  wider perceptual-similarity threshold than F03's), each as new,
  separately-tested grouping logic, then wire F14/S03 on top. (b) Reuse
  F03's existing near-duplicate groups for both, explicitly disclosed as a
  narrower-than-intended proxy (F14 → "no tight/eye-level frame within any
  safety-copy burst"; S03 → "tightest frame within a safety-copy burst"),
  labeled as a known limitation rather than presented as the taxonomy's full
  claim. (c) Leave both stubbed (unchanged from D-005) until (a)'s
  grouping infrastructure is deliberately scoped as its own QUEUE item,
  rather than assumed to already exist because "Stage 2 landed."
- **Recommendation:** (c), with (a) as the real follow-up work. D-005's own
  reasoning ("a per-frame proxy under either item's real ID would
  misclassify... worse than a stub that visibly says 'not yet
  implemented'") applies just as directly to a too-narrow *group* as it did
  to no group at all - (b) would tag frames F14/S03 based on a burst
  grouping the Detection text does not describe, which is exactly the kind
  of plausible substitute CRITIC checks for. Filed now rather than left
  implicit because every builder session since builder-008 has logged "D-005
  covers F14/S03" in its test-count note as if the deferral's precondition
  were still unmet - it no longer is (Stage 2 exists), so the stubs are now
  blocked on a genuine open question (what grouping to build) rather than on
  waiting for Stage 2, and CLAUDE.md is explicit that this belongs in
  DECISIONS.md rather than being quietly carried forward.
- **Ruling (12 Aug 2026, owner):** Split by ID; this entry's own
  too-narrow-substitute reasoning is accepted in full.
  - **S03: modified (a), scoped small.** Implement subject clustering as a
    wider perceptual-similarity grouping — the relaxed variant this entry's
    option (a) itself names: a looser Hamming threshold than F03's, no
    focal-length or timestamp gates, so "same subject, different
    attempts/angles" cluster together where F03's "copies, not variations"
    deliberately does not. New, separately-tested grouping logic (own
    constants, documented as distinct from F03's calibration; in
    `duplicates.py` or a sibling module), then implement S03 against those
    subject clusters per its Detection text ("the tightest frame of a
    subject among its batch-mates"), with per-ID named tests so the
    coverage guard's `missing_test` drops S03.
  - **F14: (c), standing for the remainder of the experiment.** Its honest
    precondition is location clustering (EXIF GPS parsing + clustering +
    documented no-GPS fallback semantics) — deliberately out of scope for
    the remaining session budget. Batch-as-location and F03-groups-as-
    location are both rejected as too-narrow substitutes, per this entry's
    reasoning. F14 stays a visible `DetectorNotImplemented` stub;
    `missing_test = [F14]` is the documented, intended end state of the
    coverage guard for this experiment, and location clustering is named
    post-experiment work.
  - Agreed that "D-005 covers F14/S03" is no longer an accurate citation;
    worklogs should cite D-007 from here forward.

---

*Provenance note: D-008a–D-009 are owner-authored (15 Aug 2026, post-experiment phase 2), not builder flags — the experiment's autonomous phase ended at builder-015. Question/options/recommendation are drafted by the owner from the capstone evidence (docs/capstone-vienna-report.md) and PICSTORY_SCORECARD.md; the format is kept so future sessions read these like any other entry.*

## D-008a · F03/CMP keeper election: who decides which frame in a run is the keeper? — **RULED**
- **Question:** The capstone run exposed a contradiction between F03 and CMP.
  F03's convention (builder-008): the *first* frame of a near-duplicate run
  is the keeper; later frames get the safety-copy Finding. CMP then judges
  the same group on the rubric's axes — and in 2 of the capstone's 3 groups
  (11 over 10, and 30 over 29), CMP's winner was a frame F03 had already
  flagged as a copy. n=3 supports no rate claim, but it establishes the
  convention is not deterministically right — and the mechanism is obvious
  in hindsight: people often reshoot *because* the first frame had a
  problem, so a later frame winning is an expected case, not an edge case.
  Meanwhile safety-copy Findings count against `score_frame`, so the keeper
  election directly shapes the ranking and the pick.
- **Options:** (a) Keep first-frame-as-keeper; accept the occasional
  contradiction as two independent opinions. (b) CMP elects the keeper:
  F03 identifies runs only; no frame in a run carries an F03 Finding until
  CMP has ruled; CMP's winner is the keeper, the losers get the copy
  Finding. First-frame becomes the *fallback* keeper when CMP cannot rule.
  (c) Drop the keeper concept; flag every frame in a run equally.
- **Recommendation:** (b). (a) ships a known internal contradiction into
  the pick; (c) disqualifies whole bursts wholesale, which the pick's
  design already rejected (the best frame is often *in* the burst). (b)
  makes the two mechanisms one pipeline: F03 finds, CMP judges.
- **Ruling (15 Aug 2026, owner):** (b), with the sequencing consequences
  stated as requirements, not left to discovery:
  - `run_batch_analysis` must run CMP over each run *before* F03 Findings
    are merged — reversing the current order (F03 merge currently precedes
    comparisons). F03's `detect()` (or its batch-level wiring) takes the
    per-run keeper election as input rather than assuming position 1.
  - **Fallback:** when CMP cannot rule on a run — vision-call error, spend
    cap, or any other failure — the first-frame convention applies, and
    the resulting F03 Findings' descriptions must say the keeper was
    fallback-elected (disclosed, same standard as every proxy).
  - The copy Finding's description should name the elected keeper (it
    already names a keeper today; only the election changes).
  - Tests must cover both paths: CMP-elected keeper (including a case
    where CMP overturns position 1, per the capstone evidence) and the
    fallback.

## D-008b · Ranking: should a named strength beat a clean-but-empty frame outright? — **RULED**
- **Question:** The capstone pick came down to a tie at score 0:
  16_IMG_0967 (S03 minus F08) versus 18_IMG_0969 (no findings at all).
  Batch order broke the tie for 0967 — which matched the owner's own
  preference. A previously-proposed rule ("a frame with any disqualifier
  cannot outrank a clean frame at equal score") would have inverted this,
  preferring *nothing wrong* over *something right* — which reinstates the
  curation app the product exists to not be. The live question is the
  inverse: should the strength win *outright* rather than by the luck of
  batch order?
- **Options:** (a) Keep pure `count(S) − count(F)` with batch-order ties.
  (b) Keep the linear score, add S-count as the first tie-breaker:
  at equal score, more named strengths wins; batch order only breaks
  genuine ties after that. (c) Reweight strengths above flaws (e.g. S=2,
  F=1) so the strength-bearing frame wins on score alone.
- **Recommendation:** (b). It encodes exactly the principle the capstone
  validated — at equal net craft, a frame with something *right* beats a
  frame with merely nothing wrong — without inventing arithmetic the
  taxonomy nowhere defines, which is (c)'s flaw and the same invented-
  ordinal-scale move builder-005 correctly refused for recurrence.
- **Ruling (15 Aug 2026, owner):** (b). At equal `count(S) − count(F)`,
  higher `count(S)` ranks first; batch order remains the final,
  documented tie-breaker. The capstone tie (0967 over 0969) becomes the
  regression test: 0967 must now win by rule, not by order. Revisit only
  as part of severity weighting (QUEUE phase-2 calibration) — if per-
  finding severities ever exist, this tie-breaker may be subsumed and
  this entry should be cited when that happens.

## D-008c · The habit: most-frequent is the least informative — what replaces raw count? — **RULED**
- **Question:** The capstone habit selected F05 — correct by builder-010's
  raw-count rule (28 of 31 frames), and the least useful possible advice:
  it describes the ultrawide lens, not the user. Three detectors (F05×28,
  F06×27, F11×25) fired at base rate — 80 of 150 detections — and any
  raw-count habit will always be captured by whichever of them tops the
  batch. Meanwhile "you tilt up" (F08, 9 frames) is a fact about the
  user's hands. The honest ledger stands: builder-010 implemented the
  queue item's own words ("most-recurrent F/S item") faithfully; the
  definition was the flaw. The ideal fix — surprise relative to the
  user's own cross-session base rate — requires profile history that
  mostly doesn't exist yet.
- **Options:** (a) Keep raw count. (b) Batch-pervasiveness exclusion:
  an ID that fired on more than a threshold share of the batch's frames
  (proposed: >2/3) is classified *pervasive* — it describes the batch's
  shooting conditions or equipment, not a per-frame choice — and is
  excluded from habit selection; the habit is the most recurrent
  *non-pervasive* F/S ID, existing tie-break unchanged. Pervasive
  findings are not discarded: they may surface as a separate one-line
  session note ("this batch: ultrawide throughout"), distinct from the
  habit. (c) Full statistical informativeness (frequency relative to a
  base rate) — requires either cross-user priors that don't exist or
  profile depth that doesn't exist yet.
- **Recommendation:** (b) now, (c) later. (b) is implementable today
  without inventing statistics, and on the capstone data it selects F08
  ("you tilt up," 9 frames) over F05/F06/F11 — precisely the outcome the
  critique asked for. (c) is the right end state once the profile has
  enough sessions to define the user's own base rate; it should arrive as
  a future entry citing this one, not be improvised now.
- **Ruling (15 Aug 2026, owner):** (b). Threshold 2/3, defined as a named,
  documented constant with the reasoning in the selector's docstring —
  and the capstone batch is the calibration fixture: F05/F06/F11 must
  classify as pervasive on it, F08 must win the habit. The session note
  for pervasive findings is approved as part of the same item (one line,
  not a list, per the product spec). The profile's recurrence *store*
  is unchanged — pervasiveness affects habit selection, not what gets
  recorded. When profile depth permits a user-relative base rate,
  reopen as a new D-item citing this ruling.

## D-009 · Editing suggestions: the v1 scope excluded editing — the Check context requires it — **RULED**
- **Question:** The product seed's v1 scope excluded "editing, filters,
  any pixel manipulation." The Check surface (product spec v2 §2.5)
  analyzes a photo that may have been taken days ago — a context where
  "reshoot it" is not actionable and an edit *suggestion* ("the intruding
  figure is in the right 8% — crop it out") is the only useful coaching.
  Honoring the suggestion requires knowing, per taxonomy item, whether
  the failure is post-fixable at all — a field the frozen taxonomy does
  not carry. Complication: fixability is not static for every ID. F05 is
  the proof case: pure ultrawide bowing is lens-correctable, but a
  symmetric subject drifted off the optical center is capture-only — the
  same ID, two fixabilities, decided by which failure the finding
  actually describes.
- **Options:** (a) Amend TAXONOMY.md (version bump) with a per-item
  `- **Fixability:**` bullet — post-fixable / capture-only / conditional —
  parsed verbatim like every other bullet, keeping the single source of
  truth. The taxonomy freeze was an experiment-phase rule; the owner may
  version it post-experiment, and the amendment discipline (a new bullet,
  no rewording of existing text) preserves the frozen Detection/Correction
  language every detector depends on. (b) A sidecar fixability mapping in
  code — leaves the taxonomy untouched but creates the second source of
  truth the whole architecture was built to prevent. (c) Ask the vision
  model to judge fixability per finding at Check time with no taxonomy
  grounding — a vague-prompt substitute by another name.
- **Recommendation:** (a), with the conditional cases handled by the
  machinery that already exists: `SubPatternSpec`. F05's Fixability reads
  `conditional`, and its detector opts into a closed-vocabulary
  sub-pattern (e.g. `bowing` / `off_center_drift`) exactly as F06 already
  does for edges — the finding itself then carries which case applies,
  enum-constrained, and the Check surface maps sub-pattern → fix. No new
  mechanism; the profile's sub-pattern design generalizes as built.
- **Ruling (15 Aug 2026, owner):** (a), as TAXONOMY.md **v1.2**, with
  hard constraints: the amendment adds `- **Fixability:**` bullets (and,
  where `conditional`, the sub-pattern vocabulary) and changes *no
  existing text* — Detection, Correction, Reinforcement, Rule and
  Profile-note bullets are byte-identical before and after; a test should
  assert the parsed texts are unchanged across the version bump. Initial
  assignments per the product spec v2 §2.5 (F08 straighten; F06/F07/F02
  crop; F05 conditional per above; F11/F15/F04/F03 capture-only), each
  derivable from the item's own Correction text — where it isn't
  derivable, that item's Fixability is a question back to the owner, not
  a guess. Performing edits remains out of scope permanently: suggestions
  name what, where, and which tool, then hand off. The unfixable verdict
  ("no edit saves this one") is in scope and required — an improvement
  path that always exists is flattery, not coaching. Timestamp-switched
  delivery (reshoot vs. edit) is product behavior, not taxonomy, and is
  not part of this ruling.

## D-010 · Habit calibration: does F08 actually win on the capstone batch, or does S01?
- **Question:** QUEUE.md item 17(a) and D-008c's own ruling both name the
  calibration fixture's required outcome explicitly: "F05/F06/F11 must
  classify pervasive and F08 must win the habit." Implementing D-008c's
  mechanism exactly as ruled — `PERVASIVE_THRESHOLD = 2/3`, "the habit is
  the most recurrent *non-pervasive* F/S ID" — against the capstone
  report's own per-ID frame counts (counted directly from
  `docs/capstone-vienna-report.md`'s `[detected]` lines, id by id, summing
  to the report's own header total of 150 detections across 31 frames —
  not eyeballed) gives: F05 (28/31), F06 (27/31), F11 (25/31) all clear the
  threshold and are correctly excluded, exactly as required. But the next
  count down is not F08 — it's S01 at 20/31 (64.5%), *under* the 2/3
  threshold (66.7%), so S01 stays eligible and outranks F08 (13/31) for
  the habit. D-008c's own narrative text separately cites "F08, 9 frames"
  — a count that does not match the report as it stands (F08 is 13 by
  direct count) and that predates this session; S01 is not mentioned
  anywhere in D-008c's narrative at all, despite being the second-highest
  count in the batch after the three pervasive IDs. The mechanism itself
  is unambiguous and was implemented exactly as ruled (`ranking.py`:
  `PERVASIVE_THRESHOLD`, `pervasive_ids`, `pervasive_note`,
  `compute_habit`'s exclusion); it is the fixture's *named expected
  winner* that does not hold against the cited evidence.
- **Options:** (a) Correct the calibration fixture's expected winner to
  S01 — the honest result of applying the ruling's own stated mechanism to
  the report's actual, verified counts. (b) Treat S01 as pervasive too
  (e.g. lower the threshold below 64.5%, or a qualitative carve-out for
  "human in the foreground" as a touristy-batch shooting pattern rather
  than a per-frame choice) — not supported by the ">2/3" rule as literally
  ruled, and would need its own justification rather than being reverse-
  engineered to hit F08. (c) Re-derive "F08, 9 frames" from a counting
  convention the ruling's text doesn't spell out (e.g. sessions rather
  than frames, or some subset of F08's 13 occurrences) and reconcile it
  with the report's own 13-count — unclear what that convention would be.
- **Recommendation:** (a). The mechanism is implemented faithfully and
  matches every part of the ruling that the actual data can verify
  (F05/F06/F11 pervasive); only the named winner is inconsistent with the
  cited evidence. This session's tests (`test_ranking.py`'s
  `test_capstone_calibration_pervasiveness_and_actual_habit_winner`)
  assert the honest, mechanism-derived result (habit = S01) rather than a
  forced F08, with this discrepancy documented in the test itself and
  here — not silently overriding the ruling's stated outcome, per
  CLAUDE.md's "nothing answers its own decision."
- **Ruling:** (pending)
