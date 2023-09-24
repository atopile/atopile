from unittest.mock import MagicMock
from atopile.model.accessors import ModelVertexView

def test_instance_str_attribute():
    self = MagicMock()
    self.data = {"some_value": 1234}
    assert ModelVertexView.get_data(self, "some_value") == 1234

def test_superclass_str_attribute():
    self = MagicMock()

    superclass = MagicMock()
    self.superclasses = [superclass]

    self.data = {}
    superclass.data = {"some_value": 1234}

    assert ModelVertexView.get_data(self, "some_value") == 1234

def test_instance_tuple_attribute():
    self = MagicMock()
    self.data = {"some_value": 1234}
    assert ModelVertexView.get_data(self, ("some_value",)) == 1234

def test_superclass_tuple_attribute():
    self = MagicMock()

    superclass = MagicMock()
    self.superclasses = [superclass]

    self.data = {}
    superclass.data = {"some_value": 1234}

    assert ModelVertexView.get_data(self, ("some_value",)) == 1234

def test_instance_nested_tuple_attribute():
    self = MagicMock()
    self.data = {"path_to": {"some_value": 1234}}
    assert ModelVertexView.get_data(self, ("path_to", "some_value")) == 1234

def test_superclass_nested_tuple_attribute():
    self = MagicMock()

    superclass = MagicMock()
    self.superclasses = [superclass]

    self.data = {}
    superclass.data = {"path_to": {"some_value": 1234}}

    assert ModelVertexView.get_data(self, ("path_to", "some_value")) == 1234
