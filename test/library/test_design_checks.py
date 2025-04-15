import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.app.checks import check_design


def test_i2c_requires_pulls():
    class App(Module):
        a: F.I2C
        b: F.I2C

        def __postinit__(self):
            self.a.connect(self.b)

    app = App()

    with pytest.raises(F.requires_pulls.RequiresPullNotFulfilled):
        check_design(app.get_graph())

    app.a.terminate(app)
    check_design(app.get_graph())
