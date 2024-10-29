/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include <nanobind/nanobind.h>

// check if c++20 is used
#if __cplusplus < 202002L
#error "C++20 is required"
#endif

namespace nb = nanobind;

#if EDITABLE
#define PYMOD(m) NB_MODULE(faebryk_core_cpp_editable, m)
#warning "EDITABLE"
#else
#define PYMOD(m) NB_MODULE(faebryk_core_cpp, m)
#endif

// -------------------------------------------------------------------------------------

int add(int i, int j) {
    return i + j;
}

PYMOD(m) {
    m.doc() = "faebryk core c++ module";

    m.def("add", &add, "A function that adds two numbers");
}
