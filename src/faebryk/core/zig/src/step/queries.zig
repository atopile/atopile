const std = @import("std");
const ast = @import("ast.zig");

const Parameter = ast.Parameter;
const Entity = ast.Entity;
const StepFile = ast.StepFile;

/// 3D Point
pub const Point3D = struct {
    x: f64,
    y: f64,
    z: f64,
};

/// 3D Direction (unit vector)
pub const Direction3D = struct {
    x: f64,
    y: f64,
    z: f64,

    pub fn isVertical(self: Direction3D, tolerance: f64) bool {
        // Check if direction is parallel to Z axis
        return @abs(self.z) > 1.0 - tolerance and
            @abs(self.x) < tolerance and
            @abs(self.y) < tolerance;
    }
};

/// Axis placement in 3D
pub const Axis2Placement3D = struct {
    location: Point3D,
    axis: Direction3D, // Z direction
    ref_direction: Direction3D, // X direction
};

/// Bounding box
pub const BoundingBox = struct {
    min: Point3D,
    max: Point3D,

    pub fn size(self: BoundingBox) Point3D {
        return .{
            .x = self.max.x - self.min.x,
            .y = self.max.y - self.min.y,
            .z = self.max.z - self.min.z,
        };
    }

    pub fn center(self: BoundingBox) Point3D {
        return .{
            .x = (self.min.x + self.max.x) / 2.0,
            .y = (self.min.y + self.max.y) / 2.0,
            .z = (self.min.z + self.max.z) / 2.0,
        };
    }
};

/// Detected cylinder in the model
pub const Cylinder = struct {
    position: Axis2Placement3D,
    radius: f64,
    /// True if cylinder axis is vertical (parallel to Z)
    is_vertical: bool,
};

/// Unit conversion factor for SI_UNIT
fn getUnitConversionFactor(step_file: *const StepFile) f64 {
    // Search for LENGTH_UNIT definition to determine scale
    // Default to millimeters (1.0)
    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        // Check for complex entity with LENGTH_UNIT and SI_UNIT
        if (entity.complex_types) |types| {
            var is_length_unit = false;
            var prefix: ?[]const u8 = null;

            for (types) |t| {
                if (std.mem.eql(u8, t.type_name, "LENGTH_UNIT")) {
                    is_length_unit = true;
                }
                if (std.mem.eql(u8, t.type_name, "SI_UNIT")) {
                    // SI_UNIT has prefix and unit type
                    if (t.parameters.len >= 1) {
                        if (ast.getEnumeration(t.parameters[0])) |p| {
                            prefix = p;
                        }
                    }
                }
            }

            if (is_length_unit) {
                if (prefix) |p| {
                    if (std.mem.eql(u8, p, "MILLI")) {
                        return 1.0; // Already in mm
                    } else if (std.mem.eql(u8, p, "CENTI")) {
                        return 10.0; // cm to mm
                    } else if (std.mem.eql(u8, p, "METRE") or std.mem.eql(u8, p, "$")) {
                        return 1000.0; // m to mm
                    }
                }
                // Default SI unit is meters
                return 1000.0;
            }
        }
    }

    // Default to mm (most common for electronic components)
    return 1.0;
}

/// Extract a Point3D from a CARTESIAN_POINT entity
fn extractCartesianPoint(step_file: *const StepFile, entity_id: u32) ?Point3D {
    const entity = step_file.getEntity(entity_id) orelse return null;

    if (!std.mem.eql(u8, entity.type_name, "CARTESIAN_POINT")) return null;

    // CARTESIAN_POINT('name', (x, y, z))
    if (entity.parameters.len < 2) return null;

    const coords = ast.getList(entity.parameters[1]) orelse return null;
    if (coords.len < 3) return null;

    const x = ast.getReal(coords[0]) orelse return null;
    const y = ast.getReal(coords[1]) orelse return null;
    const z = ast.getReal(coords[2]) orelse return null;

    return Point3D{ .x = x, .y = y, .z = z };
}

/// Extract a Direction3D from a DIRECTION entity
fn extractDirection(step_file: *const StepFile, entity_id: u32) ?Direction3D {
    const entity = step_file.getEntity(entity_id) orelse return null;

    if (!std.mem.eql(u8, entity.type_name, "DIRECTION")) return null;

    // DIRECTION('name', (x, y, z))
    if (entity.parameters.len < 2) return null;

    const coords = ast.getList(entity.parameters[1]) orelse return null;
    if (coords.len < 3) return null;

    const x = ast.getReal(coords[0]) orelse return null;
    const y = ast.getReal(coords[1]) orelse return null;
    const z = ast.getReal(coords[2]) orelse return null;

    return Direction3D{ .x = x, .y = y, .z = z };
}

