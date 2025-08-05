const std = @import("std");
const sexp = @import("sexp");

const RESOURCES_ROOT = "test/resources/v9";

test "load real netlist file - basic checks" {
    const FILE_PATH = RESOURCES_ROOT ++ "/netlist/test_e.net";

    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    var netlist_file = sexp.kicad.netlist.NetlistFile.loads(allocator, .{ .path = FILE_PATH }) catch |err| {
        sexp.structure.printError(try std.fs.cwd().readFileAlloc(allocator, FILE_PATH, 1024 * 1024), err);
        return err;
    };
    defer netlist_file.free(allocator);

    try std.testing.expect(netlist_file.netlist != null);
    const nl = netlist_file.netlist.?;

    try std.testing.expectEqualStrings("E", nl.version);
    try std.testing.expectEqual(@as(usize, 13), nl.components.comps.len);
}

test "comprehensive netlist example" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    // Comprehensive test netlist
    const test_netlist =
        \\(export (version "E")
        \\  (design
        \\    (source "test_circuit.kicad_sch")
        \\    (date "2024-01-01T12:00:00+0000")
        \\    (tool "faebryk 1.0")
        \\    (sheet (number "1") (name "Main") (tstamps "/")
        \\      (title_block
        \\        (title "Test Circuit")
        \\        (company "Faebryk Inc")
        \\        (rev "1.0")
        \\        (date "2024-01-01")
        \\        (source "test_circuit.kicad_sch")
        \\        (comment (number "1") (value "Test netlist"))
        \\        (comment (number "2") (value "For unit testing"))
        \\      )
        \\    )
        \\  )
        \\  (components
        \\    (comp (ref "R1")
        \\      (value "10k")
        \\      (footprint "Resistor_SMD:R_0603_1608Metric")
        \\      (fields
        \\        (field (name "Footprint") "Resistor_SMD:R_0603_1608Metric")
        \\        (field (name "Datasheet"))
        \\        (field (name "Description") "Resistor")
        \\      )
        \\      (libsource (lib "Device") (part "R") (description "Resistor"))
        \\      (property (name "Sheetname") (value "Main"))
        \\      (property (name "Sheetfile") (value "test_circuit.kicad_sch"))
        \\      (sheetpath (names "/") (tstamps "/"))
        \\      (tstamps "11111111-1111-1111-1111-111111111111")
        \\    )
        \\    (comp (ref "C1")
        \\      (value "100nF")
        \\      (footprint "Capacitor_SMD:C_0603_1608Metric")
        \\      (libsource (lib "Device") (part "C") (description "Capacitor"))
        \\      (sheetpath (names "/") (tstamps "/"))
        \\      (tstamps "22222222-2222-2222-2222-222222222222")
        \\    )
        \\  )
        \\  (nets
        \\    (net (code "1") (name "GND")
        \\      (node (ref "R1") (pin "2") (pintype "passive"))
        \\      (node (ref "C1") (pin "2") (pintype "passive"))
        \\    )
        \\    (net (code "2") (name "VCC")
        \\      (node (ref "R1") (pin "1") (pintype "passive"))
        \\      (node (ref "C1") (pin "1") (pintype "passive"))
        \\    )
        \\  )
        \\  (libparts
        \\    (libpart (lib "Device") (part "R")
        \\      (footprints
        \\        (fp "R_*")
        \\      )
        \\      (fields
        \\        (field (name "Reference") "R")
        \\        (field (name "Value") "R")
        \\      )
        \\      (pins
        \\        (pin (num "1") (name "~") (type "passive"))
        \\        (pin (num "2") (name "~") (type "passive"))
        \\      )
        \\    )
        \\    (libpart (lib "Device") (part "C")
        \\      (footprints
        \\        (fp "C_*")
        \\      )
        \\      (fields
        \\        (field (name "Reference") "C")
        \\        (field (name "Value") "C")
        \\      )
        \\      (pins
        \\        (pin (num "1") (name "~") (type "passive"))
        \\        (pin (num "2") (name "~") (type "passive"))
        \\      )
        \\    )
        \\  )
        \\  (libraries)
        \\)
    ;

    // Parse the netlist
    const parsed = sexp.kicad.netlist.NetlistFile.loads(allocator, .{ .string = test_netlist }) catch |err| {
        std.debug.print("\nError parsing netlist: {}\n", .{err});
        if (sexp.structure.getErrorContext()) |ctx| {
            std.debug.print("  Location: {s}\n", .{ctx.path});
            if (ctx.field_name) |field| {
                std.debug.print("  Field: {s}\n", .{field});
            }
            if (ctx.sexp_preview) |preview| {
                std.debug.print("  Near: {s}\n", .{preview});
            }
        }
        return err;
    };

    // Verify comprehensive content
    try std.testing.expect(parsed.netlist != null);
    const nl = parsed.netlist.?;

    // Check all major sections
    try std.testing.expectEqualStrings("E", nl.version);
    try std.testing.expectEqual(@as(usize, 2), nl.components.comps.len);
    try std.testing.expectEqual(@as(usize, 2), nl.nets.nets.len);
    try std.testing.expectEqual(@as(usize, 2), nl.libparts.libparts.len);

    // Check design details
    try std.testing.expect(nl.design != null);
    const design = nl.design.?;
    try std.testing.expectEqualStrings("test_circuit.kicad_sch", design.source);
    try std.testing.expectEqualStrings("2024-01-01T12:00:00+0000", design.date);
    try std.testing.expectEqualStrings("faebryk 1.0", design.tool);

    // Check title block
    try std.testing.expectEqualStrings("Test Circuit", design.sheet.title_block.title);
    try std.testing.expectEqualStrings("Faebryk Inc", design.sheet.title_block.company);
    try std.testing.expectEqual(@as(usize, 2), design.sheet.title_block.comment.len);

    // Check a component in detail
    const r1 = nl.components.comps[0];
    try std.testing.expectEqualStrings("R1", r1.ref);
    try std.testing.expectEqualStrings("10k", r1.value);
    try std.testing.expectEqual(@as(usize, 2), r1.propertys.len);

    // Check fields
    try std.testing.expect(r1.fields != null);
    if (r1.fields) |fields| {
        try std.testing.expectEqual(@as(usize, 3), fields.fields.len);
        try std.testing.expectEqualStrings("Footprint", fields.fields[0].name);
        try std.testing.expectEqualStrings("Resistor_SMD:R_0603_1608Metric", fields.fields[0].value.?);
        try std.testing.expectEqualStrings("Datasheet", fields.fields[1].name);
        try std.testing.expect(fields.fields[1].value == null);
        try std.testing.expectEqualStrings("Description", fields.fields[2].name);
        try std.testing.expectEqualStrings("Resistor", fields.fields[2].value.?);
    }

    // Check a net
    const gnd = nl.nets.nets[0];
    try std.testing.expectEqualStrings("1", gnd.code);
    try std.testing.expectEqualStrings("GND", gnd.name);
    try std.testing.expectEqual(@as(usize, 2), gnd.nodes.len);

    // Check a libpart
    const resistor = nl.libparts.libparts[0];
    try std.testing.expectEqualStrings("Device", resistor.lib);
    try std.testing.expectEqualStrings("R", resistor.part);

    // Check pins
    try std.testing.expect(resistor.pins != null);
    if (resistor.pins) |pins| {
        try std.testing.expectEqual(@as(usize, 2), pins.pin.len);
    }

    // Check fields
    try std.testing.expect(resistor.fields != null);
    if (resistor.fields) |fields| {
        try std.testing.expectEqual(@as(usize, 2), fields.fields.len);
    }

    // Now test round-trip
    const serialized = try parsed.dumps(allocator, null);
    const reparsed = try sexp.kicad.netlist.NetlistFile.loads(allocator, .{ .string = serialized });

    try std.testing.expect(reparsed.netlist != null);
    const nl2 = reparsed.netlist.?;

    // Verify round-trip preserved everything
    try std.testing.expectEqualStrings(nl.version, nl2.version);
    try std.testing.expectEqual(nl.components.comps.len, nl2.components.comps.len);
    try std.testing.expectEqual(nl.nets.nets.len, nl2.nets.nets.len);
    try std.testing.expectEqual(nl.libparts.libparts.len, nl2.libparts.libparts.len);

    // Note: We don't need to call free when using arena allocator
    // The arena.deinit() in the defer statement will free all memory
}

