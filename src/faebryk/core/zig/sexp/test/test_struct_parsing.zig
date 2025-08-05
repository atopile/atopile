const std = @import("std");
const sexp = @import("sexp");

pub fn main() !void {
    var arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    // Test 1: Simple Wh struct
    std.debug.print("Test 1: Parsing Wh struct\n", .{});
    const wh_sexp = "(size 1.524 1.524)";
    const wh = sexp.structure.loads(sexp.kicad.pcb.Wh, allocator, .{ .string = wh_sexp }, "size") catch |err| {
        sexp.structure.printError(wh_sexp, err);
        return err;
    };
    std.debug.print("  Success! w={d}, h={?d}\n", .{ wh.w, wh.h });

    // Test 2: Font struct with size
    std.debug.print("\nTest 2: Parsing Font struct\n", .{});
    const font_sexp = "(font (size 1.524 1.524) (thickness 0.3))";
    const font = sexp.structure.loads(sexp.kicad.pcb.Font, allocator, .{ .string = font_sexp }, "font") catch |err| {
        sexp.structure.printError(font_sexp, err);
        return err;
    };
    std.debug.print("  Success! size.w={d}, thickness={?d}\n", .{ font.size.w, font.thickness });

    // Test 3: Effects struct
    std.debug.print("\nTest 3: Parsing Effects struct\n", .{});
    const effects_sexp = "(effects (font (size 1.524 1.524) (thickness 0.3)))";
    const effects = sexp.structure.loads(sexp.kicad.pcb.Effects, allocator, .{ .string = effects_sexp }, "effects") catch |err| {
        sexp.structure.printError(effects_sexp, err);
        return err;
    };
    std.debug.print("  Success! font.size.w={d}\n", .{effects.font.size.w});

    // Test 4: Full property
    std.debug.print("\nTest 4: Parsing full Property struct\n", .{});
    const property_sexp =
        \\ (property "Reference" "G***"
        \\   (at 0 0 0)
        \\   (hide yes)
        \\   (uuid "13bc68c1-7d1e-4abb-88c2-bf2277ec8354")
        \\   (effects
        \\     (font
        \\       (size 1.524 1.524)
        \\       (thickness 0.3)
        \\     )
        \\   )
        \\ )
    ;
    const property = sexp.structure.loads(sexp.kicad.pcb.Property, allocator, .{ .string = property_sexp }, "property") catch |err| {
        sexp.structure.printError(property_sexp, err);
        return err;
    };
    std.debug.print("  Success! name={s}, value={s}\n", .{ property.name, property.value });
}