import pytest

from faebryk.exporters.schematic.kicad.skidl.shims import Part, Pin


@pytest.fixture
def part() -> Part:

    part = Part()

    part.pins = [Pin() for _ in range(4)]
    part.pins[0].orientation = "U"
    part.pins[1].orientation = "D"
    part.pins[2].orientation = "L"
    part.pins[3].orientation = "R"

    part.pins_by_orientation = {
        "U": part.pins[0],
        "D": part.pins[1],
        "L": part.pins[2],
        "R": part.pins[3],
    }

    return part


@pytest.mark.parametrize(
    "pwr_pins, gnd_pins, expected, certainty",
    [
        (["U"], ["D"], 180, 1.0),
        (["L"], ["R"], 90, 1.0),
        (["R"], ["L"], 270, 1.0),
        ([], [], 0, 0),
    ],
)
def test_ideal_part_rotation(part, pwr_pins, gnd_pins, expected, certainty):
    from faebryk.exporters.schematic.kicad.skidl.gen_schematic import (
        _ideal_part_rotation,
    )

    assert isinstance(part, Part)
    for orientation, pin in part.pins_by_orientation.items():
        assert isinstance(pin, Pin)
        if orientation in pwr_pins:
            pin.fab_is_pwr = True
            pin.fab_is_gnd = False
        elif orientation in gnd_pins:
            pin.fab_is_gnd = True
            pin.fab_is_pwr = False
        else:
            pin.fab_is_pwr = False
            pin.fab_is_gnd = False

    assert _ideal_part_rotation(part) == (expected, certainty)
