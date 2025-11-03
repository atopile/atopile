const graph_mod = @import("graph");
const pointer_mod = @import("pointer.zig");

const graph = graph_mod.graph;
const GraphView = graph.GraphView;
const BoundNodeReference = graph.BoundNodeReference;
const EdgePointer = pointer_mod.EdgePointer;

const LinkerError = error{ TypeReferenceNotInGraph, TargetTypeNotInGraph };

pub const Linker = struct {
    pub const Error = LinkerError;

    pub fn link_type_reference(g: *GraphView, type_reference: BoundNodeReference, target_type: BoundNodeReference) Error!void {
        if (type_reference.g != g) {
            return Error.TypeReferenceNotInGraph;
        }

        if (target_type.g != g) {
            return Error.TargetTypeNotInGraph;
        }

        _ = EdgePointer.point_to(type_reference, target_type.node, "resolved", null);
    }
};
