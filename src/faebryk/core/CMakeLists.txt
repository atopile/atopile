cmake_minimum_required(VERSION 3.20)
project(faebryk_core_super LANGUAGES C CXX)

# Build the existing C++ module via nanobind
add_subdirectory(cpp)

# Discover Python to get include/lib info for the Zig extension
find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)

# Python include
set(PY_INCLUDE "${Python3_INCLUDE_DIRS}")

# Compute Python lib name and (on Windows) the libs directory
if(WIN32)
  # e.g. python313
  set(PY_LIB_NAME "python${Python3_VERSION_MAJOR}${Python3_VERSION_MINOR}")
  # Derive base from the first include path: .../cpython-3.13.x-.../Include -> base
  list(GET Python3_INCLUDE_DIRS 0 PY_INC0)
  get_filename_component(_py_base "${PY_INC0}" DIRECTORY)
  set(PY_LIB_DIR "${_py_base}/libs")
  if(EXISTS "${PY_LIB_DIR}")
    set(ZIG_PY_LIB_DIR_ARG "-Dpython-lib-dir=${PY_LIB_DIR}")
  else()
    set(ZIG_PY_LIB_DIR_ARG "")
  endif()
  set(PYZIG_NAME "pyzig.pyd")
else()
  # e.g. python3.13
  set(PY_LIB_NAME "python${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}")
  set(ZIG_PY_LIB_DIR_ARG "")
  set(PYZIG_NAME "pyzig.so")
endif()

# Paths for the Zig experiment build
set(ZIG_WORKDIR "${CMAKE_CURRENT_SOURCE_DIR}/zig/experiment")
set(ZIG_OUT_LIB "${ZIG_WORKDIR}/zig-out/lib/${PYZIG_NAME}")
# Use a stamp file as the custom command OUTPUT to avoid multiple-rule conflicts
set(ZIG_BUILD_STAMP "${ZIG_WORKDIR}/zig-out/pyzig.build.stamp")

# Build the Zig extension via ziglang module (ensures zig is available in build env)
# Construct OS-conditional args explicitly to avoid generator-expression quoting issues
set(ZIG_PY_LIB_NAME_ARG "")
set(ZIG_PY_LIB_DIR_ARG_USE "")
if(WIN32)
  set(ZIG_PY_LIB_NAME_ARG -Dpython-lib=${PY_LIB_NAME})
  set(ZIG_PY_LIB_DIR_ARG_USE ${ZIG_PY_LIB_DIR_ARG})
endif()