/// Extract an Axis2Placement3D from an AXIS2_PLACEMENT_3D entity
fn extractAxis2Placement3D(step_file: *const StepFile, entity_id: u32) ?Axis2Placement3D {
    const entity = step_file.getEntity(entity_id) orelse return null;

    if (!std.mem.eql(u8, entity.type_name, "AXIS2_PLACEMENT_3D")) return null;

    // AXIS2_PLACEMENT_3D('name', location, axis, ref_direction)
    if (entity.parameters.len < 2) return null;

    const location_id = ast.getEntityRef(entity.parameters[1]) orelse return null;
    const location = extractCartesianPoint(step_file, location_id) orelse return null;

    // Axis and ref_direction are optional
    var axis = Direction3D{ .x = 0, .y = 0, .z = 1 }; // Default Z
    var ref_direction = Direction3D{ .x = 1, .y = 0, .z = 0 }; // Default X

    if (entity.parameters.len >= 3) {
        if (ast.getEntityRef(entity.parameters[2])) |axis_id| {
            if (extractDirection(step_file, axis_id)) |a| {
                axis = a;
            }
        }
    }

    if (entity.parameters.len >= 4) {
        if (ast.getEntityRef(entity.parameters[3])) |ref_id| {
            if (extractDirection(step_file, ref_id)) |r| {
                ref_direction = r;
            }
        }
    }

    return Axis2Placement3D{
        .location = location,
        .axis = axis,
        .ref_direction = ref_direction,
    };
}

/// Calculate bounding box from all CARTESIAN_POINT entities
pub fn boundingBox(step_file: *const StepFile) ?BoundingBox {
    const scale = getUnitConversionFactor(step_file);

    var min_x: f64 = std.math.floatMax(f64);
    var min_y: f64 = std.math.floatMax(f64);
    var min_z: f64 = std.math.floatMax(f64);
    var max_x: f64 = -std.math.floatMax(f64);
    var max_y: f64 = -std.math.floatMax(f64);
    var max_z: f64 = -std.math.floatMax(f64);

    var found_any = false;

    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        if (!std.mem.eql(u8, entity.type_name, "CARTESIAN_POINT")) continue;

        // CARTESIAN_POINT('name', (x, y, z))
        if (entity.parameters.len < 2) continue;

        const coords = ast.getList(entity.parameters[1]) orelse continue;
        if (coords.len < 3) continue;

        const x = (ast.getReal(coords[0]) orelse continue) * scale;
        const y = (ast.getReal(coords[1]) orelse continue) * scale;
        const z = (ast.getReal(coords[2]) orelse continue) * scale;

        min_x = @min(min_x, x);
        min_y = @min(min_y, y);
        min_z = @min(min_z, z);
        max_x = @max(max_x, x);
        max_y = @max(max_y, y);
        max_z = @max(max_z, z);

        found_any = true;
    }

    if (!found_any) return null;

    return BoundingBox{
        .min = .{ .x = min_x, .y = min_y, .z = min_z },
        .max = .{ .x = max_x, .y = max_y, .z = max_z },
    };
}

/// Find all cylindrical surfaces in the model
pub fn findCylinders(
    allocator: std.mem.Allocator,
    step_file: *const StepFile,
    min_radius: f64,
    max_radius: f64,
) ![]Cylinder {
    const scale = getUnitConversionFactor(step_file);

    var cylinders = std.ArrayList(Cylinder).init(allocator);
    errdefer cylinders.deinit();

    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        if (!std.mem.eql(u8, entity.type_name, "CYLINDRICAL_SURFACE")) continue;

        // CYLINDRICAL_SURFACE('name', position, radius)
        if (entity.parameters.len < 3) continue;

        const position_id = ast.getEntityRef(entity.parameters[1]) orelse continue;
        const radius = (ast.getReal(entity.parameters[2]) orelse continue) * scale;

        // Filter by radius
        if (radius < min_radius or radius > max_radius) continue;

        const position = extractAxis2Placement3D(step_file, position_id) orelse continue;

        const is_vertical = position.axis.isVertical(0.01);

        try cylinders.append(Cylinder{
            .position = position,
            .radius = radius,
            .is_vertical = is_vertical,
        });
    }

    return cylinders.toOwnedSlice();
}

