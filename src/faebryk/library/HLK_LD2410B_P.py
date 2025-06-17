# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class HLK_LD2410B_P(Module):
    class _ld2410b_esphome_config(F.has_esphome_config.impl()):
        throttle = L.p_field(
            units=P.ms,
            soft_set=L.Range(10 * P.ms, 1000 * P.ms),
            tolerance_guess=0,
        )

        def get_config(self) -> dict:
            obj = self.obj
            assert isinstance(obj, HLK_LD2410B_P)

            uart_candidates = {
                mif
                for mif in obj.uart.get_connected()
                if mif.has_trait(F.is_esphome_bus)
                and mif.has_trait(F.has_esphome_config)
            }

            assert len(uart_candidates) == 1, f"Expected 1 UART, got {uart_candidates}"
            uart = uart_candidates.pop()
            uart_cfg = uart.get_trait(F.has_esphome_config).get_config()["uart"][0]
            assert (
                uart_cfg["baud_rate"] == 256000
            ), f"Baudrate not 256000 but {uart_cfg['baud_rate']}"

            return {
                "ld2410": {
                    "throttle": self.throttle,
                    "uart_id": uart_cfg["id"],
                },
                "binary_sensor": [
                    {
                        "platform": "ld2410",
                        "has_target": {
                            "name": "Presence",
                        },
                        "has_moving_target": {
                            "name": "Moving Target",
                        },
                        "has_still_target": {
                            "name": "Still Target",
                        },
                        "out_pin_presence_status": {
                            "name": "Out pin presence status",
                        },
                    },
                ],
            }

    # interfaces
    power: F.ElectricPower
    uart: F.UART_Base
    out: F.ElectricLogic

    esphome_config: _ld2410b_esphome_config

    @L.rt_field
    def attach_to_footprint(self):
        x = self
        return F.can_attach_to_footprint_via_pinmap(
            {
                "5": x.power.hv,
                "4": x.power.lv,
                "3": x.uart.rx.line,
                "2": x.uart.tx.line,
                "1": x.out.line,
            }
        )

    def __preinit__(self):
        self.uart.baud.constrain_le(256 * P.kbaud)

    # connect all logic references
    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    explicit_part = L.f_field(F.has_explicit_part.by_supplier)("C5183132")
