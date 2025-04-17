/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include "pathfinder/pathfinder.hpp"
#include "graph/links.hpp"
#include "pathfinder/bfs.hpp"
#include "pathfinder/pathcounter.hpp"
#include <algorithm>
#include <ranges>
#include <unordered_map>
#include <unordered_set>

// Debug Util --------------------------------------------------------------------------
// TODO set to empty
#define printf_split printf

// -------------------------------------------------------------------------------------

// Util --------------------------------------------------------------------------------
GI_refs_weak get_split_children(GI_ref_weak split_point) {
    // TODO this can be optimized I think
    auto children = split_point->get_node()->get_children(
        true, {{Node::Type::get_moduleinterface_type()}}, false);
    GI_refs_weak out;
    for (auto &c : children) {
        out.push_back(c->get_parent_gif().get());
    }
    return out;
}

SplitState::SplitState(const BFSPath &path)
  : split_prefix(std::vector(path.get_path().begin(), path.get_path().end() - 1)) {
    for (auto &gif : get_split_children(split_point())) {
        suffix_complete_paths[gif];
        wait_paths[gif];
    }
}

GI_ref_weak SplitState::split_point() const {
    return split_prefix.last();
}

std::optional<PathStackElement> _extend_path_hierarchy_stack(Edge &edge) {
    bool up = GraphInterfaceHierarchical::is_uplink(edge.from, edge.to);
    if (!up && !GraphInterfaceHierarchical::is_downlink(edge.from, edge.to)) {
        return {};
    }
    auto child_gif = dynamic_cast<GI_parent_ref_weak>(up ? edge.from : edge.to);
    auto parent_gif = dynamic_cast<GI_parent_ref_weak>(up ? edge.to : edge.from);

    auto name = child_gif->get_parent()->second;
    return PathStackElement{parent_gif->get_node()->get_type(),
                            child_gif->get_node()->get_type(),
                            parent_gif,
                            child_gif,
                            name,
                            up};
}

void _extend_fold_stack(PathStackElement &elem, UnresolvedStack &unresolved_stack,
                        PathStack &split_stack) {
    if (!unresolved_stack.empty() && unresolved_stack.back().match(elem)) {
        unresolved_stack.pop_back();
    } else {
        bool multi_child = get_split_children(elem.parent_gif).size() > 1;

        // FIXME: on it's own unfortunately not fully correct, because allows
        //  intermediaries now to be marked strong
        //  see: (test_split_chain_double_flat_no_inter)
        //  maybe we need to mark it as split after all, and then treat it special
        //  during handle_valid_split_branch's resolution
        // check if any elem in split_stack has same parent type and name
        bool in_same_split = std::any_of(
            split_stack.begin(), split_stack.end(), [&](const PathStackElement &e) {
                return e.parent_type == elem.parent_type && e.name == elem.name;
            });

        // if down and multipath -> split
        bool split = !elem.up && multi_child && !in_same_split;

        unresolved_stack.push_back(UnresolvedStackElement{elem, split});
        if (split) {
            split_stack.push_back(elem);
        }
    }
}

// -------------------------------------------------------------------------------------

// PathFinder implementations
PathFinder::PathFinder()
  : filters{
        Filter{
            .filter = &PathFinder::_count,
            .discovery = true,
            .counter =
                Counter{
                    .hide = true,
                },
        },
        Filter{
            .filter = &PathFinder::_filter_path_by_node_type,
            .discovery = true,
            .counter =
                Counter{
                    .name = "node type",
                },
        },
        Filter{
            .filter = &PathFinder::_filter_path_gif_type,
            .discovery = true,
            .counter =
                Counter{
                    .name = "gif type",
                },
        },
        Filter{
            .filter = &PathFinder::_filter_path_by_dead_end_split,
            .discovery = true,
            .counter =
                Counter{
                    .name = "dead end split",
                },
        },
        Filter{
            .filter = &PathFinder::_filter_conditional_link,
            .discovery = true,
            .counter =
                Counter{
                    .name = "conditional link",
                },
        },
        Filter{
            .filter = &PathFinder::_build_path_stack_and_handle_splits,
            .discovery = true,
            .counter =
                Counter{
                    .name = "build stack",
                },
        },
        Filter{
            .filter = &PathFinder::_filter_path_by_end_in_self_gif,
            .discovery = false,
            .counter =
                Counter{
                    .name = "end in self gif",
                },
        },
        Filter{
            .filter = &PathFinder::_filter_path_same_end_type,
            .discovery = false,
            .counter =
                Counter{
                    .name = "same end type",
                },
        },
        Filter{
            .filter = &PathFinder::_filter_path_by_stack,
            .discovery = false,
            .counter =
                Counter{
                    .name = "stack",
                },
        },
        Filter{
            .filter = &PathFinder::_handle_valid_split_branch,
            .discovery = false,
            .counter =
                Counter{
                    .name = "valid split branch",
                },
        },
    } {
}

