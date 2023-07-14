from typing import Dict, Iterable, List

from atopile.model.accessors import ModelVertexView
from atopile.model.model import Model, EdgeType, VertexType
from atopile.model.names import resolve_abs_name


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


def find_net_names(model: Model) -> Dict[str, NetType]:
    nets = find_nets(model)
    return {resolve_abs_name(n)[1]: n for n in nets}
