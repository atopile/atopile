import textwrap

import pytest

from atopile.compiler.parse import UserSyntaxError, parse_text_as_file


def test_syntax_error():
    src = textwrap.dedent("""
    a = 1
     b = 2  # bad indent
    """)
    with pytest.raises(UserSyntaxError) as exc_info:
        parse_text_as_file(src)

    assert exc_info.value.origin_start is not None


def test_identifier_starting_with_number():
    """Test that identifiers starting with numbers produce a clear error message."""
    src = textwrap.dedent("""
    module App:
        68f47 = new Electrical
    """)
    with pytest.raises(UserSyntaxError) as exc_info:
        parse_text_as_file(src)

    assert exc_info.value.message == (
        "Invalid name `68f47`: names cannot start with a number."
    )


def test_plain_number_where_name_expected():
    """Test that a plain number where a name is expected produces a clear error."""
    src = textwrap.dedent("""
    module App:
        123 = new Electrical
    """)
    with pytest.raises(UserSyntaxError) as exc_info:
        parse_text_as_file(src)

    assert exc_info.value.message == (
        "Invalid name `123`: names cannot start with a number."
    )
