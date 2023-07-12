import pytest

from atopile.model.accessors import ModelVertexView

def test_self(comp0: ModelVertexView):
    with pytest.raises(ValueError):
        comp0.relative_mvv_path(comp0)

def test_direct_child(comp0: ModelVertexView, comp0_p0: ModelVertexView):
    assert comp0.relative_mvv_path(comp0_p0) == [comp0_p0]

def test_two_down(module: ModelVertexView, comp0: ModelVertexView, comp0_p0: ModelVertexView):
    assert module.relative_mvv_path(comp0_p0) == [comp0, comp0_p0]
