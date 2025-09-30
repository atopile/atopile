from typing import Protocol, runtime_checkable

from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.graph.graph import GraphView, Node, BoundNode, BoundEdge
from faebryk.libs.util import cast

node = ZNode.create(example1="value1", example2="value2")
duplicate_node = node
test_node = ZNode.create(example1="value1", example2="value2")
print(node.get_attr(key="example1"))
print(node.is_same(other=duplicate_node))
print(node.is_same(other=test_node))


# Build Trait
# Build implement_type
# Instantiate implement_type and assign to Trait
# Rest easy

# No python type checking, use protocol checking instead
# Everything should inherit directly from ZNode
# Traits are not special, they are just marked by a "implements_trait" node
# Types are slightly special because they have rules for constructing children
# Types are marked by an "implements_type" node

typegraph_view = GraphView.create()


def compose(g: GraphView, parent: BoundNode, child: BoundNode, child_identifier: str):
    assert isinstance(parent, BoundNode)
    assert isinstance(child, BoundNode)
    assert parent.g() == child.g()
    edge = EdgeComposition.create(
        parent=parent.node(), child=child.node(), child_identifier=child_identifier
    )
    bound_edge = g.insert_edge(edge=edge)
    return bound_edge


# def instantiate(type_node: ZNode, name: str = ""):
#     node = ZNode()
#     added_objects: dict[str, ZNode | GraphInterface] = {name: node}
#     node.is_type = GraphInterfaceHierarchical(is_parent=False)
#     assert isinstance(node, ZNode.ProtoZNode)
#     assert isinstance(type_node, Class_ImplementsType.Proto_Type)
#     node.is_type.connect(type_node.instances, LinkNamedParent(name))

#     if (
#         type_node._identifier == "ImplementsTrait"
#         or type_node._identifier == "ImplementsType"
#     ):
#         return node, added_objects

#     for rule in type_node.get_children(direct_only=True, types=[ZNode]):
#         if isinstance(rule, Class_MakeChild.Proto_MakeChild):
#             assert isinstance(rule, ZNode)
#             added_children = Class_MakeChild.execute(
#                 make_child_instance=rule, parent_node=node
#             )
#             added_objects.update(added_children)

#     # for rule in type_node.get_children(direct_only=True, types=[ZNode]):
#     #     if isinstance(rule, Class_Connect.Proto_Connect):
#     #         assert isinstance(rule, ZNode)
#     #         Class_Connect.execute(connect_instance=rule, parent_node=node)

#     return node, added_objects


# Base Traits --------------------------------------------------------------------------
class Class_ImplementsType:
    @runtime_checkable
    class Proto_Type(Protocol):
        _identifier: str

    @staticmethod
    def init_type_node(g: GraphView, identifier_input: str):
        type_node = Node.create(identifier=identifier_input)
        if identifier_input == "ImplementsType":
            return type_node
        compose(
            typegraph_view,
            type_node,
            instantiate(Type_ImplementsType)[0],
            "ImplementsType",
        )
        return type_node


# Type_ImplementsType = Class_ImplementsType.init_type_node(ZNode(), "ImplementsType")
# # need to manually set it now that it's bootstrapped
# compose(Type_ImplementsType, instantiate(Type_ImplementsType)[0], "ImplementsType")


# class Class_ImplementsTrait:
#     @staticmethod
#     def init_trait_type(trait_node: ZNode, identifier: str):
#         Class_ImplementsType.init_type_node(trait_node, identifier)
#         # bootstrap
#         if identifier == "ImplementsTrait":
#             return trait_node
#         compose(trait_node, instantiate(Type_ImplementsTrait)[0], "ImplementsTrait")
#         return trait_node


# Type_ImplementsTrait = Class_ImplementsTrait.init_trait_type(ZNode(), "ImplementsTrait")
# # now that we have trait, init our base traits with it
# compose(Type_ImplementsTrait, instantiate(Type_ImplementsTrait)[0], "ImplementsTrait")
# compose(Type_ImplementsType, instantiate(Type_ImplementsTrait)[0], "ImplementsTrait")


# # Standard Types =======================================================================


