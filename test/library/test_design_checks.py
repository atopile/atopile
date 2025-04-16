import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.app.checks import check_design
from faebryk.libs.exceptions import UserDesignCheckException
from faebryk.libs.library import L
from faebryk.libs.units import P


def test_i2c_requires_pulls():
    class A(Module):
        i2c: F.I2C

    class App(Module):
        a: A
        b: A

        def __postinit__(self):
            self.a.i2c.connect(self.b.i2c)

    app = App()

    # no issue if no footprint boundary is crossed
    check_design(app.get_graph())

    class App2(Module):
        a: A
        b: A

        def __postinit__(self):
            self.a.i2c.connect(self.b.i2c)

            fp = F.Footprint()
            self.a.add(F.has_footprint_defined(fp))

    app2 = App2()

    # required resistance can be customized
    app2.a.i2c.get_trait(F.requires_pulls).required_resistance = L.Range(
        0.1 * P.kohm, 0.5 * P.kohm
    )

    # connection crosses footprint boundary, so the check now fails
    with pytest.raises(UserDesignCheckException):
        check_design(app2.get_graph())

    # terminating the connection does not completely satisfy the check
    app2.a.i2c.terminate(app2.a)
    with pytest.raises(UserDesignCheckException):
        check_design(app2.get_graph())

    # setting an insufficient resistance does not satisfy the check
    app2.a.i2c.pull_up_sda.resistance = 1 * P.ohm
    app2.a.i2c.pull_up_scl.resistance = 1 * P.ohm
    with pytest.raises(UserDesignCheckException):
        check_design(app2.get_graph())

    # setting a sufficient resistance does satisfy the check
    app2.a.i2c.pull_up_sda.resistance = 0.2 * P.kohm
    app2.a.i2c.pull_up_scl.resistance = 0.2 * P.kohm
    check_design(app2.get_graph())
