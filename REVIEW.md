# REVIEW — critic-001, 2026-08-09

Scope: no prior CRITIC commit exists, so this covers the full diff from repo
inception through `17ae14c` (HEAD) — builder-001 (schema, `fae7457`) and
builder-002 (detector registry, `d8c4ecd`), i.e. QUEUE.md Stage 1 items 1–2.

Per CLAUDE.md's CRITIC instruction: for each taxonomy ID, does the detector
implement the actual described failure, or a plausible substitute?

## Headline finding

**No taxonomy ID has a detector yet.** All 20 modules under
`src/picstory/detectors/` (`f01`–`f15`, `s01`–`s04`, `r01`) are registry
stubs: each claims its ID's slot via `@register(...)` and its `detect()`
unconditionally raises `DetectorNotImplemented`. None contain detection
logic — no EXIF read, no pixel analysis, no API call, no comparison against
the item's Detection text. There is nothing yet to classify as "actual
failure" versus "plausible substitute," because there is no behavior to
classify. This is expected at this point in QUEUE.md (items 3–4, the
detectors with real logic, haven't started) and is accurately represented
in both builder worklogs and in the stub docstrings/exception messages
themselves — the code does not claim more than it does.

Per-ID status, all 20: **stub only**, `DetectorNotImplemented` on every
call. `test_every_id_has_detector_and_named_test` fails as designed
(`missing_test` lists all 20; `missing_detector` is empty) — this is the
coverage guard correctly refusing to go green on names alone, matching
CLAUDE.md's explicit "a stub returning nothing is not an implementation."
25/26 tests pass, 1 expected fail, consistent with both builder worklogs.

## What does exist: schema + registry, checked against TAXONOMY.md

These two pieces don't detect anything, but they encode structural claims
about the taxonomy that can already be checked for drift:

- `Finding.taxonomy_id` accepts the 20 frozen IDs or `"unclassified"`, and
  requires a non-empty `description` exactly when `unclassified` — matches
  TAXONOMY.md §U's "either a taxonomy ID or `unclassified` + description."
- `Pick.reasons` restricted to S-items, `Pick.disqualifiers` restricted to
  F-items — matches TAXONOMY.md's "Strengths ... as the 'why it's
  share-worthy' one-liners; failure modes as disqualifiers."
- `Habit.taxonomy_id` restricted to F- or S-items, R01 explicitly excluded
  — matches §R's framing of R01 as a conditional rule ("triggered by
  shooting conditions, not detected in frames"), not a recurring habit.
- `taxonomy_ids()` parses `### ([FSR]\d{2})` headings from TAXONOMY.md
  directly rather than hardcoding a second list — correctly yields 20 (15 F
  + 4 S + 1 R), matching the file's own stated item count. CMP and §U carry
  no ID and are correctly left out of this set.
- Detector registry (`base.py`): one slot per ID, duplicate registration
  rejected, `registered_ids() == taxonomy_ids()` — no ID silently dropped,
  no invented ID silently added. Mechanically sound; carries no detection
  opinion of its own, by design (builder-002 worklog is explicit about
  this).

No drift found between these structural pieces and TAXONOMY.md. This part
of the build is honest about what it is: plumbing, not detection.

## Forward-looking note (not a finding — nothing to verify against yet)

QUEUE.md item 4 groups S03 (Tight framing) with the judgment-dependent,
API-vision-call detectors. TAXONOMY.md's Detection text for S03 is "the
tightest frame of a subject among its batch-mates" — a relative comparison
across near-duplicate frames, which reads as more computable (subject
fill-ratio / framing-tightness comparison) than judgment-dependent in the
way F04's face-stretch or F06's edge-intrusion calls are. This is worth
watching when item 4 actually lands: if S03 ships as a generic vision-model
call rather than a comparative metric, that would be exactly the kind of
substitute PREDICTION.md names ("the judgement-dependent ones get ... a
model call with a vague prompt"). Not a finding now — there's no S03 logic
yet to judge — flagged so the next CRITIC pass checks it specifically
against TAXONOMY.md's actual wording rather than against QUEUE.md's
grouping.

## DECISIONS.md

Not adding an entry this session. Nothing found rises to "unimplementable
item" or a question needing a human ruling — the gap is sequencing (items
3–6 not started), not a taxonomy/implementation mismatch. Open count
unchanged at 2 (D-003, D-004), below the halt threshold.
