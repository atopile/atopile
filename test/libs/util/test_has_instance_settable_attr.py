from faebryk.libs.util import has_instance_settable_attr, write_only_property


class SomeClass:
    def __init__(self):
        self.regular_attr = "initial"
        self._rw_value = "initial"

    @property
    def read_only_prop(self):
        return "read_only"

    @write_only_property
    def write_only_prop(self, value):
        self._wo_value = value

    @property
    def read_write_prop(self):
        return self._rw_value

    @read_write_prop.setter
    def read_write_prop(self, value):
        self._rw_value = value


def test_set_regular_attribute():
    """Test setting a regular attribute"""
    obj = SomeClass()
    assert has_instance_settable_attr(obj, "regular_attr")


def test_set_new_attribute():
    """Test setting a new attribute (should fail)"""
    obj = SomeClass()
    assert not has_instance_settable_attr(obj, "new_attr")


def test_set_read_only_property():
    """Test setting a read-only property (should fail)"""
    obj = SomeClass()
    assert not has_instance_settable_attr(obj, "read_only_prop")


def test_set_read_write_property():
    """Test setting a read-write property"""
    obj = SomeClass()
    assert has_instance_settable_attr(obj, "read_write_prop")


def test_set_nonexistent_attribute():
    """Test setting a nonexistent attribute"""
    obj = SomeClass()
    assert not has_instance_settable_attr(obj, "nonexistent_attr")


def test_set_class_level_attribute():
    """Test setting a class-level attribute"""

    class ClassWithClassAttr:
        class_attr = "initial"

    obj = ClassWithClassAttr()
    assert not has_instance_settable_attr(obj, "class_attr")


def test_set_inherited_property():
    """Test setting an inherited property"""

    class ChildClass(SomeClass):
        pass

    obj = ChildClass()
    assert has_instance_settable_attr(obj, "read_write_prop")


def test_set_none_object():
    """Test setting attribute on None (should fail)"""
    assert not has_instance_settable_attr(None, "attr")


def test_set_primitive_types():
    """Test setting attributes on primitive types (should fail)"""
    assert not has_instance_settable_attr(42, "attr")
    assert not has_instance_settable_attr("string", "attr")


def test_set_with_property_no_setter():
    """Test setting a property that has no setter"""

    class NoSetterClass:
        @property
        def prop(self):
            return "value"

    obj = NoSetterClass()
    assert not has_instance_settable_attr(obj, "prop")


def test_write_only_property():
    """Test setting a write-only property"""
    obj = SomeClass()
    assert has_instance_settable_attr(obj, "write_only_prop")
