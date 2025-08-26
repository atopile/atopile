from .conftest import EXEC_T


def test_duplicate_specified_net_names(
    build_app: EXEC_T, save_tmp_path_on_failure: None
):
    _, stderr, p = build_app(
        """
        import Resistor
        module App:
            a = new Resistor
            b = new Resistor
            a.p1.override_net_name = "net"
            b.p1.override_net_name = "net"
        """,
        [],
    )

    assert p.returncode != 0
    assert "Net name collision" in stderr


def test_conflicting_net_names(build_app: EXEC_T, save_tmp_path_on_failure: None):
    _, stderr, p = build_app(
        """
        import Resistor
        module App:
            a = new Resistor
            b = new Resistor
            a.p1 ~ b.p1
            a.p1.override_net_name = "net1"
            b.p1.override_net_name = "net2"
        """,
        [],
    )

    assert p.returncode != 0
    assert "Multiple conflicting required net names" in stderr


def test_agreeing_net_names(build_app: EXEC_T, save_tmp_path_on_failure: None):
    _, _, p = build_app(
        """
        import Resistor
        module App:
            a = new Resistor
            b = new Resistor
            a.p1 ~ b.p1
            a.p1.override_net_name = "net"
            b.p1.override_net_name = "net"
        """,
        [],
    )

    assert p.returncode == 0


def test_duplicate_suggested_net_names(
    build_app: EXEC_T, save_tmp_path_on_failure: None
):
    """
    Two different nets with the same suggested name should not error.
    They should be deconflicted by the naming algorithm.
    """
    _, _, p = build_app(
        """
        import Resistor
        module App:
            a = new Resistor
            b = new Resistor
            a.p1.suggest_net_name = "net"
            b.p1.suggest_net_name = "net"
        """,
        [],
    )

    assert p.returncode == 0


def test_conflicting_suggested_names_on_same_net(
    build_app: EXEC_T, save_tmp_path_on_failure: None
):
    """
    If multiple suggested names exist on the same electrical net, the build
    should succeed. One suggestion will win and no error should be raised.
    """
    _, _, p = build_app(
        """
        import Resistor
        module App:
            a = new Resistor
            b = new Resistor
            a.p1 ~ b.p1
            a.p1.suggest_net_name = "net1"
            b.p1.suggest_net_name = "net2"
        """,
        [],
    )

    assert p.returncode == 0


def test_differential_pair_suffixes(build_app: EXEC_T, save_tmp_path_on_failure: None):
    """
    DifferentialPair should enforce `_p` and `_n` suffixes on the nets.
    """
    _, stdout, p = build_app(
        """
        import DifferentialPair
        module App:
            dp = new DifferentialPair
            # Connect each side to a unique signal to force separate nets
            signal a ~ dp.p.line
            signal b ~ dp.n.line
        """,
        [],
    )

    assert p.returncode == 0
