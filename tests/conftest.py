from typing import Callable

from pytest import fixture

from atopile.model.accessors import ModelVertexView
from atopile.model.model import EdgeType, Model, VertexType


@fixture
def dummy_maker() -> Callable[[], Model]:
    def _make_dummy():
        m = Model()
        m.src_files = ["dummy_file.ato"]
        file = m.new_vertex(VertexType.file, "dummy_file.ato")
        module = m.new_vertex(VertexType.module, "dummy_module", file)
        top_signal_path = m.new_vertex(VertexType.signal, "top_sig", module)

        comp1 = m.new_vertex(VertexType.component, "dummy_comp0", module)
        comp2 = m.new_vertex(VertexType.component, "dummy_comp1", module)
        for c in (comp1, comp2):
            m.new_vertex(VertexType.signal, "spare_sig", c)
            for i in range(2):
                p_path = m.new_vertex(VertexType.pin, f"p{i}", c)
                s_path = m.new_vertex(VertexType.signal, f"sig{i}", c)

                m.new_edge(EdgeType.connects_to, p_path, s_path)

        # s_path is still dummy_comp2.sig2
        m.new_edge(EdgeType.connects_to, top_signal_path, s_path)
        m.new_edge(EdgeType.connects_to, comp1 + ".sig0", comp1 + ".sig1")
        m.new_edge(EdgeType.connects_to, comp1 + ".spare_sig", comp2 + ".spare_sig")

        return m

    return _make_dummy


@fixture
def dummy_model(dummy_maker) -> Model:
    return dummy_maker()


@fixture
def module(dummy_model: Model):
    return ModelVertexView.from_path(dummy_model, "dummy_file.ato:dummy_module")


@fixture
def comp0(dummy_model: Model):
    return ModelVertexView.from_path(
        dummy_model, "dummy_file.ato:dummy_module.dummy_comp0"
    )


@fixture
def comp0_p0(dummy_model: Model):
    return ModelVertexView.from_path(
        dummy_model, "dummy_file.ato:dummy_module.dummy_comp0.p0"
    )
