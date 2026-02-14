//! Custom test runner that accepts --test-filter at runtime.
//! Based on the default zig test runner's mainTerminal().
const std = @import("std");
const builtin = @import("builtin");
const testing = std.testing;

pub const std_options: std.Options = .{
    .logFn = log,
};

var log_err_count: usize = 0;
var is_fuzz_test: bool = undefined;

pub fn main() void {
    @disableInstrumentation();

    var filter: ?[]const u8 = null;

    var args = std.process.args();
    _ = args.next(); // skip argv[0]
    while (args.next()) |arg| {
        if (std.mem.eql(u8, arg, "--test-filter")) {
            filter = args.next() orelse @panic("--test-filter requires an argument");
        }
        // silently ignore other args (--seed, --cache-dir, etc.)
    }

    const test_fn_list = builtin.test_functions;
    var ok_count: usize = 0;
    var skip_count: usize = 0;
    var fail_count: usize = 0;
    var filtered_count: usize = 0;

    const root_node = if (builtin.fuzz) std.Progress.Node.none else std.Progress.start(.{
        .root_name = "Test",
        .estimated_total_items = test_fn_list.len,
    });
    const have_tty = std.io.getStdErr().isTty();

    var leaks: usize = 0;
    for (test_fn_list, 0..) |test_fn, i| {
        if (filter) |f| {
            if (!std.mem.containsAtLeast(u8, test_fn.name, 1, f)) {
                filtered_count += 1;
                continue;
            }
        }

        testing.allocator_instance = .{};
        defer {
            if (testing.allocator_instance.deinit() == .leak) {
                leaks += 1;
            }
        }
        testing.log_level = .warn;

        const test_node = root_node.start(test_fn.name, 0);
        if (!have_tty) {
            std.debug.print("{d}/{d} {s}...", .{ i + 1, test_fn_list.len, test_fn.name });
        }
        is_fuzz_test = false;
        if (test_fn.func()) |_| {
            ok_count += 1;
            test_node.end();
            if (!have_tty) std.debug.print("OK\n", .{});
        } else |err| switch (err) {
            error.SkipZigTest => {
                skip_count += 1;
                if (have_tty) {
                    std.debug.print("{d}/{d} {s}...SKIP\n", .{ i + 1, test_fn_list.len, test_fn.name });
                } else {
                    std.debug.print("SKIP\n", .{});
                }
                test_node.end();
            },
            else => {
                fail_count += 1;
                if (have_tty) {
                    std.debug.print("{d}/{d} {s}...FAIL ({s})\n", .{
                        i + 1, test_fn_list.len, test_fn.name, @errorName(err),
                    });
                } else {
                    std.debug.print("FAIL ({s})\n", .{@errorName(err)});
                }
                if (@errorReturnTrace()) |trace| {
                    std.debug.dumpStackTrace(trace.*);
                }
                test_node.end();
            },
        }
    }
    root_node.end();

    const ran = ok_count + skip_count + fail_count;
    if (ran == 0 and filter != null) {
        std.debug.print("0 tests matched filter.\n", .{});
        std.process.exit(1);
    }
    if (fail_count == 0 and leaks == 0 and log_err_count == 0) {
        std.debug.print("All {d} tests passed", .{ok_count});
        if (skip_count > 0) std.debug.print(" ({d} skipped)", .{skip_count});
        if (filtered_count > 0) std.debug.print(" ({d} filtered)", .{filtered_count});
        std.debug.print(".\n", .{});
    } else {
        std.debug.print("{d} passed; {d} skipped; {d} failed.\n", .{ ok_count, skip_count, fail_count });
        if (leaks != 0) std.debug.print("{d} tests leaked memory.\n", .{leaks});
        if (log_err_count != 0) std.debug.print("{d} errors were logged.\n", .{log_err_count});
        std.process.exit(1);
    }
}

pub fn log(
    comptime message_level: std.log.Level,
    comptime scope: @Type(.enum_literal),
    comptime format: []const u8,
    args: anytype,
) void {
    @disableInstrumentation();
    if (@intFromEnum(message_level) <= @intFromEnum(std.log.Level.err)) {
        log_err_count +|= 1;
    }
    if (@intFromEnum(message_level) <= @intFromEnum(testing.log_level)) {
        std.debug.print(
            "[" ++ @tagName(scope) ++ "] (" ++ @tagName(message_level) ++ "): " ++ format ++ "\n",
            args,
        );
    }
}
