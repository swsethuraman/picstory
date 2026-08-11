"""CLI: one photo in -> full per-detector analysis out (QUEUE.md Stage 1, item 5).

Runs every evaluable taxonomy detector against a single photo and writes the
full per-ID breakdown through `_report.py` (CLAUDE.md's output-discipline
rule): full body to outputs/reports/, at most three lines to stdout.

R01 and F03 are excluded from the per-frame sweep. R01: TAXONOMY.md's R
section frames it as "triggered by shooting conditions, not detected in
frames" - a batch/conditional rule, not a per-photo detector. This is the
same reasoning schema.py's `Habit` already encodes (R01 is explicitly
barred from Habit.taxonomy_id). F03: its Detection text ("2-5 consecutive
frames ... no change in position, focal length, or angle") names a property
of a run of frames, not of any one photo - `picstory.detectors.f03.detect`
requires a `batch` kwarg no single-frame call here can supply. Both are
genuinely implemented (F03 for real, as of QUEUE.md item 8; R01 still a
stub) - the exclusion is structural, not "pending work," so running either
through the same "stub" bucket as F14/S03 would misrepresent that.
`scripts/analyze_batch.py` runs F03 for real at the batch level, once it
has the frame list this module's one-photo-at-a-time signature never has.

`pick` and `habit` on the output are left `None`. Per schema.py's own
docstring, both are batch-level (populated from Stage 2 onward, QUEUE.md
items 9-10) - a single Stage 1 photo has no batch to rank a pick against or
recur a habit across. Setting either here would invent batch semantics this
run doesn't have, overriding an already-settled, CRITIC-reviewed design
decision from item 1 without a DECISIONS.md entry to justify the change.

Each detector call is classified into exactly one of four outcomes:
- detected: a Finding came back - included in the output's findings.
- clean:    the detector ran and found nothing.
- stub:     DetectorNotImplemented - QUEUE.md sequencing, not a run-time
            failure (e.g. F14/S03 pending Stage 2, DECISIONS.md D-005).
- error:    the detector raised anything else - a vision call failing for
            lack of ANTHROPIC_API_KEY, a spend cap, or a network problem.
            Per CLAUDE.md's spending rule ("if the cap is hit ... treat
            that as a blocked item, log it, move on"), this is logged and
            does not stop the run.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _report import report  # noqa: E402

from picstory import detectors  # noqa: E402
from picstory.detectors.base import DetectorNotImplemented  # noqa: E402
from picstory.frame import Frame, load_frame  # noqa: E402
from picstory.schema import AnalysisOutput, Finding, FrameAnalysis, taxonomy_ids  # noqa: E402

# Batch/conditional, not a per-frame detector - see module docstring.
_NOT_PER_FRAME = frozenset({"R01", "F03"})


@dataclass(frozen=True)
class DetectorRun:
    taxonomy_id: str
    status: str  # "detected" | "clean" | "stub" | "error"
    detail: str | None  # finding description, or the stub/error message


def evaluable_ids() -> list[str]:
    """Taxonomy IDs this CLI sweeps per-frame: every ID except R01 and F03."""
    return sorted(taxonomy_ids() - _NOT_PER_FRAME)


def classify_call(taxonomy_id: str, call) -> tuple[Finding | None, DetectorRun]:
    """Run one detector call and classify it into detected/clean/stub/error.

    Factored out of `run_analysis` so `scripts/analyze_batch.py` can reuse
    the exact same classification for F03's batch-level call (which needs a
    `batch=` kwarg `run_analysis`'s per-frame `detect(frame)` call can't
    supply) without duplicating the detected/clean/stub/error rules.
    """
    try:
        finding = call()
    except DetectorNotImplemented as exc:
        return None, DetectorRun(taxonomy_id, "stub", str(exc))
    except Exception as exc:  # noqa: BLE001 - a blocked detector is logged, not fatal
        return None, DetectorRun(taxonomy_id, "error", f"{type(exc).__name__}: {exc}")
    if finding is None:
        return None, DetectorRun(taxonomy_id, "clean", None)
    return finding, DetectorRun(taxonomy_id, "detected", finding.description)


def run_analysis(
    frame: Frame,
    *,
    detector_lookup=detectors.get,
    ids: list[str] | None = None,
) -> tuple[AnalysisOutput, list[DetectorRun]]:
    """Run every evaluable detector against one frame.

    `detector_lookup` defaults to the real registry; tests inject a fake
    mapping (same injection pattern as `_vision.VisionCaller`) so the CLI's
    per-ID dispatch/classification logic is exercised without a live API
    key or network - CLAUDE.md requires the test suite to run offline.
    """
    ids = evaluable_ids() if ids is None else ids
    findings: list[Finding] = []
    runs: list[DetectorRun] = []
    for taxonomy_id in ids:
        detect = detector_lookup(taxonomy_id)
        finding, run = classify_call(taxonomy_id, lambda detect=detect: detect(frame))
        runs.append(run)
        if finding is not None:
            findings.append(finding)

    output = AnalysisOutput(frames=[FrameAnalysis(frame_id=frame.frame_id, findings=findings)])
    return output, runs


def _counts(runs: list[DetectorRun]) -> dict[str, int]:
    counts = {"detected": 0, "clean": 0, "stub": 0, "error": 0}
    for r in runs:
        counts[r.status] += 1
    return counts


def render_report(photo: Path, frame: Frame, output: AnalysisOutput, runs: list[DetectorRun]) -> str:
    counts = _counts(runs)
    lines = [
        f"# analyze: {photo}",
        "",
        f"frame_id: {frame.frame_id}",
        f"schema_version: {output.schema_version}",
        (
            f"{counts['detected']} detected, {counts['clean']} clean, "
            f"{counts['stub']} stub, {counts['error']} error "
            f"(of {len(runs)} evaluable IDs; R01 excluded - batch/conditional, "
            "not a per-frame detector)"
        ),
        "",
        "pick: None, habit: None - both are batch-level (schema.py: "
        '"populated from Stage 2 onward"); a single Stage 1 photo has no '
        "batch to compute either against.",
        "",
        "## Per-ID results",
        "",
    ]
    for r in sorted(runs, key=lambda r: r.taxonomy_id):
        detail = f" — {r.detail}" if r.detail else ""
        lines.append(f"- {r.taxonomy_id} [{r.status}]{detail}")

    lines += ["", "## AnalysisOutput JSON", "", "```json", output.to_json(), "```"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("photo", type=Path, help="path to one photo")
    args = parser.parse_args(argv)

    try:
        frame = load_frame(args.photo)
    except Exception as exc:  # noqa: BLE001 - fatal and reportable, unlike a per-detector error
        report(
            "analyze",
            f"# analyze: {args.photo}\n\nfailed to load frame: {type(exc).__name__}: {exc}\n",
            f"analyze failed: could not load {args.photo}",
            passed=False,
        )
        return 1

    output, runs = run_analysis(frame)
    body = render_report(args.photo, frame, output, runs)
    counts = _counts(runs)
    summary = (
        f"analyzed {frame.frame_id}: {counts['detected']} detected, "
        f"{counts['clean']} clean, {counts['stub']} stub, {counts['error']} error"
    )
    report("analyze", body, summary, passed=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
