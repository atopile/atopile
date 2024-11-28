/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include "graph/links.hpp"
#include "pyutil.hpp"

// LinkDirect --------------------------------------------------------------------------
LinkDirect::LinkDirect()
  : Link() {
}

LinkDirect::LinkDirect(GI_ref_weak from, GI_ref_weak to)
  : Link(from, to) {
}

LinkDirect::LinkDirect(const LinkDirect &other)
  : Link(other) {
}

Link_ref LinkDirect::clone() const {
    return std::make_shared<LinkDirect>(*this);
}

bool LinkDirect::is_cloneable() const {
    return pyutil::is_cpp_type(this);
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

LinkParent::LinkParent(const LinkParent &other)
  : Link(other)
  , parent(nullptr)
  , child(nullptr) {
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

Link_ref LinkParent::clone() const {
    return std::make_shared<LinkParent>(*this);
}

bool LinkParent::is_cloneable() const {
    return pyutil::is_cpp_type(this);
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

LinkNamedParent::LinkNamedParent(const LinkNamedParent &other)
  : LinkParent(other)
  , name(other.name) {
}

std::string LinkNamedParent::get_name() {
    return this->name;
}

Link_ref LinkNamedParent::clone() const {
    return std::make_shared<LinkNamedParent>(*this);
}

bool LinkNamedParent::operator==(const Link &other) const {
    auto other_np = dynamic_cast<const LinkNamedParent *>(&other);
    return Link::operator==(other) && this->name == other_np->name;
}

bool LinkNamedParent::is_cloneable() const {
    return pyutil::is_cpp_type(this);
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

LinkPointer::LinkPointer(const LinkPointer &other)
  : Link(other)
  , pointee(nullptr)
  , pointer(nullptr) {
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

Link_ref LinkPointer::clone() const {
    return std::make_shared<LinkPointer>(*this);
}

bool LinkPointer::is_cloneable() const {
    return pyutil::is_cpp_type(this);
}

// LinkSibling ------------------------------------------------------------------------
LinkSibling::LinkSibling()
  : LinkPointer() {
}

LinkSibling::LinkSibling(GI_ref_weak from, GraphInterfaceSelf *to)
  : LinkPointer(from, to) {
}

LinkSibling::LinkSibling(const LinkSibling &other)
  : LinkPointer(other) {
}

Link_ref LinkSibling::clone() const {
    return std::make_shared<LinkSibling>(*this);
}

bool LinkSibling::is_cloneable() const {
    return pyutil::is_cpp_type(this);
}

// LinkDirectConditional ----------------------------------------------------------------
LinkDirectConditional::LinkDirectConditional(FilterF filter,
                                             bool needs_only_first_in_path)
  : LinkDirect()
  , filter(filter)
  , needs_only_first_in_path(needs_only_first_in_path) {

    // TODO 1 actually check implied is on
    // TODO 2 implement this
    //  not easy, needs some changes in how split paths are handled
    if (!needs_only_first_in_path) {
        throw std::runtime_error("No support for path conditions with implied links on");
    }
}

LinkDirectConditional::LinkDirectConditional(FilterF filter,
                                             bool needs_only_first_in_path,
                                             GI_ref_weak from, GI_ref_weak to)
  : LinkDirect(from, to)
  , filter(filter)
  , needs_only_first_in_path(needs_only_first_in_path) {

    // TODO 1 actually check implied is on
    // TODO 2 implement this
    //  not easy, needs some changes in how split paths are handled
    if (!needs_only_first_in_path) {
        throw std::runtime_error("No support for path conditions with implied links on");
    }

    this->set_connections(from, to);
}

LinkDirectConditional::LinkDirectConditional(const LinkDirectConditional &other)
  : LinkDirect(other)
  , filter(other.filter)
  , needs_only_first_in_path(other.needs_only_first_in_path) {
}

void LinkDirectConditional::set_connections(GI_ref_weak from, GI_ref_weak to) {
    if (this->filter(Path({from, to})) != FilterResult::FILTER_PASS) {
        throw LinkFilteredException("LinkDirectConditional filtered");
    }
    LinkDirect::set_connections(from, to);
}

LinkDirectConditional::FilterResult LinkDirectConditional::run_filter(Path path) {
    return this->filter(path);
}

bool LinkDirectConditional::needs_to_check_only_first_in_path() {
    return this->needs_only_first_in_path;
}

Link_ref LinkDirectConditional::clone() const {
    return std::make_shared<LinkDirectConditional>(*this);
}

bool LinkDirectConditional::operator==(const Link &other) const {
    auto other_dc = dynamic_cast<const LinkDirectConditional *>(&other);
    // TODO
    return Link::operator==(other) && false;
}

bool LinkDirectConditional::is_cloneable() const {
    return pyutil::is_cpp_type(this);
}

// LinkDirectDerived -------------------------------------------------------------------
LinkDirectDerived::LinkDirectDerived(Path path)
  : LinkDirectDerived(path, make_filter_from_path(path)) {
}

LinkDirectDerived::LinkDirectDerived(Path path, GI_ref_weak from, GI_ref_weak to)
  : LinkDirectDerived(path, make_filter_from_path(path), from, to) {
}

LinkDirectDerived::LinkDirectDerived(Path path, std::pair<FilterF, bool> filter)
  : LinkDirectConditional(filter.first, filter.second)
  , path(path) {
}

LinkDirectDerived::LinkDirectDerived(Path path, std::pair<FilterF, bool> filter,
                                     GI_ref_weak from, GI_ref_weak to)
  : LinkDirectConditional(filter.first, filter.second, from, to)
  , path(path) {
}

LinkDirectDerived::LinkDirectDerived(const LinkDirectDerived &other)
  : LinkDirectConditional(other)
  , path(other.path) {
}

Link_ref LinkDirectDerived::clone() const {
    return std::make_shared<LinkDirectDerived>(*this);
}

std::pair<LinkDirectConditional::FilterF, bool>
LinkDirectDerived::make_filter_from_path(Path path) {
    std::vector<FilterF> derived_filters;
    bool needs_only_first_in_path = true;

    // why make implicit path from self ref path
    assert(path.size() > 1);

    path.iterate_edges([&](Edge &edge) {
        if (auto link_conditional =
                dynamic_cast<LinkDirectConditional *>(path.get_link(edge))) {
            derived_filters.push_back(link_conditional->filter);
            needs_only_first_in_path &=
                link_conditional->needs_to_check_only_first_in_path();
        }
        return true;
    });

    auto filterf = [path, derived_filters](Path check_path) {
        bool ok = true;
        bool recoverable = true;
        for (auto &filter : derived_filters) {
            auto res = filter(check_path);
            ok &= res == LinkDirectConditional::FilterResult::FILTER_PASS;
            recoverable &=
                res != LinkDirectConditional::FilterResult::FILTER_FAIL_UNRECOVERABLE;
        }
        return ok ? LinkDirectConditional::FilterResult::FILTER_PASS
                  : (recoverable
                         ? LinkDirectConditional::FilterResult::FILTER_FAIL_RECOVERABLE
                         : LinkDirectConditional::FilterResult::
                               FILTER_FAIL_UNRECOVERABLE);
    };

    return {filterf, needs_only_first_in_path};
}

bool LinkDirectDerived::operator==(const Link &other) const {
    auto other_dd = dynamic_cast<const LinkDirectDerived *>(&other);
    return Link::operator==(other) && this->path.path == other_dd->path.path;
}

bool LinkDirectDerived::is_cloneable() const {
    return pyutil::is_cpp_type(this);
}

// LinkDirectShallow -------------------------------------------------------------------
// LinkDirectShallow::LinkDirectShallow()
//  : LinkDirectConditional() {
//}
//
// LinkDirectShallow::LinkDirectShallow(const LinkDirectShallow &other)
//  : LinkDirectConditional(other) {
//}
//
// Link_ref LinkDirectShallow::clone() const {
//    return std::make_shared<LinkDirectShallow>(*this);
//}