/// Find vertical cylinders (potential pins) and return their XY positions
pub fn findVerticalCylinderPositions(
    allocator: std.mem.Allocator,
    step_file: *const StepFile,
    min_radius: f64,
    max_radius: f64,
) ![]Point3D {
    const cylinders = try findCylinders(allocator, step_file, min_radius, max_radius);
    defer allocator.free(cylinders);

    var positions = std.ArrayList(Point3D).init(allocator);
    errdefer positions.deinit();

    for (cylinders) |cyl| {
        if (cyl.is_vertical) {
            try positions.append(cyl.position.location);
        }
    }

    return positions.toOwnedSlice();
}

/// Find the Z coordinate of the bottom face (lowest horizontal plane)
pub fn bottomFaceZ(step_file: *const StepFile) ?f64 {
    const scale = getUnitConversionFactor(step_file);

    var min_z: f64 = std.math.floatMax(f64);
    var found = false;

    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        if (!std.mem.eql(u8, entity.type_name, "PLANE")) continue;

        // PLANE('name', position)
        if (entity.parameters.len < 2) continue;

        const position_id = ast.getEntityRef(entity.parameters[1]) orelse continue;
        const position = extractAxis2Placement3D(step_file, position_id) orelse continue;

        // Check if plane is horizontal (normal parallel to Z)
        if (position.axis.isVertical(0.01)) {
            const z = position.location.z * scale;
            if (z < min_z) {
                min_z = z;
                found = true;
            }
        }
    }

    if (!found) {
        // Fall back to bounding box minimum Z
        if (boundingBox(step_file)) |bbox| {
            return bbox.min.z;
        }
        return null;
    }

    return min_z;
}

/// Calculate centroid of the model (average of all points)
pub fn centroid(step_file: *const StepFile) ?Point3D {
    const scale = getUnitConversionFactor(step_file);

    var sum_x: f64 = 0;
    var sum_y: f64 = 0;
    var sum_z: f64 = 0;
    var count: usize = 0;

    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        if (!std.mem.eql(u8, entity.type_name, "CARTESIAN_POINT")) continue;

        if (entity.parameters.len < 2) continue;

        const coords = ast.getList(entity.parameters[1]) orelse continue;
        if (coords.len < 3) continue;

        const x = (ast.getReal(coords[0]) orelse continue) * scale;
        const y = (ast.getReal(coords[1]) orelse continue) * scale;
        const z = (ast.getReal(coords[2]) orelse continue) * scale;

        sum_x += x;
        sum_y += y;
        sum_z += z;
        count += 1;
    }

    if (count == 0) return null;

    const n: f64 = @floatFromInt(count);
    return Point3D{
        .x = sum_x / n,
        .y = sum_y / n,
        .z = sum_z / n,
    };
}

/// Get entity counts by type (for debugging/stats)
pub fn entityCounts(allocator: std.mem.Allocator, step_file: *const StepFile) !std.StringHashMap(usize) {
    var counts = std.StringHashMap(usize).init(allocator);
    errdefer counts.deinit();

    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        const result = try counts.getOrPut(entity.type_name);
        if (result.found_existing) {
            result.value_ptr.* += 1;
        } else {
            result.value_ptr.* = 1;
        }
    }

    return counts;
}

/// Get all CARTESIAN_POINT coordinates (for point cloud visualization)
pub fn getAllPoints(allocator: std.mem.Allocator, step_file: *const StepFile) ![]Point3D {
    const scale = getUnitConversionFactor(step_file);

    var points = std.ArrayList(Point3D).init(allocator);
    errdefer points.deinit();

    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        if (!std.mem.eql(u8, entity.type_name, "CARTESIAN_POINT")) continue;

        if (entity.parameters.len < 2) continue;

        const coords = ast.getList(entity.parameters[1]) orelse continue;
        if (coords.len < 3) continue;

        const x = (ast.getReal(coords[0]) orelse continue) * scale;
        const y = (ast.getReal(coords[1]) orelse continue) * scale;
        const z = (ast.getReal(coords[2]) orelse continue) * scale;

        try points.append(.{ .x = x, .y = y, .z = z });
    }

    return points.toOwnedSlice();
}

