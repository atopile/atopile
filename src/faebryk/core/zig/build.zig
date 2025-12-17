const std = @import("std");

const py_lib_name = "pyzig";

const ModuleMap = std.StringArrayHashMap(*std.Build.Module);

fn build_pyi(b: *std.Build, modules: ModuleMap, target: std.Build.ResolvedTarget, optimize: std.builtin.OptimizeMode) *std.Build.Step {
    // Build a small executable that generates the pyi files
    const pyi_exe = b.addExecutable(.{
        .name = "pyi",
        .root_source_file = b.path("src/python/pyi.zig"),
        .target = target,
        .optimize = optimize,
    });

    const pyzig_mod = b.createModule(.{
        .root_source_file = b.path("src/pyzig/lib.zig"),
    });
    pyi_exe.root_module.addImport("pyzig", pyzig_mod);

    for (modules.keys()) |name| {
        pyi_exe.root_module.addImport(name, modules.get(name).?);
    }

    // Run the executable to generate pyi files
    const run_gen = b.addRunArtifact(pyi_exe);
    // Pass the output directory as an argument
    run_gen.addArg(b.getInstallPath(.lib, "."));
    // Pass source directory for manual pyi files
    run_gen.addArg(b.path("src/python/").getPath(b));

    // Create a step that ensures the output directory exists
    const make_dir_step = b.addSystemCommand(&.{ "mkdir", "-p", b.getInstallPath(.lib, ".") });
    run_gen.step.dependOn(&make_dir_step.step);

    return &run_gen.step;
}

fn addPythonExtension(
    b: *std.Build,
    modules: ModuleMap,
    target: std.Build.ResolvedTarget,
    optimize: std.builtin.OptimizeMode,
    python_include: []const u8,
    python_lib_opt: ?[]const u8,
    python_lib_dir_opt: ?[]const u8,
    sexp_lib: *std.Build.Step.Compile,
) *std.Build.Step {
    const python_ext = b.addSharedLibrary(.{
        .name = py_lib_name,
        .root_source_file = b.path("src/python/py.zig"),
        .target = target,
        .optimize = optimize,
        .pic = true,
    });

    const pyzig_mod = b.createModule(.{
        .root_source_file = b.path("src/pyzig/lib.zig"),
    });
    python_ext.root_module.addImport("pyzig", pyzig_mod);

    for (modules.keys()) |name| {
        python_ext.root_module.addImport(name, modules.get(name).?);
    }

    // Link prebuilt sexp static library so changes in other modules don't force recompiling it.
    python_ext.linkLibrary(sexp_lib);

    python_ext.addIncludePath(.{ .cwd_relative = python_include });

    const builtin = @import("builtin");
    if (builtin.os.tag == .macos) {
        // Do not link libpython on macOS; allow undefined symbols to be
        // resolved at runtime by the Python interpreter (like distutils does).
        python_ext.linker_allow_shlib_undefined = true;
    }
    if (builtin.os.tag == .windows) {
        // On Windows, Python extension modules must link against the import library
        if (python_lib_opt) |python_lib| {
            if (python_lib_dir_opt) |lib_dir| {
                python_ext.addLibraryPath(.{ .cwd_relative = lib_dir });
            }
            python_ext.linkSystemLibrary(python_lib);
        } else {
            @panic("python-lib must be provided on Windows builds");
        }
    }

    python_ext.linkLibC();

    // Choose extension filename based on host OS at comptime
    // This value must be comptime-known for dest_sub_path.
    const ext = if (builtin.os.tag == .windows) ".pyd" else ".so";
    const install_python_ext = b.addInstallArtifact(python_ext, .{
        .dest_dir = .{ .override = .{ .custom = "lib" } },
        .dest_sub_path = py_lib_name ++ ext,
    });

    const python_ext_step = b.step("python-ext", "Build Python extension module");
    python_ext_step.dependOn(&install_python_ext.step);

    return python_ext_step;
}

