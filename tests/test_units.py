import pytest
from atopile.units import parse_number, InvalidPhysicalValue


def test_ones():
    assert parse_number("1k") == 1000
    assert parse_number("1M") == 1000_000
    assert parse_number("1m") == 0.001
    assert parse_number("1u") == 0.000_001
    assert parse_number("1n") == 0.000_000_001
    assert parse_number("1p") == 0.000_000_000_001
    assert parse_number("1") == 1
    assert parse_number("1.5k") == 1500
    assert parse_number("1.5") == 1.5


def test_units():
    assert parse_number("1kR") == 1000
    assert parse_number("1kF") == 1000
    assert parse_number("1kr") == 1000
    assert parse_number("1kf") == 1000
    assert parse_number("1R") == 1
    assert parse_number("1F") == 1
    assert parse_number("1r") == 1
    assert parse_number("1f") == 1


def test_empty():
    with pytest.raises(InvalidPhysicalValue):
        parse_number("")


def test_invalid_multiplier():
    with pytest.raises(InvalidPhysicalValue):
        parse_number("1000x")


def test_invalid_number():
    with pytest.raises(InvalidPhysicalValue):
        parse_number("abc")  # 'abc' is not a valid number
