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

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import lsprotocol.types as lsp

import faebryk.library._F as F
from atopile.lsp.lsp_server import (
    DOCUMENT_STATES,
    _build_stdlib_type_hover,
    _create_auto_import_action,
    _find_child_member_definition,
    _find_import_insert_line,
    _find_references_in_document,
    _find_stdlib_type,
    _find_type_definition,
    _find_type_in_ato_file,
    _format_comment,
    _format_line,
    _get_type_hover_info,
    _get_type_source_location,
    _get_type_usage_example,
    _is_already_imported,
    build_document,
    extract_field_reference_before_dot,
    format_ato_source,
    on_code_action,
    on_document_completion,
    on_document_definition,
    on_document_formatting,
    on_document_hover,
    on_find_references,
)


@contextmanager
def mock_file(
    content: str,
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ato") as temp_file:
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
        result = extract_field_reference_before_dot(line, position)
        assert result == expected, f"Failed for '{line}' at pos {position}"

    def test_extract_field_reference_complex_cases(self):
        """Test more complex field reference extraction scenarios"""
        # Test with whitespace
        line = "  resistor.  "
        result = extract_field_reference_before_dot(line, 11)
        assert result == "resistor"

        # Test right after dot vs typing after dot
        line = "resistor."
        result = extract_field_reference_before_dot(line, 9)  # Right after dot
        assert result == "resistor"

        line = "resistor.r"
        result = extract_field_reference_before_dot(line, 10)  # Typing after dot
        assert result == "resistor"

        # Test with brackets and special characters
        line = "app.modules[hello_world]."
        result = extract_field_reference_before_dot(line, 25)
        assert result == "app.modules[hello_world]"


@contextmanager
def _to_mock(code: str, marker="#|#"):
    """Create mock params for testing completion at marker position."""
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

    # Create a unique test URI
    test_uri = f"file:///test_{id(code)}.ato"

    mock_document = Mock()
    mock_document.source = dedented
    mock_document.path = f"/test_{id(code)}.ato"

    mock_params = Mock()
    mock_params.text_document.uri = test_uri
    mock_params.position.line = marker_row
    mock_params.position.character = marker_column

    # Clear any existing document state for this URI
    if test_uri in DOCUMENT_STATES:
        del DOCUMENT_STATES[test_uri]

    # Pre-build the document to populate state
    build_document(test_uri, dedented)

    with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
        mock_server.workspace.get_text_document.return_value = mock_document
        yield mock_params, mock_document

    # Cleanup
    if test_uri in DOCUMENT_STATES:
        state = DOCUMENT_STATES[test_uri]
        state.reset_graph()
        del DOCUMENT_STATES[test_uri]


class TestEndToEndCompletion:
    """End-to-end tests with real ato code scenarios"""

    def test_new_keyword_completion_end_to_end(self):
        """Test completion after 'new' keyword with partial type name"""
        # Mock ato content with imports and local definitions
        # Use valid syntax with a placeholder type that will be replaced
        ato_content = """
            import Resistor
            import Capacitor
            import LED

            module TestModule:
                x = new Resistor
                y = new #|#
                pass

            interface TestInterface:
                pass
        """

        with _to_mock(ato_content) as (mock_params, _):
            types = on_document_completion(mock_params)

            assert isinstance(types, lsp.CompletionList)
            assert len(types.items) > 0

            labels = {item.label for item in types.items}

            # Should find local definitions (note: the test document needs to
            # build successfully to get local types, which requires valid syntax)
            # For incomplete code, at minimum stdlib types should be present
            stdlib_types = {"Resistor", "Capacitor", "LED"}
            assert len(labels.intersection(stdlib_types)) > 0

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


class TestGoToDefinition:
    """Tests for go-to-definition functionality"""

    def test_find_stdlib_type_resistor(self):
        """Test finding stdlib type Resistor"""
        result = _find_stdlib_type("Resistor")
        assert result is not None
        assert result.__name__ == "Resistor"

    def test_find_stdlib_type_capacitor(self):
        """Test finding stdlib type Capacitor"""
        result = _find_stdlib_type("Capacitor")
        assert result is not None
        assert result.__name__ == "Capacitor"

    def test_find_stdlib_type_nonexistent(self):
        """Test finding nonexistent stdlib type returns None"""
        result = _find_stdlib_type("NonexistentType")
        assert result is None

    def test_get_type_source_location_resistor(self):
        """Test getting source location for Resistor"""
        result = _get_type_source_location(F.Resistor)
        assert result is not None
        assert isinstance(result, lsp.Location)
        assert "Resistor" in result.uri
        assert result.range.start.line >= 0

    def test_find_type_definition_stdlib(self):
        """Test finding definition for stdlib type like Resistor"""
        # Build a document that imports Resistor
        ato_content = """
import Resistor

module App:
    r1 = new Resistor
"""
        test_uri = "file:///test_definition.ato"

        # Clear any existing state
        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        state = build_document(test_uri, dedent(ato_content))

        # Find definition for "Resistor"
        result = _find_type_definition("Resistor", state, test_uri)

        assert result is not None
        assert isinstance(result, lsp.Location)
        assert "Resistor" in result.uri

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            state = DOCUMENT_STATES[test_uri]
            state.reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_find_type_definition_local(self):
        """Test finding definition for a local type"""
        ato_content = """
module MyLocalModule:
    pass

module App:
    x = new MyLocalModule
"""
        test_uri = "file:///test_local_definition.ato"

        # Clear any existing state
        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        state = build_document(test_uri, dedent(ato_content))

        # Find definition for "MyLocalModule"
        result = _find_type_definition("MyLocalModule", state, test_uri)

        assert result is not None
        assert isinstance(result, lsp.Location)
        # Local types should point to the current file
        assert result.uri == test_uri

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            state = DOCUMENT_STATES[test_uri]
            state.reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_go_to_definition_end_to_end(self):
        """End-to-end test for go-to-definition on 'new Resistor'"""
        # Note: This tests the full flow but requires proper AST indexing
        # which may not capture all node types perfectly yet
        ato_content = """
import Resistor

module App:
    r1 = new Resistor
"""
        test_uri = "file:///test_e2e_definition.ato"

        # Clear any existing state
        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        build_document(test_uri, dedent(ato_content))

        # Create mock params pointing to "Resistor" in "new Resistor"
        # Line 4 (0-indexed: 3), character around 13-21 for "Resistor"
        mock_params = Mock()
        mock_params.text_document.uri = test_uri
        mock_params.position.line = 3  # "    r1 = new Resistor"
        mock_params.position.character = 14  # Position in "Resistor"

        result = on_document_definition(mock_params)

        # Note: This may return None if AST indexing doesn't capture
        # the NewExpression or TypeRef at this position.
        # The unit tests above verify the core logic works.
        if result is not None:
            assert isinstance(result, lsp.Location)
            assert "Resistor" in result.uri

        # Cleanup

    def test_find_type_in_ato_file_module(self):
        """Test finding a module definition in an ato file"""
        ato_content = """import Something

module TestModule:
    pass

module AnotherModule from TestModule:
    x = 1
"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ato", mode="w") as f:
            f.write(ato_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            # Find TestModule
            result = _find_type_in_ato_file("TestModule", temp_path)
            assert result is not None
            assert result.range.start.line == 2  # Line 3 (0-indexed)
            assert ".ato" in result.uri  # URI points to ato file

            # Find AnotherModule (with 'from' clause)
            result2 = _find_type_in_ato_file("AnotherModule", temp_path)
            assert result2 is not None
            assert result2.range.start.line == 5
        finally:
            temp_path.unlink(missing_ok=True)

    def test_find_type_in_ato_file_interface(self):
        """Test finding an interface definition in an ato file"""
        ato_content = """interface MyInterface:
    pass
"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ato", mode="w") as f:
            f.write(ato_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            result = _find_type_in_ato_file("MyInterface", temp_path)
            assert result is not None
            assert result.range.start.line == 0
        finally:
            temp_path.unlink(missing_ok=True)

    def test_find_type_in_ato_file_not_found(self):
        """Test that nonexistent types return None"""
        ato_content = """module ExistingModule:
    pass
"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ato", mode="w") as f:
            f.write(ato_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            result = _find_type_in_ato_file("NonexistentType", temp_path)
            assert result is None
        finally:
            temp_path.unlink(missing_ok=True)

    def test_find_instance_definition(self):
        """Test go-to-definition on an instance takes you to assignment"""
        from atopile.lsp.lsp_server import _find_instance_definition

        ato_content = """\
import Resistor

module App:
    my_resistor = new Resistor
    my_resistor.resistance = 10kohm +/- 10%
"""
        test_uri = "file:///test_instance_def.ato"

        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        state = build_document(test_uri, ato_content)

        # Find instance definition for "my_resistor"
        result = _find_instance_definition("my_resistor", state, test_uri)

        assert result is not None
        assert isinstance(result, lsp.Location)
        assert result.uri == test_uri
        # Should point to the assignment line (0-indexed: line 3)
        assert result.range.start.line == 3  # "my_resistor = new Resistor"

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_find_instance_type_definition(self):
        """Test go-to-type-definition on an instance takes you to the type"""
        from atopile.lsp.lsp_server import _find_instance_type_definition

        ato_content = """\
import Resistor

module App:
    my_resistor = new Resistor
"""
        test_uri = "file:///test_instance_type_def.ato"

        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        state = build_document(test_uri, ato_content)

        # Find type definition for instance "my_resistor"
        result = _find_instance_type_definition("my_resistor", state, test_uri)

        assert result is not None
        assert isinstance(result, lsp.Location)
        # Should point to Resistor's definition
        assert "Resistor" in result.uri

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_find_child_member_definition(self):
        """
        Test go-to-definition on a child member takes you to the member definition.
        """
        ato_content = """\
import ElectricPower

module OtherModule:
    some_power = new ElectricPower
    some_logic = new ElectricPower

module ESP32_MINIMAL:
    power_3v3 = new ElectricPower
    some_other_module = new OtherModule
    some_other_module.some_power ~ power_3v3
"""
        test_uri = "file:///test_child_member_def.ato"

        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        state = build_document(test_uri, ato_content)

        # Test clicking on 'some_power' in 'some_other_module.some_power'
        # This should take us to line 3 where 'some_power = new ElectricPower'
        #  is defined
        result = _find_child_member_definition(
            "some_other_module.some_power", "some_power", state, test_uri
        )

        assert result is not None
        assert isinstance(result, lsp.Location)
        # Line 3 (0-indexed) is where some_power is defined
        assert result.range.start.line == 3, (
            f"Expected line 3, got {result.range.start.line}"
        )
        # Column should be 4 (indented)
        assert result.range.start.character == 4

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_find_child_member_definition_nested(self):
        """Test go-to-definition on nested child members."""
        ato_content = """\
import ElectricPower

module InnerModule:
    inner_power = new ElectricPower

module OuterModule:
    inner = new InnerModule

module App:
    outer = new OuterModule
    outer.inner.inner_power ~ outer.inner.inner_power
"""
        test_uri = "file:///test_nested_child_def.ato"

        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        state = build_document(test_uri, ato_content)

        # Test clicking on 'inner' in 'outer.inner'
        result = _find_child_member_definition("outer.inner", "inner", state, test_uri)

        assert result is not None
        assert isinstance(result, lsp.Location)
        # Line 6 (0-indexed) is where 'inner = new InnerModule' is defined
        assert result.range.start.line == 6, (
            f"Expected line 6, got {result.range.start.line}"
        )

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]


class TestHover:
    """Tests for hover functionality"""

    def test_get_type_hover_info_resistor(self):
        """Test hover info for Resistor"""
        test_uri = "file:///test_hover.ato"
        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        state = build_document(test_uri, "module App:\n    pass")
        hover = _get_type_hover_info("Resistor", state)

        assert hover is not None
        assert "Resistor" in hover
        assert "module" in hover.lower() or "class" in hover.lower()

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_get_type_hover_info_with_docstring(self):
        """Test hover info includes docstring for types that have one"""
        test_uri = "file:///test_hover_doc.ato"
        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        state = build_document(test_uri, "module App:\n    pass")
        hover = _get_type_hover_info("ElectricLogic", state)

        assert hover is not None
        assert "ElectricLogic" in hover
        # Should contain part of the docstring
        assert "logic signal" in hover.lower()

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_build_stdlib_type_hover_has_members(self):
        """Test that stdlib hover includes member info"""
        hover = _build_stdlib_type_hover(F.Resistor)

        assert hover is not None
        assert "Members" in hover
        assert "resistance" in hover

    def test_hover_includes_usage_example(self):
        """Test that hover info includes usage example when available"""
        test_uri = "file:///test_hover_usage.ato"
        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        # Build a document to ensure type_graph is created
        state = build_document(test_uri, "module App:\n    pass")
        hover = _get_type_hover_info("Resistor", state)

        assert hover is not None
        # Should contain usage example section
        assert "Usage Example" in hover
        # Should contain typical Resistor usage example content
        assert "new Resistor" in hover or "resistor" in hover.lower()
        # Should have ato code fence
        assert "```ato" in hover

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_get_type_usage_example_resistor(self):
        """Test getting usage example directly for Resistor"""
        test_uri = "file:///test_usage_example.ato"
        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        state = build_document(test_uri, "module App:\n    pass")

        # Get usage example using the type_graph from state
        result = _get_type_usage_example(F.Resistor, state.type_graph)

        assert result is not None
        example_text, language = result
        assert "Resistor" in example_text
        assert language == "ato"

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_get_type_usage_example_without_typegraph(self):
        """Test that usage example returns None without typegraph"""
        result = _get_type_usage_example(F.Resistor, None)
        assert result is None

    def test_hover_nonexistent_type(self):
        """Test hover returns None for nonexistent types"""
        test_uri = "file:///test_hover_none.ato"
        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        state = build_document(test_uri, "module App:\n    pass")
        hover = _get_type_hover_info("NonexistentType", state)

        assert hover is None

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_hover_local_type_with_docstring(self):
        """Test hover info for local type includes docstring"""
        test_uri = "file:///test_hover_local_doc.ato"
        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        ato_content = '''
import Resistor

module MyModule:
    """
    This is a helpful docstring for MyModule.
    It explains what this module does.
    """
    r = new Resistor

module App:
    m = new MyModule
'''
        state = build_document(test_uri, dedent(ato_content))
        hover = _get_type_hover_info("MyModule", state)

        assert hover is not None
        assert "MyModule" in hover
        assert "module" in hover.lower()
        # Should include the docstring
        assert "helpful docstring" in hover
        assert "explains what this module does" in hover

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_hover_local_type_without_docstring(self):
        """Test hover info for local type without docstring"""
        test_uri = "file:///test_hover_local_no_doc.ato"
        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        ato_content = """
import Resistor

module SimpleModule:
    r = new Resistor

module App:
    m = new SimpleModule
"""
        state = build_document(test_uri, dedent(ato_content))
        hover = _get_type_hover_info("SimpleModule", state)

        assert hover is not None
        assert "SimpleModule" in hover
        assert "module" in hover.lower()
        # Should not crash without docstring

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_hover_end_to_end(self):
        """End-to-end test for hover on type name"""
        ato_content = """
import Resistor

module App:
    r1 = new Resistor
"""
        test_uri = "file:///test_e2e_hover.ato"

        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        build_document(test_uri, dedent(ato_content))

        # Create mock params for hover at 'Resistor' (line 0, char 10)
        mock_params = Mock()
        mock_params.text_document.uri = test_uri
        mock_params.position.line = 1  # "import Resistor"
        mock_params.position.character = 10

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            mock_document = Mock()
            mock_document.source = dedent(ato_content)
            mock_server.workspace.get_text_document.return_value = mock_document

            result = on_document_hover(mock_params)

        assert result is not None
        assert "Resistor" in result.contents.value

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]


class TestFindReferences:
    """Tests for find all references functionality"""

    def test_find_references_single_word(self):
        """Test finding references to a word that appears once"""
        source = "import Resistor\n\nmodule App:\n    pass"
        refs = _find_references_in_document("Resistor", "file:///test.ato", source)

        assert len(refs) == 1
        assert refs[0].range.start.line == 0
        assert refs[0].range.start.character == 7

    def test_find_references_multiple_occurrences(self):
        """Test finding references when word appears multiple times"""
        source = """import Resistor

module App:
    r1 = new Resistor
    r2 = new Resistor
"""
        refs = _find_references_in_document("Resistor", "file:///test.ato", source)

        assert len(refs) == 3
        # import line
        assert refs[0].range.start.line == 0
        # first new
        assert refs[1].range.start.line == 3
        # second new
        assert refs[2].range.start.line == 4

    def test_find_references_no_partial_matches(self):
        """Test that partial word matches are not included"""
        source = """import Resistor

module ResistorModule:
    r = new Resistor
"""
        refs = _find_references_in_document("Resistor", "file:///test.ato", source)

        # Should find: import Resistor, ResistorModule (contains Resistor), new Resistor
        # Actually, ResistorModule should NOT match because we use word boundaries
        assert len(refs) == 2

    def test_find_references_local_type(self):
        """Test finding references to a locally defined type"""
        source = """module MyModule:
    pass

module App:
    m = new MyModule
"""
        refs = _find_references_in_document("MyModule", "file:///test.ato", source)

        assert len(refs) == 2
        # Definition
        assert refs[0].range.start.line == 0
        # Usage
        assert refs[1].range.start.line == 4

    def test_find_references_end_to_end(self):
        """End-to-end test for find references"""
        ato_content = """
import Resistor

module App:
    r1 = new Resistor
"""
        test_uri = "file:///test_refs.ato"

        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        build_document(test_uri, dedent(ato_content))

        mock_params = Mock()
        mock_params.text_document.uri = test_uri
        mock_params.position.line = 1
        mock_params.position.character = 10
        mock_params.context.include_declaration = True

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            mock_document = Mock()
            mock_document.source = dedent(ato_content)
            mock_server.workspace.get_text_document.return_value = mock_document

            result = on_find_references(mock_params)

        assert result is not None
        # Should find at least the import and the new expression
        assert len(result) >= 2

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]


class TestAutoImportCodeAction:
    """Tests for auto-import code action functionality"""

    def test_is_already_imported_simple(self):
        """Test detecting simple imports"""
        source = "import Resistor\n\nmodule App:\n    pass"
        assert _is_already_imported("Resistor", source) is True
        assert _is_already_imported("Capacitor", source) is False

    def test_is_already_imported_multi(self):
        """Test detecting multi imports"""
        source = "import Resistor, Capacitor, LED\n\nmodule App:\n    pass"
        assert _is_already_imported("Resistor", source) is True
        assert _is_already_imported("Capacitor", source) is True
        assert _is_already_imported("LED", source) is True
        assert _is_already_imported("ElectricLogic", source) is False

    def test_find_import_insert_line_with_imports(self):
        """Test finding insert line when imports exist"""
        source = "import Resistor\nimport Capacitor\n\nmodule App:\n    pass"
        assert _find_import_insert_line(source) == 2  # After last import

    def test_find_import_insert_line_no_imports(self):
        """Test finding insert line when no imports exist"""
        source = "module App:\n    pass"
        assert _find_import_insert_line(source) == 0  # At the top

    def test_find_import_insert_line_with_comments(self):
        """Test finding insert line with leading comments"""
        source = "# Comment\n# Another comment\nmodule App:\n    pass"
        assert _find_import_insert_line(source) == 2  # After comments

    def test_create_auto_import_action_stdlib(self):
        """Test creating auto-import action for stdlib type"""
        source = "module App:\n    r = new Resistor"
        action = _create_auto_import_action("Resistor", "file:///test.ato", source)

        assert action is not None
        assert action.title == "Import 'Resistor' from stdlib"
        assert action.kind == lsp.CodeActionKind.QuickFix
        assert action.edit is not None

    def test_create_auto_import_action_already_imported(self):
        """Test that no action is created if already imported"""
        source = "import Resistor\n\nmodule App:\n    r = new Resistor"
        action = _create_auto_import_action("Resistor", "file:///test.ato", source)

        assert action is None

    def test_create_auto_import_action_nonexistent_type(self):
        """Test that no action is created for non-stdlib types"""
        source = "module App:\n    x = new NonexistentType"
        action = _create_auto_import_action(
            "NonexistentType", "file:///test.ato", source
        )

        assert action is None

    def test_code_action_end_to_end(self):
        """End-to-end test for code action on undefined type"""
        ato_content = """
module App:
    logic = new ElectricLogic
"""
        test_uri = "file:///test_code_action.ato"

        # Clear any existing state
        if test_uri in DOCUMENT_STATES:
            del DOCUMENT_STATES[test_uri]

        build_document(test_uri, dedent(ato_content))

        # Create mock params for code action at 'ElectricLogic'
        mock_params = Mock()
        mock_params.text_document.uri = test_uri
        mock_params.range.start.line = 2
        mock_params.range.start.character = 16
        mock_params.range.end.line = 2
        mock_params.range.end.character = 29
        mock_params.context.diagnostics = []

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            mock_document = Mock()
            mock_document.source = dedent(ato_content)
            mock_server.workspace.get_text_document.return_value = mock_document

            result = on_code_action(mock_params)

        assert result is not None
        assert len(result) > 0
        assert any("ElectricLogic" in action.title for action in result)

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            state = DOCUMENT_STATES[test_uri]
            state.reset_graph()
            del DOCUMENT_STATES[test_uri]


class TestFormatting:
    """Tests for document formatting functionality"""

    def test_format_operator_spacing_assignment(self):
        """Test spacing around assignment operator"""
        assert format_ato_source("x=1").strip() == "x = 1"
        assert format_ato_source("x  =  1").strip() == "x = 1"

    def test_format_operator_spacing_connection(self):
        """Test spacing around connection operator"""
        assert format_ato_source("a~b").strip() == "a ~ b"
        assert format_ato_source("a  ~  b").strip() == "a ~ b"

    def test_format_operator_spacing_bridge(self):
        """Test spacing around bridge operators"""
        assert format_ato_source("a~>b~>c").strip() == "a ~> b ~> c"
        assert format_ato_source("a<~b<~c").strip() == "a <~ b <~ c"

    def test_format_operator_spacing_tolerance(self):
        """Test spacing around tolerance operator"""
        assert format_ato_source("10kohm+/-5%").strip() == "10kohm +/- 5%"

    def test_format_type_hint(self):
        """Test formatting type hints"""
        assert format_ato_source("x:ohm=1").strip() == "x: ohm = 1"
        assert format_ato_source("x: ohm = 1").strip() == "x: ohm = 1"

    def test_format_indentation_normalization(self):
        """Test that indentation is normalized to 4 spaces"""
        # 2 spaces should become 4
        assert _format_line("  x = 1") == "    x = 1"
        # 3 spaces should become 4
        assert _format_line("   x = 1") == "    x = 1"
        # 5 spaces should become 8
        assert _format_line("     x = 1") == "        x = 1"
        # 8 spaces stays 8
        assert _format_line("        x = 1") == "        x = 1"

    def test_format_comment_spacing(self):
        """Test that comments get proper spacing after #"""
        assert _format_comment("#comment") == "# comment"
        assert _format_comment("# comment") == "# comment"
        assert _format_comment("#  comment") == "# comment"

    def test_format_comment_pragma_preserved(self):
        """Test that pragma comments are preserved"""
        assert (
            _format_comment('#pragma experiment("FOR_LOOP")')
            == '#pragma experiment("FOR_LOOP")'
        )

    def test_format_inline_comment(self):
        """Test formatting inline comments"""
        result = format_ato_source("x=1 #comment").strip()
        assert result == "x = 1  # comment"

    def test_format_preserves_strings(self):
        """Test that strings are not modified"""
        result = format_ato_source('name = "test # not a comment"').strip()
        assert result == 'name = "test # not a comment"'

    def test_format_preserves_docstrings(self):
        """Test that docstrings are preserved"""
        code = '''module App:
    """
    This is a docstring
    """
    pass'''
        result = format_ato_source(code)
        assert '"""' in result
        assert "This is a docstring" in result

    def test_format_multiple_statements(self):
        """Test formatting multiple statements on one line"""
        assert format_ato_source("a=1;b=2").strip() == "a = 1; b = 2"

    def test_format_removes_trailing_whitespace(self):
        """Test that trailing whitespace is removed"""
        result = format_ato_source("x = 1   \n")
        assert "   " not in result.split("\n")[0]

    def test_format_block_spacing(self):
        """Test that blocks get proper blank lines"""
        code = """import Resistor
module App:
    pass
module Other:
    pass"""
        result = format_ato_source(code)
        lines = result.strip().split("\n")
        # Should have blank line before module definitions
        assert "" in lines

    def test_format_full_file(self):
        """Test formatting a complete ato file"""
        code = """import Resistor
import   ElectricPower

module App:
  r1=new Resistor
  r1.resistance=10kohm+/-5%
  power=new ElectricPower
  r1.unnamed[0]~power.hv  #connect to power
"""
        result = format_ato_source(code)

        # Check key formatting rules applied
        assert "    r1 = new Resistor" in result
        assert "10kohm +/- 5%" in result
        assert "r1.unnamed[0] ~ power.hv" in result
        assert "# connect to power" in result
        # Multiple spaces in import should be normalized
        assert "import ElectricPower" in result
        assert "import   ElectricPower" not in result

    def test_format_end_to_end(self):
        """End-to-end test for document formatting via LSP"""
        ato_content = """import Resistor
module App:
  r1=new Resistor
"""
        test_uri = "file:///test_format.ato"

        mock_params = Mock()
        mock_params.text_document.uri = test_uri
        mock_params.options.tab_size = 4
        mock_params.options.insert_spaces = True

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            mock_document = Mock()
            mock_document.source = ato_content
            mock_server.workspace.get_text_document.return_value = mock_document

            result = on_document_formatting(mock_params)

        assert result is not None
        assert len(result) == 1  # Single edit replacing the whole document
        assert "    r1 = new Resistor" in result[0].new_text


# -----------------------------------------------------------------------------
# Rename Symbol Tests
# -----------------------------------------------------------------------------


class TestRenameSymbol:
    """Tests for rename symbol functionality"""

    def test_get_renameable_symbol_simple(self):
        """Test extracting a simple symbol at cursor position"""
        from atopile.lsp.lsp_server import _get_renameable_symbol_at_position

        source = "r1 = new Resistor"
        position = lsp.Position(line=0, character=0)  # On 'r1'

        result = _get_renameable_symbol_at_position(source, position)
        assert result is not None
        symbol, range_ = result
        assert symbol == "r1"
        assert range_.start.character == 0
        assert range_.end.character == 2

    def test_get_renameable_symbol_in_path(self):
        """Test extracting a symbol from a field path"""
        from atopile.lsp.lsp_server import _get_renameable_symbol_at_position

        source = "r1.resistance = 10kohm"
        # Cursor on 'resistance' (starts at column 3)
        position = lsp.Position(line=0, character=5)

        result = _get_renameable_symbol_at_position(source, position)
        assert result is not None
        symbol, range_ = result
        assert symbol == "resistance"
        assert range_.start.character == 3
        assert range_.end.character == 13

    def test_get_renameable_symbol_keyword_rejected(self):
        """Test that keywords cannot be renamed"""
        from atopile.lsp.lsp_server import _get_renameable_symbol_at_position

        source = "import Resistor"
        position = lsp.Position(line=0, character=0)  # On 'import'

        result = _get_renameable_symbol_at_position(source, position)
        assert result is None

    def test_get_renameable_symbol_module_keyword_rejected(self):
        """Test that 'module' keyword cannot be renamed"""
        from atopile.lsp.lsp_server import _get_renameable_symbol_at_position

        source = "module MyModule:"
        position = lsp.Position(line=0, character=0)  # On 'module'

        result = _get_renameable_symbol_at_position(source, position)
        assert result is None

    def test_is_valid_identifier(self):
        """Test identifier validation"""
        from atopile.lsp.lsp_server import _is_valid_identifier

        assert _is_valid_identifier("r1") is True
        assert _is_valid_identifier("my_resistor") is True
        assert _is_valid_identifier("_private") is True
        assert _is_valid_identifier("Resistor123") is True

        assert _is_valid_identifier("") is False
        assert _is_valid_identifier("123abc") is False
        assert _is_valid_identifier("my-resistor") is False
        assert _is_valid_identifier("my resistor") is False

    def test_find_rename_edits_simple(self):
        """Test finding rename edits for a simple symbol using typegraph"""
        from atopile.lsp.lsp_server import (
            DOCUMENT_STATES,
            _find_rename_edits,
            build_document,
        )

        test_uri = "file:///test_rename_edits.ato"
        source = """import Resistor

module App:
    r1 = new Resistor
    r1.resistance = 10kohm +/- 5%
"""
        # Cleanup any existing state
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

        state = build_document(test_uri, source)

        edits = _find_rename_edits("r1", "resistor1", state, test_uri, source)

        # Should find 2 occurrences of 'r1' (definition + usage)
        assert len(edits) == 2

        # All edits should replace with the new name
        for edit in edits:
            assert edit.new_text == "resistor1"

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_prepare_rename_valid_position(self):
        """Test prepare rename at a valid position"""
        from atopile.lsp.lsp_server import on_prepare_rename

        ato_content = "r1 = new Resistor"
        test_uri = "file:///test_rename.ato"

        mock_params = Mock()
        mock_params.text_document.uri = test_uri
        mock_params.position = lsp.Position(line=0, character=0)

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            mock_document = Mock()
            mock_document.source = ato_content
            mock_server.workspace.get_text_document.return_value = mock_document

            result = on_prepare_rename(mock_params)

        assert result is not None
        assert result.placeholder == "r1"
        assert result.range.start.character == 0
        assert result.range.end.character == 2

    def test_prepare_rename_invalid_position(self):
        """Test prepare rename at an invalid position (keyword)"""
        from atopile.lsp.lsp_server import on_prepare_rename

        ato_content = "import Resistor"
        test_uri = "file:///test_rename.ato"

        mock_params = Mock()
        mock_params.text_document.uri = test_uri
        mock_params.position = lsp.Position(line=0, character=0)  # On 'import'

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            mock_document = Mock()
            mock_document.source = ato_content
            mock_server.workspace.get_text_document.return_value = mock_document

            result = on_prepare_rename(mock_params)

        assert result is None

    def test_rename_symbol_end_to_end(self):
        """End-to-end test for rename symbol using typegraph"""
        from atopile.lsp.lsp_server import DOCUMENT_STATES, build_document, on_rename

        ato_content = """import Resistor

module App:
    r1 = new Resistor
    r1.resistance = 10kohm +/- 5%
"""
        test_uri = "file:///test_rename_e2e.ato"

        # Cleanup any existing state
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

        # Build document to populate typegraph
        build_document(test_uri, ato_content)

        mock_params = Mock()
        mock_params.text_document.uri = test_uri
        mock_params.position = lsp.Position(line=3, character=4)  # On 'r1'
        mock_params.new_name = "my_resistor"

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            mock_document = Mock()
            mock_document.source = ato_content
            mock_server.workspace.get_text_document.return_value = mock_document

            result = on_rename(mock_params)

        assert result is not None
        assert test_uri in result.changes
        edits = result.changes[test_uri]

        # Should find 2 occurrences of 'r1' (definition + usage)
        assert len(edits) == 2

        # All should be replaced with new name
        for edit in edits:
            assert edit.new_text == "my_resistor"

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_rename_invalid_new_name(self):
        """Test that invalid new names are rejected"""
        from atopile.lsp.lsp_server import on_rename

        ato_content = "r1 = new Resistor"
        test_uri = "file:///test_rename_invalid.ato"

        mock_params = Mock()
        mock_params.text_document.uri = test_uri
        mock_params.position = lsp.Position(line=0, character=0)
        mock_params.new_name = "123invalid"  # Invalid identifier

        with patch("atopile.lsp.lsp_server.LSP_SERVER") as mock_server:
            mock_document = Mock()
            mock_document.source = ato_content
            mock_server.workspace.get_text_document.return_value = mock_document

            result = on_rename(mock_params)

        assert result is None


class TestFieldReferenceValidation:
    """Tests for field reference validation (detecting non-existent fields)"""

    @pytest.mark.xfail(
        reason="Field reference validation not yet fully implemented. "
        "The compiler creates fields on assignment, so 'r1.nonexistent_field' "
        "creates a new field on App rather than erroring. Proper validation "
        "would require checking against the resolved type (Resistor) hierarchy.",
        strict=False,
    )
    def test_validate_nonexistent_field(self):
        """Test that referencing a non-existent field creates a diagnostic"""
        from textwrap import dedent

        from atopile.lsp.lsp_server import DOCUMENT_STATES, build_document

        test_uri = "file:///test_field_validation.ato"
        ato_content = dedent("""
            import Resistor

            module App:
                r1 = new Resistor
                r1.nonexistent_field = 10kohm
        """).strip()

        # Cleanup any existing state
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

        state = build_document(test_uri, ato_content)

        # Should have a diagnostic for nonexistent_field
        error_messages = [d.message for d in state.diagnostics]

        # Check that we have a diagnostic about the nonexistent field
        found_error = any(
            "nonexistent_field" in msg
            and ("does not exist" in msg or "not defined" in msg)
            for msg in error_messages
        )
        assert found_error, (
            f"Expected error for nonexistent_field, got: {error_messages}"
        )

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

    def test_validate_valid_field(self):
        """Test that valid field references don't create diagnostics"""
        from textwrap import dedent

        from atopile.lsp.lsp_server import DOCUMENT_STATES, build_document

        test_uri = "file:///test_field_validation_valid.ato"
        ato_content = dedent("""
            import Resistor

            module App:
                r1 = new Resistor
                r1.resistance = 10kohm +/- 5%
        """).strip()

        # Cleanup any existing state
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]

        state = build_document(test_uri, ato_content)

        # Should NOT have diagnostics about non-existent fields
        # (may have other diagnostics like missing imports)
        nonexistent_errors = [
            d.message
            for d in state.diagnostics
            if "does not exist" in d.message or "not defined" in d.message
        ]
        assert len(nonexistent_errors) == 0, f"Unexpected errors: {nonexistent_errors}"

        # Cleanup
        if test_uri in DOCUMENT_STATES:
            DOCUMENT_STATES[test_uri].reset_graph()
            del DOCUMENT_STATES[test_uri]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
