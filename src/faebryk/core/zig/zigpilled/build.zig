const std = @import("std");

pub fn build(b: *std.Build) void {
    // Standard target options allows the person running `zig build` to choose
    // what target to build for. Here we do not override the defaults, which
    // means any target is allowed, and the default is native. Other options
    // for restricting supported target set are available.
    const target = b.standardTargetOptions(.{});

    // Standard optimization options allow the person running `zig build` to select
    // between Debug, ReleaseSafe, ReleaseFast, and ReleaseSmall. Here we do not
    // set a preferred release mode, allowing the user to decide how to optimize.
    const optimize = b.standardOptimizeOption(.{});

    const exe = b.addExecutable(.{
        .name = "zigpilled",
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });

    // This declares intent for the executable to be installed into the
    // standard location when the user invokes the "install" step (the default
    // step when running `zig build`).
    b.installArtifact(exe);

    // This *creates* a Run step in the build graph, to be executed when another
    // step is evaluated that depends on it. The next line below will establish
    // such a dependency.
    const run_cmd = b.addRunArtifact(exe);

    // By making the run step depend on the install step, it will be run from the
    // installation directory rather than directly from within the cache directory.
    // This is not necessary, however, if the application depends on other installed
    // files, this ensures they will be present and in the expected location.
    run_cmd.step.dependOn(b.getInstallStep());

    // This allows the user to pass arguments to the application in the build
    // command itself, like this: `zig build run -- arg1 arg2 etc`
    if (b.args) |args| {
        run_cmd.addArgs(args);
    }

    // This creates a build step. It will be visible in the `zig build --help` menu,
    // and can be selected like this: `zig build run`
    // This will evaluate the `run` step rather than the default, which is "install".
    const run_step = b.step("run", "Run the app");
    run_step.dependOn(&run_cmd.step);

    // Creates a step for unit testing. This only builds the test executable
    // but does not run it.
    const unit_tests = b.addTest(.{
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });

    const run_unit_tests = b.addRunArtifact(unit_tests);

    // Add tokenizer tests
    const tokenizer_tests = b.addTest(.{
        .root_source_file = b.path("src/sexp/tokenizer_test.zig"),
        .target = target,
        .optimize = optimize,
    });

    const run_tokenizer_tests = b.addRunArtifact(tokenizer_tests);

    // Add ato file test
    const ato_file_test = b.addTest(.{
        .root_source_file = b.path("src/sexp/test_ato_file.zig"),
        .target = target,
        .optimize = optimize,
    });

    const run_ato_file_test = b.addRunArtifact(ato_file_test);

    // Similar to creating the run step earlier, this exposes a `test` step to
    // the `zig build --help` menu, providing a way for the user to request
    // running the unit tests.
    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_unit_tests.step);
    test_step.dependOn(&run_tokenizer_tests.step);
    test_step.dependOn(&run_ato_file_test.step);

    // Add a specific step for testing the tokenizer
    const test_tokenizer_step = b.step("test-tokenizer", "Run tokenizer tests");
    test_tokenizer_step.dependOn(&run_tokenizer_tests.step);

    // Add executable for testing ato file
    const test_ato = b.addExecutable(.{
        .name = "test_ato",
        .root_source_file = b.path("src/sexp/test_ato_file.zig"),
        .target = target,
        .optimize = optimize,
    });

    b.installArtifact(test_ato);

    const run_test_ato = b.addRunArtifact(test_ato);
    const test_ato_step = b.step("test-ato", "Test tokenizer with ato.kicad_pcb file");
    test_ato_step.dependOn(&run_test_ato.step);
}