# builder-014 — 2026-08-12

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 13/20 builder sessions
  used (this session is the 14th), hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (critic-003, covers through builder-010 / `7136ac1`,
  predates builder-011 through builder-013 and this session). Its two open
  notes (F09's center-third proxy, r01.py's stale citation) are both
  untouched by this session's work — neither file was in scope.
- `DECISIONS.md`: open count 0 at session start. D-007 (opened by
  builder-013, same day) already carries an owner ruling dated 12 Aug
  2026 — visible in the file at session start, not something this session
  ruled on. No new entries opened this session.
- Most recent `logs/` entry: `builder-013.md`, confirmed via file listing
  (`builder-013.md` highest-numbered; this session writes `builder-014.md`).
- Branch: designated branch `claude/brave-clarke-yf3qxb` already existed on
  `origin`, HEAD (`64cdec3`, the D-007 ruling commit) — continued directly
  on it, no fresh branch needed.

## What moved
D-007's ruling (already in `DECISIONS.md` at session start, commit
`64cdec3`) authorized two things: implement S03 via subject clustering
(modified option (a), scoped small), leave F14 stubbed for the rest of the
experiment. This session implemented the S03 half; F14 was intentionally
left alone (its own precondition — location clustering — is out of scope
per the ruling's own text).

1. **`src/picstory/detectors/_imaging.py`**: added `sharp_area_fraction`, a
   new general-purpose primitive (no taxonomy opinion, matching this
   module's existing convention) — the area share of the largest
   4-connected "sharp" tile blob, scored via localized Laplacian energy
   relative to the frame's own median tile energy (a `min_energy_floor`
   guards flat images from spurious relative-threshold triggering).
   Prototyped interactively before committing to constants: verified it's
   monotonic in synthetic subject-size sweeps from 20 to 120 (of a 200px
   frame) and documented its known breakdown at the extreme where the
   subject nearly fills the frame (no flat-background majority left to set
   a baseline against) — same disclosure pattern F07's MIN/MAX_AREA_SHARE
   bounds already use for its own extremes.
2. **`src/picstory/detectors/subject_clusters.py`** (new): D-007's ruling
   verbatim — "a looser Hamming threshold than F03's, no focal-length or
   timestamp gates" over the same dHash primitive F03 uses. Own constant
   (`HASH_DISTANCE_THRESHOLD = 15`), calibrated by hand against F03's own
   checkerboard+moving-block scene generator (prototyped interactively,
   not guessed): a 15%-of-frame-width subject shift scores 14 (already
   above F03's own threshold of 6, so F03 would reject it as "a real
   variation" — exactly the case S03 wants to admit as "a different
   attempt at the same subject"); a 50%-shift scores 20 (clearly a
   different composition). 15 sits between the two and — checked directly
   against the specific three-frame fixture the tests use — avoids
   chaining an unrelated third frame in through an intermediate one, the
   same transitivity risk critic-003 flagged for F03's own grouping.
   `group_subject_clusters` compares every pair in the batch (not just
   consecutive, unlike F03 — "batch-mates" isn't an adjacency relationship)
   via union-find, returning connected components of size >= 2.
3. **`src/picstory/detectors/s03.py`**: replaced the D-005 stub. `detect()`
   takes `list[Frame]` (batch-level, mirroring F03's shape), groups via
   `subject_clusters.group_subject_clusters`, and within each cluster picks
   the frame with the highest `_framing_tightness` (`sharp_area_fraction`
   on the downsampled luminance) as the S03 winner — ties keep cluster
   (batch) order, since `max()` returns the first maximal element. Returns
   `{frame_id: Finding}` for winners only, matching F03's "absent, not a
   negative Finding" convention.
4. **`scripts/analyze.py`**: added `"S03"` to `_NOT_PER_FRAME` (now
   `{R01, F03, S03}`); updated the module docstring, `evaluable_ids`'s
   docstring, and the CLI report line to explain S03's exclusion the same
   way F03's already was.
5. **`scripts/analyze_batch.py`**: generalized `_run_f03` into
   `_run_batch_level_findings(taxonomy_id, frames, detector_lookup)` (same
   three-way stub/error/success classification, now shared rather than
   F03-specific) and factored the per-frame merge loop into
   `_merge_batch_level_findings`, used for both F03 and S03 —
   avoids duplicating the ~15-line merge block a second time. `S03` now
   runs once per batch, right after F03, before ranking/habit, so an S03
   finding counts toward its frame's score exactly like any other S-item.
   Updated the module docstring accordingly (no behavior change to F03's
   own wiring, only the shared extraction).
6. **`src/picstory/detectors/f14.py`**: docstring updated to cite D-007 (not
   the now-superseded D-005) as the standing ruling — F14 stays stubbed for
   the remainder of the experiment, its own precondition (location
   clustering) out of scope. **`f03.py`**/**`f13.py`**: cross-references to
   "F14/S03 (D-005)" updated to point at D-007 / `detectors.s03` where S03
   is now real, since D-005 no longer accurately describes S03's status.
7. **`QUEUE.md`**: added item 14 (`[agent-proposed]`), documenting this
   work in the same style builder-013 used for R01's item 13.
8. **Tests**: `tests/test_s03_tight_framing.py` (new, 12): subject-cluster
   grouping (admits a shift F03 would reject, rejects a clearly different
   scene, no chaining through an intermediate frame, ignores focal-length
   and timestamp gates unlike F03, no group below 2 frames, non-adjacent
   frames can still cluster) and `detect()` (winner is the largest
   sharp-area frame in its cluster, three-way ranking, no finding for a
   frame with no batch-mate, empty batch, registration). Every distance/
   threshold claim in the module docstrings and this worklog was checked
   by running the actual functions against the actual fixtures before
   being written down, not asserted from memory.
   `tests/test_detector_registry.py`'s `_STILL_STUBBED` set: `{F14, S03}` →
   `{F14}`. `tests/test_vision_detectors.py`'s docstring: updated to stop
   grouping S03 with F14 (S03 is no longer a single-photo-stage gap).
   `tests/test_cli_analyze.py`: `evaluable_ids()` assertions extended to
   include S03's exclusion, count 18 → 17.
   `tests/test_cli_analyze_batch.py`: `_lookup`'s default table gained a
   `"S03": _no_s03_findings` entry (needed — `run_batch_analysis` now calls
   `detector_lookup("S03")` unconditionally, same as F03/R01, so every
   existing test using the fake lookup would otherwise `KeyError`); two
   assertions updated for S03 always running now (`{"F06","F07","F03"}` →
   `+ "S03"`; `"2 detected, 4 clean..."` → `"2 detected, 6 clean..."`).

## DECISIONS.md
No new entries. D-007 already ruled at session start; this session
implemented its S03 half without hitting a further ambiguity that would
need its own human ruling — the specific threshold/metric calibration
choices were checked empirically against the fixtures (see "What moved"),
not left as open questions. Open count: 0 (unchanged).

## Test count
266 collected: 265 passed, 1 failed
(`test_every_id_has_detector_and_named_test`, `missing_test = [F14]` — down
from `[F14, S03]`, and per D-007's ruling this is now the **documented,
intended end state** of this guard for the remainder of the experiment, not
a "land it later" gap). Full suite run directly (`uv run pytest -q`),
~1.5s — no network-dependent tests touched this session (S03 has no vision/
network dependency; confirmed no live Anthropic calls by first attempting a
full offline smoke run through `analyze_batch.run_batch_analysis` with the
*real* unfaked registry, which hung on a live vision-detector network call
as expected — killed it, then re-ran restricted to the local-only detector
IDs, which completed instantly and correctly flagged the largest-subject
frame as S03's winner across 5 synthetic photos). Growth: 254 → 266 (+12,
all from `test_s03_tight_framing.py`).

## What's open
- REVIEW.md's F09 center-third-proxy note: still open, still untouched.
- `r01.py`'s previously-flagged stale citation: resolved by builder-013,
  confirmed still resolved (untouched this session).
- F14 stays a `DetectorNotImplemented` stub, per D-007's ruling, standing
  for the remainder of the experiment.
- This session made no Anthropic API calls (S03 has no vision/network
  dependency) — no fixture files touched.
- DECISIONS.md open count: 0.

## Files touched
`QUEUE.md`, `scripts/analyze.py`, `scripts/analyze_batch.py`,
`src/picstory/detectors/_imaging.py`, `src/picstory/detectors/f03.py`,
`src/picstory/detectors/f13.py`, `src/picstory/detectors/f14.py`,
`src/picstory/detectors/s03.py`,
`src/picstory/detectors/subject_clusters.py` (new),
`tests/test_cli_analyze.py`, `tests/test_cli_analyze_batch.py`,
`tests/test_detector_registry.py`, `tests/test_s03_tight_framing.py` (new),
`tests/test_vision_detectors.py`.
