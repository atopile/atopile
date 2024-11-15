/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <cxxabi.h>
#include <memory>
#include <sstream>
#include <string>

#if GLOBAL_PRINTF_DEBUG
#else
#define printf(...)
#endif

namespace util {

template <typename T> inline std::string get_type_name(const T *obj) {
    int status;
    std::unique_ptr<char, void (*)(void *)> demangled_name(
        abi::__cxa_demangle(typeid(*obj).name(), nullptr, nullptr, &status), std::free);
    return demangled_name ? demangled_name.get() : "unknown type";
}

template <typename T> inline std::string get_type_name(const std::shared_ptr<T> &obj) {
    return get_type_name(obj.get());
}

inline std::string formatted_ptr(void *ptr) {
    std::stringstream ss;
    ss << std::hex << std::uppercase << reinterpret_cast<uintptr_t>(ptr);
    auto out = ss.str();
    return "*" + out.substr(out.size() - 4);
}

// TODO not really used
// template <typename T> inline std::string str_vec(const std::vector<T> &vec) {
//    std::stringstream ss;
//    ss << "[";
//    for (size_t i = 0; i < vec.size(); ++i) {
//        // if T is string just put it into stream directly
//        if constexpr (std::is_same_v<T, std::string>) {
//            ss << '"' << vec[i] << '"';
//        } else {
//            ss << vec[i].str();
//        }
//        if (i < vec.size() - 1) {
//            ss << ", ";
//        }
//    }
//    ss << "]";
//    return ss.str();
//}

} // namespace util
