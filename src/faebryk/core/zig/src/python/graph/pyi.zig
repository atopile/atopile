const std = @import("std");
const graph = @import("graph");
const pyzig = @import("pyzig");

fn generateModuleStub(allocator: std.mem.Allocator, comptime name: []const u8, comptime T: type, output_dir: []const u8) !void {
    var generator = pyzig.pyi.PyiGenerator.init(allocator);
    defer generator.deinit();

    const content = try generator.generate(T);
    defer allocator.free(content);

    // Create the output file path
    var path_buf: [256]u8 = undefined;
    const file_path = try std.fmt.bufPrint(&path_buf, "{s}/{s}.pyi", .{ output_dir, name });

    // Write the content to the file
    const file = try std.fs.cwd().createFile(file_path, .{});
    defer file.close();

    try file.writeAll(content);
    try file.writeAll("\n");
}

pub fn make_pyi(allocator: std.mem.Allocator, output_dir: []const u8) !void {
    // Ensure output directory exists
    std.fs.cwd().makePath(output_dir) catch |err| {
        if (err != error.PathAlreadyExists) return err;
    };

    try generateModuleStub(allocator, "graph", graph.graph, output_dir);
}
