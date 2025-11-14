import pytest

import atopile.parse
import faebryk.core.node as fabll
from atopile.front_end import Bob
from faebryk.libs.units import P


def _parser(src: str):
    input = atopile.parse.InputStream(src)
    input.name = "test"
    parser, _ = atopile.parse.make_parser(input)
    return parser


@pytest.mark.parametrize(
    "src, qty",
    [
        ("1", fabll.Range(1, 1)),
        ("1V", fabll.Range(1 * P.V, 1 * P.V)),
        ("5V", fabll.Range(5 * P.V, 5 * P.V)),
        ("5V to 8V", fabll.Range(5 * P.V, 8 * P.V)),
        ("5 to 8V", fabll.Range(5 * P.V, 8 * P.V)),
        ("5V to 8", fabll.Range(5 * P.V, 8 * P.V)),
        ("100mV +/- 10%", fabll.Range(90 * P.mV, 110 * P.mV)),
        ("3.3V +/- 50mV", fabll.Range(3.25 * P.V, 3.35 * P.V)),
        ("3300 +/- 50mV", fabll.Range(3.25 * P.V, 3.35 * P.V)),
    ],
)
def test_literals(src: str, qty):
    ast = _parser(src).literal_physical()
    visitor = Bob()
    computed = visitor.visit(ast)

    # FIXME: don't use str comparison
    # used in place of __eq__ due to float comparison
    assert str(computed) == str(qty)
