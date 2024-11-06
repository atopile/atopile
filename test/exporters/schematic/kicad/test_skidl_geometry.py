import pytest

from faebryk.exporters.schematic.kicad.skidl.geometry import Point, Tx


@pytest.mark.parametrize(
    "tx, expected",
    [
        (Tx.ROT_CCW_90, (False, 90)),
        (Tx.FLIP_X * Tx.ROT_CCW_90, (True, 90)),
        (Tx.ROT_CW_90, (False, 270)),
        (Tx.FLIP_X * Tx.ROT_CW_90, (True, 270)),
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


@pytest.mark.parametrize(
    "tx, expected",
    [
        (Tx(), (1, 0)),
        (Tx.ROT_CCW_90, (0, 1)),
        (Tx.FLIP_X, (-1, 0)),
        (Tx.FLIP_X * Tx.ROT_CCW_90, (0, -1)),
        (Tx.FLIP_Y, (1, 0)),
        (Tx.ROT_CCW_90 * Tx.FLIP_Y, (0, -1)),
        (Tx.ROT_CW_90 * Tx.FLIP_Y, (0, 1)),
        (Tx.ROT_CW_180, (-1, 0)),
        (Tx.ROT_CW_270, (0, 1)),
    ],
)
def test_find_orientation_from_tx(tx: Tx, expected: tuple[float, float]):
    txd = Point(1, 0) * tx
    assert txd == Point(expected[0], expected[1])
