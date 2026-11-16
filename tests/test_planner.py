from sfw.planner import build_research_plan


def test_compost_tea_maize_plan_is_topic_specific():
    plan = build_research_plan(
        "Effects of Different Compost Tea Concentrations on the Early Vegetative Growth of Maize",
        "Investigate compost tea concentration effects on maize seedlings.",
        "Agriculture",
        "College / university",
        "12 seedlings; rain-fed conditions",
        location="Rironi, Kipipiri, Nyandarua County",
        duration="4 weeks",
        intervention="compost tea concentration",
        primary_outcome="maize seedling height (cm)",
    )
    assert "maize" in plan["research_question"].lower()
    assert "compost tea" in plan["research_question"].lower()
    assert "water-only control" in " ".join(plan["treatment_structure"]).lower()
    assert plan["specific_objectives"]
    assert plan["variables"]["dependent"] == "maize seedling height (cm)"


def test_short_seedling_study_warns_against_grain_yield_claim():
    plan = build_research_plan(
        "Compost tea effects on maize seedling growth and grain yield",
        "Compare compost tea treatments.",
        "Agriculture",
        duration="4 weeks",
        primary_outcome="seedling height and grain yield",
    )
    assert any("too short to measure grain yield" in warning for warning in plan["warnings"])
    assert any("mix seedling growth and grain yield" in warning for warning in plan["warnings"])


def test_generic_plan_does_not_claim_results_or_references():
    plan = build_research_plan("", "", "Biology")
    assert "not evidence" in plan["integrity_note"].lower() or "no experiment" in plan["integrity_note"].lower()
    assert plan["method_outline"]
    assert plan["variables"]["independent"]
    assert plan["variables"]["dependent"]


def test_duration_parser_handles_weeks_and_months():
    from sfw.planner import _duration_weeks
    assert _duration_weeks("4 weeks") == 4
    assert _duration_weeks("2 months") == 8
