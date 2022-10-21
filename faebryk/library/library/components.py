# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import List

from faebryk.library.trait_impl.component import (
    can_bridge_defined,
    has_defined_footprint,
    has_defined_type_description,
    has_symmetric_footprint_pinmap,
)
from faebryk.library.traits.component import (
    contructable_from_component,
    has_footprint_pinmap,
    has_type_description,
)
from faebryk.library.traits.interface import contructable_from_interface_list
from faebryk.libs.util import consume_iterator

logger = logging.getLogger("library")

from faebryk.library.core import Component, ComponentTrait, Parameter
from faebryk.library.library.interfaces import Electrical, Power
from faebryk.library.library.parameters import Constant
from faebryk.library.util import times, unit_map


class Resistor(Component):
    def _setup_traits(self):
        # class _contructable_from_component(contructable_from_component.impl()):
        #    @staticmethod
        #    def from_component(comp: Component, resistance: Parameter) -> Resistor:
        #        interfaces = comp.IFs.get_all()
        #        assert len(interfaces) == 2
        #        assert len([i for i in interfaces if type(i) is not Electrical]) == 0

        #        r = Resistor.__new__(Resistor)
        #        r.set_resistance(resistance)
        #        class _IFs(Component.InterfacesCls()):
        #            unnamed = interfaces

        #        r.IFs = _IFs(r)

        #        return r

        # self.add_trait(_contructable_from_component())
        pass

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)

        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self, resistance: Parameter):
        super().__init__()

        self._setup_interfaces()
        self.set_resistance(resistance)

    def set_resistance(self, resistance: Parameter):
        self.resistance = resistance

        if type(resistance) is not Constant:
            # TODO this is a bit ugly
            # it might be that there was another more abstract valid trait
            # but this challenges the whole trait overriding mechanism
            # might have to make a trait stack thats popped or so
            self.del_trait(has_type_description)
            return

        class _has_type_description(has_type_description.impl()):
            @staticmethod
            def get_type_description():
                assert isinstance(self.resistance, Constant)
                resistance: Constant = self.resistance
                return unit_map(
                    resistance.value, ["µΩ", "mΩ", "Ω", "KΩ", "MΩ", "GΩ"], start="Ω"
                )

        self.add_trait(_has_type_description())


class Capacitor(Component):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self, capacitance: Parameter):
        super().__init__()

        self._setup_interfaces()
        self.set_capacitance(capacitance)

    def _setup_traits(self):
        pass

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)
        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

    def set_capacitance(self, capacitance: Parameter):
        self.capacitance = capacitance

        if type(capacitance) is not Constant:
            return
        _capacitance: Constant = capacitance

        class _has_type_description(has_type_description.impl()):
            @staticmethod
            def get_type_description():
                capacitance = self.capacitance
                return unit_map(
                    _capacitance.value, ["µF", "mF", "F", "KF", "MF", "GF"], start="F"
                )

        self.add_trait(_has_type_description())


class BJT(Component):
    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("BJT"))

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            emitter = Electrical()
            base = Electrical()
            collector = Electrical()

        self.IFs = _IFs(self)


class MOSFET(Component):
    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("MOSFET"))

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            source = Electrical()
            gate = Electrical()
            drain = Electrical()

        self.IFs = _IFs(self)


class LED(Component):
    class has_calculatable_needed_series_resistance(ComponentTrait):
        @staticmethod
        def get_needed_series_resistance_ohm(input_voltage_V: float) -> Constant:
            raise NotImplemented

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("LED"))

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            anode = Electrical()
            cathode = Electrical()

        self.IFs = _IFs(self)

    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()

    def set_forward_parameters(self, voltage_V: Parameter, current_A: Parameter):
        if type(voltage_V) is Constant and type(current_A) is Constant:
            _voltage_V: Constant = voltage_V
            _current_A: Constant = current_A

            class _(self.has_calculatable_needed_series_resistance.impl()):
                @staticmethod
                def get_needed_series_resistance_ohm(
                    input_voltage_V: float,
                ) -> Constant:
                    return LED.needed_series_resistance_ohm(
                        input_voltage_V, _voltage_V.value, _current_A.value
                    )

            self.add_trait(_())

    @staticmethod
    def needed_series_resistance_ohm(
        input_voltage_V: float, forward_voltage_V: float, forward_current_A: float
    ) -> Constant:
        return Constant(int((input_voltage_V - forward_voltage_V) / forward_current_A))


