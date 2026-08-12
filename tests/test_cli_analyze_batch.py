"""Behavior tests for scripts/analyze_batch.py (QUEUE.md Stage 2, items 7-8,
and Stage 3 item 11's CMP wiring).

Same import-shim and detector-injection pattern as test_cli_analyze.py:
`analyze_batch.py` lives under scripts/, and `run_batch_analysis` takes a
`detector_lookup` so these tests never touch the real (network-calling)
vision detectors - CLAUDE.md requires the test suite to run offline. F03's
and S03's real batch-level logic are pure local computations (no network),
so their own behavior is tested directly in test_f03_safety_copies.py and
test_s03_tight_framing.py; here they are mostly stubbed to `{}` (no
findings) so tests that only care about the per-frame sweep aren't coupled
to either one's actual grouping decisions.

`_frame()` gives every frame a distinct EXIF `FocalLength`, which is enough
on its own to break `detectors.f03.group_near_duplicates`'s pairwise check
(see f03.py: a focal-length mismatch between two frames blocks a match
outright, regardless of pixel content) - `run_batch_analysis` calls that
*real* grouping function directly to find CMP's near-duplicate groups
(item 11), independent of the `detector_lookup` fake above, so without this
the identical all-zero pixel frames these tests already use would silently
group and exercise `cmp_compare`'s real default (`picstory.cmp.compare_group`,
a live API call) in every test below that doesn't otherwise care about CMP.
Tests that *do* want a near-duplicate group construct frames with matching
FocalLength explicitly (see the CMP section).
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import analyze_batch  # noqa: E402

from picstory.batch import MIN_BATCH_SIZE, load_batch  # noqa: E402
from picstory.detectors import r01  # noqa: E402
from picstory.detectors.base import DetectorNotImplemented  # noqa: E402
from picstory.frame import Frame  # noqa: E402
from picstory.profile import Profile, record_session  # noqa: E402
from picstory.schema import Comparison, Finding, taxonomy_correction_text, taxonomy_rule_text  # noqa: E402

_focal_lengths = itertools.count(1)


def _frame(frame_id: str, *, focal_length: float | None = None) -> Frame:
    import numpy as np

    if focal_length is None:
        focal_length = float(next(_focal_lengths)) * 10.0
    exif = {} if focal_length is None else {"FocalLength": focal_length}
    return Frame(frame_id=frame_id, path=Path("."), rgb=np.zeros((4, 4, 3), dtype="uint8"), exif=exif)


def _no_f03_findings(frames):
    return {}


def _no_s03_findings(frames):
    return {}


def _no_r01_rule(frame_analyses):
    return None


def _lookup(table: dict[str, object]):
    table = {"F03": _no_f03_findings, "S03": _no_s03_findings, "R01": _no_r01_rule, **table}
    return lambda taxonomy_id: table[taxonomy_id]


def _no_comparisons(frames):
    raise AssertionError(
        "cmp_compare should not be called - this test's frames are not near-duplicates "
        "(see _frame()'s distinct-FocalLength docstring note)"
    )


# --- run_batch_analysis(): reuses analyze.run_analysis per frame ----------


def test_run_batch_analysis_aggregates_one_frame_analysis_per_frame() -> None:
    def detected(frame):
        return Finding(taxonomy_id="F06", description=f"edge intrusion in {frame.frame_id}")

    def clean(frame):
        return None

    lookup = _lookup({"F06": detected, "F07": clean})
    frames = [_frame("00_a"), _frame("01_b"), _frame("02_c")]

    output, runs_by_frame, _comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F06", "F07"]
    )

    assert [fa.frame_id for fa in output.frames] == ["00_a", "01_b", "02_c"]
    assert set(runs_by_frame) == {"00_a", "01_b", "02_c"}
    for frame_id in runs_by_frame:
        # F03/S03 always run too (see module docstring) even though `ids`
        # here only names F06/F07 - `ids` governs the per-frame sweep, not
        # F03/S03.
        assert {r.taxonomy_id for r in runs_by_frame[frame_id]} == {"F06", "F07", "F03", "S03"}


def test_run_batch_analysis_findings_stay_scoped_to_their_own_frame() -> None:
    def detected(frame):
        # Only fires for one specific frame, like a real per-frame detector.
        return Finding(taxonomy_id="F06", description="edge") if frame.frame_id == "01_b" else None

    lookup = _lookup({"F06": detected})
    frames = [_frame("00_a"), _frame("01_b"), _frame("02_c")]

    output, _runs, _comparison_runs = analyze_batch.run_batch_analysis(frames, detector_lookup=lookup, ids=["F06"])

    by_id = {fa.frame_id: fa for fa in output.frames}
    assert by_id["00_a"].findings == []
    assert [f.taxonomy_id for f in by_id["01_b"].findings] == ["F06"]
    assert by_id["02_c"].findings == []


def test_run_batch_analysis_habit_none_when_nothing_recurs() -> None:
    """A batch with zero F/S findings has nothing to name a habit from."""
    lookup = _lookup({"F07": lambda frame: None})
    output, _runs, _comparison_runs = analyze_batch.run_batch_analysis(
        [_frame("00_a")], detector_lookup=lookup, ids=["F07"]
    )
    assert output.habit is None
    assert output.pick is not None
    assert output.pick.frame_id == "00_a"
    assert output.pick.reasons == []
    assert output.pick.disqualifiers == []


def test_run_batch_analysis_habit_is_most_recurrent_f_or_s_item() -> None:
    def detected(frame):
        return Finding(taxonomy_id="F06", description="edge")

    lookup = _lookup({"F06": detected, "F07": lambda frame: None})
    frames = [_frame("00_a"), _frame("01_b"), _frame("02_c")]

    output, _runs, _comparison_runs = analyze_batch.run_batch_analysis(frames, detector_lookup=lookup, ids=["F06", "F07"])

    assert output.habit is not None
    assert output.habit.taxonomy_id == "F06"
    assert output.habit.description == taxonomy_correction_text("F06")


def test_run_batch_analysis_habit_counts_f03_merged_findings() -> None:
    """The habit runs over the batch's *final* findings, F03's merge included."""

    def f03_findings(frames):
        return {f.frame_id: Finding(taxonomy_id="F03", description="safety copy") for f in frames}

    lookup = _lookup({"F03": f03_findings, "F07": lambda frame: None})
    frames = [_frame("00_a"), _frame("01_b")]

    output, _runs, _comparison_runs = analyze_batch.run_batch_analysis(frames, detector_lookup=lookup, ids=["F07"])

    assert output.habit is not None
    assert output.habit.taxonomy_id == "F03"


# --- run_batch_analysis(): F03's batch-level pass (item 8) -----------------


def test_run_batch_analysis_merges_f03_findings_into_flagged_frames_only() -> None:
    def f03_findings(frames):
        # Mirrors picstory.detectors.f03.detect's shape: only the flagged
        # (non-keeper) frame_ids appear in the returned mapping.
        return {"01_b": Finding(taxonomy_id="F03", description="safety copy of '00_a'")}

    lookup = _lookup({"F07": lambda frame: None, "F03": f03_findings})
    frames = [_frame("00_a"), _frame("01_b"), _frame("02_c")]

    output, runs_by_frame, _comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F07"]
    )

    by_id = {fa.frame_id: fa for fa in output.frames}
    assert by_id["00_a"].findings == []
    assert [f.taxonomy_id for f in by_id["01_b"].findings] == ["F03"]
    assert by_id["02_c"].findings == []

    f03_runs = {
        frame_id: [r for r in runs if r.taxonomy_id == "F03"][0]
        for frame_id, runs in runs_by_frame.items()
    }
    assert f03_runs["00_a"].status == "clean"
    assert f03_runs["01_b"].status == "detected"
    assert f03_runs["02_c"].status == "clean"


def test_run_batch_analysis_classifies_f03_stub_like_a_per_frame_stub() -> None:
    def f03_stub(frames):
        raise DetectorNotImplemented("not yet")

    lookup = _lookup({"F07": lambda frame: None, "F03": f03_stub})
    frames = [_frame("00_a"), _frame("01_b")]

    _output, runs_by_frame, _comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F07"]
    )

    for frame_id in ("00_a", "01_b"):
        f03_run = [r for r in runs_by_frame[frame_id] if r.taxonomy_id == "F03"][0]
        assert f03_run.status == "stub"


def test_run_batch_analysis_classifies_f03_error_like_a_per_frame_error() -> None:
    def f03_broken(frames):
        raise RuntimeError("boom")

    lookup = _lookup({"F07": lambda frame: None, "F03": f03_broken})
    frames = [_frame("00_a"), _frame("01_b")]

    _output, runs_by_frame, _comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F07"]
    )

    for frame_id in ("00_a", "01_b"):
        f03_run = [r for r in runs_by_frame[frame_id] if r.taxonomy_id == "F03"][0]
        assert f03_run.status == "error"
        assert "boom" in f03_run.detail


# --- run_batch_analysis(): ranking + pick (item 9) -------------------------


def test_run_batch_analysis_picks_the_highest_scoring_frame() -> None:
    def by_frame(findings: dict[str, str]):
        return lambda frame: (
            Finding(taxonomy_id=findings[frame.frame_id], description="x")
            if frame.frame_id in findings
            else None
        )

    lookup = _lookup(
        {
            # 00_a: no findings (score 0). 01_b: one S-item (score 1).
            # 02_c: two F-items (score -2).
            "S01": by_frame({"01_b": "S01"}),
            "F06": by_frame({"02_c": "F06"}),
            "F07": by_frame({"02_c": "F07"}),
        }
    )
    frames = [_frame("00_a"), _frame("01_b"), _frame("02_c")]

    output, _runs, _comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["S01", "F06", "F07"]
    )

    assert output.pick.frame_id == "01_b"
    assert output.pick.reasons == ["S01"]
    assert output.pick.disqualifiers == []


def test_run_batch_analysis_pick_disqualifiers_include_the_pick_s_own_f03_finding() -> None:
    """F03's batch-level merge happens before ranking, so it counts like any other F-item."""

    def f03_findings(frames):
        return {"00_a": Finding(taxonomy_id="F03", description="safety copy of '01_b'")}

    lookup = _lookup({"F07": lambda frame: None, "F03": f03_findings})
    frames = [_frame("00_a"), _frame("01_b")]

    output, _runs, _comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F07"]
    )

    # 00_a scores -1 (its own F03 finding); 01_b scores 0 (clean) and wins.
    assert output.pick.frame_id == "01_b"
    assert output.pick.disqualifiers == []


