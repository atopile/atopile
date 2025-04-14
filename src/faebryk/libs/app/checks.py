# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.libs.app.erc import simple_erc
from faebryk.libs.exceptions import accumulate

logger = logging.getLogger(__name__)


def run_checks(app: Module, G: Graph):
    simple_erc(G)

    design_check_traits = GraphFunctions(G).nodes_of_type(F.implements_design_check)
    logger.info(f"Checking {len(design_check_traits)} module-defined conditions")
    with accumulate(CheckException) as accumulator:
        with accumulator.collect():
            for trait in design_check_traits:
                trait.check()
