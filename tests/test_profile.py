"""Tests for src/picstory/profile.py (QUEUE.md Stage 4, item 12: the running profile).

`load_profile`/`save_profile` are the only I/O; every other test here works
with in-memory `Profile`/`IdRecurrence` objects and a `tmp_path` file when it
does touch disk - `tests/conftest.py`'s `_isolate_profile_store` fixture
additionally guarantees `default_profile_path()` itself never resolves to a
real `~/.picstory/profile.json` anywhere in this suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from picstory.profile import (
    PROFILE_SCHEMA_VERSION,
    IdRecurrence,
    Profile,
    ProfileError,
    default_profile_path,
    load_profile,
    record_session,
    save_profile,
    summary_lines,
    top_recurrences,
)
from picstory.schema import Finding, FrameAnalysis

# --- Profile/IdRecurrence: construction, validation, roundtrip ------------


def test_profile_default_is_empty() -> None:
    p = Profile()
    assert p.schema_version == PROFILE_SCHEMA_VERSION
    assert p.sessions_recorded == 0
    assert p.recurrences == {}


def test_profile_rejects_stale_schema_version() -> None:
    with pytest.raises(ProfileError):
        Profile(schema_version="0.9")


def test_profile_rejects_mismatched_recurrence_key() -> None:
    with pytest.raises(ProfileError):
        Profile(recurrences={"F06": IdRecurrence(taxonomy_id="F01")})


def test_profile_roundtrip_json() -> None:
    p = Profile(
        sessions_recorded=2,
        recurrences={
            "F06": IdRecurrence(taxonomy_id="F06", sessions=2, frames=3, sub_patterns={"right": 2, "left": 1}),
        },
    )
    round_tripped = Profile.from_json(p.to_json())
    assert round_tripped == p


def test_id_recurrence_to_dict_and_from_dict() -> None:
    rec = IdRecurrence(taxonomy_id="F06", sessions=1, frames=2, sub_patterns={"right": 2})
    data = rec.to_dict()
    assert data == {"taxonomy_id": "F06", "sessions": 1, "frames": 2, "sub_patterns": {"right": 2}}
    assert IdRecurrence.from_dict(data) == rec


# --- default_profile_path() -------------------------------------------------


def test_default_profile_path_honors_env_var(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    override = tmp_path / "somewhere" / "profile.json"
    monkeypatch.setenv("PICSTORY_PROFILE_PATH", str(override))
    assert default_profile_path() == override


def test_default_profile_path_falls_back_to_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PICSTORY_PROFILE_PATH", raising=False)
    assert default_profile_path() == Path.home() / ".picstory" / "profile.json"


# --- load_profile()/save_profile(): the only I/O in this module -----------


def test_load_profile_missing_file_returns_empty_profile(tmp_path: Path) -> None:
    p = load_profile(tmp_path / "does-not-exist.json")
    assert p == Profile()


def test_save_profile_then_load_profile_roundtrips(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "profile.json"
    original = Profile(sessions_recorded=1, recurrences={"S01": IdRecurrence(taxonomy_id="S01", sessions=1, frames=1)})
    save_profile(original, path)
    assert path.exists()  # save_profile creates parent dirs
    assert load_profile(path) == original


# --- record_session(): pure, per-session recurrence folding ----------------


def _frame_analysis(frame_id: str, *findings: Finding) -> FrameAnalysis:
    return FrameAnalysis(frame_id=frame_id, findings=list(findings))


def test_record_session_is_pure_does_not_mutate_input() -> None:
    original = Profile()
    frames = [_frame_analysis("00_a", Finding(taxonomy_id="F06", sub_pattern="right"))]
    record_session(original, frames)
    assert original == Profile()  # untouched


def test_record_session_first_session_counts_one_session_one_frame() -> None:
    updated = record_session(Profile(), [_frame_analysis("00_a", Finding(taxonomy_id="F06"))])
    assert updated.sessions_recorded == 1
    assert updated.recurrences["F06"].sessions == 1
    assert updated.recurrences["F06"].frames == 1


def test_record_session_counts_one_frame_per_carrying_frame() -> None:
    frames = [
        _frame_analysis("00_a", Finding(taxonomy_id="F06")),
        _frame_analysis("01_b", Finding(taxonomy_id="F06")),
        _frame_analysis("02_c"),  # clean, does not count
    ]
    updated = record_session(Profile(), frames)
    assert updated.recurrences["F06"].sessions == 1  # one session
    assert updated.recurrences["F06"].frames == 2  # two carrying frames


def test_record_session_accumulates_across_multiple_sessions() -> None:
    session_1 = record_session(Profile(), [_frame_analysis("00_a", Finding(taxonomy_id="F06"))])
    session_2 = record_session(
        session_1,
        [
            _frame_analysis("00_a", Finding(taxonomy_id="F06")),
            _frame_analysis("01_b", Finding(taxonomy_id="F06")),
        ],
    )
    assert session_2.sessions_recorded == 2
    assert session_2.recurrences["F06"].sessions == 2
    assert session_2.recurrences["F06"].frames == 3  # 1 + 2


def test_record_session_id_present_only_once_still_counts_one_session() -> None:
    """Recurrence within a batch, even repeated, is still just one session."""
    frames = [_frame_analysis(f"{i:02d}", Finding(taxonomy_id="F03")) for i in range(5)]
    updated = record_session(Profile(), frames)
    assert updated.recurrences["F03"].sessions == 1
    assert updated.recurrences["F03"].frames == 5


def test_record_session_excludes_conditional_rule_and_unclassified() -> None:
    # Named to avoid an accidental "r01" substring match in
    # test_taxonomy_coverage.py's naming guard - this test only asserts R01
    # (never a per-frame Finding, see scripts/analyze.py) and unclassified
    # (no polarity) don't recur here; it is not R01 test coverage.
    frames = [
        _frame_analysis(
            "00_a",
            Finding(taxonomy_id="unclassified", description="a dog photobombing"),
        )
    ]
    updated = record_session(Profile(), frames)
    assert updated.recurrences == {}
    assert updated.sessions_recorded == 1  # the session still happened - just recorded nothing recurring


def test_record_session_tallies_sub_pattern_per_occurrence() -> None:
    frames = [
        _frame_analysis("00_a", Finding(taxonomy_id="F06", sub_pattern="right")),
        _frame_analysis("01_b", Finding(taxonomy_id="F06", sub_pattern="right")),
        _frame_analysis("02_c", Finding(taxonomy_id="F06", sub_pattern="left")),
        _frame_analysis("03_d", Finding(taxonomy_id="F06")),  # no sub_pattern - not tallied
    ]
    updated = record_session(Profile(), frames)
    assert updated.recurrences["F06"].sub_patterns == {"right": 2, "left": 1}


def test_record_session_sub_pattern_tally_accumulates_across_sessions() -> None:
    session_1 = record_session(Profile(), [_frame_analysis("00_a", Finding(taxonomy_id="F06", sub_pattern="right"))])
    session_2 = record_session(session_1, [_frame_analysis("00_a", Finding(taxonomy_id="F06", sub_pattern="right"))])
    assert session_2.recurrences["F06"].sub_patterns == {"right": 2}


# --- top_recurrences()/summary_lines(): display ordering -------------------


def test_top_recurrences_orders_by_sessions_then_frames_then_id() -> None:
    p = Profile(
        recurrences={
            "F07": IdRecurrence(taxonomy_id="F07", sessions=1, frames=5),
            "F06": IdRecurrence(taxonomy_id="F06", sessions=3, frames=1),
            "S01": IdRecurrence(taxonomy_id="S01", sessions=3, frames=4),
        }
    )
    ordered = [rec.taxonomy_id for rec in top_recurrences(p)]
    # F06 and S01 tie on sessions (3); S01 has more frames (4 > 1), so it
    # ranks first. F07 (1 session) ranks last.
    assert ordered == ["S01", "F06", "F07"]


def test_summary_lines_includes_sub_pattern_detail_most_frequent_first() -> None:
    p = Profile(
        recurrences={
            "F06": IdRecurrence(taxonomy_id="F06", sessions=2, frames=3, sub_patterns={"left": 1, "right": 2}),
        }
    )
    lines = summary_lines(p)
    assert lines == ["F06: 2 sessions, 3 frames (right x2, left x1)"]


def test_summary_lines_omits_sub_pattern_parenthetical_when_none_recorded() -> None:
    p = Profile(recurrences={"S01": IdRecurrence(taxonomy_id="S01", sessions=1, frames=1)})
    assert summary_lines(p) == ["S01: 1 session, 1 frame"]


def test_summary_lines_empty_profile() -> None:
    assert summary_lines(Profile()) == []
