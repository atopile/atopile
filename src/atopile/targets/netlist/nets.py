from typing import Dict, Iterable, List, Optional

from atopile.model.accessors import ModelVertexView
from atopile.model.model import Model, EdgeType, VertexType
from atopile.model.names import resolve_rel_path_sections, generate_hash_name


NetType = List[ModelVertexView]


def find_nets(model: Model) -> Iterable[NetType]:
    # Create the nets
    electrical_graph = model.get_graph_view([EdgeType.connects_to])
    clusters_of_ids = [
        set(c) for c in electrical_graph.connected_components(mode="weak")
    ]
    clusters_of_mvv = [
        [ModelVertexView(model, i) for i in cid] for cid in clusters_of_ids
    ]
    clusters_of_elec_mvv = [
        c
        for c in clusters_of_mvv
        if c[0].vertex_type in (VertexType.signal, VertexType.pin)
    ]
    return clusters_of_elec_mvv


def generate_net_name(net: NetType, occupied_names: Optional[Iterable[str]] = None) -> str:
    lca, rel_name = resolve_rel_path_sections(net)
    if rel_name is None:
        # final fallback - slap a UUID on it and call it a day
        name = f"{lca.ref}-{generate_hash_name(net)[:6]}"
        return name

    for i in range(1000):
        candidate_name = f"{lca.ref}-{rel_name[0][-1]}"
        if i:
            candidate_name += f"-{i}"
        if occupied_names is None:
            return candidate_name
        if candidate_name not in occupied_names:
            return candidate_name
    else:
        raise ValueError(f"Too many nets with the sanme name {candidate_name}")


def find_net_names(model: Model) -> Dict[str, NetType]:
    nets = find_nets(model)
    names = {}
    for net in nets:
        names[generate_net_name(net, names.keys())] = net
    return names
