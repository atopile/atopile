# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum
from textwrap import indent
from typing import (
    Callable,
    Iterable,
    cast,
)

from typing_extensions import deprecated

import faebryk.library._F as F
from faebryk.core.graphinterface import (
    Graph,
    GraphInterface,
    GraphInterfaceSelf,
)
from faebryk.core.link import Link, LinkDirect
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.core.parameter import Parameter
from faebryk.core.trait import Trait
from faebryk.libs.units import Quantity, UnitsContainer, to_si_str
from faebryk.libs.util import NotNone, cast_assert, zip_dicts_by_key

logger = logging.getLogger(__name__)

# Parameter ----------------------------------------------------------------------------


def enum_parameter_representation(param: Parameter, required: bool = False) -> str:
    if isinstance(param, F.Constant):
        return param.value.name if isinstance(param.value, Enum) else str(param.value)
    elif isinstance(param, F.Range):
        return (
            f"{enum_parameter_representation(param.min)} - "
            f"{enum_parameter_representation(param.max)}"
        )
    elif isinstance(param, F.Set):
        return f"Set({', '.join(map(enum_parameter_representation, param.params))})"
    elif isinstance(param, F.TBD):
        return "TBD" if required else ""
    elif isinstance(param, F.ANY):
        return "ANY" if required else ""
    else:
        return type(param).__name__


def as_unit(
    param: Parameter[Quantity],
    unit: str | UnitsContainer,
    base: int = 1000,
    required: bool = False,
) -> str:
    if base != 1000:
        raise NotImplementedError("Only base 1000 supported")
    if isinstance(param, F.Constant):
        return to_si_str(param.value, unit)
    elif isinstance(param, F.Range):
        return (
            as_unit(param.min, unit, base=base)
            + " - "
            + as_unit(param.max, unit, base=base, required=True)
        )
    elif isinstance(param, F.Set):
        return (
            "Set("
            + ", ".join(map(lambda x: as_unit(x, unit, required=True), param.params))
            + ")"
        )
    elif isinstance(param, F.TBD):
        return "TBD" if required else ""
    elif isinstance(param, F.ANY):
        return "ANY" if required else ""

    raise ValueError(f"Unsupported {param=}")


def as_unit_with_tolerance(
    param: Parameter, unit: str, base: int = 1000, required: bool = False
) -> str:
    if isinstance(param, F.Constant):
        return as_unit(param, unit, base=base)
    elif isinstance(param, F.Range):
        center, delta = param.as_center_tuple(relative=True)
        delta_percent_str = f"±{to_si_str(delta.value, "%", 0)}"
        return (
            f"{as_unit(center, unit, base=base, required=required)} {delta_percent_str}"
        )
    elif isinstance(param, F.Set):
        return (
            "Set("
            + ", ".join(
                map(lambda x: as_unit_with_tolerance(x, unit, base), param.params)
            )
            + ")"
        )
    elif isinstance(param, F.TBD):
        return "TBD" if required else ""
    elif isinstance(param, F.ANY):
        return "ANY" if required else ""
    raise ValueError(f"Unsupported {param=}")


def get_parameter_max(param: Parameter):
    if isinstance(param, F.Constant):
        return param.value
    if isinstance(param, F.Range):
        return param.max
    if isinstance(param, F.Set):
        return max(map(get_parameter_max, param.params))
    raise ValueError(f"Can't get max for {param}")


def with_same_unit(to_convert: float | int, param: Parameter | Quantity | float | int):
    if isinstance(param, F.Constant) and isinstance(param.value, Quantity):
        return Quantity(to_convert, param.value.units)
    if isinstance(param, Quantity):
        return Quantity(to_convert, param.units)
    if isinstance(param, (float, int)):
        return to_convert
    raise NotImplementedError(f"Unsupported {param=}")


# --------------------------------------------------------------------------------------

# Graph Querying -----------------------------------------------------------------------


# Make all kinds of graph filtering functions so we can optimize them in the future
# Avoid letting user query all graph nodes always because quickly very slow


def node_projected_graph(g: Graph) -> set[Node]:
    """
    Don't call this directly, use get_all_nodes_by/of/with instead
    """
    return Node.get_nodes_from_gifs(g.subgraph_type(GraphInterfaceSelf))


