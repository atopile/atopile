from pytest import fixture, mark
from atopile.model.model import Model, VertexType, EdgeType
from atopile.targets.netlist.nets import resolve_net_name, find_nets, find_net_names

@fixture
def dummy_model() -> Model:
    m = Model()
    file = m.new_vertex(VertexType.file, "dummy_file.ato")
    module = m.new_vertex(VertexType.module, "dummy_module", file)
    top_signal_path = m.new_vertex(VertexType.signal, "top_sig", module)

    comp1 = m.new_vertex(VertexType.component, "dummy_comp1", module)
    comp2 = m.new_vertex(VertexType.component, "dummy_comp2", module)
    for c in (comp1, comp2):
        for i in range(2):
            p_path = m.new_vertex(VertexType.pin, f"p{i}", c)
            s_path = m.new_vertex(VertexType.signal, f"sig{i}", c)

            m.new_edge(EdgeType.connects_to, p_path, s_path)

    # s_path is still dummy_comp2/sig2
    m.new_edge(EdgeType.connects_to, top_signal_path, s_path)
    m.new_edge(EdgeType.connects_to, comp1 + "/sig0", comp1 + "/sig1")

    return m

expected_nets = {
    "dummy_file.ato/dummy_module/dummy_comp1.sig0-sig1": [
        "dummy_file.ato/dummy_module/dummy_comp1/sig0",
        "dummy_file.ato/dummy_module/dummy_comp1/sig1",
        "dummy_file.ato/dummy_module/dummy_comp1/p0",
        "dummy_file.ato/dummy_module/dummy_comp1/p1"
    ],
    "dummy_file.ato/dummy_module/dummy_comp2.sig0": [
        "dummy_file.ato/dummy_module/dummy_comp2/sig0",
        "dummy_file.ato/dummy_module/dummy_comp2/p0"
    ],
    "dummy_file.ato/dummy_module.top_sig": [
        "dummy_file.ato/dummy_module/dummy_comp2/sig1",
        "dummy_file.ato/dummy_module/dummy_comp2/p1",
        "dummy_file.ato/dummy_module/top_sig"
    ],
}

def test_find_nets(dummy_model: Model):
    nets = find_nets(dummy_model)
    assert len(nets) == 3

    checked_nets = []
    for net in nets:
        for i, expected_net in enumerate(expected_nets.values()):
            if i in checked_nets:
                continue
            net_paths = [v.path for v in net]
            if not any(p in net_paths for p in expected_net):
                continue
            assert set(net_paths) == set(expected_net)
            checked_nets += [i]

    assert len(checked_nets) == len(expected_nets)

@mark.xfail
def test_nothing():
    raise NotImplementedError

def test_naming(dummy_model: Model):
    nets = find_nets(dummy_model)
    net_names = {resolve_net_name(n) for n in nets}

    assert net_names == set(expected_nets.keys())

def test_find_net_names(dummy_model: Model):
    net_names = find_net_names(dummy_model)
    assert set(net_names.keys()) == set(expected_nets.keys())

    for name, net in net_names.items():
        assert {v.path for v in net} == set(expected_nets[name])
