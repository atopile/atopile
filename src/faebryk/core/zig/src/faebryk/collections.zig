const std = @import("std");
const graph_mod = @import("graph");
const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const faebryk = @import("faebryk");
const fabll = @import("fabll.zig");
const str = []const u8;

fn child_identifier_of(comptime ChildFieldType: type) str {
    if (!@hasDecl(ChildFieldType, "ChildType") or !@hasDecl(ChildFieldType, "Identifier")) {
        @compileError("expected ChildField(...) type");
    }
    return ChildFieldType.Identifier orelse
        @compileError("child field must have explicit Identifier for typed edge helpers");
}

fn child_refpath_of(comptime ChildFieldType: type) fabll.RefPath {
    return fabll.RefPath.child_identifier(child_identifier_of(ChildFieldType));
}

fn edge_factory(comptime identifier: ?str, comptime index: ?u15) type {
    return struct {
        pub fn build() faebryk.edgebuilder.EdgeCreationAttributes {
            return faebryk.pointer.EdgePointer.build(identifier, index);
        }
    };
}

const RawPointer = struct {
    node: fabll.Node,

    pub fn MakeEdge(comptime pointer_ref: fabll.RefPath, comptime elem_ref: fabll.RefPath) type {
        return fabll.MakeDependantEdge(pointer_ref, elem_ref, edge_factory(null, null));
    }

    pub fn try_deref(self: @This()) ?graph.BoundNodeReference {
        return faebryk.pointer.EdgePointer.get_referenced_node_from_node(self.node.instance);
    }

    pub fn point(self: @This(), target: graph.BoundNodeReference) void {
        _ = faebryk.pointer.EdgePointer.point_to(self.node.instance, target.node, null, null) catch
            @panic("failed to create pointer edge");
    }

    pub fn as_list(self: @This(), allocator: std.mem.Allocator) ![]graph.BoundNodeReference {
        if (self.try_deref()) |n| {
            var out = try allocator.alloc(graph.BoundNodeReference, 1);
            out[0] = n;
            return out;
        }
        return allocator.alloc(graph.BoundNodeReference, 0);
    }
};

const RawPointerSequence = struct {
    node: fabll.Node,

    const elem_identifier = "e";

    pub fn MakeEdge(comptime seq_ref: fabll.RefPath, comptime elem_ref: fabll.RefPath, comptime index: u15) type {
        return fabll.MakeDependantEdge(seq_ref, elem_ref, edge_factory(elem_identifier, index));
    }

    pub fn MakeEdges(comptime seq_ref: fabll.RefPath, comptime elem_refs: []const fabll.RefPath) []const type {
        return comptime blk: {
            var out: [elem_refs.len]type = undefined;
            for (elem_refs, 0..) |elem_ref, i| {
                out[i] = MakeEdge(seq_ref, elem_ref, @as(u15, @intCast(i)));
            }
            const finalized = out;
            break :blk &finalized;
        };
    }

    pub fn append(self: @This(), elems: []const graph.BoundNodeReference) void {
        var cur_len: usize = 0;
        {
            const cur = self.as_list(std.heap.page_allocator) catch @panic("OOM");
            defer std.heap.page_allocator.free(cur);
            cur_len = cur.len;
        }

        for (elems, 0..) |elem, i| {
            const idx: u15 = @intCast(cur_len + i);
            _ = faebryk.pointer.EdgePointer.point_to(self.node.instance, elem.node, elem_identifier, idx) catch
                @panic("failed to append pointer sequence element");
        }
    }

    const IndexedNode = struct {
        index: u15,
        node: graph.BoundNodeReference,
    };

    pub fn as_list(self: @This(), allocator: std.mem.Allocator) ![]graph.BoundNodeReference {
        const Ctx = struct {
            out: std.ArrayList(IndexedNode),

            fn visit(ctx_ptr: *anyopaque, be: graph.BoundEdgeReference) visitor.VisitResult(void) {
                const ctx: *@This() = @ptrCast(@alignCast(ctx_ptr));
                const target = be.g.bind(faebryk.pointer.EdgePointer.get_referenced_node(be.edge));
                const idx = faebryk.pointer.EdgePointer.get_index(be.edge) orelse 0;
                ctx.out.append(.{ .index = idx, .node = target }) catch
                    return visitor.VisitResult(void){ .ERROR = error.OutOfMemory };
                return visitor.VisitResult(void){ .CONTINUE = {} };
            }
        };

        var ctx: Ctx = .{ .out = std.ArrayList(IndexedNode).init(allocator) };
        errdefer ctx.out.deinit();

        switch (faebryk.pointer.EdgePointer.visit_pointed_edges_with_identifier(self.node.instance, elem_identifier, void, &ctx, Ctx.visit)) {
            .ERROR => |err| return err,
            else => {},
        }

        std.sort.block(IndexedNode, ctx.out.items, {}, struct {
            fn lessThan(_: void, lhs: IndexedNode, rhs: IndexedNode) bool {
                return lhs.index < rhs.index;
            }
        }.lessThan);

        var out = try allocator.alloc(graph.BoundNodeReference, ctx.out.items.len);
        for (ctx.out.items, 0..) |item, i| out[i] = item.node;
        ctx.out.deinit();
        return out;
    }
};

