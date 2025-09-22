from typing import Protocol, runtime_checkable

from faebryk.core.cpp import (
    GraphInterface,
    GraphInterfaceHierarchical,
    GraphInterfaceReference,
    LinkNamedParent,
    LinkParent,
    LinkPointer,
    LinkSibling,
)
from faebryk.core.node import CNode, Node

# Manually create Trait type and implements_type instance here,

# Build TYPE
# Build Trait
# Build implement_type
# Instantiate implement_type and assign to Trait
# Rest easy

# No python type checking, use protocol checking instead
# Everything should inherit directly from _Node
# Traits are not special, they are just marked by a "implements_trait" node
# Types are slightly special because they have rules for constructing children
# Types are marked by an "implements_type" node


class _Node(CNode):
    @runtime_checkable
    class Proto_Node(Protocol):
        is_type: GraphInterfaceHierarchical

    def __setattr__(self, name: str, value, /) -> None:
        super().__setattr__(name, value)
        if isinstance(value, GraphInterface):
            self.self_gif.connect(value, link=LinkSibling())
            value.node = self
            value.name = name
        elif isinstance(value, CNode):
            value.parent.connect(value.children, LinkNamedParent(name))
        if isinstance(value, Node):
            value._handle_added_to_parent()


def compose(parent: _Node, child: _Node, name: str | None = None):
    link = LinkParent() if not name else LinkNamedParent(name)
    parent.children.connect(child.parent, link)
    return parent


# Base Traits --------------------------------------------------------------------------
class Class_ImplementsType:
    @runtime_checkable
    class Proto_Type(Protocol):
        _identifier: str
        instances: GraphInterfaceHierarchical

    @staticmethod
    def init_type_node(type_node: _Node, identifier: str):
        type_node._identifier = identifier
        type_node.instances = GraphInterfaceHierarchical(is_parent=True)
        # bootstrap
        if identifier == "ImplementsType":
            return type_node
        compose(type_node, instantiate(Type_ImplementsType))
        return type_node

    @staticmethod
    def execute(type_node: _Node, node: _Node) -> None:
        child_ref = child_ref_pointer.get_reference()
        assert isinstance(child_ref, ChildRef)
        identifier = child_ref._identifier

        node_type = child_ref.node_type_pointer.get_reference()
        assert isinstance(node_type, Proto_Type)
        obj = node_type.execute()

        node.add(obj, name=identifier)


Type_ImplementsType = Class_ImplementsType.init_type_node(_Node(), "ImplementsType")
# need to manually set it now that it's bootstrapped
compose(Type_ImplementsType, instantiate(Type_ImplementsType))


class Class_ImplementsTrait:
    @staticmethod
    def init_trait_type(trait_node: _Node, identifier: str):
        Class_ImplementsType.init_type_node(trait_node, identifier)
        # bootstrap
        if identifier == "ImplementsTrait":
            return trait_node
        compose(trait_node, instantiate(Type_ImplementsTrait))
        return trait_node


Type_ImplementsTrait = Class_ImplementsTrait.init_trait_type(_Node(), "ImplementsTrait")
# now that we have trait, init our base traits with it
compose(Type_ImplementsTrait, instantiate(Type_ImplementsTrait))
compose(Type_ImplementsType, instantiate(Type_ImplementsTrait))


# --------------------------------------------------------------------------------------

TwoTerminal = Class_ImplementsTrait.init_trait_type(_Node(), "TwoTerminal")


class Class_CanBridge:
    @runtime_checkable
    class Proto_CanBridge(Protocol):
        in_: GraphInterfaceReference
        out: GraphInterfaceReference

    @staticmethod
    def init_can_bridge_node(node: _Node):
        Class_ImplementsTrait.init_trait_type(node, "CanBridge")

        node.in_ = GraphInterfaceReference()
        node.out = GraphInterfaceReference()

    @staticmethod
    def get_in(node: _Node):
        assert isinstance(node, Class_CanBridge.Proto_CanBridge)
        return node.in_.get_referenced_gif().node

    @staticmethod
    def get_out(node: _Node):
        assert isinstance(node, Class_CanBridge.Proto_CanBridge)
        return node.out.get_referenced_gif().node


CanBridge = Class_CanBridge.init_can_bridge_node(_Node())


# Standard Types =======================================================================
class Class_MakeChild:
    @runtime_checkable
    class Proto_MakeChild(Protocol):
        child_ref_pointer: GraphInterfaceReference

    @staticmethod
    def init_make_child_type(node: _Node) -> _Node:
        make_child_type_node = Class_ImplementsType.init_type_node(node, "MakeChild")
        return make_child_type_node

    @staticmethod
    def execute(type_node: _Node, node: _Node) -> None:
        assert isinstance(type_node, Class_MakeChild.Proto_MakeChild)
        child_ref = type_node.child_ref_pointer.get_reference()
        assert isinstance(child_ref, Class_ChildReference.Proto_ChildReference)
        identifier = child_ref._identifier

        node_type = child_ref.node_type_pointer.get_reference()
        assert isinstance(node_type, Class_ImplementsType.Proto_Type)
        new_node = Class_ImplementsType.execute(node_type, _Node())

        node.add(new_node, name=identifier)


