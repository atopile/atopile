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

class PathFinder {
    std::vector<BFSPath> multi_paths;
    size_t path_cnt = 0;

    bool _count(BFSPath &p);
    bool _filter_path_by_node_type(BFSPath &p);
    bool _filter_path_gif_type(BFSPath &p);
    bool _filter_path_by_dead_end_split(BFSPath &p);
    bool _build_path_stack(BFSPath &p);
    bool _filter_path_by_end_in_self_gif(BFSPath &p);
    bool _filter_path_same_end_type(BFSPath &p);
    bool _filter_path_by_stack(BFSPath &p);
    bool _filter_shallow(BFSPath &p);
    bool _filter_conditional_link(BFSPath &p);
    std::vector<BFSPath> _filter_paths_by_split_join(std::vector<BFSPath> &paths);

  public:
    PathFinder();

    std::vector<Filter> filters;
    bool run_filters(BFSPath &p);
    std::pair<std::vector<Path>, std::vector<Counter>>
    find_paths(Node_ref src, std::vector<Node_ref> dst);
};
