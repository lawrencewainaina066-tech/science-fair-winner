import math
import pytest

from sfw.science_tools import (
    CalculationError,
    calculate_expression,
    convert_units,
)


def test_calculate_arithmetic_and_functions():
    result = calculate_expression("sqrt(81) + 2*pi")
    assert result["result"] == pytest.approx(9 + 2 * math.pi)


def test_calculator_rejects_code_execution():
    with pytest.raises(CalculationError):
        calculate_expression("__import__('os').system('echo unsafe')")


def test_calculator_rejects_division_by_zero():
    with pytest.raises(CalculationError):
        calculate_expression("1 / 0")


def test_metric_conversion():
    result = convert_units(250, "cm", "m")
    assert result["result"] == pytest.approx(2.5)


def test_temperature_conversion():
    result = convert_units(0, "C", "F")
    assert result["result"] == pytest.approx(32)


def test_incompatible_units_are_rejected():
    with pytest.raises(CalculationError):
        convert_units(1, "kg", "m")
