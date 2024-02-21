import pint

from atopile.expressions import RangedValue


def test_comparitors():
    a = RangedValue(1, 2)
    b = RangedValue(2, 3)
    c = RangedValue(1, 3)

    assert a < b
    assert b > a
    assert not a.within(b)
    assert a.within(c)


def test_units():
    a = RangedValue(1000, 2000, "mV")
    b = RangedValue(1, 2, "kV")
    assert a < b

    c = a * b
    assert c.unit == pint.Unit("V") ** 2


def test_arithmetic():
    assert RangedValue(1, 2) + RangedValue(2, 3) == RangedValue(3, 5)
    assert RangedValue(1, 2) - RangedValue(2, 3) == RangedValue(-2, 0)
    assert RangedValue(1, 2) * RangedValue(2, 3) == RangedValue(2, 6)
