from .conftest import EXEC_T


def test_net_names_deterministic(build_app: EXEC_T, save_tmp_path_on_failure: None):
    # Build a simple chain so multiple nets are generated deterministically
    src = """
        #pragma experiment("BRIDGE_CONNECT")
        import Resistor
        module App:
            r = new Resistor[3]
            r[0] ~> r[1] ~> r[2]
        """

    # First build (establish baseline)
    _, _, p1 = build_app(src, [])
    assert p1.returncode == 0

    # Second build with --frozen should not report layout changes if net names
    # are deterministic
    _, stderr2, p2 = build_app(src, ["--frozen"])
    assert p2.returncode == 0, stderr2
