# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import typer

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.util import specialize_module
from faebryk.libs.examples.buildutil import apply_design_to_pcb
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class App(Module):
    lowpass: F.Filter

    def __preinit__(self) -> None:
        # TODO actually do something with the filter

        # Parametrize
        self.lowpass.cutoff_frequency.merge(200 * P.Hz)
        self.lowpass.response.merge(F.Filter.Response.LOWPASS)

        # Specialize
        special = specialize_module(self.lowpass, F.FilterElectricalLC())

        # Construct
        special.get_trait(F.has_construction_dependency).construct()


def main():
    logger.info("Building app")
    app = App()

    logger.info("Export")
    apply_design_to_pcb(app)


if __name__ == "__main__":
    setup_basic_logging()
    logger.info("Running experiment")

    typer.run(main)
