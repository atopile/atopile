import pytest

from faebryk.exporters.schematic.kicad.skidl.geometry import Tx


@pytest.mark.parametrize(
    "tx, expected",
    [
        (Tx.ROT_CCW_90, (90, False)),
        (Tx.FLIP_X * Tx.ROT_CCW_90, (90, True)),
        (Tx.ROT_CW_90, (270, False)),
        (Tx.FLIP_X * Tx.ROT_CW_90, (270, True)),
    ],
)
def test_find_orientation(tx: Tx, expected: tuple[float, bool]):
    assert tx.find_orientation() == expected


@pytest.mark.parametrize(
    "degs, expected",
    [
        (0, Tx()),
        (90, Tx.ROT_CW_90),
        (180, Tx.ROT_CW_180),
        (270, Tx.ROT_CW_270),
    ],
)
def test_rot_cw(degs: float, expected: Tx):
    tx = Tx()
    assert tx.rot_cw(degs) == expected
