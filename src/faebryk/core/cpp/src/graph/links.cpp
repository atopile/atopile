/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include "graph/links.hpp"

// LinkDirect --------------------------------------------------------------------------
LinkDirect::LinkDirect()
  : Link() {
}

LinkDirect::LinkDirect(GI_ref_weak from, GI_ref_weak to)
  : Link(from, to) {
}

// LinkParent --------------------------------------------------------------------------
LinkParent::LinkParent()
  : Link()
  , parent(nullptr)
  , child(nullptr) {
}

LinkParent::LinkParent(GraphInterfaceHierarchical *from, GraphInterfaceHierarchical *to)
  : Link(from, to)
  , parent(nullptr)
  , child(nullptr) {
    this->set_connections(from, to);
}

void LinkParent::set_connections(GI_ref_weak from, GI_ref_weak to) {
    auto from_h = dynamic_cast<GraphInterfaceHierarchical *>(from);
    auto to_h = dynamic_cast<GraphInterfaceHierarchical *>(to);

    if (!from_h || !to_h) {
        throw std::runtime_error("invalid gifs for LinkParent");
    }

    Link::set_connections(from, to);
    if (from_h->get_is_parent() && !to_h->get_is_parent()) {
        this->parent = from_h;
        this->child = to_h;
    } else if (!from_h->get_is_parent() && to_h->get_is_parent()) {
        this->parent = to_h;
        this->child = from_h;
    } else {
        throw std::runtime_error("invalid parent-child relationship");
    }
}

GraphInterfaceHierarchical *LinkParent::get_parent() {
    if (!this->is_setup()) {
        throw std::runtime_error("link not setup");
    }
    return this->parent;
}

GraphInterfaceHierarchical *LinkParent::get_child() {
    if (!this->is_setup()) {
        throw std::runtime_error("link not setup");
    }
    return this->child;
}

// LinkNamedParent ---------------------------------------------------------------------
LinkNamedParent::LinkNamedParent(std::string name)
  : LinkParent()
  , name(name) {
}

LinkNamedParent::LinkNamedParent(std::string name, GraphInterfaceHierarchical *from,
                                 GraphInterfaceHierarchical *to)
  : LinkParent(from, to)
  , name(name) {
}

std::string LinkNamedParent::get_name() {
    return this->name;
}

// LinkPointer -------------------------------------------------------------------------
LinkPointer::LinkPointer()
  : Link()
  , pointee(nullptr)
  , pointer(nullptr) {
}

LinkPointer::LinkPointer(GI_ref_weak from, GraphInterfaceSelf *to)
  : Link(from, to)
  , pointee(nullptr)
  , pointer(nullptr) {
    this->set_connections(from, to);
}

void LinkPointer::set_connections(GI_ref_weak from, GI_ref_weak to) {
    auto from_s = dynamic_cast<GraphInterfaceSelf *>(from);
    auto to_s = dynamic_cast<GraphInterfaceSelf *>(to);

    if (!from_s && !to_s) {
        throw std::runtime_error("LinkPointer needs to point to a self-gif");
    }
    if (!to_s) {
        to_s = from_s;
        from = to;
    }

    Link::set_connections(from, to_s);
    this->pointer = from;
    this->pointee = to_s;
}

GraphInterfaceSelf *LinkPointer::get_pointee() {
    if (!this->is_setup()) {
        throw std::runtime_error("link not setup");
    }
    return this->pointee;
}

GraphInterface *LinkPointer::get_pointer() {
    if (!this->is_setup()) {
        throw std::runtime_error("link not setup");
    }
    return this->pointer;
}

// LinkSibling ------------------------------------------------------------------------
LinkSibling::LinkSibling()
  : LinkPointer() {
}

LinkSibling::LinkSibling(GI_ref_weak from, GraphInterfaceSelf *to)
  : LinkPointer(from, to) {
}

// LinkDirectConditional ----------------------------------------------------------------
LinkDirectConditional::LinkDirectConditional(FilterF filter)
  : LinkDirect()
  , filter(filter) {
}

LinkDirectConditional::LinkDirectConditional(FilterF filter, GI_ref_weak from,
                                             GI_ref_weak to)
  : LinkDirect(from, to)
  , filter(filter) {
    this->set_connections(from, to);
}

void LinkDirectConditional::set_connections(GI_ref_weak from, GI_ref_weak to) {
    if (this->filter(from, to) != FilterResult::FILTER_PASS) {
        throw LinkFilteredException("LinkDirectConditional filtered");
    }
    LinkDirect::set_connections(from, to);
}

// LinkDirectDerived -------------------------------------------------------------------
LinkDirectDerived::LinkDirectDerived(Path path)
  : LinkDirectConditional(make_filter_from_path(path)) {
}

LinkDirectDerived::LinkDirectDerived(Path path, GI_ref_weak from, GI_ref_weak to)
  : LinkDirectConditional(make_filter_from_path(path), from, to) {
}

LinkDirectConditional::FilterF LinkDirectDerived::make_filter_from_path(Path path) {
    // TODO
    return [path](GI_ref_weak, GI_ref_weak) {
        return LinkDirectConditional::FilterResult::FILTER_PASS;
    };
}
