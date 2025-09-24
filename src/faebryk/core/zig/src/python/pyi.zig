const std = @import("std");

fn make_pyi(allocator: std.mem.Allocator, output_dir: []const u8, comptime T: type, comptime name: []const u8, source_dir: []const u8) !void {
    const out = try std.fs.path.join(allocator, &.{ output_dir, name });
    defer allocator.free(out);
    const source_nested = try std.fs.path.join(allocator, &.{ source_dir, name });
    defer allocator.free(source_nested);
    try T.make_pyi(allocator, out, source_nested);
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const args = try std.process.argsAlloc(allocator);
    defer std.process.argsFree(allocator, args);
    if (args.len < 3) {
        std.debug.print("Usage: {s} <output_dir> <source_dir>\n", .{args[0]});
        return error.InvalidUsage;
    }

    const root_output_dir = args[1];
    const output_dir = try std.fs.path.join(allocator, &.{ root_output_dir, "gen" });
    defer allocator.free(output_dir);

    const source_dir = args[2];

    // Ensure output directory exists
    std.fs.cwd().makePath(root_output_dir) catch |err| {
        if (err != error.PathAlreadyExists) return err;
    };

    // TODO: instead of giving responsibility to modules just directly use pyigenerator here
    // But first need to make pyigenerator better to do more fancy stuff

    const sexp_pyi = @import("sexp/pyi.zig");
    try make_pyi(allocator, output_dir, sexp_pyi, "sexp", source_dir);
    const graph_pyi = @import("graph/pyi.zig");
    try make_pyi(allocator, output_dir, graph_pyi, "graph", source_dir);
}