# class Class_MakeChild:
#     @runtime_checkable
#     class Proto_MakeChild(Protocol):
#         child_ref_pointer: GraphInterfaceReference

#     @staticmethod
#     def init_make_child_instance(node: ZNode, child_ref: ZNode) -> ZNode:
#         node.child_ref_pointer = GraphInterfaceReference()
#         assert isinstance(node, Class_MakeChild.Proto_MakeChild)
#         # assert isinstance(child_ref, Class_ChildReference.Proto_ChildReference)
#         node.child_ref_pointer.connect(child_ref.self_gif, link=LinkPointer())
#         return node

#     @staticmethod
#     def execute(
#         make_child_instance: ZNode,
#         parent_node: ZNode,
#     ):
#         assert isinstance(make_child_instance, Class_MakeChild.Proto_MakeChild)
#         child_ref = make_child_instance.child_ref_pointer.get_reference()
#         assert isinstance(child_ref, Class_ChildReference.Proto_ChildReference)
#         identifier = child_ref._identifier

#         child_type_node = child_ref.node_type_pointer.get_reference()
#         assert isinstance(child_type_node, ZNode)
#         new_node, added_objects = instantiate(child_type_node, name=identifier)

#         compose(parent_node, new_node, name=identifier)

#         return added_objects


# class Class_ChildReference:
#     @runtime_checkable
#     class Proto_ChildReference(Protocol):
#         _identifier: str
#         node_type_pointer: GraphInterfaceReference

#     @staticmethod
#     def init_child_reference_instance(
#         type_node: ZNode, node: ZNode, identifier: str
#     ) -> ZNode:
#         node._identifier = identifier
#         node.node_type_pointer = GraphInterfaceReference()
#         assert isinstance(node, Class_ChildReference.Proto_ChildReference)
#         node.node_type_pointer.connect(type_node.self_gif, link=LinkPointer())

#         return node


# class Class_NestedReference:
#     @runtime_checkable
#     class Proto_NestedReference(Protocol):
#         child_ref_pointer: GraphInterfaceReference
#         next: GraphInterface

#     @staticmethod
#     def init_nested_reference_instance(
#         node: ZNode, child_ref: ZNode, next: ZNode | None
#     ):
#         node.child_ref_pointer = GraphInterfaceReference()
#         node.next = GraphInterface()
#         assert isinstance(node, Class_NestedReference.Proto_NestedReference)
#         node.child_ref_pointer.connect(child_ref.self_gif, link=LinkPointer())
#         if next is not None:
#             node.next.connect(next.self_gif, link=LinkDirect())
#         return node


# class Class_Connect:
#     @runtime_checkable
#     class Proto_Connect(Protocol):
#         refs_gif: list[GraphInterface]

#     @staticmethod
#     def init_connect_node_instance(node: ZNode, refs: list[ZNode]):
#         node.refs_gif = GraphInterface()
#         assert isinstance(node, Class_Connect.Proto_Connect)
#         for ref in refs:
#             assert isinstance(ref, ZNode)
#             node.refs_gif.connect(ref.self_gif, link=LinkDirect())
#         return node

#     @staticmethod
#     def execute(connect_instance: ZNode, parent_node: ZNode) -> None:
#         # Recursive implementation
#         def resolve_reference_node(
#             parent_node: ZNode,
#             reference_node: ZNode,
#         ) -> ZNode | None:
#             # Get child reference of this nested reference
#             if isinstance(reference_node, Class_NestedReference.Proto_NestedReference):
#                 child_ref = reference_node.child_ref_pointer.get_reference()
#                 assert isinstance(child_ref, Class_ChildReference.Proto_ChildReference)
#                 child_identifier = child_ref._identifier
#                 ref_node = get_child_by_name(parent_node, child_identifier)
#                 assert isinstance(ref_node, ZNode)

#                 # If next NR, resolve it starting from the instance returned by first NR
#                 if len(reference_node.next.get_connected_nodes(types=[ZNode])) > 0:
#                     next_nested_ref = list(
#                         reference_node.next.get_connected_nodes(types=[ZNode])
#                     )[0]
#                     assert isinstance(next_nested_ref, ZNode)
#                     ref_node = resolve_reference_node(ref_node, next_nested_ref)

