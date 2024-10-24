cmake_minimum_required(VERSION 3.30)

# if not defined, set default
if(NOT DEFINED EDITABLE)
    set(EDITABLE 0)
endif()

add_definitions(-DEDITABLE=${EDITABLE})

if(${EDITABLE})
    set(PROJECT_NAME faebryk_core_cpp_editable)
else()
    set(PROJECT_NAME faebryk_core_cpp)
endif()

# boilerplate ----------------------------------------------------------
project(${PROJECT_NAME} LANGUAGES CXX)
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

# configure ------------------------------------------------------------
set(CMAKE_CXX_STANDARD 20)
# turn on optimization
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2")
# TODO remove
# enable debug symbols
set(CMAKE_BUILD_TYPE Debug)

# source files ---------------------------------------------------------
include_directories(${CMAKE_SOURCE_DIR}/include)
set(SOURCE_FILES src/main.cpp)

# build ----------------------------------------------------------------
pybind11_add_module(${PROJECT_NAME} ${SOURCE_FILES})
install(TARGETS ${PROJECT_NAME} DESTINATION .)
