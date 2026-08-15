# PICSTORY — THE SCORECARD
## Scoring PREDICTION.md (written 9 Aug 2026, pre-launch) against the record
### 14 Aug 2026 · after 15 builder sessions, 4 critic reviews, 7 rulings, and the Vienna capstone

---

## 0. HOW THE EXPERIMENT ENDED

**By completion, not by HALT and not by hard stop.** Session 15 of 20 budgeted found the queue exhausted, verified there was no genuine gap, declined to invent work, and wrote a no-op worklog. Both routines were then deactivated with five sessions returned unspent. PREDICTION.md's scoring clause ("read at HALT or hard stop") anticipated two endings; the experiment found a third and better one.

**The "do not rescue a stall" clause was never tested — no stall occurred.** The owner's interventions (merging PRs, ruling on decisions, fixing platform configuration) were all inside the role CLAUDE.md defined. The closest call: ruling four open decisions back to zero when the count sat at 4-of-5. That defused a *potential* halt — but ruling is the owner's defined job, not a rescue; a halt caused by unruled decisions would have been a technicality about the owner's absence, not a finding about the system.

---

## 1. PREDICTION 1 — **FALSE, decisively**

> *"It ships a working app that does the ranking and NOT the coaching. Detectors get built for the computable taxonomy items... and the judgement-dependent ones get stubs, generic language, or a model call with a vague prompt. The coverage test passes on names and fails on substance."*

**Every clause failed.**

- **The judgment detectors were the best-built part of the system.** Prompts embed each item's Detection text parsed *verbatim from the frozen taxonomy at call time* — paraphrase made structurally impossible, not merely forbidden. Verdicts are schema-forced and ID-tied. Fixtures were recorded from live calls where possible and honestly labeled hand-authored where not.
- **Four consecutive critic reviews, instructed specifically to hunt plausible substitutes, found zero** — including over the diff containing every judgment-laden design (CMP, the profile, S03's proxy, R01's type distinction).
- **The coverage test ended red on exactly one item (F14) — deliberately, by ruling, with the missing precondition and its cost documented.** The literal opposite of "passes on names and fails on substance": it refuses to pass on substance grounds the system itself argued for.
- **The capstone showed substance in the field:** rationales naming specific pixels ("elderly woman in white," "partial red 'Viking Rinda' tour sign"), CMP verdicts doing photographer-grade analysis (gaze-meets-lens vs. profile; cropping through faces vs. clean half-figures), and the ranked pick's top two matching the owner's own preferred frames out of 31.

