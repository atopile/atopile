import pint

from atopile.expressions import RangedValue


def test_comparitors():
    a = RangedValue(1, 2)  # a: |---|
    b = RangedValue(2, 3)  # b:     |---|
    c = RangedValue(1, 3)  # c: |-------|
    d = RangedValue(3, 4)  # d:         |---|

    assert a <= b
    assert not a < b
    assert a < d

    assert b >= a
    assert not b > a

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


def test_pretty_str():
    str_rep = "mhmm, this isn't a ranged value"
    assert RangedValue(3, 3, pint.Unit("V"), str_rep=str_rep).pretty_str() == str_rep
    assert RangedValue(3, 3, pint.Unit("V")).pretty_str() == "3V"
    assert RangedValue(3, 5, pint.Unit("V")).pretty_str() == "3 to 5 V"
    assert RangedValue(3, 5, pint.Unit("mV")).pretty_str() == "3 to 5 mV"
    assert RangedValue(3, 3.1, pint.Unit("V")).pretty_str() == "3.05V ± 50mV"

    # # Test Zeros
    assert RangedValue(0, 0, pint.Unit("V")).pretty_str() == "0V"
    assert RangedValue(0, 50, pint.Unit("V")).pretty_str() == "0 to 50 V"
    assert RangedValue(-50, 0, pint.Unit("V")).pretty_str() == "-50 to 0 V"

    # Test Negatives
    assert RangedValue(-50, -48, pint.Unit("V")).pretty_str() == "-49 ± 1 V"
    assert RangedValue(-50, -30, pint.Unit("V")).pretty_str() == "-50 to -30 V"
    assert RangedValue(-50, 50, pint.Unit("V")).pretty_str() == "± 50V"
    assert RangedValue(-50, 50, pint.Unit("mV")).pretty_str() == "± 50mV"

    # Make sure combined units compact properly
    v = RangedValue(3, 3, pint.Unit("V"))
    r = RangedValue(1000, 1000, pint.Unit("Ω"))
    i = v / r
    assert i.pretty_str() == "3mA"
