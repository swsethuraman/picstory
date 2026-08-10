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
class VisionRequest:
    taxonomy_id: str
    detection_text: str
    image_bytes: bytes
    media_type: str = "image/jpeg"


@dataclass(frozen=True)
class VisionVerdict:
    """The structured output a caller must return for one frame's evaluation."""

    taxonomy_id: str
    detected: bool
    rationale: str


class VisionCaller(Protocol):
    def __call__(self, request: VisionRequest) -> VisionVerdict: ...


class VisionCallError(RuntimeError):
    """Raised when the API call fails, or its output doesn't fit the structured schema."""


def _tool_schema(taxonomy_id: str) -> dict:
    return {
        "name": TOOL_NAME,
        "description": (
            f"Report whether the described condition for taxonomy item {taxonomy_id} "
            "is present in this photo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
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
            },
            "required": ["taxonomy_id", "detected", "rationale"],
        },
    }


def _prompt(taxonomy_id: str, detection_text: str) -> str:
    return (
        "You are a detector for exactly one item in a closed photo-coaching "
        f"taxonomy, item {taxonomy_id}. Evaluate ONLY the condition below against "
        "the attached photo. Do not consider any other aspect of the photo's "
        "quality, and do not substitute a generic aesthetic judgment for this "
        "specific condition.\n\n"
        f"Detection: {detection_text}\n\n"
        f"Call {TOOL_NAME} with your verdict."
    )


def _encode_jpeg(frame: Frame) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(frame.rgb).save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _verdict_from_tool_input(data: dict, taxonomy_id: str) -> VisionVerdict:
    if data.get("taxonomy_id") != taxonomy_id:
        raise VisionCallError(
            f"structured output named {data.get('taxonomy_id')!r}, expected {taxonomy_id!r}"
        )
    if not isinstance(data.get("detected"), bool):
        raise VisionCallError(f"structured output for {taxonomy_id} missing boolean 'detected'")
    rationale = (data.get("rationale") or "").strip()
    if not rationale:
        raise VisionCallError(f"structured output for {taxonomy_id} missing rationale")
    return VisionVerdict(taxonomy_id=taxonomy_id, detected=data["detected"], rationale=rationale)


def parse_tool_use_response(response, taxonomy_id: str) -> VisionVerdict:
    """Extract the `report_taxonomy_finding` tool call from a raw SDK Message.

    Exposed (not `_`-prefixed) so tests can replay a hand-built response shaped
    like the real SDK's without going through a live call.
    """
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == TOOL_NAME:
            return _verdict_from_tool_input(block.input, taxonomy_id)
    raise VisionCallError(f"no {TOOL_NAME} tool_use block in response for {taxonomy_id}")


def default_caller() -> VisionCaller:
    """Production caller: the real Anthropic API (D-001's amendment)."""
    import anthropic

    client = anthropic.Anthropic()

    def call(request: VisionRequest) -> VisionVerdict:
        image_b64 = base64.standard_b64encode(request.image_bytes).decode("ascii")
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=512,
                tools=[_tool_schema(request.taxonomy_id)],
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
                            {"type": "text", "text": _prompt(request.taxonomy_id, request.detection_text)},
                        ],
                    }
                ],
            )
        except anthropic.APIError as exc:
            raise VisionCallError(f"Anthropic API call failed for {request.taxonomy_id}: {exc}") from exc
        return parse_tool_use_response(response, request.taxonomy_id)

    return call


def judge(
    frame: Frame,
    taxonomy_id: str,
    detection_text: str,
    *,
    caller: VisionCaller | None = None,
) -> Finding | None:
    """Run one judgment-dependent detector: `caller` decides yes/no against `detection_text`.

    Returns a Finding for `taxonomy_id` (rationale as its description) when
    detected, None otherwise. `caller` defaults to the live Anthropic API;
    every test injects a fake (CLAUDE.md: the suite runs offline).
    """
    caller = caller or default_caller()
    request = VisionRequest(
        taxonomy_id=taxonomy_id,
        detection_text=detection_text,
        image_bytes=_encode_jpeg(frame),
    )
    verdict = caller(request)
    if verdict.taxonomy_id != taxonomy_id:
        raise VisionCallError(
            f"caller returned a verdict for {verdict.taxonomy_id!r}, expected {taxonomy_id!r}"
        )
    if not verdict.detected:
        return None
    return Finding(taxonomy_id=taxonomy_id, description=verdict.rationale)