class Potentiometer(Component):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        self._setup_traits()
        return self

    def __init__(self, resistance: Parameter) -> None:
        super().__init__()
        self._setup_interfaces(resistance)

    def _setup_traits(self):
        pass

    def _setup_interfaces(self, resistance):
        class _IFs(Component.InterfacesCls()):
            resistors = times(2, Electrical)
            wiper = Electrical()

        class _CMPs(Component.ComponentsCls()):
            resistors = [Resistor(resistance) for _ in range(2)]

        self.IFs = _IFs(self)
        self.CMPs = _CMPs(self)

        self.IFs.wiper.connect_all(
            [
                self.CMPs.resistors[0].IFs.unnamed[1],
                self.CMPs.resistors[1].IFs.unnamed[1],
            ]
        )

        for i, resistor in enumerate(self.CMPs.resistors):
            self.IFs.resistors[i].connect(resistor.IFs.unnamed[0])

    def connect_as_voltage_divider(self, high, low, out):
        self.IFs.resistors[0].connect(high)
        self.IFs.resistors[1].connect(low)
        self.IFs.wiper.connect(out)


class Switch(Component):
    def _setup_traits(self):
        self.add_trait(has_defined_type_description("SW"))

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)
        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()


class PJ398SM(Component):
    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("Connector"))

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            tip = Electrical()
            sleeve = Electrical()
            switch = Electrical()

        self.IFs = _IFs(self)


class NAND(Component):
    def _setup_traits(self):
        class _constructable_from_component(contructable_from_component.impl()):
            @staticmethod
            def from_comp(comp: Component) -> NAND:
                n = NAND.__new__(NAND)
                n.__init_from_comp(comp)
                return n

        self.add_trait(_constructable_from_component())

    def _setup_interfaces(self, input_cnt):
        class _IFs(Component.InterfacesCls()):
            power = Power()
            output = Electrical()
            inputs = times(input_cnt, Electrical)

        self.IFs = _IFs(self)

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)

        self._setup_traits()

        return self

    def __init__(self, input_cnt: int):
        super().__init__()

        self._setup_interfaces(input_cnt)

    def __init_from_comp(self, comp: Component):
        interfaces = comp.IFs.get_all()
        assert all(map(lambda i: type(i) is Electrical, interfaces))

        it = iter(interfaces)

        self.IFs.power = (
            Power().get_trait(contructable_from_interface_list).from_interfaces(it)
        )
        self.IFs.output = (
            Electrical().get_trait(contructable_from_interface_list).from_interfaces(it)
        )
        self.IFs.inputs = list(
            consume_iterator(
                Electrical()
                .get_trait(contructable_from_interface_list)
                .from_interfaces,
                it,
            )
        )


