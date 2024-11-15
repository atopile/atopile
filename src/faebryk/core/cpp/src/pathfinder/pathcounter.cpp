/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include "pathfinder/pathcounter.hpp"
#include "pathfinder/bfs.hpp"
#include "pathfinder/pathfinder.hpp"
#include "perf.hpp"

bool Counter::exec(PathFinder *pf, bool (PathFinder::*filter)(BFSPath &), BFSPath &p) {
    if (!INDIV_MEASURE && !total_counter) {
        return (pf->*filter)(p);
    }

    // perf pre
    in_cnt++;
    auto confidence_pre = p.confidence;
    if (confidence_pre < 1.0) {
        weak_in_cnt++;
    }
    PerfCounter pc;

    // exec
    bool res = (pf->*filter)(p);

    // perf post
    int64_t duration_ns = pc.ns();
    time_spent_s += duration_ns * 1e-9;

    if (res) {
        out_cnt++;
    }
    if (p.confidence < confidence_pre) {
        out_weaker++;
    } else if (p.confidence > confidence_pre) {
        out_stronger++;
    }

    return res;
}

std::vector<BFSPath>
Counter::exec_multi(PathFinder *pf,
                    std::vector<BFSPath> (PathFinder::*filter)(std::vector<BFSPath> &),
                    std::vector<BFSPath> &p) {
    if (!INDIV_MEASURE && !total_counter) {
        return (pf->*filter)(p);
    }

    in_cnt += p.size();
    PerfCounter pc;

    // exec
    auto res = (pf->*filter)(p);

    // perf post
    int64_t duration_ns = pc.ns();
    time_spent_s += duration_ns * 1e-9;

    out_cnt += res.size();

    return res;
}