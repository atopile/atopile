const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const test_step = b.step("test", "Run graph tests");

    const test_filter = b.option([]const u8, "test-filter", "Filter tests by substring");

    const visitor_tests = b.addTest(.{
        .root_source_file = b.path("visitor.zig"),
        .target = target,
        .optimize = optimize,
    });
    if (test_filter) |filter| {
        visitor_tests.filters = b.dupeStrings(&.{filter});
    }
    const run_visitor = b.addRunArtifact(visitor_tests);
    test_step.dependOn(&run_visitor.step);
}
