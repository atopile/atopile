const std = @import("std");
const tokenizer = @import("tokenizer.zig");

const Token = tokenizer.Token;
const TokenType = tokenizer.TokenType;
pub const TokenLocation = tokenizer.TokenLocation;

/// Parameter value in a STEP entity
pub const Parameter = union(enum) {
    /// Reference to another entity: #123
    entity_ref: u32,
    /// Integer value
    integer: i64,
    /// Real number (stored as string to preserve precision)
    real: []const u8,
    /// String value (single-quoted in STEP)
    string: []const u8,
    /// Enumeration value: .ENUM_VALUE.
    enumeration: []const u8,
    /// List of parameters: (param1, param2, ...)
    list: []Parameter,
    /// Typed parameter: TYPE(params)
    typed: TypedParameter,
    /// Undefined value: *
    undefined,
    /// Omitted value: $
    omitted,

    pub fn deinit(self: *Parameter, allocator: std.mem.Allocator) void {
        switch (self.*) {
            .list => |list| {
                for (list) |*item| {
                    item.deinit(allocator);
                }
                allocator.free(list);
            },
            .typed => |*typed| {
                typed.deinit(allocator);
            },
            // String values are slices into original input, don't free
            else => {},
        }
    }

    pub fn format(self: Parameter, comptime fmt: []const u8, options: std.fmt.FormatOptions, writer: anytype) !void {
        switch (self) {
            .entity_ref => |id| try writer.print("#{d}", .{id}),
            .integer => |i| try writer.print("{d}", .{i}),
            .real => |r| try writer.writeAll(r),
            .string => |s| try writer.print("'{s}'", .{s}),
            .enumeration => |e| try writer.print(".{s}.", .{e}),
            .list => |l| {
                try writer.writeAll("(");
                for (l, 0..) |item, i| {
                    if (i > 0) try writer.writeAll(", ");
                    try item.format(fmt, options, writer);
                }
                try writer.writeAll(")");
            },
            .typed => |t| {
                try writer.print("{s}(", .{t.type_name});
                for (t.parameters, 0..) |param, i| {
                    if (i > 0) try writer.writeAll(", ");
                    try param.format(fmt, options, writer);
                }
                try writer.writeAll(")");
            },
            .undefined => try writer.writeAll("*"),
            .omitted => try writer.writeAll("$"),
        }
    }
};

/// Typed parameter: TYPE(params)
pub const TypedParameter = struct {
    type_name: []const u8,
    parameters: []Parameter,

    pub fn deinit(self: *TypedParameter, allocator: std.mem.Allocator) void {
        for (self.parameters) |*param| {
            param.deinit(allocator);
        }
        allocator.free(self.parameters);
    }
};

/// A STEP entity: #id = TYPE_NAME(params);
pub const Entity = struct {
    id: u32,
    type_name: []const u8,
    parameters: []Parameter,
    /// For complex entities (multiple types): #id = (TYPE1(...) TYPE2(...))
    complex_types: ?[]TypedParameter = null,
    location: ?TokenLocation = null,

    pub fn deinit(self: *Entity, allocator: std.mem.Allocator) void {
        for (self.parameters) |*param| {
            param.deinit(allocator);
        }
        allocator.free(self.parameters);

        if (self.complex_types) |types| {
            for (types) |*t| {
                t.deinit(allocator);
            }
            allocator.free(types);
        }
    }

    pub fn format(self: Entity, comptime fmt: []const u8, options: std.fmt.FormatOptions, writer: anytype) !void {
        _ = fmt;
        _ = options;
        try writer.print("#{d} = ", .{self.id});

        if (self.complex_types) |types| {
            try writer.writeAll("(");
            for (types, 0..) |t, i| {
                if (i > 0) try writer.writeAll(" ");
                try writer.print("{s}(", .{t.type_name});
                for (t.parameters, 0..) |param, j| {
                    if (j > 0) try writer.writeAll(", ");
                    try param.format("", .{}, writer);
                }
                try writer.writeAll(")");
            }
            try writer.writeAll(")");
        } else {
            try writer.print("{s}(", .{self.type_name});
            for (self.parameters, 0..) |param, i| {
                if (i > 0) try writer.writeAll(", ");
                try param.format("", .{}, writer);
            }
            try writer.writeAll(")");
        }
        try writer.writeAll(";");
    }
};

