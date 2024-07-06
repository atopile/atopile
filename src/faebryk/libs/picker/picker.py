# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import pprint
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from textwrap import indent
from typing import Any, Callable, Iterable

from faebryk.core.core import Module, ModuleInterface, ModuleTrait, Parameter
from faebryk.library.ANY import ANY
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.Electrical import Electrical
from faebryk.libs.util import NotNone, flatten

logger = logging.getLogger(__name__)


class Supplier(ABC):
    @abstractmethod
    def attach(self, module: Module, part: "PickerOption"): ...


@dataclass
class Part:
    partno: str
    supplier: Supplier


class DescriptiveProperties(StrEnum):
    manufacturer = "Manufacturer"
    partno = "Partnumber"
    datasheet = "Datasheet"


@dataclass
class PickerOption:
    part: Part
    params: dict[str, Parameter] | None = None
    filter: Callable[[Module], bool] | None = None
    pinmap: dict[str, Electrical] | None = None
    info: dict[str | DescriptiveProperties, str] | None = None


class PickError(Exception):
    def __init__(self, message: str, module: Module):
        super().__init__(message)
        self.message = message
        self.module = module


class PickErrorChildren(PickError):
    def __init__(self, module: Module, children: dict[Module, PickError]):
        self.children = children

        message = f"Could not pick parts for children of {module}:\n" + "\n".join(
            f"{m}: caused by {v.message}" for m, v in self.get_all_children().items()
        )
        super().__init__(message, module)

    def get_all_children(self):
        return {
            k: v
            for k, v in self.children.items()
            if not isinstance(v, PickErrorChildren)
        } | {
            module: v2
            for v in self.children.values()
            if isinstance(v, PickErrorChildren)
            for module, v2 in v.get_all_children().items()
        }


class PickErrorParams(PickError):
    def __init__(self, module: Module, options: list[PickerOption]):
        self.options = options

        MAX = 5

        options_str = "\n".join(
            f"{pprint.pformat(o.params, indent=4)}" for o in self.options[:MAX]
        )
        if len(self.options) > MAX:
            options_str += f"\n... and {len(self.options) - MAX} more"

        params = {
            NotNone(p.get_parent())[1]: p.get_most_narrow()
            for p in module.PARAMs.get_all()
        }
        params_str = "\n".join(f"{k}: {v}" for k, v in params.items())

        message = (
            f"Could not find part for {module}"
            f"\nwith params:\n{indent(params_str, ' '*4)}"
            f"\nin options:\n {indent(options_str, ' '*4)}"
        )
        super().__init__(message, module)


class has_part_picked(ModuleTrait):
    @abstractmethod
    def get_part(self) -> Part: ...


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

    options = list(options)

    try:
        option = next(
            filter(
                lambda o: (not o.filter or o.filter(module))
                and all(
                    v.is_more_specific_than(params.get(k, ANY()))
                    for k, v in (o.params or {}).items()
                    if not k.startswith("_")
                ),
                options,
            )
        )
    except StopIteration:
        raise PickErrorParams(module, options)

    if option.pinmap:
        module.add_trait(can_attach_to_footprint_via_pinmap(option.pinmap))

    option.part.supplier.attach(module, option)
    module.add_trait(has_part_picked_defined(option.part))

    # Merge params from footprint option
    for k, v in (option.params or {}).items():
        if k not in params:
            continue
        params[k].merge(v)

    logger.debug(f"Attached {option.part.partno} to {module}")
    return option


def _get_mif_top_level_modules(mif: ModuleInterface):
    return [n for n in mif.NODEs.get_all() if isinstance(n, Module)] + [
        m for nmif in mif.IFs.get_all() for m in _get_mif_top_level_modules(nmif)
    ]


def pick_part_recursively(module: Module, pick: Callable[[Module], Any]):
    try:
        _pick_part_recursively(module, pick)
    except PickErrorChildren as e:
        failed_parts = e.get_all_children()
        for m, sube in failed_parts.items():
            logger.error(f"Could not find pick for {m}:\n {sube.message}")
        raise e

    # check if lowest children are picked
    def get_not_picked(m: Module):
        ms = m.get_most_special()

        # check if parent is picked
        if ms is not m:
            parents = [p for p, _ in ms.get_hierarchy()]
            if any(p.has_trait(has_part_picked) for p in parents):
                return []

        m = ms

        out = flatten(
            [
                get_not_picked(mod)
                for mif in m.IFs.get_all()
                for mod in _get_mif_top_level_modules(mif)
            ]
        )

        if m.has_trait(has_part_picked):
            return out

        children = [c for c in m.NODEs.get_all() if isinstance(c, Module)]
        if not children:
            return out + [m]

        return out + flatten([get_not_picked(c) for c in children])

    not_picked = get_not_picked(module)
    for np in not_picked:
        logger.warning(f"Part without pick {np}")


def _pick_part_recursively(module: Module, pick: Callable[[Module], Any]):
    assert isinstance(module, Module)

    # pick only for most specialized module
    module = module.get_most_special()

    if module.has_trait(has_part_picked):
        return

    # pick mif module parts

    for mif in module.IFs.get_all():
        for mod in _get_mif_top_level_modules(mif):
            _pick_part_recursively(mod, pick)

    # pick
    pick(module)
    if module.has_trait(has_part_picked):
        return

    # if module has been specialized during pick, try again
    if module.get_most_special() != module:
        _pick_part_recursively(module, pick)
        return

    # go level lower
    children = module.NODEs.get_all()

    to_pick: set[Module] = {
        c for c in children if isinstance(c, Module) and c is not module
    }
    failed: dict[Module, PickError] = {}

    # try repicking as long as progress is being made
    while to_pick:
        for child in to_pick:
            try:
                _pick_part_recursively(child, pick)
            except PickError as e:
                failed[child] = e
        if to_pick == set(failed.keys()):
            raise PickErrorChildren(module, failed)

        to_pick = set(failed.keys())
        failed.clear()
