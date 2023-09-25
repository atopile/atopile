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


def test_instance_nested_tuple_attribute():
    self = MagicMock()
    self.data = {"path_to": {"some_value": 1234}}
    assert ModelVertexView.get_data(self, ("path_to", "some_value")) == 1234
