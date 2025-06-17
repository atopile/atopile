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
