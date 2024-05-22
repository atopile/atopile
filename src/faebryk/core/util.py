# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from typing import Callable, Iterable, Sequence, SupportsFloat, Tuple, TypeVar, cast

import networkx as nx
from faebryk.core.core import (
    GraphInterface,
    GraphInterfaceSelf,
    Link,
    Module,
    ModuleInterface,
    Node,
    Parameter,
)
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Constant import Constant
from faebryk.library.Electrical import Electrical
from faebryk.library.has_overriden_name_defined import has_overriden_name_defined
from faebryk.library.Range import Range
from faebryk.library.Set import Set
from faebryk.libs.util import NotNone, cast_assert

logger = logging.getLogger(__name__)
T = TypeVar("T")


def as_scientific(value: SupportsFloat, base=10):
    if value == 0:
        return 0, 0
    exponent = math.floor(math.log(abs(value), base))
    mantissa = value / (base**exponent)

    return mantissa, exponent


def unit_map(
    value: SupportsFloat,
    units: Sequence[str],
    start: str | None = None,
    base: int = 1000,
    allow_out_of_bounds: bool = False,
):
    value = float(value)
    start_idx = units.index(start) if start is not None else 0

    mantissa, exponent = as_scientific(value, base=base)

    available_exponent = max(min(exponent + start_idx, len(units) - 1), 0) - start_idx
    exponent_difference = exponent - available_exponent

    if not allow_out_of_bounds and exponent_difference:
        raise ValueError(f"Value {value} with {exponent=} out of bounds for {units=}")

    effective_mantissa = mantissa * (base**exponent_difference)
    round_digits = round(math.log(base, 10) * (1 - exponent_difference))
    # print(f"{exponent_difference=}, {effective_mantissa=}, {round_digits=}")

    idx = available_exponent + start_idx
    rounded_mantissa = round(effective_mantissa, round_digits)
    if rounded_mantissa == math.floor(rounded_mantissa):
        rounded_mantissa = math.floor(rounded_mantissa)

    out = f"{rounded_mantissa}{units[idx]}"

    return out


def get_unit_prefix(value: SupportsFloat, base: int = 1000):
    if base == 1000:
        units = ["f", "p", "n", "µ", "m", "", "k", "M", "G", "T", "P", "E"]
    elif base == 1024:
        units = ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei"]
    else:
        raise NotImplementedError(f"Unsupported {base=}")

    return unit_map(value, units, start="", base=base, allow_out_of_bounds=True)


def as_unit(value: SupportsFloat, unit: str, base: int = 1000):
    return get_unit_prefix(value, base=base) + unit


def get_all_nodes(node: Node, order_types=None) -> list[Node]:
    if order_types is None:
        order_types = []

    out: list[Node] = list(node.NODEs.get_all())
    if isinstance(node, (Module, ModuleInterface)):
        mifs = node.IFs.get_all()
        out.extend(mifs)
        out.extend([i for nested in mifs for i in get_all_nodes(nested)])
    out.extend([i for nested in out for i in get_all_nodes(nested)])

    out = sorted(
        out,
        key=lambda x: order_types.index(type(x))
        if type(x) in order_types
        else len(order_types),
    )

    return out


def get_all_modules(node: Node) -> set[Module]:
    return {n for n in get_all_nodes(node) if isinstance(n, Module)}


def get_all_nodes_graph(G: nx.Graph):
    return {
        n
        for gif in G.nodes
        if isinstance(gif, GraphInterfaceSelf) and (n := gif.node) is not None
    }


def get_all_highest_parents_graph(G: nx.Graph):
    return {n for n in get_all_nodes_graph(G) if n.GIFs.parent.get_parent() is None}


def get_all_connected(gif: GraphInterface) -> list[tuple[GraphInterface, Link]]:
    return [
        (other, link)
        for link in gif.connections
        for other in link.get_connections()
        if other is not gif
    ]


def get_connected_mifs(gif: GraphInterface):
    return set(get_connected_mifs_with_link(gif).keys())


def get_connected_mifs_with_link(gif: GraphInterface):
    assert isinstance(gif.node, ModuleInterface)
    connections = get_all_connected(gif)

    # check if ambiguous links between mifs
    assert len(connections) == len({c[0] for c in connections})

    return {
        cast_assert(ModuleInterface, s.node): link
        for s, link in connections
        if s.node is not gif.node
    }