def test_run_batch_analysis_pick_ties_keep_batch_order() -> None:
    lookup = _lookup({"F07": lambda frame: None})
    frames = [_frame("00_a"), _frame("01_b"), _frame("02_c")]

    output, _runs, _comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F07"]
    )

    assert output.pick.frame_id == "00_a"


# --- run_batch_analysis(): CMP over near-duplicate groups (item 11) -------


def test_run_batch_analysis_no_comparisons_when_no_near_duplicates() -> None:
    """Distinct-FocalLength frames (the module default) never group - cmp_compare unused."""
    lookup = _lookup({"F07": lambda frame: None})
    frames = [_frame("00_a"), _frame("01_b"), _frame("02_c")]

    output, _runs, comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F07"], cmp_compare=_no_comparisons
    )

    assert output.comparisons == []
    assert comparison_runs == []


def test_run_batch_analysis_compares_a_near_duplicate_group() -> None:
    lookup = _lookup({"F07": lambda frame: None})
    frames = [
        _frame("00_a", focal_length=24.0),
        _frame("01_b", focal_length=24.0),
        _frame("02_c"),  # distinct focal length - not part of the group
    ]

    def fake_compare(group_frames):
        assert [f.frame_id for f in group_frames] == ["00_a", "01_b"]
        return Comparison(
            group=[f.frame_id for f in group_frames],
            winner_frame_id="01_b",
            subject_placement="00_a centers the tower; 01_b drifts left of center",
            edge_amputations="00_a clips the flag at the top edge; 01_b doesn't",
            incidental_distractions="a cyclist enters frame in 01_b",
            tiebreaker="the cyclist mid-pedal reads as a moment, not a record shot",
        )

    output, _runs, comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F07"], cmp_compare=fake_compare
    )

    assert len(output.comparisons) == 1
    assert output.comparisons[0].winner_frame_id == "01_b"
    assert output.comparisons[0].group == ["00_a", "01_b"]
    assert len(comparison_runs) == 1
    assert comparison_runs[0].status == "compared"
    assert comparison_runs[0].group == ["00_a", "01_b"]


