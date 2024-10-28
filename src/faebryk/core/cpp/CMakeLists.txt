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
set(PYBIND11_FINDPYTHON OFF)
find_package(Python COMPONENTS Interpreter Development.Module)
find_package(pybind11 CONFIG REQUIRED)

# configure ------------------------------------------------------------
# c++ standard
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
# turn on optimization
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2")
# enable debug symbols
if(${EDITABLE})
    set(CMAKE_BUILD_TYPE Debug)
else()
    set(CMAKE_BUILD_TYPE Release)
endif()

# source files ---------------------------------------------------------
include_directories(${CMAKE_SOURCE_DIR}/include)
set(SOURCE_FILES src/main.cpp)

# build ----------------------------------------------------------------
pybind11_add_module(${PROJECT_NAME} ${SOURCE_FILES})
install(TARGETS ${PROJECT_NAME} DESTINATION .)
