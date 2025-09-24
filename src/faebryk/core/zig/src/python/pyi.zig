const std = @import("std");
const sexp_pyi = @import("sexp/pyi.zig");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const args = try std.process.argsAlloc(allocator);
    defer std.process.argsFree(allocator, args);
    if (args.len < 2) {
        std.debug.print("Usage: {s} <output_dir>\n", .{args[0]});
        return error.InvalidUsage;
    }

    const root_output_dir = args[1];
    const output_dir = try std.fs.path.join(allocator, &.{ root_output_dir, "gen" });
    defer allocator.free(output_dir);

    // Ensure output directory exists
    std.fs.cwd().makePath(root_output_dir) catch |err| {
        if (err != error.PathAlreadyExists) return err;
    };

    const sexp_output_dir = try std.fs.path.join(allocator, &.{ output_dir, "sexp" });
    defer allocator.free(sexp_output_dir);
    try sexp_pyi.make_pyi(allocator, sexp_output_dir);
}
