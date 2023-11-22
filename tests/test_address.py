from pathlib import Path

import pytest

from atopile.address import AddrStr


def test_addrstr_properties():
    addr = AddrStr("/path/to/file:test.node")

    assert addr.file == Path("/path/to/file")
    assert addr.node_as_str == "test.node"
    assert addr.node_as_ref == ("test", "node")


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
