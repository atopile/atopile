from unittest.mock import MagicMock

import pytest
from atopile.model.accessors import ModelVertexView


@pytest.mark.parametrize(
    ("path"),
    [
        "some_value",
        ("some_value",),
    ],
)
def test_instance_attribute(path):
    self = MagicMock()
    self.data = {"some_value": 1234}
    assert ModelVertexView.get_data(self, path) == 1234


@pytest.mark.parametrize(
    ("path"),
    [
        "some_value",
        ("some_value",),
    ]
)
def test_instance_of_attribute(path):
    self = MagicMock()
    self.data = {}
    self.is_instance = True
    self.instance_of = MagicMock()
    self.instance_of.data = {"some_value": 1234}

    assert ModelVertexView.get_data(self, path) == 1234

@pytest.mark.parametrize(
    ("path"),
    [
        "some_value",
        ("some_value",),
    ]
)
def test_superclass_attribute(path):
    self = MagicMock()
    self.data = {}
    self.is_instance = True
    self.instance_of = MagicMock()
    self.instance_of.data = {}
    self.instance_of.superclasses = [MagicMock()]
    self.instance_of.superclasses[0].data = {"some_value": 1234}

    assert ModelVertexView.get_data(self, path) == 1234

def test_return_all_superclass_attribute():
    self = MagicMock()
    self.data = {"some_value": 1234}
    self.is_instance = True
    self.instance_of = MagicMock()
    self.instance_of.data = {}
    self.instance_of.superclasses = [MagicMock()]
    self.instance_of.superclasses[0].data = {"some_value": 2345, "some_other_value": 3456}

    assert ModelVertexView.get_all_data(self) == {"some_value": 1234, "some_other_value": 3456}


def test_instance_nested_tuple_attribute():
    self = MagicMock()
    self.data = {"path_to": {"some_value": 1234}}
    assert ModelVertexView.get_data(self, ("path_to", "some_value")) == 1234


def test_default_return():
    self = MagicMock()
    self.data = {}
    self.is_instance = True
    self.instance_of = MagicMock()
    self.instance_of.data = {}
    self.instance_of.superclasses = []
    assert ModelVertexView.get_data(self, "some_value", failure=1234) == 1234


def test_exception_class():
    self = MagicMock()
    self.data = {}
    self.is_instance = True
    self.instance_of = MagicMock()
    self.instance_of.data = {}
    self.instance_of.superclasses = []
    with pytest.raises(KeyError):
        assert ModelVertexView.get_data(self, "some_value", failure=KeyError)


def test_exception_instance():
    self = MagicMock()
    self.data = {}
    self.is_instance = True
    self.instance_of = MagicMock()
    self.instance_of.data = {}
    self.instance_of.superclasses = []
    with pytest.raises(KeyError, match="exceptiony exception"):
        assert ModelVertexView.get_data(self, "some_value", failure=KeyError("exceptiony exception"))
