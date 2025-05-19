# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.app.checks import check_design
from faebryk.libs.exceptions import UserDesignCheckException
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


class I2CBusTopology(Module):
    server: F.I2C
    clients = L.list_field(3, ConfigurableI2CClient)

    def __init__(self, isolated=False):
        super().__init__()
        self._isolated = isolated

    def __preinit__(self) -> None:
        # self.server.address.alias_is(0)
        if not self._isolated:
            self.server.connect(*[c.i2c for c in self.clients])
            self.server.terminate(self)
        else:
            self.server.connect_shallow(*[c.i2c for c in self.clients])
            # for c in [self.server] + [c.i2c for c in self.clients]:
            #    c.terminate(self)


def test_i2c_unique_addresses():
    app = I2CBusTopology()
    app.clients[0].addressor.offset.alias_is(1)
    app.clients[1].addressor.offset.alias_is(2)
    app.clients[2].addressor.offset.alias_is(3)

    solver = DefaultSolver()
    solver.simplify(app)
    app.add(F.has_solver(solver))

    check_design(app.get_graph(), stage=F.implements_design_check.CheckStage.POST_SOLVE)


def test_i2c_duplicate_addresses():
    app = I2CBusTopology()
    app.clients[0].addressor.offset.alias_is(1)
    app.clients[1].addressor.offset.alias_is(3)
    app.clients[2].addressor.offset.alias_is(3)

    solver = DefaultSolver()
    solver.simplify(app)
    app.add(F.has_solver(solver))

    # with pytest.raises(F.I2C.requires_unique_addresses.DuplicateAddressException):
    with pytest.raises(ExceptionGroup) as e:
        check_design(
            app.get_graph(), stage=F.implements_design_check.CheckStage.POST_SOLVE
        )
    assert e.group_contains(
        UserDesignCheckException, match="Duplicate I2C addresses found on the bus:"
    )


def test_i2c_duplicate_addresses_isolated():
    app = I2CBusTopology(isolated=True)
    app.clients[0].addressor.offset.alias_is(1)
    app.clients[1].addressor.offset.alias_is(3)
    app.clients[2].addressor.offset.alias_is(3)

    solver = DefaultSolver()
    solver.simplify(app)
    app.add(F.has_solver(solver))

    # with pytest.raises(F.I2C.requires_unique_addresses.DuplicateAddressException):
    with pytest.raises(ExceptionGroup) as e:
        check_design(
            app.get_graph(), stage=F.implements_design_check.CheckStage.POST_SOLVE
        )
    assert e.group_contains(
        UserDesignCheckException, match="Duplicate I2C addresses found on the bus:"
    )
