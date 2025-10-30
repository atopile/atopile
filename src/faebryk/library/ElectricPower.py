# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
from faebryk.library.Electrical import Electrical
from faebryk.library.has_usage_example import has_usage_example


class ElectricPower(fabll.Node):
    """
    ElectricPower is a class that represents a power rail. Power rails have a
    higher potential (hv), and lower potential (lv) Electrical.
    """

    @classmethod
    def MakeChild(cls):
        out = fabll.ChildField(cls)
        return out

    # class can_be_decoupled_power(F.can_be_decoupled.impl()):
    #     def decouple(
    #         self,
    #         owner: fabll.Node,
    #         count: int = 1,
    #     ):
    #         obj = self.get_obj(ElectricPower)

    #         capacitor = F.MultiCapacitor(count)

    #         # FIXME seems to cause contradictions
    #         capacitor.max_voltage.constrain_ge(obj.voltage * 1.5)

    #         obj.hv.connect_via(capacitor, obj.lv)

    #         name = f"decoupling_{obj.get_name(accept_no_parent=True)}"
    #         new_capacitor = capacitor
    #         # Merge
    #         if obj.has_trait(F.is_decoupled):
    #             old_capacitor = obj.get_trait(F.is_decoupled).capacitor
    #             capacitor = F.MultiCapacitor.from_capacitors(
    #                 old_capacitor,
    #                 new_capacitor,
    #             )
    #             name = old_capacitor.get_name(accept_no_parent=True) + "'"

    #         # TODO improve
    #         if name in owner.runtime:
    #             name += "_"
    #         owner.add(capacitor, name=name)
    #         obj.add(F.is_decoupled(capacitor))

    #         return new_capacitor

    # class can_be_surge_protected_power(F.can_be_surge_protected.impl()):
    #     def protect(self, owner: fabll.Node):
    #         obj = self.get_obj(ElectricPower)
    #         surge_protection = F.SurgeProtection.from_interfaces(obj.lv, obj.hv)
    #         owner.add(
    #             surge_protection,
    #             name=f"surge_protection_{obj.get_name(accept_no_parent=True)}",
    #         )
    #         obj.add(F.is_surge_protected_defined(surge_protection))
    #         return surge_protection

    hv = Electrical.MakeChild()
    lv = Electrical.MakeChild()

    voltage = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Volt,
    )
    max_current = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Ampere,
    )

    # _has_single_electric_reference = F.has_single_electric_reference_defined.MakeChild()

    bus_max_current_consumption_sum = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Ampere,
    )

    # _surge_protected: can_be_surge_protected_power
    # _decoupled: can_be_decoupled_power

    # def fused(self, attach_to: fabll.Node | None = None):
    #     fused_power = type(self)()
    #     fuse = fused_power.add(F.Fuse())

    #     fused_power.hv.connect_via(fuse, self.hv)
    #     fused_power.lv.connect(self.lv)

    #     self.connect_shallow(fused_power)

    #     fuse.trip_current.constrain_subset(
    #         self.max_current * fabll.Range.from_center_rel(1.0, 0.1)
    #     )
    #     # TODO maybe better bus_consumption
    #     fused_power.max_current.constrain_le(fuse.trip_current)

    #     if attach_to is not None:
    #         attach_to.add(fused_power)

    #     return fused_power

    # def __preinit__(self) -> None:
    #     ...
    #     # self.voltage.alias_is(
    #     #    self.hv.potential - self.lv.potential
    #     # )
    #     self.voltage.add(F.is_bus_parameter())
    #     self.bus_max_current_consumption_sum.add(
    #         F.is_bus_parameter(reduce=(self.max_current, Add))
    #     )

    #     self.lv.add(F.has_net_name("gnd"))

    # @property
    # def vcc(self) -> F.Electrical:
    #     """Higher-voltage side of the power interface."""
    #     return self.hv

    # @property
    # def gnd(self) -> F.Electrical:
    #     """Lower-voltage side of the power interface."""
    #     return self.lv

    # def __postinit__(self, *args, **kwargs):
    #     super().__postinit__(*args, **kwargs)
    #     # Apply suffixes to the electrical lines of the signals
    #     self.hv.add(F.has_net_name("VCC", level=F.has_net_name.Level.SUGGESTED))
    #     self.lv.add(F.has_net_name("GND", level=F.has_net_name.Level.SUGGESTED))

    usage_example = has_usage_example.MakeChild(
        example="""
        import ElectricPower

        power_5v = new ElectricPower
        assert power_5v.voltage within 5V +/- 5%
        assert power_5v.max_current <= 1A

        # Connect 2 ElectricPowers together
        power_5v ~ ic.power_input

        # Connect an example bypass capacitor
        power_5v.hv ~> example_capacitor ~> power_5v.lv
        """,
        language=has_usage_example.Language.ato,
    )
