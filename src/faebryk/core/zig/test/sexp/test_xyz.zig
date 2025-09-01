const std = @import("std");
const sexp = @import("sexp");

pub fn main() !void {
    var arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    // Test parsing Xyz
    const xyz_sexp = "(xyz 1.0 2.0 3.0)";
    
    std.debug.print("Parsing Xyz: {s}\n", .{xyz_sexp});
    
    // Parse to tokens and AST
    const tokens = try sexp.tokenizer.tokenize(allocator, xyz_sexp);
    defer allocator.free(tokens);
    
    var sexp_ast = try sexp.ast.parse(allocator, tokens);
    defer sexp_ast.deinit(allocator);
    
    // Debug: print the AST structure
    std.debug.print("\nAST structure:\n", .{});
    if (sexp.ast.getList(sexp_ast)) |items| {
        std.debug.print("List has {} items:\n", .{items.len});
        for (items, 0..) |item, i| {
            std.debug.print("  Item {}: ", .{i});
            switch (item.value) {
                .symbol => |s| std.debug.print("Symbol '{s}'\n", .{s}),
                .number => |n| std.debug.print("Number {s}\n", .{n}),
                else => std.debug.print("Other\n", .{}),
            }
        }
    }
    
    // This should work - parsing with the wrapper symbol
    const xyz1 = sexp.structure.loads(sexp.kicad.pcb.Xyz, allocator, .{ .sexp = sexp_ast }, "xyz") catch |err| {
        sexp.structure.printError(xyz_sexp, err);
        std.debug.print("\nLet's try without the wrapper...\n", .{});
        
        // Try parsing just the values (simulate what happens in nested parsing)
        if (sexp.ast.getList(sexp_ast)) |items| {
            if (items.len >= 4) {
                // Create a new sexp with just the values
                const value_sexp = sexp.ast.SExp{
                    .value = .{ .list = items[1..] },
                    .location = null,
                };
                
                const xyz2 = sexp.structure.decode(sexp.kicad.pcb.Xyz, allocator, value_sexp) catch |err2| {
                    std.debug.print("Also failed without wrapper: {}\n", .{err2});
                    return err2;
                };
                
                std.debug.print("Success without wrapper! x={d}, y={d}, z={d}\n", .{xyz2.x, xyz2.y, xyz2.z});
                return;
            }
        }
        return err;
    };
    
    std.debug.print("\nSuccess with wrapper! x={d}, y={d}, z={d}\n", .{xyz1.x, xyz1.y, xyz1.z});
}