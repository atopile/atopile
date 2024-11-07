/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include "graph/graph.hpp"
#include "graph/links.hpp"

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
