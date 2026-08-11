"""CLI: a batch of 5-50 photos in -> per-frame analysis out (QUEUE.md Stage 2, items 7-8).

"Per-frame analysis reusing Stage 1": this does not reimplement per-ID
dispatch/classification. Each frame in the batch is run straight through
`analyze.run_analysis` - the same function, same detected/clean/stub/error
classification, same R01/F03 exclusion from the per-frame sweep - and the
results are collected into one `AnalysisOutput` with one `FrameAnalysis`
per frame.

F03 (near-duplicate grouping, item 8) is exactly the detector that per-frame
sweep cannot run - its Detection text names "consecutive frames," a batch
property (see `picstory.detectors.f03`'s module docstring). This is the
first module with an actual batch to give it, so `run_batch_analysis` runs
it once, across the whole ordered batch, after the per-frame sweep, and
merges any resulting findings into their frames' `FrameAnalysis.findings` -
the same detected/clean/stub/error classification as every other ID, not a
separate code path with different semantics.

Ranking/shortlist (item 9) is now wired in too: once the per-frame sweep and
F03's merge have produced the batch's final findings, `picstory.ranking`
scores every frame (S-item findings for, F-item findings against - see that
module's docstring for why) and `run_batch_analysis` sets `AnalysisOutput.pick`
from the top-ranked frame. The session habit (item 10) is still a separate,
later queue item; `habit` stays `None` on the output for the same reason
`scripts/analyze.py` leaves it `None` - nothing in this item computes it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _report import report  # noqa: E402
from analyze import DetectorRun, evaluable_ids, run_analysis  # noqa: E402

from picstory import detectors, ranking  # noqa: E402
from picstory.batch import load_batch  # noqa: E402
from picstory.detectors.base import DetectorNotImplemented  # noqa: E402
from picstory.frame import Frame  # noqa: E402
from picstory.schema import AnalysisOutput, FrameAnalysis  # noqa: E402


def _run_f03(
    frames: list[Frame], detector_lookup
) -> tuple[dict[str, object], str | None, str | None]:
    """Run the batch-level F03 detector once; classify like any other ID.

    Returns `(findings_by_frame_id, error_status, error_detail)`.
    `error_status`/`error_detail` are set (and `findings_by_frame_id` empty)
    on "stub"/"error", mirroring `analyze.run_analysis`'s per-ID try/except
    so F03 gets the same three-way outcome (detected/clean vs. stub vs.
    error) as every ID the per-frame loop already classifies.
    """
    detect_f03 = detector_lookup("F03")
    try:
        return detect_f03(frames), None, None
    except DetectorNotImplemented as exc:
        return {}, "stub", str(exc)
    except Exception as exc:  # noqa: BLE001 - a blocked detector is logged, not fatal
        return {}, "error", f"{type(exc).__name__}: {exc}"


def run_batch_analysis(
    frames: list[Frame],
    *,
    detector_lookup=detectors.get,
    ids: list[str] | None = None,
) -> tuple[AnalysisOutput, dict[str, list[DetectorRun]]]:
    """Run Stage 1's per-frame sweep over every frame in a batch, then F03, then ranking.

    `detector_lookup` is threaded through unchanged so tests can inject a
    fake registry exactly as `test_cli_analyze.py` does for the single-photo
    CLI - no live API key or network needed to exercise this dispatch logic.
    `ids` (default `evaluable_ids()`, which already excludes F03) governs
    only the per-frame sweep; F03 always runs once via `detector_lookup`
    regardless of `ids`, since it is not part of that sweep at all. Ranking
    (item 9) runs last, over the final per-frame findings (F03's merge
    included), so a safety-copy finding counts against its frame's score the
    same as any other F-item would.
    """
    ids = evaluable_ids() if ids is None else ids
    frame_analyses: list[FrameAnalysis] = []
    runs_by_frame: dict[str, list[DetectorRun]] = {}
    for frame in frames:
        output, runs = run_analysis(frame, detector_lookup=detector_lookup, ids=ids)
        frame_analyses.append(output.frames[0])
        runs_by_frame[frame.frame_id] = runs

    f03_findings, f03_error_status, f03_error_detail = _run_f03(frames, detector_lookup)
    for frame_analysis in frame_analyses:
        if f03_error_status is not None:
            runs_by_frame[frame_analysis.frame_id].append(
                DetectorRun("F03", f03_error_status, f03_error_detail)
            )
            continue
        finding = f03_findings.get(frame_analysis.frame_id)
        if finding is None:
            runs_by_frame[frame_analysis.frame_id].append(DetectorRun("F03", "clean", None))
        else:
            frame_analysis.findings.append(finding)
            runs_by_frame[frame_analysis.frame_id].append(
                DetectorRun("F03", "detected", finding.description)
            )

    pick = ranking.build_pick(frame_analyses)
    return AnalysisOutput(frames=frame_analyses, pick=pick), runs_by_frame


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
            "each (R01 excluded - batch/conditional, not a per-frame detector; "
            "F03 included, evaluated once across the batch rather than per-frame)"
        ),
        "",
        "habit: None - not computed by this queue item (session habit is item 10).",
        "",
        "## Shortlist (ranked, best score first; ties keep batch order)",
        "",
    ]
    for rank_position, frame_analysis in enumerate(ranking.rank_frames(output.frames), start=1):
        lines.append(
            f"{rank_position}. {frame_analysis.frame_id} "
            f"(score {ranking.score_frame(frame_analysis)})"
        )

    lines += ["", "## Pick", ""]
    if output.pick is None:
        lines.append("pick: None (empty batch)")
    else:
        lines.append(f"frame_id: {output.pick.frame_id}")
        lines.append(f"disqualifiers (F-items still present): {output.pick.disqualifiers or 'none'}")
        lines.append("share list:")
        share_lines = ranking.share_list_lines(output.pick)
        if share_lines:
            for share_line in share_lines:
                lines.append(f"- {share_line}")
        else:
            lines.append("- (no S-item findings on the pick)")

    lines += ["", "## Per-frame results", ""]
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
