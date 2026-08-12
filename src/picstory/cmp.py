"""CMP — the three-frame comparison rubric (QUEUE.md item 11).

TAXONOMY.md §CMP: near-duplicate frames get scored and explained on exactly
three axes (subject placement, edge amputations, incidental distractions),
with a story-element tiebreaker. TAXONOMY.md's own output-mapping table is
explicit that this output draws on "The CMP rubric, exclusively" - not F/S
taxonomy IDs, so `schema.Comparison` carries none.

This is judgment across multiple images at once ("which frame cuts what,"
"which one has a mid-stride walker") - not decidable from pixel math the way
Stage 1's local detectors are, and not a single-frame judgment either (unlike
F04-F15/S01-S04's `detectors._vision.judge`). So this module has its own
small call/parse plumbing, parallel to `detectors._vision` but shaped for N
images in one call rather than one: `schema.cmp_rubric_text()` is the
verbatim-source-of-truth text embedded in the prompt (CLAUDE.md's
API-discipline rule extended to CMP - see that function's docstring for why
the whole rubric section stands in for the "Detection text" role F/S items
have), structured output is enforced via a forced tool call, and the winning
frame is constrained to actually be one of the frames sent (`_tool_schema`'s
`winning_frame_id` enum), not a free-text ID the model could invent.

`detectors.f03.group_near_duplicates` (batch context) supplies the groups
this runs over: CMP judges "near-duplicate groups" (QUEUE.md item 11) - the
same runs F03 already identifies as "copies, not variations" are exactly the
near-identical frames CMP is meant to differentiate between (TAXONOMY.md's
own framing: "The failure of *taking* undifferentiated duplicates is F03;
this is how the app *judges between* them"). Wiring that lookup into the
batch pipeline lives in scripts/analyze_batch.py, the same split F03 itself
uses between this module (the real logic) and that script (where it runs).
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Protocol

from picstory.detectors._vision import MODEL, _encode_jpeg
from picstory.frame import Frame
from picstory.schema import Comparison, cmp_rubric_text

TOOL_NAME = "report_cmp_comparison"


@dataclass(frozen=True)
class CmpRequest:
    frame_ids: tuple[str, ...]
    images: tuple[bytes, ...]  # same order as frame_ids
    rubric_text: str
    media_type: str = "image/jpeg"


@dataclass(frozen=True)
class CmpVerdict:
    """The structured output a caller must return for one group's comparison."""

    winner_frame_id: str
    subject_placement: str
    edge_amputations: str
    incidental_distractions: str
    tiebreaker: str | None = None


class CmpCaller(Protocol):
    def __call__(self, request: CmpRequest) -> CmpVerdict: ...


class CmpCallError(RuntimeError):
    """Raised when the comparison call fails, or its output doesn't fit the structured schema."""


def _tool_schema(frame_ids: tuple[str, ...]) -> dict:
    return {
        "name": TOOL_NAME,
        "description": (
            "Report the three-frame comparison rubric's verdict across the attached "
            "near-duplicate frames."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "winning_frame_id": {
                    "type": "string",
                    "enum": list(frame_ids),
                    "description": "The frame_id of the winning frame, exactly as given below.",
                },
                "subject_placement": {
                    "type": "string",
                    "description": "What differs, frame to frame, in subject placement.",
                },
                "edge_amputations": {
                    "type": "string",
                    "description": "What differs, frame to frame, in edge amputations.",
                },
                "incidental_distractions": {
                    "type": "string",
                    "description": "What differs, frame to frame, in incidental distractions.",
                },
                "tiebreaker": {
                    "type": ["string", "null"],
                    "description": (
                        "If a story element (e.g. a mid-stride walker, a gaze line) "
                        "decided the winner, name it here; null if the three axes "
                        "alone settled it."
                    ),
                },
            },
            "required": [
                "winning_frame_id",
                "subject_placement",
                "edge_amputations",
                "incidental_distractions",
            ],
        },
    }


