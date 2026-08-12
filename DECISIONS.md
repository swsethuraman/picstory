# DECISIONS

D-nnn format, stable IDs. BUILDER writes here when blocked (question, options, recommendation, reasoning) and moves on. CRITIC may add entries and may not close them. Only the human writes rulings; rulings are appended, never rewritten. **At five open decisions, both routines halt and write HALT.md.**

Open count: 0

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