@deprecated("Use get_node_children_all")
def get_all_nodes(node: Node, include_root=False) -> list[Node]:
    return node.get_node_children_all(include_root=include_root)


def get_all_modules(node: Node) -> set[Module]:
    return {n for n in get_all_nodes(node) if isinstance(n, Module)}


@deprecated("Use node_projected_graph or get_all_nodes_by/of/with")
def get_all_nodes_graph(g: Graph):
    return node_projected_graph(g)


def get_all_nodes_with_trait[T: Trait](
    g: Graph, trait: type[T]
) -> list[tuple[Node, T]]:
    return [
        (n, n.get_trait(trait)) for n in node_projected_graph(g) if n.has_trait(trait)
    ]


# Waiting for python to add support for type mapping
def get_all_nodes_with_traits[*Ts](
    g: Graph, traits: tuple[*Ts]
):  # -> list[tuple[Node, tuple[*Ts]]]:
    return [
        (n, tuple(n.get_trait(trait) for trait in traits))
        for n in node_projected_graph(g)
        if all(n.has_trait(trait) for trait in traits)
    ]


def get_all_nodes_by_names(g: Graph, names: Iterable[str]) -> list[tuple[Node, str]]:
    return [
        (n, node_name)
        for n in node_projected_graph(g)
        if (node_name := n.get_full_name()) in names
    ]


def get_all_nodes_of_type[T: Node](g: Graph, t: type[T]) -> set[T]:
    return {n for n in node_projected_graph(g) if isinstance(n, t)}


def get_all_nodes_of_types(g: Graph, t: tuple[type[Node], ...]) -> set[Node]:
    return {n for n in node_projected_graph(g) if isinstance(n, t)}


def get_all_connected(gif: GraphInterface) -> list[tuple[GraphInterface, Link]]:
    return list(gif.edges.items())


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


def get_direct_connected_nodes[T: Node](
    gif: GraphInterface, ty: type[T] = Node
) -> set[T]:
    out = Node.get_nodes_from_gifs(
        g for g, t in get_all_connected(gif) if isinstance(t, LinkDirect)
    )
    assert all(isinstance(n, ty) for n in out)
    return cast(set[T], out)


def get_net(mif: F.Electrical):
    from faebryk.library.Net import Net

    nets = {
        net
        for mif in get_connected_mifs(mif.connected)
        if (net := get_parent_of_type(mif, Net)) is not None
    }

    if not nets:
        return None

    assert len(nets) == 1
    return next(iter(nets))


@deprecated("Use get_node_direct_mods_or_mifs")
def get_node_direct_children(node: Node, include_mifs: bool = True):
    return get_node_direct_mods_or_mifs(node, include_mifs=include_mifs)


def get_node_direct_mods_or_mifs(node: Node, include_mifs: bool = True):
    types = (Module, ModuleInterface) if include_mifs else Module
    return node.get_children(direct_only=True, types=types)


def get_node_tree(
    node: Node,
    include_mifs: bool = True,
    include_root: bool = True,
) -> dict[Node, dict[Node, dict]]:
    out = get_node_direct_mods_or_mifs(node, include_mifs=include_mifs)

    tree = {
        n: get_node_tree(n, include_mifs=include_mifs, include_root=False) for n in out
    }

    if include_root:
        return {node: tree}
    return tree


def iter_tree_by_depth(tree: dict[Node, dict]):
    yield list(tree.keys())

    # zip iterators, but if one iterators stops producing, the rest continue
    def zip_exhaust(*args):
        while True:
            out = [next(a, None) for a in args]
            out = [a for a in out if a]
            if not out:
                return

            yield out

    for level in zip_exhaust(*[iter_tree_by_depth(v) for v in tree.values()]):
        # merge lists of parallel subtrees
        yield [n for subtree in level for n in subtree]


def get_mif_tree(
    obj: ModuleInterface | Module,
) -> dict[ModuleInterface, dict[ModuleInterface, dict]]:
    mifs = obj.get_children(direct_only=True, types=ModuleInterface)

    return {mif: get_mif_tree(mif) for mif in mifs}


