const std = @import("std");
const step = @import("lib.zig");

/// Test parsing and basic queries on real STEP files
/// Run with: zig test src/step/tests.zig
pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Test files - relative to src/step/ directory
    // These are copied into testdata/ for portability
    const test_files = [_][]const u8{
        "src/step/testdata/R0402_L1.0-W0.5-H0.4.step",
        "src/step/testdata/C0603_L1.6-W0.8-H0.8.step",
        "src/step/testdata/SOT-23-5_L2.9-W1.6-H1.1-LS2.8-P0.95.step",
        "src/step/testdata/CAP-TH_L17.5-W8.5-H13.5-P15.0.step",
        "src/step/testdata/HDR-M-2.54_2x5.step",
        "src/step/testdata/PWRM-TH_IBXX05S-2WR3.step",
        "src/step/testdata/VQFN-20_L5.0-W5.0-H1.0-P0.65.step",
    };

    const stdout = std.io.getStdOut().writer();

    try stdout.print("STEP Parser Test Results\n", .{});
    try stdout.print("========================\n\n", .{});

    for (test_files) |path| {
        // Extract filename
        const filename = std.fs.path.basename(path);

        try stdout.print("File: {s}\n", .{filename});

        // Read file
        const content = std.fs.cwd().readFileAlloc(allocator, path, 100 * 1024 * 1024) catch |err| {
            try stdout.print("  Error reading file: {}\n\n", .{err});
            continue;
        };
        defer allocator.free(content);

        // Parse
        var model = step.loads(allocator, content) catch |err| {
            try stdout.print("  Error parsing: {}\n\n", .{err});
            continue;
        };
        defer model.deinit();

        try stdout.print("  Entity count: {d}\n", .{model.entities.count()});

        // Bounding box
        if (step.queries.boundingBox(&model)) |bbox| {
            const size = bbox.size();
            try stdout.print("  Bounding box:\n", .{});
            try stdout.print("    Min: ({d:.4}, {d:.4}, {d:.4})\n", .{ bbox.min.x, bbox.min.y, bbox.min.z });
            try stdout.print("    Max: ({d:.4}, {d:.4}, {d:.4})\n", .{ bbox.max.x, bbox.max.y, bbox.max.z });
            try stdout.print("    Size: {d:.4} x {d:.4} x {d:.4} mm\n", .{ size.x, size.y, size.z });
        }

        // Bottom face Z
        if (step.queries.bottomFaceZ(&model)) |z| {
            try stdout.print("  Bottom face Z: {d:.4} mm\n", .{z});
        }

        // Cylinders (potential pins)
        const cylinders = step.queries.findCylinders(allocator, &model, 0.1, 1.0) catch &[_]step.Cylinder{};
        defer if (cylinders.len > 0) allocator.free(cylinders);

        var vertical_count: usize = 0;
        for (cylinders) |cyl| {
            if (cyl.is_vertical) vertical_count += 1;
        }

        try stdout.print("  Cylinders found: {d} ({d} vertical/pins)\n", .{ cylinders.len, vertical_count });

        // Pin positions
        if (vertical_count > 0) {
            const pins = step.queries.findVerticalCylinderPositions(allocator, &model, 0.1, 1.0) catch &[_]step.Point3D{};
            defer if (pins.len > 0) allocator.free(pins);

            if (pins.len > 0 and pins.len <= 20) {
                try stdout.print("  Pin positions:\n", .{});
                for (pins) |pin| {
                    try stdout.print("    ({d:.4}, {d:.4})\n", .{ pin.x, pin.y });
                }
            } else if (pins.len > 20) {
                try stdout.print("  Pin positions: {d} pins (too many to list)\n", .{pins.len});
            }
        }

        // Round-trip test
        const output = step.dumps(allocator, &model) catch |err| {
            try stdout.print("  Round-trip: FAILED ({any})\n\n", .{err});
            continue;
        };
        defer allocator.free(output);

        // Parse the output
        var model2 = step.loads(allocator, output) catch |err| {
            try stdout.print("  Round-trip: FAILED (re-parse error: {any})\n\n", .{err});
            continue;
        };
        defer model2.deinit();

        // Compare entity counts
        if (model.entities.count() == model2.entities.count()) {
            try stdout.print("  Round-trip: OK (entity count preserved)\n", .{});
        } else {
            try stdout.print("  Round-trip: MISMATCH ({d} vs {d} entities)\n", .{ model.entities.count(), model2.entities.count() });
        }

        try stdout.print("\n", .{});
    }
}

// Unit tests
test "tokenizer basic" {
    const allocator = std.testing.allocator;
    const input = "#1 = CARTESIAN_POINT('test', (1.0, 2.0, 3.0));";
    const tokens = try step.tokenizer.tokenize(allocator, input);
    defer allocator.free(tokens);

    try std.testing.expect(tokens.len > 0);
}

test "parser simple" {
    const allocator = std.testing.allocator;
    const input =
        \\ISO-10303-21;
        \\HEADER;
        \\FILE_DESCRIPTION(('test'),'1');
        \\FILE_NAME('test.step','2024-01-01',(''),(''),'','','');
        \\FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));
        \\ENDSEC;
        \\DATA;
        \\#1 = CARTESIAN_POINT('NONE', (0.0, 1.0, 2.0));
        \\ENDSEC;
        \\END-ISO-10303-21;
    ;

    var model = try step.loads(allocator, input);
    defer model.deinit();

    try std.testing.expectEqual(@as(usize, 1), model.entities.count());
}
