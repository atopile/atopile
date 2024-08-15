# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from contextlib import contextmanager
import logging
import pprint
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from textwrap import indent
from typing import Callable, Iterable

from faebryk.core.core import Module, ModuleInterface, ModuleTrait, Parameter
from faebryk.core.util import get_all_modules
from faebryk.library.ANY import ANY
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.Electrical import Electrical
from faebryk.library.has_picker import has_picker
from faebryk.libs.util import NotNone, flatten
from rich.progress import Progress

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

    def __repr__(self):
        return f"{type(self).__name__}({self.module}, {self.message})"


class PickErrorNotImplemented(PickError):
    def __init__(self, module: Module):
        message = f"Could not pick part for {module}: Not implemented"
        super().__init__(message, module)


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


class has_part_picked_remove(has_part_picked.impl()):
    class RemovePart(Part):
        class NoSupplier(Supplier):
            def attach(self, module: Module, part: PickerOption):
                pass

        def __init__(self):
            super().__init__("REMOVE", self.NoSupplier())

    def __init__(self) -> None:
        super().__init__()
        self.part = self.RemovePart()

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
        params[k].override(v)

    logger.debug(f"Attached {option.part.partno} to {module}")
    return option


def _get_mif_top_level_modules(mif: ModuleInterface):
    return [n for n in mif.NODEs.get_all() if isinstance(n, Module)] + [
        m for nmif in mif.IFs.get_all() for m in _get_mif_top_level_modules(nmif)
    ]


class PickerProgress:
    def __init__(self):
        self.progress = Progress()
        self.task = self.progress.add_task("Picking", total=1)

    @classmethod
    def from_module(cls, module: Module) -> "PickerProgress":
        self = cls()
        self.progress.update(self.task, total=len(get_all_modules(module)))
        return self

    def advance(self, module: Module):
        self.progress.advance(self.task, len(get_all_modules(module)))

    @contextmanager
    def context(self):
        with self.progress:
            yield self


# TODO should be a Picker
def pick_part_recursively(module: Module):
    pp = PickerProgress.from_module(module)
    try:
        with pp.context():
            _pick_part_recursively(module, pp)
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


def _pick_part_recursively(module: Module, progress: PickerProgress | None = None):
    assert isinstance(module, Module)

    # pick only for most specialized module
    module = module.get_most_special()

    if module.has_trait(has_part_picked):
        return

    # pick mif module parts

    for mif in module.IFs.get_all():
        for mod in _get_mif_top_level_modules(mif):
            _pick_part_recursively(mod, progress)

    # pick
    if module.has_trait(has_picker):
        try:
            module.get_trait(has_picker).pick()
        except PickError as e:
            # if no children, raise
            # This whole logic will be so much easier if the recursive
            # picker is just a normal picker
            if not module.NODEs.get_all():
                raise e

    if module.has_trait(has_part_picked):
        if progress:
            progress.advance(module)
        return

    # if module has been specialized during pick, try again
    if module.get_most_special() != module:
        _pick_part_recursively(module, progress)
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
                _pick_part_recursively(child, progress)
            except PickError as e:
                failed[child] = e

        # no progress
        if to_pick == set(failed.keys()):
            raise PickErrorChildren(module, failed)

        to_pick = set(failed.keys())
        failed.clear()
