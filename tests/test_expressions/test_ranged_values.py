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
    assert a == RangedValue(1, 2)


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
    assert RangedValue(1, 2) / RangedValue(2, 3) == RangedValue(1 / 3, 1)
    assert RangedValue(1, 2) ** 2 == RangedValue(1, 4)

    assert RangedValue(1, 2) + 2 == RangedValue(3, 4)
    assert RangedValue(1, 2) - 3 == RangedValue(-2, -1)
    assert RangedValue(1, 2) * 4 == RangedValue(4, 8)
    assert RangedValue(1, 2) / 5 == RangedValue(1 / 5, 2 / 5)

    assert 2 + RangedValue(1, 2) == RangedValue(3, 4)
    assert 3 - RangedValue(1, 2) == RangedValue(-2, -1)
    assert 4 * RangedValue(1, 2) == RangedValue(4, 8)
    assert 5 / RangedValue(1, 2) == RangedValue(5 / 2, 5)