def get_net(mif: Electrical):
    from faebryk.library.Net import Net

    nets = {
        net
        for mif in get_connected_mifs(mif.GIFs.connected)
        if (net := get_parent_of_type(mif, Net)) is not None
    }

    if not nets:
        return None

    assert len(nets) == 1
    return next(iter(nets))


def get_parent(node: Node, filter_expr: Callable):
    candidates = [p for p, _ in node.get_hierarchy() if filter_expr(p)]
    if not candidates:
        return None
    return candidates[-1]


T = TypeVar("T")


def get_parent_of_type(node: Node, parent_type: type[T]) -> T | None:
    return cast(parent_type, get_parent(node, lambda p: isinstance(p, parent_type)))


def connect_interfaces_via_chain(
    start: ModuleInterface, bridges: Iterable[Node], end: ModuleInterface
):
    from faebryk.library.can_bridge import can_bridge

    last = start
    for bridge in bridges:
        last.connect(bridge.get_trait(can_bridge).get_in())
        last = bridge.get_trait(can_bridge).get_out()
    last.connect(end)


MIF = TypeVar("MIF", bound=ModuleInterface)


def connect_all_interfaces(interfaces: Iterable[MIF]):
    interfaces = list(interfaces)
    if not interfaces:
        return
    return connect_to_all_interfaces(interfaces[0], interfaces[1:])
    # not needed with current connection implementation
    # for i in interfaces:
    #    for j in interfaces:
    #        i.connect(j)


def connect_to_all_interfaces(source: MIF, targets: Iterable[MIF]):
    for i in targets:
        source.connect(i)
    return source


def zip_connect_modules(src: Iterable[Module], dst: Iterable[Module]):
    for src_m, dst_m in zip(src, dst):
        for src_i, dst_i in zip(src_m.IFs.get_all(), dst_m.IFs.get_all()):
            assert isinstance(src_i, ModuleInterface)
            assert isinstance(dst_i, ModuleInterface)
            src_i.connect(dst_i)


def zip_moduleinterfaces(
    src: Iterable[ModuleInterface], dst: Iterable[ModuleInterface]
):
    # TODO check names?
    # TODO check types?
    for src_m, dst_m in zip(src, dst):
        for src_i, dst_i in zip(src_m.IFs.get_all(), dst_m.IFs.get_all()):
            assert isinstance(src_i, ModuleInterface)
            assert isinstance(dst_i, ModuleInterface)
            yield src_i, dst_i


def get_mif_tree(
    obj: ModuleInterface | Module,
) -> dict[ModuleInterface, dict[ModuleInterface, dict]]:
    mifs = obj.IFs.get_all() if isinstance(obj, Module) else obj.IFs.get_all()
    assert all(isinstance(i, ModuleInterface) for i in mifs)
    mifs = cast(list[ModuleInterface], mifs)

    return {mif: get_mif_tree(mif) for mif in mifs}


def format_mif_tree(tree: dict[ModuleInterface, dict[ModuleInterface, dict]]) -> str:
    def str_tree(
        tree: dict[ModuleInterface, dict[ModuleInterface, dict]]
    ) -> dict[str, dict]:
        def get_name(k: ModuleInterface):
            # get_parent never none, since k gotten from parent
            return NotNone(k.get_parent())[1]

        return {
            f"{get_name(k)} ({type(k).__name__})": str_tree(v) for k, v in tree.items()
        }

    import json

    return json.dumps(str_tree(tree), indent=4)


T = TypeVar("T", bound=ModuleInterface)


def specialize_interface(
    general: ModuleInterface,
    special: T,
) -> T:
    logger.debug(f"Specializing MIF {general} with {special}")

    # This is doing the heavy lifting
    general.connect(special)

    # Establish sibling relationship
    general.GIFs.specialized.connect(special.GIFs.specializes)

    return special


T = TypeVar("T", bound=Module)
U = TypeVar("U", bound=Node)


