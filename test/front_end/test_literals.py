import pytest

import atopile.parse
from atopile.front_end import Bob
from faebryk.libs.library import L
from faebryk.libs.units import P


def _parser(src: str):
    input = atopile.parse.InputStream(src)
    input.name = "test"
    parser, _ = atopile.parse.make_parser(input)
    return parser


@pytest.mark.parametrize(
    "src, qty",
    [
        ("1", L.Range(1, 1)),
        ("1V", L.Range(1 * P.V, 1 * P.V)),
        ("5V", L.Range(5 * P.V, 5 * P.V)),
        ("5V to 8V", L.Range(5 * P.V, 8 * P.V)),
        ("5 to 8V", L.Range(5 * P.V, 8 * P.V)),
        ("5V to 8", L.Range(5 * P.V, 8 * P.V)),
        ("100mV +/- 10%", L.Range(90 * P.mV, 110 * P.mV)),
        ("3.3V +/- 50mV", L.Range(3.25 * P.V, 3.35 * P.V)),
        ("3300 +/- 50mV", L.Range(3.25 * P.V, 3.35 * P.V)),
    ],
)
def test_literals(src: str, qty):
    ast = _parser(src).literal_physical()
    visitor = Bob()
    computed = visitor.visit(ast)

    # FIXME: don't use str comparison
    # used in place of __eq__ due to float comparison
    assert str(computed) == str(qty)
