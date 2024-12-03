# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.libs.util import ConfigFlag

PLOG = ConfigFlag("PLOG", descr="Enable picker debug log")
JLOG = ConfigFlag("JLOG", descr="Enable jlcpcb picker debug log")


def setup_basic_logging():
    logging.basicConfig(level=logging.INFO)

    if PLOG:
        from faebryk.library.has_multi_picker import logger as plog

        plog.setLevel(logging.DEBUG)
        from faebryk.libs.picker.picker import logger as rlog

        rlog.setLevel(logging.DEBUG)
    if JLOG:
        from faebryk.libs.picker.jlcpcb.jlcpcb import logger as jlog

        jlog.setLevel(logging.DEBUG)
