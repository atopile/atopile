# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F
import faebryk.library.can_be_pulled as can_be_pulled


class ElectricSignal(fabll.Node):
    """
    ElectricSignal is a class that represents a signal that is represented
    by the voltage between the reference.hv and reference.lv.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    line = F.Electrical.MakeChild()
    reference = F.ElectricPower.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )
    _can_be_pulled = fabll.Traits.MakeEdge(
        can_be_pulled.can_be_pulled.MakeChild(line, reference)
    )

    @property
    def pull_resistance(self):
        """Delegate to the can_be_pulled trait to calculate pull resistance."""
        return self._can_be_pulled.get().pull_resistance

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
        import ElectricSignal, ElectricPower

        signal = new ElectricSignal

        # Connect power reference for signal levels
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%
        signal.reference ~ power_3v3

        # Connect between components
        sensor_output ~ signal.line
        adc_input ~ signal.line

        # For differential signals, use two ElectricSignals
        diff_pos = new ElectricSignal
        diff_neg = new ElectricSignal
        diff_pos.reference ~ power_3v3
        diff_neg.reference ~ power_3v3
        """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )
