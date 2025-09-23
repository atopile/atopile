from typing import Any, Protocol, runtime_checkable

from git.util import T

from faebryk.core.cpp import (
    GraphInterface,
    GraphInterfaceHierarchical,
    GraphInterfaceModuleConnection,
    GraphInterfaceReference,
    LinkDirect,
    LinkNamedParent,
    LinkParent,
    LinkPointer,
    LinkSibling,
)
from faebryk.core.node import CNode, Node
from faebryk.libs.util import cast

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
        connections: GraphInterfaceHierarchical

    def __init__(self):
        super().__init__()
        # self.is_type = GraphInterfaceHierarchical(is_parent=False)
        self.connections = GraphInterfaceModuleConnection()
        CNode.transfer_ownership(self)

    def __setattr__(self, name: str, value, /) -> None:
        super().__setattr__(name, value)
        if isinstance(value, GraphInterface):
            value.node = self
            value.name = name
            self.self_gif.connect(value, link=LinkSibling())
        elif isinstance(value, CNode):
            value.parent.connect(value.children, LinkNamedParent(name))
        if isinstance(value, Node):
            value._handle_added_to_parent()


def compose(parent: _Node, child: _Node, name: str | None = None):
    link = LinkParent() if not name else LinkNamedParent(name)
    child.parent.connect(parent.children, link)
    return parent


def instantiate(type_node: _Node) -> _Node:
    node = _Node()
    node.is_type = GraphInterfaceHierarchical(is_parent=False)
    assert isinstance(node, _Node.Proto_Node)
    assert isinstance(type_node, Class_ImplementsType.Proto_Type)
    node.is_type.connect(
        type_node.instances, LinkNamedParent("Link_names_are_going_away_anyways?")
    )

    if (
        type_node._identifier == "ImplementsTrait"
        or type_node._identifier == "ImplementsType"
    ):
        return node

    for rule in type_node.get_children(direct_only=True, types=[_Node]):
        if isinstance(rule, Class_MakeChild.Proto_MakeChild):
            assert isinstance(rule, _Node)
            Class_MakeChild.execute(make_child_instance=rule, parent_node=node)

        elif isinstance(rule, Class_Connect.Proto_Connect):
            assert isinstance(rule, _Node)
            Class_Connect.execute(connect_instance=rule, parent_node=node)

    return node


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


# Standard Types =======================================================================


class Class_MakeChild:
    @runtime_checkable
    class Proto_MakeChild(Protocol):
        child_ref_pointer: GraphInterfaceReference

    @staticmethod
    def init_make_child_instance(node: _Node, child_ref: _Node) -> _Node:
        node.child_ref_pointer = GraphInterfaceReference()
        assert isinstance(node, Class_MakeChild.Proto_MakeChild)
        # assert isinstance(child_ref, Class_ChildReference.Proto_ChildReference)
        node.child_ref_pointer.connect(child_ref.self_gif, link=LinkPointer())
        return node

    @staticmethod
    def execute(make_child_instance: _Node, parent_node: _Node) -> None:
        assert isinstance(make_child_instance, Class_MakeChild.Proto_MakeChild)
        child_ref = make_child_instance.child_ref_pointer.get_reference()
        assert isinstance(child_ref, Class_ChildReference.Proto_ChildReference)
        identifier = child_ref._identifier

        child_type_node = child_ref.node_type_pointer.get_reference()
        assert isinstance(child_type_node, _Node)
        new_node = instantiate(child_type_node)

        compose(parent_node, new_node, name=identifier)


class Class_ChildReference:
    @runtime_checkable
    class Proto_ChildReference(Protocol):
        _identifier: str
        node_type_pointer: GraphInterfaceReference

    @staticmethod
    def init_child_reference_instance(
        type_node: _Node, node: _Node, identifier: str
    ) -> _Node:
        node._identifier = identifier
        node.node_type_pointer = GraphInterfaceReference()
        assert isinstance(node, Class_ChildReference.Proto_ChildReference)
        node.node_type_pointer.connect(type_node.self_gif, link=LinkPointer())

        return node


