/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include "graph/graph.hpp"
#include "pathfinder/bfs.hpp"
#include "pathfinder/pathcounter.hpp"
#include "perf.hpp"
#include <any>
#include <chrono>
#include <deque>
#include <functional>
#include <memory>
#include <sstream>

struct PathLimits {
    uint32_t absolute = 1 << 31;
    uint32_t no_new_weak = 1 << 31;
    uint32_t no_weak = 1 << 31;
};

inline PathLimits PATH_LIMITS;

inline void set_max_paths(uint32_t absolute, uint32_t no_new_weak, uint32_t no_weak) {
    PATH_LIMITS.absolute = absolute;
    PATH_LIMITS.no_new_weak = no_new_weak;
    PATH_LIMITS.no_weak = no_weak;
}

class PathFinder;

struct Filter {
    bool (PathFinder::*filter)(BFSPath &);
    bool discovery = false;
    Counter counter;

    bool exec(PathFinder *pf, BFSPath &p);
};

struct SplitState {

    /**
     * @brief Path that led to this split
     *
     */
    Path split_prefix;

    /**
     * @brief Branch complete
     *
     * All children have complete suffix path from here on
     */
    bool complete = false;

    bool waiting = false;

    /**
     * @brief All paths that are from this split on complete further (& fully valid)
     *
     */
    Map<GI_ref_weak, std::vector<std::shared_ptr<BFSPath>>> suffix_complete_paths;

    /**
     * @brief All paths that are hibernated per child
     *
     */
    Map<GI_ref_weak, std::vector<std::shared_ptr<BFSPath>>> wait_paths;

    SplitState(const BFSPath &path);

    /**
     * @brief Parent gif of this split
     *
     * (always split_prefix.last())
     */
    GI_ref_weak split_point() const;
};

class PathFinder {
    // TODO I think we should use PathStack (slightly modified) instead of Path
    // since non-hierarchical links have no influence on the split
    Map<GI_ref_weak, Map<Path, SplitState>> split;
    size_t path_cnt = 0;

    bool _count(BFSPath &p);
    bool _filter_path_by_node_type(BFSPath &p);
    bool _filter_path_gif_type(BFSPath &p);
    bool _filter_path_by_dead_end_split(BFSPath &p);
    bool _build_path_stack_and_handle_splits(BFSPath &p);
    bool _filter_path_by_end_in_self_gif(BFSPath &p);
    bool _filter_path_same_end_type(BFSPath &p);
    bool _filter_path_by_stack(BFSPath &p);
    bool _filter_shallow(BFSPath &p);
    bool _filter_conditional_link(BFSPath &p);
    bool _handle_valid_split_branch(BFSPath &p);
    std::vector<BFSPath> _filter_paths_by_split_join(std::vector<BFSPath> &paths);
    bool _filter_incomplete(BFSPath &p);

  public:
    PathFinder();

    std::vector<Filter> filters;
    bool run_filters(BFSPath &p);
    std::pair<std::vector<Path>, std::vector<Counter>>
    find_paths(Node_ref src, std::vector<Node_ref> dst);
};
