const std = @import("std");
const sexp = @import("sexp");

// Example: KiCad-style component definition
pub const Pin = struct {
    number: []const u8,
    name: []const u8,
    type: []const u8,

    pub const sexp_metadata = .{
        .number = .{ .positional = false },
        .name = .{ .positional = false },
        .type = .{ .positional = false },
    };
};

pub const Property = struct {
    name: []const u8,
    value: []const u8,

    pub const sexp_metadata = .{
        .name = .{ .positional = true },
        .value = .{ .positional = false },
    };
};

pub const Component = struct {
    name: []const u8,
    reference: []const u8,
    value: []const u8,
    footprint: ?[]const u8 = null,
    pins: []Pin = &.{},
    properties: []Property = &.{},

    pub const sexp_metadata = .{
        .name = .{ .positional = true },
        .reference = .{ .positional = false },
        .value = .{ .positional = false },
        .footprint = .{ .positional = false },
        .pins = .{ .positional = false, .multidict = true, .sexp_name = "pin" },
        .properties = .{ .positional = false, .multidict = true, .sexp_name = "property" },
    };
};

pub const Symbol = struct {
    symbol_name: []const u8,
    components: []Component = &.{},

    pub const sexp_metadata = .{
        .symbol_name = .{ .positional = true, .sexp_name = "symbol" },
        .components = .{ .positional = false, .multidict = true, .sexp_name = "component" },
    };
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Create example data
    var pins = try allocator.alloc(Pin, 2);
    defer allocator.free(pins);
    pins[0] = .{ .number = "1", .name = "VCC", .type = "power_in" };
    pins[1] = .{ .number = "2", .name = "GND", .type = "power_in" };

    var properties = try allocator.alloc(Property, 2);
    defer allocator.free(properties);
    properties[0] = .{ .name = "Reference", .value = "U1" };
    properties[1] = .{ .name = "Datasheet", .value = "https://example.com/datasheet.pdf" };

    var components = try allocator.alloc(Component, 1);
    defer allocator.free(components);
    components[0] = .{
        .name = "MCU",
        .reference = "U1",
        .value = "STM32F103",
        .footprint = "Package_QFP:LQFP-48_7x7mm_P0.5mm",
        .pins = pins,
        .properties = properties,
    };

    const symbol = Symbol{
        .symbol_name = "STM32F103_Symbol",
        .components = components,
    };

    // Encode to S-expression
    const encoded = try sexp.structure.dumps(symbol, allocator, "symbol", null);
    defer allocator.free(encoded);

    std.debug.print("Generated S-expression:\n{s}\n\n", .{encoded});

    // Parse it back
    const tokens = try sexp.tokenizer.tokenize(allocator, encoded);
    defer allocator.free(tokens); // No need for deinitTokens here since tokens point to encoded

    var sexp_ast = try sexp.ast.parse(allocator, tokens);
    defer sexp_ast.deinit(allocator);

    const decoded = try sexp.structure.loads(Symbol, allocator, .{ .sexp = sexp_ast }, "symbol");
    defer sexp.structure.free(Symbol, allocator, decoded);

    std.debug.print("\nDecoded symbol: {s}\n", .{decoded.symbol_name});
    std.debug.print("Components: {}\n", .{decoded.components.len});
    for (decoded.components) |comp| {
        std.debug.print("  - {s} ({s})\n", .{ comp.name, comp.value });
        std.debug.print("    Pins: {}\n", .{comp.pins.len});
        for (comp.pins) |pin| {
            std.debug.print("      - Pin {s}: {s} ({s})\n", .{ pin.number, pin.name, pin.type });
        }
    }
}
