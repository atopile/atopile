/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include "graph/graph.hpp"
#include "graph/links.hpp"
#include <queue>

Graph::Graph() {
}

Graph::~Graph() {
    if (!this->invalidated) {
        printf("WARNING: graph not invalidated\n");
    }
}

void Graph::hold(GI_ref gi) {
    this->v.insert(gi);
}

Graph_ref Graph::merge_graphs(Graph_ref g1, Graph_ref g2) {
    if (g1 == g2) {
        return g1;
    }

    auto G_target = (g1->node_count() >= g2->node_count()) ? g1 : g2;
    auto G_source = (g1 == G_target) ? g2 : g1;

    assert(G_source->node_count() > 0);
    size_t v_i_offset = G_target->node_count();

    for (auto &v : G_source->v) {
        v->G = G_target;
        v->v_i += v_i_offset;
    }
    G_target->merge(*G_source);
    G_source->invalidate();

    return G_target;
}

void Graph::add_edge(Link_ref link) {
    auto [from, to] = link->get_connections();

    auto G = Graph::merge_graphs(from->G, to->G);

    // existing link
    if (G->e_cache_simple[from].contains(to)) {
        // handle policy in the caller
        throw LinkExists(G->e_cache[from][to], link, "link already exists");
    }

    G->e_cache_simple[from].insert(to);
    G->e_cache_simple[to].insert(from);
    G->e_cache[from][to] = link;
    G->e_cache[to][from] = link;
    G->e.push_back(std::make_tuple(from, to, link));
}

void Graph::remove_edge(Link_ref link) {
    auto [from, to] = link->get_connections();
    auto G = from->G;
    if (G != to->G) {
        throw std::runtime_error("link not in graph");
    }

    if (!G->e_cache_simple[from].contains(to)) {
        return;
    }
    if (G->e_cache[from][to] != link) {
        throw std::runtime_error("link not in graph");
    }
    G->e_cache_simple[from].erase(to);
    G->e_cache[from].erase(to);
    G->e_cache[to].erase(from);
    std::erase_if(G->e, [link](const auto &edge) {
        return std::get<2>(edge) == link;
    });

    // TODO
    if (G->e_cache_simple[from].empty()) {
        //     G->remove_node(from);
    }
    if (G->e_cache_simple[to].empty()) {
        //     G->remove_node(to);
    }
}

void Graph::merge(Graph &other) {
    this->v.merge(other.v);
    this->e.insert(this->e.end(), other.e.begin(), other.e.end());
    this->e_cache.merge(other.e_cache);
    this->e_cache_simple.merge(other.e_cache_simple);
}

std::unordered_set<GI_ref_weak> Graph::get_gif_edges(GI_ref_weak from) {
    return this->e_cache_simple[from];
}

Map<GI_ref_weak, Link_ref> &Graph::get_edges(GI_ref_weak from) {
    return this->e_cache[from];
}

void Graph::remove_node(GI_ref node) {
    auto node_ptr = node.get();
    this->v.erase(node);

    // TODO remove G ref from Gif

    for (auto &[from, tos] : this->e_cache_simple) {
        tos.erase(node_ptr);
    }
    this->e_cache_simple.erase(node_ptr);

    for (auto &[to, link] : this->e_cache[node_ptr]) {
        this->e_cache[to].erase(node_ptr);
    }
    this->e_cache.erase(node_ptr);

    std::erase_if(this->e, [node_ptr](const auto &edge) {
        return std::get<0>(edge) == node_ptr || std::get<1>(edge) == node_ptr;
    });
}

void Graph::invalidate() {
    this->invalidated = true;
    this->v.clear();
}

int Graph::node_count() {
    return this->v.size();
}

int Graph::edge_count() {
    return this->e.size();
}

std::string Graph::repr() {
    std::stringstream ss;
    ss << "<Graph[V:" << this->node_count() << ", E:" << this->edge_count() << "] at "
       << this << ">";
    return ss.str();
}

// Algorithms --------------------------------------------------------------------------

std::unordered_set<Node_ref> Graph::node_projection() {
    std::unordered_set<Node_ref> nodes;
    for (auto &gif : this->v) {
        if (auto self_gif = dynamic_cast<GraphInterfaceSelf *>(gif.get())) {
            auto node = self_gif->get_node();
            assert(node);
            nodes.insert(node);
        }
    }
    return nodes;
}

std::vector<std::pair<Node_ref, std::string>>
Graph::nodes_by_names(std::unordered_set<std::string> names) {
    std::vector<std::pair<Node_ref, std::string>> nodes;
    for (auto &node : this->node_projection()) {
        auto full_name = node->get_full_name();
        if (names.contains(full_name)) {
            nodes.push_back({node, full_name});
        }
    }
    return nodes;
}

std::unordered_set<GI_ref_weak>
Graph::bfs_visit(std::function<bool(std::vector<GI_ref_weak> &, Link_ref)> filter,
                 std::vector<GI_ref_weak> start) {
    std::unordered_set<GI_ref_weak> visited;
    std::queue<std::vector<GI_ref_weak>> queue;
    queue.push(start);

    while (!queue.empty()) {
        auto path = queue.front();
        queue.pop();

        auto current = path.back();

        for (auto &[next, link] : this->e_cache[current]) {
            if (visited.contains(next)) {
                continue;
            }

            std::vector<GI_ref_weak> next_path(path);
            next_path.push_back(next);

            if (filter(next_path, link)) {
                queue.push(next_path);
                visited.insert(next);
            }
        }
    }

    return visited;
}

Set<GI_ref> Graph::get_gifs() {
    return this->v;
}

std::vector<std::tuple<GI_ref_weak, GI_ref_weak, Link_ref>> Graph::all_edges() {
    return this->e;
}

LinkExists::LinkExists(Link_ref existing_link, Link_ref new_link, const std::string &msg)
  : std::runtime_error(LinkExists::make_msg(existing_link, new_link, msg))
  , existing_link(existing_link)
  , new_link(new_link) {
}

std::string LinkExists::make_msg(Link_ref existing_link, Link_ref new_link,
                                 const std::string &msg) {
    std::stringstream ss;
    ss << msg << ": E:" << existing_link->str() << " N:" << new_link->str();
    return ss.str();
}

Link_ref LinkExists::get_existing_link() {
    return this->existing_link;
}

Link_ref LinkExists::get_new_link() {
    return this->new_link;
}
