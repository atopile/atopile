const std = @import("std");
const pyzig = @import("pyzig");
const sexp = @import("sexp");

fn generateModuleStub(allocator: std.mem.Allocator, comptime name: []const u8, comptime T: type, comptime typename: []const u8, output_dir: []const u8) !void {
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

    const import_root = "from faebryk.core.zig.gen.sexp";

    // Hack: Footprint imports some types from pcb
    if (std.mem.eql(u8, name, "footprint")) {
        try file.writeAll(import_root);
        try file.writeAll(".pcb import Xyr, Property, FpText, Line, Arc, Circle, Rect, Polygon, Pad, Model, E_Attr\n");
    } else if (std.mem.eql(u8, name, "symbol")) {
        try file.writeAll(import_root);
        try file.writeAll(".schematic import Symbol\n");
    } else if (std.mem.eql(u8, name, "schematic")) {
        try file.writeAll(import_root);
        try file.writeAll(".pcb import Xy, Xyr, Wh, Effects\n");
    } else if (std.mem.eql(u8, name, "footprint_v5")) {
        try file.writeAll(import_root);
        try file.writeAll(".pcb import FpText, ModelXyz, Pad, Polygon, Property, Xy, Xyr, E_Attr\n");
        try file.writeAll(import_root);
        try file.writeAll(".footprint import Tags\n");
    } else if (std.mem.eql(u8, name, "symbol_v6")) {
        try file.writeAll(import_root);
        try file.writeAll(".pcb import Xy\n");
        try file.writeAll(import_root);
        try file.writeAll(".schematic import Polyline, Rect, SymbolPin, Fill, Stroke, Property, PinNames, Arc\n");
    }
    try file.writeAll(content);

    // Add module-specific functions if needed
    try file.writeAll("\n");
    try file.writeAll("# Module-level functions\n");
    try file.writeAll(std.fmt.comptimePrint("def loads(data: str) -> {s}: ...\n", .{typename}));
    try file.writeAll(std.fmt.comptimePrint("def dumps(obj: {s}) -> str: ...\n", .{typename}));
}

pub fn make_pyi(allocator: std.mem.Allocator, output_dir: []const u8, source_dir: []const u8) !void {
    _ = source_dir;
    // Ensure output directory exists
    std.fs.cwd().makePath(output_dir) catch |err| {
        if (err != error.PathAlreadyExists) return err;
    };

    // Generate stub for each module - comptime unrolled
    try generateModuleStub(allocator, "pcb", sexp.kicad.pcb, "PcbFile", output_dir);
    try generateModuleStub(allocator, "footprint", sexp.kicad.footprint, "FootprintFile", output_dir);
    try generateModuleStub(allocator, "netlist", sexp.kicad.netlist, "NetlistFile", output_dir);
    try generateModuleStub(allocator, "fp_lib_table", sexp.kicad.fp_lib_table, "FpLibTableFile", output_dir);
    try generateModuleStub(allocator, "symbol", sexp.kicad.symbol, "SymbolFile", output_dir);
    try generateModuleStub(allocator, "schematic", sexp.kicad.schematic, "SchematicFile", output_dir);

    try generateModuleStub(allocator, "footprint_v5", sexp.kicad.v5.footprint, "FootprintFile", output_dir);
    try generateModuleStub(allocator, "symbol_v6", sexp.kicad.v6.symbol, "SymbolFile", output_dir);
    // Add more modules as needed
}
