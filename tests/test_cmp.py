"""Behavior tests for src/picstory/cmp.py (QUEUE.md item 11, TAXONOMY.md §CMP).

Same shape as tests/test_vision_detectors.py: `compare_group`/`judge`-style
injection keeps this offline (a fake `CmpCaller`), and
`parse_tool_use_response` is exercised both against hand-built
malformed-shape objects (a real, schema-enforced call cannot produce these -
same reasoning as _vision's) and against one genuine recorded live call
(scripts/record_cmp_fixture.py, this session - CLAUDE.md's API-discipline
rule, same precedent as D-006's vision fixtures).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from picstory.cmp import (
    TOOL_NAME,
    CmpCallError,
    CmpRequest,
    CmpVerdict,
    compare_group,
    parse_tool_use_response,
)
from picstory.frame import Frame
from picstory.schema import cmp_rubric_text


def _frame(frame_id: str) -> Frame:
    rgb = np.zeros((8, 8, 3), dtype=np.uint8)
    rgb[..., 1] = 128
    return Frame(frame_id=frame_id, path=Path("."), rgb=rgb, exif={})


def _spy_caller(verdict: CmpVerdict):
    calls: list[CmpRequest] = []

    def caller(request: CmpRequest) -> CmpVerdict:
        calls.append(request)
        return verdict

    caller.calls = calls  # type: ignore[attr-defined]
    return caller


# --- compare_group(): wiring, request shape, output shape -----------------


def test_compare_group_returns_comparison_naming_the_winner() -> None:
    verdict = CmpVerdict(
        winner_frame_id="b",
        subject_placement="a centers the subject; b drifts right",
        edge_amputations="a clips a hand; b doesn't",
        incidental_distractions="an exit sign in a, absent in b",
    )
    comparison = compare_group([_frame("a"), _frame("b")], caller=_spy_caller(verdict))
    assert comparison.group == ["a", "b"]
    assert comparison.winner_frame_id == "b"
    assert comparison.tiebreaker is None


def test_compare_group_carries_the_tiebreaker_through() -> None:
    verdict = CmpVerdict(
        winner_frame_id="a",
        subject_placement="x",
        edge_amputations="y",
        incidental_distractions="z",
        tiebreaker="a mid-stride walker in frame a",
    )
    comparison = compare_group([_frame("a"), _frame("b")], caller=_spy_caller(verdict))
    assert comparison.tiebreaker == "a mid-stride walker in frame a"


def test_compare_group_sends_every_frame_and_the_rubric_verbatim() -> None:
    verdict = CmpVerdict(
        winner_frame_id="c", subject_placement="x", edge_amputations="y", incidental_distractions="z"
    )
    caller = _spy_caller(verdict)
    compare_group([_frame("a"), _frame("b"), _frame("c")], caller=caller)

    assert len(caller.calls) == 1
    request = caller.calls[0]
    assert request.frame_ids == ("a", "b", "c")
    assert len(request.images) == 3
    assert request.rubric_text == cmp_rubric_text()


def test_compare_group_requires_at_least_two_frames() -> None:
    with pytest.raises(ValueError):
        compare_group([_frame("a")], caller=_spy_caller(CmpVerdict("a", "x", "y", "z")))


def test_compare_group_rejects_caller_naming_a_frame_not_in_the_group() -> None:
    verdict = CmpVerdict(winner_frame_id="not-in-group", subject_placement="x", edge_amputations="y", incidental_distractions="z")
    with pytest.raises(CmpCallError):
        compare_group([_frame("a"), _frame("b")], caller=_spy_caller(verdict))


# --- _tool_schema(): winning_frame_id is constrained to the actual group --


def test_tool_schema_constrains_winning_frame_id_to_the_given_frames() -> None:
    from picstory.cmp import _tool_schema

    schema = _tool_schema(("a", "b", "c"))
    assert schema["name"] == TOOL_NAME
    assert schema["input_schema"]["properties"]["winning_frame_id"]["enum"] == ["a", "b", "c"]
    assert set(schema["input_schema"]["required"]) == {
        "winning_frame_id",
        "subject_placement",
        "edge_amputations",
        "incidental_distractions",
    }


def test_prompt_embeds_the_cmp_rubric_verbatim() -> None:
    from picstory.cmp import _prompt

    prompt = _prompt(("a", "b"), cmp_rubric_text())
    assert cmp_rubric_text() in prompt
    assert "'a'" in prompt and "'b'" in prompt


# --- parse_tool_use_response: hand-built malformed-shape objects ----------
# --- (a real, schema-enforced call cannot produce these - see module ------
# --- docstring / test_vision_detectors.py's identical reasoning) ----------


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


def test_parse_tool_use_response_ignores_leading_text_block() -> None:
    response = _FakeResponse(
        [
            _FakeTextBlock("Looking at both photos..."),
            _FakeToolUseBlock(
                TOOL_NAME,
                {
                    "winning_frame_id": "b",
                    "subject_placement": "x",
                    "edge_amputations": "y",
                    "incidental_distractions": "z",
                },
            ),
        ]
    )
    verdict = parse_tool_use_response(response, ("a", "b"))
    assert verdict.winner_frame_id == "b"


def test_parse_tool_use_response_raises_when_no_tool_use_block() -> None:
    response = _FakeResponse([_FakeTextBlock("I decline to answer.")])
    with pytest.raises(CmpCallError):
        parse_tool_use_response(response, ("a", "b"))


def test_parse_tool_use_response_raises_on_winner_outside_group() -> None:
    response = _FakeResponse(
        [
            _FakeToolUseBlock(
                TOOL_NAME,
                {
                    "winning_frame_id": "c",
                    "subject_placement": "x",
                    "edge_amputations": "y",
                    "incidental_distractions": "z",
                },
            )
        ]
    )
    with pytest.raises(CmpCallError):
        parse_tool_use_response(response, ("a", "b"))


def test_parse_tool_use_response_raises_on_missing_axis_field() -> None:
    response = _FakeResponse(
        [_FakeToolUseBlock(TOOL_NAME, {"winning_frame_id": "a", "subject_placement": "x", "edge_amputations": "y"})]
    )
    with pytest.raises(CmpCallError):
        parse_tool_use_response(response, ("a", "b"))


def test_parse_tool_use_response_raises_on_empty_axis_text() -> None:
    response = _FakeResponse(
        [
            _FakeToolUseBlock(
                TOOL_NAME,
                {
                    "winning_frame_id": "a",
                    "subject_placement": "   ",
                    "edge_amputations": "y",
                    "incidental_distractions": "z",
                },
            )
        ]
    )
    with pytest.raises(CmpCallError):
        parse_tool_use_response(response, ("a", "b"))


def test_parse_tool_use_response_null_tiebreaker_becomes_none() -> None:
    response = _FakeResponse(
        [
            _FakeToolUseBlock(
                TOOL_NAME,
                {
                    "winning_frame_id": "a",
                    "subject_placement": "x",
                    "edge_amputations": "y",
                    "incidental_distractions": "z",
                    "tiebreaker": None,
                },
            )
        ]
    )
    verdict = parse_tool_use_response(response, ("a", "b"))
    assert verdict.tiebreaker is None


# --- parse_tool_use_response replayed against a genuine recorded live -----
# --- call (scripts/record_cmp_fixture.py, this session) -------------------

_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "cmp" / "wide_vs_tight_with_walker.json"
)


def test_parse_tool_use_response_replays_genuine_recorded_api_call() -> None:
    from anthropic.types import Message

    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    response = Message.model_validate(data)

    verdict = parse_tool_use_response(response, ("wide", "tight"))

    assert verdict.winner_frame_id in ("wide", "tight")
    assert verdict.subject_placement
    assert verdict.edge_amputations
    assert verdict.incidental_distractions
    # The live model actually used the tiebreaker for this pair (a walker
    # figure only in "tight") - assert the shape, not a guess at wording.
    assert verdict.tiebreaker
