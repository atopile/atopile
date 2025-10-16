from dataclasses import dataclass
from typing import Any, Self, cast, override

from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import BoundNode, GraphView
from faebryk.libs.util import cast_assert, dataclass_as_kwargs, not_none


class FaebrykApiException(Exception):
    pass


class Child[T: NodeType[Any]]:
    def __init__(self, nodetype: type[T], tg: TypeGraph) -> None:
        self.nodetype = nodetype
        self.tg = tg
        self.identifier: str = None  # type: ignore

        if nodetype.Attributes is not NodeTypeAttributes:
            raise FaebrykApiException(
                f"Can't have Child with custom Attributes: {nodetype.__name__}"
            )

    def get(self) -> T:
        raise FaebrykApiException(
            "Called on class child instead of bound instance child"
        )

    def get_unbound(self, instance: BoundNode) -> T:
        assert self.identifier is not None, "Bug: Needs to be set on setattr"

        child_instance = not_none(
            EdgeComposition.get_child_by_identifier(
                node=instance, child_identifier=self.identifier
            )
        )
        bound = self.nodetype(instance=child_instance)
        return bound

    def bind(self, node: BoundNode):
        return BoundChild(child=self, instance=node)


class BoundChild[T: NodeType](Child[T]):
    def __init__(self, child: Child, instance: BoundNode) -> None:
        self.nodetype = child.nodetype
        self.node = child.nodetype
        self.identifier = child.identifier
        self.tg = child.tg
        self._instance = instance

    def get(self) -> T:
        return self.get_unbound(instance=self._instance)


class NodeTypeMeta(type):
    @override
    def __setattr__(cls, name: str, value: Any, /) -> None:
        if isinstance(value, Child) and issubclass(cls, NodeType):
            value.identifier = name
            cls.add_child(name, value.nodetype, tg=value.tg)
        return super().__setattr__(name, value)


@dataclass(frozen=True)
class NodeTypeAttributes:
    def __init_subclass__(cls) -> None:
        # TODO collect all fields (like dataclasses)
        # TODO check Attributes is dataclass and frozen
        pass

    @classmethod
    def of(cls: type[Self], node: "BoundNode | NodeType[Any]") -> Self:
        if isinstance(node, NodeType):
            node = node.instance
        return cls(**node.node().get_dynamic_attrs())

    def to_dict(self) -> dict[str, Any]:
        return dataclass_as_kwargs(self)


class NodeType[T: NodeTypeAttributes = NodeTypeAttributes](metaclass=NodeTypeMeta):
    Attributes = NodeTypeAttributes

    def __init__(self, instance: BoundNode) -> None:
        self.instance = instance
        for name, child in vars(type(self)).items():
            if not isinstance(child, Child):
                continue
            setattr(self, name, child.bind(instance))

    def __init_subclass__(cls) -> None:
        # Ensure single-level inheritance: NodeType subclasses should not themselves
        # be subclassed further.
        if len(cls.__mro__) > len(NodeType.__mro__) + 1:
            # mro(): [Leaf, NodeType, object] is allowed (len==3),
            # deeper (len>3) is forbidden
            raise FaebrykApiException(
                f"NodeType subclasses cannot themselves be subclassed "
                f"more than one level deep (found: {cls.__mro__})"
            )
        super().__init_subclass__()

    @classmethod
    def _type_identifier(cls) -> str:
        return cls.__name__

    @classmethod
    def get_or_create_type(cls, tg: TypeGraph) -> BoundNode:
        """
        Builds Type node and returns it
        """
        typenode = tg.get_type_by_name(type_identifier=cls._type_identifier())
        if typenode is not None:
            return typenode
        typenode = tg.add_type(identifier=cls._type_identifier())
        cls.create_type(tg=tg)
        return typenode

    @classmethod
    def add_child(
        cls,
        identifier: str,
        child: "BoundNode | type[NodeType]",
        *,
        tg: TypeGraph,
    ) -> BoundNode:
        child_type_node = (
            cast(type[NodeType], child).get_or_create_type(tg=tg)
            if issubclass(type(child), type) and issubclass(cast(type, child), NodeType)
            else cast_assert(BoundNode, child)
        )
        return tg.add_make_child(
            type_node=cls.get_or_create_type(tg=tg),
            child_type_node=child_type_node,
            identifier=identifier,
        )

    @classmethod
    def create_instance(
        cls, tg: TypeGraph, g: GraphView, attributes: T | None = None
    ) -> Self:
        """
        Create a node instance for the given type node
        """
        # TODO if attributes is not empty enforce not None
        typenode = cls.get_or_create_type(tg=tg)
        attrs = attributes.to_dict() if attributes else {}
        instance = tg.instantiate_node(type_node=typenode, attributes=attrs)
        return cls(instance=instance)

    def attributes(self) -> T:
        Attributes = cast(type[T], type(self).Attributes)
        return Attributes.of(self.instance)

    # OVERRIDES ------------------------------------------------------------------------
    @classmethod
    def create_type(cls, tg: TypeGraph) -> None:
        """
        Override this to add children to the type.
        """
        pass


# ------------------------------------------------------------


def test_fabll_basic():
    @dataclass(frozen=True)
    class FileLocationAttributes(NodeTypeAttributes):
        start_line: int
        start_column: int
        end_line: int
        end_column: int

    class FileLocation(NodeType[FileLocationAttributes]):
        Attributes = FileLocationAttributes

    @dataclass(frozen=True)
    class SliceAttributes(NodeTypeAttributes):
        start: int
        end: int
        step: int

    class Slice(NodeType[SliceAttributes]):
        Attributes = SliceAttributes

        @classmethod
        def create_type(cls, tg: TypeGraph) -> None:
            cls.tnwa = Child(TestNodeWithoutAttr, tg=tg)

    class TestNodeWithoutAttr(NodeType):
        pass

    class TestNodeWithChildren(NodeType):
        @classmethod
        def create_type(cls, tg: TypeGraph) -> None:
            cls.tnwa = Child(TestNodeWithoutAttr, tg=tg)

    g = GraphView.create()
    tg = TypeGraph.create(g=g)
    fileloc = FileLocation.create_instance(
        tg=tg,
        g=g,
        attributes=FileLocationAttributes(
            start_line=1,
            start_column=1,
            end_line=1,
            end_column=1,
        ),
    )

    print("fileloc.start_column:", fileloc.attributes().start_column)
    print("fileloc:", fileloc.attributes())

    tnwa = TestNodeWithoutAttr.create_instance(tg=tg, g=g)
    print("tnwa:", tnwa.instance.node().get_dynamic_attrs())

    slice = Slice.create_instance(
        tg=tg, g=g, attributes=SliceAttributes(start=1, end=1, step=1)
    )
    print("Slice:", slice.attributes())
    print("Slice.tnwa:", slice.tnwa.get().attributes())