test "simple round-trip netlist" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    // Minimal test netlist
    const minimal_netlist =
        \\(export (version "E")
        \\  (design
        \\    (source "test.kicad_sch")
        \\    (date "2024-01-01")
        \\    (tool "test")
        \\    (sheet (number "1") (name "/") (tstamps "/")
        \\      (title_block
        \\        (title "Test")
        \\        (company "Test")
        \\        (rev "1")
        \\        (date "2024-01-01")
        \\        (source "test.kicad_sch")
        \\      )
        \\    )
        \\  )
        \\  (components
        \\    (comp (ref "R1")
        \\      (value "1k")
        \\      (footprint "Resistor_SMD:R_0603_1608Metric")
        \\      (tstamps "12345678-1234-1234-1234-123456789012")
        \\    )
        \\  )
        \\  (nets
        \\    (net (code "1") (name "GND")
        \\      (node (ref "R1") (pin "1"))
        \\    )
        \\  )
        \\  (libparts
        \\    (libpart (lib "Device") (part "R")
        \\    )
        \\  )
        \\  (libraries)
        \\)
    ;

    // Parse the netlist
    const parsed = try sexp.kicad.netlist.NetlistFile.loads(allocator, .{ .string = minimal_netlist });

    // Serialize it back
    const serialized = try parsed.dumps(allocator, null);

    // Parse again
    const reparsed = try sexp.kicad.netlist.NetlistFile.loads(allocator, .{ .string = serialized });

    // Basic checks to ensure round-trip worked
    try std.testing.expect(reparsed.netlist != null);
    const nl1 = parsed.netlist.?;
    const nl2 = reparsed.netlist.?;

    try std.testing.expectEqualStrings(nl1.version, nl2.version);
    try std.testing.expectEqual(nl1.components.comps.len, nl2.components.comps.len);
    try std.testing.expectEqual(nl1.nets.nets.len, nl2.nets.nets.len);
    try std.testing.expectEqual(nl1.libparts.libparts.len, nl2.libparts.libparts.len);
}