def test_run_batch_analysis_comparison_failure_is_logged_not_fatal() -> None:
    """CLAUDE.md's spending rule: a blocked/failed call is logged and the run moves on."""
    lookup = _lookup({"F07": lambda frame: None})
    frames = [_frame("00_a", focal_length=24.0), _frame("01_b", focal_length=24.0)]

    def broken_compare(group_frames):
        raise RuntimeError("spend cap hit")

    output, _runs, comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F07"], cmp_compare=broken_compare
    )

    assert output.comparisons == []  # no crash, no partial/fabricated result
    assert len(comparison_runs) == 1
    assert comparison_runs[0].status == "error"
    assert "spend cap hit" in comparison_runs[0].detail


# --- run_batch_analysis(): R01, the haze rule (item 13) --------------------


def test_run_batch_analysis_no_rule_when_no_f12_finding() -> None:
    lookup = _lookup({"F07": lambda frame: None})
    frames = [_frame("00_a"), _frame("01_b")]

    output, _runs, _comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F07"]
    )

    assert output.rules == []


def test_run_batch_analysis_r01_triggers_on_f12_finding_anywhere_in_batch() -> None:
    # Overrides the default no-op "R01" fake with the real detector, so this
    # exercises `_run_r01` actually receiving the per-frame sweep's F12
    # finding, not just a stub that would return None regardless.
    def f12_on_second_frame(frame):
        return Finding(taxonomy_id="F12", description="hazy") if frame.frame_id == "01_b" else None

    lookup = _lookup({"F12": f12_on_second_frame, "F07": lambda frame: None, "R01": r01.detect})
    frames = [_frame("00_a"), _frame("01_b")]

    output, _runs, _comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F12", "F07"]
    )

    assert len(output.rules) == 1
    assert output.rules[0].taxonomy_id == "R01"


