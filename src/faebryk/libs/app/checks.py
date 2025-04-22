# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.libs.exceptions import UserDesignCheckException, accumulate, downgrade

logger = logging.getLogger(__name__)


def check_design(
    G: Graph,
    stage: F.implements_design_check.CheckStage,
    exclude: tuple[str, ...] = tuple(),
):
    """
    args:
        exclude: list of names of checks to exclude e.g:
        - `I2C.requires_unique_addresses`
    """
    logger.info(f"Running design checks for stage {stage.name}")

    with accumulate(UserDesignCheckException) as accumulator:
        for _, trait in GraphFunctions(G).nodes_with_trait(F.implements_design_check):
            if trait.get_name_of_test() in exclude:
                continue

            with accumulator.collect():
                try:
                    trait.run(stage)
                except F.implements_design_check.MaybeUnfulfilledCheckException as e:
                    with downgrade(UserDesignCheckException):
                        raise UserDesignCheckException.from_nodes(
                            str(e), e.nodes
                        ) from e
                except F.implements_design_check.UnfulfilledCheckException as e:
                    raise UserDesignCheckException.from_nodes(str(e), e.nodes) from e
