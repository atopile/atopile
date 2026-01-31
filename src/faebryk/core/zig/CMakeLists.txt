cmake_minimum_required(VERSION 3.20)

# Python headers ---------------------------------------------------------------
find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
set(PY_INCLUDE "${Python3_INCLUDE_DIRS}")

# Windows: figure out import-lib for Zig --------------------------------------
set(ZIG_PY_LIB_NAME_ARG "")
set(ZIG_PY_LIB_DIR_ARG_USE "")
if (WIN32)
  set(PY_LIB_NAME "python${Python3_VERSION_MAJOR}${Python3_VERSION_MINOR}")
  list(GET Python3_INCLUDE_DIRS 0 _py_inc0)
  get_filename_component(_py_base "${_py_inc0}" DIRECTORY)
  set(_py_lib_dir "${_py_base}/libs")
  set(ZIG_PY_LIB_NAME_ARG -Dpython-lib=${PY_LIB_NAME})
  if (EXISTS "${_py_lib_dir}")
    set(ZIG_PY_LIB_DIR_ARG_USE -Dpython-lib-dir=${_py_lib_dir})
  endif()
  set(PYZIG_NAME "pyzig.pyd")
  set(PYZIG_SEXP_NAME "pyzig_sexp.pyd")
else()
  set(PYZIG_NAME "pyzig.so")
  set(PYZIG_SEXP_NAME "pyzig_sexp.so")
endif()

# Zig build paths --------------------------------------------------------------
set(ZIG_WORKDIR   "${CMAKE_CURRENT_SOURCE_DIR}")
set(ZIG_OUT_LIB   "${ZIG_WORKDIR}/zig-out/lib/${PYZIG_NAME}")
set(ZIG_OUT_LIB_SEXP "${ZIG_WORKDIR}/zig-out/lib/${PYZIG_SEXP_NAME}")

# macOS cross-arch setup -------------------------------------------------------
# Determine target architecture for cross-compilation. Priority:
# 1. CMAKE_OSX_ARCHITECTURES if set (from cibuildwheel/scikit-build for cross-compile)
# 2. Fall back to Python interpreter's architecture (for local dev builds)
set(ZIG_ENV_PREFIX "")
set(ZIG_TARGET_ARG "")
set(_TARGET_ARCH_FOR_STAMP "native")  # Default for non-Apple platforms

if (APPLE)
  if (CMAKE_OSX_ARCHITECTURES)
    # Cross-compilation: use the target architecture from CMAKE_OSX_ARCHITECTURES
    list(GET CMAKE_OSX_ARCHITECTURES 0 _TARGET_ARCH)
    string(TOLOWER "${_TARGET_ARCH}" _TARGET_ARCH)
    message(STATUS "Cross-compiling: CMAKE_OSX_ARCHITECTURES=${CMAKE_OSX_ARCHITECTURES}")
  else()
    # Local dev build: detect from Python interpreter
    execute_process(
      COMMAND "${Python3_EXECUTABLE}" -c "import platform; print(platform.machine())"
      OUTPUT_VARIABLE _TARGET_ARCH
      OUTPUT_STRIP_TRAILING_WHITESPACE)
    string(TOLOWER "${_TARGET_ARCH}" _TARGET_ARCH)
    message(STATUS "Local build: detected Python arch=${_TARGET_ARCH}")
  endif()

  set(_TARGET_ARCH_FOR_STAMP "${_TARGET_ARCH}")

  if (_TARGET_ARCH MATCHES "arm64" OR _TARGET_ARCH MATCHES "aarch64")
    set(_ZIG_ARCH "aarch64")
    set(_MAC_DEPLOY "11.0")      # first macOS with arm64
  else()
    set(_ZIG_ARCH "x86_64")
    set(_MAC_DEPLOY "10.13")
  endif()

  message(STATUS "Building for macOS ${_ZIG_ARCH} (target arch: ${_TARGET_ARCH})")

  execute_process(
    COMMAND xcrun --sdk macosx --show-sdk-path
    OUTPUT_VARIABLE _MAC_SDK_ROOT
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET)

  set(ZIG_ENV_PREFIX ${CMAKE_COMMAND} -E env
      MACOSX_DEPLOYMENT_TARGET=${_MAC_DEPLOY}
      SDKROOT=${_MAC_SDK_ROOT})

  set(ZIG_TARGET_ARG -Dtarget=${_ZIG_ARCH}-macos.${_MAC_DEPLOY})
endif()

# Stamp file includes target architecture to ensure different arch builds in the same
# source checkout (e.g., cibuildwheel building x86_64 and arm64) don't skip each other.
set(ZIG_BUILD_STAMP "${ZIG_WORKDIR}/zig-out/pyzig.${_TARGET_ARCH_FOR_STAMP}.build.stamp")

# custom rule to build the Zig extension --------------------------------------
add_custom_command(
  OUTPUT  "${ZIG_BUILD_STAMP}"
  COMMAND ${ZIG_ENV_PREFIX} "${Python3_EXECUTABLE}" -m ziglang build python-ext
          -Doptimize=ReleaseFast
          -Dpython-include=${PY_INCLUDE}
          ${ZIG_TARGET_ARG} ${ZIG_PY_LIB_NAME_ARG} ${ZIG_PY_LIB_DIR_ARG_USE}
  COMMAND ${CMAKE_COMMAND} -E touch "${ZIG_BUILD_STAMP}"
  WORKING_DIRECTORY "${ZIG_WORKDIR}"
  BYPRODUCTS "${ZIG_OUT_LIB}" "${ZIG_OUT_LIB_SEXP}"
  COMMENT "Building Zig Python extension"
  VERBATIM)
add_custom_target(pyzig ALL DEPENDS "${ZIG_BUILD_STAMP}")

# print current zig version
execute_process(
  COMMAND "${Python3_EXECUTABLE}" -m ziglang version
  OUTPUT_VARIABLE ZIG_VERSION
  OUTPUT_STRIP_TRAILING_WHITESPACE)
message(STATUS "Zig version: ${ZIG_VERSION}")

# wheel install location -------------------------------------------------------
execute_process(
  COMMAND "${Python3_EXECUTABLE}" -c "import sys, sysconfig; \
      print(sysconfig.get_config_var('EXT_SUFFIX') or ('.pyd' if sys.platform=='win32' else '.so'))"
  OUTPUT_VARIABLE PY_EXT_SUFFIX
  OUTPUT_STRIP_TRAILING_WHITESPACE)

set(ZIG_MODULE_BASENAME "pyzig")
install(
  FILES "${ZIG_OUT_LIB}"
  DESTINATION "${SKBUILD_PLATLIB_DIR}"
  RENAME "${ZIG_MODULE_BASENAME}${PY_EXT_SUFFIX}")

# Install the standalone sexp extension as well.
set(ZIG_MODULE_BASENAME_SEXP "pyzig_sexp")
install(
  FILES "${ZIG_OUT_LIB_SEXP}"
  DESTINATION "${SKBUILD_PLATLIB_DIR}"
  RENAME "${ZIG_MODULE_BASENAME_SEXP}${PY_EXT_SUFFIX}")