def test_run_batch_analysis_r01_uses_the_real_registered_detector_by_default() -> None:
    # `run_batch_analysis`'s default `detector_lookup` is the real registry
    # (`picstory.detectors.get`), not a test double - pins that R01 is wired
    # up end to end, not only reachable through the fake-lookup tests above.
    # `_frame()`'s all-zero pixel data is itself flat/hazy by F12's own
    # metric (zero luminance spread), so the real F12 detector genuinely
    # fires here and R01 should trigger off it - not a contrived double.
    frames = [_frame("00_a"), _frame("01_b"), _frame("02_c")]

    output, _runs, _comparison_runs = analyze_batch.run_batch_analysis(frames)

    assert len(output.rules) == 1
    assert output.rules[0].taxonomy_id == "R01"


# --- render_report(): per-frame sections and aggregate counts -------------


def test_render_report_includes_per_frame_sections_and_totals() -> None:
    def detected(frame):
        return Finding(taxonomy_id="F06", description="edge intrusion")

    lookup = _lookup({"F06": detected, "F07": lambda frame: None})
    frames = [_frame("00_a"), _frame("01_b")]
    output, runs_by_frame, _comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F06", "F07"]
    )
    body = analyze_batch.render_report(
        [Path("a.jpg"), Path("b.jpg")], output, runs_by_frame
    )

    # F06 detected x2 + F07 clean x2 + F03 clean x2 + S03 clean x2 (both stubbed to no findings).
    assert "2 detected, 6 clean, 0 stub, 0 error" in body
    assert "### 00_a:" in body
    assert "### 01_b:" in body
    assert "- F06 [detected] — edge intrusion" in body
    assert f"habit: F06 — {taxonomy_correction_text('F06')}" in body
    # Both frames carry the same F06 finding and tie on score -1; the tie
    # keeps batch order, so 00_a (first) is the pick.
    assert "1. 00_a (score -1)" in body
    assert "2. 01_b (score -1)" in body
    assert "frame_id: 00_a" in body
    assert "disqualifiers (F-items still present): ['F06']" in body
    assert "(no near-duplicate groups in this batch)" in body


