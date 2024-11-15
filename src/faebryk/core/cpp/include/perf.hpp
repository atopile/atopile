/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <chrono>
#include <vector>

class PerfCounter {
    std::chrono::high_resolution_clock::time_point start;

  public:
    PerfCounter();
    int64_t ns();
    double ms();
    double s();
};

class PerfCounterAccumulating {
    std::chrono::high_resolution_clock::time_point start;
    int64_t time_ns = 0;
    bool paused = false;

  public:
    PerfCounterAccumulating();
    void pause();
    void resume();
    int64_t ns();
    double ms();
    double s();
};
