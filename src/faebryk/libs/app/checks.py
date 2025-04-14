# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.libs.app.erc import simple_erc

logger = logging.getLogger(__name__)


class CheckException(Exception): ...


def run_checks(app: Module, G: Graph):
    # TODO should make a Trait Trait: `implements_design_check`
    check_requires_external_usage(G)
    simple_erc(G)


class RequiresExternalUsageNotFulfilled(CheckException):
    def __init__(self, nodes: list[Node]):
        self.nodes = nodes
        super().__init__(
            f"Nodes requiring external usage but not used externally: "
            f"{', '.join(mif.get_full_name() for mif in nodes)}"
        )


def check_requires_external_usage(G: Graph):
    unfulfilled = []
    for node, trait in GraphFunctions(G).nodes_with_trait(F.requires_external_usage):
        if not trait.fullfilled:
            unfulfilled.append(node)
    if unfulfilled:
        raise RequiresExternalUsageNotFulfilled(unfulfilled)