#                 return ref_node

#             elif isinstance(reference_node, Class_ChildReference.Proto_ChildReference):
#                 child_identifier = reference_node._identifier
#                 ref_node = get_child_by_name(parent_node, child_identifier)
#                 assert isinstance(ref_node, ZNode)
#                 return ref_node

#         # assert isinstance(parent_node, ZNode)
#         nodes_to_connect = []
#         assert isinstance(connect_instance, Class_Connect.Proto_Connect)
#         assert isinstance(connect_instance.refs_gif, GraphInterface)
#         for ref_node in connect_instance.refs_gif.get_connected_nodes(types=[ZNode]):
#             assert isinstance(ref_node, ZNode)
#             resolved_target_node = resolve_reference_node(parent_node, ref_node)
#             assert isinstance(resolved_target_node, ZNode)
#             nodes_to_connect.append(resolved_target_node)

#         for instance in nodes_to_connect[1:]:
#             assert isinstance(nodes_to_connect[0], ZNode)
#             assert isinstance(instance, ZNode)
#             nodes_to_connect[0].connections.connect(
#                 instance.connections, link=LinkDirect()
#             )


# class Class_CanBridge:
#     @runtime_checkable
#     class Proto_CanBridge(Protocol):
#         in_: GraphInterfaceReference
#         out: GraphInterfaceReference

#     @staticmethod
#     def init_can_bridge_node(node: ZNode):
#         Class_ImplementsTrait.init_trait_type(node, "CanBridge")

#         node.in_ = GraphInterfaceReference()
#         node.out = GraphInterfaceReference()

#     @staticmethod
#     def get_in(node: ZNode):
#         assert isinstance(node, Class_CanBridge.Proto_CanBridge)
#         return node.in_.get_referenced_gif().node

#     @staticmethod
#     def get_out(node: ZNode):
#         assert isinstance(node, Class_CanBridge.Proto_CanBridge)
#         return node.out.get_referenced_gif().node


# ### UTILITY FUNCTIONS ###
# def get_child_by_name(node: ZNode, name: str):
#     if hasattr(node, name):
#         return cast(ZNode, getattr(node, name))
#     for p in node.get_children(direct_only=True, types=[ZNode]):
#         assert isinstance(p, ZNode)
#         if p.get_name() == name:
#             return p
#     raise ValueError(f"No child with name {name} found")


# def get_type_by_name(name: str) -> ZNode | None:
#     assert isinstance(Type_ImplementsType, Class_ImplementsType.Proto_Type)
#     implements_type_instances_gif = Type_ImplementsType.instances
#     for instance in implements_type_instances_gif.get_children():
#         assert isinstance(instance, ZNode)
#         if parent_tuple := instance.get_parent():
#             parent_node = parent_tuple[0]
#             assert isinstance(parent_node, ZNode)
#             if not isinstance(parent_node, Class_ImplementsType.Proto_Type):
#                 continue
#             if getattr(parent_node, "_identifier", None) == name:
#                 return parent_node
#     return None


# def make_child_rule_and_child_ref(
#     child_type_node: ZNode, name: str, parent_node: ZNode
# ):
#     assert isinstance(child_type_node, Class_ImplementsType.Proto_Type)
#     child_ref = Class_ChildReference.init_child_reference_instance(
#         child_type_node, instantiate(Type_ChildReference)[0], name
#     )
#     make_child = Class_MakeChild.init_make_child_instance(
#         instantiate(Type_MakeChild, name)[0], child_ref
#     )
#     parent_node.children.connect(make_child.parent, LinkNamedParent(name))


# # BUILT IN TYPES FOR TYPEGRAPH GENERATION
# Type_MakeChild = Class_ImplementsType.init_type_node(ZNode(), "MakeChild")
# Type_ChildReference = Class_ImplementsType.init_type_node(ZNode(), "ChildReference")
# Type_NestedReference = Class_ImplementsType.init_type_node(ZNode(), "NestedReference")
# Type_ModuleInterface = Class_ImplementsType.init_type_node(ZNode(), "ModuleInterface")
# Type_Parameter = Class_ImplementsType.init_type_node(ZNode(), "Parameter")
