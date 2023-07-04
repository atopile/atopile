# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Iterable, TypeVar

# TODO this file should not exist
from faebryk.core.core import GraphInterface, Module, ModuleInterface, Node
from faebryk.libs.util import NotNone, cast_assert

logger = logging.getLogger(__name__)
T = TypeVar("T")


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
        value //= base
    return value


def get_all_nodes(node: Node, order_types=None) -> list[Node]:
    if order_types is None:
        order_types = []

    out: list[Node] = list(node.NODEs.get_all())
    out.extend([i for nested in out for i in get_all_nodes(nested)])

    out = sorted(
        out,
        key=lambda x: order_types.index(type(x))
        if type(x) in order_types
        else len(order_types),
    )

    return out


def get_all_connected(gif: GraphInterface) -> list[GraphInterface]:
    return [
        other
        for link in gif.connections
        for other in link.get_connections()
        if other is not gif
    ]


def get_connected_mifs(gif: GraphInterface):
    assert isinstance(gif.node, ModuleInterface)
    return {
        cast_assert(ModuleInterface, s.node)
        for s in get_all_connected(gif)
        if s.node is not gif.node
    }


def connect_interfaces_via_chain(
    start: ModuleInterface, bridges: Iterable[Node], end: ModuleInterface
):
    from faebryk.library.can_bridge import can_bridge

    last = start
    for bridge in bridges:
        last.connect(bridge.get_trait(can_bridge).get_in())
        last = bridge.get_trait(can_bridge).get_out()
    last.connect(end)


def connect_all_interfaces(interfaces: list[ModuleInterface]):
    for i in interfaces:
        for j in interfaces:
            i.connect(j)


def connect_to_all_interfaces(
    source: ModuleInterface, targets: Iterable[ModuleInterface]
):
    for i in targets:
        source.connect(i)


def zip_connect_modules(src: Iterable[Module], dst: Iterable[Module]):
    for src_m, dst_m in zip(src, dst):
        for src_i, dst_i in zip(src_m.IFs.get_all(), dst_m.IFs.get_all()):
            assert isinstance(src_i, ModuleInterface)
            assert isinstance(dst_i, ModuleInterface)
            src_i.connect(dst_i)


def zip_connect_moduleinterfaces(
    src: Iterable[ModuleInterface], dst: Iterable[ModuleInterface]
):
    # TODO check names?
    # TODO check types?
    for src_m, dst_m in zip(src, dst):
        for src_i, dst_i in zip(src_m.NODEs.get_all(), dst_m.NODEs.get_all()):
            assert isinstance(src_i, ModuleInterface)
            assert isinstance(dst_i, ModuleInterface)
            src_i.connect(dst_i)


T = TypeVar("T", bound=ModuleInterface)


def specialize_interface(
    general: ModuleInterface,
    special: T,
) -> T:
    logger.debug(f"Specializing MIF {general} with {special}")

    # This is doing the heavy lifting
    general.connect(special)

    # Establish sibling relationship
    general.GIFs.sibling.connect(special.GIFs.sibling)

    return special


T = TypeVar("T", bound=Module)


def specialize_module(
    general: Module,
    special: T,
    matrix: list[tuple[ModuleInterface, ModuleInterface]] | None = None,
) -> T:
    logger.debug(f"Specializing Module {general} with {special}" + " " + "=" * 20)

    if matrix is None:

        def _get_with_names(module: Module) -> dict[str, ModuleInterface]:
            return {NotNone(i.get_parent())[1]: i for i in module.IFs.get_all()}

        s = _get_with_names(general)
        d = _get_with_names(special)

        matrix = [
            (src_i, dst_i)
            for name, src_i in s.items()
            if (dst_i := d.get(name)) is not None
        ]

        # TODO add warning if not all src interfaces used

    for src, dst in matrix:
        assert src in general.IFs.get_all()
        assert dst in special.IFs.get_all()

        specialize_interface(src, dst)

    for t in general.traits:
        # TODO needed?
        if special.has_trait(t.trait):
            continue
        special.add_trait(t)

    general.GIFs.sibling.connect(special.GIFs.sibling)
    logger.debug("=" * 120)

    return special
