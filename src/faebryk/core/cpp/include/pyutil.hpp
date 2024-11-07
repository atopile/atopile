/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <algorithm>
#include <nanobind/nanobind.h>

namespace nb = nanobind;

namespace pyutil {

// TODO avoid calling these functions
//  instance checks can be done without a python call by recreating the type tree in C++
// (for graph objects ofc)

inline bool isinstance(nb::object obj, nb::type_object type) {
    // Call the Python isinstance function
    nb::object isinstance_func = nb::module_::import_("builtins").attr("isinstance");
    return nb::cast<bool>(isinstance_func(obj, type));
}

inline bool isinstance(nb::object obj, std::vector<nb::type_object> types) {
    return std::any_of(types.begin(), types.end(), [obj](auto type) {
        return isinstance(obj, type);
    });
}

} // namespace pyutil
