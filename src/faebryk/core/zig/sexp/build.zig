const std = @import("std");

pub fn build_tests(b: *std.Build, target: std.Build.ResolvedTarget, optimize: std.builtin.OptimizeMode) void {
    const test_step = b.step("test", "Run unit tests");

    // Create the sexp module that includes all source files
    const sexp_mod = b.createModule(.{
        .root_source_file = b.path("src/sexp.zig"),
    });

    // Automatically discover test files
    const test_dir_path = b.pathFromRoot("test");
    var test_dir = std.fs.openDirAbsolute(test_dir_path, .{ .iterate = true }) catch |err| {
        std.debug.print("Failed to open test directory: {}\n", .{err});
        return;
    };
    defer test_dir.close();

    var iterator = test_dir.iterate();
    while (iterator.next() catch null) |entry| {
        // Look for test_*.zig files
        if (entry.kind == .file and
            std.mem.startsWith(u8, entry.name, "test_") and
            std.mem.endsWith(u8, entry.name, ".zig"))
        {
            const test_path = b.fmt("test/{s}", .{entry.name});
            const _test = b.addTest(.{
                .root_source_file = b.path(test_path),
                .target = target,
                .optimize = optimize,
            });

            // Add only the sexp module to the test
            _test.root_module.addImport("sexp", sexp_mod);

            const run_test = b.addRunArtifact(_test);
            test_step.dependOn(&run_test.step);
        }
    }

    // Add option to run a single test file
    const test_file = b.option([]const u8, "test-file", "Run a specific test file");
    if (test_file) |file| {
        const single_test_step = b.step("test-single", "Run a single test file");

        const test_path = b.fmt("test/{s}", .{file});
        const single_test = b.addTest(.{
            .root_source_file = b.path(test_path),
            .target = target,
            .optimize = optimize,
        });
        single_test.root_module.addImport("sexp", sexp_mod);

        const run_single_test = b.addRunArtifact(single_test);
        single_test_step.dependOn(&run_single_test.step);
    }
}

pub fn build_performance(b: *std.Build, target: std.Build.ResolvedTarget, optimize: std.builtin.OptimizeMode) void {
    const PERF_ROOT = "test/performance";

    const prettytable_dep = b.dependency("prettytable", .{
        .target = target,
        .optimize = optimize,
    });

    const sexp_mod = b.createModule(.{
        .root_source_file = b.path("src/sexp.zig"),
    });

    // Build performance_sexp executable
    const perf_sexp = b.addExecutable(.{
        .name = "performance_sexp",
        .root_source_file = b.path(PERF_ROOT ++ "/performance_sexp.zig"),
        .target = target,
        .optimize = optimize,
    });
    perf_sexp.root_module.addImport("sexp", sexp_mod);
    b.installArtifact(perf_sexp);

    // Build performance_sexp_synthetic executable
    const perf_synthetic = b.addExecutable(.{
        .name = "performance_sexp_synthetic",
        .root_source_file = b.path(PERF_ROOT ++ "/performance_sexp_synthetic.zig"),
        .target = target,
        .optimize = optimize,
    });
    perf_synthetic.root_module.addImport("sexp", sexp_mod);
    perf_synthetic.root_module.addImport("prettytable", prettytable_dep.module("prettytable"));
    b.installArtifact(perf_synthetic);

    // Add run steps for both performance tests
    const run_perf_sexp = b.addRunArtifact(perf_sexp);
    if (b.args) |args| {
        run_perf_sexp.addArgs(args);
    }

    const run_perf_synthetic = b.addRunArtifact(perf_synthetic);

    const perf_step = b.step("perf", "Run performance tests");
    perf_step.dependOn(&run_perf_sexp.step);

    const perf_synthetic_step = b.step("perf-synthetic", "Run synthetic performance test");
    perf_synthetic_step.dependOn(&run_perf_synthetic.step);
}

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Export the sexp module for other packages to use
    _ = b.addModule("sexp", .{
        .root_source_file = b.path("src/sexp.zig"),
    });

    // Build a library from the source files
    const lib = b.addStaticLibrary(.{
        .name = "sexp",
        .root_source_file = b.path("src/sexp.zig"),
        .target = target,
        .optimize = optimize,
    });
    b.installArtifact(lib);

    build_tests(b, target, optimize);
    build_performance(b, target, optimize);
}