def format_mif_tree(tree: dict[ModuleInterface, dict[ModuleInterface, dict]]) -> str:
    def str_tree(
        tree: dict[ModuleInterface, dict[ModuleInterface, dict]],
    ) -> dict[str, dict]:
        def get_name(k: ModuleInterface):
            # get_parent never none, since k gotten from parent
            return NotNone(k.get_parent())[1]

        return {
            f"{get_name(k)} ({type(k).__name__})": str_tree(v) for k, v in tree.items()
        }

    import json

    return json.dumps(str_tree(tree), indent=4)


def get_param_tree(param: Parameter) -> list[tuple[Parameter, list]]:
    out = []
    for p in param.get_narrowed_siblings():
        out.append((p, get_param_tree(p)))
    return out


# --------------------------------------------------------------------------------------

# Connection utils ---------------------------------------------------------------------


def connect_interfaces_via_chain(
    start: ModuleInterface, bridges: Iterable[Node], end: ModuleInterface, linkcls=None
):
    from faebryk.library.can_bridge import can_bridge

    last = start
    for bridge in bridges:
        last.connect(bridge.get_trait(can_bridge).get_in(), linkcls=linkcls)
        last = bridge.get_trait(can_bridge).get_out()
    last.connect(end, linkcls=linkcls)


def connect_all_interfaces[MIF: ModuleInterface](
    interfaces: Iterable[MIF], linkcls=None
):
    interfaces = list(interfaces)
    if not interfaces:
        return
    return connect_to_all_interfaces(interfaces[0], interfaces[1:], linkcls=linkcls)
    # not needed with current connection implementation
    # for i in interfaces:
    #    for j in interfaces:
    #        i.connect(j)


def connect_to_all_interfaces[MIF: ModuleInterface](
    source: MIF, targets: Iterable[MIF], linkcls=None
):
    for i in targets:
        source.connect(i, linkcls=linkcls)
    return source


def connect_module_mifs_by_name(
    src: Iterable[Module] | Module,
    dst: Iterable[Module] | Module,
    allow_partial: bool = False,
):
    if isinstance(src, Module):
        src = [src]
    if isinstance(dst, Module):
        dst = [dst]

    for src_, dst_ in zip(src, dst):
        for k, (src_m, dst_m) in zip_children_by_name(
            src_, dst_, ModuleInterface
        ).items():
            if src_m is None or dst_m is None:
                if not allow_partial:
                    raise Exception(f"Node with name {k} not present in both")
                continue
            src_m.connect(dst_m)


def reversed_bridge(bridge: Node):
    from faebryk.library.can_bridge import can_bridge

    class _reversed_bridge(Node):
        def __init__(self) -> None:
            super().__init__()

            bridge_trait = bridge.get_trait(can_bridge)
            if_in = bridge_trait.get_in()
            if_out = bridge_trait.get_out()

            self.add_trait(F.can_bridge_defined(if_out, if_in))

    return _reversed_bridge()


def zip_children_by_name[N: Node](
    node1: Node, node2: Node, sub_type: type[N]
) -> dict[str, tuple[N, N]]:
    nodes = (node1, node2)
    children = tuple(
        with_names(n.get_children(direct_only=True, include_root=False, types=sub_type))
        for n in nodes
    )
    return zip_dicts_by_key(*children)


# --------------------------------------------------------------------------------------

# Specialization -----------------------------------------------------------------------


def specialize_interface[T: ModuleInterface](
    general: ModuleInterface,
    special: T,
) -> T:
    logger.debug(f"Specializing MIF {general} with {special}")

    # This is doing the heavy lifting
    general.connect(special)

    # Establish sibling relationship
    general.specialized.connect(special.specializes)

    return special


def specialize_module[T: Module](
    general: Module,
    special: T,
    matrix: list[tuple[ModuleInterface, ModuleInterface]] | None = None,
    attach_to: Node | None = None,
) -> T:
    logger.debug(f"Specializing Module {general} with {special}" + " " + "=" * 20)

    def get_node_prop_matrix[N: Node](sub_type: type[N]):
        return list(zip_children_by_name(general, special, sub_type).values())

    if matrix is None:
        matrix = get_node_prop_matrix(ModuleInterface)

    # TODO add warning if not all src interfaces used

    param_matrix = get_node_prop_matrix(Parameter)

    for src, dst in matrix:
        if src is None:
            continue
        if dst is None:
            raise Exception(f"Special module misses interface: {src.get_name()}")
        specialize_interface(src, dst)

    for src, dst in param_matrix:
        if src is None:
            continue
        if dst is None:
            raise Exception(f"Special module misses parameter: {src.get_name()}")
        dst.merge(src)

    # TODO this cant work
    # for t in general.traits:
    #    # TODO needed?
    #    if special.has_trait(t.trait):
    #        continue
    #    special.add_trait(t)

    general.specialized.connect(special.specializes)

    # Attach to new parent
    has_parent = special.get_parent() is not None
    assert not has_parent or attach_to is None
    if not has_parent:
        if attach_to:
            attach_to.add(special, container=attach_to.specialized)
        else:
            gen_parent = general.get_parent()
            if gen_parent:
                gen_parent[0].add(special, name=f"{gen_parent[1]}_specialized")

    return special


