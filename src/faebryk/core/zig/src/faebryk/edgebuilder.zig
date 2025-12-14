const graph_mod = @import("graph");
const std = @import("std");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const Edge = graph.Edge;
const EdgeReference = graph.EdgeReference;
const GraphView = graph.GraphView;
const NodeReference = graph.NodeReference;
const BoundEdgeReference = graph.BoundEdgeReference;
const str = graph.str;

pub const EdgeCreationAttributes = struct {
    edge_type: Edge.EdgeType,
    directional: ?bool,
    name: ?str,
    dynamic: graph.DynamicAttributes,

    pub fn apply_to(self: *const @This(), edge: EdgeReference) void {
        edge.attributes.edge_type = self.edge_type;
        edge.attributes.directional = self.directional;
        edge.attributes.name = self.name;
        self.dynamic.copy_into(&edge.attributes.dynamic);
    }

    pub fn create_edge(self: *const @This(), source: NodeReference, target: NodeReference) EdgeReference {
        const edge = Edge.init(source, target, self.edge_type);
        self.apply_to(edge);
        return edge;
    }

    pub fn insert_edge(self: *const @This(), g: *GraphView, source: NodeReference, target: NodeReference) BoundEdgeReference {
        const edge = self.create_edge(source, target);
        return g.insert_edge(edge);
    }

    pub fn get_tid(self: *const @This()) Edge.EdgeType {
        return self.edge_type;
    }

    pub fn deinit(self: *@This()) void {
        self.dynamic.deinit();
    }
};
