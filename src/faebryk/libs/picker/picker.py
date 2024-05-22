# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import pprint
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Iterable

from faebryk.core.core import Module, ModuleInterface, ModuleTrait, Parameter
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.Electrical import Electrical
from faebryk.library.TBD import TBD
from faebryk.libs.util import NotNone

logger = logging.getLogger(__name__)


class Supplier(ABC):
    @abstractmethod
    def attach(self, component: Module, part: "Part"):
        ...


@dataclass
class Part:
    partno: str
    supplier: Supplier


@dataclass
class PickerOption:
    part: Part
    params: dict[str, Parameter] | None = None
    filter: Callable[[Module], bool] | None = None
    pinmap: dict[str, Electrical] | None = None
    info: dict[str, str] | None = None


class has_part_picked(ModuleTrait):
    @abstractmethod
    def get_part(self) -> Part:
        ...


class has_part_picked_defined(has_part_picked.impl()):
    def __init__(self, part: Part):
        super().__init__()
        self.part = part

    def get_part(self) -> Part:
        return self.part


def pick_module_by_params(module: Module, options: Iterable[PickerOption]):
    if module.has_trait(has_part_picked):
        logger.debug(f"Ignoring already picked module: {module}")
        return

    params = {
        NotNone(p.get_parent())[1]: p.get_most_narrow() for p in module.PARAMs.get_all()
    }

    try:
        option = next(
            filter(
                lambda o: (not o.filter or o.filter(module))
                and all(
                    v.is_mergeable_with(params.get(k, TBD()))
                    for k, v in (o.params or {}).items()
                    if not k.startswith("_")
                ),
                options,
            )
        )
    except StopIteration:
        raise ValueError(
            f"Could not find part for {module=} with params:\n"
            f" {pprint.pformat(params, indent=4)}"
        )

    if option.pinmap:
        module.add_trait(can_attach_to_footprint_via_pinmap(option.pinmap))

    option.part.supplier.attach(module, option.part)
    module.add_trait(has_part_picked_defined(option.part))

    # Merge params from footprint option
    for k, v in (option.params or {}).items():
        if k not in params:
            continue
        params[k].merge(v)

    logger.debug(f"Attached {option.part.partno} to {module}")
    return option


def pick_part_recursively(module: Module, pick: Callable[[Module], bool]):
    assert isinstance(module, Module)

    # pick only for most specialized module
    module = module.get_most_special()

    if module.has_trait(has_part_picked):
        return

    # pick mif module parts
    def _get_mif_top_level_modules(mif: ModuleInterface):
        return [n for n in mif.NODEs.get_all() if isinstance(n, Module)] + [
            m for nmif in mif.IFs.get_all() for m in _get_mif_top_level_modules(nmif)
        ]

    for mif in module.IFs.get_all():
        for mod in _get_mif_top_level_modules(mif):
            pick_part_recursively(mod, pick)

    # pick
    picked = pick(module)
    if picked:
        return

    # go level lower
    children = module.NODEs.get_all()
    if not children:
        logger.warning(f"Module without pick: {module}")
    for child in children:
        if not isinstance(child, Module):
            continue
        if child is module:
            continue
        pick_part_recursively(child, pick)
