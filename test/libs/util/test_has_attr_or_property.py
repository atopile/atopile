from faebryk.libs.util import has_attr_or_property


class SomeClass:
    def __init__(self):
        self.regular_attr = "value"

    @property
    def read_only_prop(self):
        return "read_only"

    @property
    def read_write_prop(self):
        return self._rw_value

    @read_write_prop.setter
    def read_write_prop(self, value):
        self._rw_value = value


def test_regular_attribute():
    """Test detection of regular attributes"""
    obj = SomeClass()
    assert has_attr_or_property(obj, "regular_attr")
    assert not has_attr_or_property(obj, "nonexistent_attr")


def test_property_detection():
    """Test detection of properties"""
    obj = SomeClass()
    assert has_attr_or_property(obj, "read_only_prop")
    assert has_attr_or_property(obj, "read_write_prop")


def test_dynamic_attribute():
    """Test detection of dynamically added attributes"""
    obj = SomeClass()
    obj.dynamic_attr = "dynamic"
    assert has_attr_or_property(obj, "dynamic_attr")


def test_class_level_attribute():
    """Test detection of class-level attributes"""
    SomeClass.class_attr = "class_value"
    obj = SomeClass()
    assert has_attr_or_property(obj, "class_attr")


def test_inherited_property():
    """Test detection of inherited properties"""

    class ChildClass(SomeClass):
        pass

    obj = ChildClass()
    assert has_attr_or_property(obj, "read_only_prop")
    assert has_attr_or_property(obj, "read_write_prop")


def test_builtin_attributes():
    """Test behavior with built-in attributes"""
    obj = SomeClass()
    assert has_attr_or_property(obj, "__class__")
    assert has_attr_or_property(obj, "__dict__")


def test_none_object():
    """Test behavior with None object"""
    assert not has_attr_or_property(None, "any_attr")


def test_primitive_types():
    """Test behavior with primitive types"""
    assert not has_attr_or_property(42, "custom_attr")
    assert not has_attr_or_property("string", "custom_attr")
    assert has_attr_or_property("string", "upper")  # built-in method
