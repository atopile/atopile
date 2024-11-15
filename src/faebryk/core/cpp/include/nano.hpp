/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <nanobind/nanobind.h>

// TODO this all should not really be necessary
//  seems like we have a similar issue
//  https://github.com/wjakob/nanobind/issues/668

namespace nb = nanobind;

// Fix for nanobind new override
template <typename Func, typename Sig = nb::detail::function_signature_t<Func>>
struct new__;

// 0-arg function
template <typename Func, typename Return> struct new__<Func, Return()> {
    std::remove_reference_t<Func> func;

    new__(Func &&f)
      : func((nb::detail::forward_t<Func>)f) {
    }

    template <typename Class, typename... Extra>
    NB_INLINE void execute(Class &cl, const Extra &...extra) {
        nb::detail::wrap_base_new(cl, false);

        auto wrapper_cls = [func =
                                (nb::detail::forward_t<Func>)func](nb::type_object h) {
            // printf("Called wrapper_cls with %s\n", nb::type_name(h).c_str());
            return func();
        };
        auto wrapper = [func = (nb::detail::forward_t<Func>)func]() {
            throw std::runtime_error("Called wrapper in 0-arg function");
            return func();
        };

        cl.def_static("__new__", std::move(wrapper), extra...);
        cl.def_static("__new__", std::move(wrapper_cls), nb::arg("cls"), extra...);
        cl.def(
            "__init__",
            [](nb::handle) {
                // throw std::runtime_error("Called init in 0-arg function");
            },
            extra...);
    }
};

// function with arguments
template <typename Func, typename Return, typename FirstArg, typename... Args>
struct new__<Func, Return(FirstArg, Args...)> {
    std::remove_reference_t<Func> func;

    new__(Func &&f)
      : func((nb::detail::forward_t<Func>)f) {
    }

    template <typename Class, typename... Extra>
    NB_INLINE void execute(Class &cl, const Extra &...extra) {
        nb::detail::wrap_base_new(cl, sizeof...(Args) != 0);

        constexpr bool is_first_arg_type_object =
            std::is_same_v<FirstArg, nb::type_object>;

        // function that needs cls as first argument
        if constexpr (is_first_arg_type_object) {
            auto wrapper = [func = (nb::detail::forward_t<Func>)func](nb::type_object h,
                                                                      Args... args) {
                // printf("Called wrapper with %s\n", nb::type_name(h).c_str());
                return func(h, (nb::detail::forward_t<Args>)args...);
            };
            auto wrapper_nocls = [func =
                                      (nb::detail::forward_t<Func>)func](Args... args) {
                throw std::runtime_error("Called wrapper_nocls");
            };

            cl.def_static("__new__", std::move(wrapper_nocls), extra...);
            cl.def_static("__new__", std::move(wrapper), nb::arg("cls"), extra...);
            cl.def(
                "__init__",
                [](nb::handle, Args...) {
                    // throw std::runtime_error("Called init in handle function");
                },
                extra...);
        } else {
            // function that does not need cls as first argument
            auto wrapper_cls = [func = (nb::detail::forward_t<Func>)func](
                                   nb::type_object h, FirstArg arg1, Args... args) {
                // printf("Called wrapper_cls with %s\n", nb::type_name(h).c_str());
                return func(arg1, (nb::detail::forward_t<Args>)args...);
            };
            auto wrapper = [func = (nb::detail::forward_t<Func>)func](FirstArg arg1,
                                                                      Args... args) {
                throw std::runtime_error("Called wrapper for non-handle function");
            };

            cl.def_static("__new__", std::move(wrapper), extra...);
            cl.def_static("__new__", std::move(wrapper_cls), nb::arg("cls"), extra...);
            cl.def(
                "__init__",
                [](nb::handle, FirstArg, Args...) {
                    // throw std::runtime_error("Called init in non-handle function");
                },
                extra...);
        }
    }
};

template <typename Func> new__(Func &&f) -> new__<Func>;

#define FACTORY(pyclass, newc, ...)                                                     \
    {                                                                                   \
        auto _ = pyclass;                                                               \
        new__(newc).execute(_, ##__VA_ARGS__);                                          \
    }