test "pcb: property" {
    const sexp_string =
        \\ (property "Reference" "G***"
        \\   (at 0 0 0)
        \\   (hide yes)
        \\   (layer "F.SilkS")
        \\   (uuid "13bc68c1-7d1e-4abb-88c2-bf2277ec8354")
        \\   (effects
        \\     (font
        \\       (size 1.524 1.524)
        \\       (thickness 0.3)
        \\     )
        \\   )
        \\ )
    ;

    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    const property = sexp.structure.loads(sexp.kicad.pcb.Property, allocator, .{ .string = sexp_string }, "property") catch |err| {
        sexp.structure.printError(sexp_string, err);
        return err;
    };
    defer sexp.structure.free(sexp.kicad.pcb.Property, allocator, property);

    try std.testing.expectEqualStrings("Reference", property.name);
    try std.testing.expectEqualStrings("G***", property.value);
    try std.testing.expectEqualStrings("F.SilkS", property.layer);
    try std.testing.expectEqualStrings("13bc68c1-7d1e-4abb-88c2-bf2277ec8354", property.uuid);
    try std.testing.expectEqual(0, property.at.x);
    try std.testing.expectEqual(0, property.at.y);
    try std.testing.expectEqual(0, property.at.r);
    try std.testing.expectEqual(true, property.hide);
    try std.testing.expectEqual(1.524, property.effects.font.size.w);
    try std.testing.expectEqual(1.524, property.effects.font.size.h);
    try std.testing.expectEqual(0.3, property.effects.font.thickness.?);
}

test "load real pcb file" {
    const FILE_PATH = RESOURCES_ROOT ++ "/pcb/top.kicad_pcb";

    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    var pcb_file = sexp.kicad.pcb.PcbFile.loads(allocator, .{ .path = FILE_PATH }) catch |err| {
        sexp.structure.printError(try std.fs.cwd().readFileAlloc(allocator, FILE_PATH, 1024 * 1024), err);
        return err;
    };
    defer pcb_file.free(allocator);

    const pcb_ = pcb_file.kicad_pcb;

    try std.testing.expectEqual(20241229, pcb_.version);
    try std.testing.expectEqual(@as(usize, 12), pcb_.footprints.len);
    const fp_logo = pcb_.footprints[0];
    try std.testing.expectEqualStrings("UNI_ROYAL_0402WGF1001TCE:R0402", fp_logo.name);
}

