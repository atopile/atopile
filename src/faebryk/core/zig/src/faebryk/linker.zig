const graph_mod = @import("graph");
const pointer_mod = @import("pointer.zig");

const graph = graph_mod.graph;
const GraphView = graph.GraphView;
const BoundNodeReference = graph.BoundNodeReference;
const EdgePointer = pointer_mod.EdgePointer;

const LinkerError = error{ TypeReferenceNotInGraph, TargetTypeNotInGraph };

pub const Linker = struct {
    pub const Error = LinkerError;

    const resolved_identifier = "resolved";

    pub fn link_type_reference(g: *GraphView, type_reference: BoundNodeReference, target_type: BoundNodeReference) Error!void {
        if (type_reference.g != g) {
            return Error.TypeReferenceNotInGraph;
        }

        if (target_type.g != g) {
            return Error.TargetTypeNotInGraph;
        }

        _ = EdgePointer.point_to(type_reference, target_type.node, resolved_identifier, null);
    }

    pub fn try_get_resolved_type(type_reference: BoundNodeReference) ?BoundNodeReference {
        return EdgePointer.get_pointed_node_by_identifier(type_reference, resolved_identifier);
    }
};
