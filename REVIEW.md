# REVIEW — critic-002, 2026-08-10

Scope: diff from `fa60c8c` (critic-001, HEAD at the time `17ae14c`) through
`1a78643` (HEAD now) — builder-003 (local detectors, `0e5586a`), builder-004
(API-vision detectors, `49aca72`), builder-005 (CLI, `bf19f87`), and
builder-006 (D-006 follow-through: live-key resolution + recorded vision
fixtures, `08ee5bb`/`09badc5`). QUEUE.md Stage 1 items 3–6 (partially) and the
D-006 ruling.

Per CLAUDE.md's CRITIC instruction: for each taxonomy ID, does the detector
implement the actual described failure, or a plausible substitute?

## Headline finding

**No plausible-substitute pattern found.** This is the first session with
real detection logic, and it's the session PREDICTION.md's first prediction
is specifically about ("the judgement-dependent ones get stubs, generic
language, or a model call with a vague prompt"). Checked against that bar
directly:

- The 9 vision-call detectors (F04, F05, F06, F11, F13, F15, S01, S02, S04)
  all route through one shared `_vision.judge()`, but the prompt it builds is
  **not** generic — it embeds each item's actual Detection text, read
  verbatim from TAXONOMY.md via `schema.taxonomy_detection_text()` (not a
  hand-copied paraphrase that could drift), and forces structured tool output
  that echoes the taxonomy ID (`_vision._verdict_from_tool_input` rejects a
  mismatched ID). That is exactly what CLAUDE.md's API-discipline rule asks
  for, and exactly what it contrasts against ("a generic 'critique this
  photo' prompt is the substitute"). `tests/test_vision_detectors.py` has a
  parametrized check per ID confirming the real Detection text (not a
  paraphrase) is what actually gets sent — this is enforced, not just
  asserted in a docstring.
- The 7 local pixel/metadata detectors (F01, F02, F07, F08, F09, F10, F12) go
  further than "computable" — several specifically encode the distinguishing
  clause in their item's Detection text rather than a looser proxy for the
  general shape of the problem. Two examples worth naming: F08 separates
  keystoning (position-dependent convergence) from a uniformly rolled camera
  (position-independent tilt) via a slope-vs-x-position regression, matching
  TAXONOMY.md's "parallel lines converging" wording rather than "any vertical
  line looks tilted"; F10 requires a *connected* clipped region, not just an
  area-fraction of near-white pixels, so scattered specular glints (chrome,
  water) don't trip a detector meant for "featureless blobs." Both have tests
  asserting the discriminating case specifically (`test_f08_..._clean_on_uniform_roll_not_convergence`,
  `test_f10_..._clean_on_scattered_specular_glints`).

Per-ID status for everything touched this diff:

| ID | Kind | Verdict |
|---|---|---|
| F01 | local | Matches — requires *both* `DigitalZoomRatio>1` (the literal metadata signal) and low Laplacian-variance sharpness; doesn't guess from softness alone. |
| F02 | local (single-frame subset) | Matches the single-frame half honestly. TAXONOMY.md's "typically consistent across consecutive frames" is a secondary/supporting clause ("typically"), not the defining condition — the defining condition ("dark, out-of-focus mass along a frame edge") is genuinely single-frame, and the docstring says plainly that the cross-frame check is out of scope until Stage 2. Not the same shape of gap as F14/S03 (see below), and correctly not deferred. |
| F07 | local | Matches — uses largest-*connected*-region, not raw featureless-pixel fraction, matching "30-50% of the frame given to featureless area" (a zone, not scattered flat pixels). |
| F08 | local | Matches, and does the hard part: distinguishes convergence from roll via regression slope, not just "are verticals tilted." |
| F09 | local (documented proxy) | Partial substitute, but an honest one. No face detector is available, so "the subject" is approximated as the center third of the frame. This means a dark building or object centered against a bright sky could also trip F09, which is not what "person in the foreground" describes. The docstring states this proxy plainly rather than implying real subject detection — flagging for awareness, not as an undisclosed substitute. Worth a sharper subject region (or explicit "no person detector available" caveat surfaced in output) if F09 starts firing on non-portrait frames in practice. |
| F10 | local | Matches — connected-blob requirement, per-channel clip check (not luminance-only), same contiguity reasoning as F07. |
| F12 | local | Matches — explicitly measures tonal spread (5th-95th percentile) rather than edge sharpness, matching the taxonomy's own "sharpening does not help" tell that this is a contrast problem, not a focus one. |
| F04, F05, F06, F11, F15, S01, S02, S04 | vision-call | Match — each Detection text names a genuinely judgment-dependent visual condition (stretching, curved lines, "center chosen, edges unchosen," in-focus bystanders, focal-spot competition, "meaningfully placed," blue-hour color/light, saturated-object-against-quiet-field), and the shared plumbing sends that exact text with a schema-forced verdict tied to the ID. No generic aesthetic-critique substitute found. |
| F13 | vision-call (documented per-frame reading) | Matches on a defensible reading. Detection text is "Large subject with nothing indicating its size; the set reads as 'one idea repeated' ...". The operative, decidable-per-frame clause is the first one (no scale reference for a large subject); "the set reads as..." is described in `f13.py`'s docstring as the batch-level *consequence* of that per-frame gap recurring, not a separate multi-frame precondition — unlike F14 ("a location's *coverage* is all establishing views", true only of a set) or S03 ("the tightest frame... *among its batch-mates*", explicitly comparative). This distinction holds up on a close read of the three Detection texts side by side. Correctly not bundled into D-005's deferral, and correctly not given its own DECISIONS.md entry — this is a documented interpretation, not an unresolved ambiguity. |
| F14, S03 | stub, deferred | Correct call, and the right kind of stub. Both Detection texts are genuinely undecidable from one frame (D-005). Left as `DetectorNotImplemented` rather than a plausible single-frame proxy — which is the substitute PREDICTION.md and CLAUDE.md both warn about, and which critic-001 flagged in advance specifically for S03. Confirmed by reading both current stub docstrings: neither quietly returns a negative or answers an easier question. |

## One inherited inaccuracy, out of this diff's scope but worth flagging now

`src/picstory/detectors/r01.py` (unchanged since builder-002, `d8c4ecd` —
before critic-001's pass, and not touched by this diff) says R01's "real
detection logic... lands in QUEUE.md item 3." That's wrong on inspection:
QUEUE.md item 3's list (F01, F09/F10, F02, F12, F07, F08) does not include
R01, and R01's own Detection text ("triggered by shooting conditions,
detected via F12 findings **in the batch**") is a batch-level trigger — it
needs the same Stage 2 batching that F14/S03 are correctly waiting for, not
a Stage 1 single-frame implementation. If a future BUILDER session trusts
this docstring's citation at face value, it risks building R01 as a
single-frame check the same way F14/S03 almost were before D-005 caught it.
Not opening a DECISIONS.md entry for this — it's a stale comment, not an
ambiguity needing a ruling — but flagging so the next session that touches
R01 corrects the citation and treats it as Stage-2-dependent from the start.

## D-006 follow-through (builder-006)

Did what the ruling asked, precisely: confirmed `PICSTORY_VISION_KEY` (not
`ANTHROPIC_API_KEY`) is the visible variable, updated `default_caller()` to
prefer it, made 4 live calls, and replaced the hand-authored "happy path"
fixture with genuine recorded-response replays
(`test_parse_tool_use_response_replays_genuine_recorded_api_call`). Coverage
is honestly partial — only F13 and S01 have live recordings; the other 7
vision IDs still rest on hand-authored malformed-shape tests only, and
builder-006's worklog says so directly rather than implying broader
coverage. No taxonomy-match concern here (this is fixture/test
infrastructure, not detection logic), noted for completeness since it was
the largest single piece of this diff by DECISIONS.md follow-through.

## DECISIONS.md

Not adding an entry this session. Open count unchanged at 0 (D-001–D-006 all
`RULED`). Nothing found rises to "unimplementable item" — F09's proxy
limitation and R01's stale citation are both disclosed/inspectable gaps in
already-landed work, not blocking ambiguities needing a human ruling.

## Test suite

101 collected, 100 passed, 1 expected fail
(`test_every_id_has_detector_and_named_test`, `missing_test = [F03, F14, R01,
S03]` — matches builder-006's own count and the documented Stage 2/D-005
deferrals). Verified by running the suite directly this session, not just
reading the worklog's claim.
