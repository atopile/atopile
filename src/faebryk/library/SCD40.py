# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class SCD40(Module):
    """
    Sensirion SCD4x NIR CO2 sensor
    """

    class _scd4x_esphome_config(F.has_esphome_config.impl()):
        update_interval = L.p_field(units=P.s, tolerance_guess=0)

        def get_config(self) -> dict:
            obj = self.get_obj(SCD40)

            i2c = F.is_esphome_bus.find_connected_bus(obj.i2c)

            return {
                "sensor": [
                    {
                        "platform": "scd4x",
                        "co2": {
                            "name": "CO2",
                        },
                        "temperature": {
                            "name": "Moving Temperature",
                        },
                        "humidity": {
                            "name": "Humidity",
                        },
                        "address": 0x62,
                        "i2c_id": i2c.get_trait(F.is_esphome_bus).get_bus_id(),
                        "update_interval": self.update_interval,
                    }
                ]
            }

    esphome_config: _scd4x_esphome_config

    # interfaces
    power: F.ElectricPower
    i2c: F.I2C

    @L.rt_field
    def attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "6": self.power.lv,
                "20": self.power.lv,
                "21": self.power.lv,
                "7": self.power.hv,
                "19": self.power.hv,
                "9": self.i2c.scl.line,
                "10": self.i2c.sda.line,
            }
        )

    explicit_part = L.f_field(F.has_explicit_part.by_supplier)("C3037696")

    def __preinit__(self):
        self.power.voltage.constrain_subset(L.Range.from_center_rel(3.3 * P.V, 0.05))
        # FIXME
        # self.i2c.terminate()
        # self.power.decoupled.decouple()
        self.i2c.frequency.constrain_le(
            F.I2C.define_max_frequency_capability(F.I2C.SpeedMode.fast_speed)
        )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://sensirion.com/media/documents/48C4B7FB/64C134E7/Sensirion_SCD4x_Datasheet.pdf"
    )
