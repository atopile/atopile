const std = @import("std");
const tokenizer = @import("tokenizer.zig");
const ast = @import("ast.zig");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Example KiCad S-expression
    const input =
        \\(kicad_pcb (version 20211014) (generator pcbnew)
        \\  (general
        \\    (thickness 1.6)
        \\    (drawings 4)
        \\    (tracks 0)
        \\    (zones 0)
        \\    (modules 2)
        \\    (nets 1))
        \\  (page A4)
        \\  (layers
        \\    (0 F.Cu signal)
        \\    (31 B.Cu signal)
        \\    (32 B.Adhes user)
        \\    (33 F.Adhes user))
        \\  (net 0 "")
        \\  (module Resistor_SMD:R_0603_1608Metric (layer F.Cu) (at 100 50)
        \\    (fp_text reference R1 (at 0 -1.43) (layer F.SilkS)
        \\      (effects (font (size 1 1) (thickness 0.15))))
        \\    (pad 1 smd rect (at -0.775 0) (size 0.9 0.95) (layers F.Cu F.Paste F.Mask))
        \\    (pad 2 smd rect (at 0.775 0) (size 0.9 0.95) (layers F.Cu F.Paste F.Mask))))
    ;

    // Tokenize
    const tokens = try tokenizer.tokenize(allocator, input);
    defer allocator.free(tokens);

    std.debug.print("Tokenized {} tokens\n\n", .{tokens.len});

    // Parse into AST
    var sexp = try ast.parse(allocator, tokens) orelse {
        std.debug.print("Did not find a top-level S-expression\n", .{});
        return;
    };
    defer sexp.deinit(allocator);

    // Analyze the PCB structure
    if (!ast.isForm(sexp, "kicad_pcb")) {
        std.debug.print("Not a KiCad PCB file!\n", .{});
        return;
    }

    std.debug.print("KiCad PCB file analysis:\n", .{});

    // Find version
    const items = ast.getList(sexp).?;
    for (items) |item| {
        if (ast.isForm(item, "version")) {
            const version_items = ast.getList(item).?;
            if (version_items.len > 1) {
                std.debug.print("  Version: {}\n", .{version_items[1]});
            }
        } else if (ast.isForm(item, "general")) {
            std.debug.print("  General settings:\n", .{});
            const general_items = ast.getList(item).?;
            for (general_items[1..]) |setting| {
                if (ast.isList(setting)) {
                    const setting_items = ast.getList(setting).?;
                    if (setting_items.len >= 2) {
                        std.debug.print("    {}: {}\n", .{ setting_items[0], setting_items[1] });
                    }
                }
            }
        } else if (ast.isForm(item, "module")) {
            const module_items = ast.getList(item).?;
            if (module_items.len > 1) {
                std.debug.print("  Module: {}\n", .{module_items[1]});

                // Find position
                for (module_items) |module_item| {
                    if (ast.isForm(module_item, "at")) {
                        const at_items = ast.getList(module_item).?;
                        if (at_items.len >= 3) {
                            std.debug.print("    Position: ({}, {})\n", .{ at_items[1], at_items[2] });
                        }
                    }
                }
            }
        }
    }

    std.debug.print("\nFormatted S-expression:\n", .{});

    // Pretty print a smaller expression
    const module_expr = blk: {
        for (items) |item| {
            if (ast.isForm(item, "module")) {
                break :blk item;
            }
        }
        break :blk null;
    };

    if (module_expr) |module| {
        var buffer = std.ArrayList(u8).init(allocator);
        defer buffer.deinit();

        try module.format("", .{}, buffer.writer());
        std.debug.print("{s}\n", .{buffer.items});
    }
}