/// Get all VERTEX_POINT positions (actual geometry vertices, not control points)
pub fn getVertexPoints(allocator: std.mem.Allocator, step_file: *const StepFile) ![]Point3D {
    const scale = getUnitConversionFactor(step_file);

    var points = std.ArrayList(Point3D).init(allocator);
    errdefer points.deinit();

    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        if (!std.mem.eql(u8, entity.type_name, "VERTEX_POINT")) continue;

        // VERTEX_POINT('name', point_ref)
        if (entity.parameters.len < 2) continue;

        const point_id = ast.getEntityRef(entity.parameters[1]) orelse continue;
        const point = extractCartesianPoint(step_file, point_id) orelse continue;

        try points.append(.{
            .x = point.x * scale,
            .y = point.y * scale,
            .z = point.z * scale,
        });
    }

    return points.toOwnedSlice();
}

/// Rectangular pin/feature detected in the model
pub const RectangularPin = struct {
    center: Point3D,
    size_x: f64,
    size_y: f64,
    min_z: f64,
    max_z: f64,
    is_vertical: bool, // extends primarily in Z direction

    /// Check if this pin could match a hole at the given position
    pub fn matchesHole(self: RectangularPin, hole_x: f64, hole_y: f64, tolerance: f64) bool {
        const dx = @abs(self.center.x - hole_x);
        const dy = @abs(self.center.y - hole_y);
        return dx < tolerance and dy < tolerance;
    }
};

/// 2D point for silhouette
pub const Point2D = struct {
    x: f64,
    y: f64,
};

/// Silhouette data - outline of model projected to a plane
pub const Silhouette = struct {
    points: []Point2D,
    min_x: f64,
    max_x: f64,
    min_y: f64,
    max_y: f64,
};

/// Extract high-resolution silhouette (outline) of model projected to X-Y plane
/// Uses all vertex points and creates a dense boundary representation
pub fn extractSilhouetteXY(
    allocator: std.mem.Allocator,
    step_file: *const StepFile,
    z_min: f64,
    z_max: f64,
) !Silhouette {
    const scale = getUnitConversionFactor(step_file);
    _ = z_min;
    _ = z_max;

    // Collect ALL vertex points (not filtered by Z - we want full projection)
    var all_points = std.ArrayList(Point2D).init(allocator);
    defer all_points.deinit();

    var min_x: f64 = std.math.floatMax(f64);
    var max_x: f64 = -std.math.floatMax(f64);
    var min_y: f64 = std.math.floatMax(f64);
    var max_y: f64 = -std.math.floatMax(f64);

    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        if (!std.mem.eql(u8, entity.type_name, "VERTEX_POINT")) continue;

        if (entity.parameters.len < 2) continue;

        const point_id = ast.getEntityRef(entity.parameters[1]) orelse continue;
        const point = extractCartesianPoint(step_file, point_id) orelse continue;

        const x = point.x * scale;
        const y = point.y * scale;

        try all_points.append(.{ .x = x, .y = y });

        min_x = @min(min_x, x);
        max_x = @max(max_x, x);
        min_y = @min(min_y, y);
        max_y = @max(max_y, y);
    }

    // High-resolution convex hull: 360 bins (1 degree resolution)
    const num_bins = 360;
    var bins: [num_bins]?Point2D = .{null} ** num_bins;
    var bin_dist: [num_bins]f64 = .{0} ** num_bins;

    if (all_points.items.len > 0) {
        const cx = (min_x + max_x) / 2.0;
        const cy = (min_y + max_y) / 2.0;

        for (all_points.items) |p| {
            const dx = p.x - cx;
            const dy = p.y - cy;
            const dist = @sqrt(dx * dx + dy * dy);
            if (dist < 0.001) continue;

            var angle = std.math.atan2(dy, dx);
            if (angle < 0) angle += 2 * std.math.pi;

            const bin_idx: usize = @intFromFloat(@floor(angle / (2 * std.math.pi) * num_bins));
            const safe_idx = @min(bin_idx, num_bins - 1);

            // Keep the point furthest from center in each bin
            if (dist > bin_dist[safe_idx]) {
                bins[safe_idx] = p;
                bin_dist[safe_idx] = dist;
            }
        }
    }

    // Collect non-null bins as hull points
    var hull_points = std.ArrayList(Point2D).init(allocator);
    errdefer hull_points.deinit();

    for (bins) |maybe_p| {
        if (maybe_p) |p| {
            try hull_points.append(p);
        }
    }

    return Silhouette{
        .points = try hull_points.toOwnedSlice(),
        .min_x = min_x,
        .max_x = max_x,
        .min_y = min_y,
        .max_y = max_y,
    };
}

