"""Tests for src/picstory/schema.py (QUEUE.md Stage 1, item 1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from picstory.schema import (
    SCHEMA_VERSION,
    AnalysisOutput,
    Finding,
    FrameAnalysis,
    Habit,
    Pick,
    SchemaError,
    taxonomy_detection_text,
    taxonomy_ids,
    taxonomy_reinforcement_text,
)

ROOT = Path(__file__).resolve().parents[1]


def test_taxonomy_ids_matches_frozen_count() -> None:
    ids = taxonomy_ids()
    assert len(ids) == 20, f"expected 20 frozen IDs (15 F + 4 S + 1 R), got {len(ids)}: {sorted(ids)}"
    assert "F01" in ids and "S01" in ids and "R01" in ids


def test_finding_classified_needs_no_description() -> None:
    f = Finding(taxonomy_id="F06")
    assert f.to_dict() == {"taxonomy_id": "F06", "description": None}


def test_finding_unclassified_requires_description() -> None:
    with pytest.raises(SchemaError):
        Finding(taxonomy_id="unclassified")
    with pytest.raises(SchemaError):
        Finding(taxonomy_id="unclassified", description="   ")


def test_finding_unclassified_with_description_ok() -> None:
    f = Finding(taxonomy_id="unclassified", description="a dog photobombing, no taxonomy match")
    assert f.taxonomy_id == "unclassified"


def test_finding_rejects_unknown_id() -> None:
    with pytest.raises(SchemaError):
        Finding(taxonomy_id="F99")


def test_pick_reasons_must_be_s_items() -> None:
    with pytest.raises(SchemaError):
        Pick(frame_id="IMG_1.jpg", reasons=["F06"])


def test_pick_disqualifiers_must_be_f_items() -> None:
    with pytest.raises(SchemaError):
        Pick(frame_id="IMG_1.jpg", disqualifiers=["S01"])


def test_pick_valid() -> None:
    p = Pick(frame_id="IMG_1.jpg", reasons=["S01"], disqualifiers=["F06"])
    assert p.to_dict()["frame_id"] == "IMG_1.jpg"


def test_habit_rejects_r_item() -> None:
    with pytest.raises(SchemaError):
        Habit(taxonomy_id="R01", description="haze rule is not a habit")


def test_habit_requires_description() -> None:
    with pytest.raises(SchemaError):
        Habit(taxonomy_id="F06", description="")


def test_habit_valid() -> None:
    h = Habit(taxonomy_id="F06", description="edge intrusion, right third, 4 of 6 frames")
    assert h.taxonomy_id == "F06"


def test_analysis_output_default_version() -> None:
    out = AnalysisOutput()
    assert out.schema_version == SCHEMA_VERSION
    assert out.frames == []
    assert out.pick is None
    assert out.habit is None


def test_analysis_output_rejects_stale_version() -> None:
    with pytest.raises(SchemaError):
        AnalysisOutput(schema_version="0.9")


def test_analysis_output_pick_must_reference_known_frame() -> None:
    with pytest.raises(SchemaError):
        AnalysisOutput(
            frames=[FrameAnalysis(frame_id="IMG_1.jpg")],
            pick=Pick(frame_id="IMG_2.jpg"),
        )


def test_analysis_output_roundtrip_json() -> None:
    out = AnalysisOutput(
        frames=[
            FrameAnalysis(
                frame_id="IMG_1.jpg",
                findings=[
                    Finding(taxonomy_id="F06"),
                    Finding(taxonomy_id="unclassified", description="a kite in the sky, no match"),
                ],
            )
        ],
        pick=Pick(frame_id="IMG_1.jpg", reasons=["S01"], disqualifiers=["F06"]),
        habit=Habit(taxonomy_id="F06", description="edge intrusion recurring"),
    )
    round_tripped = AnalysisOutput.from_json(out.to_json())
    assert round_tripped == out


def test_analysis_output_single_photo_has_no_pick_or_habit() -> None:
    """Stage 1 runs one photo at a time (QUEUE.md item 1); pick/habit need a batch."""
    out = AnalysisOutput(frames=[FrameAnalysis(frame_id="IMG_1.jpg", findings=[Finding(taxonomy_id="F01")])])
    assert out.pick is None
    assert out.habit is None
    json.loads(out.to_json())  # serializes without error even with both absent


def test_json_schema_file_ids_match_taxonomy() -> None:
    """schema/analysis.json enumerates IDs statically; guard it against TAXONOMY.md drift."""
    schema = json.loads((ROOT / "schema" / "analysis.json").read_text(encoding="utf-8"))
    enumerated = set(schema["$defs"]["taxonomyOrUnclassifiedId"]["enum"])
    expected = taxonomy_ids() | {"unclassified"}
    assert enumerated == expected


def test_json_schema_file_is_valid_json() -> None:
    schema = json.loads((ROOT / "schema" / "analysis.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION


def test_taxonomy_reinforcement_text_matches_taxonomy_md_verbatim() -> None:
    # Hand-transcribed from TAXONOMY.md so this test fails if either the
    # parser or the frozen source drifts - same guard style as the existing
    # detection-text tests in test_vision_detectors.py.
    assert taxonomy_reinforcement_text("S01") == (
        "These consistently outrank empty landmark shots — keep leading with people."
    )
    assert taxonomy_reinforcement_text("S04") == (
        "Produced the trip's best still-life frame (the red vessel in the white niche)."
    )


def test_taxonomy_reinforcement_text_missing_for_f_and_r_items() -> None:
    # F/R items have no Reinforcement bullet in TAXONOMY.md - only S-items do.
    with pytest.raises(SchemaError):
        taxonomy_reinforcement_text("F06")
    with pytest.raises(SchemaError):
        taxonomy_reinforcement_text("R01")


def test_taxonomy_reinforcement_text_distinct_from_detection_text() -> None:
    assert taxonomy_reinforcement_text("S01") != taxonomy_detection_text("S01")
