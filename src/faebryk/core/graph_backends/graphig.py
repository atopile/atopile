# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


# class GraphIG[T](Graph[T, ig.Graph]):
#     # Notes:
#     # - union is slow
#     # - add_edge is slowish
#
#     def __init__(self):
#         super().__init__(ig.Graph(vertex_attrs={"name": "name"}))
#
#     @property
#     def node_cnt(self) -> int:
#         return len(self().vs)
#
#     @property
#     def edge_cnt(self) -> int:
#         return len(self().es)
#
#     def v(self, obj: T, add=False) -> ig.Vertex:
#         out = str(id(obj))
#         if add and out not in self().vs["name"]:
#             return self().add_vertex(name=out, obj=obj)
#         return out
#
#     def add_edge(self, from_obj: T, to_obj: T, link: "Link") -> ig.Edge:
#         from_v = self.v(from_obj, True)
#         to_v = self.v(to_obj, True)
#         return self().add_edge(from_v, to_v, link=link)
#
#     def is_connected(self, from_obj: T, to_obj: T) -> "Link | None":
#         try:
#             v_from = self().vs.find(name=self.v(from_obj))
#             v_to = self().vs.find(name=self.v(to_obj))
#         except ValueError:
#             return None
#         edge = self().es.select(_source=v_from, _target=v_to)
#         if not edge:
#             return None
#
#         return edge[0]["link"]
#
#     def get_edges(self, obj: T) -> Mapping[T, "Link"]:
#         edges = self().es.select(_source=self.v(obj))
#         return {self().vs[edge.target]["name"]: edge["link"] for edge in edges}
#
#     @staticmethod
#     def _union(rep: ig.Graph, old: ig.Graph):
#         return rep + old  # faster, but correct?
