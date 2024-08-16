# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass, field

from faebryk.core.core import Module, Parameter
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.Capacitor import Capacitor
from faebryk.library.Constant import Constant
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import (
    has_designator_prefix_defined,
)
from faebryk.library.has_esphome_config import has_esphome_config
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.I2C import I2C
from faebryk.library.is_esphome_bus import is_esphome_bus
from faebryk.library.Range import Range
from faebryk.library.Resistor import Resistor
from faebryk.library.TBD import TBD
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class BH1750FVI_TR(Module):
    @dataclass
    class _bh1750_esphome_config(has_esphome_config.impl()):
        update_interval_s: Parameter = field(default_factory=TBD)

        def __post_init__(self) -> None:
            super().__init__()

        def get_config(self) -> dict:
            assert isinstance(
                self.update_interval_s, Constant
            ), "No update interval set!"

            obj = self.get_obj()
            assert isinstance(obj, BH1750FVI_TR)

            i2c = is_esphome_bus.find_connected_bus(obj.IFs.i2c)

            return {
                "sensor": [
                    {
                        "platform": "bh1750",
                        "name": "BH1750 Illuminance",
                        "address": "0x23",
                        "i2c_id": i2c.get_trait(is_esphome_bus).get_bus_id(),
                        "update_interval": f"{self.update_interval_s.value}s",
                    }
                ]
            }

    def set_address(self, addr: int):
        raise NotImplementedError()
        # ADDR = ‘H’ ( ADDR ≧ 0.7VCC ) “1011100“
        # ADDR = 'L' ( ADDR ≦ 0.3VCC ) “0100011“
        ...
        # assert addr < (1 << len(self.IFs.e))

        # for i, e in enumerate(self.IFs.e):
        #    e.set(addr & (1 << i) != 0)

    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()):
            dvi_capacitor = Capacitor()
            dvi_resistor = Resistor()

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            power = ElectricPower()
            addr = ElectricLogic()
            dvi = ElectricLogic()
            ep = ElectricLogic()
            i2c = I2C()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        self.NODEs.dvi_capacitor.PARAMs.capacitance.merge(1 * P.uF)
        self.NODEs.dvi_resistor.PARAMs.resistance.merge(1 * P.kohm)

        self.IFs.i2c.terminate()

        self.IFs.i2c.PARAMs.frequency.merge(
            I2C.define_max_frequency_capability(I2C.SpeedMode.fast_speed)
        )

        self.add_trait(has_designator_prefix_defined("U"))

        self.add_trait(
            can_attach_to_footprint_via_pinmap(
                {
                    "1": self.IFs.power.IFs.hv,
                    "2": self.IFs.addr.IFs.signal,
                    "3": self.IFs.power.IFs.lv,
                    "4": self.IFs.i2c.IFs.sda.IFs.signal,
                    "5": self.IFs.dvi.IFs.signal,
                    "6": self.IFs.i2c.IFs.scl.IFs.signal,
                    "7": self.IFs.ep.IFs.signal,
                }
            )
        )

        self.add_trait(
            has_datasheet_defined(
                "https://datasheet.lcsc.com/lcsc/1811081611_ROHM-Semicon-BH1750FVI-TR_C78960.pdf"
            )
        )

        # set constraints
        self.IFs.power.PARAMs.voltage.merge(Range(2.4 * P.V, 3.6 * P.V))

        # internal connections
        ref = ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))
        ref.connect(self.IFs.power)

        self.IFs.power.get_trait(can_be_decoupled).decouple().PARAMs.capacitance.merge(
            0.1 * P.uF
        )
        # TODO: self.IFs.dvi.low_pass(self.IF.dvi_capacitor, self.IF.dvi_resistor)

        # self.IFs.i2c.add_trait(is_esphome_bus.impl()())
        self.esphome = self._bh1750_esphome_config()
        self.add_trait(self.esphome)
