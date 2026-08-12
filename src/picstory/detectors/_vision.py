"""Shared plumbing for the judgment-dependent (Anthropic API vision-call) detectors.

QUEUE.md item 4 / CLAUDE.md's API-discipline rule: a model-call detector embeds
the taxonomy item's Detection text verbatim in its prompt and returns structured
output naming the ID. This module owns the mechanical half of that contract -
the actual API call, the structured-output tool schema, response parsing - so
it isn't duplicated in every per-ID module. No item-specific detection wording
lives here; each per-ID module supplies its own ID and reads its Detection text
from `schema.taxonomy_detection_text()` (verbatim from TAXONOMY.md, never a
local copy that could drift).

The call boundary is `VisionCaller` (`VisionRequest -> VisionVerdict`), injected
via `judge(..., caller=...)`. Production code gets `default_caller()`, built
from the `anthropic` SDK and `ANTHROPIC_API_KEY` (D-001's amendment allowing
calls to api.anthropic.com). Tests always inject a fake caller - CLAUDE.md
requires the suite to run offline and never make live calls.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import Callable, Protocol

from PIL import Image

from picstory.frame import Frame
from picstory.schema import Finding

# Sonnet, not Opus: these are bounded-cost per-frame judgment calls under an
# owner spend cap (CLAUDE.md), not the flagship reasoning tier the task needs.
MODEL = "claude-sonnet-5"

TOOL_NAME = "report_taxonomy_finding"


@dataclass(frozen=True)
class SubPatternSpec:
    """An optional closed-vocabulary field a detector can ask the model to
    name alongside its yes/no verdict - TAXONOMY.md's profile-layer sub-
    pattern (QUEUE.md item 12; e.g. F06's Profile note: "which edge").
    Enum-constrained in the tool schema itself, so the model is structurally
    bound to the same closed vocabulary the rest of this taxonomy uses -
    not a free-text rationale a caller would have to parse for keywords.
    """

    field_name: str
    enum_values: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class VisionRequest:
    taxonomy_id: str
    detection_text: str
    image_bytes: bytes
    media_type: str = "image/jpeg"
    sub_pattern: SubPatternSpec | None = None


@dataclass(frozen=True)
class VisionVerdict:
    """The structured output a caller must return for one frame's evaluation."""

    taxonomy_id: str
    detected: bool
    rationale: str
    sub_pattern: str | None = None


class VisionCaller(Protocol):
    def __call__(self, request: VisionRequest) -> VisionVerdict: ...


class VisionCallError(RuntimeError):
    """Raised when the API call fails, or its output doesn't fit the structured schema."""


def _tool_schema(taxonomy_id: str, sub_pattern: SubPatternSpec | None = None) -> dict:
    properties = {
        "taxonomy_id": {
            "type": "string",
            "const": taxonomy_id,
            "description": "Must echo the taxonomy ID under evaluation, unchanged.",
        },
        "detected": {
            "type": "boolean",
            "description": "Whether the Detection text's condition is present in this photo.",
        },
        "rationale": {
            "type": "string",
            "description": "One or two sentences: what in the frame supports this verdict.",
        },
    }
    if sub_pattern is not None:
        properties[sub_pattern.field_name] = {
            "type": "string",
            "enum": list(sub_pattern.enum_values),
            "description": (
                f"Required when detected is true: {sub_pattern.description} "
                "Omit this field entirely when detected is false."
            ),
        }
    return {
        "name": TOOL_NAME,
        "description": (
            f"Report whether the described condition for taxonomy item {taxonomy_id} "
            "is present in this photo."
        ),
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": ["taxonomy_id", "detected", "rationale"],
        },
    }


def _prompt(taxonomy_id: str, detection_text: str, sub_pattern: SubPatternSpec | None = None) -> str:
    sub_pattern_instruction = (
        f"If detected, also set '{sub_pattern.field_name}': {sub_pattern.description}\n\n"
        if sub_pattern is not None
        else ""
    )
    return (
        "You are a detector for exactly one item in a closed photo-coaching "
        f"taxonomy, item {taxonomy_id}. Evaluate ONLY the condition below against "
        "the attached photo. Do not consider any other aspect of the photo's "
        "quality, and do not substitute a generic aesthetic judgment for this "
        "specific condition.\n\n"
        f"Detection: {detection_text}\n\n"
        f"{sub_pattern_instruction}"
        f"Call {TOOL_NAME} with your verdict."
    )


