from antlr4 import InputStream

from atopile.expressions import RangedValue, Expression, Symbol
from atopile.front_end import Roley
from atopile.parse import make_parser
from atopile.parser.AtopileParser import AtopileParser


def parse(src_code: str) -> AtopileParser.Arithmetic_expressionContext:
    """Parse a string as a file input."""
    input = InputStream(src_code)
    input.name = "<inline>"
    parser = make_parser(input)
    return parser.arithmetic_expression()


roley = Roley("//a:b::")


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


def test_units():
    assert _run("1 V + 205 mV") == RangedValue(1205, 1205, "mV")
    assert _run("1V + 205mV") == RangedValue(1205, 1205, "mV")
    assert _run("1V ± 205mV + 1V ± 1mV") == RangedValue(1794, 2206, "mV")


def test_parens():
    assert _run("(1 + 2) * 3") == 9
    assert _run("1 + (2 * 3)") == 7
    assert _run("1 * (2 + 3)") == 5
    assert _run("1 * (2 + 3) * 4") == 20
    assert _run("1 * (2 + 3) * 4 + 5") == 25
    assert _run("1 * (2 + 3) * (4 + 5)") == 45
    assert _run("1 * (2 + 3) * (4 + 5) + 6") == 51


def test_simple_pseudo_symbols():
    a = _run("1 + 2 + c.d.e")
    assert callable(a)
    assert isinstance(a, Expression)
    assert a({"//a:b::c.d.e": 5}) == 8
    assert a.symbols == {Symbol("//a:b::c.d.e")}


def test_pseudo_symbols():
    context = {
        "//a:b::a.a.a": 4,
        "//a:b::b": 3,
        "//a:b::c": 9,
    }
    assert _run("(a.a.a**b + 17) / c + 53")(context) == 62
