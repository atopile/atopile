import pytest

from atopile.model.accessors import ModelVertexView
from atopile.model.differ import Delta, Empty
from atopile.model.model import Model, VertexType, EdgeType


@pytest.fixture
def module1_root(dummy_model: Model):
    return ModelVertexView.from_path(dummy_model, "dummy_file.ato:dummy_module")


@pytest.fixture
def dummy2(dummy_maker):
    return dummy_maker()


@pytest.fixture
def module2_root(dummy2: Model):
    return ModelVertexView.from_path(dummy2, "dummy_file.ato:dummy_module")


def test_zero_delta(module1_root, module2_root):
    delta = Delta.diff(module1_root, module2_root)
    assert not delta.node
    assert not delta.connection
    assert not delta.data


def add_nodes(module2_root: ModelVertexView):
    module2_root.model.new_vertex(
        VertexType.module, "new_module", "dummy_file.ato:dummy_module"
    )
    module2_root.model.new_vertex(
        VertexType.component, "new_component", "dummy_file.ato:dummy_module.new_module"
    )


def test_added_node2(module1_root: ModelVertexView, module2_root: ModelVertexView):
    add_nodes(module2_root)
    delta = Delta.diff(module1_root, module2_root)
    assert delta.node == {
        ("new_module",): VertexType.module,
        ("new_module", "new_component"): VertexType.component,
    }
    assert not delta.connection
    assert not delta.data


def test_remove_node2(module1_root: ModelVertexView, module2_root: ModelVertexView):
    add_nodes(module1_root)
    delta = Delta.diff(module1_root, module2_root)
    assert delta.node == {
        ("new_module",): Empty,
        ("new_module", "new_component"): Empty,
    }
    assert not delta.connection
    assert not delta.data


def add_connection(module2_root: ModelVertexView):
    module2_root.model.new_edge(
        EdgeType.connects_to,
        "dummy_file.ato:dummy_module.dummy_comp0.sig0",
        "dummy_file.ato:dummy_module.dummy_comp1.sig0",
    )


def test_added_connection(module1_root: ModelVertexView, module2_root: ModelVertexView):
    add_connection(module2_root)
    delta = Delta.diff(module1_root, module2_root)
    assert not delta.node
    assert delta.connection == {
        (("dummy_comp0", "sig0"), ("dummy_comp1", "sig0")): True
    }
    assert not delta.data


def test_remove_connection(module1_root: ModelVertexView, module2_root: ModelVertexView):
    add_connection(module1_root)
    delta = Delta.diff(module1_root, module2_root)
    assert not delta.node
    assert delta.connection == {
        (("dummy_comp0", "sig0"), ("dummy_comp1", "sig0")): Empty
    }
    assert not delta.data


def add_data(module2_root: ModelVertexView):
    module2_root.data["test"] = {"test2": "hello-world"}
    assert module2_root.data["test"]["test2"] == "hello-world"


def test_added_data(module1_root: ModelVertexView, module2_root: ModelVertexView):
    add_data(module2_root)
    delta = Delta.diff(module1_root, module2_root)
    assert not delta.node
    assert not delta.connection
    assert delta.data == {("test", "test2"): "hello-world"}


def test_modify_data(module1_root: ModelVertexView, module2_root: ModelVertexView):
    add_data(module1_root)
    add_data(module2_root)
    module2_root.data["test"]["test2"] = "new-world"
    delta = Delta.diff(module1_root, module2_root)
    assert not delta.node
    assert not delta.connection
    assert delta.data == {("test", "test2"): "new-world"}


def test_remove_data(module1_root: ModelVertexView, module2_root: ModelVertexView):
    add_data(module1_root)
    delta = Delta.diff(module1_root, module2_root)
    assert not delta.node
    assert not delta.connection
    assert delta.data == {("test", "test2"): Empty}
