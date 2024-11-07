# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Any, Callable

import yaml

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.parameter import Parameter

logger = logging.getLogger(__name__)


# TODO move to util
def dict_map_values(d: dict, function: Callable[[Any], Any]) -> dict:
    """recursively map all values in a dict"""

    result = {}
    for key, value in d.items():
        if isinstance(value, dict):
            result[key] = dict_map_values(value, function)
        elif isinstance(value, list):
            result[key] = [dict_map_values(v, function) for v in value]
        else:
            result[key] = function(value)
    return result


def merge_dicts(*dicts: dict) -> dict:
    """merge a list of dicts into a single dict,
    if same key is present and value is list, lists are merged
    if same key is dict, dicts are merged recursively
    """
    result = {}
    for d in dicts:
        for k, v in d.items():
            if k in result:
                if isinstance(v, list):
                    assert isinstance(
                        result[k], list
                    ), f"Trying to merge list into key '{k}' of type {type(result[k])}"
                    result[k] += v
                elif isinstance(v, dict):
                    assert isinstance(result[k], dict)
                    result[k] = merge_dicts(result[k], v)
                else:
                    result[k] = v
            else:
                result[k] = v
    return result


def make_esphome_config(G: Graph) -> dict:
    esphome_components = GraphFunctions(G).nodes_with_trait(F.has_esphome_config)

    esphome_config = merge_dicts(*[t.get_config() for _, t in esphome_components])

    def instantiate_param(param: Parameter | Any):
        if not isinstance(param, Parameter):
            return param

        if not isinstance(param, F.Constant):
            raise Exception(
                f"Parameter {param} is not a F.Constant, but {type(param)}"
                f"Config: {esphome_config}"
            )
        return param.value

    instantiated = dict_map_values(esphome_config, instantiate_param)

    return instantiated


def dump_esphome_config(config: dict) -> str:
    return yaml.dump(config)
