const graph_mod = @import("graph");
const std = @import("std");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const Edge = graph.Edge;
const EdgeReference = graph.EdgeReference;
const str = graph.str;

pub const EdgeCreationAttributes = struct {
    edge_type: Edge.EdgeType,
    directional: ?bool,
    name: ?str,
    dynamic: ?graph.DynamicAttributes,

    pub fn apply_to(self: *const @This(), edge: EdgeReference) void {
        edge.attributes.edge_type = self.edge_type;
        edge.attributes.directional = self.directional;
        edge.attributes.name = self.name;
        if (self.dynamic) |dynamic| {
            dynamic.copy_into(&edge.attributes.dynamic);
        }
    }
};
