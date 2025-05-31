# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class _BH1750FVI_TR(Module):
    class _bh1750_esphome_config(F.has_esphome_config.impl()):
        update_interval = L.p_field(
            units=P.s,
            soft_set=L.Range(100 * P.ms, 1 * P.day),
            guess=1 * P.s,
            tolerance_guess=0,
        )

        def get_config(self) -> dict:
            obj = self.obj
            assert isinstance(obj, _BH1750FVI_TR)

            i2c = F.is_esphome_bus.find_connected_bus(obj.i2c)

            return {
                "sensor": [
                    {
                        "platform": "bh1750",
                        "name": "BH1750 Illuminance",
                        "address": "0x23",
                        "i2c_id": i2c.get_trait(F.is_esphome_bus).get_bus_id(),
                        "update_interval": self.update_interval,
                    }
                ]
            }

    dvi_capacitor: F.Capacitor
    dvi_resistor: F.Resistor

    power: F.ElectricPower
    addr: F.ElectricLogic
    dvi: F.ElectricLogic
    ep: F.ElectricLogic
    i2c: F.I2C

    def set_address(self, addr: int):
        raise NotImplementedError()
        # TODO: Implement set_address
        # ADDR = ‘H’ ( ADDR ≧ 0.7VCC ) “1011100“
        # ADDR = 'L' ( ADDR ≦ 0.3VCC ) “0100011“
        ...
        # assert addr < (1 << len(self.e))

        # for i, e in enumerate(self.e):
        #    e.set(addr & (1 << i) != 0)

    esphome_config: _bh1750_esphome_config

    def __preinit__(self):
        self.dvi_capacitor.capacitance.constrain_subset(
            L.Range.from_center_rel(1 * P.uF, 0.1)
        )
        self.dvi_resistor.resistance.constrain_subset(
            L.Range.from_center_rel(1 * P.kohm, 0.1)
        )

        self.i2c.frequency.constrain_le(
            F.I2C.define_max_frequency_capability(F.I2C.SpeedMode.fast_speed)
        )

        # set constraints
        self.power.voltage.constrain_subset(L.Range(2.4 * P.V, 3.6 * P.V))

        # TODO: self.dvi.low_pass(self.dvi_capacitor, self.dvi_resistor)
        self.dvi.line.connect_via(self.dvi_capacitor, self.power.lv)
        self.dvi.line.connect_via(self.dvi_resistor, self.power.hv)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.power.hv,
                "2": self.addr.line,
                "3": self.power.lv,
                "4": self.i2c.sda.line,
                "5": self.dvi.line,
                "6": self.i2c.scl.line,
                "7": self.ep.line,
            }
        )

    explicit_part = L.f_field(F.has_explicit_part.by_supplier)("C78960")


# TODO should be a reference design
class BH1750FVI_TR(Module):
    ic: _BH1750FVI_TR

    def __preinit__(self):
        self.ic.i2c.terminate(self)

        self.ic.power.decoupled.decouple(owner=self).capacitance.constrain_subset(
            L.Range.from_center_rel(100 * P.nF, 0.1)
        )
