const std = @import("std");
const sexp = @import("sexp");

pub fn main() !void {
    var arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    // Test parsing a single layer without wrapper
    const layer_str_no_wrapper = "(0 \"F.Cu\" signal)";
    
    const tokens1 = try sexp.tokenizer.tokenize(allocator, layer_str_no_wrapper);
    defer allocator.free(tokens1);
    
    var sexp_ast = try sexp.ast.parse(allocator, tokens1);
    defer sexp_ast.deinit(allocator);
    
    const layer = sexp.structure.decode(sexp.kicad.pcb.Layer, allocator, sexp_ast) catch |err| {
        std.debug.print("Error parsing layer: {}\n", .{err});
        if (sexp.structure.getErrorContext()) |ctx| {
            std.debug.print("{}\n", .{ctx});
        }
        return err;
    };
    
    std.debug.print("Layer number: {}\n", .{layer.number});
    std.debug.print("Layer name: {s}\n", .{layer.name});
    std.debug.print("Layer type: {s}\n", .{layer.type});
    
    // Now test the PCB hex numbers issue
    std.debug.print("\n--- Testing hex number tokenization ---\n", .{});
    const hex_test = "(layerselection 0x00000000_00000000_55555555_5755f5ff)";
    
    const hex_tokens = try sexp.tokenizer.tokenize(allocator, hex_test);
    defer allocator.free(hex_tokens);
    
    std.debug.print("Tokens from hex test:\n", .{});
    for (hex_tokens) |token| {
        switch (token.type) {
            .symbol => std.debug.print("  Symbol: '{s}'\n", .{token.value}),
            .number => std.debug.print("  Number: '{s}'\n", .{token.value}),
            .string => std.debug.print("  String: \"{s}\"\n", .{token.value}),
            else => {},
        }
    }
}