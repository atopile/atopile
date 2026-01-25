const graph_mod = @import("graph");
const std = @import("std");

const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const Node = graph.Node;
const NodeReference = graph.NodeReference;
const DynamicAttributes = graph.DynamicAttributes;
const str = graph.str;

pub const NodeCreationAttributes = struct {
    dynamic: DynamicAttributes,

    pub fn apply_to(self: *const @This(), node: NodeReference) void {
        node.copy_dynamic_attributes_into(&self.dynamic);
    }
};
