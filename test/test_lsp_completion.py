#!/usr/bin/env python3
"""
Tests for the LSP auto-completion functionality
"""

import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent
from unittest.mock import Mock, patch

import pytest

from faebryk.core.module import Module
from faebryk.core.parameter import Parameter

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import lsprotocol.types as lsp

import faebryk.library._F as F
from atopile.lsp.lsp_server import (
    _extract_field_reference_before_dot,
    _find_field_reference_node,
    _get_node_completions,
    on_document_completion,
)
from faebryk.core.node import Node


@contextmanager
def mock_file(
    content: str,
):
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(content.encode("utf-8"))
        yield Path(temp_file.name)


class TestFieldReferenceExtraction:
    """Test field reference extraction from cursor position"""

    @pytest.mark.parametrize(
        "line,position,expected",
        [
            # Basic cases
            ("resistor.", 9, "resistor"),
            ("mymodule.instance.", 18, "mymodule.instance"),
            # Array indexing
            ("app.modules[0].", 15, "app.modules[0]"),
            ("resistors[42].", 14, "resistors[42]"),
            ("complex.path[0].sub[1].", 23, "complex.path[0].sub[1]"),
            # Edge cases
            ("test", 4, None),  # No dot
            (".", 1, None),  # Dot at start
            ("  ", 2, None),  # No valid field ref
            ("", 0, None),  # Empty string
            ("a.", 2, "a"),  # Single character
            # Nested brackets
            ("matrix[0][1].", 13, "matrix[0][1]"),
            ("data[key1][key2].", 17, "data[key1][key2]"),
            # Mixed alphanumeric and underscores
            ("my_module.sub_item.", 19, "my_module.sub_item"),
            ("item123.value456.", 17, "item123.value456"),
        ],
    )
    def test_extract_field_reference_before_dot(self, line, position, expected):
        """Test extraction of field references before dots"""
        result = _extract_field_reference_before_dot(line, position)
        assert result == expected, f"Failed for '{line}' at pos {position}"

    def test_extract_field_reference_complex_cases(self):
        """Test more complex field reference extraction scenarios"""
        # Test with whitespace
        line = "  resistor.  "
        result = _extract_field_reference_before_dot(line, 11)
        assert result == "resistor"

        # Test right after dot vs typing after dot
        line = "resistor."
        result = _extract_field_reference_before_dot(line, 9)  # Right after dot
        assert result == "resistor"

        line = "resistor.r"
        result = _extract_field_reference_before_dot(line, 10)  # Typing after dot
        assert result == "resistor"

        # Test with brackets and special characters
        line = "app.modules[hello_world]."
        result = _extract_field_reference_before_dot(line, 25)
        assert result == "app.modules[hello_world]"


