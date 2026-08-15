"""CLI: a batch of 5-50 photos in -> per-frame analysis out (QUEUE.md Stage 2, items 7-8).

"Per-frame analysis reusing Stage 1": this does not reimplement per-ID
dispatch/classification. Each frame in the batch is run straight through
`analyze.run_analysis` - the same function, same detected/clean/stub/error
classification, same R01/F03/S03 exclusion from the per-frame sweep - and
the results are collected into one `AnalysisOutput` with one `FrameAnalysis`
per frame.

F03 (near-duplicate grouping, item 8) and S03 (tight framing, DECISIONS.md
D-007) are exactly the detectors that per-frame sweep cannot run - their
Detection text each names a property of a set of frames, not of any one
photo (see `picstory.detectors.f03`'s and `picstory.detectors.s03`'s module
docstrings). This is the first module with an actual batch to give them, so
`run_batch_analysis` runs each once, across the whole ordered batch, after
the per-frame sweep, and merges any resulting findings into their frames'
`FrameAnalysis.findings` via the shared `_run_batch_level_findings`/
`_merge_batch_level_findings` helpers - the same detected/clean/stub/error
classification as every other ID, not a separate code path with different
semantics.

Ranking/shortlist (item 9) is now wired in too: once the per-frame sweep and
F03/S03's merges have produced the batch's final findings, `picstory.ranking`
scores every frame (S-item findings for, F-item findings against - see that
module's docstring for why) and `run_batch_analysis` sets `AnalysisOutput.pick`
from the top-ranked frame. The session habit (item 10) runs over the same
final findings: `ranking.compute_habit` sets `AnalysisOutput.habit` to
whichever F- or S-item recurs across the most frames.

CMP (item 11, TAXONOMY.md §CMP) now runs *before* F03's findings are merged
(DECISIONS.md D-008a), over the same near-duplicate groups F03 already
identifies (`picstory.detectors.f03.group_near_duplicates` - a pure local
computation, called here directly rather than through F03's own registered
`detect()`, since that returns per-frame Findings, not the groups
themselves). Each group is judged once via `picstory.cmp.compare_group`
(injectable as `cmp_compare`, same test-injection pattern as `detector_lookup`)
and the result appended to `AnalysisOutput.comparisons`. A group whose
comparison call fails (network, spend cap - CLAUDE.md's spending rule: "log
it, move on") is logged as a `ComparisonRun("error", ...)` rather than
crashing the batch, the same non-fatal treatment `_run_batch_level_findings`
gives a broken F03/S03 detector.

Per D-008a, CMP's own winner *is* the run's keeper: `_run_comparisons` also
returns `keeper_by_group` (`{tuple(group_ids): winner_frame_id}`, only for
groups CMP actually judged), which is threaded into the F03 finding pass via
`_run_batch_level_findings`'s `extra_kwargs` so `picstory.detectors.f03.detect`
receives it as `keeper_by_group=...`. A run CMP could not judge (error, or
simply missing from the mapping) is absent from `keeper_by_group`, and
`f03.detect` falls back to first-frame election for that run, disclosed in
the resulting Finding's description (see `f03.py`'s own docstring) - exactly
the fallback D-008a's ruling requires, not a silent behavior change.

R01 (item 13, TAXONOMY.md §R) runs after ranking/habit, over the same final
per-frame findings (F03/S03's merges included, same set `ranking.compute_habit`
sees): `picstory.detectors.r01.detect` takes the batch's `FrameAnalysis`
list (not raw frames - R01's trigger is "F12 findings in the batch," a
property of already-computed findings, not something to re-derive from
pixels) and returns a `schema.Rule` once if F12 was found anywhere,
appended to `AnalysisOutput.rules` - a different object on the output from
`frames`/`comparisons`, per TAXONOMY.md's "different object type for the
classifier" framing of §R.

The running profile (item 12, TAXONOMY.md's "The running profile" output row)
is updated once per `main()` run: `picstory.profile.load_profile` reads
whatever this user's machine has recorded so far, `profile.record_session`
folds this batch's final F/S findings (and F06's `edge` sub-pattern, when
present) into it, and `profile.save_profile` persists the result -
`run_batch_analysis` itself stays pure/testable (no I/O), the load/record/
save sequence lives in `main()` alongside the CLI's other side effects (the
`_report.py` write). `render_report` gained a `## Profile` section built
from the already-updated `Profile`, so a batch report shows both this
session's findings and how they fit the user's running pattern.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _report import report  # noqa: E402
from analyze import DetectorRun, evaluable_ids, run_analysis  # noqa: E402

from picstory import cmp, detectors, profile as profile_module, ranking  # noqa: E402
from picstory.batch import load_batch  # noqa: E402
from picstory.detectors import f03, r01  # noqa: E402
from picstory.detectors.base import DetectorNotImplemented  # noqa: E402
from picstory.frame import Frame  # noqa: E402
from picstory.schema import AnalysisOutput, Finding, FrameAnalysis, Rule  # noqa: E402


@dataclass(frozen=True)
class ComparisonRun:
    group: list[str]
    status: str  # "compared" | "error"
    detail: str | None


def _run_batch_level_findings(
    taxonomy_id: str, frames: list[Frame], detector_lookup, extra_kwargs: dict | None = None
) -> tuple[dict[str, Finding], str | None, str | None]:
    """Run one batch-level, dict-of-Findings detector (F03 or S03) once.

    Both take the whole ordered batch and return `{frame_id: Finding}`
    (see f03.py/s03.py's own docstrings for why each is batch-level, not
    per-frame). Returns `(findings_by_frame_id, error_status, error_detail)`
    - `error_status`/`error_detail` are set (and `findings_by_frame_id`
    empty) on "stub"/"error", mirroring `analyze.run_analysis`'s per-ID
    try/except so a batch-level ID gets the same three-way outcome
    (detected/clean vs. stub vs. error) as every ID the per-frame loop
    already classifies.

    `extra_kwargs` (default none) is forwarded to the looked-up `detect`
    call - today only F03 uses this, to pass D-008a's `keeper_by_group`
    election through without changing S03's call shape at all.
    """
    detect = detector_lookup(taxonomy_id)
    try:
        return detect(frames, **(extra_kwargs or {})), None, None
    except DetectorNotImplemented as exc:
        return {}, "stub", str(exc)
    except Exception as exc:  # noqa: BLE001 - a blocked detector is logged, not fatal
        return {}, "error", f"{type(exc).__name__}: {exc}"


def _merge_batch_level_findings(
    taxonomy_id: str,
    findings: dict[str, Finding],
    error_status: str | None,
    error_detail: str | None,
    frame_analyses: list[FrameAnalysis],
    runs_by_frame: dict[str, list[DetectorRun]],
) -> None:
    """Fold one batch-level detector's per-frame outcome into the sweep's results, in place.

    Same detected/clean/stub/error classification `_run_batch_level_findings`
    produces, applied to every frame in the batch (not just the ones with a
    Finding) so a batch-level ID's `DetectorRun` shows up per frame exactly
    like a per-frame ID's does.
    """
    for frame_analysis in frame_analyses:
        if error_status is not None:
            runs_by_frame[frame_analysis.frame_id].append(
                DetectorRun(taxonomy_id, error_status, error_detail)
            )
            continue
        finding = findings.get(frame_analysis.frame_id)
        if finding is None:
            runs_by_frame[frame_analysis.frame_id].append(DetectorRun(taxonomy_id, "clean", None))
        else:
            frame_analysis.findings.append(finding)
            runs_by_frame[frame_analysis.frame_id].append(
                DetectorRun(taxonomy_id, "detected", finding.description)
            )


def _run_comparisons(
    frames: list[Frame], cmp_compare
) -> tuple[list, list[ComparisonRun], dict[tuple[str, ...], str]]:
    """Run CMP over every near-duplicate group F03 identifies.

    Returns `(comparisons, comparison_runs, keeper_by_group)`: `comparisons`
    are the successful `schema.Comparison` results (destined for
    `AnalysisOutput.comparisons`); `comparison_runs` names every attempted
    group's outcome, success or failure, for the report - mirroring
    `DetectorRun`'s detected/stub/error split, but per-group rather than
    per-frame-per-ID since CMP is not a taxonomy-ID detector. `keeper_by_group`
    (D-008a) maps each judged group's frame-id tuple to CMP's own
    `winner_frame_id` - the run's elected keeper; a group whose comparison
    call failed is simply absent, so `picstory.detectors.f03.detect` falls
    back to first-frame election for that run (disclosed there, per D-008a's
    ruling).
    """
    frames_by_id = {frame.frame_id: frame for frame in frames}
    comparisons = []
    comparison_runs: list[ComparisonRun] = []
    keeper_by_group: dict[tuple[str, ...], str] = {}
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
        keeper_by_group[tuple(group_ids)] = comparison.winner_frame_id
    return comparisons, comparison_runs, keeper_by_group


def _run_r01(frame_analyses: list[FrameAnalysis], detector_lookup) -> Rule | None:
    """Run the batch-level R01 rule once, over the batch's final findings.

    Unlike F03/CMP, R01 has no network or spend dependency (it is a pure
    check over already-computed findings - TAXONOMY.md's own trigger
    condition, "F12 findings in the batch") and nothing that plausibly
    raises in normal operation, so there is no stub/error status to
    classify or report here (CLAUDE.md's "log it, move on" rule covers
    spend-cap/network failures, neither of which applies to a local check).
    `detector_lookup` is still threaded through rather than calling
    `picstory.detectors.r01.detect` directly, so tests can inject a fake
    registry the same way they do for every other ID.
    """
    detect_r01 = detector_lookup("R01")
    return detect_r01(frame_analyses)


def run_batch_analysis(
    frames: list[Frame],
    *,
    detector_lookup=detectors.get,
    ids: list[str] | None = None,
    cmp_compare=cmp.compare_group,
) -> tuple[AnalysisOutput, dict[str, list[DetectorRun]], list[ComparisonRun]]:
    """Run Stage 1's per-frame sweep, then CMP, F03/S03, ranking, and R01.

    `detector_lookup` is threaded through unchanged so tests can inject a
    fake registry exactly as `test_cli_analyze.py` does for the single-photo
    CLI - no live API key or network needed to exercise this dispatch logic.
    `ids` (default `evaluable_ids()`, which already excludes F03/S03) governs
    only the per-frame sweep; F03 and S03 each always run once via
    `detector_lookup` regardless of `ids`, since neither is part of that
    sweep at all.

    CMP (item 11) now runs *before* F03's findings are merged (DECISIONS.md
    D-008a: CMP's winner is the run's elected keeper, not "position 1" by
    default) - `_run_comparisons` returns `keeper_by_group` alongside the
    comparisons themselves, and that mapping is handed to F03's detector via
    `_run_batch_level_findings`'s `extra_kwargs`. A run CMP could not judge
    is simply absent from `keeper_by_group`; `picstory.detectors.f03.detect`
    falls back to first-frame election for that run, disclosed in the
    resulting Finding (see f03.py). S03 is unaffected by any of this - its
    own batch-level pass is untouched.

    Ranking (item 9) runs next, over the final per-frame findings (F03/S03's
    merges included), so a safety-copy or tight-framing finding counts
    toward its frame's score the same as any other F-/S-item would. R01
    (item 13) runs last, over the same final findings (see `_run_r01`).
    """
    ids = evaluable_ids() if ids is None else ids
    frame_analyses: list[FrameAnalysis] = []
    runs_by_frame: dict[str, list[DetectorRun]] = {}
    for frame in frames:
        output, runs = run_analysis(frame, detector_lookup=detector_lookup, ids=ids)
        frame_analyses.append(output.frames[0])
        runs_by_frame[frame.frame_id] = runs

    comparisons, comparison_runs, keeper_by_group = _run_comparisons(frames, cmp_compare)

    f03_findings, f03_error_status, f03_error_detail = _run_batch_level_findings(
        "F03", frames, detector_lookup, extra_kwargs={"keeper_by_group": keeper_by_group}
    )
    _merge_batch_level_findings(
        "F03", f03_findings, f03_error_status, f03_error_detail, frame_analyses, runs_by_frame
    )

    s03_findings, s03_error_status, s03_error_detail = _run_batch_level_findings(
        "S03", frames, detector_lookup
    )
    _merge_batch_level_findings(
        "S03", s03_findings, s03_error_status, s03_error_detail, frame_analyses, runs_by_frame
    )

    pick = ranking.build_pick(frame_analyses)
    habit = ranking.compute_habit(frame_analyses)
    rule = _run_r01(frame_analyses, detector_lookup)
    output = AnalysisOutput(
        frames=frame_analyses,
        pick=pick,
        habit=habit,
        comparisons=comparisons,
        rules=[rule] if rule is not None else [],
    )
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
    updated_profile: profile_module.Profile | None = None,
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
            "F03/S03 included, each evaluated once across the batch rather "
            "than per-frame)"
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

    lines += ["", "## Rules (TAXONOMY.md §R, forward-looking advice)", ""]
    if not output.rules:
        lines.append(f"(no rule triggered - no {r01.TRIGGER_ID} finding in this batch)")
    else:
        for rule in output.rules:
            lines.append(f"- {rule.taxonomy_id}: {rule.advice}")

    lines += ["", "## Profile (per-user recurrence across sessions, this session included)", ""]
    if updated_profile is None:
        lines.append("(not recorded)")
    else:
        lines.append(f"sessions recorded: {updated_profile.sessions_recorded}")
        summary = profile_module.summary_lines(updated_profile)
        if summary:
            lines += [f"- {line}" for line in summary]
        else:
            lines.append("- (no F- or S-item finding recorded yet)")

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
    parser.add_argument(
        "--profile-path",
        type=Path,
        default=None,
        help="running profile JSON file (default: PICSTORY_PROFILE_PATH env var, or ~/.picstory/profile.json)",
    )
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

    profile_path = args.profile_path or profile_module.default_profile_path()
    updated_profile = profile_module.record_session(profile_module.load_profile(profile_path), output.frames)
    profile_module.save_profile(updated_profile, profile_path)

    body = render_report(args.photos, output, runs_by_frame, comparison_runs, updated_profile)
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
