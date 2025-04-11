cmake_minimum_required(VERSION 3.15...3.27)
set(PROJECT_BASE_NAME faebryk_core_cpp)

# editable hacks --------------------------------------------------------
if(NOT DEFINED EDITABLE)
    set(EDITABLE 0)
endif()

add_definitions(-DEDITABLE=${EDITABLE})

if(${EDITABLE})
    set(PROJECT_NAME ${PROJECT_BASE_NAME}_editable)
else()
    set(PROJECT_NAME ${PROJECT_BASE_NAME})
endif()

# boilerplate ----------------------------------------------------------
project(${PROJECT_NAME} LANGUAGES CXX)
# Currently, Scikit-build does not support FindPython, so we convert the
# provided hints ourselves.
if(SKBUILD)
    set(Python_EXECUTABLE "${PYTHON_EXECUTABLE}")
    set(Python_INCLUDE_DIR "${PYTHON_INCLUDE_DIR}")
    set(Python_LIBRARY "${PYTHON_LIBRARY}")
endif()
if (CMAKE_VERSION VERSION_LESS 3.18)
  set(DEV_MODULE Development)
else()
  set(DEV_MODULE Development.Module)
endif()
find_package(Python COMPONENTS Interpreter ${DEV_MODULE} REQUIRED)
execute_process(
  COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
  OUTPUT_STRIP_TRAILING_WHITESPACE OUTPUT_VARIABLE nanobind_ROOT)
find_package(nanobind CONFIG REQUIRED)

message(STATUS "Python_EXECUTABLE: ${Python_EXECUTABLE}")
message(STATUS "Python_INCLUDE_DIR: ${Python_INCLUDE_DIR}")
message(STATUS "Python_LIBRARY: ${Python_LIBRARY}")

# To make a debug build, run cmake with -DCMAKE_BUILD_TYPE=Debug
# or in environment: FBRK_CPP_DEBUG_BUILD=y
if (NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Choose the type of build." FORCE)
  set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS "Debug" "Release" "MinSizeRel" "RelWithDebInfo")
endif()

# configure ------------------------------------------------------------
message(STATUS "CXX Compiler ID: ${CMAKE_CXX_COMPILER_ID}")

# c++ standard
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
message(STATUS "Set CMAKE_CXX_STANDARD: ${CMAKE_CXX_STANDARD}")

# turn on optimization
message(STATUS "CMAKE_CXX_FLAGS before O2: ${CMAKE_CXX_FLAGS}")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2")
message(STATUS "CMAKE_CXX_FLAGS after O2: ${CMAKE_CXX_FLAGS}")

# if editable and GCC enable colors
if(${EDITABLE} AND CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fdiagnostics-color=always")
    message(STATUS "CMAKE_CXX_FLAGS after color: ${CMAKE_CXX_FLAGS}")
endif()

if(GLOBAL_PRINTF_DEBUG)
    add_definitions(-DGLOBAL_PRINTF_DEBUG=1)
endif()

# source files ---------------------------------------------------------
include_directories(${CMAKE_SOURCE_DIR}/include)
file(GLOB_RECURSE SOURCE_FILES 
  "${CMAKE_SOURCE_DIR}/src/*.cpp"
)


# build ----------------------------------------------------------------
nanobind_add_module(${PROJECT_NAME} ${SOURCE_FILES})
message(STATUS "Added nanobind module: ${PROJECT_NAME}")
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_20)
message(STATUS "Set target_compile_features cxx_std_20 for ${PROJECT_NAME}")

# Force /std:c++20 for MSVC target
target_compile_options(${PROJECT_NAME} PRIVATE "$<$<CXX_COMPILER_ID:MSVC>:/std:c++20>")
message(STATUS "Added /std:c++20 compile option for MSVC target ${PROJECT_NAME}")

install(TARGETS ${PROJECT_NAME} DESTINATION .)

if(${EDITABLE})
# create pyi stub file with type annotations
nanobind_add_stub(${PROJECT_NAME}_stub 
    MODULE ${PROJECT_NAME} 
    OUTPUT ${PROJECT_NAME}.pyi
    PYTHON_PATH $<TARGET_FILE_DIR:${PROJECT_NAME}>
    MARKER_FILE py.typed
    DEPENDS ${PROJECT_NAME})

#TODO currently pyi is imported into source dir by editable __init__ load
# better to do that automatically with a precommit hook or in the CI
endif()
