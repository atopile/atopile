# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.app.checks import check_design
from faebryk.libs.exceptions import UserDesignCheckException


class ConfigurableI2CClient(fabll.Node):
    addressor = F.Addressor.MakeChild(address_bits=3)
    i2c = F.I2C.MakeChild()
    config = [F.ElectricLogic.MakeChild() for _ in range(3)]
    ref = F.ElectricPower.MakeChild()

    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    def setup(self, g, tg) -> None:
        self.addressor.get().address.get().alias_to_literal(g, self.i2c.get().address.get())
        self.addressor.get().base.get().alias_to_literal(g, F.Literals.Numbers.bind_typegraph(tg).create_instance(g).setup_from_singleton(value=16))

        for a, b in zip(self.addressor.get().address_lines, self.config):
            a.get_trait(fabll.is_interface).connect_to(b.get())


def test_addressor():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    app = ConfigurableI2CClient.bind_typegraph(tg).create_instance(g=g)
    app.setup(g, tg)

    # app.addressor.offset.alias_is(3)
    app.i2c.get().address.get().alias_to_literal(g, F.Literals.Numbers.bind_typegraph(tg).create_instance(g).setup_from_singleton(value=16 + 3))

    solver = DefaultSolver()
    solver.simplify(g, tg)

    assert solver.inspect_get_known_supersets(app.i2c.address) == 16 + 3

    assert app.config[0].line.is_connected_to(app.ref.hv)
    assert app.config[1].line.is_connected_to(app.ref.hv)
    assert app.config[2].line.is_connected_to(app.ref.lv)


class I2CBusTopology(fabll.Node):
    server: F.I2C
    clients = [ConfigurableI2CClient.MakeChild() for _ in range(3)]

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

    check_design(app.tg, stage=F.implements_design_check.CheckStage.POST_SOLVE)


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
            app.tg, stage=F.implements_design_check.CheckStage.POST_SOLVE
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
            app.tg, stage=F.implements_design_check.CheckStage.POST_SOLVE
        )
    assert e.group_contains(
        UserDesignCheckException, match="Duplicate I2C addresses found on the bus:"
    )
