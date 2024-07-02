import textwrap

import pytest
from antlr4 import TokenStream

import atopile
import atopile.parse
import atopile.parse_utils


def _parser(src: str):
    input = atopile.parse.InputStream(src)
    input.name = "test"
    return atopile.parse.make_parser(input)


@pytest.mark.parametrize(
    "txt",
    [
        "a = 1",
        "assert 1 within 2",
        "b = 1kV +/- 10% + (2V - 1V)",
    ]
)
def test_reconstructor_simple_stmt(txt: str):
    """Ensure we can faithfully re-construct the source code from a parse tree"""
    assert atopile.parse_utils.reconstruct(_parser(txt).simple_stmt()) == txt


def test_get_comments():
    module = atopile.parse.parse_text_as_file(textwrap.dedent(
        """
        # Test
        module Test:
            a = 1  # A is a variable

        """))

    token_stream: TokenStream = module.parser.getTokenStream()

    token_by_line = {token.line: token for token in token_stream.tokens}

    c = atopile.parse_utils.get_comment_from_token(token_by_line[4])
    assert c == "A is a variable"
