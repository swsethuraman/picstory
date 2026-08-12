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
from the top-ranked frame. The session habit (item 10) runs over the same
final findings: `ranking.compute_habit` sets `AnalysisOutput.habit` to
whichever F- or S-item recurs across the most frames.

CMP (item 11, TAXONOMY.md §CMP) runs last, over the same near-duplicate
groups F03 already identifies (`picstory.detectors.f03.group_near_duplicates`
- a pure local computation, called here directly rather than through F03's
own registered `detect()`, since that returns per-frame Findings, not the
groups themselves). Each group is judged once via `picstory.cmp.compare_group`
(injectable as `cmp_compare`, same test-injection pattern as `detector_lookup`)
and the result appended to `AnalysisOutput.comparisons`. A group whose
comparison call fails (network, spend cap - CLAUDE.md's spending rule: "log
it, move on") is logged as a `ComparisonRun("error", ...)` rather than
crashing the batch, the same non-fatal treatment `_run_f03` already gives a
broken F03 detector.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _report import report  # noqa: E402
from analyze import DetectorRun, evaluable_ids, run_analysis  # noqa: E402

from picstory import cmp, detectors, ranking  # noqa: E402
from picstory.batch import load_batch  # noqa: E402
from picstory.detectors import f03  # noqa: E402
from picstory.detectors.base import DetectorNotImplemented  # noqa: E402
from picstory.frame import Frame  # noqa: E402
from picstory.schema import AnalysisOutput, FrameAnalysis  # noqa: E402


@dataclass(frozen=True)
class ComparisonRun:
    group: list[str]
    status: str  # "compared" | "error"
    detail: str | None


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


def _run_comparisons(
    frames: list[Frame], cmp_compare
) -> tuple[list, list[ComparisonRun]]:
    """Run CMP over every near-duplicate group F03 identifies.

    Returns `(comparisons, comparison_runs)`: `comparisons` are the
    successful `schema.Comparison` results (destined for
    `AnalysisOutput.comparisons`); `comparison_runs` names every attempted
    group's outcome, success or failure, for the report - mirroring
    `DetectorRun`'s detected/stub/error split, but per-group rather than
    per-frame-per-ID since CMP is not a taxonomy-ID detector.
    """
    frames_by_id = {frame.frame_id: frame for frame in frames}
    comparisons = []
    comparison_runs: list[ComparisonRun] = []
    for group_ids in f03.group_near_duplicates(frames):
        group_frames = [frames_by_id[fid] for fid in group_ids]
        try:
            comparison = cmp_compare(group_frames)
        except Exception as exc:  # noqa: BLE001 - a blocked comparison is logged, not fatal
            comparison_runs.append(
                ComparisonRun(group_ids, "error", f"{type(exc).__name__}: {exc}")
            )
            continue
        comparisons.append(comparison)
        comparison_runs.append(
            ComparisonRun(group_ids, "compared", f"winner: {comparison.winner_frame_id}")
        )
    return comparisons, comparison_runs


def run_batch_analysis(
    frames: list[Frame],
    *,
    detector_lookup=detectors.get,
    ids: list[str] | None = None,
    cmp_compare=cmp.compare_group,
) -> tuple[AnalysisOutput, dict[str, list[DetectorRun]], list[ComparisonRun]]:
    """Run Stage 1's per-frame sweep over every frame in a batch, then F03, ranking, and CMP.

    `detector_lookup` is threaded through unchanged so tests can inject a
    fake registry exactly as `test_cli_analyze.py` does for the single-photo
    CLI - no live API key or network needed to exercise this dispatch logic.
    `ids` (default `evaluable_ids()`, which already excludes F03) governs
    only the per-frame sweep; F03 always runs once via `detector_lookup`
    regardless of `ids`, since it is not part of that sweep at all. Ranking
    (item 9) runs next, over the final per-frame findings (F03's merge
    included), so a safety-copy finding counts against its frame's score the
    same as any other F-item would. CMP (item 11) runs last, over F03's own
    near-duplicate groups (`cmp_compare` injected the same way for tests -
    see `_run_comparisons`).
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
    habit = ranking.compute_habit(frame_analyses)
    comparisons, comparison_runs = _run_comparisons(frames, cmp_compare)
    output = AnalysisOutput(frames=frame_analyses, pick=pick, habit=habit, comparisons=comparisons)
    return output, runs_by_frame, comparison_runs


def _counts(runs: list[DetectorRun]) -> dict[str, int]:
    counts = {"detected": 0, "clean": 0, "stub": 0, "error": 0}
    for r in runs:
        counts[r.status] += 1
    return counts


def render_report(
    photos: list[Path],
    output: AnalysisOutput,
    runs_by_frame: dict[str, list[DetectorRun]],
    comparison_runs: list[ComparisonRun] | None = None,
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
        (
            f"habit: {output.habit.taxonomy_id} — {output.habit.description}"
            if output.habit is not None
            else "habit: None (no F- or S-item finding recurred across the batch)"
        ),
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

    lines += ["", "## Comparisons (TAXONOMY.md §CMP, near-duplicate groups only)", ""]
    if not output.comparisons and not comparison_runs:
        lines.append("(no near-duplicate groups in this batch)")
    else:
        for comparison in output.comparisons:
            lines.append(f"- {comparison.group} → winner {comparison.winner_frame_id!r}")
            lines.append(f"  - subject placement: {comparison.subject_placement}")
            lines.append(f"  - edge amputations: {comparison.edge_amputations}")
            lines.append(f"  - incidental distractions: {comparison.incidental_distractions}")
            if comparison.tiebreaker:
                lines.append(f"  - tiebreaker: {comparison.tiebreaker}")
        for comparison_run in comparison_runs or []:
            if comparison_run.status == "error":
                lines.append(f"- {comparison_run.group} → error: {comparison_run.detail}")

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

    output, runs_by_frame, comparison_runs = run_batch_analysis(frames)
    body = render_report(args.photos, output, runs_by_frame, comparison_runs)
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
