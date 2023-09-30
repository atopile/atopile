import pytest
from atopile.version import match, parse

# disable docstring checks - it's a test file
# pylint: disable=C0116


@pytest.fixture
def version():
    return parse("1.2.3")


def test_match_equal(version):
    assert match("==1.2.3", version)
    assert match("==1.2.4", version) is False
    assert match("==1.2.4", version) is False


def test_match_greater_than(version):
    assert match(">1.2.2", version)
    assert match(">1.2.3", version) is False
    assert match(">1.2.4", version) is False


def test_match_less_than(version):
    assert match("<1.2.4", version)
    assert match("<1.2.3", version) is False
    assert match("<1.2.2", version) is False


def test_match_greater_than_or_equal(version):
    assert match(">=1.2.2", version)
    assert match(">=1.2.3", version)
    assert match(">=1.2.4", version) is False


def test_match_less_than_or_equal(version):
    assert match("<=1.2.4", version)
    assert match("<=1.2.3", version)
    assert match("<=1.2.2", version) is False


def test_match_caret(version):
    assert match("^1.2.3", version)
    assert match("^1.3.0", version) is False
    assert match("^2.0.0", version) is False


def test_match_dirty():
    version = parse("0.0.17-dev6+gdaf6b51")
    assert match("^0.0.16", version)
    assert match("^0.0.17", version)
    assert match("^0.0.18", version) is False


def test_match_tilde(version):
    assert match("~1.2.3", version)
    assert match("~1.3.0", version) is False
    assert match("~2.0.0", version) is False


def test_match_multiple(version):
    assert match(">=1.2.0 <1.3.0", version)
    assert match(">=1.2.0 <1.2.3", version) is False
    assert match(">=1.2.0 <1.2.4", version)


def test_match_union(version):
    assert match(">=1.2.0 || >=2.0.0", version)
    assert match(">=1.3.0 || >=2.0.0", version) is False
    assert match(">=2.0.0 || >=1.2.0", version)


def test_match_negation(version):
    assert match("!1.2.3", version) is False
    assert match("!1.2.4", version)


def test_syntax_error(version):
    with pytest.raises(SyntaxError):
        match("abc", version)
