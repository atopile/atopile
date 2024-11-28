/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include "graph/graph.hpp"
#include <algorithm>
#include <sstream>

Path::Path(/*const*/ GI_ref_weak path_head)
  : path(std::vector</*const*/ GI_ref_weak>{path_head}) {
}

Path::Path(std::vector<GI_ref_weak> path)
  : path(path) {
}

Path::Path(const Path &other)
  : path(other.path) {
}

Path::Path(Path &&other)
  : path(std::move(other.path)) {
}

Path::Path(std::vector<GI_ref_weak> path, GI_ref_weak head)
  : path([&path, &head]() {
      auto new_path = path;
      new_path.push_back(head);
      return new_path;
  }()) {
}

Path::~Path() {
}

/*const*/ Link_weak_ref Path::get_link(Edge edge) const {
    auto out = edge.from->is_connected(edge.to);
    assert(out);
    return out->get();
}

std::optional<Edge> Path::last_edge() const {
    if (path.size() < 2) {
        return {};
    }
    return Edge{path[path.size() - 2], path.back()};
}

std::optional<TriEdge> Path::last_tri_edge() const {
    if (path.size() < 3) {
        return {};
    }
    return std::make_tuple(path[path.size() - 3], path[path.size() - 2], path.back());
}

/*const*/ GI_ref_weak Path::last() const {
    return path.back();
}

/*const*/ GI_ref_weak Path::first() const {
    return path.front();
}

/*const*/ GI_ref_weak Path::operator[](int idx) const {
    if (idx < 0) {
        idx = path.size() + idx;
    }
    if (idx >= path.size()) {
        throw std::out_of_range("Path index out of range");
    }
    return path[idx];
}

size_t Path::size() const {
    return path.size();
}

bool Path::contains(/*const*/ GI_ref_weak gif) const {
    return std::find(path.begin(), path.end(), gif) != path.end();
}

void Path::iterate_edges(std::function<bool(Edge &)> visitor) const {
    for (size_t i = 1; i < path.size(); i++) {
        Edge edge{path[i - 1], path[i]};
        bool res = visitor(edge);
        if (!res) {
            return;
        }
    }
}

const std::vector</*const*/ GI_ref_weak> &Path::get_path() const {
    return this->path;
}

std::vector</*const*/ GI_ref_weak> Path::get_path_mut() const {
    return std::vector<GI_ref_weak>(this->path);
}

size_t Path::index(/*const*/ GI_ref_weak gif) const {
    return std::distance(path.begin(), std::find(path.begin(), path.end(), gif));
}

std::string Path::str() const {
    std::stringstream ss;
    ss << "Path(" << path.size() << ")";
    ss << "[";
    for (auto &gif : path) {
        ss << "\n    " << gif->get_full_name(false);
    }
    ss << "]";
    return ss.str();
}

bool Path::operator==(const Path &other) const {
    return this->path == other.path;
}

bool Path::starts_with(const Path &other) const {
    if (other.path.size() > this->path.size()) {
        return false;
    }
    return std::equal(other.path.begin(), other.path.end(), this->path.begin());
}
