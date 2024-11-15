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

inline bool issubclass(nb::handle obj, nb::type_object type) {
    nb::object issubclass_func = nb::module_::import_("builtins").attr("issubclass");
    return nb::cast<bool>(issubclass_func(obj, type));
}

inline std::string get_name(nb::handle type) {
    auto out = std::string(nb::repr(type.attr("__name__")).c_str());
    // extract ClassName
    // remove quotes
    auto pos = out.find_first_of('\'');
    if (pos != std::string::npos) {
        out = out.substr(pos + 1, out.size() - 2);
    }
    return out;
}

template <typename T> inline std::string get_typename(T *obj) {
    auto instance = nb::find(obj);
    if (!instance.is_valid()) {
        return std::string("unknown type");
    }
    auto type = instance.type();
    return get_name(type);
}

/**
 * @brief Only works if T is the actual type (not a base class)
 *
 * @tparam T
 * @param obj
 * @return true
 * @return false
 */
template <typename T> inline bool is_cpp_type(T *obj) {
    auto instance = nb::find(obj);
    if (!instance.is_valid()) {
        return true;
    }
    auto pytype = instance.type();
    assert(nb::type_check(pytype));
    auto cpy_type = nb::type<T>();
    return cpy_type.is(pytype);
}

} // namespace pyutil
