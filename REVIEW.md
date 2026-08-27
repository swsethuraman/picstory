# REVIEW — critic-007 session note, 2026-08-27

Checked for a diff since the last critic commit landed on `main`
(`50bce0f`/`a8bbbd1`, critic-006): `git log 50bce0f..HEAD` on the
designated branch (already even with `main`'s real tip) shows only the
merge of critic-006's own PR — zero BUILDER commits have landed in the
eleven days since. Re-ran the full suite directly: **316 passed, 1
xfailed**, identical to critic-006's own reported count, confirming no
silent drift in the code these findings describe. `DECISIONS.md` open
count is unchanged at **1** (D-011, filed by critic-006, still
`(pending)` an owner ruling — not this role's to close). QUEUE.md has no
unimplemented items left for a BUILDER session to pick up.

Separately, `mcp__github__list_pull_requests` shows **seven** open,
unmerged PRs (#28–#34) opened by prior scheduled CRITIC sessions between
17 and 26 Aug, every one reporting this identical "no new diff since
critic-006" finding and none of them merged. That pile-up, plus D-011's
eleven days unruled against a hard stop now two days out (29 Aug), is
flagged to the owner directly (see this session's worklog,
`logs/critic-007.md`) rather than acted on unilaterally — closing or
merging someone else's open PRs is outside a CRITIC session's authority,
and ruling D-011 is the owner's alone per CLAUDE.md.

critic-006's own review, unchanged below, remains the operative content
for the diff it covered.

---

# REVIEW — critic-006, 2026-08-16

Scope: diff from `3f77028` (critic-005) through `6aa200e` (HEAD) —
QUEUE.md item 17 (habit pervasiveness + ranking S-count tie-break,
`a1b77f9`), the owner's D-010 ruling and its QUEUE.md/DECISIONS.md
bookkeeping (`231cc1f`, `8b91188`, `93745bb`), QUEUE.md item 18
(Fixability parsing per D-009, `aa6bd28`), and QUEUE.md item 19 (the
hygiene sweep, `b70ad16`). Not covered by critic-005 (its own scope ended
at `50a80f8`, before item 17 landed).

Per CLAUDE.md's CRITIC instruction: for each taxonomy ID / output row,
does the implementation match the actual described behavior, or a
plausible substitute?

## Headline finding

One genuine taxonomy-match question, filed as **DECISIONS.md D-011**
(open, not ruled): F05's Fixability-driven `bowing` sub-pattern accepts
a condition — subject centered — that F05's own frozen Detection text
appears to require the *opposite* of ("when the subject drifts off the
ultrawide's center"). Everything else in this diff — item 17's
pervasiveness/tie-break mechanisms, item 18's fixability parsing and
per-finding surfacing, item 19's hygiene fixes, and the D-010 process
itself — checked out as real, faithful implementations of their
governing text.

## QUEUE item 17 · Habit pervasiveness + ranking S-count tie-break (D-008c/D-008b)

| Check | Verdict |
|---|---|
| `PERVASIVE_THRESHOLD = 2/3`, named/documented constant | Matches — `ranking.py:131`, docstring cites the capstone calibration (F05/F06/F11 at 28/27/25 of 31, all `>2/3`). |
| `compute_habit` excludes pervasive IDs, picks most-recurrent non-pervasive F/S ID | Matches — read `compute_habit` directly: `eligible = {tid: count ... if tid not in excluded}`, `excluded = set(pervasive_ids(...))`. Existing ascending-ID tie-break unchanged. |
| Pervasive IDs surface as one disclosed report line, distinct from habit | Matches — `pervasive_note` returns a single f-string line ("This batch, throughout (excluded from habit selection): ..."), wired into `analyze_batch.render_report` right after the habit line, not folded into it. |
| Calibration fixture built from the capstone report's own counts | Matches, and independently re-verified this session: `test_capstone_calibration_pervasiveness_and_actual_habit_winner`'s `counts` dict sums to 150 (asserted in the test itself) — cross-checked F02's frame count (5) against `docs/capstone-vienna-report.md`'s own `[detected]` lines directly rather than trusting the test's transcription, and it matches the report's real per-frame F02 findings. |
| D-010's outcome (S01 as habit, F08 as top F-item, mechanism unchanged) | Matches — the test asserts `habit.taxonomy_id == "S01"`, and its docstring states the F08-vs-S01 discrepancy plainly rather than silently forcing F08. This is CLAUDE.md's "nothing answers its own decision" working as intended end to end: builder-018 (item 17) found the mismatch and logged it as D-010 without closing it; the owner ruled it in a later commit; builder-019 inherited the ruling, and this session confirms the ruled outcome is what the code actually produces, not merely what the test's own docstring claims. |
| Ranking: `count(S)` breaks a `score_frame` tie before batch order | Matches — `rank_frames`'s sort key is `(score_frame(fa), len(_ids_with_prefix(fa, "S")))`. `test_rank_frames_s_count_breaks_score_ties` is a stronger test than QUEUE.md item 17(b) literally asked for: rather than the literal capstone frame IDs (0967/0969), where 0967 already happens to sort first by batch order regardless of the new rule, this fixture deliberately places the S-bearing frame *second* in the input list — so only the S-count rule (not batch-order luck) can produce the asserted winner. Worth naming as a positive, not a gap: a literal 0967/0969-named test would have passed even on the *old*, pre-D-008b behavior. |

No substitute pattern found in item 17.

## QUEUE item 18 · Fixability parsing (DECISIONS.md D-009)

| Sub-part | Verdict |
|---|---|
| (a) `schema.taxonomy_fixability(id)` / `taxonomy_fixability_category(id)` | Matches — same verbatim-regex-from-TAXONOMY.md pattern as every other `taxonomy_*_text` helper; category parsed out of the fixability text itself (`_FIXABILITY_CATEGORY` regex), not a second hardcoded copy. Spot-checked three categories directly against TAXONOMY.md: F02/F06/F07/F08/F09/F12 `post-fixable`, F03/F04/F11/F13/F14/F15 `capture-only`, F05 `conditional` — all as parsed. |
| (b) byte-identical guard across v1.1→v1.2 | Matches — `test_v1_2_preserves_every_previously_parsed_text_byte_identical` hand-transcribes all 20 Detection texts, all 15 Correction texts, all 4 Reinforcement texts, R01's Rule, and F06's Profile note (the full set D-009(b) named, not a sample) and asserts each against the live parser. Ran it directly this session as part of the full suite — passes. |
| (c) F05's `conditional` Fixability via `SubPatternSpec` | Mechanically matches the pattern F06 already established (one enum-constrained field added to the same structured tool call). See headline finding / D-011 for a scope question this raises, distinct from whether the mechanism itself was wired correctly — it was. The two recorded fixtures (`f05_bowing_ceiling.json`, `f05_off_center_drift_ceiling.json`) are genuine live-call recordings, not hand-authored: both carry realistic Anthropic message/tool-use IDs, per-call token usage, and a `cache_creation` block no hand-authored fixture in this repo has ever included — checked directly, not assumed from builder-019's own description. `CONDITIONAL_FIXABILITY_RESOLUTION = {"F05": {"bowing": "post-fixable", "off_center_drift": "capture-only"}}` matches TAXONOMY.md's Fixability bullet prose exactly. |
| (d) Finding-level fixability surfaced in `analyze_batch`'s report | Matches — `DetectorRun.fixability`, computed via `analyze._fixability_or_disclosed_gap` (catches `SchemaError` and discloses `"unresolved (...)"` rather than crashing the batch on a hand-built `Finding` without a `sub_pattern` — a real, disclosed degradation path, not a silent one) at both `DetectorRun` construction sites (`analyze.py` and `analyze_batch.py`), printed as `(fixability: <word>)` in both CLIs' `render_report`. |

## QUEUE item 19 · Hygiene sweep

| Sub-part | Verdict |
|---|---|
| (a) `f14.py` cites D-007, not "QUEUE.md item 4" | Matches — read the module docstring and the raised message directly; both now name D-007 and state the actual reason (location clustering out of scope) rather than the stale citation. |
| (b) `record_vision_fixtures.py` per-ID split | Assessed, not coded — builder-020's own conclusion that the `--only ID` filter (added by builder-019, used live for F05) already satisfies the item's actual complaint (re-spending on the whole call list) holds up: grepped the script directly, `--only` is real and filters `calls` before any are made, not after. Reasonable call under CLAUDE.md's no-premature-abstraction rule; not a substitute-pattern concern since nothing in TAXONOMY.md/CLAUDE.md governs this script's internal structure. |
| (c) F02 known-limitation disclosure | Matches, verbatim — the docstring's quoted capstone text ("Dark, low-texture mass along the top edge covering 86%...", frame `30_IMG_0981`) cross-checked directly against `docs/capstone-vienna-report.md` line 718: exact match, not a paraphrase. Explicitly framed as disclosure, not a threshold change, per the item's own instruction. |
| (d) `xfail(strict=True, ...)` marker | Matches — `tests/test_taxonomy_coverage.py`, `@pytest.mark.xfail(strict=True, reason="F14 stands stubbed per DECISIONS.md D-007 ...")` directly above `test_every_id_has_detector_and_named_test`. Ran the suite this session: reports `1 xfailed`, not a `FAILED` line, confirming the marker does what item 19(d) asked. |

Also checked the operational note critic-005 flagged (QUEUE.md item 18's
stale `[blocked: ...]` bracket) — cleared in `231cc1f`, alongside the
D-010 ruling, exactly as critic-005 asked the next BUILDER session to do.

## D-011 detail (new this session)

F05's Detection text (v1.0, confirmed byte-identical under item 18b's
guard): "Curved or skewed lines on ceilings and symmetric architecture
when the subject drifts off the ultrawide's center." Read literally, this
requires an off-center subject for the condition to be present — matching
F05's Correction text, "keep symmetric subjects centered" (recentering
only fixes something if drift is the problem).

TAXONOMY.md v1.2's Fixability bullet (owner-authored, D-009) splits F05
into `bowing` ("curved lines *with the subject centered*") and
`off_center_drift` ("subject placed off center"). `f05.py`'s
`GEOMETRY_SUB_PATTERN` restates the same split independently in its own
`description` field, sent to the model in the same tool call as the
Detection text. The result, verified against a genuine recorded API
response (not a hand-authored guess): the live model reports
`detected=true, geometry=bowing` for a frame it explicitly describes as
having a centered subject — the literal opposite of what Detection's own
clause states as the trigger.

This is not necessarily a bug — D-009's own "Complication" narrative
already names "pure ultrawide bowing" as a real, standalone case, which
reads as the owner's actual intent predating this implementation. But
it means the prompt CLAUDE.md's API-discipline rule requires to embed
verbatim (Detection alone) is narrower than what the request as a whole
(Detection + sub-pattern instruction) now accepts as a positive — worth
an explicit ruling rather than leaving future audits to rediscover the
same gap. Filed as DECISIONS.md D-011, open, not closed by this session
per CLAUDE.md's "CRITIC may add entries and may not close them."

## Still open from prior reviews, untouched by this diff

- F09's center-third subject proxy — untouched, still an accepted,
  disclosed proxy (critic-002's original standard).
- The `_keeper_for_group` / CMP-enum-constraint assumption critic-005
  named — untouched this session (`cmp.py`/`f03.py` not in this diff's
  file list).

## Test suite

Ran directly this session (`uv run pytest -q`): **317 collected, 316
passed, 1 xfailed** — 15.18s. Matches builder-020's own reported count
exactly; no drift between what the worklog claims and what the suite
actually does.

## DECISIONS.md

One new entry this session: **D-011** (open, F05 Detection-vs-Fixability
scope question, detailed above). Open count now **1** (was 0). Well under
the five-open hard-stop threshold; no `HALT.md` implication.
