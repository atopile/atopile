# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import yaml

import faebryk.library._F as F
from faebryk.core.graphinterface import Graph
from faebryk.libs.util import merge_dicts

logger = logging.getLogger(__name__)


def make_esphome_config(G: Graph) -> dict:
    esphome_components = G.nodes_with_trait(F.has_esphome_config)

    esphome_config = merge_dicts(*[t.get_config() for _, t in esphome_components])

    return esphome_config


def dump_esphome_config(config: dict) -> str:
    return yaml.dump(config)