def _encode_jpeg(frame: Frame) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(frame.rgb).save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _verdict_from_tool_input(
    data: dict, taxonomy_id: str, sub_pattern: SubPatternSpec | None = None
) -> VisionVerdict:
    if data.get("taxonomy_id") != taxonomy_id:
        raise VisionCallError(
            f"structured output named {data.get('taxonomy_id')!r}, expected {taxonomy_id!r}"
        )
    if not isinstance(data.get("detected"), bool):
        raise VisionCallError(f"structured output for {taxonomy_id} missing boolean 'detected'")
    rationale = (data.get("rationale") or "").strip()
    if not rationale:
        raise VisionCallError(f"structured output for {taxonomy_id} missing rationale")
    sub_pattern_value = None
    if sub_pattern is not None and data["detected"]:
        sub_pattern_value = data.get(sub_pattern.field_name)
        if sub_pattern_value not in sub_pattern.enum_values:
            raise VisionCallError(
                f"structured output for {taxonomy_id} detected=true but "
                f"{sub_pattern.field_name!r} is {sub_pattern_value!r}, "
                f"expected one of {sub_pattern.enum_values}"
            )
    return VisionVerdict(
        taxonomy_id=taxonomy_id, detected=data["detected"], rationale=rationale, sub_pattern=sub_pattern_value
    )


def parse_tool_use_response(
    response, taxonomy_id: str, sub_pattern: SubPatternSpec | None = None
) -> VisionVerdict:
    """Extract the `report_taxonomy_finding` tool call from a raw SDK Message.

    Exposed (not `_`-prefixed) so tests can replay a hand-built response shaped
    like the real SDK's without going through a live call.
    """
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == TOOL_NAME:
            return _verdict_from_tool_input(block.input, taxonomy_id, sub_pattern)
    raise VisionCallError(f"no {TOOL_NAME} tool_use block in response for {taxonomy_id}")


def default_caller() -> VisionCaller:
    """Production caller: the real Anthropic API (D-001's amendment).

    Reads PICSTORY_VISION_KEY first, falling back to ANTHROPIC_API_KEY. Per
    D-006: this platform's cloud sessions filter the reserved
    ANTHROPIC_API_KEY name out of the environment, so the owner provisions
    the same key under PICSTORY_VISION_KEY as well.
    """
    import os

    import anthropic

    api_key = os.environ.get("PICSTORY_VISION_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    def call(request: VisionRequest) -> VisionVerdict:
        image_b64 = base64.standard_b64encode(request.image_bytes).decode("ascii")
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=512,
                tools=[_tool_schema(request.taxonomy_id, request.sub_pattern)],
                tool_choice={"type": "tool", "name": TOOL_NAME},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": request.media_type,
                                    "data": image_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": _prompt(request.taxonomy_id, request.detection_text, request.sub_pattern),
                            },
                        ],
                    }
                ],
            )
        except anthropic.APIError as exc:
            raise VisionCallError(f"Anthropic API call failed for {request.taxonomy_id}: {exc}") from exc
        return parse_tool_use_response(response, request.taxonomy_id, request.sub_pattern)

    return call


def judge(
    frame: Frame,
    taxonomy_id: str,
    detection_text: str,
    *,
    caller: VisionCaller | None = None,
    sub_pattern: SubPatternSpec | None = None,
) -> Finding | None:
    """Run one judgment-dependent detector: `caller` decides yes/no against `detection_text`.

    Returns a Finding for `taxonomy_id` (rationale as its description) when
    detected, None otherwise. `caller` defaults to the live Anthropic API;
    every test injects a fake (CLAUDE.md: the suite runs offline).

    `sub_pattern` (QUEUE.md item 12) is opt-in, closed-vocabulary profile
    detail the model names alongside its verdict - e.g. F06's "which edge."
    Only detectors whose ID has a TAXONOMY.md Profile note may pass one
    (enforced by `Finding.__post_init__` via `schema.taxonomy_ids_with_subpattern`);
    every other detector leaves this `None` and behaves exactly as before.
    """
    caller = caller or default_caller()
    request = VisionRequest(
        taxonomy_id=taxonomy_id,
        detection_text=detection_text,
        image_bytes=_encode_jpeg(frame),
        sub_pattern=sub_pattern,
    )
    verdict = caller(request)
    if verdict.taxonomy_id != taxonomy_id:
        raise VisionCallError(
            f"caller returned a verdict for {verdict.taxonomy_id!r}, expected {taxonomy_id!r}"
        )
    if not verdict.detected:
        return None
    return Finding(taxonomy_id=taxonomy_id, description=verdict.rationale, sub_pattern=verdict.sub_pattern)
