const graph_mod = @import("graph");
const std = @import("std");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const Edge = graph.Edge;
const EdgeReference = graph.EdgeReference;
const GraphView = graph.GraphView;
const NodeReference = graph.NodeReference;
const BoundEdgeReference = graph.BoundEdgeReference;
const DynamicAttributes = graph.DynamicAttributes;
const DynamicAttributesReference = graph.DynamicAttributesReference;
const str = graph.str;

pub const EdgeCreationAttributes = struct {
    edge_type: Edge.EdgeType,
    directional: ?bool,
    name: ?str,
    order: u7 = 0,
    edge_specific: ?u16 = null,
    dynamic: DynamicAttributes,

    pub fn apply_to(self: *const @This(), edge: EdgeReference) void {
        edge.set_attribute_edge_type(self.edge_type);
        if (self.directional) |d| {
            edge.set_attribute_directional(d);
        }
        edge.set_attribute_name(self.name);
        edge.set_order(self.order);
        if (self.edge_specific) |edge_specific| {
            edge.set_edge_specific(edge_specific);
        }
        edge.copy_dynamic_attributes_into(&self.dynamic);
    }

    pub fn create_edge(self: *const @This(), source: NodeReference, target: NodeReference) EdgeReference {
        const edge = EdgeReference.init(source, target, self.edge_type);
        self.apply_to(edge);
        return edge;
    }

    pub fn insert_edge(self: *const @This(), g: *GraphView, source: NodeReference, target: NodeReference) GraphView.InsertEdgeError!BoundEdgeReference {
        const edge = self.create_edge(source, target);
        return g.insert_edge(edge);
    }

    pub fn get_tid(self: *const @This()) Edge.EdgeType {
        return self.edge_type;
    }
};