const RawPointerSet = struct {
    node: fabll.Node,

    const elem_identifier = "e";

    pub fn MakeEdge(comptime set_ref: fabll.RefPath, comptime elem_ref: fabll.RefPath) type {
        return fabll.MakeDependantEdge(set_ref, elem_ref, edge_factory(elem_identifier, null));
    }

    pub fn MakeEdges(comptime set_ref: fabll.RefPath, comptime elem_refs: []const fabll.RefPath) []const type {
        return comptime blk: {
            var out: [elem_refs.len]type = undefined;
            for (elem_refs, 0..) |elem_ref, i| {
                out[i] = MakeEdge(set_ref, elem_ref);
            }
            const finalized = out;
            break :blk &finalized;
        };
    }

    pub fn append(self: @This(), elems: []const graph.BoundNodeReference) void {
        var by_uuid = std.AutoHashMap(u32, graph.BoundNodeReference).init(std.heap.page_allocator);
        defer by_uuid.deinit();

        for (elems) |elem| {
            by_uuid.put(elem.node.get_uuid(), elem) catch @panic("OOM");
        }

        const cur = self.as_list(std.heap.page_allocator) catch @panic("OOM");
        defer std.heap.page_allocator.free(cur);
        const cur_len = cur.len;

        for (cur) |elem| {
            _ = by_uuid.remove(elem.node.get_uuid());
        }

        var it = by_uuid.iterator();
        var i: usize = 0;
        while (it.next()) |entry| : (i += 1) {
            const idx: u15 = @intCast(cur_len + i);
            _ = faebryk.pointer.EdgePointer.point_to(self.node.instance, entry.value_ptr.*.node, elem_identifier, idx) catch
                @panic("failed to append pointer set element");
        }
    }

    pub fn as_list(self: @This(), allocator: std.mem.Allocator) ![]graph.BoundNodeReference {
        return (RawPointerSequence{ .node = self.node }).as_list(allocator);
    }
};

