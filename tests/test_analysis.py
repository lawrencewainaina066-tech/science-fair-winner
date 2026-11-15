import numpy as np
import pandas as pd
import pytest

from sfw.analysis import (
    independent_t_test, paired_t_test, chi_square_test,
    linear_regression, interpret_p_value,
)


def test_welch_t_test_reports_mean_difference_ci_and_effect_size():
    result = independent_t_test([1, 2, 3, 4], [3, 4, 5, 6])
    assert result["mean_difference_a_minus_b"] == pytest.approx(-2)
    assert result["mean_difference_ci"][0] < -2 < result["mean_difference_ci"][1]
    assert result["cohens_d"] < 0
    assert result["test"] == "Welch independent-samples t-test"


def test_independent_t_test_rejects_invalid_alpha_and_infinite_values():
    with pytest.raises(ValueError):
        independent_t_test([1, 2], [3, 4], alpha=1)
    with pytest.raises(ValueError):
        independent_t_test([1, np.inf], [3, 4])


def test_paired_t_test_uses_after_minus_before_and_reports_ci():
    result = paired_t_test([1, 2, 3, 4], [2, 4, 4, 6])
    assert result["mean_difference_after_minus_before"] == pytest.approx(1.5)
    assert result["mean_difference_ci"][0] < 1.5 < result["mean_difference_ci"][1]
    assert result["cohens_dz"] > 0


def test_chi_square_flags_small_expected_counts():
    result = chi_square_test([[2, 8], [7, 3]])
    assert result["minimum_expected_frequency"] < 5
    assert isinstance(result["expected"], list)
    assert result["small_expected_frequency_warning"] is True


def test_chi_square_rejects_zero_margin_and_infinity():
    with pytest.raises(ValueError):
        chi_square_test([[1, 2], [0, 0]])
    with pytest.raises(ValueError):
        chi_square_test([[1, np.inf], [2, 3]])


def test_regression_rejects_constant_predictor():
    with pytest.raises(ValueError):
        linear_regression(pd.DataFrame({"x": [1, 1, 1], "y": [2, 3, 4]}), "x", "y")


def test_p_value_interpretation_validates_range():
    with pytest.raises(ValueError):
        interpret_p_value(1.2)
    with pytest.raises(ValueError):
        interpret_p_value(0.03, alpha=0)
    assert "does not prove" in interpret_p_value(0.5)
