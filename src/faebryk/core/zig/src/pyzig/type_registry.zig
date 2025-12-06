const std = @import("std");
const py = @import("pybindings.zig");

// Global registry for type objects to avoid creating duplicates
var type_registry = std.HashMap([]const u8, *py.PyTypeObject, std.hash_map.StringContext, std.hash_map.default_max_load_percentage).init(std.heap.c_allocator);
var registry_mutex = std.Thread.Mutex{};

// Global cache to reuse list wrappers per underlying ArrayList pointer
// No global list wrapper cache

// Helper to register a type object in the global registry
pub fn registerTypeObject(type_name: [*:0]const u8, type_obj: *py.PyTypeObject) void {
    registry_mutex.lock();
    defer registry_mutex.unlock();
    const type_name_slice = std.mem.span(type_name);
    // Make a copy of the string to ensure it lives as long as the HashMap
    const owned_key = std.heap.c_allocator.dupe(u8, type_name_slice) catch return;

    // Hold a strong reference so the type object survives until process exit.
    py.Py_INCREF(@ptrCast(type_obj));

    type_registry.put(owned_key, type_obj) catch {
        // If put fails, free the allocated key
        std.heap.c_allocator.free(owned_key);
        py.Py_DECREF(@ptrCast(type_obj));
    };
}

// Helper to get a registered type object by name
pub fn getRegisteredTypeObject(type_name: [*:0]const u8) ?*py.PyTypeObject {
    registry_mutex.lock();
    defer registry_mutex.unlock();
    const type_name_slice = std.mem.span(type_name);
    return type_registry.get(type_name_slice);
}