// Filter implementations
bool Filter::exec(PathFinder *pf, BFSPath &p) {
    bool out = counter.exec(pf, filter, p);
    if (!out && discovery) {
        p.filtered = true;
    }
    return out;
}

bool PathFinder::run_filters(BFSPath &p) {
    for (auto &filter : filters) {
        bool res = filter.exec(this, p);
        if (!res) {
            return false;
        }
    }
    return true;
}

/*
filtered: contains illegal links
valid: reached dst with no illegal links
complete: all splits have a valid branch
*/

std::pair<std::vector<Path>, std::vector<Counter>>
PathFinder::find_paths(Node_ref src, std::vector<Node_ref> dst) {
    if (!src->get_type().is_moduleinterface()) {
        throw std::runtime_error("src type is not MODULEINTERFACE");
    }
    std::unordered_set<Node_ref> dsts;
    for (auto &d : dst) {
        if (!d->get_type().is_moduleinterface()) {
            throw std::runtime_error("dst type is not MODULEINTERFACE");
        }
        dsts.insert(d);
    }

    std::vector<std::shared_ptr<BFSPath>> valid_paths;

    Counter total_counter{.name = "total", .total_counter = true};

    PerfCounter pc_bfs;

    // Valid paths BFS
    bfs_visit(src->get_self_gif().get(), [&](BFSPath &p) {
        bool res = total_counter.exec(this, &PathFinder::run_filters, p);
        if (!res) {
            return;
        }

        valid_paths.push_back(p.shared_from_this());

        if (p.get_path_data().not_complete) {
            return;
        }

        // TODO consider removing this if the new path split pruning works well
        // shortcut if path to dst found
        auto last = p.last()->get_node();
        if (dsts.contains(last)) {
            dsts.erase(last);
            if (dsts.empty()) {
                p.stop = true;
            }
        }
    });

    printf("TIME: %3.2lf ms BFS\n", pc_bfs.ms());

    // Complete paths
    Counter incomplete_counter{.name = "incomplete", .total_counter = false};
    std::vector<Path> complete_paths;
    for (const auto &p : valid_paths) {
        if (!incomplete_counter.exec(this, &PathFinder::_filter_incomplete, *p)) {
            continue;
        }
        complete_paths.push_back(Path(std::move(p->get_path())));
    }

    // Counters
    std::vector<Counter> counters;
    for (auto &f : filters) {
        auto &counter = f.counter;
        if (counter.hide) {
            continue;
        }
        counters.push_back(counter);
    }
    counters.push_back(total_counter);
    counters.push_back(incomplete_counter);

    // Return
    return std::make_pair(complete_paths, counters);
}

// Filters -----------------------------------------------------------------------------

bool PathFinder::_count(BFSPath &p) {
    path_cnt++;
    if (path_cnt % 50000 == 0) {
        printf("path_cnt: %lld\n", path_cnt);
    }
    if (path_cnt > PATH_LIMITS.absolute) {
        p.stop = true;
    }
    return true;
}

bool PathFinder::_filter_path_by_node_type(BFSPath &p) {
    return (p.last()->get_node()->get_type().is_moduleinterface());
}

bool PathFinder::_filter_path_gif_type(BFSPath &p) {
    auto last = p.last();
    return (dynamic_cast<GraphInterfaceSelf *>(last) ||
            dynamic_cast<GraphInterfaceHierarchical *>(last) ||
            dynamic_cast<GraphInterfaceModuleConnection *>(last));
}

