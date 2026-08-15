# builder-018 — 2026-08-15

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 17/25 builder sessions
  used (this session is the 18th), hard date 2026-08-29.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-004, covers through builder-015; predates
  builder-016/017's work, nothing in it names this session's scope).
- `DECISIONS.md`: open count 0 at session start (D-001–D-009 all `RULED`).
- Most recent `logs/` entry: `builder-017.md` (item 16, CMP elects the F03
  keeper). Since then, the owner made one commit (`50a80f8`) editing only
  QUEUE.md's item 19(d) text (adding the xfail-marker description) — no
  code changed, no worklog for it (it's an owner edit, not a BUILDER
  session).
- Also since builder-017: TAXONOMY.md v1.2 has been committed by the owner
  (Fixability bullets, D-009). This lifts QUEUE.md item 18's
  `[blocked: owner's TAXONOMY.md v1.2 commit]` tag — but item 18 sits
  *after* item 17 in QUEUE.md, and item 17 (not blocked, not yet
  implemented) is still the top unblocked item, so item 18 is next
  session's concern, not this one's.
- Branch: `claude/epic-meitner-udeqj8`, clean working tree at session
  start, `origin/main` at `50a80f8`.

## What moved
QUEUE.md item 17, "Habit and ranking calibration per D-008c and D-008b" —
the top unblocked item. Implemented against both rulings' text directly in
`src/picstory/ranking.py`:

- **17(b), ranking (D-008b):** `rank_frames`'s sort key is now
  `(score_frame(fa), len(S-items))`, both descending — at equal score, more
  named S-item strengths ranks first; a genuine tie on both keeps batch
  order (Python's `sorted` stability, unchanged mechanism).
- **17(a), habit (D-008c):** added `PERVASIVE_THRESHOLD = 2/3` (named,
  documented constant) and `pervasive_ids()` (F/S items firing on more than
  that share of the batch's frames). `compute_habit` now excludes
  `pervasive_ids` before picking the most-recurrent remaining F/S item;
  everything else (frame-not-finding counting, R01/unclassified exclusion,
  ascending-ID tie-break) is unchanged. `pervasive_note()` gives the
  one-line, non-discarding session note the ruling requires ("This batch,
  throughout (excluded from habit selection): ..."), wired into
  `scripts/analyze_batch.py`'s `render_report` right after the habit line,
  only when non-empty.

**The calibration fixture surfaced a real discrepancy, not implemented
around.** D-008c's ruling and QUEUE item 17(a) both name the required
calibration outcome: "F05/F06/F11 must classify pervasive and F08 must win
the habit." I counted `docs/capstone-vienna-report.md`'s own `[detected]`
lines directly (id by id; the counts sum to the report's own header total
of 150 detections across 31 frames, so the count is verified, not
eyeballed): F05=28, F06=27, F11=25 — all correctly pervasive. But the next
count down is S01 at 20/31 (64.5%), *under* `PERVASIVE_THRESHOLD` (66.7%),
not F08 (13/31). Applying the ruling's own mechanism to the ruling's own
cited evidence gives S01 as the habit, not F08 — D-008c's narrative
separately (and inconsistently with the report) cites "F08, 9 frames," and
never mentions S01 at all despite it being the batch's second-highest
count. I did not force the fixture to assert F08 — that would be answering
the discrepancy myself rather than logging it. Implemented the mechanism
exactly as ruled, wrote the calibration test
(`test_capstone_calibration_pervasiveness_and_actual_habit_winner` in
`tests/test_ranking.py`) to assert what that mechanism honestly produces
(pervasive = F05/F06/F11, habit = S01), and filed **DECISIONS.md D-010**
with the full count-by-count evidence, asking the owner to confirm whether
S01 is the correct calibration target or something else is meant. Open
count: 0 → 1.

**Tests** (13 new, all passing):
- `tests/test_ranking.py` (+11): D-008b's two tie-break cases (S-count
  breaks a batch-order-would-be-wrong tie; genuine tie on both score and
  S-count still keeps batch order); `PERVASIVE_THRESHOLD` value;
  `pervasive_ids` (empty batch, exactly-at-threshold is not pervasive,
  sorted output); `pervasive_note` (`None` vs. one-line); `compute_habit`
  excludes a pervasive raw-count winner and falls through to the next
  eligible ID, and returns `None` when everything recurring is pervasive;
  the capstone calibration fixture above.
- `tests/test_cli_analyze_batch.py` (+2): `render_report` includes the
  pervasive-note line when an ID clears the threshold, and omits it
  entirely when nothing does.
- Five **existing** habit tests in both files needed fixture changes, not
  logic changes: at 2 frames, an ID firing on "both" is 2/2 = 100%,
  trivially pervasive under the new rule, which broke tests whose actual
  intent was just "recurs on more than one frame." Each was widened to 3
  frames (or given a second disqualifier) so the ID under test sits at or
  below 2/3 and the original assertions hold for the reason they always
  claimed to, not by accident. Documented inline at each site rather than
  left as unexplained churn.

## DECISIONS.md
One new entry, D-010 (open) — see "What moved" above for the full
evidence and reasoning. Open count: 1. This is not a blocking count (halt
is at 5), so no further action this session; next BUILDER/CRITIC session
should re-check it before starting.

## Test count
308 collected: 307 passed, 1 failed
(`test_every_id_has_detector_and_named_test`, `missing_test = [F14]` — the
documented, intended end state of the coverage guard per D-007's ruling,
pre-existing and untouched by this session's diff; QUEUE.md item 19(d)
names the follow-up `xfail` marker but that's a separate, not-yet-actioned
hygiene item). Growth this session: 295 → 308 (+13), all new, all green.
Full suite run directly (`uv run pytest -q`), ~15s.

## What's open
- **DECISIONS.md D-010** (new, open) — needs the owner's ruling on the
  habit calibration fixture's actual expected winner (S01 per the honest
  count, vs. the ruling's stated F08).
- QUEUE.md item 18, Fixability parsing per D-009 — TAXONOMY.md v1.2 has
  landed (its blocker is lifted), so this is next in line once item 17 is
  done, which it now is.
- QUEUE.md item 19, the hygiene sweep — (a), (b), (c) untouched; (d) (the
  xfail marker for `test_every_id_has_detector_and_named_test`) has its
  QUEUE.md description written by the owner but no code change yet — still
  a hard `FAILED`, not an `xfail`.
- No Anthropic API calls made this session — item 17's work is entirely
  local (arithmetic over already-computed findings, no network).

## Files touched
`src/picstory/ranking.py`, `scripts/analyze_batch.py`,
`tests/test_ranking.py`, `tests/test_cli_analyze_batch.py`,
`DECISIONS.md`, `logs/builder-018.md` (this file).