pub fn PointerOf(comptime T: type) type {
    return struct {
        node: fabll.Node,

        pub fn MakeChild() type {
            return fabll.Node.MakeChild(@This());
        }

        pub fn MakeEdge(comptime pointer_ref: fabll.RefPath, comptime elem_ref: fabll.RefPath) type {
            return RawPointer.MakeEdge(pointer_ref, elem_ref);
        }

        pub fn MakeEdgeToField(comptime pointer_ref: fabll.RefPath, comptime field: type) type {
            return MakeEdge(pointer_ref, child_refpath_of(field));
        }

        pub fn MakeEdgeForField(comptime out: type, comptime pointer_ref: fabll.RefPath, comptime field: type) type {
            return out
                .add_dependant(MakeEdgeToField(pointer_ref, field))
                .add_dependant_before(field);
        }

        pub fn try_deref(self: @This()) ?T {
            if ((RawPointer{ .node = self.node }).try_deref()) |node| {
                return fabll.Node.bind_instance(T, node);
            }
            return null;
        }

        pub fn deref(self: @This()) T {
            return self.try_deref() orelse @panic("Pointer is not pointing to a node");
        }

        pub fn point(self: @This(), target: T) void {
            (RawPointer{ .node = self.node }).point(target.node.instance);
        }

        pub fn as_list(self: @This(), allocator: std.mem.Allocator) ![]T {
            if (self.try_deref()) |n| {
                var out = try allocator.alloc(T, 1);
                out[0] = n;
                return out;
            }
            return allocator.alloc(T, 0);
        }
    };
}

pub fn PointerSequenceOf(comptime T: type) type {
    return struct {
        node: fabll.Node,

        pub fn MakeChild() type {
            return fabll.Node.MakeChild(@This());
        }

        pub fn MakeEdge(comptime seq_ref: fabll.RefPath, comptime elem_ref: fabll.RefPath, comptime index: u15) type {
            return RawPointerSequence.MakeEdge(seq_ref, elem_ref, index);
        }

        pub fn MakeEdgeToField(comptime seq_ref: fabll.RefPath, comptime field: type, comptime index: u15) type {
            return MakeEdge(seq_ref, child_refpath_of(field), index);
        }

        pub fn MakeEdges(comptime seq_ref: fabll.RefPath, comptime elem_refs: []const fabll.RefPath) []const type {
            return RawPointerSequence.MakeEdges(seq_ref, elem_refs);
        }

        pub fn append(self: @This(), elems: []const T) void {
            var raw = std.ArrayList(graph.BoundNodeReference).init(std.heap.page_allocator);
            defer raw.deinit();
            for (elems) |elem| raw.append(elem.node.instance) catch @panic("OOM");
            (RawPointerSequence{ .node = self.node }).append(raw.items);
        }

        pub fn as_list(self: @This(), allocator: std.mem.Allocator) ![]T {
            const raw = try (RawPointerSequence{ .node = self.node }).as_list(allocator);
            defer allocator.free(raw);
            var out = try allocator.alloc(T, raw.len);
            for (raw, 0..) |node, i| out[i] = fabll.Node.bind_instance(T, node);
            return out;
        }
    };
}

pub fn PointerSetOf(comptime T: type) type {
    return struct {
        node: fabll.Node,

        pub fn MakeChild() type {
            return fabll.Node.MakeChild(@This());
        }

        pub fn MakeEdge(comptime set_ref: fabll.RefPath, comptime elem_ref: fabll.RefPath) type {
            return RawPointerSet.MakeEdge(set_ref, elem_ref);
        }

        pub fn MakeEdgeToField(comptime set_ref: fabll.RefPath, comptime field: type) type {
            return MakeEdge(set_ref, child_refpath_of(field));
        }

        pub fn MakeEdgeForField(comptime out: type, comptime set_ref: fabll.RefPath, comptime field: type) type {
            return out
                .add_dependant(MakeEdgeToField(set_ref, field))
                .add_dependant_before(field);
        }

        pub fn MakeEdges(comptime set_ref: fabll.RefPath, comptime elem_refs: []const fabll.RefPath) []const type {
            return RawPointerSet.MakeEdges(set_ref, elem_refs);
        }

        pub fn append(self: @This(), elems: []const T) void {
            var raw = std.ArrayList(graph.BoundNodeReference).init(std.heap.page_allocator);
            defer raw.deinit();
            for (elems) |elem| raw.append(elem.node.instance) catch @panic("OOM");
            (RawPointerSet{ .node = self.node }).append(raw.items);
        }

        pub fn as_list(self: @This(), allocator: std.mem.Allocator) ![]T {
            const raw = try (RawPointerSet{ .node = self.node }).as_list(allocator);
            defer allocator.free(raw);
            var out = try allocator.alloc(T, raw.len);
            for (raw, 0..) |node, i| out[i] = fabll.Node.bind_instance(T, node);
            return out;
        }
    };
}

