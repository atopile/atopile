from functools import partial
from itertools import chain
from typing import Any

from atopile.utils import shield_to_none
from atopile.model.accessors import ModelVertexView, NodeNotFoundError
from atopile.model.model import EdgeType, VertexType


class Empty:
    """
    Representes an empty field - eg. soemthing that's in one side of the diff and not the other.
    """


EMPTY = Empty()


class Root:
    """
    Representes the root of the model.
    """


ROOT = Root()


FragPath = tuple[str | Root]
EdgeFragPath = tuple[FragPath, FragPath]

NodeRep = dict[FragPath, VertexType]
EdgeRep = dict[EdgeFragPath, EdgeType]
DataRep = dict[FragPath, Any]

NodeDelta = dict[FragPath, VertexType | Empty]
EdgeDelta = dict[EdgeFragPath, EdgeType | Empty]
DataDelta = dict[FragPath, Any]


def get_root_path(mvv: ModelVertexView) -> FragPath:
    return (ROOT,) + tuple(a.ref for a in mvv.get_ancestors()[::-1])


class FragRep:
    def __init__(self) -> None:
        self.node: NodeRep = {}
        self.edge: EdgeRep = {}
        self.data: DataRep = {}

    @classmethod
    def from_mvv(cls, root: ModelVertexView) -> "FragRep":
        frag_rep = cls()
        children = root.get_descendants(list(VertexType))
        # cache this because we'll use it a bit
        relative_frag_paths: dict[str, FragPath] = {
            k.path: tuple(mvv.ref for mvv in root.relative_mvv_path(k))
            for k in children
        }
        relative_frag_paths[root.path] = ()

        for child in [root] + children:
            # node rep
            child_frag_path = relative_frag_paths[child.path]
            frag_rep.node[child_frag_path] = child.vertex_type

            # data rep
            def _recurse_data(data_rel_path: FragPath, data: dict):
                for k, v in data.items():
                    sub_path = data_rel_path + (k,)

                    # we ignore data that has the same path as a node
                    if sub_path in relative_frag_paths.values():
                        continue

                    if isinstance(v, dict):
                        _recurse_data(sub_path, v)
                    else:
                        frag_rep.data[sub_path] = v

            _recurse_data(child_frag_path, child.data)

            # edge rep
            _adj = partial(
                child.get_adjacents_with_edge_types, edge_type=list(EdgeType)
            )
            for edge_type, from_mvv, to_mvv, mode in chain(
                ((edge_type, other, child, "in") for edge_type, other in _adj("in")),
                ((edge_type, child, other, "out") for edge_type, other in _adj("out")),
            ):
                if from_mvv.path in relative_frag_paths:
                    from_frag = relative_frag_paths[from_mvv.path]
                else:
                    from_frag = get_root_path(from_mvv)

                if to_mvv.path in relative_frag_paths:
                    to_frag = relative_frag_paths[to_mvv.path]
                else:
                    to_frag = get_root_path(to_mvv)

                edge_rep = (from_frag, to_frag)
                frag_rep.edge[edge_rep] = edge_type

        return frag_rep


