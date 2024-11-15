/* This file is part of the faebryk project
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include "graph/graph.hpp"
#include "graphinterfaces.hpp"

class LinkDirect : public Link {
  public:
    LinkDirect();
    LinkDirect(GI_ref_weak from, GI_ref_weak to);
    LinkDirect(const LinkDirect &other);
    Link_ref clone() const override;
    bool is_cloneable() const override;
};

class LinkParent : public Link {
    GraphInterfaceHierarchical *parent;
    GraphInterfaceHierarchical *child;

  public:
    LinkParent();
    LinkParent(GraphInterfaceHierarchical *from, GraphInterfaceHierarchical *to);
    LinkParent(const LinkParent &other);
    void set_connections(GI_ref_weak from, GI_ref_weak to) override;
    GraphInterfaceHierarchical *get_parent();
    GraphInterfaceHierarchical *get_child();
    Link_ref clone() const override;
    bool is_cloneable() const override;
};

class LinkNamedParent : public LinkParent {
    std::string name;

  public:
    LinkNamedParent(std::string name);
    LinkNamedParent(std::string name, GraphInterfaceHierarchical *from,
                    GraphInterfaceHierarchical *to);
    LinkNamedParent(const LinkNamedParent &other);
    std::string get_name();
    Link_ref clone() const override;
    bool operator==(const Link &other) const override;
    bool is_cloneable() const override;
};

class LinkPointer : public Link {
    GraphInterfaceSelf *pointee;
    GraphInterface *pointer;

  public:
    LinkPointer();
    LinkPointer(GI_ref_weak from, GraphInterfaceSelf *to);
    LinkPointer(const LinkPointer &other);
    void set_connections(GI_ref_weak from, GI_ref_weak to) override;
    GraphInterface *get_pointer();
    GraphInterfaceSelf *get_pointee();
    Link_ref clone() const override;
    bool is_cloneable() const override;
};

class LinkSibling : public LinkPointer {
  public:
    LinkSibling();
    LinkSibling(GI_ref_weak from, GraphInterfaceSelf *to);
    LinkSibling(const LinkSibling &other);
    Link_ref clone() const override;
    bool is_cloneable() const override;
};

class LinkDirectConditional : public LinkDirect {
    friend class LinkDirectDerived;

  public:
    enum FilterResult {
        FILTER_PASS,
        FILTER_FAIL_RECOVERABLE,
        FILTER_FAIL_UNRECOVERABLE
    };

    using FilterF = std::function<FilterResult(Path path)>;

    struct LinkFilteredException : public std::runtime_error {
        LinkFilteredException(std::string msg)
          : std::runtime_error(msg) {
        }
    };

  private:
    FilterF filter;
    bool needs_only_first_in_path;

  public:
    LinkDirectConditional(FilterF filter, bool needs_only_first_in_path);
    LinkDirectConditional(FilterF filter, bool needs_only_first_in_path,
                          GI_ref_weak from, GI_ref_weak to);
    LinkDirectConditional(const LinkDirectConditional &other);
    void set_connections(GI_ref_weak from, GI_ref_weak to) override;
    FilterResult run_filter(Path path);

    bool needs_to_check_only_first_in_path();
    Link_ref clone() const override;
    bool operator==(const Link &other) const override;
    bool is_cloneable() const override;
};

class LinkDirectShallow : public LinkDirectConditional {
    // TODO
  public:
    LinkDirectShallow();
    LinkDirectShallow(const LinkDirectShallow &other);
    Link_ref clone() const override;
    bool operator==(const Link &other) const override;
    bool is_cloneable() const override;
};

class LinkDirectDerived : public LinkDirectConditional {
  private:
    static std::pair<LinkDirectConditional::FilterF, bool>
    make_filter_from_path(Path path);

    Path path;

  public:
    LinkDirectDerived(Path path);
    LinkDirectDerived(Path path, std::pair<FilterF, bool> filter);
    LinkDirectDerived(Path path, GI_ref_weak from, GI_ref_weak to);
    LinkDirectDerived(Path path, std::pair<FilterF, bool> filter, GI_ref_weak from,
                      GI_ref_weak to);
    LinkDirectDerived(const LinkDirectDerived &other);
    Link_ref clone() const override;
    bool operator==(const Link &other) const override;
    bool is_cloneable() const override;
};
