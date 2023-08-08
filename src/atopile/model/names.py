from typing import Iterable, Optional

from atopile.model.accessors import (
    ModelVertexView,
    lowest_common_ancestor_with_ancestor_ids,
)
from atopile.model.model import VertexType
from atopile.model.utils import generate_uid_from_path

# specifically a list of Signal and Pin vertices

PATH_SEPERATOR = "."

def resolve_rel_path_sections(all_electrical_verticies: Iterable[ModelVertexView]) -> tuple[ModelVertexView, Optional[list[list[str]]]]:
    if not all_electrical_verticies:
        raise ValueError("No verticies provided")

    lca, rel_anc_ids = lowest_common_ancestor_with_ancestor_ids(
        all_electrical_verticies
    )

    # descend down, checking for signals as we go
    rel_by_depth: dict[int, list[ModelVertexView]] = {}
    for electrical_vertex, rel_ids in zip(all_electrical_verticies, rel_anc_ids):
        if electrical_vertex.vertex_type != VertexType.signal:
            continue
        depth = len(rel_ids)
        rel_path_sections = [ModelVertexView(electrical_vertex.model, i).ref for i in rel_ids] + [electrical_vertex.ref]
        rel_by_depth.setdefault(depth, []).append(rel_path_sections)

    if rel_by_depth:
        min_depth = min(rel_by_depth.keys())
        return lca, rel_by_depth[min_depth]

    return lca, None


def generate_hash_name(all_electrical_verticies: Iterable[ModelVertexView]) -> str:
    return generate_uid_from_path(
        "".join(sorted(ev.ref for ev in all_electrical_verticies))
    )


def resolve_rel_name(all_electrical_verticies: Iterable[ModelVertexView]) -> tuple[ModelVertexView, str]:
    lca, rel_path_sections = resolve_rel_path_sections(all_electrical_verticies)

    # we're going to name the net <module-path>.<signal-name>
    # if there are multiple signals, we'll name it <module-path>.<signal-name1>-<signal-name2>
    if rel_path_sections is not None:
        rel_paths = [PATH_SEPERATOR.join(rel_path_section) for rel_path_section in rel_path_sections]
        rel_name = "-".join(sorted(signal_name for signal_name in rel_paths))
        return lca, rel_name

    # final fallback - slap a UUID on it and call it a day
    vertex_names_uuidd = generate_hash_name(all_electrical_verticies)[:6]
    return lca, vertex_names_uuidd


def resolve_abs_name(all_electrical_verticies: Iterable[ModelVertexView]) -> tuple[ModelVertexView, str]:
    lca, rel_name = resolve_rel_name(all_electrical_verticies)
    if lca.vertex_type == VertexType.file:
        # FIXME: paths need a rework, this is cruddy
        return lca, lca.ref + ":" + rel_name
    return lca, lca.path + PATH_SEPERATOR + rel_name
