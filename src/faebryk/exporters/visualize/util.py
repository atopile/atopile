import colorsys
from typing import Iterable, Sequence, Set


def generate_pastel_palette(num_colors: int) -> list[str]:
    """
    Generate a well-spaced pastel color palette.

    Args:
    num_colors (int): The number of colors to generate.

    Returns:
    List[str]: A list of hex color codes.
    """
    palette: list[str] = []
    hue_step: float = 1.0 / num_colors

    for i in range(num_colors):
        hue: float = i * hue_step
        # Use fixed saturation and value for pastel colors
        saturation: float = 0.4  # Lower saturation for softer colors
        value: float = 0.95  # High value for brightness

        # Convert HSV to RGB
        rgb: tuple[float, float, float] = colorsys.hsv_to_rgb(hue, saturation, value)

        # Convert RGB to hex
        hex_color: str = "#{:02x}{:02x}{:02x}".format(
            int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)
        )

        palette.append(hex_color)

    return palette


# TODO: this belongs elsewhere
class IDSet[T](Set[T]):
    def __init__(self, data: Sequence[T] | None = None):
        self._data = set(data) if data is not None else set()

    def add(self, item: T):
        self._data.add(id(item))

    def __contains__(self, item: T):
        return id(item) in self._data

    def __iter__(self) -> Iterable[T]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)