def test_render_report_includes_comparison_section() -> None:
    lookup = _lookup({"F07": lambda frame: None})
    frames = [_frame("00_a", focal_length=24.0), _frame("01_b", focal_length=24.0)]

    def fake_compare(group_frames):
        return Comparison(
            group=["00_a", "01_b"],
            winner_frame_id="01_b",
            subject_placement="centered vs. off-center",
            edge_amputations="flag clipped in 00_a",
            incidental_distractions="cyclist in 01_b",
        )

    output, runs_by_frame, comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F07"], cmp_compare=fake_compare
    )
    body = analyze_batch.render_report(
        [Path("a.jpg"), Path("b.jpg")], output, runs_by_frame, comparison_runs
    )

    assert "['00_a', '01_b'] → winner '01_b'" in body
    assert "subject placement: centered vs. off-center" in body
    assert "edge amputations: flag clipped in 00_a" in body
    assert "incidental distractions: cyclist in 01_b" in body


def test_render_report_includes_comparison_error() -> None:
    lookup = _lookup({"F07": lambda frame: None})
    frames = [_frame("00_a", focal_length=24.0), _frame("01_b", focal_length=24.0)]

    def broken_compare(group_frames):
        raise RuntimeError("spend cap hit")

    output, runs_by_frame, comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F07"], cmp_compare=broken_compare
    )
    body = analyze_batch.render_report(
        [Path("a.jpg"), Path("b.jpg")], output, runs_by_frame, comparison_runs
    )

    assert "error: RuntimeError: spend cap hit" in body


def test_render_report_no_rule_triggered_line() -> None:
    lookup = _lookup({"F07": lambda frame: None})
    frames = [_frame("00_a"), _frame("01_b")]
    output, runs_by_frame, _comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F07"]
    )

    body = analyze_batch.render_report([Path("a.jpg"), Path("b.jpg")], output, runs_by_frame)

    assert "(no rule triggered - no F12 finding in this batch)" in body


def test_render_report_includes_triggered_rule() -> None:
    def f12_on_first_frame(frame):
        return Finding(taxonomy_id="F12", description="hazy") if frame.frame_id == "00_a" else None

    lookup = _lookup({"F12": f12_on_first_frame, "F07": lambda frame: None, "R01": r01.detect})
    frames = [_frame("00_a"), _frame("01_b")]
    output, runs_by_frame, _comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F12", "F07"]
    )

    body = analyze_batch.render_report([Path("a.jpg"), Path("b.jpg")], output, runs_by_frame)

    assert f"- R01: {taxonomy_rule_text('R01')}" in body


# --- render_report(): the Profile section (item 12) -----------------------


def test_render_report_profile_section_reflects_the_updated_profile() -> None:
    lookup = _lookup({"F06": lambda frame: Finding(taxonomy_id="F06", description="edge"), "F07": lambda frame: None})
    frames = [_frame("00_a")]
    output, runs_by_frame, _comparison_runs = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F06", "F07"]
    )
    updated_profile = record_session(Profile(), output.frames)

    body = analyze_batch.render_report([Path("a.jpg")], output, runs_by_frame, updated_profile=updated_profile)

    assert "## Profile (per-user recurrence across sessions, this session included)" in body
    assert "sessions recorded: 1" in body
    assert "F06: 1 session, 1 frame" in body


