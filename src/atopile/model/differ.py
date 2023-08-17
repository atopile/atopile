from typing import Any, Type

from atopile.model.accessors import ModelVertexView
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
