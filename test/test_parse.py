import textwrap

import pytest

from atopile.parse import UserSyntaxError, parse_text_as_file


def test_syntax_error():
    src = textwrap.dedent("""
    a = 1
     b = 2  # bad indent
    """)
    with pytest.raises(UserSyntaxError) as exc_info:
        parse_text_as_file(src)

    assert exc_info.value.origin_start is not None
