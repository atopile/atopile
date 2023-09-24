import pytest

from atopile.model.accessors import ModelVertexView
from atopile.model.differ import Delta, EMPTY, ROOT
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
    assert not delta.edge
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

    assert delta.edge == {
        (('new_module',), ()): EdgeType.part_of,
        (('new_module', 'new_component'), ('new_module',)): EdgeType.part_of,
    }
    assert not delta.data


def test_remove_node2(module1_root: ModelVertexView, module2_root: ModelVertexView):
    add_nodes(module1_root)
    delta = Delta.diff(module1_root, module2_root)
    assert delta.node == {
        ("new_module",): EMPTY,
        ("new_module", "new_component"): EMPTY,
    }

    assert delta.edge == {
        (('new_module',), ()): EMPTY,
        (('new_module', 'new_component'), ('new_module',)): EMPTY,
    }

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
    assert delta.edge == {
        (("dummy_comp0", "sig0"), ("dummy_comp1", "sig0")): EdgeType.connects_to
    }
    assert not delta.data


def test_remove_connection(module1_root: ModelVertexView, module2_root: ModelVertexView):
    add_connection(module1_root)
    delta = Delta.diff(module1_root, module2_root)
    assert not delta.node
    assert delta.edge == {
        (("dummy_comp0", "sig0"), ("dummy_comp1", "sig0")): EMPTY
    }
    assert not delta.data


def add_data(module2_root: ModelVertexView):
    module2_root.data["test"] = {"test2": "hello-world"}
    assert module2_root.data["test"]["test2"] == "hello-world"


def test_added_data(module1_root: ModelVertexView, module2_root: ModelVertexView):
    add_data(module2_root)
    delta = Delta.diff(module1_root, module2_root)
    assert not delta.node
    assert not delta.edge
    assert delta.data == {("test", "test2"): "hello-world"}


def test_modify_data(module1_root: ModelVertexView, module2_root: ModelVertexView):
    add_data(module1_root)
    add_data(module2_root)
    module2_root.data["test"]["test2"] = "new-world"
    delta = Delta.diff(module1_root, module2_root)
    assert not delta.node
    assert not delta.edge
    assert delta.data == {("test", "test2"): "new-world"}


def test_remove_data(module1_root: ModelVertexView, module2_root: ModelVertexView):
    add_data(module1_root)
    delta = Delta.diff(module1_root, module2_root)
    assert not delta.node
    assert not delta.edge
    assert delta.data == {("test", "test2"): EMPTY}


def test_apply_to(module1_root: ModelVertexView, module2_root: ModelVertexView):
    # we create some decent sized diff
    add_nodes(module2_root)
    add_connection(module2_root)
    add_data(module2_root)
    delta = Delta.diff(module1_root, module2_root)

    # then let's re-apply it to module1_root
    delta.apply_to(module1_root)

    # and finally check there's no diff between the objects anymore
    delta2 = Delta.diff(module1_root, module2_root)
    assert not delta2.node
    assert not delta2.edge
    assert not delta2.data


def test_apply_to_root_type_change(module1_root: ModelVertexView, module2_root: ModelVertexView):
    """
    This case happens when we subclass a module to a component

    NOTE: eh, we really shouldn't allow components in components, but there's not checks for now so this test is fine
    """
    module2_root.vertex["type"] = VertexType.component.value
    delta = Delta.diff(module1_root, module2_root)

    # then let's re-apply it to module1_root
    delta.apply_to(module1_root)

    # and finally check there's no diff between the objects anymore
    delta2 = Delta.diff(module1_root, module2_root)
    assert not delta2.node
    assert not delta2.edge
    assert not delta2.data
    assert module1_root.vertex_type == VertexType.component
