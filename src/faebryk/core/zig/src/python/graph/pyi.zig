const std = @import("std");
const graph = @import("graph");
const pyzig = @import("pyzig");

fn generateModuleStub(allocator: std.mem.Allocator, comptime name: []const u8, comptime T: type, output_dir: []const u8) !void {
    var generator = pyzig.pyi.PyiGenerator.init(allocator);
    defer generator.deinit();

    const content = try generator.generate(T);
    defer allocator.free(content);

    var final_content = std.ArrayList(u8).init(allocator);
    defer final_content.deinit();

    if (std.mem.eql(u8, name, "composition")) {
        const marker = "from enum import Enum  # noqa: F401\n\n";
        if (std.mem.indexOf(u8, content, marker)) |idx| {
            try final_content.appendSlice(content[0 .. idx + marker.len]);
            try final_content.appendSlice(
                "from .graph import BoundEdgeReference, BoundNodeReference, Edge, Node\n\n",
            );
            try final_content.appendSlice(content[idx + marker.len ..]);
        } else {
            try final_content.appendSlice(content);
        }
    } else {
        try final_content.appendSlice(content);
    }

    // Create the output file path
    var path_buf: [256]u8 = undefined;
    const file_path = try std.fmt.bufPrint(&path_buf, "{s}/{s}.pyi", .{ output_dir, name });

    // Write the content to the file
    const file = try std.fs.cwd().createFile(file_path, .{});
    defer file.close();

    try file.writeAll(final_content.items);
    try file.writeAll("\n");
}

/// Copy the pyi file from __file__.parent/manual/<name>.pyi to the output directory
fn manualModuleStub(allocator: std.mem.Allocator, comptime name: []const u8, comptime T: type, output_dir: []const u8, source_dir: []const u8) !void {
    _ = T;
    const manual_dir = try std.fs.path.join(allocator, &.{ source_dir, "manual" });
    defer allocator.free(manual_dir);
    const manual_file_path = try std.fs.path.join(allocator, &.{ manual_dir, name ++ ".pyi" });
    defer allocator.free(manual_file_path);
    const manual_file = try std.fs.cwd().openFile(manual_file_path, .{});
    defer manual_file.close();
    const manual_content = try manual_file.readToEndAlloc(allocator, 1024 * 1024);
    defer allocator.free(manual_content);
    var path_buf: [256]u8 = undefined;
    const file_path = try std.fmt.bufPrint(&path_buf, "{s}/{s}.pyi", .{ output_dir, name });
    const file = try std.fs.cwd().createFile(file_path, .{});
    defer file.close();
    try file.writeAll(manual_content);
    try file.writeAll("\n");
}

pub fn make_pyi(allocator: std.mem.Allocator, output_dir: []const u8, source_dir: []const u8) !void {
    // Ensure output directory exists
    std.fs.cwd().makePath(output_dir) catch |err| {
        if (err != error.PathAlreadyExists) return err;
    };

    //try generateModuleStub(allocator, "graph", graph.graph, output_dir);
    //try generateModuleStub(allocator, "composition", graph.composition, output_dir);

    try manualModuleStub(allocator, "graph", graph.graph, output_dir, source_dir);
    try manualModuleStub(allocator, "composition", graph.composition, output_dir, source_dir);
}
