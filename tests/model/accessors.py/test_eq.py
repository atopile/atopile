from atopile.model.accessors import ModelVertexView
from atopile.model.model import Model, VertexType

def test_equals():
    m = Model()
    m.new_vertex(VertexType.file, "dummy_file.ato")

    assert ModelVertexView(m, 0) == ModelVertexView(m, 0)

def test_different_models():
    m1 = Model()
    m2 = Model()
    m1.new_vertex(VertexType.file, "dummy_file.ato")
    m2.new_vertex(VertexType.file, "dummy_file.ato")

    assert ModelVertexView(m1, 0) != ModelVertexView(m2, 0)

def test_different_verticies():
    m = Model()
    m.new_vertex(VertexType.file, "dummy_file1.ato")
    m.new_vertex(VertexType.file, "dummy_file2.ato")

    assert ModelVertexView(m, 0) != ModelVertexView(m, 1)

def test_contains():
    m = Model()
    m.new_vertex(VertexType.file, "dummy_file.ato")
    m.new_vertex(VertexType.file, "dummy_file2.ato")

    assert ModelVertexView(m, 0) in [ModelVertexView(m, 0)]
    assert ModelVertexView(m, 0) not in [ModelVertexView(m, 1)]
    assert ModelVertexView(m, 1) not in [ModelVertexView(m, 0)]
