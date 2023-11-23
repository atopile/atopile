from pathlib import Path

import pytest

from atopile.address import AddrStr, AddrValueError


def test_addrstr_properties():
    addr = AddrStr("/path/to/file:test.node")

    assert addr.file == Path("/path/to/file")
    assert addr.node_as_str == "test.node"
    assert addr.node == ("test", "node")


def test_addrstr_properties2():
    addr = AddrStr("/path/to/file")

    assert addr.file == Path("/path/to/file")
    assert addr.node_as_str == ""
    assert addr.node == tuple()


def test_addrstr_properties3():
    addr = AddrStr(":node.path")

    assert addr.file is None
    assert addr.node_as_str == "node.path"
    assert addr.node == ("node", "path")


@pytest.mark.parametrize(
    "path, node, expected",
    [
        ("/path/to/file", ("test", "node"), "/path/to/file:test.node"),
        (Path("/path/to/file"), ("test", "node"), "/path/to/file:test.node"),
        (Path("/path/to/file"), "test.node", "/path/to/file:test.node"),
        ("/path/to/file", None, "/path/to/file:"),
        (None, ("test", "node"), ":test.node"),
        (None, None, ":"),
    ],
)
def test_addrstr_from_parts(path, node, expected):
    assert AddrStr.from_parts(path, node) == expected


@pytest.mark.parametrize(
    "address",
    [
        "::",
        "/path:./to/file:",
    ],
)
def test_addrstr_validation(address: str):
    with pytest.raises(AddrValueError):
        AddrStr.from_str(address)
