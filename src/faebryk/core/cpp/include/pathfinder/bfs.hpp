/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include "graph/graph.hpp"
#include "graph/graphinterfaces.hpp"
#include <optional>
#include <string>
#include <tuple>
#include <vector>

using GI_parent_ref_weak = GraphInterfaceHierarchical *;

struct PathStackElement {
    Node::Type parent_type;
    Node::Type child_type;
    /*const*/ GI_parent_ref_weak parent_gif;
    std::string name;
    bool up;

    std::string str() /*const*/;
};

struct UnresolvedStackElement {
    PathStackElement elem;
    bool split;

    bool match(PathStackElement &other);
    std::string str() /*const*/;
};

using PathStack = std::vector<PathStackElement>;
using UnresolvedStack = std::vector<UnresolvedStackElement>;

struct PathData {
    UnresolvedStack unresolved_stack;
    PathStack split_stack;
};

class BFSPath : public Path {
    std::shared_ptr<PathData> path_data;

  public:
    double confidence = 1.0;
    bool filtered = false;
    bool stop = false;

    BFSPath(/*const*/ GI_ref_weak path_head);
    BFSPath(const BFSPath &other);
    BFSPath(const BFSPath &other, /*const*/ GI_ref_weak new_head);
    BFSPath(BFSPath &&other);
    BFSPath operator+(/*const*/ GI_ref_weak gif);

    PathData &get_path_data_mut();
    PathData &get_path_data() /*const*/;
    bool strong() /*const*/;
};

void bfs_visit(/*const*/ GI_ref_weak root, std::function<void(BFSPath &)> visitor);