# --------------------------------------------------------------------------------------


# Hierarchy queries --------------------------------------------------------------------


def get_parent(node: Node, filter_expr: Callable):
    candidates = [p for p, _ in node.get_hierarchy() if filter_expr(p)]
    if not candidates:
        return None
    return candidates[-1]


def get_parent_of_type[T: Node](node: Node, parent_type: type[T]) -> T | None:
    return cast(parent_type, get_parent(node, lambda p: isinstance(p, parent_type)))


def get_parent_with_trait[TR: Trait](
    node: Node, trait: type[TR], include_self: bool = True
):
    hierarchy = node.get_hierarchy()
    if not include_self:
        hierarchy = hierarchy[:-1]
    for parent, _ in reversed(hierarchy):
        if parent.has_trait(trait):
            return parent, parent.get_trait(trait)
    raise ValueError("No parent with trait found")


def get_children_of_type[U: Node](node: Node, child_type: type[U]) -> list[U]:
    return list(node.get_children(direct_only=False, types=child_type))


def get_first_child_of_type[U: Node](node: Node, child_type: type[U]) -> U:
    for level in iter_tree_by_depth(get_node_tree(node)):
        for child in level:
            if isinstance(child, child_type):
                return child
    raise ValueError("No child of type found")


# --------------------------------------------------------------------------------------

# Printing -----------------------------------------------------------------------------


def pretty_params(node: Module | ModuleInterface) -> str:
    params = {
        NotNone(p.get_parent())[1]: p.get_most_narrow()
        for p in node.get_children(direct_only=True, types=Parameter)
    }
    params_str = "\n".join(f"{k}: {v}" for k, v in params.items())

    return params_str


def pretty_param_tree(param: Parameter) -> str:
    # TODO this is def broken for actual trees
    # TODO i think the repr automatically resolves

    tree = get_param_tree(param)
    out = f"{param!r}"
    next_levels = [tree]
    while next_levels:
        if any(next_levels):
            out += indent("\n|\nv\n", " " * 12)
        for next_level in next_levels:
            for p, _ in next_level:
                out += f"{p!r}"
        next_levels = [
            children for next_level in next_levels for _, children in next_level
        ]

    return out


def pretty_param_tree_top(param: Parameter) -> str:
    arrow = indent("\n|\nv", prefix=" " * 12)
    out = (arrow + "\n").join(
        f"{param!r}| {len(param.get_narrowed_siblings())}x"
        for param in param.get_narrowing_chain()
    )
    return out


# --------------------------------------------------------------------------------------


def use_interface_names_as_net_names(node: Node, name: str | None = None):
    from faebryk.library.Net import Net

    if not name:
        p = node.get_parent()
        assert p
        name = p[1]

    name_prefix = node.get_full_name()

    el_ifs = {n for n in get_all_nodes(node) if isinstance(n, F.Electrical)}

    # for el_if in el_ifs:
    #    print(el_if)
    # print("=" * 80)

    # performance
    resolved: set[ModuleInterface] = set()

    # get representative interfaces that determine the name of the Net
    to_use: set[F.Electrical] = set()
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
            and n.part_of in connections
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

    nets: dict[str, tuple[Net, F.Electrical]] = {}
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
                + "\n\t".join(map(str, net.part_of.get_direct_connections()))
            )

        net = Net()
        net.add_trait(F.has_overriden_name_defined(net_name))
        net.part_of.connect(el_if)
        logger.debug(f"Created {net_name} for {el_if}")
        nets[net_name] = net, el_if


def with_names[N: Node](nodes: Iterable[N]) -> dict[str, N]:
    return {n.get_name(): n for n in nodes}