def specialize_module(
    general: Module,
    special: T,
    matrix: list[tuple[ModuleInterface, ModuleInterface]] | None = None,
    attach_to: Node | None = None,
) -> T:
    logger.debug(f"Specializing Module {general} with {special}" + " " + "=" * 20)

    def get_node_prop_matrix(sub_type: type[U]) -> list[tuple[U, U]]:
        def _get_with_names(module: Module) -> dict[str, U]:
            if sub_type is ModuleInterface:
                holder = module.IFs
            elif sub_type is Parameter:
                holder = module.PARAMs
            elif sub_type is Node:
                holder = module.NODEs
            else:
                raise Exception()

            return {NotNone(i.get_parent())[1]: i for i in holder.get_all()}

        s = _get_with_names(general)
        d = _get_with_names(special)

        matrix = [
            (src_i, dst_i)
            for name, src_i in s.items()
            if (dst_i := d.get(name)) is not None
        ]

        return matrix

    if matrix is None:
        matrix = get_node_prop_matrix(ModuleInterface)

        # TODO add warning if not all src interfaces used

    param_matrix = get_node_prop_matrix(Parameter)

    for src, dst in matrix:
        specialize_interface(src, dst)

    for src, dst in param_matrix:
        dst.merge(src)

    # TODO this cant work
    # for t in general.traits:
    #    # TODO needed?
    #    if special.has_trait(t.trait):
    #        continue
    #    special.add_trait(t)

    general.GIFs.specialized.connect(special.GIFs.specializes)
    logger.debug("=" * 120)

    # Attach to new parent
    has_parent = special.get_parent() is not None
    assert not has_parent or attach_to is None
    if not has_parent:
        if attach_to:
            attach_to.NODEs.extend_list("specialized", special)
        else:
            gen_parent = general.get_parent()
            if gen_parent:
                setattr(gen_parent[0].NODEs, f"{gen_parent[1]}_specialized", special)

    return special


def get_parameter_max(param: Parameter):
    if isinstance(param, Constant):
        return param.value
    if isinstance(param, Range):
        return param.max
    if isinstance(param, Set):
        return max(map(get_parameter_max, param.params))
    raise ValueError(f"Can't get max for {param}")


def reversed_bridge(bridge: Node):
    from faebryk.library.can_bridge import can_bridge

    class _reversed_bridge(Node):
        def __init__(self) -> None:
            super().__init__()

            bridge_trait = bridge.get_trait(can_bridge)
            if_in = bridge_trait.get_in()
            if_out = bridge_trait.get_out()

            self.add_trait(can_bridge_defined(if_out, if_in))

    return _reversed_bridge()


def use_interface_names_as_net_names(node: Node, name: str | None = None):
    from faebryk.library.Net import Net

    if not name:
        p = node.get_parent()
        assert p
        name = p[1]

    name_prefix = node.get_full_name()

    el_ifs = {n for n in get_all_nodes(node) if isinstance(n, Electrical)}

    # for el_if in el_ifs:
    #    print(el_if)
    # print("=" * 80)

    # performance
    resolved: set[ModuleInterface] = set()

    # get representative interfaces that determine the name of the Net
    to_use: set[Electrical] = set()
    for el_if in el_ifs:
        # performance
        if el_if in resolved:
            continue

        connections = el_if.get_direct_connections() | {el_if}

        # skip ifs with Nets
        if matched_nets := {  # noqa: F841
            n
            for c in connections
            if (p := c.get_parent())
            and isinstance(n := p[0], Net)
            and n.IFs.part_of in connections
        }:
            # logger.warning(f"Skipped, attached to Net: {el_if}: {matched_nets!r}")
            resolved.update(connections)
            continue

        group = {mif for mif in connections if mif in el_ifs}

        # heuristic: choose shortest name
        picked = min(group, key=lambda x: len(x.get_full_name()))
        to_use.add(picked)

        # for _el_if in group:
        #    print(_el_if if _el_if is not picked else f"{_el_if} <-")
        # print("-" * 80)

        # performance
        resolved.update(group)

    nets: dict[str, Tuple[Net, Electrical]] = {}
    for el_if in to_use:
        net_name = f"{name}{el_if.get_full_name().removeprefix(name_prefix)}"

        # name collision
        if net_name in nets:
            net, other_el = nets[net_name]
            raise Exception(
                f"{el_if} resolves to {net_name} but not connected"
                + f"\nwhile attaching nets to {node}={name} (connected via {other_el})"
                + "\n"
                + "\nConnections\n\t"
                + "\n\t".join(map(str, el_if.get_direct_connections()))
                + f"\n{'-'*80}"
                + "\nNet Connections\n\t"
                + "\n\t".join(map(str, net.IFs.part_of.get_direct_connections()))
            )

        net = Net()
        net.add_trait(has_overriden_name_defined(net_name))
        net.IFs.part_of.connect(el_if)
        logger.debug(f"Created {net_name} for {el_if}")
        nets[net_name] = net, el_if
