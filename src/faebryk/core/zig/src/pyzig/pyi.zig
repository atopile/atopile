const std = @import("std");

pub const PyiGenerator = struct {
    allocator: std.mem.Allocator,
    output: std.ArrayList(u8),

    const Self = @This();

    pub fn init(allocator: std.mem.Allocator) Self {
        return Self{
            .allocator = allocator,
            .output = std.ArrayList(u8).init(allocator),
        };
    }

    pub fn deinit(self: *Self) void {
        self.output.deinit();
    }

    fn generateFunctionParameters(self: *Self, comptime fn_info: std.builtin.Type.Fn, comptime skip_first: bool) !void {
        var first_param = true;

        inline for (fn_info.params, 0..) |param, i| {
            if (param.type) |param_type| {
                // Skip first parameter if it's self
                if (skip_first and i == 0) continue;

                if (!first_param) {
                    try self.output.writer().print(", ", .{});
                }
                first_param = false;

                // Calculate the parameter index (adjusted for skipped params)
                const param_index = if (skip_first) i - 1 else i;

                // TODO: currently zig can't reflect on parameter names
                const param_name = std.fmt.comptimePrint("arg_{d}", .{param_index});
                try self.output.writer().print("{s}: ", .{param_name});
                try self.writeZigTypeToPython(self.output.writer(), param_type);
            }
        }
    }

    fn writeZigTypeToPython(self: *Self, writer: anytype, comptime T: type) !void {
        const ti = @typeInfo(T);
        // Treat std.DoublyLinkedList(T) as list[T]
        if (ti == .@"struct" and @hasField(T, "first") and @hasField(T, "last") and @hasDecl(T, "Node")) {
            const NodeType = T.Node;
            const Elem = std.meta.FieldType(NodeType, .data);
            try writer.writeAll("list[");
            try self.writeZigTypeToPython(writer, Elem);
            try writer.writeAll("]");
            return;
        }
        switch (ti) {
            .int => |int_info| {
                try writer.writeAll(if (int_info.signedness == .signed) "int" else "int");
            },
            .float => try writer.writeAll("float"),
            .bool => try writer.writeAll("bool"),
            .pointer => |ptr_info| {
                if (ptr_info.size == .slice) {
                    if (ptr_info.child == u8) {
                        try writer.writeAll("str");
                    } else {
                        // Handle slices as lists
                        try writer.writeAll("list[");
                        try self.writeZigTypeToPython(writer, ptr_info.child);
                        try writer.writeAll("]");
                    }
                } else {
                    try writer.writeAll("Any");
                }
            },
            .@"struct" => {
                const full_name = @typeName(T);
                // Remove module path from type name if present
                const clean_name = if (std.mem.lastIndexOf(u8, full_name, ".")) |idx|
                    full_name[idx + 1 ..]
                else
                    full_name;
                try writer.writeAll(clean_name);
            },
            .@"enum" => {
                // Enums are handled as strings in Python bindings
                // For now, enums are strings at runtime
                try writer.writeAll("str");
            },
            .optional => |opt_info| {
                try self.writeZigTypeToPython(writer, opt_info.child);
                try writer.writeAll(" | None");
            },
            .array => |arr_info| {
                try writer.writeAll("list[");
                try self.writeZigTypeToPython(writer, arr_info.child);
                try writer.writeAll("]");
            },
            .void => try writer.writeAll("None"),
            else => try writer.writeAll("Any"),
        }
    }

    fn generateEnumDefinition(self: *Self, comptime T: type) !void {
        const type_info = @typeInfo(T);
        if (type_info != .@"enum") return;

        const enum_info = type_info.@"enum";
        const class_name = @typeName(T);

        // Remove module path from class name if present
        const clean_name = if (std.mem.lastIndexOf(u8, class_name, ".")) |idx|
            class_name[idx + 1 ..]
        else
            class_name;

        // Generate as proper Enum class
        try self.output.writer().print("class {s}(str, Enum):\n", .{clean_name});

        inline for (enum_info.fields) |field| {
            // Convert field name to valid Python identifier
            try self.output.writer().print("    ", .{});

            // Handle field names - replace spaces/hyphens with underscores
            // and convert to uppercase
            for (field.name) |c| {
                if (c >= 'a' and c <= 'z') {
                    try self.output.writer().print("{c}", .{c - 32}); // Convert to uppercase
                } else if (c >= 'A' and c <= 'Z' or c >= '0' and c <= '9' or c == '_') {
                    try self.output.writer().print("{c}", .{c}); // Keep as is
                } else {
                    // Replace any other character (spaces, hyphens, etc) with underscore
                    try self.output.writer().print("_", .{});
                }
            }
            try self.output.writer().print(" = \"{s}\"\n", .{field.name});
        }
        try self.output.writer().print("\n", .{});
    }

    fn generateStructDefinition(self: *Self, comptime T: type) !void {
        const type_info = @typeInfo(T);
        if (type_info != .@"struct") return;

        const struct_info = type_info.@"struct";
        const class_name = @typeName(T);

        // Remove module path from class name if present
        const clean_name = if (std.mem.lastIndexOf(u8, class_name, ".")) |idx|
            class_name[idx + 1 ..]
        else
            class_name;

        try self.output.writer().print("class {s}:\n", .{clean_name});

        // Generate field annotations
        inline for (struct_info.fields) |field| {
            try self.output.writer().print("    {s}: ", .{field.name});
            try self.writeZigTypeToPython(self.output.writer(), field.type);
            try self.output.writer().print("\n", .{});
        }

        try self.output.writer().print("\n", .{});

        // Generate __init__ method
        try self.output.writer().print("    def __init__(self", .{});
        if (struct_info.fields.len > 0) {
            try self.output.writer().print(", *", .{});
        }
        inline for (struct_info.fields) |field| {
            try self.output.writer().print(", {s}: ", .{field.name});
            try self.writeZigTypeToPython(self.output.writer(), field.type);
        }
        try self.output.writer().print(") -> None: ...\n", .{});

        // Generate __repr__ method
        try self.output.writer().print("    def __repr__(self) -> str: ...\n", .{});

        try self.output.writer().print("    @staticmethod\n", .{});
        try self.output.writer().print("    def __field_names__() -> list[str]: ...\n", .{});
        try self.output.writer().print("    def __zig_address__(self) -> int: ...\n", .{});

        // Generate methods
        inline for (struct_info.decls) |decl| {
            {
                const func = @field(T, decl.name);
                const func_type_info = @typeInfo(@TypeOf(func));

                switch (func_type_info) {
                    .@"fn" => |fn_info| {
                        // Skip if it's not a method (doesn't take self as first parameter)
                        if (fn_info.params.len == 0) continue;

                        const first_param_type_info = @typeInfo(fn_info.params[0].type.?);
                        const is_method = switch (first_param_type_info) {
                            .pointer => |ptr_info| ptr_info.child == T,
                            else => false,
                        };

                        if (is_method) {
                            try self.output.writer().print("    def {s}(self", .{decl.name});
                            // Add comma if there are additional parameters beyond self
                            if (fn_info.params.len > 1) {
                                try self.output.writer().print(", ", .{});
                            }
                            try self.generateFunctionParameters(fn_info, true); // Skip first param (self)
                            try self.output.writer().print(") -> ", .{});
                            if (fn_info.return_type) |ret_type| {
                                try self.writeZigTypeToPython(self.output.writer(), ret_type);
                            } else {
                                try self.output.writer().print("None", .{});
                            }
                            try self.output.writer().print(": ...\n", .{});
                        }
                    },
                    else => {},
                }
            }
        }

        try self.output.writer().print("\n", .{});
    }

    fn generateFunctionDefinitions(self: *Self, comptime T: type) !void {
        const root_type_info = @typeInfo(T);
        switch (root_type_info) {
            .@"struct" => |struct_info| {
                inline for (struct_info.decls) |decl| {
                    {
                        const func = @field(T, decl.name);
                        const func_type_info = @typeInfo(@TypeOf(func));

                        switch (func_type_info) {
                            .@"fn" => |fn_info| {
                                // Skip struct methods (they're handled in generateStructDefinition)
                                const is_standalone_fn = blk: {
                                    if (fn_info.params.len == 0) break :blk true;

                                    const first_param_type_info = @typeInfo(fn_info.params[0].type.?);
                                    const is_struct_method = switch (first_param_type_info) {
                                        .pointer => |ptr_info| {
                                            const child_type_info = @typeInfo(ptr_info.child);
                                            switch (child_type_info) {
                                                .@"struct" => true,
                                                else => false,
                                            }
                                        },
                                        else => false,
                                    };
                                    break :blk !is_struct_method;
                                };

                                if (is_standalone_fn) {
                                    try self.output.writer().print("def {s}(", .{decl.name});
                                    try self.generateFunctionParameters(fn_info, false); // Don't skip any params
                                    try self.output.writer().print(") -> ", .{});
                                    if (fn_info.return_type) |ret_type| {
                                        try self.writeZigTypeToPython(self.output.writer(), ret_type);
                                    } else {
                                        try self.output.writer().print("None", .{});
                                    }
                                    try self.output.writer().print(": ...\n", .{});
                                }
                            },
                            else => {},
                        }
                    }
                }
            },
            else => {},
        }
    }

    pub fn generate(self: *Self, comptime T: type) ![]const u8 {
        //header
        try self.output.writer().print("from typing import Any  # noqa: F401\n", .{});
        try self.output.writer().print("from enum import Enum  # noqa: F401\n\n", .{});

        try self.output.writer().print("# Dirty hack to not error in ruff check\n", .{});
        try self.output.writer().print("type Allocator = Any\n\n", .{});

        // First generate enum definitions
        const root_type_info = @typeInfo(T);
        switch (root_type_info) {
            .@"struct" => |struct_info| {
                inline for (struct_info.decls) |decl| {
                    {
                        const decl_type = @TypeOf(@field(T, decl.name));
                        const decl_type_info = @typeInfo(decl_type);

                        switch (decl_type_info) {
                            .type => {
                                const actual_type = @field(T, decl.name);
                                const actual_type_info = @typeInfo(actual_type);

                                switch (actual_type_info) {
                                    .@"enum" => {
                                        // Only generate enums that start with E_ (our naming convention)
                                        if (std.mem.startsWith(u8, decl.name, "E_")) {
                                            try self.generateEnumDefinition(actual_type);
                                        }
                                    },
                                    else => {},
                                }
                            },
                            else => {},
                        }
                    }
                }
            },
            else => {},
        }

        // Generate struct definitions
        switch (root_type_info) {
            .@"struct" => |struct_info| {
                inline for (struct_info.decls) |decl| {
                    {
                        const decl_type = @TypeOf(@field(T, decl.name));
                        const decl_type_info = @typeInfo(decl_type);

                        switch (decl_type_info) {
                            .type => {
                                const actual_type = @field(T, decl.name);
                                const actual_type_info = @typeInfo(actual_type);

                                switch (actual_type_info) {
                                    .@"struct" => {
                                        try self.generateStructDefinition(actual_type);
                                    },
                                    else => {},
                                }
                            },
                            else => {},
                        }
                    }
                }
            },
            else => {},
        }

        // Generate standalone function definitions
        try self.generateFunctionDefinitions(T);

        return self.output.toOwnedSlice();
    }
};
