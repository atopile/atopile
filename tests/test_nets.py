import pytest
from atopile.nets import _Net

@pytest.fixture
def net():
    return _Net([])

@pytest.mark.parametrize(
    "prefix, base, suffix, expected",
    [
        (None, None, None, "net"),
        ("a", None, None, "a-net"),
        (None, "b", None, "b"),
        (None, None, 3, "net-3"),
        ("a", "b", None, "a-b"),
        ("a", "b", 3, "a-b-3"),
    ]
)
def test_net_name(net: _Net, prefix, base, suffix, expected):
    net.prefix = prefix
    net.base_name = base
    net.suffix = suffix
    assert net.get_name() == expected
