"""Tests for src/picstory/schema.py (QUEUE.md Stage 1, item 1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from picstory.schema import (
    SCHEMA_VERSION,
    AnalysisOutput,
    Comparison,
    Finding,
    FrameAnalysis,
    Habit,
    Pick,
    Rule,
    SchemaError,
    cmp_rubric_text,
    taxonomy_correction_text,
    taxonomy_detection_text,
    taxonomy_ids,
    taxonomy_ids_with_subpattern,
    taxonomy_reinforcement_text,
    taxonomy_rule_text,
)

ROOT = Path(__file__).resolve().parents[1]


def test_taxonomy_ids_matches_frozen_count() -> None:
    ids = taxonomy_ids()
    assert len(ids) == 20, f"expected 20 frozen IDs (15 F + 4 S + 1 R), got {len(ids)}: {sorted(ids)}"
    assert "F01" in ids and "S01" in ids and "R01" in ids


def test_finding_classified_needs_no_description() -> None:
    f = Finding(taxonomy_id="F06")
    assert f.to_dict() == {"taxonomy_id": "F06", "description": None, "sub_pattern": None}


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


def test_taxonomy_ids_with_subpattern_parses_f06_profile_note() -> None:
    # TAXONOMY.md v1.1: F06 is the only item with a "- **Profile note:**"
    # bullet ("Directional sub-patterns ... are per-user traits tracked by
    # the profile, not separate taxonomy items"). Parsed, not hardcoded -
    # same single-source-of-truth reasoning as taxonomy_detection_text.
    assert taxonomy_ids_with_subpattern() == frozenset({"F06"})


def test_finding_sub_pattern_allowed_on_documented_id() -> None:
    f = Finding(taxonomy_id="F06", description="stranger's shoulder", sub_pattern="right")
    assert f.sub_pattern == "right"
    assert f.to_dict() == {"taxonomy_id": "F06", "description": "stranger's shoulder", "sub_pattern": "right"}


def test_finding_sub_pattern_rejected_on_undocumented_id() -> None:
    # F01 has no TAXONOMY.md Profile note - only F06 does.
    with pytest.raises(SchemaError):
        Finding(taxonomy_id="F01", sub_pattern="right")


def test_finding_sub_pattern_rejects_blank_string() -> None:
    with pytest.raises(SchemaError):
        Finding(taxonomy_id="F06", sub_pattern="   ")


def test_finding_sub_pattern_defaults_to_none() -> None:
    assert Finding(taxonomy_id="F06").sub_pattern is None


def test_finding_from_dict_roundtrips_sub_pattern() -> None:
    f = Finding.from_dict({"taxonomy_id": "F06", "description": "x", "sub_pattern": "left"})
    assert f.sub_pattern == "left"


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


def test_taxonomy_correction_text_matches_taxonomy_md_verbatim() -> None:
    # Hand-transcribed from TAXONOMY.md - same drift guard as the
    # Reinforcement-text test above.
    assert taxonomy_correction_text("F01") == (
        "Stay at true optical focal lengths (1x / 2x / 5x). Need tighter? "
        "Move closer, or crop in edit."
    )
    assert taxonomy_correction_text("F06") == (
        "Sweep all four edges before pressing the shutter. Commit fully: a "
        "whole label or none. Crop as salvage."
    )


def test_taxonomy_correction_text_missing_for_s_and_r_items() -> None:
    # Only F-items have a Correction bullet - S-items have Reinforcement
    # instead, R01 has neither.
    with pytest.raises(SchemaError):
        taxonomy_correction_text("S01")
    with pytest.raises(SchemaError):
        taxonomy_correction_text("R01")


def test_taxonomy_correction_text_distinct_from_detection_text() -> None:
    assert taxonomy_correction_text("F01") != taxonomy_detection_text("F01")


def test_cmp_rubric_text_contains_the_three_axes_and_tiebreaker_verbatim() -> None:
    # Hand-transcribed from TAXONOMY.md's §CMP section - same drift guard
    # style as the Detection/Reinforcement/Correction text tests above, but
    # as verbatim substrings (not full equality): CMP's own text spans
    # several paragraphs, not one bullet line.
    text = cmp_rubric_text()
    assert (
        "1. **Subject placement** — position relative to center / thirds / "
        "the composition's focal lines." in text
    )
    assert (
        "2. **Edge amputations** — which elements each frame cuts at its "
        "edges, and whether the cuts are committed or accidental." in text
    )
    assert (
        "3. **Incidental distractions** — exit signs, vehicles, bystanders, "
        "clutter present in one frame and absent in another." in text
    )
    assert (
        "**Tiebreaker:** a story element wins. A frame with a mid-stride "
        "walker or a gaze line beats a cleaner empty record of the same "
        "scene." in text
    )


def test_cmp_rubric_text_excludes_the_next_section_heading() -> None:
    # Regression guard for the regex's own end boundary: it must stop before
    # "## U", not swallow the next section.
    assert "## U" not in cmp_rubric_text()
    assert "unclassified" not in cmp_rubric_text()


def test_comparison_requires_at_least_two_frames() -> None:
    with pytest.raises(SchemaError):
        Comparison(
            group=["IMG_1.jpg"],
            winner_frame_id="IMG_1.jpg",
            subject_placement="x",
            edge_amputations="y",
            incidental_distractions="z",
        )


def test_comparison_winner_must_be_in_group() -> None:
    with pytest.raises(SchemaError):
        Comparison(
            group=["IMG_1.jpg", "IMG_2.jpg"],
            winner_frame_id="IMG_3.jpg",
            subject_placement="x",
            edge_amputations="y",
            incidental_distractions="z",
        )


def test_comparison_axes_require_non_empty_text() -> None:
    with pytest.raises(SchemaError):
        Comparison(
            group=["IMG_1.jpg", "IMG_2.jpg"],
            winner_frame_id="IMG_1.jpg",
            subject_placement="   ",
            edge_amputations="y",
            incidental_distractions="z",
        )


def test_comparison_valid_with_optional_tiebreaker() -> None:
    c = Comparison(
        group=["IMG_1.jpg", "IMG_2.jpg"],
        winner_frame_id="IMG_2.jpg",
        subject_placement="IMG_1 centers the tower; IMG_2 drifts left",
        edge_amputations="IMG_1 clips the flag; IMG_2 doesn't",
        incidental_distractions="a cyclist enters IMG_2",
        tiebreaker="the cyclist mid-pedal reads as a moment",
    )
    assert c.tiebreaker is not None
    assert c.to_dict()["winner_frame_id"] == "IMG_2.jpg"


def test_comparison_tiebreaker_defaults_to_none() -> None:
    c = Comparison(
        group=["IMG_1.jpg", "IMG_2.jpg"],
        winner_frame_id="IMG_1.jpg",
        subject_placement="x",
        edge_amputations="y",
        incidental_distractions="z",
    )
    assert c.tiebreaker is None
    assert c.to_dict()["tiebreaker"] is None


def test_analysis_output_comparison_group_must_reference_known_frames() -> None:
    with pytest.raises(SchemaError):
        AnalysisOutput(
            frames=[FrameAnalysis(frame_id="IMG_1.jpg")],
            comparisons=[
                Comparison(
                    group=["IMG_1.jpg", "IMG_2.jpg"],
                    winner_frame_id="IMG_1.jpg",
                    subject_placement="x",
                    edge_amputations="y",
                    incidental_distractions="z",
                )
            ],
        )


def test_analysis_output_roundtrip_json_with_comparisons() -> None:
    out = AnalysisOutput(
        frames=[
            FrameAnalysis(frame_id="IMG_1.jpg"),
            FrameAnalysis(frame_id="IMG_2.jpg"),
        ],
        comparisons=[
            Comparison(
                group=["IMG_1.jpg", "IMG_2.jpg"],
                winner_frame_id="IMG_2.jpg",
                subject_placement="x",
                edge_amputations="y",
                incidental_distractions="z",
                tiebreaker="a gaze line",
            )
        ],
    )
    round_tripped = AnalysisOutput.from_json(out.to_json())
    assert round_tripped == out


def test_analysis_output_default_comparisons_empty() -> None:
    assert AnalysisOutput().comparisons == []


def test_taxonomy_rule_text_matches_taxonomy_md_verbatim() -> None:
    # Hand-transcribed from TAXONOMY.md §R - same drift guard style as the
    # Reinforcement/Correction text tests above.
    assert taxonomy_rule_text("R01") == (
        "Shoot tighter. Tight frames suppress haze's flattening effect; the "
        "tightest frames consistently ranked highest."
    )


def test_taxonomy_rule_text_missing_for_f_and_s_items() -> None:
    # Only R-items have a Rule bullet - F-items have Correction, S-items have
    # Reinforcement.
    with pytest.raises(SchemaError):
        taxonomy_rule_text("F12")
    with pytest.raises(SchemaError):
        taxonomy_rule_text("S01")


def test_rule_rejects_non_r_item() -> None:
    with pytest.raises(SchemaError):
        Rule(taxonomy_id="F12", advice="shoot tighter")


def test_rule_requires_non_empty_advice() -> None:
    with pytest.raises(SchemaError):
        Rule(taxonomy_id="R01", advice="")


def test_rule_valid() -> None:
    rule = Rule(taxonomy_id="R01", advice="shoot tighter")
    assert rule.taxonomy_id == "R01"
    assert Rule.from_dict(rule.to_dict()) == rule


def test_analysis_output_default_rules_empty() -> None:
    assert AnalysisOutput().rules == []


def test_analysis_output_roundtrip_json_with_rules() -> None:
    out = AnalysisOutput(
        frames=[FrameAnalysis(frame_id="IMG_1.jpg")],
        rules=[Rule(taxonomy_id="R01", advice="shoot tighter")],
    )
    round_tripped = AnalysisOutput.from_json(out.to_json())
    assert round_tripped == out
