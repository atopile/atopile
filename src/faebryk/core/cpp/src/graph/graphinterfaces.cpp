/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include "graph/graphinterfaces.hpp"
#include "graph/links.hpp"

// GraphInterfaceSelf ------------------------------------------------------------------
// GraphInterfaceHierarchical ----------------------------------------------------------

bool GraphInterfaceHierarchical::get_is_parent() {
    return this->is_parent;
}

std::vector<Node_ref> GraphInterfaceHierarchical::get_children() {
    assert(this->is_parent);

    auto edges = this->get_edges();
    std::vector<Node_ref> children;
    for (auto [to, link] : edges) {
        if (auto named_link = std::dynamic_pointer_cast<LinkParent>(link)) {
            children.push_back(to->get_node());
        }
    }
    return children;
}

std::vector<HierarchicalNodeRef> GraphInterfaceHierarchical::get_children_with_names() {
    assert(this->is_parent);

    auto edges = this->get_edges();
    std::vector<HierarchicalNodeRef> children;
    for (auto [to, link] : edges) {
        if (auto named_link = dynamic_cast<LinkNamedParent *>(link.get())) {
            children.push_back(std::make_pair(to->get_node(), named_link->get_name()));
        }
    }
    return children;
}

std::optional<std::shared_ptr<LinkParent>>
GraphInterfaceHierarchical::get_parent_link() {
    assert(!this->is_parent);

    auto edges = this->get_edges();
    for (auto [to, link] : edges) {
        if (auto parent_link = std::dynamic_pointer_cast<LinkParent>(link)) {
            return parent_link;
        }
    }
    return std::nullopt;
}

std::optional<HierarchicalNodeRef> GraphInterfaceHierarchical::get_parent() {
    auto link = this->get_parent_link();
    if (!link) {
        return std::nullopt;
    }
    auto p = (*link)->get_parent();
    // if unnamed, name is empty string
    std::string name;
    if (auto named_link = std::dynamic_pointer_cast<LinkNamedParent>(*link)) {
        name = named_link->get_name();
    }
    return std::make_pair(p->get_node(), name);
}

GraphInterfaceHierarchical::GraphInterfaceHierarchical(bool is_parent)
  : GraphInterface()
  , is_parent(is_parent) {
}

void GraphInterfaceHierarchical::disconnect_parent() {
    auto link = this->get_parent_link();
    if (!link) {
        return;
    }
    Graph::remove_edge(*link);
}

bool GraphInterfaceHierarchical::is_uplink(GI_ref_weak from, GI_ref_weak to) {
    auto from_gif = dynamic_cast<GraphInterfaceHierarchical *>(from);
    auto to_gif = dynamic_cast<GraphInterfaceHierarchical *>(to);
    if (!from_gif || !to_gif) {
        return false;
    }
    return !from_gif->is_parent && to_gif->is_parent;
}

bool GraphInterfaceHierarchical::is_downlink(GI_ref_weak from, GI_ref_weak to) {
    auto from_gif = dynamic_cast<GraphInterfaceHierarchical *>(from);
    auto to_gif = dynamic_cast<GraphInterfaceHierarchical *>(to);
    if (!from_gif || !to_gif) {
        return false;
    }
    return from_gif->is_parent && !to_gif->is_parent;
}

// GraphInterfaceReference -------------------------------------------------------------
GraphInterfaceSelf *GraphInterfaceReference::get_referenced_gif() {
    auto edges = this->get_edges();
    for (auto [to, link] : edges) {
        if (auto pointer_link = std::dynamic_pointer_cast<LinkPointer>(link)) {
            if (!std::dynamic_pointer_cast<LinkSibling>(link)) {
                return pointer_link->get_pointee();
            }
        }
    }
    throw UnboundError("Reference is not bound");
}

Node_ref GraphInterfaceReference::get_reference() {
    return this->get_referenced_gif()->get_node();
}

// GraphInterfaceModuleSibling -------------------------------------------------------
// GraphInterfaceModuleConnection -----------------------------------------------------