class Class_NestedReference:
    @runtime_checkable
    class Proto_NestedReference(Protocol):
        child_ref_pointer: GraphInterfaceReference
        next: GraphInterfaceReference

    @staticmethod
    def init_nested_reference_instance(node: _Node, child_ref: _Node, next: _Node):
        node.child_ref_pointer = GraphInterfaceReference()
        node.next = GraphInterfaceReference()
        return node


class Class_Connect:
    @runtime_checkable
    class Proto_Connect(Protocol):
        refs_gif: list[GraphInterface]

    @staticmethod
    def init_connect_node_instance(node: _Node, refs: list[_Node]):
        node.refs_gif = GraphInterface()
        assert isinstance(node, Class_Connect.Proto_Connect)
        for ref in refs:
            assert isinstance(ref, _Node)
            node.refs_gif.connect(ref.self_gif, link=LinkDirect())
        return node

    @staticmethod
    def execute(connect_instance: _Node, parent_node: _Node) -> None:
        # Recursive implementation
        def resolve_reference_node(
            parent_node: _Node,
            reference_node: _Node,
        ) -> _Node | None:
            # Get child reference of this nested reference
            if isinstance(reference_node, Class_NestedReference.Proto_NestedReference):
                child_ref = reference_node.child_ref_pointer.get_reference()
                assert isinstance(child_ref, Class_ChildReference.Proto_ChildReference)
                child_identifier = child_ref._identifier
                ref_node = get_child_by_name(parent_node, child_identifier)
                assert isinstance(ref_node, _Node)

                # If next NR, resolve it starting from the instance returned by first NR
                if len(reference_node.next.get_connected_nodes(types=[_Node])) > 0:
                    next_nested_ref = list(
                        reference_node.next.get_connected_nodes(types=[_Node])
                    )[0]
                    assert isinstance(next_nested_ref, _Node)
                    ref_node = resolve_reference_node(ref_node, next_nested_ref)
                    return ref_node

            elif isinstance(reference_node, Class_ChildReference.Proto_ChildReference):
                child_identifier = reference_node._identifier
                ref_node = get_child_by_name(parent_node, child_identifier)
                assert isinstance(ref_node, _Node)
                return ref_node

        # assert isinstance(parent_node, _Node)
        nodes_to_connect = []
        assert isinstance(connect_instance, Class_Connect.Proto_Connect)
        assert isinstance(connect_instance.refs_gif, GraphInterface)
        for ref_node in connect_instance.refs_gif.get_connected_nodes(types=[_Node]):
            assert isinstance(ref_node, _Node)
            resolved_target_node = resolve_reference_node(parent_node, ref_node)
            assert isinstance(resolved_target_node, _Node)
            nodes_to_connect.append(resolved_target_node)

        for instance in nodes_to_connect[1:]:
            assert isinstance(nodes_to_connect[0], _Node)
            assert isinstance(instance, _Node)
            nodes_to_connect[0].connections.connect(instance.connections)


def get_child_by_name(node: _Node, name: str):
    if hasattr(node, name):
        return cast(_Node, getattr(node, name))
    for p in node.get_children(direct_only=True, types=[_Node]):
        assert isinstance(p, _Node)
        if p.get_name() == name:
            return p
    raise ValueError(f"No child with name {name} found")


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


TwoTerminal = Class_ImplementsTrait.init_trait_type(_Node(), "TwoTerminal")
CanBridge = Class_CanBridge.init_can_bridge_node(_Node())
Type_MakeChild = Class_ImplementsType.init_type_node(_Node(), "MakeChild")
Type_Connect = Class_ImplementsType.init_type_node(_Node(), "Connect")


