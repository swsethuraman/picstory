"""One-off tool: make a small number of LIVE Anthropic API vision calls and
save the raw responses under tests/fixtures/vision/ (DECISIONS.md D-006).

Why this exists: tests/test_vision_detectors.py's parse_tool_use_response
tests were, until this session, hand-authored objects shaped like the
documented Anthropic Messages API tool_use response - never a live call,
because no agent BUILDER session had a usable API key (D-006). D-006's
ruling provisions PICSTORY_VISION_KEY for exactly this purpose and asks the
next BUILDER session to record genuine fixtures once, here, then swap them
into the test suite. The test suite itself stays offline permanently
(CLAUDE.md) - this script is the one place that's allowed to touch the
network, run by hand, not by pytest.

Two synthetic-but-structured images (drawn with Pillow, not photographs -
none exist in this repo) exercise two taxonomy IDs each, so the recorded
set has real variation instead of one repeated shape:

- landmark_alone:        a lone tall monument, no human figure.
- landmark_with_figure:  the same monument, plus a small human silhouette
                          at its base.

F13 (missing human scale) and S01 (human in the foreground) are evaluated
against both, for 4 live calls total - "a small number," per the ruling.

A third scene, edge_intrusion_right, adds a dark shoulder-like mass along
the right edge of the lone-monument scene. F06 (edge intrusion) is
evaluated against it and against landmark_alone (clean), for 2 more live
calls - QUEUE.md item 12 (the running profile) needs a genuine recorded
example of F06's `edge` sub-pattern field (see
`picstory.detectors.f06.EDGE_SUB_PATTERN`), not just a hand-authored one.

6 live calls total.

Usage: uv run python scripts/record_vision_fixtures.py
Requires PICSTORY_VISION_KEY (or ANTHROPIC_API_KEY) in the environment.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from PIL import Image, ImageDraw

from _report import report  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from picstory.detectors._vision import (  # noqa: E402
    MODEL,
    TOOL_NAME,
    SubPatternSpec,
    _encode_jpeg,
    _prompt,
    _tool_schema,
    parse_tool_use_response,
)
from picstory.detectors.f06 import EDGE_SUB_PATTERN  # noqa: E402
from picstory.frame import Frame  # noqa: E402
from picstory.schema import taxonomy_detection_text  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "vision"


def _landmark_scene(*, with_figure: bool) -> np.ndarray:
    """A drawn (not photographed) scene: sky, ground, a tall monument, optionally a figure."""
    width, height = 512, 512
    image = Image.new("RGB", (width, height), (176, 214, 230))  # sky
    draw = ImageDraw.Draw(image)
    ground_y = int(height * 0.75)
    draw.rectangle([0, ground_y, width, height], fill=(120, 120, 110))  # ground

    tower_w = int(width * 0.14)
    tower_left = width // 2 - tower_w // 2
    draw.rectangle([tower_left, int(height * 0.08), tower_left + tower_w, ground_y], fill=(90, 90, 95))
    tip = [
        (tower_left, int(height * 0.08)),
        (tower_left + tower_w, int(height * 0.08)),
        (width // 2, int(height * 0.02)),
    ]
    draw.polygon(tip, fill=(90, 90, 95))

    if with_figure:
        fig_h = int(height * 0.16)
        fig_w = int(fig_h * 0.32)
        fig_x = int(width * 0.30)
        fig_y = ground_y - fig_h
        draw.ellipse(
            [fig_x, fig_y, fig_x + fig_w, fig_y + fig_w], fill=(30, 30, 30)
        )  # head
        draw.rectangle(
            [fig_x, fig_y + fig_w, fig_x + fig_w, fig_y + fig_h], fill=(30, 30, 30)
        )  # body

    return np.array(image)


def _edge_intrusion_scene() -> np.ndarray:
    """The lone-monument scene, plus a dark shoulder-like mass entering the right edge."""
    image = Image.fromarray(_landmark_scene(with_figure=False))
    draw = ImageDraw.Draw(image)
    width, height = image.size
    intrusion_w = int(width * 0.16)
    top = int(height * 0.28)
    bottom = int(height * 0.78)
    draw.ellipse([width - intrusion_w, top, width + intrusion_w // 2, bottom], fill=(32, 28, 26))
    return np.array(image)


def _frame(name: str, *, with_figure: bool) -> Frame:
    rgb = _landmark_scene(with_figure=with_figure)
    return Frame(frame_id=name, path=Path(f"{name}.jpg"), rgb=rgb, exif={})


def _record_one(
    client, image_name: str, frame: Frame, taxonomy_id: str, sub_pattern: SubPatternSpec | None = None
) -> dict:
    """Make one live call, verify it parses, save the raw response, return a summary row."""
    import base64

    detection_text = taxonomy_detection_text(taxonomy_id)
    image_b64 = base64.standard_b64encode(_encode_jpeg(frame)).decode("ascii")
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        tools=[_tool_schema(taxonomy_id, sub_pattern)],
        tool_choice={"type": "tool", "name": TOOL_NAME},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64},
                    },
                    {"type": "text", "text": _prompt(taxonomy_id, detection_text, sub_pattern)},
                ],
            }
        ],
    )
    verdict = parse_tool_use_response(response, taxonomy_id, sub_pattern)  # fails loudly if shape is off

    fixture_name = f"{taxonomy_id.lower()}_{image_name}.json"
    (FIXTURES_DIR / fixture_name).write_text(
        json.dumps(response.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "fixture": fixture_name,
        "taxonomy_id": taxonomy_id,
        "image": image_name,
        "detected": verdict.detected,
        "rationale": verdict.rationale,
        "sub_pattern": verdict.sub_pattern,
    }


def main() -> int:
    import anthropic
    import os

    api_key = os.environ.get("PICSTORY_VISION_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    key_source = (
        "PICSTORY_VISION_KEY"
        if os.environ.get("PICSTORY_VISION_KEY")
        else ("ANTHROPIC_API_KEY" if os.environ.get("ANTHROPIC_API_KEY") else "none")
    )
    if api_key is None:
        report(
            "record_vision_fixtures",
            "# record_vision_fixtures\n\nNo PICSTORY_VISION_KEY or ANTHROPIC_API_KEY in "
            "the environment. Nothing recorded.\n",
            "record_vision_fixtures: no key in environment, aborted",
            passed=False,
        )
        return 1

    client = anthropic.Anthropic(api_key=api_key)
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    images = {
        "landmark_alone": _frame("landmark_alone", with_figure=False),
        "landmark_with_figure": _frame("landmark_with_figure", with_figure=True),
        "edge_intrusion_right": Frame(
            frame_id="edge_intrusion_right", path=Path("edge_intrusion_right.jpg"),
            rgb=_edge_intrusion_scene(), exif={},
        ),
    }
    calls = [
        ("landmark_alone", "F13", None),
        ("landmark_with_figure", "F13", None),
        ("landmark_alone", "S01", None),
        ("landmark_with_figure", "S01", None),
        ("landmark_alone", "F06", EDGE_SUB_PATTERN),
        ("edge_intrusion_right", "F06", EDGE_SUB_PATTERN),
    ]

    rows = []
    failures = []
    for image_name, taxonomy_id, sub_pattern in calls:
        try:
            rows.append(_record_one(client, image_name, images[image_name], taxonomy_id, sub_pattern))
        except Exception as exc:  # noqa: BLE001 - a blocked/failed call is reported, not fatal to the batch
            failures.append(f"{taxonomy_id} / {image_name}: {type(exc).__name__}: {exc}")

    body_lines = [
        "# record_vision_fixtures",
        "",
        f"key source: {key_source}",
        f"model: {MODEL}",
        f"{len(rows)}/{len(calls)} live calls recorded to {FIXTURES_DIR}",
        "",
        "## Recorded",
        "",
    ]
    for row in rows:
        sub_pattern_note = f", edge={row['sub_pattern']}" if row["sub_pattern"] else ""
        body_lines.append(
            f"- {row['fixture']}: {row['taxonomy_id']} on {row['image']} -> "
            f"detected={row['detected']}{sub_pattern_note} ({row['rationale']})"
        )
    if failures:
        body_lines += ["", "## Failed", ""]
        body_lines += [f"- {f}" for f in failures]

    report(
        "record_vision_fixtures",
        "\n".join(body_lines) + "\n",
        f"record_vision_fixtures: {len(rows)}/{len(calls)} recorded via {key_source}",
        passed=not failures,
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
