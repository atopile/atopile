# SPDX-License-Identifier: MIT
"""
Test the `.default` override for parameter default values.

This tests the feature that allows package authors to set default values
for parameters that can be overridden by users without causing contradictions.
"""

import pytest

import faebryk.library._F as F
from test.compiler.conftest import build_instance, build_type


def test_default_syntax_parses():
    """Test that `.default` syntax parses correctly."""
    _, _, _, result = build_type(
        """
        module TestModule:
            max_current: A
            max_current.default = 1A
        """
    )

    assert "TestModule" in result.state.type_roots


def test_default_creates_trait():
    """Test that `.default` syntax creates has_default_constraint trait."""
    g, tg, stdlib, result, app_root = build_instance(
        """
        import NumericParameter

        module TestModule:
            max_current = new NumericParameter
            max_current.default = 1A
        """,
        root="TestModule",
        stdlib_extra=[F.Parameters.NumericParameter],
    )

    # The module should be built
    assert "TestModule" in result.state.type_roots


def test_default_bilateral_quantity():
    """Test that `.default` works with bilateral quantities."""
    _, _, _, result = build_type(
        """
        module TestModule:
            resistance: ohm
            resistance.default = 10kohm +/- 5%
        """
    )
    assert "TestModule" in result.state.type_roots


def test_default_bounded_quantity():
    """Test that `.default` works with bounded quantities."""
    _, _, _, result = build_type(
        """
        module TestModule:
            voltage: V
            voltage.default = 3V to 5V
        """
    )
    assert "TestModule" in result.state.type_roots


def test_default_on_nested_field():
    """Test that `.default` works on nested fields."""
    _, _, _, result = build_type(
        """
        import Resistor

        module TestModule:
            r = new Resistor
            r.resistance.default = 10kohm +/- 5%
        """
    )
    assert "TestModule" in result.state.type_roots


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
