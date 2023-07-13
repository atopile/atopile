from typing import Iterable

from atopile.model.accessors import (
    ModelVertexView,
    lowest_common_ancestor_with_ancestor_ids,
)
from atopile.model.model import VertexType
from atopile.model.utils import generate_uid_from_path

# specifically a list of Signal and Pin vertices

PATH_SEPERATOR = "."


def resolve_rel_name(all_electrical_verticies: Iterable[ModelVertexView]) -> tuple[ModelVertexView, str]:
    if not all_electrical_verticies:
        raise ValueError("No verticies provided")

    lca, rel_anc_ids = lowest_common_ancestor_with_ancestor_ids(
        all_electrical_verticies
    )

    # descend down, checking for signals as we go
    # we're going to name the net <module-path>.<signal-name>
    # if there are multiple signals, we'll name it <module-path>.<signal-name1>-<signal-name2>
    rel_by_depth: dict[int, list[ModelVertexView]] = {}
    for electrical_vertex, rel_ids in zip(all_electrical_verticies, rel_anc_ids):
        if electrical_vertex.vertex_type != VertexType.signal:
            continue
        depth = len(rel_ids)
        rel_path = PATH_SEPERATOR.join(
            [ModelVertexView(electrical_vertex.model, i).ref for i in rel_ids]
            + [electrical_vertex.ref]
        )
        rel_by_depth.setdefault(depth, []).append(rel_path)

    if rel_by_depth:
        min_depth = min(rel_by_depth.keys())
        rel_names = rel_by_depth[min_depth]
        rel_name = "-".join(sorted(signal_name for signal_name in rel_names))
        return lca, rel_name

    # final fallback - slap a UUID on it and call it a day
    vertex_names_uuidd = generate_uid_from_path(
        "".join(sorted(ev.ref for ev in all_electrical_verticies))
    )[:6]
    return lca, vertex_names_uuidd

def resolve_abs_name(all_electrical_verticies: Iterable[ModelVertexView]) -> tuple[ModelVertexView, str]:
    lca, rel_name = resolve_rel_name(all_electrical_verticies)
    if lca.vertex_type == VertexType.file:
        # FIXME: paths need a rework, this is cruddy
        return lca, lca.ref + ":" + rel_name
    return lca, lca.path + PATH_SEPERATOR + rel_name