class Class_ChildReference:
    @runtime_checkable
    class Proto_ChildReference(Protocol):
        _identifier: str
        node_type_pointer: GraphInterfaceReference

    # @staticmethod
    # def init_child_reference_type(node: _Node) -> _Node:
    #     child_reference_type_node = Class_ImplementsType.init_type_node(node, "ChildReference")


Type_MakeChild = Class_ImplementsType.init_type_node(_Node(), "MakeChild")


def instantiate(type_node: _Node) -> _Node:
    assert isinstance(type_node, Class_ImplementsType.Proto_Type)

    node_instance = _Node()
    node_instance.is_type = GraphInterfaceHierarchical(is_parent=False)
    node_instance.is_type.connect(type_node.instances, link=LinkParent())

    for rule in type_node.get_children(
        direct_only=True, types=[Class_MakeChild.Proto_MakeChild]
    ):
        assert isinstance(rule, Class_MakeChild.Proto_MakeChild)
        child_reference = rule.child_ref_pointer.get_reference()
        assert isinstance(child_reference, Class_ChildReference.Proto_ChildReference)
        child_identifier = child_reference._identifier
        child_type_node = child_reference.node_type_pointer.get_reference()
        assert isinstance(child_type_node, Class_ImplementsType.Proto_Type)
        child_node_instance = instantiate(child_type_node)
    for rule in t.get_children(direct_only=True, types=Connect):
        assert isinstance(rule, Rule)
        rule.execute(node)

    return node


### Construction Rules ###

# class FieldDeclaration(Rule):
#     def __init__(self, identifier: str | None, nodetype: type[_Node]):
#         super().__init__()
#         self.identifier = identifier
#         self.nodetype = nodetype

#     def execute(self, node: _Node) -> None:
#         super().execute(node)
#         obj = self.nodetype()

#         node.add(obj, name=self.identifier)


class MakeChild(_Node):
    child_ref_pointer: GraphInterfaceReference

    def __postinit__(self):
        self.type.connect(type_make_child.self_gif)

    def with_child_reference(self, child_ref: ChildRef) -> "MakeChild":
        self.child_ref_pointer.connect(child_ref.self_gif, link=LinkPointer())
        return self

    def execute(self, node: Node) -> None:
        super().execute(node)

        child_ref = self.child_ref_pointer.get_reference()
        assert isinstance(child_ref, ChildRef)
        identifier = child_ref._identifier

        node_type = child_ref.node_type_pointer.get_reference()
        assert isinstance(node_type, Class_ImplementsType.Proto_Type)
        obj = node_type.execute(_Node())

        node.add(obj, name=identifier)


class Connect(_Node):
    def with_nested_references(self, refs: list[NestedReference]) -> "Connect":
        self._refs = refs
        return self

    def execute(self, node: Node) -> None:
        super().execute(node)

        # Recursive implementation
        def resolve_nested_reference(
            parent_node: Node, nested_ref: NestedReference
        ) -> Node:
            # Get child reference of this nested reference
            child_ref = nested_ref.child_ref_pointer.get_reference()
            assert isinstance(child_ref, ChildRef)
            child_identifier = child_ref._identifier
            ref_node = parent_node.get_child_by_name(child_identifier)
            assert isinstance(ref_node, Node)

            # If next NR, resolve it starting from the instance returned by first NR
            if len(nested_ref.next.get_connected_nodes(types=[NestedReference])) > 0:
                next_nested_ref = list(
                    nested_ref.next.get_connected_nodes(types=[NestedReference])
                )[0]
                assert isinstance(next_nested_ref, NestedReference)
                ref_node = resolve_nested_reference(ref_node, next_nested_ref)

            return ref_node

        nodes_to_connect = []
        for ref in self._refs:
            resolved_target_node = resolve_nested_reference(node, ref)
            assert isinstance(resolved_target_node, Node)
            nodes_to_connect.append(resolved_target_node)

        for instance in nodes_to_connect[1:]:
            assert isinstance(nodes_to_connect[0], Node)
            assert isinstance(instance, Node)
            nodes_to_connect[0].connections.connect(instance.connections)


### References ###
class RefNode(Node):
    pass


class ChildRef(RefNode):
    node_type_pointer: GraphInterfaceReference

    def __init__(self, identifier: str):
        super().__init__()
        self._identifier = identifier

    def with_nodetype(self, child_type_ref: Proto_Type) -> "ChildRef":
        self.node_type_pointer.connect(child_type_ref.self_gif, link=LinkPointer())
        return self


class NestedReference(RefNode):
    child_ref_pointer: GraphInterfaceReference
    prev: GraphInterface
    next: GraphInterface

    def with_child_reference(self, child_ref: ChildRef) -> "NestedReference":
        self.child_ref_pointer.connect(child_ref.self_gif, link=LinkPointer())
        return self
