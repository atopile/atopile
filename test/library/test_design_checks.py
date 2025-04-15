import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.app.checks import check_design
from faebryk.libs.exceptions import UserDesignCheckException


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

    # connection crosses footprint boundary, so the check now fails
    with pytest.raises(UserDesignCheckException):
        check_design(app2.get_graph())

    # terminating the connection satisfies the check
    app.a.i2c.terminate(app.a)
    check_design(app.get_graph())
