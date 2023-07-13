from atopile.model.accessors import ModelVertexView

def test_direct_child(comp0: ModelVertexView, comp0_p0: ModelVertexView):
    assert comp0.relative_path(comp0_p0) == "p0"

def test_two_down(module: ModelVertexView, comp0: ModelVertexView, comp0_p0: ModelVertexView):
    assert module.relative_path(comp0_p0) == "dummy_comp0.p0"
