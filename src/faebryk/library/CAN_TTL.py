# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class CAN_TTL(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    rx = F.ElectricLogic.MakeChild()
    tx = F.ElectricLogic.MakeChild()

    baudrate = F.Parameters.NumericParameter.MakeChild(unit=F.Units.BitsPerSecond)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    bus_spec = fabll.Traits.MakeEdge(
        F.DataBus.has_specification.MakeChild(
            topology=[F.DataBus.has_specification.Topology.POINT_TO_POINT],
            data_flow=F.DataBus.has_specification.DataFlow.HALF_DUPLEX,
            multi_controller=False,
        )
    )

    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    bus_parameters = [
        fabll.Traits.MakeEdge(F.is_alias_bus_parameter.MakeChild(), owner=[baudrate]),
    ]