bool PathFinder::_filter_path_by_end_in_self_gif(BFSPath &p) {
    return dynamic_cast<GraphInterfaceSelf *>(p.last());
}

bool PathFinder::_filter_path_same_end_type(BFSPath &p) {
    return p.last()->get_node()->get_type() == p.first()->get_node()->get_type();
}

bool PathFinder::_build_path_stack_and_handle_splits(BFSPath &p) {
    auto edge = p.last_edge();
    if (!edge) {
        return true;
    }

    auto elem = _extend_path_hierarchy_stack(*edge);
    if (!elem) {
        return true;
    }

    auto &data = p.get_path_data_mut();
    auto &unresolved_stack = data.unresolved_stack;
    auto &split_stack = data.split_stack;

    size_t split_cnt = split_stack.size();

    // heuristic, stop weak paths after limit
    // no need to check for extension first, since growth of split results earlier in
    // stop
    if (split_cnt > 0 && path_cnt > PATH_LIMITS.no_weak) {
        return false;
    }

    _extend_fold_stack(elem.value(), unresolved_stack, split_stack);
    size_t split_cnt_new = split_stack.size();

    int split_growth = split_cnt_new - split_cnt;
    p.confidence *= std::pow(0.5, split_growth);

    // heuristic, stop making weaker paths after limit
    if (split_growth > 0 && path_cnt > PATH_LIMITS.no_new_weak) {
        return false;
    }

    if (split_growth == 0) {
        return true;
    }

    assert(!elem->up);

    // handle split
    data.not_complete = true;

    auto split_point = elem->parent_gif;
    Path split_prefix(std::vector(p.get_path().begin(), p.get_path().end() - 1));
    auto &splits = this->split[split_point];

    printf_split("Split: %s\n", p.str().c_str());

    // check if split point already in split map
    // if yes, hibernate, wait till other branches complete
    if (splits.contains(split_prefix)) {
        auto &split_state = splits.at(split_prefix);
        // TODO this should never happen imo with Path as key
        // later we will need this when using PathStack as key
        if (split_state.complete) {
            assert(false);
            return false;
        }
        // if split has no valid paths yet (no waiting), but already exists
        // it is either a deadend or still busy, thus hibernate and either wait for wake
        // or never wake up
        if (split_state.waiting) {
            printf_split("Skip hibernate, being awated\n");
        } else {
            printf_split("Hibernate until scheduled\n");
            p.hibernated = true;
            split_state.wait_paths[elem->child_gif].push_back(p.shared_from_this());
        }
        return true;
    }

    // make new split
    printf_split("New split\n");
    splits.emplace(split_prefix, SplitState{p});

    return true;
}

bool PathFinder::_filter_path_by_stack(BFSPath &p) {
    const auto splits = p.get_path_data();
    auto &unresolved_stack = splits.unresolved_stack;

    return unresolved_stack.empty();
}