# print(Type_ImplementsTrait.get_children(direct_only=True, types=[_Node]))

# ## ELECTRICAL TYPE ##
Type_Electrical = Class_ImplementsType.init_type_node(_Node(), "Electrical")
# electrical = instantiate(Type_Electrical)

# ### RESISTOR TYPE ###
Type_Resistor = Class_ImplementsType.init_type_node(_Node(), "Resistor")

p1_ref = Class_ChildReference.init_child_reference_instance(
    Type_Electrical, _Node(), "p1"
)
p1_rule = Class_MakeChild.init_make_child_instance(instantiate(Type_MakeChild), p1_ref)
Type_Resistor.children.connect(p1_rule.parent, LinkNamedParent("p1"))

p2_ref = Class_ChildReference.init_child_reference_instance(
    Type_Electrical, _Node(), "p2"
)
p2_rule = Class_MakeChild.init_make_child_instance(instantiate(Type_MakeChild), p2_ref)
Type_Resistor.children.connect(p2_rule.parent, LinkNamedParent("p2"))

p1p2_connect_rule = Class_Connect.init_connect_node_instance(
    instantiate(Type_Connect), [p1_ref, p2_ref]
)
Type_Resistor.children.connect(p1p2_connect_rule.parent, LinkNamedParent("p1p2connect"))

resistor = instantiate(Type_Resistor)

# rules = Type_Resistor.get_children(direct_only=True, types=[_Node])
# for rule in rules:
#     if isinstance(rule, Class_MakeChild.Proto_MakeChild):
#         print(rule.get_name())


# class Connect(_Node):
#     def with_nested_references(self, refs: list[NestedReference]) -> "Connect":
#         self._refs = refs
#         return self

#     def execute(self, node: Node) -> None:
#         super().execute(node)

#         # Recursive implementation
#         def resolve_nested_reference(
#             parent_node: Node, nested_ref: NestedReference
#         ) -> Node:
#             # Get child reference of this nested reference
#             child_ref = nested_ref.child_ref_pointer.get_reference()
#             assert isinstance(child_ref, ChildRef)
#             child_identifier = child_ref._identifier
#             ref_node = parent_node.get_child_by_name(child_identifier)
#             assert isinstance(ref_node, Node)

#             # If next NR, resolve it starting from the instance returned by first NR
#             if len(nested_ref.next.get_connected_nodes(types=[NestedReference])) > 0:
#                 next_nested_ref = list(
#                     nested_ref.next.get_connected_nodes(types=[NestedReference])
#                 )[0]
#                 assert isinstance(next_nested_ref, NestedReference)
#                 ref_node = resolve_nested_reference(ref_node, next_nested_ref)

#             return ref_node

#         nodes_to_connect = []
#         for ref in self._refs:
#             resolved_target_node = resolve_nested_reference(node, ref)
#             assert isinstance(resolved_target_node, Node)
#             nodes_to_connect.append(resolved_target_node)

#         for instance in nodes_to_connect[1:]:
#             assert isinstance(nodes_to_connect[0], Node)
#             assert isinstance(instance, Node)
#             nodes_to_connect[0].connections.connect(instance.connections)


# ### References ###
# class RefNode(Node):
#     pass


# class ChildRef(RefNode):
#     node_type_pointer: GraphInterfaceReference

#     def __init__(self, identifier: str):
#         super().__init__()
#         self._identifier = identifier

#     def with_nodetype(self, child_type_ref: Proto_Type) -> "ChildRef":
#         self.node_type_pointer.connect(child_type_ref.self_gif, link=LinkPointer())
#         return self


# class NestedReference(RefNode):
#     child_ref_pointer: GraphInterfaceReference
#     prev: GraphInterface
#     next: GraphInterface

#     def with_child_reference(self, child_ref: ChildRef) -> "NestedReference":
#         self.child_ref_pointer.connect(child_ref.self_gif, link=LinkPointer())
#         return self
