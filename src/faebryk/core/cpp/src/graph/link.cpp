/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include "graph/graph.hpp"
#include "graph/links.hpp"
#include "pyutil.hpp"

Link::Link()
  : from(nullptr)
  , to(nullptr)
  , setup(false) {
}

Link::Link(GI_ref_weak from, GI_ref_weak to)
  : from(from)
  , to(to)
  , setup(true) {
}

Link::Link(const Link &other)
  : from(nullptr)
  , to(nullptr)
  , setup(false) {
}

std::pair<GI_ref_weak, GI_ref_weak> Link::get_connections() {
    if (!this->setup) {
        throw std::runtime_error("link not setup");
    }
    return {this->from, this->to};
}

void Link::set_connections(GI_ref_weak from, GI_ref_weak to) {
    this->from = from;
    this->to = to;
    this->setup = true;
}

bool Link::is_setup() {
    return this->setup;
}

std::string Link::str() const {
    std::stringstream ss;
    ss << util::get_type_name(this) << "(";
    if (this->setup) {
        ss << this->from->get_full_name(false) << " -> "
           << this->to->get_full_name(false);
    }
    ss << ")";
    return ss.str();
}

bool Link::operator==(const Link &other) const {
    bool same_type = typeid(*this) == typeid(other);
    bool same_connections = this->from == other.from && this->to == other.to;
    bool both_setup = this->setup && other.setup;

    return same_type && (!both_setup || same_connections);
}