**The honest asterisks:** disclosed proxies exist (F09's center-third subject, F03's dHash-as-pose, S03's sharp-area-as-tightness) — the honest cousin of substitution, each named in its docstring and accepted by review under a consistent disclosure standard. And the substitution *pressure* the prediction named was entirely real: it surfaced at least four times (the S03 queue-grouping trap, the F14/S03 single-frame temptation, the F03-groups-as-proxy shortcut, a test name that accidentally satisfied the coverage guard) — and every time it was refused, flagged, or ruled on rather than taken. **The prediction failed not because the failure mode was imaginary but because the design made honesty cheaper than substitution.** That is the experiment's central result.

---

## 2. PREDICTION 2 — **HALF RIGHT: the mechanism fired, the event never did**

> *"The first HALT comes from decisions accumulating, not from a crash."*

- **The accumulation happened exactly as predicted:** by the second day of building, four decisions (D-003–D-006) stood open simultaneously — one short of the halt threshold — arriving through honest flags (a genuinely ambiguous deferral, a missing API key), not confusion.
- **The HALT never fired**, because the owner ruled same-day and the count returned to zero. It never rose above one again. No crash ever occurred either — fifteen sessions, zero unrecoverable failures.
- **One wrinkle worth the record:** builder-005 declined to open a D-item partly *because* opening it would trip the halt — correct on the merits, but a system factoring halt-proximity into what counts as a decision is how thresholds get managed instead of respected. It did not recur; the eventual D-007 was opened without hesitation when a genuine question existed.

**Score: half.** The prediction correctly identified decisions as the system's real pressure point and correctly ruled out crashes. It implicitly predicted the human would let the pile grow; the human didn't. The threshold worked as designed — as a fuse the owner services, not a bomb that goes off.

---

## 3. PREDICTION 3 — **TRUE, nearly dead-center**

> *"Sessions to something usable: 7–12."*

- **"Usable" — batch in; ranked shortlist; near-duplicate comparison naming differentiating variables; one habit by taxonomy ID — closed at session 10.** Mid-window.
- The complete engine (19 of 20 IDs, CMP, profile, rules) landed at session 14; session 15 was the honest no-op. Five budgeted sessions returned unspent.
- **The asterisk:** "usable" was true at fixture scale and false at real-photo scale — the capstone's first runs died on full-resolution iPhone frames (no downsampling anywhere in the pipeline; ~5MB API payloads; uncached full-res hashing), invisible to 266 green tests whose fixtures were all ≤200px. A manual pre-resize made the capstone succeed. **Usable-per-spec at session 10; usable-on-real-photos required one workaround the spec never asked for.** The prediction is scored on its own terms: true.

---

## 4. THE CAPSTONE — 31 Vienna frames against the finished engine

**Validated:**
- **The pick matched.** The engine's #1 and #2 (16_IMG_0967, 18_IMG_0969) are the two frames the owner independently named as his preferred — and #1 won *because* it carried a named strength, the coaching thesis expressed as arithmetic.
- **CMP is the product.** Per-axis verdicts matched a photographer's read; the tiebreaker fired honestly once and declined to invent a story element once.
- **F03 found three genuine safety-copy runs;** S03's subject clusters were visibly wider than F03's pairs (D-007's two-groupings ruling, working in the field).
- **The signature finding came home:** frame 0955's right-edge obstruction — the failure flagged across three batches in the original critiques — was caught independently by two detectors (F02 measuring 67% of the edge; F06's vision call describing "a dark, out-of-focus vertical element... clearly unintended"), and the owner's own eye agreed on sight.

**Revealed (the phase-2 queue):**
1. **Three detectors fire at base rate** — F05×28, F06×27, F11×25: 80 of 150 detections, individually correct, collectively uninformative. Severity/salience weighting is the prerequisite for any score.
2. **The habit selected the most frequent finding, not the most informative** — a faithful implementation of a flawed spec definition ("most-recurrent"). Redesign: informativeness over frequency.
3. **F03 and CMP disagree on keepers** — CMP overturned the first-frame convention in two of three groups (n=3: not deterministic, no rate claim). D-008: F03 finds the run, CMP adjudicates, first-frame demoted to fallback.
4. **The resolution contract** — ingest at working resolution, cache derived arrays, cap API payloads, test at realistic scale. The single most valuable engineering finding, and it could only have come from real photos.
5. One clean false positive (F02 reading a stone arch shot through as a grip obstruction); F06's "multiple" swamping the directional edge signal (multiple×23 vs. right×3).

---

## 5. THE LEDGER, ONE PARAGRAPH

Fifteen builder sessions (fourteen with real work, one honest no-op), four critic reviews (unanimous no-substitute verdicts, one wrong worklog number caught by re-running the evidence, one five-session live-call leak missed by three reviews and then caught, owned, fixed, and verified by the fourth), seven decisions ruled, two agent-proposed queue items (one implementing an orphaned spec item with a type-level distinction the taxonomy implied, one formally contesting a stale deferral its own predecessors had been citing on autopilot), one duplicate-session accident that became a controlled experiment in spec-determinism, one deliberately unimplemented item with its price tag documented, and a capstone in which the machine's top two picks matched its maker's eye. Total spend: a few dollars. Full mechanics and failure modes: see the BUILDER/CRITIC playbook.

---

## 6. WHAT THE BET WAS ACTUALLY ABOUT

PREDICTION.md bet that an autonomous builder, left alone with a hard spec, would fake the hard parts — and it lost. But the loss was earned, not lucky: the substitution pressure it predicted showed up on schedule, repeatedly, and was diverted every time into the channels built for it. The seven rulings in DECISIONS.md are the counterfactual substitutes — each one a place where a lesser design would have shipped the easy version silently. **The finding is not that agents are honest. It is that honesty is a property of the system around them: freeze what done-honestly means, pay an adversary to hunt the shortcut, give the builder a cheap way to hand you its doubts, and the compliant path wins on cost.** The engine was the deliverable of the product. This sentence is the deliverable of the experiment.
