# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.library.traits import interface

logger = logging.getLogger("library")

# TODO this file should not exist

from faebryk.library.core import Interface, Component
from faebryk.library.traits.interface import is_part_of_component


def default_with(given, default):
    if given is not None:
        return given
    return default


def times(cnt, lamb):
    return [lamb() for _ in range(cnt)]


def unit_map(value: int, units, start=None, base=1000):
    if start is None:
        start_idx = 0
    else:
        start_idx = units.index(start)

    cur = base ** ((-start_idx) + 1)
    ptr = 0
    while value >= cur:
        cur *= base
        ptr += 1
    form_value = integer_base(value, base=base)
    return f"{form_value}{units[ptr]}"


def integer_base(value: int, base=1000):
    while value < 1:
        value *= base
    while value >= base:
        value /= base
    return value


def get_all_interfaces(interfaces: list[Interface]) -> list[Interface]:
    out = interfaces
    out.extend([i for nested in out for i in get_all_interfaces(nested.IFs.get_all())])
    return out


def get_all_components(component: Component) -> list[Component]:
    out = component.CMPs.get_all()
    out.extend([i for nested in out for i in get_all_components(nested)])
    return out


def get_components_of_interfaces(interfaces: list[Interface]) -> list[Component]:
    out = [
        i.get_trait(is_part_of_component).get_component()
        for i in interfaces
        if i.has_trait(is_part_of_component)
    ]
    return out


class NotifiesOnPropertyChange(object):
    def __init__(self, callback) -> None:
        self.callback = callback

    def __setattr__(self, __name, __value) -> None:
        super().__setattr__(__name, __value)
        self.callback(__name, __value)
