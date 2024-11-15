import pytest

from faebryk.core.node import FieldError, Node
from faebryk.core.reference import Reference


def test_points_to_correct_node():
    class A(Node):
        pass

    class B(Node):
        x = Reference(A)

    a = A()
    b = B()
    b.x = a
    assert b.x is a


def test_immutable():
    class A(Node):
        pass

    class B(Node):
        x = Reference(A)

    b = B()
    a = A()
    b.x = a

    with pytest.raises(TypeError):
        b.x = A()


def test_unset():
    class A(Node):
        pass

    class B(Node):
        x = Reference(A)

    b = B()
    with pytest.raises(Reference.UnboundError):
        b.x


def test_wrong_type():
    class A(Node):
        pass

    class B(Node):
        x = Reference(A)

    b = B()
    with pytest.raises(TypeError):
        b.x = 1


def test_set_value_before_constuction():
    class A(Node):
        pass

    class B(Node):
        x = Reference(A)

        def __init__(self, x):
            super().__init__()
            self.x = x

    a = A()
    b = B(a)
    assert b.x is a


def test_get_value_before_constuction():
    class A(Node):
        pass

    class B(Node):
        x = Reference(A)
        y = Reference(A)

        def __init__(self, x):
            super().__init__()
            self.x = x
            self.y = self.x

    a = A()
    b = B(a)
    assert b.y is a


def test_typed_construction_doesnt_work():
    class B(Node):
        x: Reference

    # check using the property directly that everything is working
    with pytest.raises(AttributeError):
        B.x


def test_typed_construction_protection():
    """
    Ensure references aren't constructed as a field

    If properties are constructed as instance fields, their
    getters and setters aren't called when assigning to them.

    This means we won't actually construct the underlying graph properly.
    It's pretty insidious because it's completely non-obvious that we're
    missing these graph connections.
    """

    class A(Node):
        pass

    class B(Node):
        x: Reference[A]

    with pytest.raises(FieldError):
        B()


def test_underlying_property_explicitly():
    class A(Node):
        pass

    class B(Node):
        x = Reference(A)

    a = A()
    b = B()
    b.x = a

    # check using the property directly that everything is working
    assert B.x.gifs[b].get_reference() is a

    # check that the property is set
    assert b.x is a
