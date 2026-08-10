# DECISIONS

D-nnn format, stable IDs. BUILDER writes here when blocked (question, options, recommendation, reasoning) and moves on. CRITIC may add entries and may not close them. Only the human writes rulings; rulings are appended, never rewritten. **At five open decisions, both routines halt and write HALT.md.**

Open count: 4

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

## D-003 · Does the taxonomy get shown to users? — **OPEN**
- **Question:** Is the closed list a visible teaching asset or hidden machinery?
- **Options:** (a) Fully public. (b) Fully hidden. (c) Item names surface in findings ("Edge intrusion — F06"); the full list stays unpublished.
- **Recommendation:** (c). Named findings make the coaching feel diagnostic; recurring names make the profile legible. Not blocking for the experiment (output is for the owner), so left open without cost.
- **Ruling:** —

## D-004 · Free, subscription, or one-off? — **OPEN**
- **Question:** Pricing model.
- **Options:** (a) Free. (b) Subscription. (c) One-off.
- **Recommendation:** Defer; free for the ten-person test. Gates only the profile (Stage 4, queue item 12), which is `[blocked: D-004]` accordingly.
- **Ruling:** —

## D-005 · F14 and S03: their Detection text isn't a single-frame property — **OPEN**
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
- **Ruling:** —

## D-006 · No ANTHROPIC_API_KEY in BUILDER sessions — how do item 4's detectors get genuine recorded test fixtures? — **OPEN**
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
- **Ruling:** —
