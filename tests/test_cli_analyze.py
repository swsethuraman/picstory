"""Behavior tests for scripts/analyze.py (QUEUE.md Stage 1, item 5).

`analyze.py` lives under scripts/, not src/picstory/, so it is imported here
via a sys.path shim rather than a normal package import - the same
production/test boundary as `scripts/_report.py`.

These tests exercise the CLI's per-ID dispatch/classification logic
(detected/clean/stub/error) with a fake `detector_lookup`, mirroring the
`VisionCaller` injection pattern in `_vision.py`/`test_vision_detectors.py`.
Never routes through the real registry's vision detectors here: this
sandboxed session has no ANTHROPIC_API_KEY, so a real call would only ever
exercise the local "no key" failure path, and a differently configured
session could exercise a genuine live call - exactly what CLAUDE.md's "the
test suite must run offline" rule forbids. Injection keeps this suite
config-independent.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import analyze  # noqa: E402

from picstory.detectors.base import DetectorNotImplemented  # noqa: E402
from picstory.frame import Frame  # noqa: E402
from picstory.schema import Finding, taxonomy_ids  # noqa: E402


def _frame(frame_id: str = "t") -> Frame:
    import numpy as np

    return Frame(frame_id=frame_id, path=Path("."), rgb=np.zeros((4, 4, 3), dtype="uint8"), exif={})


def _lookup(table: dict[str, object]):
    return lambda taxonomy_id: table[taxonomy_id]


# --- evaluable_ids(): R01 and F03 are structurally excluded ---------------


def test_evaluable_ids_excludes_the_conditional_batch_rule() -> None:
    # Not named with an ID substring on purpose: this checks CLI wiring
    # (R01 and F03 are structurally excluded from the per-frame sweep -
    # both need batch context this one-photo-at-a-time module never has),
    # not either ID's actual detection logic - naming it "..._r01" or
    # "..._f03" would incidentally satisfy test_taxonomy_coverage.py's
    # per-ID name check without genuine detector-substance coverage here,
    # which is exactly the gap that guard exists to catch. F03's real
    # substance is covered by tests/test_duplicates.py and
    # tests/test_cli_analyze_batch.py, where its batch context exists.
    ids = analyze.evaluable_ids()
    assert "R01" not in ids
    assert "F03" not in ids
    assert set(ids) == taxonomy_ids() - {"R01", "F03"}
    assert len(ids) == 18


# --- run_analysis(): per-ID classification --------------------------------


def test_run_analysis_classifies_detected_clean_stub_and_error() -> None:
    def detected(frame):
        return Finding(taxonomy_id="F06", description="stranger's shoulder, right edge")

    def clean(frame):
        return None

    def stub(frame):
        raise DetectorNotImplemented("F14: not yet implemented")

    def errors(frame):
        raise RuntimeError("no ANTHROPIC_API_KEY")

    lookup = _lookup({"F06": detected, "F07": clean, "F14": stub, "F04": errors})
    output, runs = analyze.run_analysis(
        _frame("p1"), detector_lookup=lookup, ids=["F06", "F07", "F14", "F04"]
    )

    by_id = {r.taxonomy_id: r for r in runs}
    assert by_id["F06"].status == "detected"
    assert by_id["F06"].detail == "stranger's shoulder, right edge"
    assert by_id["F07"].status == "clean" and by_id["F07"].detail is None
    assert by_id["F14"].status == "stub"
    assert by_id["F04"].status == "error" and "no ANTHROPIC_API_KEY" in by_id["F04"].detail


def test_run_analysis_output_findings_are_detected_only() -> None:
    def detected(frame):
        return Finding(taxonomy_id="S01", description="figure in the foreground")

    def clean(frame):
        return None

    lookup = _lookup({"S01": detected, "F07": clean})
    output, _runs = analyze.run_analysis(_frame("p1"), detector_lookup=lookup, ids=["S01", "F07"])

    assert [f.taxonomy_id for f in output.frames[0].findings] == ["S01"]
    assert output.frames[0].frame_id == "p1"


def test_run_analysis_leaves_pick_and_habit_none() -> None:
    lookup = _lookup({"F07": lambda frame: None})
    output, _runs = analyze.run_analysis(_frame(), detector_lookup=lookup, ids=["F07"])
    assert output.pick is None
    assert output.habit is None


def test_run_analysis_one_error_does_not_stop_the_sweep() -> None:
    def errors(frame):
        raise ValueError("boom")

    def clean(frame):
        return None

    lookup = _lookup({"F04": errors, "F07": clean})
    _output, runs = analyze.run_analysis(_frame(), detector_lookup=lookup, ids=["F04", "F07"])
    assert {r.taxonomy_id for r in runs} == {"F04", "F07"}


# --- render_report(): counts and per-ID lines land in the body -----------


def test_render_report_includes_counts_and_per_id_lines() -> None:
    def detected(frame):
        return Finding(taxonomy_id="F06", description="edge intrusion")

    lookup = _lookup({"F06": detected, "F07": lambda frame: None})
    frame = _frame("p1")
    output, runs = analyze.run_analysis(frame, detector_lookup=lookup, ids=["F06", "F07"])
    body = analyze.render_report(Path("photo.jpg"), frame, output, runs)

    assert "1 detected, 1 clean, 0 stub, 0 error" in body
    assert "- F06 [detected] — edge intrusion" in body
    assert "- F07 [clean]" in body
    assert "pick: None, habit: None" in body
    assert '"schema_version": "1.0"' in body


# --- main(): end-to-end through a real (tiny, on-disk) image -------------


def test_main_writes_report_and_prints_at_most_three_lines(tmp_path, monkeypatch, capsys) -> None:
    import numpy as np
    from PIL import Image

    photo = tmp_path / "clean.jpg"
    Image.fromarray(np.full((16, 16, 3), 128, dtype="uint8")).save(photo)

    import _report as report_module

    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(report_module, "REPORTS", reports_dir)

    exit_code = analyze.main([str(photo)])
    assert exit_code == 0

    out = capsys.readouterr().out.splitlines()
    assert 1 <= len(out) <= 3
    assert out[-1] == "PASS"

    written = list(reports_dir.glob("*_analyze.md"))
    assert len(written) == 1
    assert "frame_id: clean" in written[0].read_text(encoding="utf-8")


def test_main_reports_failure_for_a_bad_path(tmp_path, monkeypatch, capsys) -> None:
    import _report as report_module

    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(report_module, "REPORTS", reports_dir)

    exit_code = analyze.main([str(tmp_path / "does-not-exist.jpg")])
    assert exit_code == 1

    out = capsys.readouterr().out.splitlines()
    assert out[-1] == "FAIL"
    assert list(reports_dir.glob("*_analyze.md"))
