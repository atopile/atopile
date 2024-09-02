# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.core.graph import Graph
from faebryk.core.module import Module
from faebryk.libs.app.erc import simple_erc


def run_checks(app: Module, G: Graph):
    simple_erc(G)
