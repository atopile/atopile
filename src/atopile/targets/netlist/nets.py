from typing import Dict, Iterable, List

from atopile.model.accessors import (
    ModelVertexView,
    lowest_common_ancestor_with_ancestor_ids,
)
from atopile.model.model import Model, EdgeType, VertexType
from atopile.model.utils import generate_uid_from_path

# specifically a list of Signal and Pin vertices
NetType = Iterable[ModelVertexView]

def resolve_net_name(all_electrical_verticies: NetType) -> str:
    if not all_electrical_verticies:
        raise ValueError("No verticies provided")

    lca, rel_anc_ids = lowest_common_ancestor_with_ancestor_ids(all_electrical_verticies)

    relative_depths = [len(anc_ids) for anc_ids in rel_anc_ids]

    # descend down, checking for signals as we go
    # we're going to name the net <module-path>.<signal-name>
    # if there are multiple signals, we'll name it <module-path>.<signal-name1>-<signal-name2>
    signals_by_depth: Dict[int, List[ModelVertexView]] = {}
    for electrical_vertex, depth in zip(all_electrical_verticies, relative_depths):
        if electrical_vertex.vertex_type != VertexType.signal:
            continue
        signals_by_depth.setdefault(depth, []).append(electrical_vertex)

    if signals_by_depth:
        signals = signals_by_depth[min(signals_by_depth.keys())]
        signal_name = "-".join(sorted(signal.ref for signal in signals))
        return f"{lca.path}.{signal_name}"

    # final fallback - slap a UUID on it and call it a day
    vertex_names_uuidd = generate_uid_from_path("".join(sorted(ev.ref for ev in all_electrical_verticies)))[:6]
    return f"{lca.path}.{vertex_names_uuidd}"

def find_nets(model: Model) -> Iterable[NetType]:
    # Create the nets
    electrical_graph = model.get_graph_view([EdgeType.connects_to])
    clusters_of_ids = [set(c) for c in electrical_graph.connected_components(mode="weak")]
    clusters_of_mvv = [[ModelVertexView(model, i) for i in cid] for cid in clusters_of_ids]
    clusters_of_elec_mvv = [c for c in clusters_of_mvv if c[0].vertex_type in (VertexType.signal, VertexType.pin)]
    return clusters_of_elec_mvv

def find_net_names(model: Model) -> Dict[str, NetType]:
    nets = find_nets(model)
    return {resolve_net_name(n): n for n in nets}