class Delta:
    def __init__(self) -> None:
        self.node: NodeDelta = {}
        self.edge: EdgeDelta = {}
        self.data: DataDelta = {}

    @classmethod
    def diff(cls, _a: ModelVertexView, _b: ModelVertexView) -> "Delta":
        delta = cls()

        a = FragRep.from_mvv(_a)
        b = FragRep.from_mvv(_b)

        # diff nodes
        a_nodes = set(a.node.keys())
        b_nodes = set(b.node.keys())

        for common_node in a_nodes & b_nodes:
            if a.node[common_node] != b.node[common_node]:
                delta.node[common_node] = b.node[common_node]

        for new_data in b_nodes - a_nodes:
            delta.node[new_data] = b.node[new_data]

        for deleted_data in a_nodes - b_nodes:
            delta.node[deleted_data] = EMPTY

        # diff edges
        a_conn = set(a.edge.keys())
        b_conn = set(b.edge.keys())

        for common_conn in a_conn & b_conn:
            if a.edge[common_conn] != b.edge[common_conn]:
                delta.edge[common_conn] = b.edge[common_conn]

        for new_conn in b_conn - a_conn:
            delta.edge[new_conn] = b.edge[new_conn]

        for deleted_conn in a_conn - b_conn:
            delta.edge[deleted_conn] = EMPTY

        # diff data
        a_data = set(a.data.keys())
        b_data = set(b.data.keys())

        for common_data in a_data & b_data:
            if a.data[common_data] != b.data[common_data]:
                delta.data[common_data] = b.data[common_data]

        for new_data in b_data - a_data:
            delta.data[new_data] = b.data[new_data]

        for deleted_data in a_data - b_data:
            delta.data[deleted_data] = EMPTY

        return delta

    @classmethod
    def combine_union(cls, first: "Delta", second: "Delta") -> "Delta":
        """
        Like a dict.update, but for Delta objects.
        Cleans up possible path conflicts
        """
        new_delta = cls()

        for delta in (first, second):
            new_delta.node.update(delta.node)
            new_delta.edge.update(delta.edge)
            new_delta.data.update(delta.data)

        for k in new_delta.data:
            if k in new_delta.node:
                del new_delta.data[k]

        return new_delta

    @classmethod
    def combine_diff(cls, potitive: "Delta", negative: "Delta") -> "Delta":
        """
        Like a dict.update, but for Delta objects.
        Cleans up possible path conflicts
        """
        new_delta = cls()

        for new_dict, pos_dict, neg_dict in (
            (new_delta.node, potitive.node, negative.node),
            (new_delta.edge, potitive.edge, negative.edge),
            (new_delta.data, potitive.data, negative.data),
        ):
            diff_keys = set(pos_dict.keys()) - set(neg_dict.keys())
            for k in diff_keys:
                new_dict[k] = pos_dict[k]

        for k in new_delta.data:
            if k in new_delta.node:
                del new_delta.data[k]

        return new_delta

    def apply_to(self, target: ModelVertexView) -> None:
        """
        An extremely problematic and painful partially written implementation of applying a delta to a model.
        FIXME: it only really works for ADDING things
        FIXME: it can deal with modifications to node types and data, but no other characteristics
        """
        # FIXME: KILLME: hacky string manipulation of paths
        def _make_path(path: FragPath) -> str:
            if path and path[0] == ROOT:
                # we're just gonna make the gross assumption
                # that the first thing after the root is a file
                if len(path) == 2:
                    return path[1]
                return path[1] + ":" + ".".join(path[2:])
            return ".".join([target.path, *path])

        # apply node delta
        # by addressing the shortest paths first we can make sure upstream nodes exist
        for rel_frag_path in sorted(self.node.keys(), key=len):
            node_type = self.node[rel_frag_path]
            if node_type == EMPTY:
                raise NotImplementedError(
                    "Deleting things isn't currently implemented - because I'm not sure how'd you'd get there."
                )
            if existing_node := shield_to_none(NodeNotFoundError, ModelVertexView.from_path, target.model, _make_path(rel_frag_path)):
                existing_node.vertex_type = node_type
                continue
            part_of_path = _make_path(rel_frag_path[:-1])
            target.model.new_vertex(node_type, rel_frag_path[-1], part_of_path)

        # apply edges
        for edge_from_to, edge_type in self.edge.items():
            edge_from, edge_to = edge_from_to
            if edge_type == EMPTY:
                raise NotImplementedError(
                    "Deleting things isn't currently implemented - because I'm not sure how'd you'd get there."
                    f"Failed to remove {str(edge_type)} from {edge_from} to {edge_to}"
                )
            edge_from_path = _make_path(edge_from)
            edge_to_path = _make_path(edge_to)
            target.model.new_edge(
                edge_type, edge_from_path, edge_to_path
            )

        # apply data updates
        for candidate_data_path, data_value in self.data.items():
            data_node = target
            data_path = list(candidate_data_path)
            for data_path_frag in candidate_data_path:
                for candidate_date_node in data_node.get_adjacents(
                    "in", EdgeType.part_of
                ):
                    if candidate_date_node.ref == data_path_frag:
                        data_path.pop(0)
                        data_node = candidate_date_node
                        break
                else:
                    break

            data_dict = data_node.data
            for data_path_sec in data_path[:-1]:
                data_dict = data_dict.setdefault(data_path_sec, {})
            if data_value == EMPTY:
                if data_path[-1] in data_dict:
                    del data_dict[data_path[-1]]
            else:
                data_dict[data_path[-1]] = data_value
