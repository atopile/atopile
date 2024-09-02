# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter

logger = logging.getLogger(__name__)


def replace_tbd_with_any(module: Module, recursive: bool, loglvl: int | None = None):
    """
    Replace all F.TBD instances with F.ANY instances in the given module.

    :param module: The module to replace F.TBD instances in.
    :param recursive: If True, replace F.TBD instances in submodules as well.
    """
    from faebryk.core.util import get_all_modules

    lvl = logger.getEffectiveLevel()
    if loglvl is not None:
        logger.setLevel(loglvl)

    module = module.get_most_special()

    for param in module.get_children(direct_only=True, types=Parameter):
        if isinstance(param.get_most_narrow(), F.TBD):
            logger.debug(f"Replacing in {module}: {param} with F.ANY")
            param.merge(F.ANY())

    logger.setLevel(lvl)

    if recursive:
        for m in {_m.get_most_special() for _m in get_all_modules(module)}:
            replace_tbd_with_any(m, recursive=False, loglvl=loglvl)
