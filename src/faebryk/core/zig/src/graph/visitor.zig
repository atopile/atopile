pub fn VisitResult(comptime T: type) type {
    return union(enum) {
        OK: T, // Visitor found a result
        EXHAUSTED: void, // Visitor visited all elements
        CONTINUE: void, // Visitor should continue visiting
        STOP: void, // Visitor stopped
        ERROR: anyerror, // Visitor encountered an error
    };
}

test "visitor simple" {
    const std = @import("std");
    const Result = VisitResult(i32);

    const visitor_test = struct {
        fn visit(f: fn (i32) VisitResult(i32)) VisitResult(i32) {
            const to_be_visited = [_]i32{ 1, 2, 5, 4, 4 };
            for (to_be_visited) |val| {
                const result = f(val);
                switch (result) {
                    .OK => |ok| return Result{ .OK = ok },
                    .CONTINUE => {},
                    .STOP => return Result{ .STOP = {} },
                    .ERROR => |err| return Result{ .ERROR = err },
                    .EXHAUSTED => unreachable,
                }
            }
            return Result{ .EXHAUSTED = {} };
        }

        fn visitor(val: i32) VisitResult(i32) {
            if (val == 5) {
                return Result{ .OK = val };
            }
            return Result{ .CONTINUE = {} };
        }
    };

    const result = visitor_test.visit(visitor_test.visitor);

    try std.testing.expectEqual(Result{ .OK = 5 }, result);
}

test "visitor closure" {
    const std = @import("std");
    const Result = VisitResult(i32);

    const visitor_test = struct {
        fn visit(ctx: *anyopaque, f: fn (*anyopaque, i32) VisitResult(i32)) VisitResult(i32) {
            const to_be_visited = [_]i32{ 1, 2, 5, 4, 4 };
            for (to_be_visited) |val| {
                const result = f(ctx, val);
                switch (result) {
                    .OK => |ok| return Result{ .OK = ok },
                    .CONTINUE => {},
                    .STOP => return Result{ .STOP = {} },
                    .ERROR => |err| return Result{ .ERROR = err },
                    .EXHAUSTED => unreachable,
                }
            }
            return Result{ .EXHAUSTED = {} };
        }

        const Closure = struct {
            max_value: i32 = 0,

            fn visitor(ctx: *anyopaque, val: i32) VisitResult(i32) {
                const self: *@This() = @ptrCast(@alignCast(ctx));
                if (val > self.max_value) {
                    self.max_value = val;
                }
                return Result{ .CONTINUE = {} };
            }
        };
    };

    var closure: visitor_test.Closure = .{};
    const result = visitor_test.visit(&closure, visitor_test.Closure.visitor);

    try std.testing.expectEqual(Result{ .EXHAUSTED = {} }, result);
    try std.testing.expectEqual(5, closure.max_value);
}
