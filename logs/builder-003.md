# builder-003 — 2026-08-10

## Role
BUILDER.

## Start-of-session checks
- `uv run python scripts/check_hard_stop.py`: OK — 2/20 builder sessions used, hard date 2026-08-22.
- `HALT.md`: absent.
- `REVIEW.md`: present (`critic-001`) — no findings requiring action; confirmed
  no taxonomy/implementation drift in the schema+registry work to date.
  Flagged one forward-looking watch item for S03 (item 4, not this session).
- `DECISIONS.md`: open count 2 (D-003, D-004) — unchanged, below the 5-item
  halt threshold.
- Most recent `logs/` entry: `critic-001.md`.
- **Branch note:** this session's designated branch
  (`claude/brave-clarke-wr60b9`) carried only the already-merged critic-001
  PR (#3, merged into `main` as `f1c3ef4`). Per the platform instructions for
  a merged designated branch, restarted it from `origin/main` before doing
  any new work; no unmerged commits existed to preserve.

## What moved
Implemented QUEUE.md Stage 1, item 3 — the seven local (metadata/pixel)
detectors: F01, F02, F07, F08, F09, F10, F12. All operate on real EXIF and
pixel data, no stubs, no model calls (those are item 4).

- `src/picstory/frame.py` — `Frame` (rgb array + flattened EXIF + luminance
  property) and `load_frame()`, decoding a photo once so item 3's seven
  detectors share the same input shape rather than each re-reading the file.
  This settles the detector call signature left open by `base.py`:
  `detect(frame: Frame) -> Finding | None`.
- `src/picstory/detectors/_imaging.py` — shared, taxonomy-agnostic pixel
  math: Sobel gradients, Laplacian/sharpness score, longest-true-run (1-D),
  largest-connected-area (2-D, for contiguous-region checks), block
  downsampling for speed on full-size photos. No detection opinions live
  here; that's the per-ID modules.
- Per-detector logic, each with its own calibration reasoning in its
  docstring:
  - **F01** digital-zoom softness: EXIF `DigitalZoomRatio` > 1.0 **and**
    Laplacian-variance sharpness below a threshold calibrated against
    synthetic sharp/blurred fixtures. Deliberately narrower than
    TAXONOMY.md's "metadata **or** rendering" wording — see "Scope note"
    below; this is not a DECISIONS.md item, it's a documented implementation
    boundary within an honestly-implemented half of the detection text.
  - **F02** lens/grip obstruction: per-edge strips, dark+locally-flat pixel
    mask, flags when the longest contiguous obstructed run along one edge
    covers ≥25% of that edge's length.
  - **F07** empty-space overallocation: coarse-grid per-tile luminance
    variance, flags the largest *connected* low-variance region when it
    covers 30-85% of the frame (contiguity check, not a bare flat-pixel
    percentage — see module docstring for why that distinction matters).
  - **F08** keystoning: Sobel-derived per-pixel edge tilt from vertical,
    linear regression of tilt vs. normalized x-position. Flags on a
    positive slope (converging verticals) above a calibrated threshold, and
    is verified (via a dedicated test) to *not* fire on uniform camera roll
    (same tilt at every x - a level problem, not keystoning). Sign
    convention and thresholds calibrated against a synthetic two-edge
    generator; see the module docstring for the full derivation.
  - **F09** underexposed subject: center-third vs. border-ring luminance,
    converted to approximate linear light (gamma 2.2) before computing the
    stop difference, so "a stop or more dark" is a real log2 luminance-ratio
    check rather than a raw 8-bit delta.
  - **F10** blown highlights: per-channel ≥250 clip mask, coarse-grid
    connected-blob check (distinguishes a real blown light source/sky from
    scattered specular glints, which shouldn't fire this).
  - **F12** haze/flat contrast: 5th-95th percentile luminance range below a
    threshold - percentile spread rather than raw std, so a single small
    saturated highlight doesn't mask an otherwise flat/hazy frame.
- `tests/test_local_detectors.py` — 18 tests, two (positive/negative) per ID
  plus one wiring test, named `test_f01_..` through `test_f12_..` per
  `test_taxonomy_coverage.py`'s naming convention. All built from synthetic
  pixel arrays (checkerboards, box-blurred variants, analytic converging-edge
  images, uniform blocks) except one F01 test that round-trips a real
  written-then-loaded image file to exercise `frame.load_frame`'s EXIF
  wiring end to end. F08 specifically tests the roll-vs-keystoning
  distinction (module docstring's central design claim) rather than just a
  single positive/negative pair.
- `tests/test_detector_registry.py` — updated
  `test_unimplemented_stub_raises_not_implemented` to check only the 13 IDs
  still pending (item 4's API-vision detectors, plus F03 which is Stage 2
  item 8). It previously iterated all 20 and would now fail for the seven
  real detectors, which correctly no longer raise `DetectorNotImplemented`.
- `pyproject.toml` / `uv.lock` — added `pillow` and `numpy` as runtime
  dependencies (image decode/EXIF, pixel arrays). A `uv add`, i.e. a package
  install - allowed under CLAUDE.md's network rule; no other network access
  used or needed.

## Scope note: F01's "metadata or rendering" gap
TAXONOMY.md's F01 detection text offers two alternative signals ("focal
length metadata **or** rendering consistent with digital zoom"). This
detector implements only the metadata-confirmed half: `DigitalZoomRatio`
present and >1 **and** the frame renders soft. The pure-rendering
alternative - recognizing digital-zoom upsampling artifacts from pixels
alone, with no metadata support - would need to distinguish upsampling
blur from ordinary optical/motion blur, which is a materially harder
computer-vision problem than what's implemented here, and was out of scope
for this session's local-heuristic pass. The docstring states this
explicitly and the detector returns no finding (not a guess) when metadata
is absent, rather than substituting a generic blur check for the missing
signal. Flagging this here for the CRITIC rather than treating it as
silently covered.

## What is open
- QUEUE item 4 (API-vision detectors: F04, F05, F06, F11, F13, F14, F15,
  S01-S04) not started.
- QUEUE item 5 (CLI) and item 6 (formal per-detector test-coverage pass for
  the remaining 13 IDs) not started. This session's tests satisfy item 6's
  naming convention for the 7 IDs done here as a side effect of testing what
  was built, not as a claim that item 6 itself is complete.
- `tests/test_taxonomy_coverage.py::test_every_id_has_detector_and_named_test`
  still fails, expected: `missing_detector` is now empty for all 20 (was
  already true after item 2); `missing_test` now lists only the 13 IDs from
  item 4/item 8, down from 20.
- DECISIONS.md D-003 (taxonomy visibility) and D-004 (pricing) unchanged,
  still open, still non-blocking.

## Test count
44 collected: 43 passed, 1 failed (the coverage guard, expected — down to
13 missing IDs from 20). 26 pre-existing (19 schema + 6 registry + 1
taxonomy-parses) all still pass, unchanged; 18 new in
`tests/test_local_detectors.py`.
