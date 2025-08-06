/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#include "graph/graph.hpp"
#include "graph/graphinterfaces.hpp"
#include "graph/links.hpp"
#include "nano.hpp"
#include "pathfinder/pathfinder.hpp"
#include <nanobind/nanobind.h>

// check if c++20 is used
#if __cplusplus < 202002L
#error "C++20 is required"
#endif

#if EDITABLE
#define PYMOD(m) NB_MODULE(faebryk_core_cpp_editable, m)
#pragma message("EDITABLE")
#else
#define PYMOD(m) NB_MODULE(faebryk_core_cpp, m)
#endif

// #include <nanobind/nb_types.h>

namespace nb = nanobind;
using namespace nb::literals;

// -------------------------------------------------------------------------------------

int add(int i, int j) {
    return i + j;
}

int call_python_function(std::function<int()> func) {
    auto out = func();
    printf("%d\n", out);
    return out;
}

void print_obj(nb::handle obj) {
    printf("%s\n", nb::repr(obj).c_str());
}

void print_obj_pyptr(PyObject *pyobj) {
    auto obj = nb::handle(pyobj);
    print_obj(obj);
}

std::pair<std::vector<Path>, std::vector<Counter>>
find_paths(Node_ref src, std::vector<Node_ref> dst) {
    PerfCounter pc;

    PathFinder pf;
    auto res = pf.find_paths(src, dst);

    printf("TIME: %3.2lf ms C++ find paths\n", pc.ms());
    return res;
}