/// Extract high-resolution side silhouette (X-Z plane projection)
pub fn extractSilhouetteXZ(
    allocator: std.mem.Allocator,
    step_file: *const StepFile,
) !Silhouette {
    const scale = getUnitConversionFactor(step_file);

    var all_points = std.ArrayList(Point2D).init(allocator);
    defer all_points.deinit();

    var min_x: f64 = std.math.floatMax(f64);
    var max_x: f64 = -std.math.floatMax(f64);
    var min_z: f64 = std.math.floatMax(f64);
    var max_z: f64 = -std.math.floatMax(f64);

    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        if (!std.mem.eql(u8, entity.type_name, "VERTEX_POINT")) continue;

        if (entity.parameters.len < 2) continue;

        const point_id = ast.getEntityRef(entity.parameters[1]) orelse continue;
        const point = extractCartesianPoint(step_file, point_id) orelse continue;

        const x = point.x * scale;
        const z = point.z * scale;

        try all_points.append(.{ .x = x, .y = z });

        min_x = @min(min_x, x);
        max_x = @max(max_x, x);
        min_z = @min(min_z, z);
        max_z = @max(max_z, z);
    }

    // High-resolution convex hull: 360 bins
    const num_bins = 360;
    var bins: [num_bins]?Point2D = .{null} ** num_bins;
    var bin_dist: [num_bins]f64 = .{0} ** num_bins;

    if (all_points.items.len > 0) {
        const cx = (min_x + max_x) / 2.0;
        const cz = (min_z + max_z) / 2.0;

        for (all_points.items) |p| {
            const dx = p.x - cx;
            const dz = p.y - cz;
            const dist = @sqrt(dx * dx + dz * dz);
            if (dist < 0.001) continue;

            var angle = std.math.atan2(dz, dx);
            if (angle < 0) angle += 2 * std.math.pi;

            const bin_idx: usize = @intFromFloat(@floor(angle / (2 * std.math.pi) * num_bins));
            const safe_idx = @min(bin_idx, num_bins - 1);

            if (dist > bin_dist[safe_idx]) {
                bins[safe_idx] = p;
                bin_dist[safe_idx] = dist;
            }
        }
    }

    var hull_points = std.ArrayList(Point2D).init(allocator);
    errdefer hull_points.deinit();

    for (bins) |maybe_p| {
        if (maybe_p) |p| {
            try hull_points.append(p);
        }
    }

    return Silhouette{
        .points = try hull_points.toOwnedSlice(),
        .min_x = min_x,
        .max_x = max_x,
        .min_y = min_z,
        .max_y = max_z,
    };
}

/// Search for a feature at a specific expected location
/// Returns confidence score (0-1) of finding a matching feature
pub const FeatureMatch = struct {
    found: bool,
    confidence: f64,
    actual_x: f64,
    actual_y: f64,
    offset_x: f64,
    offset_y: f64,
};

