#!/usr/bin/env python3
"""
Tests for the LSP auto-completion functionality
"""

import sys
from pathlib import Path
from textwrap import dedent
from unittest.mock import Mock, patch

import pytest

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
                    "resistance": lsp.CompletionItemKind.Variable,
                    "unnamed[0]": lsp.CompletionItemKind.Interface,
                    "unnamed[1]": lsp.CompletionItemKind.Interface,
                    "max_power": lsp.CompletionItemKind.Variable,
                    "max_voltage": lsp.CompletionItemKind.Variable,
                },
            ),
            (
                F.LEDIndicator,
                {
                    "logic_in": lsp.CompletionItemKind.Interface,
                    "power_in": lsp.CompletionItemKind.Interface,
                    "led": lsp.CompletionItemKind.Field,
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

    def test_find_field_reference_node_simple(self):
        """Test finding a node from a simple field reference"""
        # This is harder to test without a full graph setup
        # For now, test that the function handles invalid cases gracefully

        result = _find_field_reference_node("fake_uri", "nonexistent.field", 0)
        assert result is None, "Should return None for non-existent field references"

    def test_find_field_reference_node_invalid_input(self):
        """Test field reference resolution with invalid inputs"""
        # Test empty field reference
        result = _find_field_reference_node("fake_uri", "", 0)
        assert result is None

        # Test with invalid characters
        result = _find_field_reference_node("fake_uri", "invalid..field", 0)
        assert result is None


class TestLSPCompletionHandler:
    """Test the main LSP completion handler"""

    def test_on_document_completion_no_field_ref(self):
        """Test completion handler when no field reference is detected"""
        # Mock the LSP server and document
        mock_params = Mock()
        mock_params.text_document.uri = "test_uri"
        mock_params.position.character = 5

        mock_document = Mock()
        mock_document.source = "test content"

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            with patch("atopile.lsp.lsp_server.utils") as mock_utils:
                mock_server.workspace.get_text_document.return_value = mock_document
                mock_utils.cursor_line.return_value = "no field ref here"

                result = on_document_completion(mock_params)

                # Should return None when no field reference is found
                assert result is None

    def test_on_document_completion_with_field_ref(self):
        """Test completion handler with a field reference"""
        mock_params = Mock()
        mock_params.text_document.uri = "test_uri"
        mock_params.position.character = 10

        mock_document = Mock()
        mock_document.source = "test content"

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            with patch("atopile.lsp.lsp_server.utils") as mock_utils:
                with patch(
                    "atopile.lsp.lsp_server._find_field_reference_node"
                ) as mock_find:
                    with patch(
                        "atopile.lsp.lsp_server._get_node_completions"
                    ) as mock_completions:
                        mock_server.workspace.get_text_document.return_value = (
                            mock_document
                        )
                        mock_utils.cursor_line.return_value = "resistor."

                        # Mock the _extract_field_reference_before_dot to return a
                        # field reference
                        with patch(
                            "atopile.lsp.lsp_server._extract_field_reference_before_dot"
                        ) as mock_extract:
                            mock_extract.return_value = "resistor"

                            # Mock finding a node
                            mock_node = Mock(spec=Node)
                            mock_find.return_value = mock_node

                            # Mock completions
                            mock_completion_items = [
                                lsp.CompletionItem(
                                    label="test_item",
                                    kind=lsp.CompletionItemKind.Property,
                                )
                            ]
                            mock_completions.return_value = mock_completion_items

                            result = on_document_completion(mock_params)

                            # Should return a CompletionList
                            assert isinstance(result, lsp.CompletionList)
                            assert result.is_incomplete is False
                            assert len(result.items) == 1
                            assert result.items[0].label == "test_item"

    def test_on_document_completion_exception_handling(self):
        """Test that completion handler gracefully handles exceptions"""
        mock_params = Mock()

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            # Make the server raise an exception
            mock_server.workspace.get_text_document.side_effect = Exception(
                "Test error"
            )

            result = on_document_completion(mock_params)

            # Should return None on exception
            assert result is None


class TestIntegration:
    """Integration tests for the full completion pipeline"""

    def test_full_completion_pipeline(self):
        """Test the complete completion pipeline with real objects"""
        # Create a real resistor for testing
        resistor = F.Resistor()

        # Test the completion extraction
        completions = _get_node_completions(resistor)

        # Verify we get valid completions
        assert len(completions) > 0

        # Test that all completions are properly formatted
        for item in completions:
            assert isinstance(item, lsp.CompletionItem)
            assert item.label
            assert item.kind is not None
            assert item.detail
            assert item.documentation
            assert isinstance(item.documentation, lsp.MarkupContent)
            assert item.documentation.kind == lsp.MarkupKind.Markdown


class TestEndToEndCompletion:
    """End-to-end tests with real ato code scenarios"""

    def test_resistor_completion_end_to_end(self):
        """Test completion for 'resistor = new Resistor' followed by 'resistor.'"""
        # Simulate ato code with a resistor instantiation
        ato_code = dedent("""
            module TestModule:
                resistor = new Resistor
                # cursor position after resistor.
            """)

        # Mock the LSP environment
        mock_params = Mock()
        mock_params.text_document.uri = "test://test.ato"
        mock_params.position.line = 3  # Line with "resistor."
        mock_params.position.character = 14  # After the dot

        mock_document = Mock()
        mock_document.source = ato_code
        mock_document.path = "test.ato"

        # Create a real resistor for the graph
        test_resistor = F.Resistor()
        mock_graphs = {
            "test://test.ato": {
                "TestModule": Mock(),  # Mock module containing the resistor
            }
        }

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            with patch("atopile.lsp.lsp_server.utils") as mock_utils:
                with patch("atopile.lsp.lsp_server.GRAPHS", mock_graphs):
                    with patch(
                        "atopile.lsp.lsp_server._find_field_reference_node"
                    ) as mock_find:
                        with patch(
                            "atopile.lsp.lsp_server._extract_field_reference_before_dot"
                        ) as mock_extract:
                            mock_server.workspace.get_text_document.return_value = (
                                mock_document
                            )
                            mock_utils.cursor_line.return_value = "    resistor."

                            # Mock the field reference extraction
                            mock_extract.return_value = "resistor"

                            # Mock finding the resistor node
                            mock_find.return_value = test_resistor

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

    def test_led_indicator_completion_end_to_end(self):
        """Test completion for 'led = new LEDIndicator' followed by 'led.'"""
        ato_code = dedent("""
            module TestModule:
                led = new LEDIndicator
                # cursor position after led.
            """)

        mock_params = Mock()
        mock_params.text_document.uri = "test://test.ato"
        mock_params.position.line = 3
        mock_params.position.character = 8  # After "led."

        mock_document = Mock()
        mock_document.source = ato_code

        # Create a real LED indicator for the graph
        test_led = F.LEDIndicator()

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            with patch("atopile.lsp.lsp_server.utils") as mock_utils:
                with patch(
                    "atopile.lsp.lsp_server._find_field_reference_node"
                ) as mock_find:
                    with patch(
                        "atopile.lsp.lsp_server._extract_field_reference_before_dot"
                    ) as mock_extract:
                        mock_server.workspace.get_text_document.return_value = (
                            mock_document
                        )
                        mock_utils.cursor_line.return_value = "    led."

                        # Mock the field reference extraction
                        mock_extract.return_value = "led"

                        # Mock finding the LED node
                        mock_find.return_value = test_led

                        result = on_document_completion(mock_params)

                        # Should return a CompletionList with LED attributes
                        assert isinstance(result, lsp.CompletionList)
                        assert len(result.items) > 0

                        # Check for expected LED completions
                        labels = [item.label for item in result.items]
                        expected_completions = ["logic_in", "power_in", "led"]

                        for expected in expected_completions:
                            assert expected in labels, (
                                f"Expected '{expected}' in completions: {labels}"
                            )

    def test_nested_field_completion_end_to_end(self):
        """Test completion for nested field access like 'module.submodule.field.'"""
        ato_code = dedent("""
            module TestModule:
                led_indicator = new LEDIndicator
                # cursor position after led_indicator.led.
            """)

        mock_params = Mock()
        mock_params.text_document.uri = "test://test.ato"
        mock_params.position.line = 3
        mock_params.position.character = 21  # After "led_indicator.led."

        mock_document = Mock()
        mock_document.source = ato_code

        # Create the nested structure: LEDIndicator -> LED
        test_led_indicator = F.LEDIndicator()
        test_led = test_led_indicator.led  # Get the LED from the indicator

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            with patch("atopile.lsp.lsp_server.utils") as mock_utils:
                with patch(
                    "atopile.lsp.lsp_server._find_field_reference_node"
                ) as mock_find:
                    with patch(
                        "atopile.lsp.lsp_server._extract_field_reference_before_dot"
                    ) as mock_extract:
                        mock_server.workspace.get_text_document.return_value = (
                            mock_document
                        )
                        mock_utils.cursor_line.return_value = "    led_indicator.led."

                        # Mock the field reference extraction
                        mock_extract.return_value = "led_indicator.led"

                        # Mock finding the nested LED node
                        mock_find.return_value = test_led

                        result = on_document_completion(mock_params)

                        # Should return a CompletionList with LED-specific attributes
                        assert isinstance(result, lsp.CompletionList)

                        if len(result.items) > 0:
                            # Verify we get actual LED completions, not LEDIndicator
                            #  completions
                            labels = [item.label for item in result.items]
                            # The LED should have different attributes than the
                            #  LEDIndicator
                            assert (
                                "logic_in" not in labels
                            )  # This belongs to LEDIndicator, not LED

    def test_array_access_completion_end_to_end(self):
        """Test completion for array access like 'resistors[0].'"""
        ato_code = dedent("""
            module TestModule:
                resistors = new Resistor[5]
                # cursor position after resistors[0].
            """)

        mock_params = Mock()
        mock_params.text_document.uri = "test://test.ato"
        mock_params.position.line = 3
        mock_params.position.character = 16  # After "resistors[0]."

        mock_document = Mock()
        mock_document.source = ato_code

        # Create a resistor for array access
        test_resistor = F.Resistor()

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            with patch("atopile.lsp.lsp_server.utils") as mock_utils:
                with patch(
                    "atopile.lsp.lsp_server._find_field_reference_node"
                ) as mock_find:
                    with patch(
                        "atopile.lsp.lsp_server._extract_field_reference_before_dot"
                    ) as mock_extract:
                        mock_server.workspace.get_text_document.return_value = (
                            mock_document
                        )
                        mock_utils.cursor_line.return_value = "    resistors[0]."

                        # Mock the field reference extraction
                        mock_extract.return_value = "resistors[0]"

                        # Mock finding the resistor from array access
                        mock_find.return_value = test_resistor

                        result = on_document_completion(mock_params)

                        # Should return a CompletionList with resistor attributes
                        assert isinstance(result, lsp.CompletionList)
                        assert len(result.items) > 0

                        # Check for resistor-specific completions
                        labels = [item.label for item in result.items]
                        expected_completions = [
                            "resistance",
                            "max_power",
                            "max_voltage",
                        ]

                        for expected in expected_completions:
                            assert expected in labels, (
                                f"Expected '{expected}' in array access completions:"
                                f" {labels}"
                            )

    def test_no_completion_for_invalid_field_reference(self):
        """Test that no completions are provided for invalid field references"""
        ato_code = dedent("""
            module TestModule:
                resistor = new Resistor
                # cursor position after nonexistent.
            """)

        mock_params = Mock()
        mock_params.text_document.uri = "test://test.ato"
        mock_params.position.line = 3
        mock_params.position.character = 15  # After "nonexistent."

        mock_document = Mock()
        mock_document.source = ato_code

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            with patch("atopile.lsp.lsp_server.utils") as mock_utils:
                with patch(
                    "atopile.lsp.lsp_server._find_field_reference_node"
                ) as mock_find:
                    mock_server.workspace.get_text_document.return_value = mock_document
                    mock_utils.cursor_line.return_value = "    nonexistent."

                    # Mock that the field reference cannot be resolved
                    mock_find.return_value = None

                    result = on_document_completion(mock_params)

                    # Should return None for non-existent field references
                    assert result is None

    def test_completion_with_different_module_types(self):
        """Test completion works with different types of modules"""
        test_cases = [
            (
                "capacitor",
                F.Capacitor(),
                ["capacitance", "max_voltage", "unnamed[0]", "unnamed[1]"],
            ),
            ("led", F.LED(), []),  # LED might have different or no completions
        ]

        for module_name, module_instance, expected_partial in test_cases:
            ato_code = dedent(f"""
                module TestModule:
                    {module_name} = new {module_instance.__class__.__name__}
                    # cursor position after {module_name}.
                """)

            mock_params = Mock()
            mock_params.text_document.uri = f"test://test_{module_name}.ato"
            mock_params.position.line = 3
            mock_params.position.character = len(f"    {module_name}.")

            mock_document = Mock()
            mock_document.source = ato_code

            with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
                with patch("atopile.lsp.lsp_server.utils") as mock_utils:
                    with patch(
                        "atopile.lsp.lsp_server._find_field_reference_node"
                    ) as mock_find:
                        mock_server.workspace.get_text_document.return_value = (
                            mock_document
                        )
                        mock_utils.cursor_line.return_value = f"    {module_name}."

                        # Mock finding the module
                        mock_find.return_value = module_instance

                        result = on_document_completion(mock_params)

                        # Verify we get some kind of valid response
                        if expected_partial:
                            assert isinstance(result, lsp.CompletionList)
                            assert len(result.items) > 0

                            labels = [item.label for item in result.items]
                            for expected in expected_partial:
                                assert expected in labels, (
                                    f"Expected '{expected}' in {module_name} "
                                    f"completions: {labels}"
                                )
                        else:
                            # For modules with no expected completions,
                            # just verify it doesn't crash
                            assert result is None or isinstance(
                                result, lsp.CompletionList
                            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