class TestNodeCompletions:
    """Test node completion extraction"""

    @pytest.mark.parametrize(
        "node_class, params",
        [
            (
                F.Resistor,
                {
                    "resistance": lsp.CompletionItemKind.Unit,
                    "unnamed[0]": lsp.CompletionItemKind.Interface,
                    "unnamed[1]": lsp.CompletionItemKind.Interface,
                    "max_power": lsp.CompletionItemKind.Unit,
                    "max_voltage": lsp.CompletionItemKind.Unit,
                },
            ),
            (
                F.Inductor,
                {
                    "inductance": lsp.CompletionItemKind.Unit,
                    "unnamed[0]": lsp.CompletionItemKind.Interface,
                    "unnamed[1]": lsp.CompletionItemKind.Interface,
                    "max_current": lsp.CompletionItemKind.Unit,
                    "dc_resistance": lsp.CompletionItemKind.Unit,
                    "saturation_current": lsp.CompletionItemKind.Unit,
                    "self_resonant_frequency": lsp.CompletionItemKind.Unit,
                },
            ),
        ],
    )
    def test_get_node_completions(self, node_class, params):
        """Test completion extraction from a Resistor node"""
        node = node_class()
        completions = _get_node_completions(node)

        # Should have at least some completions
        assert len(completions) > 0

        # All completions should be CompletionItem objects
        for item in completions:
            assert isinstance(item, lsp.CompletionItem)
            assert item.label  # Should have a label
            assert item.kind  # Should have a kind
            assert item.detail  # Should have detail text

        # Check for expected resistor attributes
        items = {item.label: item.kind for item in completions}
        assert items == params

    def test_get_node_completions_empty_node(self):
        """Test completion extraction from a minimal node"""

        class EmptyNode(Node):
            pass

        node = EmptyNode()
        completions = _get_node_completions(node)

        # Even empty nodes might have some basic completions
        assert isinstance(completions, list)

        # All items should be valid CompletionItems
        for item in completions:
            assert isinstance(item, lsp.CompletionItem)
            assert item.label

    def test_completion_item_kinds(self):
        """Test that completion items have appropriate kinds"""
        resistor = F.Resistor()
        completions = _get_node_completions(resistor)

        # Check that we have different kinds of completions
        kinds = {item.kind for item in completions}

        # Should have at least some recognizable kinds
        expected_kinds = {
            lsp.CompletionItemKind.Module,
            lsp.CompletionItemKind.Interface,
            lsp.CompletionItemKind.Property,
            lsp.CompletionItemKind.Class,
        }

        # At least some expected kinds should be present
        assert len(kinds.intersection(expected_kinds)) > 0


class TestFieldReferenceResolution:
    """Test field reference to node resolution"""

    def test_find_field_reference_node_simple_missing(self):
        """Test finding a node from a simple field reference"""
        # This is harder to test without a full graph setup
        # For now, test that the function handles invalid cases gracefully

        result = _find_field_reference_node("fake_uri", "pass", "nonexistent.field", 0)
        assert result is None, "Should return None for non-existent field references"

    def test_find_field_reference_node_invalid_input(self):
        """Test field reference resolution with invalid inputs"""
        # Test empty field reference
        result = _find_field_reference_node("fake_uri", "pass", "", 0)
        assert result is None

        # Test with invalid characters
        result = _find_field_reference_node("fake_uri", "pass", "invalid..field", 0)
        assert result is None

    def test_find_field_reference_node_nested_present(self):
        """Test finding a node from a nested field reference"""
        ato = dedent("""
            import Resistor             #1
            module TestModule:          #2
                resistor = new Resistor #3
                                        #4
            """)
        with mock_file(ato) as uri:
            result = _find_field_reference_node(str(uri), ato, "resistor.resistance", 4)
        assert result is not None
        assert isinstance(result, Parameter)

    def test_find_field_reference_node_duplicate(self):
        """Test finding a node from a duplicate field reference"""
        ato = dedent("""
                                        #1
            import Resistor             #2
            module TestModule1:         #3
                resistor = new Resistor #4
                                        #5
            module TestModule2:         #6
                resistor = 100mA        #7
                                        #8
            """)
        with mock_file(ato) as uri:
            result = _find_field_reference_node(str(uri), ato, "resistor", 5)
            assert isinstance(result, Module)
            result2 = _find_field_reference_node(str(uri), ato, "resistor", 8)
            assert isinstance(result2, Parameter)


@contextmanager
def _to_mock(code: str, marker="#|#"):
    dedented = dedent(code)

    marker_row = None
    marker_column = None

    # find marker row & column
    for row, line in enumerate(dedented.split("\n")):
        if marker in line:
            marker_row = row
            marker_column = line.index(marker)
            break
    dedented = dedented.replace(marker, "", count=1)

    if marker_row is None or marker_column is None:
        raise ValueError(f"Marker {marker} not found in code")

    mock_document = Mock()
    mock_document.source = dedented
    mock_document.path = "test.ato"

    mock_params = Mock()
    mock_params.text_document.uri = f"test://{mock_document.path}"
    mock_params.position.line = marker_row
    mock_params.position.character = marker_column

    with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
        mock_server.workspace.get_text_document.return_value = mock_document
        yield mock_params, mock_document