/// Search for rectangular/cylindrical features near expected pad positions
/// This is footprint-driven detection - we know where to look
pub fn findFeatureAtLocation(
    step_file: *const StepFile,
    expected_x: f64,
    expected_y: f64,
    search_radius: f64,
    expected_size: f64, // Expected pin size (drill diameter or pad width)
) FeatureMatch {
    const scale = getUnitConversionFactor(step_file);

    var best_match = FeatureMatch{
        .found = false,
        .confidence = 0,
        .actual_x = expected_x,
        .actual_y = expected_y,
        .offset_x = 0,
        .offset_y = 0,
    };

    // Search for cylindrical surfaces near the expected location
    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        if (std.mem.eql(u8, entity.type_name, "CYLINDRICAL_SURFACE")) {
            if (entity.parameters.len < 3) continue;

            const position_id = ast.getEntityRef(entity.parameters[1]) orelse continue;
            const radius = (ast.getReal(entity.parameters[2]) orelse continue) * scale;

            const position = extractAxis2Placement3D(step_file, position_id) orelse continue;
            const x = position.location.x * scale;
            const y = position.location.y * scale;

            const dist = @sqrt((x - expected_x) * (x - expected_x) + (y - expected_y) * (y - expected_y));

            // Check if cylinder is vertical and near expected location
            if (dist < search_radius and position.axis.isVertical(0.1)) {
                // Size match bonus
                const size_match = 1.0 - @min(1.0, @abs(radius * 2 - expected_size) / expected_size);
                const dist_score = 1.0 - (dist / search_radius);
                const confidence = (size_match * 0.4 + dist_score * 0.6);

                if (confidence > best_match.confidence) {
                    best_match = .{
                        .found = true,
                        .confidence = confidence,
                        .actual_x = x,
                        .actual_y = y,
                        .offset_x = x - expected_x,
                        .offset_y = y - expected_y,
                    };
                }
            }
        }
    }

    // Also search for vertices clustered near the expected location
    // (for rectangular pins, there should be 4+ vertices forming a rectangle)
    var vertex_count: usize = 0;
    var vertex_sum_x: f64 = 0;
    var vertex_sum_y: f64 = 0;

    it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        if (!std.mem.eql(u8, entity.type_name, "VERTEX_POINT")) continue;

        if (entity.parameters.len < 2) continue;

        const point_id = ast.getEntityRef(entity.parameters[1]) orelse continue;
        const point = extractCartesianPoint(step_file, point_id) orelse continue;

        const x = point.x * scale;
        const y = point.y * scale;
        const z = point.z * scale;

        // Only consider vertices below or near board level (pin area)
        if (z > 1.0) continue;

        const dist = @sqrt((x - expected_x) * (x - expected_x) + (y - expected_y) * (y - expected_y));

        if (dist < search_radius) {
            vertex_count += 1;
            vertex_sum_x += x;
            vertex_sum_y += y;
        }
    }

    // If we found clustered vertices (likely a rectangular pin)
    if (vertex_count >= 4 and !best_match.found) {
        const avg_x = vertex_sum_x / @as(f64, @floatFromInt(vertex_count));
        const avg_y = vertex_sum_y / @as(f64, @floatFromInt(vertex_count));
        const dist = @sqrt((avg_x - expected_x) * (avg_x - expected_x) + (avg_y - expected_y) * (avg_y - expected_y));
        const confidence = 0.5 * (1.0 - dist / search_radius) * @min(1.0, @as(f64, @floatFromInt(vertex_count)) / 8.0);

        if (confidence > best_match.confidence) {
            best_match = .{
                .found = true,
                .confidence = confidence,
                .actual_x = avg_x,
                .actual_y = avg_y,
                .offset_x = avg_x - expected_x,
                .offset_y = avg_y - expected_y,
            };
        }
    }

    return best_match;
}

