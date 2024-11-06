import pytest

from faebryk.core.node import Node
from faebryk.library.has_schematic_hints import _hint, has_schematic_hints


@pytest.fixture
def custom_hints():
    return has_schematic_hints(lock_rotation_certainty=0.8, symbol_rotation=90)


def test_default_hint_values():
    """Default hint values should match their defined defaults"""
    hints = has_schematic_hints()
    assert hints.lock_rotation_certainty == 0.6
    assert hints.symbol_rotation is None


def test_custom_hint_values(custom_hints):
    """Custom hint values should be retrievable"""
    assert custom_hints.lock_rotation_certainty == 0.8
    assert custom_hints.symbol_rotation == 90


def test_hint_value_modification():
    """Hint values should be modifiable after creation"""
    hints = has_schematic_hints()
    hints.lock_rotation_certainty = 0.7
    hints.symbol_rotation = 180

    assert hints.lock_rotation_certainty == 0.7
    assert hints.symbol_rotation == 180


def test_custom_hint_property():
    """New hint properties should work in subclasses"""

    class CustomHints(has_schematic_hints):
        @_hint
        def custom_value(self) -> str:
            return "default"

    hints = CustomHints()
    assert hints.custom_value == "default"

    hints.custom_value = "modified"
    assert hints.custom_value == "modified"


@pytest.mark.parametrize(
    "first_hints,second_hints,expected",
    [
        # Test case 1: First hints more specific
        (
            {"lock_rotation_certainty": 0.8},
            {"symbol_rotation": 90},
            {"lock_rotation_certainty": 0.8, "symbol_rotation": 90},
        ),
        # Test case 2: Second hints more specific
        (
            {"symbol_rotation": 90},
            {"lock_rotation_certainty": 0.8},
            {"lock_rotation_certainty": 0.8, "symbol_rotation": 90},
        ),
        # Test case 3: Overlapping hints
        (
            {"lock_rotation_certainty": 0.8, "symbol_rotation": 90},
            {"lock_rotation_certainty": 0.7},
            {"lock_rotation_certainty": 0.7, "symbol_rotation": 90},
        ),
    ],
)
def test_handle_duplicate_merging(first_hints, second_hints, expected):
    """Hints should merge correctly when handling duplicates"""
    node = Node()
    hints1 = has_schematic_hints(**first_hints)
    hints2 = has_schematic_hints(**second_hints)

    node.add_trait(hints1)
    node.add_trait(hints2)

    remaining_hints = node.get_trait(has_schematic_hints)

    # Verify merged hint values
    for hint_name, expected_value in expected.items():
        assert getattr(remaining_hints, hint_name) == expected_value


def test_hint_inheritance():
    """Subclassed hints should inherit parent hints while allowing new ones"""

    class ExtendedHints(has_schematic_hints):
        @_hint
        def extra_hint(self) -> int:
            return 42

    hints = ExtendedHints(lock_rotation_certainty=0.9)

    # Test inherited hints
    assert hints.lock_rotation_certainty == 0.9
    assert hints.symbol_rotation is None

    # Test new hint
    assert hints.extra_hint == 42

    # Test hint modification
    hints.extra_hint = 100
    assert hints.extra_hint == 100


def test_hint_error_cases():
    """Test error cases for hint handling"""
    hints = has_schematic_hints()

    # Test setting non-existent hint
    with pytest.raises(AttributeError):
        _ = hints.nonexistent_hint