def test_render_report_profile_section_absent_when_no_profile_given() -> None:
    lookup = _lookup({"F07": lambda frame: None})
    output, runs_by_frame, _comparison_runs = analyze_batch.run_batch_analysis(
        [_frame("00_a")], detector_lookup=lookup, ids=["F07"]
    )
    body = analyze_batch.render_report([Path("a.jpg")], output, runs_by_frame)
    assert "(not recorded)" in body


# --- main(): end-to-end through real (tiny, on-disk) images ---------------


def test_main_writes_report_and_prints_at_most_three_lines(tmp_path, monkeypatch, capsys) -> None:
    import numpy as np
    from PIL import Image

    photos = []
    for i in range(MIN_BATCH_SIZE):
        photo = tmp_path / f"clean{i}.jpg"
        Image.fromarray(np.full((16, 16, 3), 128, dtype="uint8")).save(photo)
        photos.append(str(photo))

    import _report as report_module

    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(report_module, "REPORTS", reports_dir)

    exit_code = analyze_batch.main(photos)
    assert exit_code == 0

    out = capsys.readouterr().out.splitlines()
    assert 1 <= len(out) <= 3
    assert out[-1] == "PASS"

    written = list(reports_dir.glob("*_analyze_batch.md"))
    assert len(written) == 1
    body = written[0].read_text(encoding="utf-8")
    for i in range(MIN_BATCH_SIZE):
        assert f"{i:02d}_clean{i}" in body


def test_main_records_and_accumulates_the_profile_across_invocations(tmp_path, monkeypatch, capsys) -> None:
    import numpy as np
    from PIL import Image

    def _photos(prefix: str) -> list[str]:
        paths = []
        for i in range(MIN_BATCH_SIZE):
            photo = tmp_path / f"{prefix}{i}.jpg"
            Image.fromarray(np.full((16, 16, 3), 128, dtype="uint8")).save(photo)
            paths.append(str(photo))
        return paths

    import _report as report_module

    monkeypatch.setattr(report_module, "REPORTS", tmp_path / "reports")
    profile_path = tmp_path / "profile.json"

    exit_code = analyze_batch.main(["--profile-path", str(profile_path), *_photos("a")])
    assert exit_code == 0
    assert profile_path.exists()
    first = Profile.from_json(profile_path.read_text(encoding="utf-8"))
    assert first.sessions_recorded == 1

    capsys.readouterr()  # drain stdout between runs

    exit_code = analyze_batch.main(["--profile-path", str(profile_path), *_photos("b")])
    assert exit_code == 0
    second = Profile.from_json(profile_path.read_text(encoding="utf-8"))
    assert second.sessions_recorded == 2  # accumulated, not overwritten


def test_main_reports_failure_for_a_batch_outside_size_range(tmp_path, monkeypatch, capsys) -> None:
    import numpy as np
    from PIL import Image

    photo = tmp_path / "solo.jpg"
    Image.fromarray(np.full((8, 8, 3), 128, dtype="uint8")).save(photo)

    import _report as report_module

    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(report_module, "REPORTS", reports_dir)

    exit_code = analyze_batch.main([str(photo)])
    assert exit_code == 1

    out = capsys.readouterr().out.splitlines()
    assert out[-1] == "FAIL"
    assert list(reports_dir.glob("*_analyze_batch.md"))


def test_main_reports_failure_for_a_bad_path(tmp_path, monkeypatch, capsys) -> None:
    import numpy as np
    from PIL import Image

    photos = []
    for i in range(MIN_BATCH_SIZE - 1):
        photo = tmp_path / f"clean{i}.jpg"
        Image.fromarray(np.full((8, 8, 3), 128, dtype="uint8")).save(photo)
        photos.append(str(photo))
    photos.append(str(tmp_path / "does-not-exist.jpg"))

    import _report as report_module

    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(report_module, "REPORTS", reports_dir)

    exit_code = analyze_batch.main(photos)
    assert exit_code == 1

    out = capsys.readouterr().out.splitlines()
    assert out[-1] == "FAIL"
