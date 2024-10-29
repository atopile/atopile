# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


def test_add():
    from faebryk.core.cpp import add

    assert add(1, 2) == 3
