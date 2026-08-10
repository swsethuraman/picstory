"""Behavior tests for the QUEUE.md item 4 judgment-dependent (Anthropic API
vision-call) detectors: F04, F05, F06, F11, F13, F15, S01, S02, S04.

F14 and S03 are NOT covered here - see `src/picstory/detectors/f14.py` and
`s03.py` and DECISIONS.md D-005: their Detection text is a property of a
batch of frames, not of any single photo, so they cannot be honestly
implemented at this single-photo stage and remain
`DetectorNotImplemented` stubs (already covered by
`tests/test_detector_registry.py::test_unimplemented_stub_raises_not_implemented`).

Fixture note (read before assuming these are "recorded API responses" per
CLAUDE.md's API-discipline rule): this session's sandboxed environment has no
ANTHROPIC_API_KEY, so no live call to api.anthropic.com was possible to
record genuine fixtures from. The response shapes below
(`_FakeToolUseBlock`/`_FakeResponse`) are hand-authored to match the
documented Anthropic Messages API tool_use structure so that
`_vision.parse_tool_use_response` - the real parsing code, not a bypass of it
- is genuinely exercised. This is a gap, not a substitute: flagged in
DECISIONS.md D-005 for the owner, since fixing it needs either API access in
agent sessions or an owner-recorded round of real fixtures to replace these.
No test here claims to be a live-call recording.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from picstory import detectors
from picstory.detectors._vision import (
    TOOL_NAME,
    VisionCallError,
    VisionRequest,
    VisionVerdict,
    judge,
    parse_tool_use_response,
)
from picstory.frame import Frame
from picstory.schema import taxonomy_detection_text

# --- shared fixtures ----------------------------------------------------


def _frame(frame_id: str = "t") -> Frame:
    rgb = np.zeros((8, 8, 3), dtype=np.uint8)
    rgb[..., 1] = 128  # arbitrary flat green square, content is irrelevant - caller is faked
    return Frame(frame_id=frame_id, path=Path("."), rgb=rgb, exif={})


def _spy_caller(detected: bool, rationale: str = "because reasons"):
    """A fake VisionCaller that records the request it received and answers `detected`."""
    calls: list[VisionRequest] = []

    def caller(request: VisionRequest) -> VisionVerdict:
        calls.append(request)
        return VisionVerdict(taxonomy_id=request.taxonomy_id, detected=detected, rationale=rationale)

    caller.calls = calls  # type: ignore[attr-defined]
    return caller


# One (module, taxonomy_id) pair per detector landed this session.
_MODULES = {
    "F04": "f04",
    "F05": "f05",
    "F06": "f06",
    "F11": "f11",
    "F13": "f13",
    "F15": "f15",
    "S01": "s01",
    "S02": "s02",
    "S04": "s04",
}


def _detect_fn(taxonomy_id: str):
    return detectors.get(taxonomy_id)


# --- per-ID wiring: positive, negative, and detection-text fidelity -----


def test_f04_ultrawide_distortion_on_people_positive() -> None:
    finding = _detect_fn("F04")(_frame(), caller=_spy_caller(True, "near arm looks enormous"))
    assert finding is not None
    assert finding.taxonomy_id == "F04"
    assert finding.description == "near arm looks enormous"


def test_f04_ultrawide_distortion_on_people_negative() -> None:
    assert _detect_fn("F04")(_frame(), caller=_spy_caller(False)) is None


def test_f05_ultrawide_geometric_distortion_positive() -> None:
    finding = _detect_fn("F05")(_frame(), caller=_spy_caller(True, "ceiling lines curve"))
    assert finding is not None and finding.taxonomy_id == "F05"


def test_f05_ultrawide_geometric_distortion_negative() -> None:
    assert _detect_fn("F05")(_frame(), caller=_spy_caller(False)) is None


def test_f06_edge_intrusion_positive() -> None:
    finding = _detect_fn("F06")(_frame(), caller=_spy_caller(True, "stranger's shoulder, right edge"))
    assert finding is not None and finding.taxonomy_id == "F06"


def test_f06_edge_intrusion_negative() -> None:
    assert _detect_fn("F06")(_frame(), caller=_spy_caller(False)) is None


def test_f11_busy_background_behind_figures_positive() -> None:
    finding = _detect_fn("F11")(_frame(), caller=_spy_caller(True, "bystander looking into lens"))
    assert finding is not None and finding.taxonomy_id == "F11"


def test_f11_busy_background_behind_figures_negative() -> None:
    assert _detect_fn("F11")(_frame(), caller=_spy_caller(False)) is None


def test_f13_missing_human_scale_positive() -> None:
    finding = _detect_fn("F13")(_frame(), caller=_spy_caller(True, "no figure for scale against the arcade sphere"))
    assert finding is not None and finding.taxonomy_id == "F13"


def test_f13_missing_human_scale_negative() -> None:
    assert _detect_fn("F13")(_frame(), caller=_spy_caller(False)) is None


def test_f15_subject_landmark_competition_positive() -> None:
    finding = _detect_fn("F15")(_frame(), caller=_spy_caller(True, "landmark amputated behind portrait"))
    assert finding is not None and finding.taxonomy_id == "F15"


def test_f15_subject_landmark_competition_negative() -> None:
    assert _detect_fn("F15")(_frame(), caller=_spy_caller(False)) is None


def test_s01_human_in_the_foreground_positive() -> None:
    finding = _detect_fn("S01")(_frame(), caller=_spy_caller(True, "figure meaningfully placed foreground"))
    assert finding is not None and finding.taxonomy_id == "S01"


def test_s01_human_in_the_foreground_negative() -> None:
    assert _detect_fn("S01")(_frame(), caller=_spy_caller(False)) is None


def test_s02_blue_hour_timing_positive() -> None:
    finding = _detect_fn("S02")(_frame(), caller=_spy_caller(True, "deep blue sky, lit subject"))
    assert finding is not None and finding.taxonomy_id == "S02"


def test_s02_blue_hour_timing_negative() -> None:
    assert _detect_fn("S02")(_frame(), caller=_spy_caller(False)) is None


def test_s04_restraint_composition_positive() -> None:
    finding = _detect_fn("S04")(_frame(), caller=_spy_caller(True, "red vessel against quiet white niche"))
    assert finding is not None and finding.taxonomy_id == "S04"


def test_s04_restraint_composition_negative() -> None:
    assert _detect_fn("S04")(_frame(), caller=_spy_caller(False)) is None


@pytest.mark.parametrize("taxonomy_id", sorted(_MODULES))
def test_detector_embeds_verbatim_detection_text(taxonomy_id: str) -> None:
    # API-discipline rule (CLAUDE.md): the prompt must embed the item's
    # Detection text verbatim. Each module reads it from
    # schema.taxonomy_detection_text() rather than a local copy, so this
    # spies on what actually reached the caller instead of re-parsing
    # TAXONOMY.md a second way.
    caller = _spy_caller(False)
    _detect_fn(taxonomy_id)(_frame(), caller=caller)
    assert len(caller.calls) == 1
    request = caller.calls[0]
    assert request.taxonomy_id == taxonomy_id
    assert request.detection_text == taxonomy_detection_text(taxonomy_id)
    assert request.detection_text  # non-empty, i.e. actually found in TAXONOMY.md


@pytest.mark.parametrize("taxonomy_id", sorted(_MODULES))
def test_detector_module_exposes_expected_taxonomy_id(taxonomy_id: str) -> None:
    module = __import__(f"picstory.detectors.{_MODULES[taxonomy_id]}", fromlist=["TAXONOMY_ID"])
    assert module.TAXONOMY_ID == taxonomy_id


# --- judge() guards against a caller answering for the wrong ID ---------


def test_judge_rejects_caller_returning_mismatched_taxonomy_id() -> None:
    def wrong_id_caller(request: VisionRequest) -> VisionVerdict:
        return VisionVerdict(taxonomy_id="F99", detected=True, rationale="oops")

    with pytest.raises(VisionCallError):
        judge(_frame(), "F04", "some detection text", caller=wrong_id_caller)


# --- parse_tool_use_response: exercised against hand-built SDK-shaped ----
# --- response objects (see module docstring for why these are synthetic) -


class _FakeToolUseBlock:
    def __init__(self, name: str, input: dict) -> None:
        self.type = "tool_use"
        self.name = name
        self.input = input


class _FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeResponse:
    def __init__(self, content: list) -> None:
        self.content = content


def test_parse_tool_use_response_extracts_valid_verdict() -> None:
    response = _FakeResponse(
        [_FakeToolUseBlock(TOOL_NAME, {"taxonomy_id": "F06", "detected": True, "rationale": "shoulder at right edge"})]
    )
    verdict = parse_tool_use_response(response, "F06")
    assert verdict == VisionVerdict(taxonomy_id="F06", detected=True, rationale="shoulder at right edge")


def test_parse_tool_use_response_ignores_leading_text_block() -> None:
    # Real responses can include a text block before the forced tool call;
    # parsing must find the tool_use block rather than assuming content[0].
    response = _FakeResponse(
        [
            _FakeTextBlock("Looking at the photo..."),
            _FakeToolUseBlock(TOOL_NAME, {"taxonomy_id": "S01", "detected": False, "rationale": "no person present"}),
        ]
    )
    verdict = parse_tool_use_response(response, "S01")
    assert verdict.detected is False


def test_parse_tool_use_response_raises_when_no_tool_use_block() -> None:
    response = _FakeResponse([_FakeTextBlock("I decline to answer.")])
    with pytest.raises(VisionCallError):
        parse_tool_use_response(response, "F04")


def test_parse_tool_use_response_raises_on_taxonomy_id_mismatch() -> None:
    response = _FakeResponse(
        [_FakeToolUseBlock(TOOL_NAME, {"taxonomy_id": "F05", "detected": True, "rationale": "x"})]
    )
    with pytest.raises(VisionCallError):
        parse_tool_use_response(response, "F04")


def test_parse_tool_use_response_raises_on_missing_detected_field() -> None:
    response = _FakeResponse([_FakeToolUseBlock(TOOL_NAME, {"taxonomy_id": "F04", "rationale": "x"})])
    with pytest.raises(VisionCallError):
        parse_tool_use_response(response, "F04")


def test_parse_tool_use_response_raises_on_empty_rationale() -> None:
    response = _FakeResponse(
        [_FakeToolUseBlock(TOOL_NAME, {"taxonomy_id": "F04", "detected": True, "rationale": "   "})]
    )
    with pytest.raises(VisionCallError):
        parse_tool_use_response(response, "F04")
