/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include "graph.hpp"

class LinkParent;

class GraphInterfaceSelf : public GraphInterface {
  public:
    using GraphInterface::GraphInterface;
};

class GraphInterfaceHierarchical : public GraphInterface {
    bool is_parent;

  public:
    GraphInterfaceHierarchical(bool is_parent);

    template <typename T> static std::shared_ptr<T> factory(bool is_parent);
    bool get_is_parent();
    std::vector<Node_ref> get_children();
    std::vector<HierarchicalNodeRef> get_children_with_names();
    std::optional<HierarchicalNodeRef> get_parent();
    void disconnect_parent();

    static bool is_uplink(GI_ref_weak from, GI_ref_weak to);
    static bool is_downlink(GI_ref_weak from, GI_ref_weak to);

  private:
    std::optional<std::shared_ptr<LinkParent>> get_parent_link();
};

/** Represents a reference to a node object */
class GraphInterfaceReference : public GraphInterface {
  public:
    /** Cannot resolve unbound reference */
    struct UnboundError : public std::runtime_error {
        UnboundError(const std::string &msg)
          : std::runtime_error(msg) {
        }
    };

  public:
    using GraphInterface::GraphInterface;

    GraphInterfaceSelf *get_referenced_gif();
    Node_ref get_reference();
};

// TODO move those back to python when inherited GIFs work again

class GraphInterfaceModuleSibling : public GraphInterfaceHierarchical {
  public:
    using GraphInterfaceHierarchical::GraphInterfaceHierarchical;
};

class GraphInterfaceModuleConnection : public GraphInterface {
  public:
    using GraphInterface::GraphInterface;
};

template <typename T>
inline std::shared_ptr<T> GraphInterfaceHierarchical::factory(bool is_parent) {
    static_assert(std::is_base_of<GraphInterfaceHierarchical, T>::value,
                  "T must be a subclass of GraphInterfaceHierarchical");

    auto gi = std::make_shared<T>(is_parent);
    gi->register_graph(gi);
    return gi;
}