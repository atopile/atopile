import textwrap
from typing import Iterable

from antlr4 import InputStream

from atopile.front_end import Bob, TypeRef
from atopile.parse import make_parser
from atopile.parser.AtoParser import AtoParser
from faebryk.core.parameter import Expression, Is, Parameter
from faebryk.libs.library import L
from faebryk.libs.sets.quantity_sets import Quantity_Interval
from faebryk.libs.units import P
from faebryk.libs.util import cast_assert


def _parse(src: str) -> AtoParser:
    input = InputStream(src)
    input.name = "test"
    parser, _ = make_parser(input)
    return parser


def _build_file(src: str, ref: TypeRef = TypeRef(["App"])) -> L.Module:
    tree = _parse(textwrap.dedent(src)).file_input()
    bob = Bob()
    return cast_assert(L.Module, bob.build_ast(tree, ref))


def _lonely[T](iterable: Iterable[T]) -> T:
    items = list(iterable)
    assert len(items) == 1
    return items[0]


def test_assert_is():
    module = _build_file(
        """
        module App:
            a: voltage
            b: dimensionless
            c: dimensionless
            d: dimensionless
            e: dimensionless
            f: dimensionless

            assert a is 2mV +/- 10%
            assert b is c
            assert d is e is f
        """
    )

    a, b, c, d, e, f = sorted(
        (p for p in module.get_children(False, types=Parameter)),
        key=lambda p: p.get_name(),
    )

    a_is = _lonely(a.operated_on.get_connected_nodes(types=[Expression]))
    assert isinstance(a_is, Is)
    should_be_a, should_be_2_ish_mv = a_is.operands
    assert should_be_a is a
    assert isinstance(should_be_2_ish_mv, Quantity_Interval)
    assert a_is.constrained
    # FIXME: this float comparison might be brittle
    assert Quantity_Interval.from_center_rel(2 * P.mV, 0.1) == should_be_2_ish_mv

    b_c_is = _lonely(b.operated_on.get_connected_nodes(types=[Expression]))
    assert isinstance(b_c_is, Is)
    assert b_c_is.operands == (b, c)
    assert b_c_is.constrained

    d_e_is = _lonely(d.operated_on.get_connected_nodes(types=[Expression]))
    e_f_is = _lonely(f.operated_on.get_connected_nodes(types=[Expression]))
    assert isinstance(d_e_is, Is)
    assert d_e_is.operands == (d, e)
    assert isinstance(e_f_is, Is)
    assert e_f_is.operands == (e, f)
    assert d_e_is.constrained
    assert e_f_is.constrained