/// STEP file header
pub const Header = struct {
    file_description: FileDescription = .{},
    file_name: FileName = .{},
    file_schema: FileSchema = .{},

    pub const FileDescription = struct {
        description: [][]const u8 = &.{},
        implementation_level: []const u8 = "",
    };

    pub const FileName = struct {
        name: []const u8 = "",
        time_stamp: []const u8 = "",
        author: [][]const u8 = &.{},
        organization: [][]const u8 = &.{},
        preprocessor_version: []const u8 = "",
        originating_system: []const u8 = "",
        authorization: []const u8 = "",
    };

    pub const FileSchema = struct {
        schemas: [][]const u8 = &.{},
    };
};

/// Complete STEP file
pub const StepFile = struct {
    header: Header,
    entities: std.AutoHashMap(u32, Entity),
    /// Entities in order of appearance (for round-trip)
    entity_order: std.ArrayList(u32),
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) StepFile {
        return .{
            .header = Header{},
            .entities = std.AutoHashMap(u32, Entity).init(allocator),
            .entity_order = std.ArrayList(u32).init(allocator),
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *StepFile) void {
        // Free header allocations
        if (self.header.file_description.description.len > 0) {
            self.allocator.free(self.header.file_description.description);
        }
        if (self.header.file_schema.schemas.len > 0) {
            self.allocator.free(self.header.file_schema.schemas);
        }

        // Free entities
        var it = self.entities.valueIterator();
        while (it.next()) |entity| {
            var e = entity.*;
            e.deinit(self.allocator);
        }
        self.entities.deinit();
        self.entity_order.deinit();
    }

    pub fn getEntity(self: *const StepFile, id: u32) ?*const Entity {
        return self.entities.getPtr(id);
    }

    /// Get count of entities of a specific type
    pub fn countEntitiesOfType(self: *const StepFile, type_name: []const u8) usize {
        var count: usize = 0;
        var it = self.entities.valueIterator();
        while (it.next()) |entity| {
            if (std.mem.eql(u8, entity.type_name, type_name)) {
                count += 1;
            }
        }
        return count;
    }

    /// Get all entities of a specific type
    pub fn getEntitiesOfType(self: *const StepFile, allocator: std.mem.Allocator, type_name: []const u8) ![]Entity {
        var list = std.ArrayList(Entity).init(allocator);
        errdefer list.deinit();

        var it = self.entities.valueIterator();
        while (it.next()) |entity| {
            if (std.mem.eql(u8, entity.type_name, type_name)) {
                try list.append(entity.*);
            }
        }
        return list.toOwnedSlice();
    }
};

// Helper functions for working with parameters

/// Get entity reference from parameter
pub fn getEntityRef(param: Parameter) ?u32 {
    return switch (param) {
        .entity_ref => |id| id,
        else => null,
    };
}

/// Get integer from parameter
pub fn getInteger(param: Parameter) ?i64 {
    return switch (param) {
        .integer => |i| i,
        else => null,
    };
}

/// Get real from parameter (as f64)
pub fn getReal(param: Parameter) ?f64 {
    return switch (param) {
        .real => |r| std.fmt.parseFloat(f64, r) catch null,
        .integer => |i| @floatFromInt(i),
        else => null,
    };
}

/// Get real from parameter (as string for precision)
pub fn getRealString(param: Parameter) ?[]const u8 {
    return switch (param) {
        .real => |r| r,
        else => null,
    };
}

/// Get string from parameter
pub fn getString(param: Parameter) ?[]const u8 {
    return switch (param) {
        .string => |s| s,
        else => null,
    };
}

/// Get enumeration from parameter
pub fn getEnumeration(param: Parameter) ?[]const u8 {
    return switch (param) {
        .enumeration => |e| e,
        else => null,
    };
}

/// Get list from parameter
pub fn getList(param: Parameter) ?[]Parameter {
    return switch (param) {
        .list => |l| l,
        else => null,
    };
}

/// Check if parameter is undefined (*)
pub fn isUndefined(param: Parameter) bool {
    return param == .undefined;
}

/// Check if parameter is omitted ($)
pub fn isOmitted(param: Parameter) bool {
    return param == .omitted;
}
