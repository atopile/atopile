# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.app.checks import (
    RequiresExternalUsageNotFulfilled,
    check_requires_external_usage,
)

logger = logging.getLogger(__name__)


def test_requires_external_usage():
    class App(Module):
        class Outer(Module):
            class Inner(Module):
                b: F.Electrical

            a: F.Electrical
            inner: Inner

            def __preinit__(self):
                self.a.add(F.requires_external_usage())

        outer1: Outer
        outer2: Outer

    app = App()

    # no connections
    with pytest.raises(RequiresExternalUsageNotFulfilled):
        check_requires_external_usage(app, app.get_graph())

    # internal connection
    app.outer1.a.connect(app.outer1.inner.b)
    with pytest.raises(RequiresExternalUsageNotFulfilled):
        check_requires_external_usage(app, app.get_graph())

    # path to external
    app.outer1.inner.b.connect(app.outer2.a)
    with pytest.raises(RequiresExternalUsageNotFulfilled):
        check_requires_external_usage(app, app.get_graph())

    # direct external connection
    app.outer1.a.connect(app.outer2.inner.b)
    check_requires_external_usage(app, app.get_graph())
