# REVIEW — critic-005, 2026-08-16

Scope: diff from `97f59e7` (critic-004) through `50a80f8` (HEAD) — builder-016
(item 15, the resolution contract, `98609a2`), builder-017 (item 16, keeper
election, `4a6d1c5`), plus owner commits in the same range: D-008a/b/c and
D-009 rulings (`7862d5a`), Stage 5 opening and the hard-stop extension
(`e2e085a`), the scorecard (`f2d6d06`), and TAXONOMY.md v1.2 plus a QUEUE.md
text addition for item 19(d) (`50a80f8`). No critic-only diff this session —
code landed from two BUILDER sessions since the last review.

Per CLAUDE.md's CRITIC instruction: for each taxonomy ID / output row, does
the implementation match the actual described behavior, or a plausible
substitute?

## Headline finding

**No plausible-substitute pattern found in this diff.** Item 15 is
infrastructure (no taxonomy ID of its own) and item 16 is orchestration
(F03 + CMP) — both checked directly against their governing text (the
module docstrings' own claims, and D-008a's ruling) rather than taken on
faith, and both hold up.

## QUEUE item 15 · The resolution contract

| Sub-part | Verdict |
|---|---|
| (a) downsample-after-EXIF-read | Matches. `frame.load_frame` reads EXIF from the still-open original `Image`, then downsamples via `_downsample_to_working_resolution` before building the `Frame` — read the function order directly in `frame.py`; EXIF extraction happens before the `np.array(...)` call that downsamples. `WORKING_RESOLUTION_MAX_DIM = 2000` is a named, documented module constant, not a magic number buried in the resize call. |
| (b) caching | Matches. `Frame.luminance` is a `functools.cached_property` (was a plain `@property`); `Frame.dhash(hash_size)` memoizes per `hash_size` on a new `_hash_cache` field (`compare=False`, correctly excluded from `Frame` equality — checked the dataclass field directly). `f03.py` and `subject_clusters.py` both call `frame.dhash(hash_size=8)` now instead of `_imaging.difference_hash` directly — confirmed by reading both modules' `_frame_hash` functions post-diff. |
| (c) upload ceiling | Matches, and confirmed to actually run even when a test blocks the live API call. `_vision._encode_jpeg` gained an independent resize-then-quality-reduction loop (`_MAX_UPLOAD_DIM=1500`, `_JPEG_QUALITY=85→30` in steps of 15, `_MAX_PAYLOAD_BYTES=4MB`). Traced the call order in `_vision.judge()`: `_encode_jpeg(frame)` runs while building the `VisionRequest`, *before* `caller(request)` is invoked — so `tests/test_frame.py`'s `test_five_large_frames_load_and_analyze_within_a_time_budget` (which relies on `conftest.py`'s autouse live-call block to keep the suite offline) still exercises this encode/resize path on every large frame it builds, not just the local decode/hash portion. Not a hole in the item-15e regression test's coverage — verified by reading the call sequence, not assumed from the docstring's claim. |
| (d) `Frame.path` retained | Matches. Docstring on both the module and the field names it as the lazy native-resolution escape hatch, explicitly "no detector needs this today" — accurate; grepped for `.path` reads elsewhere in `src/picstory/detectors/` and found none beyond the constructor/EXIF path already exercised in `load_frame` itself. |
| (e) regression tests | Matches the item's own ask. `tests/test_frame.py` (new, 7 tests): 8000×6000 working-res-ingestion, EXIF-survives-resize, cached-luminance/memoized-dhash identity, F01-at-working-resolution, and the timing-bounded 5-frame end-to-end. Ran the full suite directly this session (see Test suite below) — the timing test passes in the full run, not just in isolation. |
| (f) F01 recalibration disclosure | Matches. F01's new "Resolution note" explains *why* it does not call `_imaging.downsample` (would erase the fine detail it measures), cites the specific empirical check (`~24000` sharp / `~660` soft at both 200px and 2000px) backing "`SOFT_THRESHOLD` holds without adjustment," and names a real, undisclosed-until-now limitation (native detail finer than the working-resolution downsample's own Nyquist limit can be anti-aliased away before F01 ever sees it) rather than claiming the fix is complete. Checked the other locally-resolution-sensitive detectors named in builder-016's own worklog (F02/F07/F08/F09/F10/F12/S03) — F02/F08/S03 already call `_imaging.downsample` to their own fixed scale (independent of `WORKING_RESOLUTION_MAX_DIM`, so no new disclosure needed) and F07/F09/F10/F12 are grid-fraction/percentile-based; none of the six needed the same docstring addition, and none silently got skipped — this is a `grep`-verified negative, not an assumed one. |

One thing worth flagging for whoever runs this on real photos next, not a
taxonomy-match defect: item 15's own worklog reports a 124s manual benchmark
against a live key from a bare script that skipped the test suite's
offline discipline (46 unintended, spend-cap-metered live calls) — already
self-flagged, already corrected in the same worklog, not repeated here as a
new finding, just confirming it reads as intended: a documented mistake with
its cost stated, not a hidden one.

## QUEUE item 16 · Keeper election (DECISIONS.md D-008a)