PYMOD(m) {
    m.doc() = "faebryk core c++ module";

    m.def("add", &add, "i"_a, "j"_a = 1, "A function that adds two numbers");
    m.def("call_python_function", &call_python_function, "func"_a);
    m.def("set_leak_warnings", &nb::set_leak_warnings, "value"_a);
    m.def("print_obj", &print_obj, "obj"_a);

    // TODO why this rv_pol needed
    m.def("find_paths", &find_paths, "src"_a, "dst"_a, nb::rv_policy::reference);
    m.def("set_indiv_measure", &set_indiv_measure, "value"_a);

    m.def("set_max_paths", &set_max_paths);
    // Graph
    using GI = GraphInterface;

    FACTORY(
        nb::class_<GI>(m, "GraphInterface")
            .def("__repr__", &GI::repr)
            .def("get_graph", &GI::get_graph)
            .def_prop_ro("G", &GI::get_graph)
            .def("get_gif_edges", &GI::get_gif_edges, nb::rv_policy::reference)
            .def_prop_ro("edges", &GI::get_edges, nb::rv_policy::reference)
            .def_prop_rw("node", &GI::get_node, &GI::set_node)
            .def("is_connected_to", &GI::is_connected)
            .def_prop_rw("name", &GI::get_name, &GI::set_name)
            .def("get_connected_nodes", &GI::get_connected_nodes, "types"_a)
            .def("connect", nb::overload_cast<GI_ref_weak>(&GI::connect), "other"_a)
            .def("connect", nb::overload_cast<GI_refs_weak>(&GI::connect), "others"_a)
            .def("connect", nb::overload_cast<GI_ref_weak, Link_ref>(&GI::connect),
                 "other"_a, "link"_a)
            .def("connect", nb::overload_cast<GI_refs_weak, Link_ref>(&GI::connect),
                 "others"_a, "link"_a),
        &GraphInterface::factory<GraphInterface>);

    nb::class_<Graph>(m, "Graph")
        .def(nb::init<>())
        .def("get_edges", &Graph::get_edges, nb::rv_policy::reference)
        .def_prop_ro("edges", &Graph::all_edges, nb::rv_policy::reference)
        .def("get_gifs", &Graph::get_gifs, nb::rv_policy::reference)
        .def("invalidate", &Graph::invalidate)
        .def_prop_ro("node_count", &Graph::node_count)
        .def_prop_ro("edge_count", &Graph::edge_count)
        .def("node_projection", &Graph::node_projection)
        .def("nodes_by_names", &Graph::nodes_by_names)
        .def("bfs_visit", &Graph::bfs_visit, "filter"_a, "start"_a,
             nb::rv_policy::reference)
        .def("__repr__", &Graph::repr);

    nb::exception<LinkExists>(m, "LinkExists");
    // nb::class_<LinkExists>(m, "LinkExists")
    //     .def("existing_link", &LinkExists::get_existing_link,
    //     nb::rv_policy::reference) .def("new_link", &LinkExists::get_new_link,
    //     nb::rv_policy::reference);

    // Graph interfaces
    FACTORY((nb::class_<GraphInterfaceSelf, GI>(m, "GraphInterfaceSelf")),
            &GraphInterfaceSelf::factory<GraphInterfaceSelf>);

    FACTORY((nb::class_<GraphInterfaceReference, GI>(m, "GraphInterfaceReference")
                 .def("get_referenced_gif", &GraphInterfaceReference::get_referenced_gif,
                      nb::rv_policy::reference)
                 .def("get_reference", &GraphInterfaceReference::get_reference)),
            &GraphInterfaceReference::factory<GraphInterfaceReference>);

    nb::exception<GraphInterfaceReference::UnboundError>(
        m, "GraphInterfaceReferenceUnboundError");

    FACTORY(
        (nb::class_<GraphInterfaceHierarchical, GI>(m, "GraphInterfaceHierarchical")
             .def("get_parent", &GraphInterfaceHierarchical::get_parent)
             .def("get_children", &GraphInterfaceHierarchical::get_children)
             .def_prop_ro("is_parent", &GraphInterfaceHierarchical::get_is_parent)
             .def("disconnect_parent", &GraphInterfaceHierarchical::disconnect_parent)),
        &GraphInterfaceHierarchical::factory<GraphInterfaceHierarchical>, "is_parent"_a);

    FACTORY((nb::class_<GraphInterfaceModuleSibling, GraphInterfaceHierarchical>(
                m, "GraphInterfaceModuleSibling")),
            &GraphInterfaceModuleSibling::factory<GraphInterfaceModuleSibling>,
            "is_parent"_a);

    FACTORY((nb::class_<GraphInterfaceModuleConnection, GI>(
                m, "GraphInterfaceModuleConnection")),
            &GraphInterfaceModuleConnection::factory<GraphInterfaceModuleConnection>);

    // Links
    nb::class_<Link>(m, "Link")
        .def("__eq__", &Link::operator==)
        .def("is_cloneable", &Link::is_cloneable);
    nb::class_<LinkParent, Link>(m, "LinkParent").def(nb::init<>());
    nb::class_<LinkNamedParent, LinkParent>(m, "LinkNamedParent")
        .def(nb::init<std::string>());
    nb::class_<LinkDirect, Link>(m, "LinkDirect").def(nb::init<>());
    nb::class_<LinkPointer, Link>(m, "LinkPointer").def(nb::init<>());
    nb::class_<LinkSibling, LinkPointer>(m, "LinkSibling").def(nb::init<>());
    nb::class_<LinkDirectConditional, LinkDirect>(m, "LinkDirectConditional")
        .def(nb::init<LinkDirectConditional::FilterF, bool>(), "filter"_a,
             "needs_only_first_in_path"_a = false);
    nb::class_<LinkDirectDerived, LinkDirectConditional>(m, "LinkDirectDerived")
        .def(nb::init<Path>());

    nb::exception<LinkDirectConditional::LinkFilteredException>(m,
                                                                "LinkFilteredException");
    nb::enum_<LinkDirectConditional::FilterResult>(m,
                                                   "LinkDirectConditionalFilterResult")
        .value("FILTER_PASS", LinkDirectConditional::FilterResult::FILTER_PASS)
        .value("FILTER_FAIL_RECOVERABLE",
               LinkDirectConditional::FilterResult::FILTER_FAIL_RECOVERABLE)
        .value("FILTER_FAIL_UNRECOVERABLE",
               LinkDirectConditional::FilterResult::FILTER_FAIL_UNRECOVERABLE);

    // Node
    nb::class_<Node>(m, "Node")
        .def(nb::init<>())
        .def_static("transfer_ownership", &Node::transfer_ownership)
        .def("get_graph", &Node::get_graph)
        .def_prop_ro("self_gif", &Node::get_self_gif)
        .def_prop_ro("children", &Node::get_children_gif)
        .def_prop_ro("parent", &Node::get_parent_gif)
        .def("get_children", &Node::get_children, "direct_only"_a,
             "types"_a = nb::none(), "include_root"_a = false, "f_filter"_a = nb::none(),
             "sort"_a = true)
        .def("get_parent", &Node::get_parent)
        .def("get_parent_force", &Node::get_parent_force)
        .def("get_name", &Node::get_name, "accept_no_parent"_a = false)
        .def("get_hierarchy", &Node::get_hierarchy)
        .def("get_full_name", &Node::get_full_name, "types"_a = false)
        .def("isinstance", nb::overload_cast<nb::type_object>(&Node::isinstance),
             "type"_a)
        .def("isinstance",
             nb::overload_cast<std::vector<nb::type_object>>(&Node::isinstance),
             "types"_a)
        .def("bfs_node", &Node::bfs_node, "filter"_a)
        .def_prop_rw("no_include_parents_in_full_name",
                     &Node::getter_no_include_parents_in_full_name,
                     &Node::setter_no_include_parents_in_full_name)
        .def("get_root_id", &Node::get_root_id)
        .def("__repr__", &Node::repr);

    nb::exception<Node::NodeException>(m, "NodeException");
    nb::exception<Node::NodeNoParent>(m, "NodeNoParent");

    // Pathfinder
    nb::class_<Counter>(m, "Counter")
        .def_ro("in_cnt", &Counter::in_cnt)
        .def_ro("weak_in_cnt", &Counter::weak_in_cnt)
        .def_ro("out_weaker", &Counter::out_weaker)
        .def_ro("out_stronger", &Counter::out_stronger)
        .def_ro("out_cnt", &Counter::out_cnt)
        .def_ro("time_spent_s", &Counter::time_spent_s)
        .def_ro("hide", &Counter::hide)
        .def_ro("name", &Counter::name)
        .def_ro("multi", &Counter::multi)
        .def_ro("total_counter", &Counter::total_counter);

    // Path
    nb::class_<Edge>(m, "Edge")
        .def("__repr__", &Edge::str)
        .def_ro("from_", &Edge::from, nb::rv_policy::reference)
        .def_ro("to", &Edge::to, nb::rv_policy::reference);

    // nb::class_<TriEdge>(m, "TriEdge");

    nb::class_<Path>(m, "Path")
        .def("__repr__", &Path::str)
        .def("__len__", &Path::size)
        .def("contains", &Path::contains)
        .def("last", &Path::last, nb::rv_policy::reference)
        .def("first", &Path::first, nb::rv_policy::reference)
        //.def("last_edge", &Path::last_edge)
        //.def("last_tri_edge", &Path::last_tri_edge)
        .def("get_link", &Path::get_link)
        .def("iterate_edges", &Path::iterate_edges)
        .def("__getitem__", &Path::operator[], nb::rv_policy::reference);
}
