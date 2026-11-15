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
