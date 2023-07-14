from pytest import mark

from atopile.model.accessors import (
    ModelVertexView,
    lowest_common_ancestor,
    lowest_common_ancestor_with_ancestor_ids,
)
from atopile.model.model import Model


def test_nothing():
    assert lowest_common_ancestor([]) is None

def test_one(dummy_model: Model):
    module = ModelVertexView.from_path(dummy_model, "dummy_file.ato:dummy_module")
    assert module == lowest_common_ancestor([module])

def test_pins(dummy_model: Model):
    comp = ModelVertexView.from_path(dummy_model, "dummy_file.ato:dummy_module.dummy_comp0")
    p0 = ModelVertexView.from_path(dummy_model, "dummy_file.ato:dummy_module.dummy_comp0.p0")
    p1 = ModelVertexView.from_path(dummy_model, "dummy_file.ato:dummy_module.dummy_comp0.p1")
    assert comp == lowest_common_ancestor([p0, p1])

def test_modules(dummy_model: Model):
    module = ModelVertexView.from_path(dummy_model, "dummy_file.ato:dummy_module")
    p0 = ModelVertexView.from_path(dummy_model, "dummy_file.ato:dummy_module.dummy_comp0.p0")
    p1 = ModelVertexView.from_path(dummy_model, "dummy_file.ato:dummy_module.dummy_comp1.p0")
    assert module == lowest_common_ancestor([p0, p1])

def test_ancestor_ids(dummy_model: Model):
    # module = ModelVertexView.from_path(dummy_model, "dummy_file.ato:dummy_module")
    p0 = ModelVertexView.from_path(dummy_model, "dummy_file.ato:dummy_module.dummy_comp0.p0")
    p1 = ModelVertexView.from_path(dummy_model, "dummy_file.ato:dummy_module.dummy_comp1.p0")
    _, rel_anc_ids = lowest_common_ancestor_with_ancestor_ids([p0, p1])
    assert rel_anc_ids == [
        [ModelVertexView.from_path(dummy_model, "dummy_file.ato:dummy_module.dummy_comp0").index],
        [ModelVertexView.from_path(dummy_model, "dummy_file.ato:dummy_module.dummy_comp1").index]
    ]

@mark.xfail
def test_no_common_ansestor(dummy_model: Model):
    raise NotImplementedError
