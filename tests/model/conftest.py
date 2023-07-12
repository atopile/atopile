from pytest import fixture
from atopile.model.model import Model, VertexType, EdgeType


@fixture
def dummy_model() -> Model:
    m = Model()
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

    # s_path is still dummy_comp2/sig2
    m.new_edge(EdgeType.connects_to, top_signal_path, s_path)
    m.new_edge(EdgeType.connects_to, comp1 + "/sig0", comp1 + "/sig1")
    m.new_edge(EdgeType.connects_to, comp1 + "/spare_sig", comp2 + "/spare_sig")

    return m