| Check (from D-008a's ruling text) | Verdict |
|---|---|
| CMP runs before F03 merges | Matches. `run_batch_analysis` now calls `_run_comparisons` before `_run_batch_level_findings("F03", ...)` — read the reordered body of the function directly; the prior order (F03-merge-then-CMP) is gone, not just redescribed in a docstring. |
| F03 takes the election as input, not position-1-by-default | Matches. `f03.detect(frames, keeper_by_group=None)` and the new `build_findings(groups, keeper_by_group)` / `_keeper_for_group` — `detect()`'s registry identity (`detectors.get("F03") is f03.detect`) is preserved because the new parameter is optional and defaults to full fallback, confirmed by reading `tests/test_f03_safety_copies.py`'s registration test still passing unmodified. |
| Fallback is first-frame, and disclosed | Matches. A group absent from `keeper_by_group` (including `keeper_by_group=None` entirely) elects `group[0]` and the Finding's description appends `" (keeper fallback-elected: position 1 - CMP did not rule on this run)"` — verified the exact string is asserted in three separate tests (`test_f03_build_findings_falls_back_to_first_frame_for_a_run_missing_from_the_mapping`, `test_f03_safety_copies_no_keeper_context_falls_back_and_discloses_it`, `test_run_batch_analysis_f03_falls_back_to_first_frame_when_cmp_fails`), not asserted once and assumed everywhere. |
| Copy Finding names the elected keeper | Matches, unchanged mechanism — the f-string still embeds `keeper!r`, confirmed by reading `build_findings` directly; only *which* keeper changed. |
| Tests cover CMP-elected keeper, including a position-1 overturn, and the fallback | Matches, and the overturn test is the actual capstone case, not an invented one: `test_run_batch_analysis_cmp_overturns_position_1` uses `docs/capstone-vienna-report.md`'s own frame IDs (`10_IMG_0961`, `11_IMG_0962`) and its own recorded winner (`11_IMG_0962`, position 2) — cross-checked against the capstone doc's group listing directly rather than trusting the test's own docstring citation. |

One correctness point checked rather than assumed: `_keeper_for_group`
trusts `keeper_by_group`'s value to be a member of the group without
re-validating it locally. This is safe only because CMP's own
`winning_frame_id` field is JSON-Schema-`enum`-constrained to the exact
frame IDs sent for that group (critic-004 verified this structurally, this
session re-confirmed `cmp.py`'s schema construction is unchanged in this
diff) — so a CMP-elected keeper can never actually be foreign to its group
in production. Worth naming because it is exactly the kind of assumption
that would be a real bug if the upstream guarantee ever moved; today it
holds.

## TAXONOMY.md v1.2 (DECISIONS.md D-009) — owner edit, not agent work

Confirmed by reading the full diff directly: every change is an added
`- **Fixability:**` bullet, one per F-item; no existing Detection,
Correction, Reinforcement, Rule, or Profile-note text differs by a single
character before and after (diff hunks show pure additions, no `-` lines
inside any pre-existing bullet). F05's Fixability correctly reads
`conditional` with the `bowing`/`off_center_drift` sub-pattern vocabulary
named inline, matching D-009's ruling. This is an owner commit (git author
is the human, not an agent session) — consistent with D-009's own framing
("the owner may version it post-experiment") and does not implicate the
"TAXONOMY.md is frozen and read-only" standing rule, which binds agent
sessions. No objection; nothing for CRITIC to flag here.

Operational note for the next BUILDER session, not a taxonomy defect:
QUEUE.md item 18 is still marked `[blocked: owner's TAXONOMY.md v1.2
commit]`, and that commit has now landed (`50a80f8`'s predecessor,
`e2e085a`..v1.2 content is actually in this same range — the v1.2 bump
itself is part of this diff). The blocker text in QUEUE.md item 18 was not
updated to reflect this; item 18 reads as still-blocked but its stated
precondition is satisfied. Not a DECISIONS.md-worthy ambiguity (QUEUE.md
items aren't frozen the way TAXONOMY.md is, and CLAUDE.md gives BUILDER,
not CRITIC, the QUEUE-editing role) — flagging only so the next BUILDER
session doesn't skip item 18 on a stale reading of its own bracket.

## Still open from prior reviews, untouched by this diff

- F09's center-third subject proxy — still not touched, still an accepted,
  disclosed proxy (critic-002's original standard).
- F14 stays a `DetectorNotImplemented` stub, per D-007.

## Test suite

Ran directly this session (`uv run pytest -q`), not taken from either
worklog's own report: **283 collected, 282 passed, 1 failed** — 15.06s.

The one failure is `test_every_id_has_detector_and_named_test`
(`missing_test = ['F14']`), the same guard D-007's ruling intends to stand
red for the remainder of the experiment. builder-017's worklog is the
first to describe this precisely — a hard `FAILED`, not an `xfail` —
correcting builder-016's and critic-004's looser "1 expected fail"
phrasing; this session's own run confirms builder-017's correction is
accurate, not overstated. QUEUE.md item 19(d) (adding the
`xfail(strict=True, ...)` marker so the suite's own summary line stops
reading as a real failure) has been added to QUEUE.md's text by the owner
(`50a80f8`) but not yet implemented in code — `grep`ed `tests/` for
`xfail` and found none. Not a regression; the next BUILDER session's
straightforward next step.

## DECISIONS.md

Not adding an entry this session. Open count unchanged at 0
(D-001–D-009 all `RULED`). Nothing in this diff surfaced a genuine
unresolved question — item 15's judgment calls (F01: disclose vs.
recalibrate) and item 16's mechanics were both specific enough in
QUEUE.md/D-008a to execute without one, and this review's own read agrees
that was the right call in both cases.
