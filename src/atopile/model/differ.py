from typing import Any, Type

from atopile.model.accessors import ModelVertexView, mvvs_to_path
from atopile.model.model import EdgeType, VertexType

FragPath = tuple[str]
EdgeFragPath = tuple[FragPath, FragPath]

NodeRep = dict[FragPath, VertexType]
ConnectionRep = set[EdgeFragPath]
DataRep = dict[FragPath, Any]


class Empty:
    """
    Representes an empty field - eg. soemthing that's in one side of the diff and not the other.
    """


NodeDelta = dict[FragPath, VertexType | Type[Empty]]
ConnectionDelta = dict[EdgeFragPath, bool]
DataDelta = dict[FragPath, Any]


class FragRep:
    def __init__(self) -> None:
        self.node: NodeRep = {}
        self.connection: ConnectionRep = set()
        self.data: DataRep = {}

    @classmethod
    def from_mvv(cls, root: ModelVertexView) -> "FragRep":
        frag_rep = cls()
        children = root.get_descendants(list(VertexType))
        # cache this because we'll use it a bit
        relative_frag_paths: dict[ModelVertexView, FragPath] = {
            k.path: tuple(mvv.ref for mvv in root.relative_mvv_path(k))
            for k in children
        }
        relative_frag_paths[root.path] = ()

        for child in [root] + children:
            # node rep
            child_frag_path = relative_frag_paths[child.path]
            if child != root:
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

            # connection rep
            for connection in child.get_adjacents("in", EdgeType.connects_to):
                if connection.path in relative_frag_paths:
                    frag_rep.connection.add(
                        (relative_frag_paths[connection.path], child_frag_path)
                    )
            for connection in child.get_adjacents("out", EdgeType.connects_to):
                if connection.path in relative_frag_paths:
                    frag_rep.connection.add(
                        (child_frag_path, relative_frag_paths[connection.path])
                    )

        return frag_rep


class Delta:
    def __init__(self) -> None:
        self.node: NodeDelta = {}
        self.connection: ConnectionDelta = {}
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
            delta.node[deleted_data] = Empty

        # diff connections
        for new_conn in b.connection - a.connection:
            delta.connection[new_conn] = True

        for deleted_conn in a.connection - b.connection:
            delta.connection[deleted_conn] = Empty

        # diff data
        a_data = set(a.data.keys())
        b_data = set(b.data.keys())

        for common_data in a_data & b_data:
            if a.data[common_data] != b.data[common_data]:
                delta.data[common_data] = b.data[common_data]

        for new_data in b_data - a_data:
            delta.data[new_data] = b.data[new_data]

        for deleted_data in a_data - b_data:
            delta.data[deleted_data] = Empty

        return delta

    def update(self, other: "Delta") -> None:
        """
        Like a dict.update, but for Delta objects.
        Cleans up possible path conflicts
        """
        self.node.update(other.node)
        self.connection.update(other.connection)
        self.data.update(other.data)

        for k in self.data:
            if k in self.node:
                del self.data[k]

    def apply_to(self, target: ModelVertexView) -> None:
        # apply node delta
        # by addressing teh shortest paths first we can make sure upstream nodes exist
        for rel_frag_path in sorted(self.node.keys(), key=len):
            node_delta = self.node[rel_frag_path]
            if node_delta == Empty:
                raise NotImplementedError("Deleting things isn't currently implemented - because I'm not sure how'd you'd get there.")
            # FIXME: hacky string manipulation of paths
            part_of_path = ".".join([target.path, *rel_frag_path[:-1]])
            target.model.new_vertex(node_delta, rel_frag_path[-1], part_of_path)

        # apply connections
        for connection_from_to, connection_delta in self.connection.items():
            connection_from, connection_to = connection_from_to
            if connection_delta == Empty:
                raise NotImplementedError("Deleting things isn't currently implemented - because I'm not sure how'd you'd get there.")
            # FIXME: more hacky string manipulation of paths
            connection_from_path = ".".join([target.path, *connection_from])
            connection_to_path = ".".join([target.path, *connection_to])
            target.model.new_edge(EdgeType.connects_to, connection_from_path, connection_to_path)

        # apply data updates
        for candidate_data_path, data_value in self.data.items():
            data_node = target
            data_path = list(candidate_data_path)
            for data_path_frag in candidate_data_path:
                for candidate_date_node in data_node.get_adjacents("in", EdgeType.part_of):
                    if candidate_date_node.ref == data_path_frag:
                        data_path.pop(0)
                        data_node = candidate_date_node
                        break
                else:
                    break

            data_dict = data_node.data
            for data_path_sec in data_path[:-1]:
                data_dict = data_dict.setdefault(data_path_sec, {})
            if data_value == Empty:
                if data_path[-1] in data_dict:
                    del data_dict[data_path[-1]]
            else:
                data_dict[data_path[-1]] = data_value