# On macOS, ensure a compatible deployment target so delocate matches wheel tag
set(ZIG_ENV_PREFIX)
if(APPLE)
  set(_MAC_DEPLOY "$ENV{MACOSX_DEPLOYMENT_TARGET}")
  if(NOT _MAC_DEPLOY)
    # Default per arch: x86_64 -> 10.13, arm64 -> 11.0
    if(CMAKE_OSX_ARCHITECTURES MATCHES "arm64" OR CMAKE_SYSTEM_PROCESSOR STREQUAL "arm64")
      set(_MAC_DEPLOY "11.0")
    else()
      set(_MAC_DEPLOY "10.13")
    endif()
  endif()
  
  # Determine target arch from build context (prefer explicit arch hints), not host
  unset(_ZIG_ARCH)
  if(DEFINED CMAKE_OSX_ARCHITECTURES AND NOT CMAKE_OSX_ARCHITECTURES STREQUAL "")
    if(CMAKE_OSX_ARCHITECTURES MATCHES "x86_64")
      set(_ZIG_ARCH "x86_64")
    elseif(CMAKE_OSX_ARCHITECTURES MATCHES "arm64")
      set(_ZIG_ARCH "aarch64")
    endif()
  endif()

  if(NOT DEFINED _ZIG_ARCH)
    if(DEFINED ENV{CIBW_ARCHS_MACOS})
      string(FIND "$ENV{CIBW_ARCHS_MACOS}" "x86_64" _idx)
      if(NOT _idx EQUAL -1)
        set(_ZIG_ARCH "x86_64")
      endif()
      if(NOT DEFINED _ZIG_ARCH)
        string(FIND "$ENV{CIBW_ARCHS_MACOS}" "arm64" _idx2)
        if(NOT _idx2 EQUAL -1)
          set(_ZIG_ARCH "aarch64")
        endif()
      endif()
    elseif(DEFINED ENV{CIBW_ARCHS})
      string(FIND "$ENV{CIBW_ARCHS}" "x86_64" _idx3)
      if(NOT _idx3 EQUAL -1)
        set(_ZIG_ARCH "x86_64")
      endif()
      if(NOT DEFINED _ZIG_ARCH)
        string(FIND "$ENV{CIBW_ARCHS}" "arm64" _idx4)
        if(NOT _idx4 EQUAL -1)
          set(_ZIG_ARCH "aarch64")
        endif()
      endif()
    endif()
  endif()

  if(NOT DEFINED _ZIG_ARCH AND DEFINED ENV{ARCHFLAGS})
    if("$ENV{ARCHFLAGS}" MATCHES "-arch[ ]+x86_64")
      set(_ZIG_ARCH "x86_64")
    elseif("$ENV{ARCHFLAGS}" MATCHES "-arch[ ]+arm64")
      set(_ZIG_ARCH "aarch64")
    endif()
  endif()

  if(NOT DEFINED _ZIG_ARCH)
    # Last resort: query Python's machine (can be wrong on cross builds)
    execute_process(
      COMMAND "${Python3_EXECUTABLE}" -c "import platform;print(platform.machine())"
      OUTPUT_VARIABLE _PY_MACHINE
      OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    if(_PY_MACHINE MATCHES "^(x86_64|i386)$")
      set(_ZIG_ARCH "x86_64")
    elseif(_PY_MACHINE MATCHES "^(arm64|aarch64)$")
      set(_ZIG_ARCH "aarch64")
    endif()
  endif()

  if(NOT DEFINED _ZIG_ARCH)
    # Fallback to host
    if(CMAKE_SYSTEM_PROCESSOR STREQUAL "arm64")
      set(_ZIG_ARCH "aarch64")
    else()
      set(_ZIG_ARCH "x86_64")
    endif()
  endif()

  # Ensure deployment target default matches arch
  if(NOT _MAC_DEPLOY)
    if(_ZIG_ARCH STREQUAL "x86_64")
      set(_MAC_DEPLOY "10.13")
    else()
      set(_MAC_DEPLOY "11.0")
    endif()
  endif()

  # Find SDK root for cross-arch builds
  execute_process(
    COMMAND xcrun --sdk macosx --show-sdk-path
    OUTPUT_VARIABLE _MAC_SDK_ROOT
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
  )

  # Prefix build with env var export for Zig subprocess (deployment target + SDKROOT)
  if(_MAC_SDK_ROOT)
    set(ZIG_ENV_PREFIX ${CMAKE_COMMAND} -E env MACOSX_DEPLOYMENT_TARGET=${_MAC_DEPLOY} SDKROOT=${_MAC_SDK_ROOT})
  else()
    set(ZIG_ENV_PREFIX ${CMAKE_COMMAND} -E env MACOSX_DEPLOYMENT_TARGET=${_MAC_DEPLOY})
  endif()

  # Provide an explicit Zig target triple including deployment target so the
  # produced dylib carries the correct LC_VERSION_MIN_MACOSX
  set(ZIG_TARGET_ARG -Dtarget=${_ZIG_ARCH}-macos.${_MAC_DEPLOY})
endif()
add_custom_command(
  OUTPUT "${ZIG_BUILD_STAMP}"
  COMMAND ${ZIG_ENV_PREFIX} "${Python3_EXECUTABLE}" -m ziglang build python-ext -Doptimize=ReleaseFast
          -Dpython-include=${PY_INCLUDE}
          ${ZIG_TARGET_ARG}
          ${ZIG_PY_LIB_NAME_ARG}
          ${ZIG_PY_LIB_DIR_ARG_USE}
  COMMAND ${CMAKE_COMMAND} -E touch "${ZIG_BUILD_STAMP}"
  WORKING_DIRECTORY "${ZIG_WORKDIR}"
  BYPRODUCTS "${ZIG_OUT_LIB}"
  COMMENT "Building Zig Python extension"
  VERBATIM
)
add_custom_target(pyzig ALL DEPENDS "${ZIG_BUILD_STAMP}")

# Compute Python extension suffix for proper filename (e.g., .cpython-313-x86_64-linux-gnu.so)
execute_process(
  COMMAND "${Python3_EXECUTABLE}" -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX') or '')"
  OUTPUT_VARIABLE PY_EXT_SUFFIX
  OUTPUT_STRIP_TRAILING_WHITESPACE
)
if(NOT PY_EXT_SUFFIX)
  if(WIN32)
    set(PY_EXT_SUFFIX ".pyd")
  else()
    set(PY_EXT_SUFFIX ".so")
  endif()
endif()

# Base name for the shipped Zig module at wheel root
set(ZIG_MODULE_BASENAME "pyzig")

# Install the Zig artifacts into the wheel root (platlib) with ABI suffix naming
set(WHEEL_ROOT "${SKBUILD_PLATLIB_DIR}")
install(FILES "${ZIG_OUT_LIB}"
        DESTINATION "${WHEEL_ROOT}/./"
        RENAME "${ZIG_MODULE_BASENAME}${PY_EXT_SUFFIX}")
