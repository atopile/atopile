# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class BH1750FVI_TR(Module):
    class _bh1750_esphome_config(F.has_esphome_config.impl()):
        update_interval: F.TBD

        def get_config(self) -> dict:
            val = self.update_interval.get_most_narrow()
            assert isinstance(val, F.Constant), "No update interval set!"

            obj = self.obj
            assert isinstance(obj, BH1750FVI_TR)

            i2c = F.is_esphome_bus.find_connected_bus(obj.i2c)

            return {
                "sensor": [
                    {
                        "platform": "bh1750",
                        "name": "BH1750 Illuminance",
                        "address": "0x23",
                        "i2c_id": i2c.get_trait(F.is_esphome_bus).get_bus_id(),
                        "update_interval": f"{val.value.to('s')}",
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
        self.dvi_capacitor.capacitance.merge(1 * P.uF)
        self.dvi_resistor.resistance.merge(1 * P.kohm)

        self.i2c.terminate()

        self.i2c.frequency.merge(
            F.I2C.define_max_frequency_capability(F.I2C.SpeedMode.fast_speed)
        )

        # set constraints
        self.power.voltage.merge(F.Range(2.4 * P.V, 3.6 * P.V))

        self.power.decoupled.decouple().capacitance.merge(100 * P.nF)
        # TODO: self.dvi.low_pass(self.dvi_capacitor, self.dvi_resistor)
        self.dvi.signal.connect_via(self.dvi_capacitor, self.power.lv)
        self.dvi.signal.connect_via(self.dvi_resistor, self.power.hv)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.power.hv,
                "2": self.addr.signal,
                "3": self.power.lv,
                "4": self.i2c.sda.signal,
                "5": self.dvi.signal,
                "6": self.i2c.scl.signal,
                "7": self.ep.signal,
            }
        )

    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://datasheet.lcsc.com/lcsc/1811081611_ROHM-Semicon-BH1750FVI-TR_C78960.pdf"
    )