bool PathFinder::_handle_valid_split_branch(BFSPath &p) {
    const auto splits = p.get_path_data();
    auto &split_stack = splits.split_stack;

    if (split_stack.empty()) {
        // Not a multi path branch
        return true;
    }

    // strategy:
    //  - get all splits
    //  - check if all splits have a complete branch
    //  - if yes
    //      - remove all hibernated paths related to these splits
    //        because we only have to track this (or first) branch from here
    //        done implicitly by marking them strong from here, this results in
    //        all others not having neighbours to explore
    //        will also take the shortest/best path first
    //      - make all split valid paths complete
    //        - necessary because of implied paths tracking all conditional links
    //  - if no
    //      - hibernate (no need to keep on searching if not complete yet)
    //      - awake branches from split

    printf_split("Handle valid split branch: %s\n", p.str().c_str());

    for (auto &split_elem : std::ranges::reverse_view(split_stack)) {
        auto &split_point = split_elem.parent_gif;
        auto &splits_at_point = this->split[split_point];
        for (auto &[split_prefix, split_state] : splits_at_point) {
            if (!p.starts_with(split_prefix)) {
                continue;
            }
            // found split_state for this path & split point

            split_state.suffix_complete_paths[split_elem.child_gif].push_back(
                p.shared_from_this());
            if (split_state.complete) {
                continue;
            }

            printf_split("Check complete branch for %s\n", split_prefix.str().c_str());
            // check complete branch
            for (auto &[child_gif, paths] : split_state.suffix_complete_paths) {
                // check if child complete (has path ending in same gif)
                if (paths.size()) {
                    bool found = false;
                    for (auto &path : paths) {
                        if (path->last() == p.last()) {
                            found = true;
                            break;
                        }
                    }
                    if (found) {
                        continue;
                    }
                }
                // handle incomplete child branch

                // wake up branch for that child
                auto &wait_paths = split_state.wait_paths[child_gif];
                if (wait_paths.size() == 0) {
                    // if not waiting paths we wait till they appear
                    // they will check themselves
                    split_state.waiting = true;
                    printf_split("No waiting paths\n");
                } else {
                    auto &back = wait_paths.back();
                    // TODO maybe use queue instead of vector
                    printf_split("Wake up path: %s\n", back->str().c_str());
                    back->hibernated = false;
                    wait_paths.pop_back();
                    p.wake_signal = true;
                }

                // TODO this is an optimization, but it does not fully work like this
                // we need to get woken up from somewhere in the case that this
                // is not the merging point yet (test_split_chain)

                // wait till branch complete, or woken up to advance to the next mif
                // in-case this was not the merging point yet
                // p.hibernated = true;

                // no need to go lower in stack if not complete branch
                return true;
            }

            printf_split("Complete branch found\n");
            split_state.complete = true;
            // remove all waiting paths
            for (auto &[child_gif, wait_paths] : split_state.wait_paths) {
                for (auto &wait_path : wait_paths) {
                    wait_path->filtered = true;
                }
                wait_paths.clear();
            }
            // only single match here
            break;
        }
    }

    printf_split("All branches complete\n");

    auto root_split = this->split[split_stack.front().parent_gif];
    for (auto &[split_prefix, split_state] : root_split) {
        if (!p.starts_with(split_prefix)) {
            continue;
        }

        for (auto &[child_gif, paths] : split_state.suffix_complete_paths) {
            for (auto &path : paths) {
                auto &data = path->get_path_data_mut();
                data.not_complete = false;
                path->hibernated = false;
                data.split_stack.clear();
                path->confidence = 1.0;
                p.wake_signal = true;

                printf_split("Mark strong %s\n", path->str().c_str());

                // TODO question: are we marking the path elements strong somewhere now?
            }
        }
    }

    return true;
}

bool PathFinder::_filter_path_by_dead_end_split(BFSPath &p) {
    auto last_tri_edge = p.last_tri_edge();
    if (!last_tri_edge) {
        return true;
    }
    auto &[one, two, three] = *last_tri_edge;

    auto one_h = dynamic_cast<GraphInterfaceHierarchical *>(one);
    auto two_h = dynamic_cast<GraphInterfaceHierarchical *>(two);
    auto three_h = dynamic_cast<GraphInterfaceHierarchical *>(three);
    if (!one_h || !two_h || !three_h) {
        return true;
    }

    // check if child->parent->child
    if (!one_h->get_is_parent() && two_h->get_is_parent() && !three_h->get_is_parent()) {
        return false;
    }

    return true;
}

bool PathFinder::_filter_conditional_link(BFSPath &p) {
    auto edge = p.last_edge();
    if (!edge) {
        return true;
    }
    /*const*/ auto linkobj = p.get_link(*edge);
    // printf("Path: %s\n", p.str().c_str());
    // printf("Edge: %s\n", edge->str().c_str());

    bool ok = true;
    p.iterate_edges([&](Edge &edge) {
        auto link_conditional = dynamic_cast<LinkDirectConditional *>(p.get_link(edge));
        if (!link_conditional) {
            return true;
        }
        bool is_last_edge = edge.to == p.last();
        if (link_conditional->needs_to_check_only_first_in_path() && !is_last_edge) {
            return true;
        }
        bool filtered_out = link_conditional->run_filter(p) !=
                            LinkDirectConditional::FilterResult::FILTER_PASS;
        ok &= !filtered_out;
        // no need to iterate further
        return ok;
    });

    return ok;
}

bool PathFinder::_filter_incomplete(BFSPath &p) {
    return !p.get_path_data().not_complete;
}