class CD4011(Component):
    class constructable_from_nands(ComponentTrait):
        def from_nands(self, nands: List[NAND]):
            raise NotImplementedError

    def _setup_traits(self):
        class _constructable_from_component(contructable_from_component.impl()):
            @staticmethod
            def from_comp(comp: Component) -> CD4011:
                c = CD4011.__new__(CD4011)
                c._init_from_comp(comp)
                return c

        class _constructable_from_nands(self.constructable_from_nands.impl()):
            @staticmethod
            def from_nands(nands: list[NAND]) -> CD4011:
                c = CD4011.__new__(CD4011)
                c._init_from_nands(nands)
                return c

        self.add_trait(_constructable_from_component())
        self.add_trait(_constructable_from_nands())
        self.add_trait(has_defined_type_description("cd4011"))

    def _setup_nands(self):
        class _CMPs(Component.ComponentsCls()):
            nands = times(4, lambda: NAND(input_cnt=2))

        self.CMPs = _CMPs(self)

        for n in self.CMPs.nands:
            n.add_trait(has_symmetric_footprint_pinmap())

    def _setup_interfaces(self):
        nand_inout_interfaces = [
            i for n in self.CMPs.nands for i in [n.IFs.output, *n.IFs.inputs]
        ]

        class _IFs(Component.InterfacesCls()):
            power = Power()
            in_outs = times(len(nand_inout_interfaces), Electrical)

        self.IFs = _IFs(self)

    def _setup_internal_connections(self):
        self.connection_map = {}

        it = iter(self.IFs.in_outs)
        for n in self.CMPs.nands:
            n.IFs.power.connect(self.IFs.power)
            target = next(it)
            target.connect(n.IFs.output)
            self.connection_map[n.IFs.output] = target

            for i in n.IFs.inputs:
                target = next(it)
                target.connect(i)
                self.connection_map[i] = target

        # TODO
        # assert(len(self.interfaces) == 14)

    def __new__(cls):
        self = super().__new__(cls)

        CD4011._setup_traits(self)
        return self

    def __init__(self):
        super().__init__()

        # setup
        self._setup_nands()
        self._setup_interfaces()
        self._setup_internal_connections()

    def _init_from_comp(self, comp: Component):
        super().__init__()

        # checks
        interfaces = comp.IFs.get_all()
        assert len(interfaces) == len(self.IFs.get_all())
        assert len([i for i in interfaces if type(i) is not Electrical]) == 0

        it = iter(interfaces)

        # setup
        self.IFs.power = (
            Power().get_trait(contructable_from_interface_list).from_interfaces(it)
        )
        self._setup_nands()
        self.IFs.in_outs = list(
            consume_iterator(
                Electrical()
                .get_trait(contructable_from_interface_list)
                .from_interfaces,
                it,
            )
        )
        self._setup_internal_connections()

    def _init_from_nands(self, nands: list[NAND]):
        super().__init__()

        # checks
        assert len(nands) <= 4
        cd_nands = list(nands)
        cd_nands += times(4 - len(cd_nands), lambda: NAND(input_cnt=2))

        for nand in cd_nands:
            assert len(nand.IFs.inputs) == 2

        # setup
        self.CMPs.nands = cd_nands
        self._setup_interfaces()
        self._setup_internal_connections()


class TI_CD4011BE(CD4011):
    def __init__(self):
        super().__init__()

    def __new__(cls):
        self = super().__new__(cls)

        TI_CD4011BE._setup_traits(self)
        return self

    def _setup_traits(self):
        from faebryk.library.library.footprints import DIP

        self.add_trait(
            has_defined_footprint(DIP(pin_cnt=14, spacing_mm=7.62, long_pads=False))
        )

        class _has_footprint_pinmap(has_footprint_pinmap.impl()):
            def get_pin_map(self):
                component = self.get_obj()
                return {
                    7: component.IFs.power.IFs.lv,
                    14: component.IFs.power.IFs.hv,
                    3: component.connection_map[component.CMPs.nands[0].IFs.output],
                    4: component.connection_map[component.CMPs.nands[1].IFs.output],
                    11: component.connection_map[component.CMPs.nands[2].IFs.output],
                    10: component.connection_map[component.CMPs.nands[3].IFs.output],
                    1: component.connection_map[component.CMPs.nands[0].IFs.inputs[0]],
                    2: component.connection_map[component.CMPs.nands[0].IFs.inputs[1]],
                    5: component.connection_map[component.CMPs.nands[1].IFs.inputs[0]],
                    6: component.connection_map[component.CMPs.nands[1].IFs.inputs[1]],
                    12: component.connection_map[component.CMPs.nands[2].IFs.inputs[0]],
                    13: component.connection_map[component.CMPs.nands[2].IFs.inputs[1]],
                    9: component.connection_map[component.CMPs.nands[3].IFs.inputs[0]],
                    8: component.connection_map[component.CMPs.nands[3].IFs.inputs[1]],
                }

        self.add_trait(_has_footprint_pinmap())
