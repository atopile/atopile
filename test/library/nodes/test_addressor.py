# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.library import L


class ConfigurableI2CClient(Module):
    addressor = L.f_field(F.Addressor)(address_bits=3)
    i2c: F.I2C
    config = L.list_field(3, F.ElectricLogic)
    ref: F.ElectricPower

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __preinit__(self) -> None:
        self.addressor.address.alias_is(self.i2c.address)
        self.addressor.base.alias_is(16)
        for a, b in zip(self.addressor.address_lines, self.config):
            a.connect(b)


def test_addressor():
    app = ConfigurableI2CClient()

    # app.addressor.offset.alias_is(3)
    app.i2c.address.alias_is(16 + 3)

    solver = DefaultSolver()
    solver.simplify(app)

    assert solver.inspect_get_known_supersets(app.i2c.address) == 16 + 3

    assert app.config[0].line.is_connected_to(app.ref.hv)
    assert app.config[1].line.is_connected_to(app.ref.hv)
    assert app.config[2].line.is_connected_to(app.ref.lv)
