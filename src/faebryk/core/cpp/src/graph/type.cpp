/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include "graph/graph.hpp"
#include "pyutil.hpp"

std::optional<nb::type_object> module_interface_type;

nb::type_object Node::Type::get_moduleinterface_type() {
    if (!module_interface_type) {
        module_interface_type =
            nb::module_::import_("faebryk.core.moduleinterface").attr("ModuleInterface");
    }
    return *module_interface_type;
}

Node::Type::Type(nb::handle type)
  : type(type)
  , mro_ids(nb::hasattr(type, "_mro_ids")
                ? nb::cast<std::unordered_set<uint64_t>>(type.attr("_mro_ids"))
                : std::unordered_set<uint64_t>()) {
    // Needed because of Node not having it's own id in mro_ids
    this->mro_ids.insert((uint64_t)this->type.ptr());
}

bool Node::Type::is_subclass(nb::type_object type) {
    uint64_t type_id = (uint64_t)type.ptr();
    return this->mro_ids.contains(type_id);
}

bool Node::Type::is_subclass(std::vector<nb::type_object> types) {
    return std::any_of(types.begin(), types.end(), [this](auto type) {
        return this->is_subclass(type);
    });
}

bool Node::Type::operator==(const Type &other) const {
    return this->type.ptr() == other.type.ptr();
}

std::string Node::Type::get_name() {
    return pyutil::get_name(this->type);
}

bool Node::Type::is_moduleinterface() {
    return this->is_subclass(this->get_moduleinterface_type());
}
