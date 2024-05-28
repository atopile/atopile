# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.core.util import get_all_modules
from faebryk.library.ANY import ANY
from faebryk.library.TBD import TBD

logger = logging.getLogger(__name__)


def replace_tbd_with_any(module: Module, recursive: bool):
    """
    Replace all TBD instances with ANY instances in the given module.

    :param module: The module to replace TBD instances in.
    :param recursive: If True, replace TBD instances in submodules as well.
    """
    module = module.get_most_special()

    for param in module.PARAMs.get_all():
        if isinstance(param.get_most_narrow(), TBD):
            logger.debug(f"Replacing in {module}: {param} with ANY")
            param.merge(ANY())

    if recursive:
        for m in {_m.get_most_special() for _m in get_all_modules(module)}:
            replace_tbd_with_any(m, recursive=False)
