"""Tests for src/picstory/schema.py (QUEUE.md Stage 1, item 1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from picstory.schema import (
    CONDITIONAL_FIXABILITY_RESOLUTION,
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
    resolve_finding_fixability,
    taxonomy_correction_text,
    taxonomy_detection_text,
    taxonomy_fixability,
    taxonomy_fixability_category,
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


def test_taxonomy_ids_with_subpattern_parses_f06_profile_note_and_f05_conditional_fixability() -> None:
    # TAXONOMY.md v1.1: F06 is the only item with a "- **Profile note:**"
    # bullet ("Directional sub-patterns ... are per-user traits tracked by
    # the profile, not separate taxonomy items"). v1.2 (QUEUE.md item 18c,
    # DECISIONS.md D-009) added F05 via its `conditional` Fixability bullet -
    # a second, distinct source the same function now also parses. Neither
    # is hardcoded - same single-source-of-truth reasoning as
    # taxonomy_detection_text.
    assert taxonomy_ids_with_subpattern() == frozenset({"F05", "F06"})


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


# --- Fixability (QUEUE.md item 18, DECISIONS.md D-009, TAXONOMY.md v1.2) --


def test_taxonomy_fixability_matches_taxonomy_md_verbatim() -> None:
    # Hand-transcribed from TAXONOMY.md's 15 F-item Fixability bullets -
    # same drift guard style as the Detection/Correction/Reinforcement/Rule
    # text tests above.
    expected = {
        "F01": (
            "capture-only — sharpening cannot restore detail that was never "
            "captured; the Correction's \"crop in edit\" is the alternative to "
            "zooming next time, not a repair of this frame."
        ),
        "F02": (
            "post-fixable (crop) — when the obstruction sits at the edge, crop "
            "it out; deep intrusions may leave too little frame, in which case "
            "say so."
        ),
        "F03": (
            "capture-only — the failure is in the set, not the pixels; no edit "
            "turns copies into variations."
        ),
        "F04": (
            "capture-only — geometric distortion of faces and limbs is not "
            "honestly repairable in edit; it was decided by the lens and "
            "distance when the button was pressed."
        ),
        "F05": (
            "conditional — sub-pattern decides: `bowing` (curved lines with "
            "the subject centered) is post-fixable via lens/geometry "
            "correction; `off_center_drift` (the subject placed off the "
            "ultrawide's center) is capture-only — correction tools cannot "
            "recompose the frame."
        ),
        "F06": (
            "post-fixable (crop) — the Correction's own \"crop as salvage\"; "
            "the capture fix (sweep the edges) remains the coaching."
        ),
        "F07": (
            "post-fixable (crop) — the Correction's own \"crop to 4:5 or 16:9 "
            "from the empty side.\""
        ),
        "F08": (
            "post-fixable (straighten/perspective) — the Correction's own "
            "\"fix small cases with perspective tools in edit\"; severe "
            "convergence loses frame area to the correction, in which case "
            "say so."
        ),
        "F09": (
            "post-fixable (exposure/shadow lift) — a stop of shadow recovery "
            "is routinely available on phone captures, at some noise cost; "
            "deep silhouettes are capture-only, in which case say so."
        ),
        "F10": (
            "capture-only — the Detection text itself says it: clipped to "
            "pure white with no recoverable detail. Nothing to lift."
        ),
        "F11": (
            "capture-only — the background is behind the subject; no honest "
            "crop removes it without removing the person."
        ),
        "F12": (
            "post-fixable (contrast/blacks) — the Correction's own \"in "
            "edit: lift contrast, pull blacks down\"; heavy haze recovers "
            "only partially, in which case say so."
        ),
        "F13": "capture-only — no edit adds a person who was not there.",
        "F14": (
            "capture-only — the failure is in the location's coverage as a "
            "set; no edit of any single frame supplies the missing tight or "
            "eye-level frames."
        ),
        "F15": (
            "capture-only — a crop cannot move the person off the focal "
            "spot or restore an amputated landmark."
        ),
    }
    assert set(expected) == {tid for tid in taxonomy_ids() if tid.startswith("F")}
    for taxonomy_id, text in expected.items():
        assert taxonomy_fixability(taxonomy_id) == text


def test_taxonomy_fixability_missing_for_s_and_r_items() -> None:
    # v1.2's changelog: "S-items, R-items and CMP intentionally carry no
    # Fixability - strengths need no fix, rules and the rubric are not
    # per-frame findings."
    with pytest.raises(SchemaError):
        taxonomy_fixability("S01")
    with pytest.raises(SchemaError):
        taxonomy_fixability("R01")


def test_taxonomy_fixability_category_parses_leading_word() -> None:
    assert taxonomy_fixability_category("F01") == "capture-only"
    assert taxonomy_fixability_category("F02") == "post-fixable"
    assert taxonomy_fixability_category("F05") == "conditional"


def test_taxonomy_fixability_category_only_three_values_across_all_f_items() -> None:
    for taxonomy_id in sorted(taxonomy_ids()):
        if not taxonomy_id.startswith("F"):
            continue
        assert taxonomy_fixability_category(taxonomy_id) in {
            "post-fixable",
            "capture-only",
            "conditional",
        }


def test_conditional_fixability_resolution_is_complete() -> None:
    # Guards CONDITIONAL_FIXABILITY_RESOLUTION against silent drift: every
    # `conditional`-category ID must have an entry here, and vice versa - so
    # a future TAXONOMY.md amendment adding a second conditional item fails
    # this test loudly instead of resolve_finding_fixability silently
    # returning nothing for it.
    conditional_ids = {
        tid
        for tid in taxonomy_ids()
        if tid.startswith("F") and taxonomy_fixability_category(tid) == "conditional"
    }
    assert conditional_ids == set(CONDITIONAL_FIXABILITY_RESOLUTION)


def test_resolve_finding_fixability_post_fixable() -> None:
    assert resolve_finding_fixability(Finding(taxonomy_id="F06")) == "post-fixable"


def test_resolve_finding_fixability_capture_only() -> None:
    assert resolve_finding_fixability(Finding(taxonomy_id="F13")) == "capture-only"


def test_resolve_finding_fixability_conditional_resolves_by_sub_pattern() -> None:
    bowing = Finding(taxonomy_id="F05", sub_pattern="bowing")
    drift = Finding(taxonomy_id="F05", sub_pattern="off_center_drift")
    assert resolve_finding_fixability(bowing) == "post-fixable"
    assert resolve_finding_fixability(drift) == "capture-only"


def test_resolve_finding_fixability_conditional_without_sub_pattern_raises() -> None:
    with pytest.raises(SchemaError):
        resolve_finding_fixability(Finding(taxonomy_id="F05"))


def test_resolve_finding_fixability_none_for_s_items_and_unclassified() -> None:
    assert resolve_finding_fixability(Finding(taxonomy_id="S01")) is None
    assert resolve_finding_fixability(Finding(taxonomy_id="unclassified", description="x")) is None


# --- D-009(b): every previously-parsed bullet is byte-identical across ----
# --- the v1.1 -> v1.2 version bump (Fixability bullets are new; nothing ---
# --- else may have changed a single character). --------------------------


def test_v1_2_preserves_every_previously_parsed_text_byte_identical() -> None:
    # Hand-transcribed from TAXONOMY.md, covering every ID and every bullet
    # type that existed before v1.2 (Detection for all 20 F/S items,
    # Correction for all 15 F items, Reinforcement for all 4 S items, R01's
    # Rule, F06's Profile note) - not a sample. If the owner's v1.2 amendment
    # had altered so much as one character of pre-existing text, this test
    # (not just the handful of spot-checks elsewhere in this file) would
    # catch it, per DECISIONS.md D-009's explicit requirement.
    detection = {
        "F01": (
            "Fine detail (stonework, texture, edges) visibly soft in tight "
            "frames; focal length metadata or rendering consistent with "
            "digital zoom beyond the device's optical steps."
        ),
        "F02": (
            "Dark, out-of-focus mass along a frame edge, typically "
            "consistent across consecutive frames; a finger, case edge, or "
            "strap."
        ),
        "F03": (
            "2–5 consecutive frames of the same subject with no change in "
            "position, focal length, or angle. Copies, not variations."
        ),
        "F04": (
            "Faces stretched toward frame edges; near limbs exaggerated; "
            "typical of ultrawide (0.5x) selfies and close subjects "
            "off-center."
        ),
        "F05": (
            "Curved or skewed lines on ceilings and symmetric architecture "
            "when the subject drifts off the ultrawide's center."
        ),
        "F06": (
            "Unintended elements at frame edges — strangers' shoulders, "
            "half-cropped figures, flags, banners, labels cut mid-word, "
            "construction, brackets — while the primary subject is "
            "carefully centered. The tell: center chosen, edges unchosen."
        ),
        "F07": (
            "30–50% of the frame given to featureless area — blank sky, "
            "dead pavement, empty floor — with no compositional role."
        ),
        "F08": (
            "Vertical structures visibly leaning; parallel lines converging "
            "upward; worst on tight crops of tall subjects shot from below."
        ),
        "F09": (
            "Person in the foreground a stop or more dark, or "
            "unintentionally silhouetted, because metering favored a "
            "brighter background (lit landmark, sky, window)."
        ),
        "F10": (
            "Highlights clipped to pure white with no recoverable detail — "
            "light sources, lit glass, bright sky reading as featureless "
            "blobs."
        ),
        "F11": (
            "In-focus bystanders or photobombers behind the subject; strong "
            "background lines (bars, edges, vanishing points) running "
            "through heads; crowd clutter competing with the person."
        ),
        "F12": (
            "Low-contrast, washed-out distant subjects and flat skies from "
            "atmospheric haze; sharpening does not help."
        ),
        "F13": (
            "Large subject with nothing indicating its size; the set reads "
            "as \"one idea repeated,\" a record rather than an experience."
        ),
        "F14": (
            "A location's coverage is all establishing views — no tight "
            "detail study, no eye-level frames."
        ),
        "F15": (
            "Person placed on the composition's focal spot (dead center, "
            "vanishing point) so subject and landmark fight for the same "
            "position; or landmark half-amputated by the edge behind a "
            "portrait."
        ),
        "S01": "A person meaningfully placed in the foreground of a scene or landmark shot.",
        "S02": "Shot in the post-sunset / pre-dark window; deep blue sky with lit subjects.",
        "S03": "The tightest frame of a subject among its batch-mates.",
        "S04": "A single saturated or high-interest object against a quiet, uncluttered field.",
    }
    correction = {
        "F01": (
            "Stay at true optical focal lengths (1x / 2x / 5x). Need "
            "tighter? Move closer, or crop in edit."
        ),
        "F02": (
            "Wipe the lens and check all preview edges before shooting. "
            "(Grip problem, fixed *before* composing — distinct from F05.)"
        ),
        "F03": (
            "One frame, then deliberately change something — move ten "
            "feet, crouch, switch focal length. Come home with four "
            "pictures, not four copies."
        ),
        "F04": "Switch to 1x for people; hold the phone slightly above eye level.",
        "F05": "On the ultrawide, keep symmetric subjects centered.",
        "F06": (
            "Sweep all four edges before pressing the shutter. Commit "
            "fully: a whole label or none. Crop as salvage."
        ),
        "F07": (
            "Before shooting: tilt or rotate to fill the dead zone with "
            "something chosen. After: crop to 4:5 or 16:9 from the empty "
            "side."
        ),
        "F08": (
            "Step back and shoot straighter where possible; fix small "
            "cases with perspective tools in edit."
        ),
        "F09": "Tap on the face to set exposure for the person.",
        "F10": "Drag the exposure slider down before the shutter to hold highlight detail.",
        "F11": (
            "Portrait mode at 2x for people in complex interiors; half a "
            "step forward to clear background lines; have the subject walk "
            "ahead of the crowd."
        ),
        "F12": "In edit: lift contrast, pull blacks down. In the field: apply R01.",
        "F13": (
            "Include a figure — at the base, or silhouetted looking up. "
            "Presence and gaze direction matter more than exposure on the "
            "figure."
        ),
        "F14": (
            "At every location, deliberately add tight detail frames and "
            "at least one eye-level composition."
        ),
        "F15": "Person in a third; landmark fully over a shoulder, never cut by the edge.",
    }
    reinforcement = {
        "S01": "These consistently outrank empty landmark shots — keep leading with people.",
        "S02": "Repeatedly a strength — plan key locations for this window.",
        "S03": "The tightest frames won every batch in the source sessions.",
        "S04": "Produced the trip's best still-life frame (the red vessel in the white niche).",
    }
    rule = {
        "R01": (
            "Shoot tighter. Tight frames suppress haze's flattening "
            "effect; the tightest frames consistently ranked highest."
        ),
    }
    profile_note = {
        "F06": (
            "Directional sub-patterns (e.g. a right-third or left-edge "
            "blind spot) are per-user traits tracked by the profile, not "
            "separate taxonomy items."
        ),
    }

    assert set(detection) == taxonomy_ids() - {"R01"}
    assert set(correction) == {tid for tid in taxonomy_ids() if tid.startswith("F")}
    assert set(reinforcement) == {tid for tid in taxonomy_ids() if tid.startswith("S")}
    assert set(rule) == {"R01"}
    assert set(profile_note) == taxonomy_ids_with_subpattern() - {"F05"}

    for taxonomy_id, text in detection.items():
        assert taxonomy_detection_text(taxonomy_id) == text, taxonomy_id
    for taxonomy_id, text in correction.items():
        assert taxonomy_correction_text(taxonomy_id) == text, taxonomy_id
    for taxonomy_id, text in reinforcement.items():
        assert taxonomy_reinforcement_text(taxonomy_id) == text, taxonomy_id
    for taxonomy_id, text in rule.items():
        assert taxonomy_rule_text(taxonomy_id) == text, taxonomy_id
    for taxonomy_id, text in profile_note.items():
        from picstory.schema import _PROFILE_NOTE_LINE, _TAXONOMY_MD

        raw = _TAXONOMY_MD.read_text(encoding="utf-8")
        parsed = {m.group("id"): m.group("text").strip() for m in _PROFILE_NOTE_LINE.finditer(raw)}
        assert parsed[taxonomy_id] == text, taxonomy_id
