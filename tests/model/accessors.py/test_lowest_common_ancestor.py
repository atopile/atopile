from pytest import fixture, mark
from atopile.model.accessors import lowest_common_ancestor, ModelVertexView
from atopile.model.model import Model, VertexType, EdgeType

@fixture
def dummy_model() -> Model:
    m = Model()
    file = m.new_vertex(VertexType.file, "dummy_file.ato")
    module = m.new_vertex(VertexType.module, "dummy_module", file)
    comp1 = m.new_vertex(VertexType.component, "dummy_comp1", module)
    comp2 = m.new_vertex(VertexType.component, "dummy_comp2", module)
    for c in (comp1, comp2):
        m.new_vertex(VertexType.pin, "p1", c)
        m.new_vertex(VertexType.pin, "p2", c)
    return m

def test_nothing():
    assert lowest_common_ancestor([]) is None

def test_one(dummy_model: Model):
    module = ModelVertexView.from_path(dummy_model, "dummy_file.ato/dummy_module")
    assert module == lowest_common_ancestor([module])

def test_pins(dummy_model: Model):
    comp = ModelVertexView.from_path(dummy_model, "dummy_file.ato/dummy_module/dummy_comp1")
    p1 = ModelVertexView.from_path(dummy_model, "dummy_file.ato/dummy_module/dummy_comp1/p1")
    p2 = ModelVertexView.from_path(dummy_model, "dummy_file.ato/dummy_module/dummy_comp1/p2")
    assert comp == lowest_common_ancestor([p1, p2])

def test_modules(dummy_model: Model):
    module = ModelVertexView.from_path(dummy_model, "dummy_file.ato/dummy_module")
    p1 = ModelVertexView.from_path(dummy_model, "dummy_file.ato/dummy_module/dummy_comp1/p1")
    p2 = ModelVertexView.from_path(dummy_model, "dummy_file.ato/dummy_module/dummy_comp2/p1")
    assert module == lowest_common_ancestor([p1, p2])

@mark.xfail
def test_no_common_ansestor(dummy_model: Model):
    raise NotImplementedError
