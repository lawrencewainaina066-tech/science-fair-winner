from sfw.methodology import build_methodology

def _build(**overrides):
    values = {
        "title": "Maize growth study",
        "research_question": "Does compost tea concentration affect maize seedling height?",
        "design": "Controlled experiment",
        "objective": "Compare two or more groups or treatments",
        "independent_variable": "Compost tea concentration",
        "dependent_variable": "Seedling height",
        "outcome_type": "Continuous numerical",
        "population": "Maize seedlings grown in pots",
        "sampling_method": "Simple random sampling",
        "planned_sample_size": 24,
        "groups": 3,
        "data_collection": "Measure height in centimetres every seven days",
        "duration": "Four weeks",
        "constraints": "",
    }
    values.update(overrides)
    return build_methodology(**values)

def test_continuous_three_group_comparison_recommends_anova():
    result = _build()
    assert any("ANOVA" in item for item in result["analysis_plan"])

def test_observational_association_warns_against_causal_claims():
    result = _build(
        design="Observational study",
        objective="Measure a relationship between variables",
    )
    assert any("do not by themselves establish" in item for item in result["warnings"])

def test_missing_sample_size_is_flagged():
    result = _build(planned_sample_size=None)
    assert any("No sample size was entered" in item for item in result["warnings"])

def test_invalid_sample_size_raises():
    try:
        _build(planned_sample_size=-2)
    except ValueError as exc:
        assert "at least 1" in str(exc)
    else:
        raise AssertionError("Expected invalid sample size to raise ValueError")

def test_missing_research_question_raises():
    try:
        _build(research_question="")
    except ValueError as exc:
        assert "research question" in str(exc)
    else:
        raise AssertionError("Expected missing research question to raise ValueError")


def test_qualitative_objective_with_numeric_height_is_flagged():
    result = _build(
        design="Mixed-methods study",
        objective="Explore experiences, views or processes",
        outcome_type="Continuous numerical",
    )
    validation = result["validation"]
    assert validation["suggested_objective"] == "Compare two or more groups or treatments"
    assert any(item["title"] == "Objective does not match the measured outcome"
               for item in validation["findings"])

def test_sample_smaller_than_group_count_is_an_error():
    result = _build(planned_sample_size=2, groups=3)
    assert result["validation"]["is_valid"] is False
    assert any(item["title"] == "Fewer experimental units than groups"
               for item in result["validation"]["findings"])

def test_repeated_height_measurements_trigger_repeated_analysis_warning():
    result = _build(
        data_collection="Measure plant height every 7 days",
        duration="4 weeks",
    )
    assert result["validation"]["suggested_analysis"]
    assert any(item["title"] == "Repeated measurements need a repeated-measures analysis"
               for item in result["validation"]["findings"])

def test_mixed_methods_requires_two_integrated_strands():
    result = _build(design="Mixed-methods study")
    assert any(item["title"] == "Mixed-methods requires two integrated strands"
               for item in result["validation"]["findings"])


def test_maize_style_mixed_methods_numeric_repeated_design_gets_full_corrections():
    result = _build(
        design="Mixed-methods study",
        objective="Explore experiences, views or processes",
        outcome_type="Continuous numerical",
        planned_sample_size=2,
        groups=3,
        data_collection="Measure maize height every 7 days",
        duration="4 weeks",
    )
    validation = result["validation"]
    assert validation["suggested_design"] == "Controlled experiment"
    assert validation["suggested_objective"] == "Compare two or more groups or treatments"
    assert validation["suggested_analysis"]
    assert any(item["level"] == "error" for item in validation["findings"])
    assert not any("thematic" in item.lower() for item in result["analysis_plan"])
