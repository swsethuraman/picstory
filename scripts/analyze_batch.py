"""CLI: a batch of 5-50 photos in -> per-frame analysis out (QUEUE.md Stage 2, item 7).

"Per-frame analysis reusing Stage 1": this does not reimplement per-ID
dispatch/classification. Each frame in the batch is run straight through
`analyze.run_analysis` - the same function, same detected/clean/stub/error
classification, same R01 exclusion - and the results are collected into one
`AnalysisOutput` with one `FrameAnalysis` per frame.

What this queue item is *not*: near-duplicate grouping (F03, item 8),
ranking/shortlist (item 9), and the session habit (item 10) are separate,
later queue items. `pick` and `habit` stay `None` on the output for the same
reason `scripts/analyze.py` leaves them `None` - nothing in this item
computes either.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _report import report  # noqa: E402
from analyze import DetectorRun, evaluable_ids, run_analysis  # noqa: E402

from picstory import detectors  # noqa: E402
from picstory.batch import load_batch  # noqa: E402
from picstory.frame import Frame  # noqa: E402
from picstory.schema import AnalysisOutput, FrameAnalysis  # noqa: E402


def run_batch_analysis(
    frames: list[Frame],
    *,
    detector_lookup=detectors.get,
    ids: list[str] | None = None,
) -> tuple[AnalysisOutput, dict[str, list[DetectorRun]]]:
    """Run Stage 1's per-frame sweep over every frame in a batch.

    `detector_lookup` is threaded through unchanged so tests can inject a
    fake registry exactly as `test_cli_analyze.py` does for the single-photo
    CLI - no live API key or network needed to exercise this dispatch logic.
    """
    ids = evaluable_ids() if ids is None else ids
    frame_analyses: list[FrameAnalysis] = []
    runs_by_frame: dict[str, list[DetectorRun]] = {}
    for frame in frames:
        output, runs = run_analysis(frame, detector_lookup=detector_lookup, ids=ids)
        frame_analyses.append(output.frames[0])
        runs_by_frame[frame.frame_id] = runs
    return AnalysisOutput(frames=frame_analyses), runs_by_frame


def _counts(runs: list[DetectorRun]) -> dict[str, int]:
    counts = {"detected": 0, "clean": 0, "stub": 0, "error": 0}
    for r in runs:
        counts[r.status] += 1
    return counts


def render_report(
    photos: list[Path],
    output: AnalysisOutput,
    runs_by_frame: dict[str, list[DetectorRun]],
) -> str:
    all_runs = [r for runs in runs_by_frame.values() for r in runs]
    counts = _counts(all_runs)
    ids_per_frame = len(next(iter(runs_by_frame.values()), []))
    lines = [
        f"# analyze_batch: {len(photos)} photos",
        "",
        f"schema_version: {output.schema_version}",
        (
            f"{counts['detected']} detected, {counts['clean']} clean, "
            f"{counts['stub']} stub, {counts['error']} error "
            f"across {len(output.frames)} frames x {ids_per_frame} evaluable IDs "
            "each (R01 excluded - batch/conditional, not a per-frame detector)"
        ),
        "",
        "pick: None, habit: None - not computed by this queue item (near-duplicate "
        "grouping is item 8, ranking is item 9, the session habit is item 10).",
        "",
        "## Per-frame results",
        "",
    ]
    for frame_analysis in output.frames:
        runs = runs_by_frame[frame_analysis.frame_id]
        fcounts = _counts(runs)
        lines.append(
            f"### {frame_analysis.frame_id}: {fcounts['detected']} detected, "
            f"{fcounts['clean']} clean, {fcounts['stub']} stub, {fcounts['error']} error"
        )
        for r in sorted(runs, key=lambda r: r.taxonomy_id):
            detail = f" — {r.detail}" if r.detail else ""
            lines.append(f"- {r.taxonomy_id} [{r.status}]{detail}")
        lines.append("")

    lines += ["## AnalysisOutput JSON", "", "```json", output.to_json(), "```"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("photos", type=Path, nargs="+", help="5-50 photo paths")
    args = parser.parse_args(argv)

    try:
        frames = load_batch(args.photos)
    except Exception as exc:  # noqa: BLE001 - fatal and reportable, unlike a per-detector error
        report(
            "analyze_batch",
            f"# analyze_batch: {len(args.photos)} photos\n\n"
            f"failed to load batch: {type(exc).__name__}: {exc}\n",
            f"analyze_batch failed: {type(exc).__name__}: {exc}",
            passed=False,
        )
        return 1

    output, runs_by_frame = run_batch_analysis(frames)
    body = render_report(args.photos, output, runs_by_frame)
    all_runs = [r for runs in runs_by_frame.values() for r in runs]
    counts = _counts(all_runs)
    summary = (
        f"analyzed {len(frames)} frames: {counts['detected']} detected, "
        f"{counts['clean']} clean, {counts['stub']} stub, {counts['error']} error"
    )
    report("analyze_batch", body, summary, passed=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
