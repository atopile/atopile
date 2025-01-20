import pytest
from semver import Version

from atopile import errors
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
    assert match(">=1.2.0, <1.3.0", version)
    assert match(">=1.2.0, <1.2.3", version) is False
    assert match(">=1.2.0, <1.2.4", version)


def test_match_union(version):
    assert match(">=1.2.0 || >=2.0.0", version)
    assert match(">=1.3.0 || >=2.0.0", version) is False
    assert match(">=2.0.0 || >=1.2.0", version)


def test_match_negation(version):
    assert match("!1.2.3", version) is False
    assert match("!1.2.4", version)


def test_syntax_error(version):
    with pytest.raises(errors.UserException):
        match("abc", version)


def test_parse_valid_version():
    assert parse("1.2.3") == Version(1, 2, 3)


def test_parse_version_with_build_info():
    assert parse("1.2.3-a1") == Version(1, 2, 3, "a1")


def test_parse_version_with_prerelease_and_build_info():
    assert parse("1.2.3+build123") == Version(1, 2, 3, None, "build123")


def test_parse_version_with_hatch_shenanigans():
    assert parse("0.0.17.dev0+g0151069.d20230928") == Version(
        0, 0, 17, "dev0", "g0151069.d20230928"
    )


def test_parse_invalid_version():
    with pytest.raises(ValueError):
        parse("not a version")


def test_v_prefix(version):
    assert parse("v1.2.3") == Version(1, 2, 3)
    assert match("==v1.2.3", version)
    assert match("==v1.2.4", version) is False
    assert match("==v1.2.4", version) is False


def test_stringify(version):
    assert str(parse("v1.2.3")) == "1.2.3"
