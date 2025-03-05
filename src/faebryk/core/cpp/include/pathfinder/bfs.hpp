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
    GI_parent_ref_weak child_gif;
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
    bool not_complete = false;
};

namespace std {
template <> struct hash<Path> {
    size_t operator()(const Path &p) const noexcept {
        const GI_refs_weak &path = p.get_path();
        const uint64_t HASH_PRIME = 31;
        uint64_t hash = 0;
        for (auto &gif : path) {
            hash = hash * HASH_PRIME + std::hash<GI_ref_weak>{}(gif);
        }
        return hash;
    }
};
} // namespace std

class BFSPath : public Path, public std::enable_shared_from_this<BFSPath> {
    std::shared_ptr<PathData> path_data;

  public:
    /**
     * @brief Confidence that this path might become 'valid' path
     *
     * 0 < confidence <= 1
     *
     * confidence < 1 := weak path
     */
    double confidence = 1.0;
    /**
     * @brief Removes the path from the search
     *
     */
    bool filtered = false;
    /**
     * @brief Hibernates the path
     *
     * Hibernated BFS paths are not visited as long as they are hibernated.
     */
    bool hibernated = false;
    /**
     * @brief Stops the BFS search
     *
     */
    bool stop = false;

    /**
     * @brief Notifies BFS that it woke up other paths
     *
     */
    bool wake_signal = false;

    /**
     * @brief Notifies BFS that the path has become strong after being weak
     *
     */
    bool strong_signal = false;

    BFSPath(/*const*/ GI_ref_weak path_head);
    BFSPath(const BFSPath &other);
    BFSPath(const BFSPath &other, /*const*/ GI_ref_weak new_head);
    BFSPath(BFSPath &&other) = delete;
    std::shared_ptr<BFSPath> operator+(/*const*/ GI_ref_weak gif);

    PathData &get_path_data_mut();
    PathData &get_path_data() /*const*/;
    bool strong() /*const*/;
};

void bfs_visit(/*const*/ GI_ref_weak root, std::function<void(BFSPath &)> visitor);
