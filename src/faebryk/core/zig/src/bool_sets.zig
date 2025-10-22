const std = @import("std");

pub const Bool_Set = struct {
    elements: std.ArrayList(bool),

    pub fn init(allocator: std.mem.Allocator, elements: []const bool) !Bool_Set {
        var out = Bool_Set{
            .elements = try std.ArrayList(bool).initCapacity(allocator, elements.len),
        };
        try out.elements.appendSlice(elements);
        return out;
    }

    pub fn deinit(self: *const Bool_Set) void {
        self.elements.deinit();
    }

    pub fn op_not(self: *const Bool_Set) !Bool_Set {
        var out = Bool_Set{
            .elements = try std.ArrayList(bool).initCapacity(self.elements.allocator, self.elements.items.len),
        };
        for (self.elements.items) |element| {
            try out.elements.append(!element);
        }
        return out;
    }

    pub fn op_and(self: *const Bool_Set, other: *const Bool_Set) !Bool_Set {
        var out = Bool_Set{
            .elements = try std.ArrayList(bool).initCapacity(self.elements.allocator, self.elements.items.len * other.elements.items.len),
        };
        for (self.elements.items) |element| {
            for (other.elements.items) |other_element| {
                try out.elements.append(element and other_element);
            }
        }
        return out;
    }

    pub fn op_or(self: *const Bool_Set, other: *const Bool_Set) !Bool_Set {
        var out = Bool_Set{
            .elements = try std.ArrayList(bool).initCapacity(self.elements.allocator, self.elements.items.len * other.elements.items.len),
        };
        for (self.elements.items) |element| {
            for (other.elements.items) |other_element| {
                try out.elements.append(element or other_element);
            }
        }
        return out;
    }
};

test "Bool_Set.init" {
    const allocator = std.testing.allocator;
    const elements = [_]bool{ true, false, true };
    const set = try Bool_Set.init(allocator, &elements);
    defer set.deinit();

    try std.testing.expectEqual(set.elements.items.len, elements.len);
    try std.testing.expectEqual(set.elements.items[0], true);
    try std.testing.expectEqual(set.elements.items[1], false);
    try std.testing.expectEqual(set.elements.items[2], true);
}

test "Bool_Set.op_not" {
    const allocator = std.testing.allocator;
    const elements = [_]bool{ true, true, false };
    const set = try Bool_Set.init(allocator, &elements);
    defer set.deinit();

    const result = try set.op_not();
    defer result.deinit();

    try std.testing.expectEqual(set.elements.items.len, result.elements.items.len);
    try std.testing.expectEqual(result.elements.items[0], false);
    try std.testing.expectEqual(result.elements.items[1], false);
    try std.testing.expectEqual(result.elements.items[2], true);
}

test "Bool_Set.op_and" {
    const allocator = std.testing.allocator;
    const lhs_elements = [_]bool{ true, false };
    const rhs_elements = [_]bool{ false, true };

    const lhs = try Bool_Set.init(allocator, &lhs_elements);
    const rhs = try Bool_Set.init(allocator, &rhs_elements);

    defer lhs.deinit();
    defer rhs.deinit();

    const result = try lhs.op_and(&rhs);
    defer result.deinit();

    try std.testing.expectEqual(result.elements.items.len, lhs_elements.len * rhs_elements.len);
    try std.testing.expectEqual(result.elements.items[0], false);
    try std.testing.expectEqual(result.elements.items[1], true);
    try std.testing.expectEqual(result.elements.items[2], false);
    try std.testing.expectEqual(result.elements.items[3], false);
}

test "Bool_Set.op_or" {
    const allocator = std.testing.allocator;
    const lhs_elements = [_]bool{ true, false };
    const rhs_elements = [_]bool{ false, true };

    const lhs = try Bool_Set.init(allocator, &lhs_elements);
    const rhs = try Bool_Set.init(allocator, &rhs_elements);

    defer lhs.deinit();
    defer rhs.deinit();

    const result = try lhs.op_or(&rhs);
    defer result.deinit();

    try std.testing.expectEqual(result.elements.items.len, lhs_elements.len * rhs_elements.len);
    try std.testing.expectEqual(result.elements.items[0], true);
    try std.testing.expectEqual(result.elements.items[1], true);
    try std.testing.expectEqual(result.elements.items[2], false);
    try std.testing.expectEqual(result.elements.items[3], true);
}