// TESTS ============================================================================================

test "collections pointer basics" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const Target = struct {
        node: fabll.Node,
    };
    const TypedPtr = PointerOf(Target);

    const Holder = struct {
        node: fabll.Node,
        ptr: TypedPtr.MakeChild(),
        target: fabll.Node.MakeChild(Target),
    };

    const holder = fabll.Node.bind_typegraph(Holder, &tg).create_instance(&g);
    const target = holder.target.get();

    holder.ptr.get().point(target);
    const got = holder.ptr.get().deref();
    try std.testing.expect(got.node.instance.node.is_same(target.node.instance.node));
}

test "collections pointer set append dedup" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const Leaf = struct { node: fabll.Node };
    const TypedSet = PointerSetOf(Leaf);

    const Holder = struct {
        node: fabll.Node,
        set: TypedSet.MakeChild(),
        a: fabll.Node.MakeChild(Leaf),
        b: fabll.Node.MakeChild(Leaf),
    };

    const holder = fabll.Node.bind_typegraph(Holder, &tg).create_instance(&g);
    holder.set.get().append(&.{ holder.a.get(), holder.b.get(), holder.a.get() });
    const vals = try holder.set.get().as_list(std.testing.allocator);
    defer std.testing.allocator.free(vals);
    try std.testing.expectEqual(@as(usize, 2), vals.len);
}

test "collections typed pointer set auto cast" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const Leaf = struct {
        node: fabll.Node,
        pub const Attributes = struct { v: i64 };
        pub fn MakeChild(comptime v: i64) type {
            return fabll.MakeChildWithTypedAttrs(@This(), .{ .v = v });
        }
        pub fn get(self: @This()) i64 {
            return fabll.get_typed_attributes(self).v;
        }
    };

    const LeafSet = PointerSetOf(Leaf);

    const Holder = struct {
        node: fabll.Node,
        set: LeafSet.MakeChild(),
        a: Leaf.MakeChild(1),
        b: Leaf.MakeChild(2),
    };

    const holder = fabll.Node.bind_typegraph(Holder, &tg).create_instance(&g);
    holder.set.get().append(&.{ holder.a.get(), holder.b.get(), holder.a.get() });
    const values = try holder.set.get().as_list(std.testing.allocator);
    defer std.testing.allocator.free(values);

    try std.testing.expectEqual(@as(usize, 2), values.len);
    try std.testing.expectEqual(@as(i64, 1), values[0].get());
    try std.testing.expectEqual(@as(i64, 2), values[1].get());
}

test "collections typed MakeEdgeForField helper" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const Target = struct {
        node: fabll.Node,
    };

    const TypedPtr = PointerOf(Target);
    const target_child = fabll.ChildField(Target, "target", &.{}, &.{}, &.{});

    const Holder = struct {
        node: fabll.Node,
        ptr: TypedPtr.MakeChild(),

        pub fn MakeChild() type {
            const out = fabll.Node.MakeChild(@This());
            return TypedPtr.MakeEdgeForField(
                out,
                .{
                    .segments = &.{
                        .{ .owner_child = {} },
                        .{ .child_identifier = "ptr" },
                    },
                },
                target_child,
            );
        }
    };

    const App = struct {
        node: fabll.Node,
        holder: Holder.MakeChild(),
    };

    const app = fabll.Node.bind_typegraph(App, &tg).create_instance(&g);
    const holder = app.holder.get();
    const pointed = holder.ptr.get().deref();
    const target = faebryk.composition.EdgeComposition.get_child_by_identifier(app.node.instance, "target") orelse
        @panic("missing target child");
    try std.testing.expect(pointed.node.instance.node.is_same(target.node));
}
