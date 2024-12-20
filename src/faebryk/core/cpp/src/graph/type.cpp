/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include "graph/graph.hpp"
#include "pyutil.hpp"

nb::type_object Node::Type::get_moduleinterface_type() {
    // TODO can be done in a nicer way
    return nb::module_::import_("faebryk.core.moduleinterface").attr("ModuleInterface");
}

Node::Type::Type(nb::handle type)
  : type(type) {
    // TODO can be done in a nicer way
    this->hack_cache_is_moduleinterface =
        pyutil::issubclass(this->type, this->get_moduleinterface_type());
}

bool Node::Type::is_subclass(nb::type_object type) {
    return pyutil::issubclass(this->type, type);
}

bool Node::Type::is_subclass(std::vector<nb::type_object> types) {
    return std::any_of(types.begin(), types.end(), [this](auto type) {
        return this->is_subclass(type);
    });
}

bool Node::Type::operator==(const Type &other) const {
    // TODO not sure this is ok
    return this->type.ptr() == other.type.ptr();
}

std::string Node::Type::get_name() {
    return pyutil::get_name(this->type);
}

bool Node::Type::is_moduleinterface() {
    return this->hack_cache_is_moduleinterface;
}
