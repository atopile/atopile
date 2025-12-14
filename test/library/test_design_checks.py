import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.app.checks import check_design
from faebryk.libs.exceptions import UserDesignCheckException
from faebryk.libs.smd import SMDSize


def test_i2c_requires_pulls():
    class A(fabll.Node):
        i2c: F.I2C

    class App(fabll.Node):
        a: A
        b: A

        def __preinit__(self):
            self.a.i2c.connect(self.b.i2c)

    app = App()

    # no issue if no pad boundary is crossed
    check_design(app.tg, F.implements_design_check.CheckStage.POST_DESIGN)

    class App2(fabll.Node):
        a: A
        b: A

        def __preinit__(self):
            self.a.i2c.connect(self.b.i2c)

            self.a.add(
                F.can_attach_to_footprint_via_pinmap(
                    {
                        "1": self.a.i2c.sda.line,
                        "2": self.a.i2c.scl.line,
                    },
                )
            ).attach(F.SMDTwoPin(SMDSize.I0402, F.SMDTwoPin.Type.Resistor))
            self.b.add(
                F.can_attach_to_footprint_via_pinmap(
                    {
                        "1": self.b.i2c.sda.line,
                        "2": self.b.i2c.scl.line,
                    },
                )
            ).attach(F.SMDTwoPin(SMDSize.I0402, F.SMDTwoPin.Type.Resistor))

    app2 = App2()

    # required resistance can be customized
    app2.a.i2c.get_trait(F.requires_pulls).required_resistance = fabll.Range(
        0.1 * P.kohm, 0.5 * P.kohm
    )

    # connection crosses pad boundary, so the check now fails
    with pytest.raises(UserDesignCheckException):
        check_design(app2.tg, F.implements_design_check.CheckStage.POST_DESIGN)

    # terminating the connection without providing resistance values results in a
    # warning
    app2.a.i2c.terminate(app2.a)
    check_design(app2.tg, F.implements_design_check.CheckStage.POST_DESIGN)

    # setting a sufficient resistance fully satisfies the check
    app2.a.i2c.pull_up_sda.resistance.alias_is(0.2 * 1e3 * F.Units.Ohm)
    app2.a.i2c.pull_up_scl.resistance.alias_is(0.2 * 1e3 * F.Units.Ohm)
    check_design(app2.tg, F.implements_design_check.CheckStage.POST_DESIGN)


def test_electric_signal_parallel_pull_resistance():
    """Test that ElectricSignal correctly calculates parallel pull resistance."""

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    ohm = (
        F.Units.Ohm.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .get_trait(F.Units.is_unit)
    )
    r1_value = (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_center_rel(center=10 * 1e3, rel=0.02, unit=ohm)
    )
    r2_value = (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_center_rel(center=20 * 1e3, rel=0.02, unit=ohm)
    )
    r3_value = (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_center_rel(center=30 * 1e3, rel=0.02, unit=ohm)
    )

    class TestModule(fabll.Node):
        signal = F.ElectricSignal.MakeChild()
        power = F.ElectricPower.MakeChild()

        r1 = F.Resistor.MakeChild()
        r2 = F.Resistor.MakeChild()
        r3 = F.Resistor.MakeChild()

    module = TestModule.bind_typegraph(tg=tg).create_instance(g=g)

    # Set specific resistance values for testing
    module.r1.get().resistance.get().alias_to_literal(g=g, value=r1_value)
    module.r2.get().resistance.get().alias_to_literal(g=g, value=r2_value)
    module.r3.get().resistance.get().alias_to_literal(g=g, value=r3_value)

    # Connect signal reference
    module.signal.get().reference.get()._is_interface.get().connect_to(
        module.power.get()
    )

    # Connect resistors in parallel from signal to power rail
    for resistor in [module.r1.get(), module.r2.get(), module.r3.get()]:
        terminals = resistor.get_children(
            direct_only=True, include_root=False, types=F.Electrical
        )
        module.signal.get().line.get()._is_interface.get().connect_to(terminals[0])
        terminals[1]._is_interface.get().connect_to(module.power.get().hv.get())

    expected_resistance = (
        r1_value.op_invert(g=g, tg=tg)
        .op_add_intervals(
            r2_value.op_invert(g=g, tg=tg),
            g=g,
            tg=tg,
        )
        .op_add_intervals(
            r3_value.op_invert(g=g, tg=tg),
            g=g,
            tg=tg,
        )
    ).op_invert(g=g, tg=tg)

    lit_trait = (
        module.signal.get()
        .pull_resistance.get_trait(F.Parameters.is_parameter_operatable)
        .try_get_subset_or_alias_literal()
    )
    assert lit_trait is not None
    lit = fabll.Traits(lit_trait).get_obj(F.Literals.Numbers)
    assert lit.is_subset_of(g=g, tg=tg, other=expected_resistance)
    assert expected_resistance.is_subset_of(g=g, tg=tg, other=lit)


def test_electric_signal_single_pull_resistance():
    """Test that ElectricSignal correctly handles single pull resistance."""

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    r1_value = (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_center_rel(
            center=10 * 1e3,
            rel=0.02,
            unit=F.Units.Ohm.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .get_trait(F.Units.is_unit),
        )
    )

    class TestModule(fabll.Node):
        signal = F.ElectricSignal.MakeChild()
        power = F.ElectricPower.MakeChild()

        r1 = F.Resistor.MakeChild()

    module = TestModule.bind_typegraph(tg=tg).create_instance(g=g)

    module.r1.get().resistance.get().alias_to_literal(g=g, value=r1_value)

    terminals = module.r1.get().get_children(
        direct_only=True, include_root=False, types=F.Electrical
    )

    # Connect signal reference to the module power rail
    module.signal.get().reference.get()._is_interface.get().connect_to(
        module.power.get()
    )

    # Connect the resistor between the signal line and reference HV
    module.signal.get().line.get()._is_interface.get().connect_to(terminals[0])
    terminals[1]._is_interface.get().connect_to(
        module.signal.get().reference.get().hv.get()
    )

    lit_trait = (
        module.signal.get()
        .pull_resistance.get_trait(F.Parameters.is_parameter_operatable)
        .try_get_subset_or_alias_literal()
    )
    assert lit_trait is not None
    lit = fabll.Traits(lit_trait).get_obj(F.Literals.Numbers)
    assert lit.is_subset_of(g=g, tg=tg, other=r1_value)
    assert r1_value.is_subset_of(g=g, tg=tg, other=lit)