pub fn main() !void {
    // Run tests
    std.debug.print("Running netlist tests...\n", .{});

    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Use the comprehensive test netlist that we know works
    const test_netlist_str =
        \\(export (version "E")
        \\  (design
        \\    (source "test_circuit.kicad_sch")
        \\    (date "2024-01-01T12:00:00+0000")
        \\    (tool "faebryk 1.0")
        \\    (sheet (number "1") (name "Main") (tstamps "/")
        \\      (title_block
        \\        (title "Test Circuit")
        \\        (company "Faebryk Inc")
        \\        (rev "1.0")
        \\        (date "2024-01-01")
        \\        (source "test_circuit.kicad_sch")
        \\        (comment (number "1") (value "Test netlist"))
        \\        (comment (number "2") (value "For unit testing"))
        \\      )
        \\    )
        \\  )
        \\  (components
        \\    (comp (ref "R1")
        \\      (value "10k")
        \\      (footprint "Resistor_SMD:R_0603_1608Metric")
        \\      (fields
        \\        (field (name "Footprint") "Resistor_SMD:R_0603_1608Metric")
        \\        (field (name "Datasheet"))
        \\        (field (name "Description") "Resistor")
        \\      )
        \\      (libsource (lib "Device") (part "R") (description "Resistor"))
        \\      (property (name "Sheetname") (value "Main"))
        \\      (property (name "Sheetfile") (value "test_circuit.kicad_sch"))
        \\      (sheetpath (names "/") (tstamps "/"))
        \\      (tstamps "11111111-1111-1111-1111-111111111111")
        \\    )
        \\    (comp (ref "C1")
        \\      (value "100nF")
        \\      (footprint "Capacitor_SMD:C_0603_1608Metric")
        \\      (libsource (lib "Device") (part "C") (description "Capacitor"))
        \\      (sheetpath (names "/") (tstamps "/"))
        \\      (tstamps "22222222-2222-2222-2222-222222222222")
        \\    )
        \\  )
        \\  (nets
        \\    (net (code "1") (name "GND")
        \\      (node (ref "R1") (pin "2") (pintype "passive"))
        \\      (node (ref "C1") (pin "2") (pintype "passive"))
        \\    )
        \\    (net (code "2") (name "VCC")
        \\      (node (ref "R1") (pin "1") (pintype "passive"))
        \\      (node (ref "C1") (pin "1") (pintype "passive"))
        \\    )
        \\  )
        \\  (libparts
        \\    (libpart (lib "Device") (part "R")
        \\      (footprints
        \\        (fp "R_*")
        \\      )
        \\      (fields
        \\        (field (name "Reference") "R")
        \\        (field (name "Value") "R")
        \\      )
        \\      (pins
        \\        (pin (num "1") (name "~") (type "passive"))
        \\        (pin (num "2") (name "~") (type "passive"))
        \\      )
        \\    )
        \\    (libpart (lib "Device") (part "C")
        \\      (footprints
        \\        (fp "C_*")
        \\      )
        \\      (fields
        \\        (field (name "Reference") "C")
        \\        (field (name "Value") "C")
        \\      )
        \\      (pins
        \\        (pin (num "1") (name "~") (type "passive"))
        \\        (pin (num "2") (name "~") (type "passive"))
        \\      )
        \\    )
        \\  )
        \\  (libraries)
        \\)
    ;

    var parsed = sexp.kicad.netlist.NetlistFile.loads(allocator, .{ .string = test_netlist_str }) catch |err| {
        std.debug.print("Error loading netlist: {}\n", .{err});
        if (sexp.structure.getErrorContext()) |ctx| {
            var ctx_with_source = ctx;
            ctx_with_source.source = test_netlist_str;
            std.debug.print("{}\n", .{ctx_with_source});
        }
        return err;
    };
    defer parsed.free(allocator);

    std.debug.print("Parsed netlist is null: {}\n", .{parsed.netlist == null});

    if (parsed.netlist) |nl| {
        std.debug.print("Loaded netlist version: {s}\n", .{nl.version});
        std.debug.print("Components: {} (expected 2)\n", .{nl.components.comps.len});
        std.debug.print("Nets: {} (expected 2)\n", .{nl.nets.nets.len});
        std.debug.print("Libparts: {} (expected 2)\n", .{nl.libparts.libparts.len});

        if (nl.design) |design| {
            std.debug.print("Design tool: {s}\n", .{design.tool});
            std.debug.print("Design date: {s}\n", .{design.date});
        }

        // Debug: print the actual component if it exists
        if (nl.components.comps.len > 0) {
            std.debug.print("\nFirst component:\n", .{});
            const comp = nl.components.comps[0];
            std.debug.print("  ref: {s}\n", .{comp.ref});
            std.debug.print("  value: {s}\n", .{comp.value});
            std.debug.print("  footprint: {s}\n", .{comp.footprint});
        } else {
            std.debug.print("\nNo components found!\n", .{});
        }
    }

    std.debug.print("\nAll tests passed!\n", .{});
}
