"""Behavior tests for the QUEUE.md item 4 judgment-dependent (Anthropic API
vision-call) detectors: F04, F05, F06, F11, F13, F15, S01, S02, S04.

F14 and S03 are NOT covered here - see `src/picstory/detectors/f14.py` and
`s03.py` and DECISIONS.md D-005: their Detection text is a property of a
batch of frames, not of any single photo, so they cannot be honestly
implemented at this single-photo stage and remain
`DetectorNotImplemented` stubs (already covered by
`tests/test_detector_registry.py::test_unimplemented_stub_raises_not_implemented`).

Fixture note (DECISIONS.md D-006): earlier sessions had no working API key,
so every response shape here was hand-authored to match the documented
Anthropic Messages API tool_use structure - a gap D-006 tracked, not a
substitute (`_vision.parse_tool_use_response`, the real parsing code, was
still genuinely exercised; what was missing was evidence a live call
actually comes back in the shape the code expects). D-006's ruling
provisioned `PICSTORY_VISION_KEY` for agent sessions; a prior session used it
to make 4 live calls (`scripts/record_vision_fixtures.py`) and recorded the
raw responses under `tests/fixtures/vision/`. The
"...replays_genuine_recorded_api_call" tests below replay those recordings
through `parse_tool_use_response` - genuine live-call evidence, not a
fixture. `_FakeToolUseBlock`/`_FakeResponse` remain for the malformed-shape
tests only (missing tool_use block, wrong ID, missing field, empty
rationale): a real call under this module's schema-enforced `tool_choice`
cannot produce a malformed response, so those specific cases have no live
equivalent to record and stay intentionally hand-authored.

QUEUE.md item 12 (the running profile) extended this same precedent: this
session made 2 more live F06 calls with `f06.EDGE_SUB_PATTERN` wired in
(one clean, one over a synthetic right-edge intrusion) and recorded them
too - the live model genuinely returned `edge=right` for the intrusion
scene, not a hand-picked value. See
"...replays_genuine_recorded_f06_edge_sub_pattern" below.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from picstory import detectors
from picstory.detectors._vision import (
    TOOL_NAME,
    SubPatternSpec,
    VisionCallError,
    VisionRequest,
    VisionVerdict,
    _tool_schema,
    judge,
    parse_tool_use_response,
)
from picstory.detectors.f06 import EDGE_SUB_PATTERN
from picstory.frame import Frame
from picstory.schema import taxonomy_detection_text

# --- shared fixtures ----------------------------------------------------


def _frame(frame_id: str = "t") -> Frame:
    rgb = np.zeros((8, 8, 3), dtype=np.uint8)
    rgb[..., 1] = 128  # arbitrary flat green square, content is irrelevant - caller is faked
    return Frame(frame_id=frame_id, path=Path("."), rgb=rgb, exif={})


def _spy_caller(detected: bool, rationale: str = "because reasons", sub_pattern: str | None = None):
    """A fake VisionCaller that records the request it received and answers `detected`."""
    calls: list[VisionRequest] = []

    def caller(request: VisionRequest) -> VisionVerdict:
        calls.append(request)
        return VisionVerdict(
            taxonomy_id=request.taxonomy_id, detected=detected, rationale=rationale, sub_pattern=sub_pattern
        )

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


# --- F06's edge sub_pattern (QUEUE.md item 12: the running profile) -------


def test_f06_finding_carries_edge_sub_pattern_from_caller() -> None:
    finding = _detect_fn("F06")(_frame(), caller=_spy_caller(True, "shoulder at right edge", sub_pattern="right"))
    assert finding is not None
    assert finding.sub_pattern == "right"


def test_f06_finding_sub_pattern_none_when_caller_omits_it() -> None:
    # A caller that never sets sub_pattern (e.g. an older/faked verdict) is
    # still a valid Finding - sub_pattern is optional profile detail, not a
    # required part of F06's own detection.
    finding = _detect_fn("F06")(_frame(), caller=_spy_caller(True, "edge intrusion"))
    assert finding is not None
    assert finding.sub_pattern is None


def test_f06_detector_request_carries_edge_sub_pattern_spec() -> None:
    caller = _spy_caller(True, "x", sub_pattern="left")
    _detect_fn("F06")(_frame(), caller=caller)
    assert caller.calls[0].sub_pattern is EDGE_SUB_PATTERN


@pytest.mark.parametrize("taxonomy_id", sorted(set(_MODULES) - {"F06"}))
def test_only_f06_requests_a_sub_pattern(taxonomy_id: str) -> None:
    # F06 is the only ID with a TAXONOMY.md Profile note
    # (schema.taxonomy_ids_with_subpattern()) - every other judgment-
    # dependent detector's request must carry no sub_pattern at all.
    caller = _spy_caller(True, "x")
    _detect_fn(taxonomy_id)(_frame(), caller=caller)
    assert caller.calls[0].sub_pattern is None


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


# --- _tool_schema()/_prompt(): sub_pattern is opt-in, enum-constrained ----


def test_tool_schema_without_sub_pattern_has_no_extra_property() -> None:
    schema = _tool_schema("F04")
    assert set(schema["input_schema"]["properties"]) == {"taxonomy_id", "detected", "rationale"}


def test_tool_schema_with_sub_pattern_adds_enum_constrained_property() -> None:
    schema = _tool_schema("F06", EDGE_SUB_PATTERN)
    edge_property = schema["input_schema"]["properties"]["edge"]
    assert edge_property["enum"] == list(EDGE_SUB_PATTERN.enum_values)
    # Not in `required` - the model omits it when detected is false; parsing
    # (not the JSON schema) enforces "required when detected is true."
    assert "edge" not in schema["input_schema"]["required"]


# --- parse_tool_use_response()/sub_pattern extraction ----------------------


def test_parse_tool_use_response_extracts_sub_pattern_when_detected() -> None:
    response = _FakeResponse(
        [_FakeToolUseBlock(TOOL_NAME, {"taxonomy_id": "F06", "detected": True, "rationale": "x", "edge": "left"})]
    )
    verdict = parse_tool_use_response(response, "F06", EDGE_SUB_PATTERN)
    assert verdict.sub_pattern == "left"


def test_parse_tool_use_response_sub_pattern_none_when_not_detected() -> None:
    response = _FakeResponse(
        [_FakeToolUseBlock(TOOL_NAME, {"taxonomy_id": "F06", "detected": False, "rationale": "clean"})]
    )
    verdict = parse_tool_use_response(response, "F06", EDGE_SUB_PATTERN)
    assert verdict.sub_pattern is None


def test_parse_tool_use_response_rejects_invalid_sub_pattern_when_detected() -> None:
    response = _FakeResponse(
        [
            _FakeToolUseBlock(
                TOOL_NAME, {"taxonomy_id": "F06", "detected": True, "rationale": "x", "edge": "diagonal"}
            )
        ]
    )
    with pytest.raises(VisionCallError):
        parse_tool_use_response(response, "F06", EDGE_SUB_PATTERN)


def test_parse_tool_use_response_rejects_missing_sub_pattern_when_detected() -> None:
    response = _FakeResponse([_FakeToolUseBlock(TOOL_NAME, {"taxonomy_id": "F06", "detected": True, "rationale": "x"})])
    with pytest.raises(VisionCallError):
        parse_tool_use_response(response, "F06", EDGE_SUB_PATTERN)


# --- default_caller() key resolution (DECISIONS.md D-006) ---------------
# Patches anthropic.Anthropic itself so default_caller()'s real code runs
# end-to-end (no live call - the fake client's constructor just records the
# api_key it was given).


class _FakeAnthropicClient:
    last_api_key: str | None = None

    def __init__(self, *, api_key: str | None = None) -> None:
        _FakeAnthropicClient.last_api_key = api_key


def test_default_caller_prefers_picstory_vision_key(monkeypatch: pytest.MonkeyPatch) -> None:
    import anthropic

    from picstory.detectors import _vision

    monkeypatch.setenv("PICSTORY_VISION_KEY", "vision-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setattr(anthropic, "Anthropic", _FakeAnthropicClient)

    _vision.default_caller()
    assert _FakeAnthropicClient.last_api_key == "vision-key"


def test_default_caller_falls_back_to_anthropic_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    import anthropic

    from picstory.detectors import _vision

    monkeypatch.delenv("PICSTORY_VISION_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setattr(anthropic, "Anthropic", _FakeAnthropicClient)

    _vision.default_caller()
    assert _FakeAnthropicClient.last_api_key == "anthropic-key"


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


# --- parse_tool_use_response replayed against genuine recorded live calls --
# --- (DECISIONS.md D-006): 4 calls, F13 and S01 against two drawn scenes, --
# --- recorded by scripts/record_vision_fixtures.py. Replaying a saved     --
# --- response is offline (no network here) - see module docstring.       --

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "vision"

# fixture filename -> (taxonomy_id, verdict actually returned by the live call)
_RECORDED_CALLS = {
    "f13_landmark_alone.json": ("F13", True),
    "f13_landmark_with_figure.json": ("F13", True),
    "s01_landmark_alone.json": ("S01", False),
    "s01_landmark_with_figure.json": ("S01", False),
}

# F06 recordings carry EDGE_SUB_PATTERN and so need it passed to
# parse_tool_use_response too - kept separate from _RECORDED_CALLS above
# rather than bolting an always-None sub_pattern column onto every row.
# fixture filename -> (taxonomy_id, expected detected, expected edge)
_RECORDED_F06_CALLS = {
    "f06_landmark_alone.json": (False, None),
    "f06_edge_intrusion_right.json": (True, "right"),
}


def _load_recorded_response(fixture_name: str):
    from anthropic.types import Message

    data = json.loads((_FIXTURES_DIR / fixture_name).read_text(encoding="utf-8"))
    return Message.model_validate(data)


@pytest.mark.parametrize("fixture_name", sorted(_RECORDED_CALLS))
def test_parse_tool_use_response_replays_genuine_recorded_api_call(fixture_name: str) -> None:
    taxonomy_id, expected_detected = _RECORDED_CALLS[fixture_name]
    response = _load_recorded_response(fixture_name)
    verdict = parse_tool_use_response(response, taxonomy_id)
    assert verdict.taxonomy_id == taxonomy_id
    assert verdict.detected is expected_detected
    assert verdict.rationale  # the live model always filled this in


@pytest.mark.parametrize("fixture_name", sorted(_RECORDED_F06_CALLS))
def test_parse_tool_use_response_replays_genuine_recorded_f06_edge_sub_pattern(fixture_name: str) -> None:
    # DECISIONS.md D-006's precedent, extended for QUEUE.md item 12: these
    # two recordings (scripts/record_vision_fixtures.py) are genuine live
    # calls made with EDGE_SUB_PATTERN wired in, not a hand-authored guess
    # at what the field would look like.
    expected_detected, expected_edge = _RECORDED_F06_CALLS[fixture_name]
    response = _load_recorded_response(fixture_name)
    verdict = parse_tool_use_response(response, "F06", EDGE_SUB_PATTERN)
    assert verdict.detected is expected_detected
    assert verdict.sub_pattern == expected_edge
    assert verdict.rationale


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
