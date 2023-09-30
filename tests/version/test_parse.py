import pytest
from atopile.version import parse
from semver import Version

# disable docstring checks - it's a test file
# pylint: disable=C0116


def test_parse_valid_version():
    assert parse("1.2.3") == Version(1, 2, 3)


def test_parse_version_with_build_info():
    assert parse("1.2.3-a1") == Version(1, 2, 3, "a1")


def test_parse_version_with_prerelease_and_build_info():
    assert parse("1.2.3+build123") == Version(1, 2, 3, None, "build123")


def test_parse_version_with_hatch_shenanigans():
    assert parse("0.0.17.dev0+g0151069.d20230928") == Version(0, 0, 17, "dev0", "g0151069.d20230928")


def test_parse_invalid_version():
    with pytest.raises(ValueError):
        parse("not a version")
