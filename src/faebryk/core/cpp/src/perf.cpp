/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include "perf.hpp"

// PerfCounter implementations
PerfCounter::PerfCounter() {
    start = std::chrono::high_resolution_clock::now();
}

int64_t PerfCounter::ns() {
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start);
    return duration.count();
}

double PerfCounter::ms() {
    return ns() / 1e6;
}

double PerfCounter::s() {
    return ns() / 1e9;
}

// PerfCounterAccumulating implementations
PerfCounterAccumulating::PerfCounterAccumulating() {
    start = std::chrono::high_resolution_clock::now();
}

void PerfCounterAccumulating::pause() {
    if (paused) {
        return;
    }
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start);
    this->time_ns += duration.count();
    paused = true;
}

void PerfCounterAccumulating::resume() {
    if (!paused) {
        return;
    }
    start = std::chrono::high_resolution_clock::now();
    paused = false;
}

int64_t PerfCounterAccumulating::ns() {
    pause();
    return this->time_ns;
}

double PerfCounterAccumulating::ms() {
    return ns() / 1e6;
}

double PerfCounterAccumulating::s() {
    return ns() / 1e9;
}
