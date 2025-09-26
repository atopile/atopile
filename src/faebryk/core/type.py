from typing import Any, Callable, Protocol, runtime_checkable

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
from faebryk.core.cpp import Node as CNode
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
        # if isinstance(value, Node):
        #     value._handle_added_to_parent()


def compose(parent: _Node, child: _Node, name: str):
    link = LinkParent() if not name else LinkNamedParent(name)
    child.parent.connect(parent.children, link)
    # if name:
    #     setattr(parent, "child_node", child)
    return parent


def instantiate(type_node: _Node, name: str = ""):
    node = _Node()
    added_objects: dict[str, _Node | GraphInterface] = {name: node}
    node.is_type = GraphInterfaceHierarchical(is_parent=False)
    assert isinstance(node, _Node.Proto_Node)
    assert isinstance(type_node, Class_ImplementsType.Proto_Type)
    node.is_type.connect(type_node.instances, LinkNamedParent(name))

    if (
        type_node._identifier == "ImplementsTrait"
        or type_node._identifier == "ImplementsType"
    ):
        return node, added_objects

    for rule in type_node.get_children(direct_only=True, types=[_Node]):
        if isinstance(rule, Class_MakeChild.Proto_MakeChild):
            assert isinstance(rule, _Node)
            added_children = Class_MakeChild.execute(
                make_child_instance=rule, parent_node=node
            )
            added_objects.update(added_children)

    # for rule in type_node.get_children(direct_only=True, types=[_Node]):
    #     if isinstance(rule, Class_Connect.Proto_Connect):
    #         assert isinstance(rule, _Node)
    #         Class_Connect.execute(connect_instance=rule, parent_node=node)

    return node, added_objects


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
        compose(type_node, instantiate(Type_ImplementsType)[0], "ImplementsType")
        return type_node


Type_ImplementsType = Class_ImplementsType.init_type_node(_Node(), "ImplementsType")
# need to manually set it now that it's bootstrapped
compose(Type_ImplementsType, instantiate(Type_ImplementsType)[0], "ImplementsType")


class Class_ImplementsTrait:
    @staticmethod
    def init_trait_type(trait_node: _Node, identifier: str):
        Class_ImplementsType.init_type_node(trait_node, identifier)
        # bootstrap
        if identifier == "ImplementsTrait":
            return trait_node
        compose(trait_node, instantiate(Type_ImplementsTrait)[0], "ImplementsTrait")
        return trait_node


Type_ImplementsTrait = Class_ImplementsTrait.init_trait_type(_Node(), "ImplementsTrait")
# now that we have trait, init our base traits with it
compose(Type_ImplementsTrait, instantiate(Type_ImplementsTrait)[0], "ImplementsTrait")
compose(Type_ImplementsType, instantiate(Type_ImplementsTrait)[0], "ImplementsTrait")


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
    def execute(
        make_child_instance: _Node,
        parent_node: _Node,
    ):
        assert isinstance(make_child_instance, Class_MakeChild.Proto_MakeChild)
        child_ref = make_child_instance.child_ref_pointer.get_reference()
        assert isinstance(child_ref, Class_ChildReference.Proto_ChildReference)
        identifier = child_ref._identifier

        child_type_node = child_ref.node_type_pointer.get_reference()
        assert isinstance(child_type_node, _Node)
        new_node, added_objects = instantiate(child_type_node, name=identifier)

        compose(parent_node, new_node, name=identifier)

        return added_objects


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
        next: GraphInterface

    @staticmethod
    def init_nested_reference_instance(
        node: _Node, child_ref: _Node, next: _Node | None
    ):
        node.child_ref_pointer = GraphInterfaceReference()
        node.next = GraphInterface()
        assert isinstance(node, Class_NestedReference.Proto_NestedReference)
        node.child_ref_pointer.connect(child_ref.self_gif, link=LinkPointer())
        if next is not None:
            node.next.connect(next.self_gif, link=LinkDirect())
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
            nodes_to_connect[0].connections.connect(
                instance.connections, link=LinkDirect()
            )


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


### UTILITY FUNCTIONS ###
def get_child_by_name(node: _Node, name: str):
    if hasattr(node, name):
        return cast(_Node, getattr(node, name))
    for p in node.get_children(direct_only=True, types=[_Node]):
        assert isinstance(p, _Node)
        if p.get_name() == name:
            return p
    raise ValueError(f"No child with name {name} found")


def get_type_by_name(name: str) -> _Node | None:
    assert isinstance(Type_ImplementsType, Class_ImplementsType.Proto_Type)
    implements_type_instances_gif = Type_ImplementsType.instances
    for instance in implements_type_instances_gif.get_children():
        assert isinstance(instance, _Node)
        if parent_tuple := instance.get_parent():
            parent_node = parent_tuple[0]
            assert isinstance(parent_node, _Node)
            if not isinstance(parent_node, Class_ImplementsType.Proto_Type):
                continue
            if getattr(parent_node, "_identifier", None) == name:
                return parent_node
    return None


def make_child_rule_and_child_ref(
    child_type_node: _Node, name: str, parent_node: _Node
):
    assert isinstance(child_type_node, Class_ImplementsType.Proto_Type)
    child_ref = Class_ChildReference.init_child_reference_instance(
        child_type_node, instantiate(child_type_node)[0], name
    )
    make_child = Class_MakeChild.init_make_child_instance(
        instantiate(Type_MakeChild, name)[0], child_ref
    )
    parent_node.children.connect(make_child.parent, LinkNamedParent(name))


# BUILT IN TYPES FOR TYPEGRAPH GENERATION
# TwoTerminal = Class_ImplementsTrait.init_trait_type(_Node(), "TwoTerminal")
# CanBridge = Class_CanBridge.init_can_bridge_node(_Node())
Type_MakeChild = Class_ImplementsType.init_type_node(_Node(), "MakeChild")
Type_ChildReference = Class_ImplementsType.init_type_node(_Node(), "ChildReference")
Type_NestedReference = Class_ImplementsType.init_type_node(_Node(), "NestedReference")
Type_ModuleInterface = Class_ImplementsType.init_type_node(_Node(), "ModuleInterface")
Type_Parameter = Class_ImplementsType.init_type_node(_Node(), "Parameter")
# Type_Connect = Class_ImplementsType.init_type_node(_Node(), "Connect")
