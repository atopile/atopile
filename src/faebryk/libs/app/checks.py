# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.libs.app.erc import simple_erc
from faebryk.libs.exceptions import accumulate

logger = logging.getLogger(__name__)


class CheckException(Exception): ...


class RequiresExternalUsageNotFulfilled(CheckException):
    def __init__(self, nodes: list[Node]):
        self.nodes = nodes
        super().__init__(
            f"Nodes requiring external usage but not used externally: "
            f"{', '.join(mif.get_full_name() for mif in nodes)}"
        )


class RequiresPullNotFulfilled(CheckException):
    def __init__(self, nodes: list[Node]):
        self.nodes = nodes
        super().__init__(
            f"Signals requiring pulls but not pulled: "
            f"{', '.join(mif.get_full_name() for mif in nodes)}"
        )


def check_requires_external_usage(G: Graph):
    unfulfilled = []
    for node, trait in GraphFunctions(G).nodes_with_trait(F.requires_external_usage):
        if not trait.fulfilled:
            unfulfilled.append(node)
    if unfulfilled:
        raise RequiresExternalUsageNotFulfilled(unfulfilled)


def check_requires_pulls(G: Graph):
    unfulfilled = []
    for node, trait in GraphFunctions(G).nodes_with_trait(F.requires_pulls):
        if not trait.fulfilled:
            unfulfilled.append(node)
    if unfulfilled:
        raise RequiresPullNotFulfilled(unfulfilled)


def run_checks(app: Module, G: Graph):
    # TODO should make a Trait Trait: `implements_design_check`

    with accumulate(CheckException) as accumulator:
        with accumulator.collect():
            check_requires_external_usage(G)
            check_requires_pulls(G)

    simple_erc(G)
