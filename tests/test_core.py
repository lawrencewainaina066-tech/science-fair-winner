import pandas as pd
from sfw.planner import build_research_plan
from sfw.analysis import independent_t_test, paired_t_test, linear_regression, interpret_p_value

def test_plan_contains_integrity_note():
    plan = build_research_plan("Test", "Effect of light on growth", "Biology")
    assert "hypothesis" in plan
    assert "not evidence" in plan["integrity_note"]

def test_independent_t_test():
    result = independent_t_test([1,2,3,4], [5,6,7,8])
    assert 0 <= result["p_value"] <= 1
    assert result["n_a"] == 4

def test_paired_t_test():
    result = paired_t_test([1,2,3], [2,4,4])
    assert result["n_pairs"] == 3

def test_linear_regression():
    df = pd.DataFrame({"x":[1,2,3,4], "y":[2,4,6,8]})
    result = linear_regression(df, "x", "y")
    assert abs(result["slope"] - 2) < 1e-8
    assert abs(result["r_squared"] - 1) < 1e-8

def test_p_interpretation_does_not_claim_proof():
    assert "does not prove" in interpret_p_value(0.5)
