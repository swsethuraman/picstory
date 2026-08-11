"""Behavior tests for scripts/analyze_batch.py (QUEUE.md Stage 2, items 7-8).

Same import-shim and detector-injection pattern as test_cli_analyze.py:
`analyze_batch.py` lives under scripts/, and `run_batch_analysis` takes a
`detector_lookup` so these tests never touch the real (network-calling)
vision detectors - CLAUDE.md requires the test suite to run offline. F03's
real batch-level grouping is a pure local computation (no network), so its
own behavior is tested directly in test_f03_safety_copies.py; here it is
mostly stubbed to `{}` (no findings) so tests that only care about the
per-frame sweep aren't coupled to F03's actual grouping decisions.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import analyze_batch  # noqa: E402

from picstory.batch import MIN_BATCH_SIZE, load_batch  # noqa: E402
from picstory.detectors.base import DetectorNotImplemented  # noqa: E402
from picstory.frame import Frame  # noqa: E402
from picstory.schema import Finding  # noqa: E402


def _frame(frame_id: str) -> Frame:
    import numpy as np

    return Frame(frame_id=frame_id, path=Path("."), rgb=np.zeros((4, 4, 3), dtype="uint8"), exif={})


def _no_f03_findings(frames):
    return {}


def _lookup(table: dict[str, object]):
    table = {"F03": _no_f03_findings, **table}
    return lambda taxonomy_id: table[taxonomy_id]


# --- run_batch_analysis(): reuses analyze.run_analysis per frame ----------


def test_run_batch_analysis_aggregates_one_frame_analysis_per_frame() -> None:
    def detected(frame):
        return Finding(taxonomy_id="F06", description=f"edge intrusion in {frame.frame_id}")

    def clean(frame):
        return None

    lookup = _lookup({"F06": detected, "F07": clean})
    frames = [_frame("00_a"), _frame("01_b"), _frame("02_c")]

    output, runs_by_frame = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F06", "F07"]
    )

    assert [fa.frame_id for fa in output.frames] == ["00_a", "01_b", "02_c"]
    assert set(runs_by_frame) == {"00_a", "01_b", "02_c"}
    for frame_id in runs_by_frame:
        # F03 always runs too (see module docstring) even though `ids` here
        # only names F06/F07 - `ids` governs the per-frame sweep, not F03.
        assert {r.taxonomy_id for r in runs_by_frame[frame_id]} == {"F06", "F07", "F03"}


def test_run_batch_analysis_findings_stay_scoped_to_their_own_frame() -> None:
    def detected(frame):
        # Only fires for one specific frame, like a real per-frame detector.
        return Finding(taxonomy_id="F06", description="edge") if frame.frame_id == "01_b" else None

    lookup = _lookup({"F06": detected})
    frames = [_frame("00_a"), _frame("01_b"), _frame("02_c")]

    output, _runs = analyze_batch.run_batch_analysis(frames, detector_lookup=lookup, ids=["F06"])

    by_id = {fa.frame_id: fa for fa in output.frames}
    assert by_id["00_a"].findings == []
    assert [f.taxonomy_id for f in by_id["01_b"].findings] == ["F06"]
    assert by_id["02_c"].findings == []


def test_run_batch_analysis_leaves_pick_and_habit_none() -> None:
    lookup = _lookup({"F07": lambda frame: None})
    output, _runs = analyze_batch.run_batch_analysis(
        [_frame("00_a")], detector_lookup=lookup, ids=["F07"]
    )
    assert output.pick is None
    assert output.habit is None


# --- run_batch_analysis(): F03's batch-level pass (item 8) -----------------


def test_run_batch_analysis_merges_f03_findings_into_flagged_frames_only() -> None:
    def f03_findings(frames):
        # Mirrors picstory.detectors.f03.detect's shape: only the flagged
        # (non-keeper) frame_ids appear in the returned mapping.
        return {"01_b": Finding(taxonomy_id="F03", description="safety copy of '00_a'")}

    lookup = _lookup({"F07": lambda frame: None, "F03": f03_findings})
    frames = [_frame("00_a"), _frame("01_b"), _frame("02_c")]

    output, runs_by_frame = analyze_batch.run_batch_analysis(
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

    _output, runs_by_frame = analyze_batch.run_batch_analysis(
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

    _output, runs_by_frame = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F07"]
    )

    for frame_id in ("00_a", "01_b"):
        f03_run = [r for r in runs_by_frame[frame_id] if r.taxonomy_id == "F03"][0]
        assert f03_run.status == "error"
        assert "boom" in f03_run.detail


# --- render_report(): per-frame sections and aggregate counts -------------


def test_render_report_includes_per_frame_sections_and_totals() -> None:
    def detected(frame):
        return Finding(taxonomy_id="F06", description="edge intrusion")

    lookup = _lookup({"F06": detected, "F07": lambda frame: None})
    frames = [_frame("00_a"), _frame("01_b")]
    output, runs_by_frame = analyze_batch.run_batch_analysis(
        frames, detector_lookup=lookup, ids=["F06", "F07"]
    )
    body = analyze_batch.render_report(
        [Path("a.jpg"), Path("b.jpg")], output, runs_by_frame
    )

    # F06 detected x2 + F07 clean x2 + F03 clean x2 (stubbed to no findings).
    assert "2 detected, 4 clean, 0 stub, 0 error" in body
    assert "### 00_a:" in body
    assert "### 01_b:" in body
    assert "- F06 [detected] — edge intrusion" in body
    assert "pick: None, habit: None" in body


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
