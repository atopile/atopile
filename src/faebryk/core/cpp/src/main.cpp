/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include <pybind11/pybind11.h>

// check if c++20 is used
#if __cplusplus < 202002L
#error "C++20 is required"
#endif

namespace py = pybind11;

int add(int i, int j) {
    return i + j;
}

#if EDITABLE
#define PYMOD(m) PYBIND11_MODULE(faebryk_core_cpp_editable, m)
#warning "EDITABLE"
#else
#define PYMOD(m) PYBIND11_MODULE(faebryk_core_cpp, m)
#endif

PYMOD(m) {
    m.doc() = "faebryk core c++ module";

    m.def("add", &add, "A function that adds two numbers");
}
