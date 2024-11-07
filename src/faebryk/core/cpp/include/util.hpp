/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <cxxabi.h>
#include <memory>
#include <string>

namespace util {

template <typename T> std::string get_type_name(const T *obj) {
    int status;
    std::unique_ptr<char, void (*)(void *)> demangled_name(
        abi::__cxa_demangle(typeid(*obj).name(), nullptr, nullptr, &status), std::free);
    return demangled_name ? demangled_name.get() : "unknown type";
}

template <typename T> std::string get_type_name(const std::shared_ptr<T> &obj) {
    return get_type_name(obj.get());
}

} // namespace util
