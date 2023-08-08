import pytest

from atopile.model.model import Model
from atopile.targets.netlist.nets import find_net_names, find_nets
from atopile.model.names import resolve_abs_name

expected_nets = (
    (
        "dummy_comp0-sig1",
        "dummy_file.ato:dummy_module.dummy_comp0.sig0-sig1",
        (
            "dummy_file.ato:dummy_module.dummy_comp0.sig0",
            "dummy_file.ato:dummy_module.dummy_comp0.sig1",
            "dummy_file.ato:dummy_module.dummy_comp0.p0",
            "dummy_file.ato:dummy_module.dummy_comp0.p1",
        )
    ),
    (
        "dummy_comp1-sig0",
        "dummy_file.ato:dummy_module.dummy_comp1.sig0",
        (
            "dummy_file.ato:dummy_module.dummy_comp1.sig0",
            "dummy_file.ato:dummy_module.dummy_comp1.p0",
        )
    ),
    (
        "dummy_module-top_sig",
        "dummy_file.ato:dummy_module.top_sig",
        (
            "dummy_file.ato:dummy_module.dummy_comp1.sig1",
            "dummy_file.ato:dummy_module.dummy_comp1.p1",
            "dummy_file.ato:dummy_module.top_sig",
        )
    ),
    (
        "dummy_module-spare_sig",
        "dummy_file.ato:dummy_module.dummy_comp0.spare_sig-dummy_comp1.spare_sig",
        (
            "dummy_file.ato:dummy_module.dummy_comp0.spare_sig",
            "dummy_file.ato:dummy_module.dummy_comp1.spare_sig",
        ),
    )
)


def test_find_nets(dummy_model: Model):
    nets = find_nets(dummy_model)
    assert len(nets) == len(expected_nets)

    checked_nets = []
    for net in nets:
        for i, expected_net_data in enumerate(expected_nets):
            expected_net = expected_net_data[2]
            if i in checked_nets:
                continue
            net_paths = [v.path for v in net]
            if not any(p in net_paths for p in expected_net):
                continue
            assert set(net_paths) == set(expected_net)
            checked_nets += [i]

    assert len(checked_nets) == len(expected_nets)


@pytest.mark.xfail
def test_nothing():
    raise NotImplementedError


def test_naming(dummy_model: Model):
    nets = find_nets(dummy_model)
    net_names = {resolve_abs_name(n)[1] for n in nets}

    assert net_names == set(d[1] for d in expected_nets)  # noqa: C401


def test_find_net_names(dummy_model: Model):
    net_names = find_net_names(dummy_model)
    assert set(net_names.keys()) == set(d[0] for d in expected_nets)  # noqa: C401

    _expected_net_dict = {d[0]: d[2] for d in expected_nets}

    for name, net in net_names.items():
        assert {v.path for v in net} == set(_expected_net_dict[name])


# TODO:
@pytest.mark.xfail
def test_flipped_naming():
    raise NotImplementedError
