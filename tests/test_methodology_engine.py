import pytest

from sfw.methodology import (
    DESIGN_OPTIONS,
    OBJECTIVES,
    OUTCOME_TYPES,
    SAMPLING_METHODS,
    build_methodology,
    validate_design,
)


def _valid_methodology(**overrides):
    values = {
        "title": "Compost tea and maize seedling growth",
        "research_question": "What effect do compost tea concentrations have on maize height?",
        "design": "Controlled experiment",
        "objective": "Compare two or more groups or treatments",
        "independent_variable": "Compost tea concentration",
        "dependent_variable": "Plant height (cm)",
        "outcome_type": "Continuous numerical",
        "population": "Maize seedlings of one variety",
        "sampling_method": "Simple random sampling",
        "planned_sample_size": 12,
        "groups": 3,
        "data_collection": "Measure each plant every 7 days",
        "duration": "4 weeks",
    }
    values.update(overrides)
    return build_methodology(**values)


def test_methodology_returns_analysis_steps_and_integrity_note():
    plan = _valid_methodology()
    assert plan["analysis_plan"]
    assert plan["method_steps"]
    assert "does not calculate or validate sample size" in plan["integrity_note"]
    assert plan["planned_sample_size"] == 12


def test_repeated_measurements_are_not_treated_as_independent():
    plan = _valid_methodology()
    assert plan["validation"]["suggested_analysis"]
    assert any("Repeated measurements" in item["title"] for item in plan["validation"]["findings"])


def test_small_sample_and_random_sampling_are_flagged():
    plan = _valid_methodology(planned_sample_size=6, groups=3)
    titles = [item["title"] for item in plan["validation"]["findings"]]
    assert "Small number of replicates per group" in titles
    assert "Separate sampling from treatment allocation" in titles


def test_invalid_sample_size_and_group_count_are_rejected():
    with pytest.raises(ValueError, match="at least 1"):
        _valid_methodology(planned_sample_size=0)
    with pytest.raises(ValueError, match="at least 1"):
        _valid_methodology(groups=0)


def test_empty_required_inputs_are_rejected():
    with pytest.raises(ValueError, match="research question"):
        _valid_methodology(research_question="")
    with pytest.raises(ValueError, match="target population"):
        _valid_methodology(population="")
    with pytest.raises(ValueError, match="main outcome"):
        _valid_methodology(dependent_variable="")
    with pytest.raises(ValueError, match="data will be collected"):
        _valid_methodology(data_collection="")


def test_design_validation_detects_missing_replication():
    result = validate_design(
        design="Controlled experiment",
        objective="Compare two or more groups or treatments",
        outcome_type="Continuous numerical",
        independent_variable="Treatment",
        dependent_variable="Height",
        sample_size=2,
        groups=3,
        data_collection="Measure weekly",
    )
    assert any(item["level"] == "error" for item in result["findings"])


def test_public_option_lists_are_nonempty():
    assert DESIGN_OPTIONS and OBJECTIVES and OUTCOME_TYPES and SAMPLING_METHODS
