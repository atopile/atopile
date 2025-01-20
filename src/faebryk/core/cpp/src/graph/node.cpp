/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include "graph/graph.hpp"
#include "graph/links.hpp"
#include "pyutil.hpp"

Node::Node()
  : self(GraphInterfaceSelf::factory<GraphInterfaceSelf>())
  , children(GraphInterfaceHierarchical::factory<GraphInterfaceHierarchical>(true))
  , parent(GraphInterfaceHierarchical::factory<GraphInterfaceHierarchical>(false)) {

    this->self->set_name("self");

    this->children->set_name("children");
    this->children->connect(this->self.get(), std::make_shared<LinkSibling>());

    this->parent->set_name("parent");
    this->parent->connect(this->self.get(), std::make_shared<LinkSibling>());
}

Node_ref Node::transfer_ownership(Node_ref node) {
    // TODO consider some hacking with nb::cast during new to avoid this

    node->self->set_node(node);
    node->children->set_node(node);
    node->parent->set_node(node);

    auto other = nb::find(node);
    node->set_py_handle(other);

    return node;
}

void Node::set_py_handle(nb::object handle) {
    if (this->py_handle.has_value()) {
        throw std::runtime_error("py_handle already set");
    }
    assert(handle.is_valid());
    this->py_handle = handle;
    this->type = Type(handle.type());
}

std::shared_ptr<Graph> Node::get_graph() {
    return this->self->get_graph();
}

std::shared_ptr<GraphInterfaceSelf> Node::get_self_gif() {
    return this->self;
}

std::shared_ptr<GraphInterfaceHierarchical> Node::get_children_gif() {
    return this->children;
}

std::shared_ptr<GraphInterfaceHierarchical> Node::get_parent_gif() {
    return this->parent;
}

std::optional<HierarchicalNodeRef> Node::get_parent() {
    return this->parent->get_parent();
}

HierarchicalNodeRef Node::get_parent_force() {
    auto p = this->get_parent();
    if (!p) {
        throw NodeNoParent(*this, __func__);
    }
    return *p;
}

std::string Node::get_root_id() {
    return util::formatted_ptr(this);
}

std::string Node::get_name(bool accept_no_parent) {
    if (!accept_no_parent) {
        return this->get_parent_force().second;
    }
    auto p = this->get_parent();
    if (!p) {
        return this->get_root_id();
    }
    return p->second;
}

std::vector<HierarchicalNodeRef> Node::get_hierarchy() {
    auto p = this->get_parent();
    if (!p) {
        return std::vector{std::make_pair(this->self->get_node(), this->get_root_id())};
    }
    auto [parent, name] = *p;
    auto parent_hierarchy = parent->get_hierarchy();
    parent_hierarchy.push_back(std::make_pair(this->self->get_node(), name));
    return parent_hierarchy;
}

std::string Node::get_full_name(bool types) {
    std::stringstream ss;
    auto p = this->get_parent();
    if (p) {
        auto [parent, name] = *p;
        if (!parent->getter_no_include_parents_in_full_name()) {
            auto parent_hierarchy = parent->get_full_name(types);
            ss << parent_hierarchy << ".";
        }
        ss << name;
    } else {
        if (!this->getter_no_include_parents_in_full_name()) {
            ss << this->get_root_id();
        }
    }
    if (types) {
        ss << "|" << this->get_type_name();
    }
    return ss.str();
}

std::string Node::repr() {
    std::stringstream ss;
    ss << "<" << this->get_full_name(true) << ">";
    return ss.str();
}

std::string Node::get_type_name() {
    if (this->py_handle.has_value()) {
        return this->get_type().get_name();
    }
    return util::get_type_name(this);
}

Node::Type Node::get_type() {
    if (!this->type) {
        throw std::runtime_error("Node has no py_handle");
    }
    return *this->type;
}

bool Node::isinstance(nb::type_object type) {
    if (!this->type) {
        return false;
    }
    return this->get_type().is_subclass(type);
}

bool Node::isinstance(std::vector<nb::type_object> types) {
    if (!this->type) {
        return false;
    }
    return this->get_type().is_subclass(types);
}

std::optional<nb::object> Node::get_py_handle() {
    return this->py_handle;
}

std::unordered_set<Node_ref> Node::get_children_all(bool include_root) {
    std::unordered_set<Node_ref> out;

    auto direct_children = this->get_children_direct();
    if (include_root) {
        out.insert(this->self->get_node());
    }
    for (auto child : direct_children) {
        out.merge(child->get_children_all(false));
    }
    out.merge(direct_children);

    return out;
}

std::unordered_set<Node_ref> Node::get_children_direct() {
    auto children = this->children->get_children();
    return std::unordered_set<Node_ref>(children.begin(), children.end());
}

std::vector<Node_ref>
Node::get_children(bool direct_only, std::optional<std::vector<nb::type_object>> types,
                   bool include_root, std::function<bool(Node_ref)> f_filter,
                   bool sort) {
    std::unordered_set<Node_ref> children;
    if (direct_only) {
        children = this->get_children_direct();
        if (include_root) {
            children.insert(this->self->get_node());
        }
    } else {
        children = this->get_children_all(include_root);
    }

    // always true if Node in types
    if (types) {
        auto type_h = nb::type<Node>();
        for (auto type : *types) {
            if (type.ptr() == type_h.ptr()) {
                types = {};
                break;
            }
        }
    }

    std::vector<Node_ref> children_filtered;

    // If no filtering is needed, copy all children directly
    if (!types && !f_filter) {
        children_filtered.assign(children.begin(), children.end());
    } else {
        for (auto node : children) {
            // filter by type
            if (types && !node->isinstance(*types)) {
                continue;
            }

            // filter by function
            if (f_filter && !f_filter(node)) {
                continue;
            }

            children_filtered.push_back(node);
        }
    }

    if (sort) {
        // Custom comparator for sorting by node name
        auto comp = [](const Node_ref &a, const Node_ref &b) {
            return a->get_name(true) < b->get_name(true);
        };

        // Sort the children_filtered vector using the custom comparator
        std::sort(children_filtered.begin(), children_filtered.end(), comp);
    }

    return children_filtered;
}

std::unordered_set<Node_ref> Node::bfs_node(std::function<bool(Path)> filter) {
    std::unordered_set<Node_ref> out;

    auto filter_func = [filter, &out](std::vector<GI_ref_weak> &path, Link_ref) {
        bool ok = filter(Path(path));
        if (ok) {
            out.insert(path.back()->get_node());
        }
        return ok;
    };

    this->self->get_graph()->bfs_visit(
        filter_func, std::vector({static_cast<GraphInterface *>(this->self.get())}));
    return out;
}

void Node::setter_no_include_parents_in_full_name(bool no_include_parents_in_full_name) {
    this->no_include_parents_in_full_name = no_include_parents_in_full_name;
}

bool Node::getter_no_include_parents_in_full_name() const {
    return this->no_include_parents_in_full_name;
}
