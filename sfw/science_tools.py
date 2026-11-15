"""Transparent, local scientific calculation helpers for SFW.

The expression evaluator accepts arithmetic and a small whitelist of math
functions only. It never uses eval() and does not execute user-supplied code.
"""
from __future__ import annotations

import ast
import math
import operator


_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "log": math.log10, "ln": math.log, "exp": math.exp,
    "abs": abs, "round": round,
}
_CONSTANTS = {"pi": math.pi, "e": math.e}


class CalculationError(ValueError):
    """Raised when an expression or unit conversion is invalid."""


def _evaluate(node):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise CalculationError("Exponent magnitude is limited to 100.")
        return _BINARY[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_evaluate(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS:
        if node.keywords:
            raise CalculationError("Named function arguments are not supported.")
        return _FUNCTIONS[node.func.id](*[_evaluate(arg) for arg in node.args])
    raise CalculationError("Unsupported expression. Use arithmetic, pi, e, and supported math functions.")


def calculate_expression(expression: str) -> dict:
    """Evaluate a safe mathematical expression and return reproducible details."""
    expression = (expression or "").strip()
    if not expression:
        raise CalculationError("Enter a mathematical expression.")
    if len(expression) > 240:
        raise CalculationError("Expression is too long (maximum 240 characters).")
    try:
        tree = ast.parse(expression, mode="eval")
        result = float(_evaluate(tree))
    except CalculationError:
        raise
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        raise CalculationError(f"Could not calculate this expression: {exc}") from exc
    if not math.isfinite(result):
        raise CalculationError("The result is not a finite real number.")
    return {"expression": expression, "result": result, "formatted": f"{result:.10g}"}


# Each factor converts a value to the base unit for that dimension.
_UNIT_GROUPS = {
    "length": {"m": 1.0, "cm": 0.01, "mm": 0.001, "km": 1000.0},
    "mass": {"kg": 1.0, "g": 0.001, "mg": 0.000001},
    "volume": {"L": 1.0, "mL": 0.001},
    "time": {"s": 1.0, "min": 60.0, "h": 3600.0},
    "temperature": None,
}


def convert_units(value: float, from_unit: str, to_unit: str) -> dict:
    """Convert supported metric units; temperature conversions are explicit."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CalculationError("Enter a valid numeric value.") from exc
    if not math.isfinite(number):
        raise CalculationError("Value must be finite.")
    if from_unit in ("C", "F", "K") and to_unit in ("C", "F", "K"):
        to_c = {"C": lambda x: x, "F": lambda x: (x - 32) * 5 / 9, "K": lambda x: x - 273.15}
        from_c = {"C": lambda x: x, "F": lambda x: x * 9 / 5 + 32, "K": lambda x: x + 273.15}
        celsius = to_c[from_unit](number)
        if celsius < -273.15:
            raise CalculationError("Temperature cannot be below absolute zero (-273.15 °C).")
        result = from_c[to_unit](celsius)
        return {"value": number, "from_unit": from_unit, "to_unit": to_unit, "result": result}
    for dimension, units in _UNIT_GROUPS.items():
        if units and from_unit in units and to_unit in units:
            result = number * units[from_unit] / units[to_unit]
            return {"value": number, "from_unit": from_unit, "to_unit": to_unit, "result": result}
    raise CalculationError(f"Unsupported or incompatible units: {from_unit} to {to_unit}.")