def _prompt(frame_ids: tuple[str, ...], rubric_text: str) -> str:
    numbered = "\n".join(f"{i + 1}. frame_id {fid!r}" for i, fid in enumerate(frame_ids))
    return (
        "You are comparing near-duplicate photos of the same subject under a "
        "closed, three-axis comparison rubric. The images below are attached "
        "in this exact order:\n"
        f"{numbered}\n\n"
        f"Rubric:\n{rubric_text}\n\n"
        "Score and explain on exactly the three named axes, apply the "
        "tiebreaker only if the axes alone do not settle it, and name the "
        f"winning frame_id exactly as given above. Call {TOOL_NAME} with your verdict."
    )


def _verdict_from_tool_input(data: dict, frame_ids: tuple[str, ...]) -> CmpVerdict:
    winner = data.get("winning_frame_id")
    if winner not in frame_ids:
        raise CmpCallError(
            f"structured output named winning_frame_id {winner!r}, not among {frame_ids!r}"
        )
    axis_values: dict[str, str] = {}
    for axis_name in ("subject_placement", "edge_amputations", "incidental_distractions"):
        value = (data.get(axis_name) or "").strip()
        if not value:
            raise CmpCallError(f"structured output missing non-empty {axis_name!r}")
        axis_values[axis_name] = value
    tiebreaker = data.get("tiebreaker")
    tiebreaker = tiebreaker.strip() if isinstance(tiebreaker, str) and tiebreaker.strip() else None
    return CmpVerdict(winner_frame_id=winner, tiebreaker=tiebreaker, **axis_values)


def parse_tool_use_response(response, frame_ids: tuple[str, ...]) -> CmpVerdict:
    """Extract the `report_cmp_comparison` tool call from a raw SDK Message.

    Exposed (not `_`-prefixed) so tests can replay a hand-built response the
    same way `_vision.parse_tool_use_response` does, without a live call.
    """
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == TOOL_NAME:
            return _verdict_from_tool_input(block.input, frame_ids)
    raise CmpCallError(f"no {TOOL_NAME} tool_use block in response")


def default_caller() -> CmpCaller:
    """Production caller: the real Anthropic API, same key resolution as `_vision.default_caller`."""
    import os

    import anthropic

    api_key = os.environ.get("PICSTORY_VISION_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    def call(request: CmpRequest) -> CmpVerdict:
        content: list[dict] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": request.media_type,
                    "data": base64.standard_b64encode(image_bytes).decode("ascii"),
                },
            }
            for image_bytes in request.images
        ]
        content.append({"type": "text", "text": _prompt(request.frame_ids, request.rubric_text)})
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=768,
                tools=[_tool_schema(request.frame_ids)],
                tool_choice={"type": "tool", "name": TOOL_NAME},
                messages=[{"role": "user", "content": content}],
            )
        except anthropic.APIError as exc:
            raise CmpCallError(f"Anthropic API call failed for CMP comparison: {exc}") from exc
        return parse_tool_use_response(response, request.frame_ids)

    return call


def compare_group(frames: list[Frame], *, caller: CmpCaller | None = None) -> Comparison:
    """Run one CMP comparison over a near-duplicate group.

    `frames` is the group in batch order (e.g. one of
    `detectors.f03.group_near_duplicates`'s runs, resolved back to `Frame`
    objects) - not the whole batch; at least 2 frames, same lower bound
    `schema.Comparison` itself enforces. `caller` defaults to the live
    Anthropic API; every test injects a fake (CLAUDE.md: the suite runs
    offline).
    """
    if len(frames) < 2:
        raise ValueError("a CMP comparison needs at least 2 frames")
    caller = caller or default_caller()
    frame_ids = tuple(f.frame_id for f in frames)
    request = CmpRequest(
        frame_ids=frame_ids,
        images=tuple(_encode_jpeg(f) for f in frames),
        rubric_text=cmp_rubric_text(),
    )
    verdict = caller(request)
    if verdict.winner_frame_id not in frame_ids:
        raise CmpCallError(
            f"caller returned winner {verdict.winner_frame_id!r}, not among {frame_ids!r}"
        )
    return Comparison(
        group=list(frame_ids),
        winner_frame_id=verdict.winner_frame_id,
        subject_placement=verdict.subject_placement,
        edge_amputations=verdict.edge_amputations,
        incidental_distractions=verdict.incidental_distractions,
        tiebreaker=verdict.tiebreaker,
    )
