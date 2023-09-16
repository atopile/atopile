from typing import Any

from atopile.model.accessors import ModelVertexView
from atopile.model.model import EdgeType, VertexType


class Empty:
    """
    Representes an empty field - eg. soemthing that's in one side of the diff and not the other.
    """


EMPTY = Empty()


FragPath = tuple[str]
EdgeFragPath = tuple[FragPath, FragPath]

NodeRep = dict[FragPath, VertexType]
ConnectionRep = dict[EdgeFragPath, EdgeType]
DataRep = dict[FragPath, Any]

NodeDelta = dict[FragPath, VertexType | EMPTY]
ConnectionDelta = dict[EdgeFragPath, EdgeType | EMPTY]
DataDelta = dict[FragPath, Any]


class FragRep:
    def __init__(self) -> None:
        self.node: NodeRep = {}
        self.connection: ConnectionRep = {}
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
            for connection in child.get_adjacents("in", list(EdgeType)):
                # FIXME: does this work only on connections to internal things
                # the issuue at the moment is that the frag rep eg. ("path", "to", "something")
                # is currently only designed to represent something in the scope of the diff being made - not the whole project
                # this means practically speaking it's impossible with this current scheme to apply stuff like class information
                # since the class isn't defined inside the class here
                # 1. I can translate these to be full paths instead?
                # 2. We could use full paths instead
                # 3. We could rebuild the model to add UIDs to all the elements

                # 1. seems best to me as of now
                # need to move the creation of relative paths from this function (and keep whole paths) to the application
                # the application will need to match the first N elements of the frag path against the application object's path (len == N elements)
                # if it matches, remove it and reapply the new object's path, else use original abs path
                #####
                #####
                #####
                if connection.path in relative_frag_paths:
                    # FIXME: this needs to be converted to
                    frag_rep.connection.add(
                        (relative_frag_paths[connection.path], child_frag_path)
                    )

            for connection in child.get_adjacents("out", list(EdgeType)):
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
            delta.node[deleted_data] = EMPTY

        # diff connections
        for new_conn in b.connection - a.connection:
            delta.connection[new_conn] = True

        for deleted_conn in a.connection - b.connection:
            delta.connection[deleted_conn] = EMPTY

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
    def combine(cls, first: "Delta", second: "Delta") -> "Delta":
        """
        Like a dict.update, but for Delta objects.
        Cleans up possible path conflicts
        """
        new_delta = cls()

        for delta in (first, second):
            new_delta.node.update(delta.node)
            new_delta.connection.update(delta.connection)
            new_delta.data.update(delta.data)

        for k in new_delta.data:
            if k in new_delta.node:
                del new_delta.data[k]

        return new_delta

    def apply_to(self, target: ModelVertexView) -> None:
        # apply node delta
        # by addressing teh shortest paths first we can make sure upstream nodes exist
        for rel_frag_path in sorted(self.node.keys(), key=len):
            node_delta = self.node[rel_frag_path]
            if node_delta == EMPTY:
                raise NotImplementedError(
                    "Deleting things isn't currently implemented - because I'm not sure how'd you'd get there."
                )
            # FIXME: hacky string manipulation of paths
            part_of_path = ".".join([target.path, *rel_frag_path[:-1]])
            target.model.new_vertex(node_delta, rel_frag_path[-1], part_of_path)

        # apply connections
        for connection_from_to, connection_delta in self.connection.items():
            connection_from, connection_to = connection_from_to
            if connection_delta == EMPTY:
                raise NotImplementedError(
                    "Deleting things isn't currently implemented - because I'm not sure how'd you'd get there."
                )
            # FIXME: more hacky string manipulation of paths
            connection_from_path = ".".join([target.path, *connection_from])
            connection_to_path = ".".join([target.path, *connection_to])
            target.model.new_edge(
                EdgeType.connects_to, connection_from_path, connection_to_path
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
