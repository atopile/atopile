from pytest import fixture
from atopile.model.model import Model, VertexType


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
