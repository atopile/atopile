//! STEP File Parser
//!
//! A Zig-native parser for ISO 10303-21 (STEP Part 21) files.
//! Focused on extracting geometric and topological data from 3D component models.
//!
//! ## Example Usage
//!
//! ```zig
//! const step = @import("step/lib.zig");
//!
//! // Parse a STEP file
//! const content = try std.fs.cwd().readFileAlloc(allocator, "model.step", 100 * 1024 * 1024);
//! defer allocator.free(content);
//!
//! var model = try step.loads(allocator, content);
//! defer model.deinit();
//!
//! // Query geometric properties
//! if (step.queries.boundingBox(&model)) |bbox| {
//!     std.debug.print("Size: {d:.2} x {d:.2} x {d:.2} mm\n", .{
//!         bbox.size().x, bbox.size().y, bbox.size().z
//!     });
//! }
//!
//! // Find cylinder features (potential pins)
//! const cylinders = try step.queries.findCylinders(allocator, &model, 0.1, 0.6);
//! defer allocator.free(cylinders);
//!
//! // Round-trip: dump back to string
//! const output = try step.dumps(allocator, &model);
//! defer allocator.free(output);
//! ```

const std = @import("std");

pub const tokenizer = @import("tokenizer.zig");
pub const ast = @import("ast.zig");
pub const parser = @import("parser.zig");
pub const writer = @import("writer.zig");
pub const queries = @import("queries.zig");

// Re-export commonly used types
pub const Token = tokenizer.Token;
pub const TokenType = tokenizer.TokenType;
pub const TokenLocation = tokenizer.TokenLocation;

pub const Parameter = ast.Parameter;
pub const TypedParameter = ast.TypedParameter;
pub const Entity = ast.Entity;
pub const Header = ast.Header;
pub const StepFile = ast.StepFile;

pub const Point3D = queries.Point3D;
pub const Direction3D = queries.Direction3D;
pub const Axis2Placement3D = queries.Axis2Placement3D;
pub const BoundingBox = queries.BoundingBox;
pub const Cylinder = queries.Cylinder;

// Error types
pub const TokenizeError = tokenizer.TokenizeError;
pub const ParseError = parser.ParseError;
pub const WriteError = writer.WriteError;

/// Parse a STEP file from a string
pub fn loads(allocator: std.mem.Allocator, content: []const u8) (TokenizeError || ParseError)!StepFile {
    const tokens = try tokenizer.tokenize(allocator, content);
    defer allocator.free(tokens);

    return try parser.parse(allocator, tokens);
}

/// Serialize a StepFile to a string
pub fn dumps(allocator: std.mem.Allocator, step_file: *const StepFile) WriteError![]u8 {
    return writer.write(allocator, step_file);
}

/// Load a STEP file from disk
pub fn loadFile(allocator: std.mem.Allocator, path: []const u8) !StepFile {
    const content = try std.fs.cwd().readFileAlloc(allocator, path, 100 * 1024 * 1024);
    defer allocator.free(content);

    return try loads(allocator, content);
}

/// Save a StepFile to disk
pub fn saveFile(allocator: std.mem.Allocator, step_file: *const StepFile, path: []const u8) !void {
    const content = try dumps(allocator, step_file);
    defer allocator.free(content);

    const file = try std.fs.cwd().createFile(path, .{});
    defer file.close();

    try file.writeAll(content);
}

// Tests
test "round trip simple entity" {
    const allocator = std.testing.allocator;
    const input =
        \\ISO-10303-21;
        \\HEADER;
        \\FILE_DESCRIPTION (( 'Test' ), '1' );
        \\FILE_NAME ('test.step', '2024-01-01', ( '' ), ( '' ), '', '', '' );
        \\FILE_SCHEMA (( 'AUTOMOTIVE_DESIGN' ));
        \\ENDSEC;
        \\DATA;
        \\#1 = CARTESIAN_POINT ( 'NONE', ( 0.0, 1.0, 2.0 ) ) ;
        \\#2 = DIRECTION ( 'NONE', ( 0.0, 0.0, 1.0 ) ) ;
        \\ENDSEC;
        \\END-ISO-10303-21;
    ;

    var step_file = try loads(allocator, input);
    defer step_file.deinit();

    try std.testing.expectEqual(@as(usize, 2), step_file.entities.count());

    // Check CARTESIAN_POINT
    const point = step_file.getEntity(1).?;
    try std.testing.expectEqualStrings("CARTESIAN_POINT", point.type_name);

    // Check DIRECTION
    const dir = step_file.getEntity(2).?;
    try std.testing.expectEqualStrings("DIRECTION", dir.type_name);

    // Round-trip
    const output = try dumps(allocator, &step_file);
    defer allocator.free(output);

    // Parse the output
    var step_file2 = try loads(allocator, output);
    defer step_file2.deinit();

    try std.testing.expectEqual(@as(usize, 2), step_file2.entities.count());
}

test "bounding box calculation" {
    const allocator = std.testing.allocator;
    const input =
        \\ISO-10303-21;
        \\HEADER;
        \\FILE_DESCRIPTION (( 'Test' ), '1' );
        \\FILE_NAME ('test.step', '2024-01-01', ( '' ), ( '' ), '', '', '' );
        \\FILE_SCHEMA (( 'AUTOMOTIVE_DESIGN' ));
        \\ENDSEC;
        \\DATA;
        \\#1 = CARTESIAN_POINT ( 'NONE', ( 0.0, 0.0, 0.0 ) ) ;
        \\#2 = CARTESIAN_POINT ( 'NONE', ( 10.0, 20.0, 30.0 ) ) ;
        \\#3 = CARTESIAN_POINT ( 'NONE', ( -5.0, 10.0, 15.0 ) ) ;
        \\ENDSEC;
        \\END-ISO-10303-21;
    ;

    var step_file = try loads(allocator, input);
    defer step_file.deinit();

    const bbox = queries.boundingBox(&step_file).?;

    try std.testing.expectApproxEqAbs(@as(f64, -5.0), bbox.min.x, 0.001);
    try std.testing.expectApproxEqAbs(@as(f64, 0.0), bbox.min.y, 0.001);
    try std.testing.expectApproxEqAbs(@as(f64, 0.0), bbox.min.z, 0.001);
    try std.testing.expectApproxEqAbs(@as(f64, 10.0), bbox.max.x, 0.001);
    try std.testing.expectApproxEqAbs(@as(f64, 20.0), bbox.max.y, 0.001);
    try std.testing.expectApproxEqAbs(@as(f64, 30.0), bbox.max.z, 0.001);
}
