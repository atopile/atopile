# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.core.core import Module
from faebryk.core.util import (
    as_unit,
    as_unit_with_tolerance,
)
from faebryk.library.can_attach_to_footprint_symmetrically import (
    can_attach_to_footprint_symmetrically,
)
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_simple_value_representation_based_on_params import (
    has_simple_value_representation_based_on_params,
)
from faebryk.library.TBD import TBD
from faebryk.libs.util import times


class Inductor(Module):
    def __init__(
        self,
    ):
        super().__init__()

        class _IFs(super().IFS()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)
        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

        class _PARAMs(super().PARAMS()):
            inductance = TBD[float]()
            self_resonant_frequency = TBD[float]()
            rated_current = TBD[float]()
            dc_resistance = TBD[float]()

        self.PARAMs = _PARAMs(self)

        self.add_trait(can_attach_to_footprint_symmetrically())
        self.add_trait(
            has_simple_value_representation_based_on_params(
                (
                    self.PARAMs.inductance,
                    self.PARAMs.self_resonant_frequency,
                    self.PARAMs.rated_current,
                    self.PARAMs.dc_resistance,
                ),
                lambda ps: " ".join(
                    filter(
                        None,
                        [
                            as_unit_with_tolerance(ps[0], "H"),
                            as_unit(ps[1], "Hz"),
                            as_unit(ps[2], "A"),
                            as_unit(ps[3], "Ω"),
                        ],
                    )
                ),
            )
        )
        self.add_trait(has_designator_prefix_defined("L"))