fn addSexpExtension(
    b: *std.Build,
    sexp_mod: *std.Build.Module,
    sexp_lib: *std.Build.Step.Compile,
    target: std.Build.ResolvedTarget,
    optimize: std.builtin.OptimizeMode,
) *std.Build.Step {
    const sexp_ext = b.addSharedLibrary(.{
        .name = "pyzig_sexp",
        .root_source_file = b.path("src/python/sexp/init.zig"),
        .target = target,
        .optimize = optimize,
        .pic = true,
    });

    const pyzig_mod = b.createModule(.{
        .root_source_file = b.path("src/pyzig/lib.zig"),
    });
    sexp_ext.root_module.addImport("pyzig", pyzig_mod);
    sexp_ext.root_module.addImport("sexp", sexp_mod);
    sexp_ext.linkLibrary(sexp_lib);
    sexp_ext.linkLibC();

    const builtin = @import("builtin");
    const ext = if (builtin.os.tag == .windows) ".pyd" else ".so";
    const install_sexp_ext = b.addInstallArtifact(sexp_ext, .{
        .dest_dir = .{ .override = .{ .custom = "lib" } },
        .dest_sub_path = "pyzig_sexp" ++ ext,
    });

    const sexp_ext_step = b.step("python-sexp-ext", "Build sexp Python extension module");
    sexp_ext_step.dependOn(&install_sexp_ext.step);
    return sexp_ext_step;
}

fn build_python_module(
    b: *std.Build,
    modules: ModuleMap,
    target: std.Build.ResolvedTarget,
    optimize: std.builtin.OptimizeMode,
    sexp_lib: *std.Build.Step.Compile,
) *std.Build.Step {
    const python_include = b.option([]const u8, "python-include", "Python include directory path");
    const python_lib = b.option([]const u8, "python-lib", "Python library name (Windows only; e.g., python313)");
    const python_lib_dir = b.option([]const u8, "python-lib-dir", "Directory containing the Python import library (Windows only)");

    if (python_include) |include_path| {
        return addPythonExtension(b, modules, target, optimize, include_path, python_lib, python_lib_dir, sexp_lib);
    }
    // No-op step to keep a consistent return type.
    return b.step("python-ext-skip", "Skip python extension (no python-include)");
}

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const graph_mod = b.addModule("graph", .{
        .root_source_file = b.path("src/graph/lib.zig"),
    });
    const faebryk_mod = b.addModule("faebryk", .{
        .root_source_file = b.path("src/faebryk/lib.zig"),
    });
    faebryk_mod.addImport("graph", graph_mod);

    // Build sexp once as a standalone static library (PIC for shared linking).
    const sexp_lib = b.addStaticLibrary(.{
        .name = "sexp",
        .root_source_file = b.path("src/sexp/lib.zig"),
        .target = target,
        .optimize = optimize,
        .pic = true,
    });

    const install_sexp = b.addInstallArtifact(sexp_lib, .{});
    const sexp_step = b.step("sexp-lib", "Build sexp static library");
    sexp_step.dependOn(&install_sexp.step);

    // Register modules explicitly so we control which artifacts get reused.
    var modules_all = ModuleMap.init(b.allocator);
    defer modules_all.deinit();
    modules_all.put("graph", graph_mod) catch @panic("OOM registering graph module");
    modules_all.put("faebryk", faebryk_mod) catch @panic("OOM registering faebryk module");
    modules_all.put("sexp", sexp_lib.root_module) catch @panic("OOM registering sexp module");

    // Main python extension excludes sexp so graph-only edits don't rebuild it.
    var modules_main = ModuleMap.init(b.allocator);
    defer modules_main.deinit();
    modules_main.put("graph", graph_mod) catch @panic("OOM registering graph module");
    modules_main.put("faebryk", faebryk_mod) catch @panic("OOM registering faebryk module");

    // Build standalone sexp extension, main extension, and pyi (all modules).
    const sexp_ext_step = addSexpExtension(b, sexp_lib.root_module, sexp_lib, target, optimize);
    const py_ext_step = build_python_module(b, modules_main, target, optimize, sexp_lib);
    const pyi_step = build_pyi(b, modules_all, target, optimize);

    // Ensure python-ext depends on sexp ext and pyi generation so one command builds all.
    py_ext_step.dependOn(sexp_ext_step);
    py_ext_step.dependOn(pyi_step);
}
