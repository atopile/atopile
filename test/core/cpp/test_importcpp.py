# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.cpp import add


def test_add():
    assert add(1, 2) == 3
