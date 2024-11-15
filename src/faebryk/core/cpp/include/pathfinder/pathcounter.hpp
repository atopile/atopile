/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <cstddef>
#include <vector>

inline bool INDIV_MEASURE = true;

inline void set_indiv_measure(bool v) {
    INDIV_MEASURE = v;
}

class PathFinder;
class BFSPath;

struct Counter {
    size_t in_cnt = 0;
    size_t weak_in_cnt = 0;
    size_t out_weaker = 0;
    size_t out_stronger = 0;
    size_t out_cnt = 0;
    double time_spent_s = 0;

    bool hide = false;
    const char *name = "";
    bool multi = false;
    bool total_counter = false;

    bool exec(PathFinder *pf, bool (PathFinder::*filter)(BFSPath &), BFSPath &p);
    std::vector<BFSPath>
    exec_multi(PathFinder *pf,
               std::vector<BFSPath> (PathFinder::*filter)(std::vector<BFSPath> &),
               std::vector<BFSPath> &p);
};