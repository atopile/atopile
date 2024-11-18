import pytest

from faebryk.libs.geometry.basic import Geometry


@pytest.mark.parametrize(
    "structure, axis, angle, expected",
    [
        # around origin
        ((1, 0), (0, 0), 90, (0, 1)),
        ((1, 2), (0, 0), 90, (-2, 1)),
        ((1, 2), (0, 0), 180, (-1, -2)),
        # around point
        ((0, 0), (1, 0), 180, (2, 0)),
        ((4, 0), (3, 0), 180, (2, 0)),
    ],
)
def test_rotate(structure, axis, angle, expected):
    rotated = Geometry.rotate(axis, [structure], angle)
    # rotated = tuple(map(float, rotated[0]))
    assert rotated[0] == pytest.approx(expected, abs=1e-6)
