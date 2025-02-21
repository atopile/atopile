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
