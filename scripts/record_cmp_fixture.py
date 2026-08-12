"""One-off tool: make a small number of LIVE Anthropic API CMP calls and save
the raw responses under tests/fixtures/cmp/ (same precedent as D-006/
scripts/record_vision_fixtures.py, extended to CMP - QUEUE.md item 11).

Why this exists: CLAUDE.md's API-discipline rule asks for genuine recorded
fixtures, not hand-authored response shapes, wherever a live call is
practical. This session's sandbox has a working PICSTORY_VISION_KEY (unlike
the no-key sandbox D-006 originally diagnosed), so - the same as
record_vision_fixtures.py did for the per-ID vision detectors - this script
makes one real multi-image CMP call and records it, rather than leaving
tests/test_cmp.py's parse_tool_use_response coverage entirely hand-authored.
The test suite itself stays offline permanently (CLAUDE.md); this script is
the one place allowed to touch the network, run by hand, not by pytest.

Two synthetic-but-structured images (drawn with Pillow, not photographs -
none exist in this repo) simulate one near-duplicate group with genuine
differences across all three CMP axes, so the recorded call actually has
something to differentiate instead of two identical frames:

- wide:  the full monument, centered, no figure - a clean "record" shot.
- tight: the same scene reframed tighter (crops the monument's tip - an
  edge amputation) and adds a small walking figure mid-stride at the base
  (a story element - the CMP tiebreaker's own example shape).

Usage: uv run python scripts/record_cmp_fixture.py
Requires PICSTORY_VISION_KEY (or ANTHROPIC_API_KEY) in the environment.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from PIL import Image, ImageDraw

from _report import report  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from picstory.cmp import (  # noqa: E402
    TOOL_NAME,
    _prompt,
    _tool_schema,
    parse_tool_use_response,
)
from picstory.detectors._vision import MODEL, _encode_jpeg  # noqa: E402
from picstory.frame import Frame  # noqa: E402
from picstory.schema import cmp_rubric_text  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "cmp"


def _monument_scene(*, tight_crop: bool, with_walker: bool) -> np.ndarray:
    width, height = 512, 512
    image = Image.new("RGB", (width, height), (176, 214, 230))  # sky
    draw = ImageDraw.Draw(image)
    ground_y = int(height * 0.75)
    draw.rectangle([0, ground_y, width, height], fill=(120, 120, 110))  # ground

    tower_w = int(width * 0.14)
    tower_left = width // 2 - tower_w // 2
    tower_top = int(height * 0.08)
    draw.rectangle([tower_left, tower_top, tower_left + tower_w, ground_y], fill=(90, 90, 95))
    tip = [
        (tower_left, tower_top),
        (tower_left + tower_w, tower_top),
        (width // 2, int(height * 0.02)),
    ]
    draw.polygon(tip, fill=(90, 90, 95))

    if with_walker:
        fig_h = int(height * 0.16)
        fig_w = int(fig_h * 0.32)
        fig_x = int(width * 0.68)
        fig_y = ground_y - fig_h
        draw.ellipse([fig_x, fig_y, fig_x + fig_w, fig_y + fig_w], fill=(30, 30, 30))  # head
        # Mid-stride: legs splayed, not a static stance.
        draw.line([fig_x + fig_w // 2, fig_y + fig_w, fig_x, ground_y], fill=(30, 30, 30), width=4)
        draw.line(
            [fig_x + fig_w // 2, fig_y + fig_w, fig_x + fig_w + 6, ground_y],
            fill=(30, 30, 30),
            width=4,
        )

    array = np.array(image)
    if tight_crop:
        # Crop out the tower's tip and a walker-side sliver - an edge amputation.
        array = array[int(height * 0.05) :, : int(width * 0.9)]
        array = np.array(Image.fromarray(array).resize((width, height)))
    return array


def _frame(name: str, *, tight_crop: bool, with_walker: bool) -> Frame:
    rgb = _monument_scene(tight_crop=tight_crop, with_walker=with_walker)
    return Frame(frame_id=name, path=Path(f"{name}.jpg"), rgb=rgb, exif={})


def main() -> int:
    import os

    import anthropic

    api_key = os.environ.get("PICSTORY_VISION_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    key_source = (
        "PICSTORY_VISION_KEY"
        if os.environ.get("PICSTORY_VISION_KEY")
        else ("ANTHROPIC_API_KEY" if os.environ.get("ANTHROPIC_API_KEY") else "none")
    )
    if api_key is None:
        report(
            "record_cmp_fixture",
            "# record_cmp_fixture\n\nNo PICSTORY_VISION_KEY or ANTHROPIC_API_KEY in "
            "the environment. Nothing recorded.\n",
            "record_cmp_fixture: no key in environment, aborted",
            passed=False,
        )
        return 1

    client = anthropic.Anthropic(api_key=api_key)
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    frames = [
        _frame("wide", tight_crop=False, with_walker=False),
        _frame("tight", tight_crop=True, with_walker=True),
    ]
    frame_ids = tuple(f.frame_id for f in frames)
    rubric_text = cmp_rubric_text()
    content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64.standard_b64encode(_encode_jpeg(f)).decode("ascii"),
            },
        }
        for f in frames
    ]
    content.append({"type": "text", "text": _prompt(frame_ids, rubric_text)})

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=768,
            tools=[_tool_schema(frame_ids)],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[{"role": "user", "content": content}],
        )
    except Exception as exc:  # noqa: BLE001 - a blocked/failed call is reported, not fatal
        report(
            "record_cmp_fixture",
            f"# record_cmp_fixture\n\nlive call failed: {type(exc).__name__}: {exc}\n",
            f"record_cmp_fixture: live call failed via {key_source}",
            passed=False,
        )
        return 1

    verdict = parse_tool_use_response(response, frame_ids)  # fails loudly if shape is off

    fixture_name = "wide_vs_tight_with_walker.json"
    (FIXTURES_DIR / fixture_name).write_text(
        json.dumps(response.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    body = (
        "# record_cmp_fixture\n\n"
        f"key source: {key_source}\n"
        f"model: {MODEL}\n"
        f"recorded to {FIXTURES_DIR / fixture_name}\n\n"
        f"winner: {verdict.winner_frame_id}\n"
        f"subject_placement: {verdict.subject_placement}\n"
        f"edge_amputations: {verdict.edge_amputations}\n"
        f"incidental_distractions: {verdict.incidental_distractions}\n"
        f"tiebreaker: {verdict.tiebreaker}\n"
    )
    report(
        "record_cmp_fixture",
        body,
        f"record_cmp_fixture: recorded 1/1 via {key_source}, winner={verdict.winner_frame_id}",
        passed=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