/// Find rectangular pins by clustering vertices below board level
/// This approach works much better for headers than plane-based detection
/// Algorithm:
/// 1. Find all vertices below Z=0 (pin area)
/// 2. Cluster by X,Y position (grid tolerance)
/// 3. For clusters with enough vertices, compute bounding box
/// 4. Filter by size (typical pins are 0.4-0.8mm)
pub fn findRectangularPins(
    allocator: std.mem.Allocator,
    step_file: *const StepFile,
    min_size: f64,
    max_size: f64,
) ![]RectangularPin {
    const scale = getUnitConversionFactor(step_file);
    _ = min_size; // Will use 0.3mm minimum
    _ = max_size; // Will use 1.5mm maximum

    // Collect all vertices below Z=0.5 (pin area below board)
    const PinVertex = struct {
        x: f64,
        y: f64,
        z: f64,
    };

    var pin_vertices = std.ArrayList(PinVertex).init(allocator);
    defer pin_vertices.deinit();

    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        if (!std.mem.eql(u8, entity.type_name, "VERTEX_POINT")) continue;

        if (entity.parameters.len < 2) continue;

        const point_id = ast.getEntityRef(entity.parameters[1]) orelse continue;
        const point = extractCartesianPoint(step_file, point_id) orelse continue;

        const x = point.x * scale;
        const y = point.y * scale;
        const z = point.z * scale;

        // Only collect vertices well below board level (Z < -1.0)
        // This filters out housing vertices near Z=0 that would expand bounding boxes
        // Real pins extend 2-4mm below board
        if (z < -1.0) {
            try pin_vertices.append(.{ .x = x, .y = y, .z = z });
        }
    }

    if (pin_vertices.items.len < 8) {
        return allocator.alloc(RectangularPin, 0);
    }

    // Use grid-based clustering with common header pin pitches
    // Most headers use 2.54mm (0.1"), 2.0mm, or 1.27mm pitch
    // We'll use 2.54mm as the primary grid, but also detect non-grid patterns
    const grid_size = 2.54;

    // Grid cell structure
    const GridKey = struct {
        gx: i32,
        gy: i32,
    };

    const Cluster = struct {
        min_x: f64,
        max_x: f64,
        min_y: f64,
        max_y: f64,
        min_z: f64,
        max_z: f64,
        count: usize,
    };

    var grid_clusters = std.AutoHashMap(GridKey, Cluster).init(allocator);
    defer grid_clusters.deinit();

    // Assign each vertex to a grid cell
    for (pin_vertices.items) |v| {
        const gx: i32 = @intFromFloat(@round(v.x / grid_size));
        const gy: i32 = @intFromFloat(@round(v.y / grid_size));
        const key = GridKey{ .gx = gx, .gy = gy };

        const result = try grid_clusters.getOrPut(key);
        if (result.found_existing) {
            result.value_ptr.min_x = @min(result.value_ptr.min_x, v.x);
            result.value_ptr.max_x = @max(result.value_ptr.max_x, v.x);
            result.value_ptr.min_y = @min(result.value_ptr.min_y, v.y);
            result.value_ptr.max_y = @max(result.value_ptr.max_y, v.y);
            result.value_ptr.min_z = @min(result.value_ptr.min_z, v.z);
            result.value_ptr.max_z = @max(result.value_ptr.max_z, v.z);
            result.value_ptr.count += 1;
        } else {
            result.value_ptr.* = .{
                .min_x = v.x,
                .max_x = v.x,
                .min_y = v.y,
                .max_y = v.y,
                .min_z = v.z,
                .max_z = v.z,
                .count = 1,
            };
        }
    }

    // Convert to ArrayList for processing
    var clusters = std.ArrayList(Cluster).init(allocator);
    defer clusters.deinit();

    var grid_it = grid_clusters.valueIterator();
    while (grid_it.next()) |c| {
        try clusters.append(c.*);
    }

    // Convert valid clusters to rectangular pins
    var pins = std.ArrayList(RectangularPin).init(allocator);
    errdefer pins.deinit();

    for (clusters.items) |c| {
        // Need at least 4 vertices to form a rectangle (4 corners at one Z level)
        if (c.count < 4) continue;

        const size_x = c.max_x - c.min_x;
        const size_y = c.max_y - c.min_y;
        const height = c.max_z - c.min_z;

        // Filter by size: typical pins are 0.4-1.0mm for standard headers
        // Allow up to 1.5mm for larger pins
        if (size_x < 0.4 or size_x > 1.5) continue;
        if (size_y < 0.4 or size_y > 1.5) continue;

        // Pins should have some height (at least one chamfer level)
        // Some grid cells may only catch part of the Z range
        if (height < 0.3) continue;

        // Pins should be roughly square-ish (not super elongated)
        const aspect = if (size_x > size_y) size_x / size_y else size_y / size_x;
        if (aspect > 3.0) continue;

        const center_x = (c.min_x + c.max_x) / 2.0;
        const center_y = (c.min_y + c.max_y) / 2.0;
        const center_z = (c.min_z + c.max_z) / 2.0;

        try pins.append(.{
            .center = .{ .x = center_x, .y = center_y, .z = center_z },
            .size_x = size_x,
            .size_y = size_y,
            .min_z = c.min_z,
            .max_z = c.max_z,
            .is_vertical = height > @max(size_x, size_y),
        });
    }

    return pins.toOwnedSlice();
}

/// Edge segment with start and end points
pub const Edge3D = struct {
    start: Point3D,
    end: Point3D,
};

/// Get all line edges from EDGE_CURVE entities
/// This provides actual geometry edges for detailed visualization
pub fn getEdges(allocator: std.mem.Allocator, step_file: *const StepFile) ![]Edge3D {
    const scale = getUnitConversionFactor(step_file);

    var edges = std.ArrayList(Edge3D).init(allocator);
    errdefer edges.deinit();

    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        if (!std.mem.eql(u8, entity.type_name, "EDGE_CURVE")) continue;

        // EDGE_CURVE('name', start_vertex, end_vertex, curve, same_sense)
        if (entity.parameters.len < 4) continue;

        const start_vertex_id = ast.getEntityRef(entity.parameters[1]) orelse continue;
        const end_vertex_id = ast.getEntityRef(entity.parameters[2]) orelse continue;

        // Get the vertex points
        const start_vertex = step_file.getEntity(start_vertex_id) orelse continue;
        const end_vertex = step_file.getEntity(end_vertex_id) orelse continue;

        if (!std.mem.eql(u8, start_vertex.type_name, "VERTEX_POINT")) continue;
        if (!std.mem.eql(u8, end_vertex.type_name, "VERTEX_POINT")) continue;

        if (start_vertex.parameters.len < 2 or end_vertex.parameters.len < 2) continue;

        const start_point_id = ast.getEntityRef(start_vertex.parameters[1]) orelse continue;
        const end_point_id = ast.getEntityRef(end_vertex.parameters[1]) orelse continue;

        const start_point = extractCartesianPoint(step_file, start_point_id) orelse continue;
        const end_point = extractCartesianPoint(step_file, end_point_id) orelse continue;

        try edges.append(.{
            .start = .{
                .x = start_point.x * scale,
                .y = start_point.y * scale,
                .z = start_point.z * scale,
            },
            .end = .{
                .x = end_point.x * scale,
                .y = end_point.y * scale,
                .z = end_point.z * scale,
            },
        });
    }

    return edges.toOwnedSlice();
}

