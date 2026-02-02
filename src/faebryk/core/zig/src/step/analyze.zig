//! STEP File Analyzer
//! Outputs JSON analysis for a given STEP file.
//! Usage: zig build-exe src/step/analyze.zig && ./analyze <file.step>

const std = @import("std");
const step = @import("lib.zig");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const args = try std.process.argsAlloc(allocator);
    defer std.process.argsFree(allocator, args);

    if (args.len < 2) {
        const stderr = std.io.getStdErr().writer();
        try stderr.writeAll("Usage: analyze <file.step>\n");
        std.process.exit(1);
    }

    const path = args[1];
    try analyzeAndOutput(allocator, path);
}

fn analyzeAndOutput(allocator: std.mem.Allocator, path: []const u8) !void {
    const stdout = std.io.getStdOut().writer();

    // Read file
    const content = std.fs.cwd().readFileAlloc(allocator, path, 100 * 1024 * 1024) catch |err| {
        try stdout.print("{{\"error\": \"Failed to read file: {}\"}}\n", .{err});
        return;
    };
    defer allocator.free(content);

    // Parse
    var model = step.loads(allocator, content) catch |err| {
        try stdout.print("{{\"error\": \"Failed to parse STEP: {}\"}}\n", .{err});
        return;
    };
    defer model.deinit();

    // Extract filename
    const filename = std.fs.path.basename(path);

    // Output JSON
    try stdout.writeAll("{\n");
    try stdout.print("  \"file\": \"{s}\",\n", .{filename});
    try stdout.print("  \"entities\": {d},\n", .{model.entities.count()});

    // Bounding box
    if (step.queries.boundingBox(&model)) |bbox| {
        const size = bbox.size();
        try stdout.writeAll("  \"bounding_box\": {\n");
        try stdout.print("    \"min\": [{d:.6}, {d:.6}, {d:.6}],\n", .{ bbox.min.x, bbox.min.y, bbox.min.z });
        try stdout.print("    \"max\": [{d:.6}, {d:.6}, {d:.6}]\n", .{ bbox.max.x, bbox.max.y, bbox.max.z });
        try stdout.writeAll("  },\n");
        try stdout.print("  \"size\": [{d:.6}, {d:.6}, {d:.6}],\n", .{ size.x, size.y, size.z });
    } else {
        try stdout.writeAll("  \"bounding_box\": null,\n");
        try stdout.writeAll("  \"size\": null,\n");
    }

    // Bottom face Z
    if (step.queries.bottomFaceZ(&model)) |z| {
        try stdout.print("  \"bottom_face_z\": {d:.6},\n", .{z});
    } else {
        try stdout.writeAll("  \"bottom_face_z\": null,\n");
    }

    // Centroid
    if (step.queries.centroid(&model)) |c| {
        try stdout.print("  \"centroid\": [{d:.6}, {d:.6}, {d:.6}],\n", .{ c.x, c.y, c.z });
    } else {
        try stdout.writeAll("  \"centroid\": null,\n");
    }

    // All cylinders
    const cylinders = step.queries.findCylinders(allocator, &model, 0.05, 2.0) catch &[_]step.Cylinder{};
    defer if (cylinders.len > 0) allocator.free(cylinders);

    try stdout.writeAll("  \"cylinders\": [\n");
    for (cylinders, 0..) |cyl, i| {
        try stdout.print("    {{\"x\": {d:.6}, \"y\": {d:.6}, \"z\": {d:.6}, \"radius\": {d:.6}, \"vertical\": {}}}", .{
            cyl.position.location.x,
            cyl.position.location.y,
            cyl.position.location.z,
            cyl.radius,
            cyl.is_vertical,
        });
        if (i < cylinders.len - 1) {
            try stdout.writeAll(",");
        }
        try stdout.writeAll("\n");
    }
    try stdout.writeAll("  ],\n");

    // Vertical pins only
    try stdout.writeAll("  \"vertical_pins\": [\n");
    var first = true;
    for (cylinders) |cyl| {
        if (cyl.is_vertical) {
            if (!first) try stdout.writeAll(",\n");
            try stdout.print("    {{\"x\": {d:.6}, \"y\": {d:.6}, \"radius\": {d:.6}}}", .{
                cyl.position.location.x,
                cyl.position.location.y,
                cyl.radius,
            });
            first = false;
        }
    }
    if (!first) try stdout.writeAll("\n");
    try stdout.writeAll("  ],\n");

    // Vertex points (actual geometry vertices for visualization)
    const vertices = step.queries.getVertexPoints(allocator, &model) catch &[_]step.queries.Point3D{};
    defer if (vertices.len > 0) allocator.free(vertices);

    try stdout.writeAll("  \"vertices\": [\n");
    for (vertices, 0..) |v, i| {
        try stdout.print("    [{d:.6}, {d:.6}, {d:.6}]", .{ v.x, v.y, v.z });
        if (i < vertices.len - 1) {
            try stdout.writeAll(",");
        }
        try stdout.writeAll("\n");
    }
    try stdout.writeAll("  ],\n");

    // Rectangular pins (for through-hole headers etc)
    const rect_pins = step.queries.findRectangularPins(allocator, &model, 0.2, 2.0) catch &[_]step.queries.RectangularPin{};
    defer if (rect_pins.len > 0) allocator.free(rect_pins);

    try stdout.writeAll("  \"rectangular_pins\": [\n");
    for (rect_pins, 0..) |pin, i| {
        try stdout.print("    {{\"x\": {d:.6}, \"y\": {d:.6}, \"z\": {d:.6}, \"size_x\": {d:.6}, \"size_y\": {d:.6}, \"min_z\": {d:.6}, \"max_z\": {d:.6}, \"vertical\": {}}}", .{
            pin.center.x,
            pin.center.y,
            pin.center.z,
            pin.size_x,
            pin.size_y,
            pin.min_z,
            pin.max_z,
            pin.is_vertical,
        });
        if (i < rect_pins.len - 1) {
            try stdout.writeAll(",");
        }
        try stdout.writeAll("\n");
    }
    try stdout.writeAll("  ],\n");

    // Top silhouette (X-Y outline at board level)
    const bottom_z = step.queries.bottomFaceZ(&model) orelse -1.0;
    const top_silhouette = step.queries.extractSilhouetteXY(allocator, &model, bottom_z - 0.5, bottom_z + 1.0) catch step.queries.Silhouette{
        .points = &[_]step.queries.Point2D{},
        .min_x = 0,
        .max_x = 0,
        .min_y = 0,
        .max_y = 0,
    };
    defer if (top_silhouette.points.len > 0) allocator.free(top_silhouette.points);

    try stdout.writeAll("  \"silhouette_xy\": [\n");
    for (top_silhouette.points, 0..) |p, i| {
        try stdout.print("    [{d:.6}, {d:.6}]", .{ p.x, p.y });
        if (i < top_silhouette.points.len - 1) {
            try stdout.writeAll(",");
        }
        try stdout.writeAll("\n");
    }
    try stdout.writeAll("  ],\n");

    // Side silhouette (X-Z outline)
    const side_silhouette = step.queries.extractSilhouetteXZ(allocator, &model) catch step.queries.Silhouette{
        .points = &[_]step.queries.Point2D{},
        .min_x = 0,
        .max_x = 0,
        .min_y = 0,
        .max_y = 0,
    };
    defer if (side_silhouette.points.len > 0) allocator.free(side_silhouette.points);

    try stdout.writeAll("  \"silhouette_xz\": [\n");
    for (side_silhouette.points, 0..) |p, i| {
        try stdout.print("    [{d:.6}, {d:.6}]", .{ p.x, p.y });
        if (i < side_silhouette.points.len - 1) {
            try stdout.writeAll(",");
        }
        try stdout.writeAll("\n");
    }
    try stdout.writeAll("  ],\n");

    // Edges (for detailed wireframe visualization)
    const edges = step.queries.getEdges(allocator, &model) catch &[_]step.queries.Edge3D{};
    defer if (edges.len > 0) allocator.free(edges);

    try stdout.writeAll("  \"edges\": [\n");
    for (edges, 0..) |e, i| {
        try stdout.print("    {{\"start\": [{d:.6}, {d:.6}, {d:.6}], \"end\": [{d:.6}, {d:.6}, {d:.6}]}}", .{
            e.start.x, e.start.y, e.start.z,
            e.end.x,   e.end.y,   e.end.z,
        });
        if (i < edges.len - 1) {
            try stdout.writeAll(",");
        }
        try stdout.writeAll("\n");
    }
    try stdout.writeAll("  ],\n");

    // Horizontal planes (for Z-alignment strategy)
    const h_planes = step.queries.getHorizontalPlaneZLevels(allocator, &model) catch &[_]step.queries.HorizontalPlane{};
    defer if (h_planes.len > 0) allocator.free(h_planes);

    try stdout.writeAll("  \"horizontal_planes\": [\n");
    for (h_planes, 0..) |hp, i| {
        try stdout.print("    {{\"z\": {d:.6}, \"count\": {d}}}", .{ hp.z, hp.count });
        if (i < h_planes.len - 1) {
            try stdout.writeAll(",");
        }
        try stdout.writeAll("\n");
    }
    try stdout.writeAll("  ],\n");

    // Circles (for pin visualization)
    const circles = step.queries.getCircles(allocator, &model) catch &[_]step.queries.Circle3D{};
    defer if (circles.len > 0) allocator.free(circles);

    try stdout.writeAll("  \"circles\": [\n");
    for (circles, 0..) |c, i| {
        try stdout.print("    {{\"x\": {d:.6}, \"y\": {d:.6}, \"z\": {d:.6}, \"radius\": {d:.6}, \"normal\": [{d:.6}, {d:.6}, {d:.6}]}}", .{
            c.center.x, c.center.y, c.center.z,
            c.radius,
            c.normal.x, c.normal.y, c.normal.z,
        });
        if (i < circles.len - 1) {
            try stdout.writeAll(",");
        }
        try stdout.writeAll("\n");
    }
    try stdout.writeAll("  ]\n");

    try stdout.writeAll("}\n");
}
