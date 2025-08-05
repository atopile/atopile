const std = @import("std");
const sexp = @import("sexp");

pub fn main() !void {
    var arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    // Test different layer formats
    
    // Format 1: Just a string (what we're getting)
    std.debug.print("Test 1: layer as string\n", .{});
    std.debug.print("  (layer \"F.SilkS\") - value is just a string\n", .{});
    
    // Format 2: TextLayer with positional fields
    std.debug.print("\nTest 2: layer as TextLayer struct\n", .{});
    const layer2 = "(layer \"F.SilkS\" knockout)";
    const tl2 = sexp.structure.loads(sexp.kicad.sexp.kicad.pcb.TextLayer, allocator, .{ .string = layer2 }, "layer") catch |err| {
        sexp.structure.printError(layer2, err);
        return err;
    };
    std.debug.print("  Success! layer={s}, knockout={?s}\n", .{ tl2.layer, tl2.knockout });
    
    // Let's check what FpText expects
    std.debug.print("\nChecking FpText structure...\n", .{});
    const fptext_sexp = 
        \\(fp_text reference "REF**"
        \\  (at 0 0)
        \\  (layer "F.SilkS")
        \\  (uuid "12345678-1234-1234-1234-123456789012")
        \\  (effects
        \\    (font
        \\      (size 1 1)
        \\      (thickness 0.15)
        \\    )
        \\  )
        \\)
    ;
    
    const fptext = sexp.structure.loads(sexp.kicad.pcb.FpText, allocator, .{ .string = fptext_sexp }, "fp_text") catch |err| {
        sexp.structure.printError(fptext_sexp, err);
        std.debug.print("\nLet's see what Text expects for layer...\n", .{});
        
        // Check the Text struct too
        const text_sexp = 
            \\(gr_text "Hello"
            \\  (at 0 0)
            \\  (layer "F.SilkS")
            \\  (uuid "12345678-1234-1234-1234-123456789012")
            \\  (effects
            \\    (font
            \\      (size 1 1)
            \\      (thickness 0.15)
            \\    )
            \\  )
            \\)
        ;
        
        const text = sexp.structure.loads(sexp.kicad.pcb.Text, allocator, .{ .string = text_sexp }, "gr_text") catch |err2| {
            sexp.structure.printError(text_sexp, err2);
            return err2;
        };
        
        std.debug.print("Text succeeded! text={s}\n", .{text.text});
        return err;
    };
    
    std.debug.print("  FpText succeeded! type={s}, text={s}\n", .{ fptext.type, fptext.text });
}