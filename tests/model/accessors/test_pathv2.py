import pytest

from atopile.model.model import Model
from atopile.model.accessors import ModelVertexView

@pytest.mark.parametrize(
    "v1_path, v2_path",
    [
        ("dummy_file.ato", "dummy_file.ato"),
        ("dummy_file.ato/dummy_module", "dummy_file.ato:dummy_module"),
        ("dummy_file.ato/dummy_module/dummy_comp1", "dummy_file.ato:dummy_module.dummy_comp1"),
    ]
)
def test_v1_to_v2(dummy_model: Model, v1_path, v2_path):
    ModelVertexView.from_path(dummy_model, v1_path).pathv2 == v2_path

@pytest.mark.xfail
@pytest.mark.parametrize(
    "v2_path",
    [
        "dummy_file.ato",
        "dummy_file.ato:dummy_module",
        "dummy_file.ato:dummy_module.dummy_comp1",
    ]
)
def test_v2_to_v1(dummy_model: Model, v2_path):
    ModelVertexView.from_pathv2(dummy_model, v2_path).pathv2 == v2_path
