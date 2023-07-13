import pytest

from atopile.model.model import Model
from atopile.model.accessors import ModelVertexView


@pytest.mark.parametrize(
    "path",
    [
        "dummy_file.ato",
        "dummy_file.ato:dummy_module",
        "dummy_file.ato:dummy_module.dummy_comp1",
    ],
)
def test_roundtrip(dummy_model: Model, path):
    assert ModelVertexView.from_path(dummy_model, path).path == path
