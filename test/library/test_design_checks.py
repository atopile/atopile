import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.app.checks import check_design
from faebryk.libs.exceptions import UserDesignCheckException
from faebryk.libs.library import L
from faebryk.libs.smd import SMDSize
from faebryk.libs.units import P


def test_i2c_requires_pulls():
    class A(Module):
        i2c: F.I2C

    class App(Module):
        a: A
        b: A

        def __preinit__(self):
            self.a.i2c.connect(self.b.i2c)

    app = App()

    # no issue if no pad boundary is crossed
    check_design(app.get_graph(), F.implements_design_check.CheckStage.POST_DESIGN)

    class App2(Module):
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
    app2.a.i2c.get_trait(F.requires_pulls).required_resistance = L.Range(
        0.1 * P.kohm, 0.5 * P.kohm
    )

    # connection crosses pad boundary, so the check now fails
    with pytest.raises(UserDesignCheckException):
        check_design(app2.get_graph(), F.implements_design_check.CheckStage.POST_DESIGN)

    # terminating the connection without providing resistance values results in a
    # warning
    app2.a.i2c.terminate(app2.a)
    check_design(app2.get_graph(), F.implements_design_check.CheckStage.POST_DESIGN)

    # setting a sufficient resistance fully satisfies the check
    app2.a.i2c.pull_up_sda.resistance.alias_is(0.2 * P.kohm)
    app2.a.i2c.pull_up_scl.resistance.alias_is(0.2 * P.kohm)
    check_design(app2.get_graph(), F.implements_design_check.CheckStage.POST_DESIGN)


def test_electric_signal_parallel_pull_resistance():
    """Test that ElectricSignal correctly calculates parallel pull resistance."""

    class TestModule(Module):
        signal: F.ElectricSignal
        power: F.ElectricPower

        def __preinit__(self):
            # Create multiple pull-up resistors in parallel
            self.r1 = F.Resistor()
            self.r2 = F.Resistor()
            self.r3 = F.Resistor()

            # Set specific resistance values for testing
            self.r1.resistance.alias_is(L.Single(10 * P.kohm))
            self.r2.resistance.alias_is(L.Single(20 * P.kohm))
            self.r3.resistance.alias_is(L.Single(30 * P.kohm))

            # Connect signal reference
            self.signal.reference.connect(self.power)

            # Connect resistors in parallel from signal to power rail
            self.signal.line.connect_via(self.r1, self.power.hv)
            self.signal.line.connect_via(self.r2, self.power.hv)
            self.signal.line.connect_via(self.r3, self.power.hv)

    module = TestModule()

    # Calculate expected parallel resistance: 1/R_eff = 1/10k + 1/20k + 1/30k
    # 1/R_eff = 0.1/k + 0.05/k + 0.033333/k = 0.183333/k
    # R_eff = k/0.183333 = 5.454545k ohms ≈ 5.45k ohms
    expected_resistance = 1 / (1 / 10 + 1 / 20 + 1 / 30)  # in kiloohms

    pull_resistance = module.signal.pull_resistance
    assert pull_resistance is not None, (
        "Pull resistance should be calculated for parallel resistors"
    )

    # Check that the calculated resistance is approximately correct (within 1%)
    calculated_value = float(
        pull_resistance.any().magnitude
    )  # Get the magnitude in base units
    tolerance = abs(calculated_value - expected_resistance) / expected_resistance
    error_msg = (
        f"Expected ~{expected_resistance:.1f} kiloohms, "
        f"got {calculated_value:.1f} kiloohms"
    )
    assert tolerance < 0.01, error_msg


def test_electric_signal_single_pull_resistance():
    """Test that ElectricSignal correctly handles single pull resistance."""

    class TestModule(Module):
        signal: F.ElectricSignal
        power: F.ElectricPower

        def __preinit__(self):
            # Create single pull-up resistor
            self.r1 = F.Resistor()

            # Set specific resistance value
            self.r1.resistance.alias_is(L.Single(10 * P.kohm))

            # Connect signal reference
            self.signal.reference.connect(self.power)

            # Connect single resistor from signal to power rail
            self.signal.line.connect_via(self.r1, self.power.hv)

    module = TestModule()

    pull_resistance = module.signal.pull_resistance
    assert pull_resistance is not None, (
        "Pull resistance should be calculated for single resistor"
    )

    # Check that the calculated resistance matches the single resistor value
    calculated_value = float(
        pull_resistance.any().magnitude
    )  # Get the magnitude in base units
    expected_value = 10.0  # 10k ohms in kiloohms
    assert abs(calculated_value - expected_value) / expected_value < 0.01, (
        f"Expected {expected_value} kiloohms, got {calculated_value} kiloohms"
    )
