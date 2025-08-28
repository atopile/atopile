from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import times


class Layer(Module):
    material = L.p_field(units=P.dimensionless)  # TODO: Needs to be enum
    thickness = L.p_field(units=P.um)
    # Dielectric properties (optional, primarily for non-copper layers)
    epsilon_r = L.p_field(units=P.dimensionless)
    loss_tangent = L.p_field(units=P.dimensionless)


class Stackup(Module):
    def __init__(self, layer_count: int):
        self._layer_count = layer_count
        super().__init__()

    @L.rt_field
    def layers(self):
        return times(self._layer_count, Layer)
