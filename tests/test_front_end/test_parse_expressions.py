from antlr4 import InputStream

from atopile.parser.AtopileParser import AtopileParser
from atopile.parse import make_parser
from atopile.front_end import Roley


def parse(src_code: str) -> AtopileParser.Arithmetic_expressionContext:
    """Parse a string as a file input."""
    input = InputStream(src_code)
    input.name = "<inline>"
    parser = make_parser(input)
    return parser.arithmetic_expression()


roley = Roley()


def _run(src_code: str):
    return roley.visit(parse(src_code))


def test_basic_expression():
    assert _run("1 + 2") == 3
    assert _run("1 - 2") == -1
    assert _run("1 * 2") == 2
    assert _run("1 / 2") == 0.5
    assert _run("1 ** 2") == 1
    assert _run("1 + 2 * 3") == 7
    assert _run("1 * 2 + 3") == 5
    assert _run("1 * (2 + 3)") == 5
    assert _run("(1 * 2) ** 3") == 8
