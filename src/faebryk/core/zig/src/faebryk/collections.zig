const std = @import("std");
const graph_mod = @import("graph");
const graph = graph_mod.graph;
const visitor = graph_mod.visitor;
const faebryk = @import("faebryk");
const fabll = @import("fabll.zig");
const str = []const u8;

fn edge_factory(comptime identifier: ?str, comptime index: ?u15) type {
    return struct {
        pub fn build() faebryk.edgebuilder.EdgeCreationAttributes {
            return faebryk.pointer.EdgePointer.build(identifier, index);
        }
    };
}

fn append_type(comptime items: []const type, comptime item: type) []const type {
    return comptime blk: {
        var out: [items.len + 1]type = undefined;
        for (items, 0..) |existing, i| out[i] = existing;
        out[items.len] = item;
        const finalized = out;
        break :blk &finalized;
    };
}

pub const Pointer = struct {
    node: fabll.Node,

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

    pub fn MakeEdge(comptime pointer_ref: fabll.RefPath, comptime elem_ref: fabll.RefPath) type {
        return fabll.MakeDependantEdge(pointer_ref, elem_ref, edge_factory(null, null));
    }

    pub fn try_deref(self: @This()) ?graph.BoundNodeReference {
        return faebryk.pointer.EdgePointer.get_referenced_node_from_node(self.node.instance);
    }

    pub fn deref(self: @This()) graph.BoundNodeReference {
        return self.try_deref() orelse @panic("Pointer is not pointing to a node");
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

pub fn PointerOf(comptime T: type) type {
    return struct {
        node: fabll.Node,

        pub fn MakeChild() type {
            return fabll.Node.MakeChild(@This());
        }

        pub fn MakeEdge(comptime pointer_ref: fabll.RefPath, comptime elem_ref: fabll.RefPath) type {
            return Pointer.MakeEdge(pointer_ref, elem_ref);
        }

        pub fn try_deref(self: @This()) ?T {
            if ((Pointer{ .node = self.node }).try_deref()) |node| {
                return fabll.Node.bind_instance(T, node);
            }
            return null;
        }

        pub fn deref(self: @This()) T {
            return self.try_deref() orelse @panic("Pointer is not pointing to a node");
        }

        pub fn point(self: @This(), target: T) void {
            (Pointer{ .node = self.node }).point(target.node.instance);
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

pub const PointerSequence = struct {
    node: fabll.Node,

    const elem_identifier = "e";

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

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
            allocator: std.mem.Allocator,
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

        var ctx: Ctx = .{
            .allocator = allocator,
            .out = std.ArrayList(IndexedNode).init(allocator),
        };
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

pub fn PointerSequenceOf(comptime T: type) type {
    return struct {
        node: fabll.Node,

        pub fn MakeChild() type {
            return fabll.Node.MakeChild(@This());
        }

        pub fn MakeEdge(comptime seq_ref: fabll.RefPath, comptime elem_ref: fabll.RefPath, comptime index: u15) type {
            return PointerSequence.MakeEdge(seq_ref, elem_ref, index);
        }

        pub fn MakeEdges(comptime seq_ref: fabll.RefPath, comptime elem_refs: []const fabll.RefPath) []const type {
            return PointerSequence.MakeEdges(seq_ref, elem_refs);
        }

        pub fn append(self: @This(), elems: []const T) void {
            var raw = std.ArrayList(graph.BoundNodeReference).init(std.heap.page_allocator);
            defer raw.deinit();
            for (elems) |elem| {
                raw.append(elem.node.instance) catch @panic("OOM");
            }
            (PointerSequence{ .node = self.node }).append(raw.items);
        }

        pub fn as_list(self: @This(), allocator: std.mem.Allocator) ![]T {
            const raw = try (PointerSequence{ .node = self.node }).as_list(allocator);
            defer allocator.free(raw);
            var out = try allocator.alloc(T, raw.len);
            for (raw, 0..) |node, i| {
                out[i] = fabll.Node.bind_instance(T, node);
            }
            return out;
        }
    };
}

pub const PointerSet = struct {
    node: fabll.Node,

    const elem_identifier = "e";

    pub fn MakeChild() type {
        return fabll.Node.MakeChild(@This());
    }

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

    pub fn MakeChildWithElems(comptime elems: []const fabll.RefPath) type {
        var out = MakeChild();
        inline for (elems) |elem| {
            out = out.add_dependant(MakeEdge(fabll.RefPath.owner_child(), elem));
        }
        return out;
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
        const seq: PointerSequence = .{ .node = self.node };
        return seq.as_list(allocator);
    }
};

pub fn PointerSetOf(comptime T: type) type {
    return struct {
        node: fabll.Node,

        pub fn MakeChild() type {
            return fabll.Node.MakeChild(@This());
        }

        pub fn MakeEdge(comptime set_ref: fabll.RefPath, comptime elem_ref: fabll.RefPath) type {
            return PointerSet.MakeEdge(set_ref, elem_ref);
        }

        pub fn MakeEdges(comptime set_ref: fabll.RefPath, comptime elem_refs: []const fabll.RefPath) []const type {
            return PointerSet.MakeEdges(set_ref, elem_refs);
        }

        pub fn append(self: @This(), elems: []const T) void {
            var raw = std.ArrayList(graph.BoundNodeReference).init(std.heap.page_allocator);
            defer raw.deinit();
            for (elems) |elem| {
                raw.append(elem.node.instance) catch @panic("OOM");
            }
            (PointerSet{ .node = self.node }).append(raw.items);
        }

        pub fn as_list(self: @This(), allocator: std.mem.Allocator) ![]T {
            const raw = try (PointerSet{ .node = self.node }).as_list(allocator);
            defer allocator.free(raw);
            var out = try allocator.alloc(T, raw.len);
            for (raw, 0..) |node, i| {
                out[i] = fabll.Node.bind_instance(T, node);
            }
            return out;
        }
    };
}

test "collections pointer basics" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const Holder = struct {
        node: fabll.Node,
        ptr: Pointer.MakeChild(),
        target: fabll.Node.MakeChild(struct { node: fabll.Node }),
    };

    const holder = fabll.Node.bind_typegraph(Holder, &tg).create_instance(&g);
    const target = holder.target.get().node.instance;

    holder.ptr.get().point(target);
    const got = holder.ptr.get().deref();
    try std.testing.expect(got.node.is_same(target.node));
}

test "collections pointer set append dedup" {
    var g = graph.GraphView.init(std.testing.allocator);
    defer g.deinit();
    var tg = faebryk.typegraph.TypeGraph.init(&g);

    const Leaf = struct { node: fabll.Node };
    const Holder = struct {
        node: fabll.Node,
        set: PointerSet.MakeChild(),
        a: fabll.Node.MakeChild(Leaf),
        b: fabll.Node.MakeChild(Leaf),
    };

    const holder = fabll.Node.bind_typegraph(Holder, &tg).create_instance(&g);
    const a = holder.a.get().node.instance;
    const b = holder.b.get().node.instance;

    holder.set.get().append(&.{ a, b, a });
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
