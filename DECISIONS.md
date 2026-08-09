# DECISIONS

D-nnn format, stable IDs. BUILDER writes here when blocked (question, options, recommendation, reasoning) and moves on. CRITIC may add entries and may not close them. Only the human writes rulings; rulings are appended, never rewritten. **At five open decisions, both routines halt and write HALT.md.**

Open count: 2

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
