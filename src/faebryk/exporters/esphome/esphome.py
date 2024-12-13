# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import yaml

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.parameter import Parameter
from faebryk.core.solver.solver import Solver
from faebryk.libs.units import Quantity
from faebryk.libs.util import cast_assert, dict_value_visitor, merge_dicts

logger = logging.getLogger(__name__)


def make_esphome_config(G: Graph, solver: Solver) -> dict:
    esphome_components = GraphFunctions(G).nodes_with_trait(F.has_esphome_config)

    esphome_config = merge_dicts(*[t.get_config() for _, t in esphome_components])

    # deep find parameters in dict and solve
    def solve_parameter(v):
        if not isinstance(v, Parameter):
            return v

        return str(cast_assert(Quantity, solver.get_any_single(v, lock=True).value))

    dict_value_visitor(esphome_config, lambda _, v: solve_parameter(v))

    return esphome_config


def dump_esphome_config(config: dict) -> str:
    return yaml.dump(config)