/// Horizontal plane information
pub const HorizontalPlane = struct {
    z: f64,
    count: u32, // Number of faces at this Z level
};

/// Get all distinct horizontal plane Z levels
/// Useful for Z-alignment: try placing component at each plane level
pub fn getHorizontalPlaneZLevels(allocator: std.mem.Allocator, step_file: *const StepFile) ![]HorizontalPlane {
    const scale = getUnitConversionFactor(step_file);

    // Collect all horizontal plane Z values with counts
    var z_counts = std.AutoHashMap(i64, u32).init(allocator);
    defer z_counts.deinit();

    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        if (!std.mem.eql(u8, entity.type_name, "PLANE")) continue;

        if (entity.parameters.len < 2) continue;

        const position_id = ast.getEntityRef(entity.parameters[1]) orelse continue;
        const position = extractAxis2Placement3D(step_file, position_id) orelse continue;

        // Check if plane is horizontal (normal parallel to Z)
        if (position.axis.isVertical(0.01)) {
            const z = position.location.z * scale;
            // Quantize to 0.01mm precision for grouping
            const z_key: i64 = @intFromFloat(@round(z * 100));

            const result = try z_counts.getOrPut(z_key);
            if (result.found_existing) {
                result.value_ptr.* += 1;
            } else {
                result.value_ptr.* = 1;
            }
        }
    }

    // Convert to sorted list
    var planes = std.ArrayList(HorizontalPlane).init(allocator);
    errdefer planes.deinit();

    var z_it = z_counts.iterator();
    while (z_it.next()) |entry| {
        try planes.append(.{
            .z = @as(f64, @floatFromInt(entry.key_ptr.*)) / 100.0,
            .count = entry.value_ptr.*,
        });
    }

    // Sort by Z ascending
    std.mem.sort(HorizontalPlane, planes.items, {}, struct {
        fn lessThan(_: void, a: HorizontalPlane, b: HorizontalPlane) bool {
            return a.z < b.z;
        }
    }.lessThan);

    return planes.toOwnedSlice();
}

/// Circle geometry for visualization
pub const Circle3D = struct {
    center: Point3D,
    radius: f64,
    normal: Direction3D, // Plane normal (axis direction)
};

/// Get all circle edges (from CIRCLE entities referenced by EDGE_CURVE)
pub fn getCircles(allocator: std.mem.Allocator, step_file: *const StepFile) ![]Circle3D {
    const scale = getUnitConversionFactor(step_file);

    var circles = std.ArrayList(Circle3D).init(allocator);
    errdefer circles.deinit();

    // Track which circles we've already added to avoid duplicates
    var seen = std.AutoHashMap(u32, void).init(allocator);
    defer seen.deinit();

    var it = step_file.entities.valueIterator();
    while (it.next()) |entity| {
        if (!std.mem.eql(u8, entity.type_name, "CIRCLE")) continue;

        // CIRCLE('name', position, radius)
        if (entity.parameters.len < 3) continue;

        const position_id = ast.getEntityRef(entity.parameters[1]) orelse continue;
        const radius = (ast.getReal(entity.parameters[2]) orelse continue) * scale;

        const position = extractAxis2Placement3D(step_file, position_id) orelse continue;

        try circles.append(.{
            .center = .{
                .x = position.location.x * scale,
                .y = position.location.y * scale,
                .z = position.location.z * scale,
            },
            .radius = radius,
            .normal = position.axis,
        });
    }

    return circles.toOwnedSlice();
}
