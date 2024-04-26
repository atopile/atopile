import pytest

from antlr4 import InputStream

from atopile import errors
from atopile.expressions import RangedValue
from atopile.front_end import HandlesPrimaries
from atopile.parse import make_parser
from atopile.parser.AtopileParser import AtopileParser


def parse(src_code: str) -> AtopileParser.Arithmetic_expressionContext:
    """Parse a string as a file input."""
    input = InputStream(src_code)
    input.name = "<inline>"
    parser = make_parser(input)
    return parser.atom()


def _run(src_code: str):
    return HandlesPrimaries().visit(parse(src_code))


def test_basic_expression():
    assert _run("1") == 1
    assert _run("1.5") == 1.5
    assert _run("2") == 2


def test_units():
    assert _run("3mV") == RangedValue(3, 3, "mV")
    assert _run("5 mV") == RangedValue(5, 5, "mV")


def test_name():
    assert _run("foo") == ("foo",)
    assert _run("foo.bar") == ("foo", "bar")


@pytest.mark.parametrize(
    "src, expected",
    (
        ("3mV to 5mV", RangedValue(3, 5, "mV")),
        ("6mV to 7V", RangedValue(6, 7000, "millivolt")),
        ("-2V to 7V", RangedValue(-2, 7, "V")),

        # Mix units
        ("-2mV to 7V", RangedValue(-2, 7000, "millivolt")),

        # One unit
        ("3mV to 5", RangedValue(3, 5, "mV")),
    )
)
def test_bound_quantity(src, expected):
    assert _run(src) == expected


@pytest.mark.parametrize(
    "src, expected",
    (
        ("3mV +/- 5mV", RangedValue(-2, 8, "millivolt")),
        ("6mV ± 7mV", RangedValue(-1, 13, "millivolt")),
        ("-6mV ± 7mV", RangedValue(-13, 1, "millivolt")),

        # Mix units
        ("-6V ± 7V", RangedValue(-13, 1, "V")),

        # One unit
        ("6V ± 2", RangedValue(4, 8, "V")),
    )
)
def test_bilateral_quantity(src, expected):
    assert _run(src) == expected


def test_bilateral_quantity_percent():
    r: RangedValue = _run("5.1kohm ± 1%")
    assert r.min_val == pytest.approx(5.1 * 0.99)
    assert r.max_val == pytest.approx(5.1 * 1.01)
    assert str(r.unit) == "kiloohm"


def test_zero_proportional_qty():
    with pytest.raises(errors.AtoError):
        _run("0V ± 10%")