class TestEndToEndCompletion:
    """End-to-end tests with real ato code scenarios"""

    def test_resistor_completion_end_to_end(self):
        """Test completion for 'resistor = new Resistor' followed by 'resistor.'"""
        # Simulate ato code with a resistor instantiation
        ato = """
            import Resistor
            module TestModule:
                resistor = new Resistor
                resistor.#|#
            """

        with _to_mock(ato) as (mock_params, _):
            result = on_document_completion(mock_params)

            # Should return a CompletionList with resistor attributes
            assert isinstance(result, lsp.CompletionList)
            assert len(result.items) > 0

            # Check for expected resistor completions
            labels = [item.label for item in result.items]
            expected_completions = [
                "resistance",
                "max_power",
                "max_voltage",
                "unnamed[0]",
                "unnamed[1]",
            ]

            for expected in expected_completions:
                assert expected in labels, (
                    f"Expected '{expected}' in completions: {labels}"
                )

    def test_capacitor_completion_end_to_end(self):
        """Test completion for 'capacitor = new Capacitor' followed by 'capacitor.'"""
        ato = """
            import Capacitor
            module TestModule:
                capacitor = new Capacitor
                capacitor.#|#
            """

        with _to_mock(ato) as (mock_params, _):
            result = on_document_completion(mock_params)

            # Should return a CompletionList with Capacitor attributes
            assert isinstance(result, lsp.CompletionList)
            assert len(result.items) > 0

            # Check for expected Capacitor completions
            labels = {item.label for item in result.items}

            assert labels == {
                "capacitance",
                "max_voltage",
                "unnamed[0]",
                "unnamed[1]",
                "temperature_coefficient",
            }

    def test_nested_field_completion_end_to_end(self):
        """Test completion for nested field access like 'module.submodule.field.'"""
        ato = """
            import PoweredLED
            module TestModule:
                poweredLED = new PoweredLED
                poweredLED.led.#|#
            """

        with _to_mock(ato) as (mock_params, _):
            result = on_document_completion(mock_params)

            # Should return a CompletionList with LED-specific attributes
            assert isinstance(result, lsp.CompletionList)
            labels = {item.label for item in result.items}
            assert labels == {
                "brightness",
                "color",
                "max_brightness",
                "forward_voltage",
                "current",
                "reverse_working_voltage",
                "reverse_leakage_current",
                "max_current",
                "anode",
                "cathode",
            }

    def test_array_access_completion_end_to_end(self):
        """Test completion for array access like 'resistors[0].'"""
        ato = """
            import Resistor
            module TestModule:
                resistors = new Resistor[5]
                resistors[0].#|#
            """

        with _to_mock(ato) as (mock_params, _):
            result = on_document_completion(mock_params)

            # Should return a CompletionList with resistor attributes
            assert isinstance(result, lsp.CompletionList)
            assert len(result.items) > 0

            # Check for resistor-specific completions
            labels = {item.label for item in result.items}
            expected_completions = {
                "resistance",
                "max_power",
                "max_voltage",
                "unnamed[0]",
                "unnamed[1]",
            }

            assert labels == expected_completions

    def test_no_completion_for_invalid_field_reference(self):
        """Test that no completions are provided for invalid field references"""
        ato = """
            import Resistor
            module TestModule:
                resistor = new Resistor
                nonexistent.#|#
            """

        with _to_mock(ato) as (mock_params, _):
            result = on_document_completion(mock_params)

            # Should return None for non-existent field references
            assert result is None

    def test_rhs_completion_end_to_end(self):
        """Test completion for 'resistor = new Resistor' followed by 'resistor.'"""
        # Simulate ato code with a resistor instantiation
        ato = """
            import ElectricPower
            import Resistor
            module TestModule:
                resistor = new Resistor
                power = new ElectricPower
                resistor.unnamed[0] ~ power.#|#
            """

        with _to_mock(ato) as (mock_params, _):
            result = on_document_completion(mock_params)

            # Should return a CompletionList with resistor attributes
            assert isinstance(result, lsp.CompletionList)
            assert len(result.items) > 0

            # Check for expected resistor completions
            labels = [item.label for item in result.items]
            expected_completions = [
                "hv",
                "lv",
                "voltage",
                "max_current",
                "bus_max_current_consumption_sum",
            ]

            for expected in expected_completions:
                assert expected in labels, (
                    f"Expected '{expected}' in completions: {labels}"
                )

    def test_new_keyword_completion_end_to_end(self):
        """Test completion after 'new' keyword with partial type name"""
        # Mock ato content with imports and local definitions
        ato_content = """
            import Resistor
            import Capacitor
            import LED

            module TestModule:
                x = new #|#
                pass

            interface TestInterface:
                pass
        """

        with _to_mock(ato_content) as (mock_params, _):
            types = on_document_completion(mock_params)

            assert isinstance(types, lsp.CompletionList)
            assert len(types.items) > 0

            labels = {item.label for item in types.items}

            # Should find local definitions at minimum
            expected_local_types = {
                "TestModule",
                "TestInterface",
                "Resistor",
                "Capacitor",
                "LED",
            }

            assert expected_local_types.intersection(labels) == expected_local_types

    def test_import_completion_end_to_end(self):
        """Test completion for 'import' keyword"""
        ato = """
            import #|#
            """
        with _to_mock(ato) as (mock_params, _):
            result = on_document_completion(mock_params)

            assert isinstance(result, lsp.CompletionList)
            assert len(result.items) > 0

            labels = {item.label for item in result.items}
            must_contain = {"Resistor", "Capacitor", "LED", "ElectricPower"}
            assert labels.intersection(must_contain) == must_contain

            # TODO check no raw traits (only impl) in list

    def test_multi_import_comma_separated_completion(self):
        """Test completion for comma-separated multi imports.

        Tests 'import Module1, Module2' syntax.
        """
        ato = """
            import Resistor, Capacitor, #|#
            """
        with _to_mock(ato) as (mock_params, _):
            result = on_document_completion(mock_params)

            assert isinstance(result, lsp.CompletionList)
            assert len(result.items) > 0

            labels = {item.label for item in result.items}
            must_contain = {"LED", "ElectricPower", "ElectricLogic"}
            assert labels.intersection(must_contain) == must_contain

    def test_multi_import_semicolon_separated_completion(self):
        """Test completion for semicolon-separated multi imports"""
        ato = """
            import Resistor; import Capacitor; import #|#
            """
        with _to_mock(ato) as (mock_params, _):
            result = on_document_completion(mock_params)

            assert isinstance(result, lsp.CompletionList)
            assert len(result.items) > 0

            labels = {item.label for item in result.items}
            must_contain = {"LED", "ElectricPower", "ElectricLogic"}
            assert labels.intersection(must_contain) == must_contain

    def test_completion_in_middle_of_multi_import_statement(self):
        """Test completion when cursor is in the middle of a multi import statement"""
        ato = """
            import Resistor, #|#, LED
            """
        with _to_mock(ato) as (mock_params, _):
            result = on_document_completion(mock_params)

            assert isinstance(result, lsp.CompletionList)
            assert len(result.items) > 0

            labels = {item.label for item in result.items}
            expected_modules = {"Capacitor", "ElectricPower", "ElectricLogic"}
            assert len(labels.intersection(expected_modules)) > 0

    def test_completion_with_nested_multi_import(self):
        """Test completion with nested module references in multi imports"""
        ato = """
            import Module1.SubModule, Module2.SubModule, #|#
            """
        with _to_mock(ato) as (mock_params, _):
            result = on_document_completion(mock_params)

            assert isinstance(result, lsp.CompletionList)
            assert len(result.items) > 0

            labels = {item.label for item in result.items}
            # Should suggest available modules including nested ones
            expected_modules = {"Resistor", "Capacitor", "LED"}
            assert len(labels.intersection(expected_modules)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
