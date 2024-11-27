import pytest

from faebryk.libs.util import write_only_property


def test_write_only_property():
    """Test that write-only property raises on get and allows set"""

    class TestClass:
        def __init__(self):
            self._value = None

        @write_only_property
        def write_only(self, value):
            self._value = value

        def get_value(self):
            return self._value

    obj = TestClass()

    # Reading should raise AttributeError
    with pytest.raises(AttributeError) as exc_info:
        _ = obj.write_only
    assert "write_only is write-only" in str(exc_info.value)

    # Writing should work
    test_value = "test"
    obj.write_only = test_value
    assert obj.get_value() == test_value
