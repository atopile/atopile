from pathlib import Path

from test.end_to_end.conftest import dump_and_run
from test.end_to_end.test_pcb_export import PcbSummary, summarize_pcb_file

from .conftest import EXEC_T


def test_duplicate_specified_net_names(
    build_app: EXEC_T, save_tmp_path_on_failure: None
):
    stdout, _, p = build_app(
        """
        import Resistor
        module App:
            a = new Resistor
            b = new Resistor
            a.unnamed[0].override_net_name = "net"
            b.unnamed[0].override_net_name = "net"
        """,
        [],
    )

    assert p.returncode != 0
    assert "Net name collision" in stdout


def test_conflicting_net_names(build_app: EXEC_T, save_tmp_path_on_failure: None):
    stdout, _, p = build_app(
        """
        import Resistor
        module App:
            a = new Resistor
            b = new Resistor
            a.unnamed[0] ~ b.unnamed[0]
            a.unnamed[0].override_net_name = "net1"
            b.unnamed[0].override_net_name = "net2"
        """,
        [],
    )

    assert p.returncode != 0
    assert "Multiple conflicting required net names" in stdout


def test_agreeing_net_names(build_app: EXEC_T, save_tmp_path_on_failure: None):
    _, _, p = build_app(
        """
        import Resistor
        module App:
            a = new Resistor
            b = new Resistor
            a.unnamed[0] ~ b.unnamed[0]
            a.unnamed[0].override_net_name = "net"
            b.unnamed[0].override_net_name = "net"
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
            a.unnamed[0].suggest_net_name = "net"
            b.unnamed[0].suggest_net_name = "net"
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
            a.unnamed[0] ~ b.unnamed[0]
            a.unnamed[0].suggest_net_name = "net1"
            b.unnamed[0].suggest_net_name = "net2"
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


def test_expected_net_name(tmpdir: Path):
    pcb_file = tmpdir / Path("layout/app/app.kicad_pcb")
    assert not pcb_file.exists()

    app = """
    #pragma experiment("BRIDGE_CONNECT")
    import I2C
    import Resistor

    module App:
        i2c = new I2C
        resistor = new Resistor
        resistor.lcsc_id = "C25804"

        i2c.scl.line ~> resistor ~> i2c.sda.line
    """

    _, stderr, p = dump_and_run(app, [], working_dir=tmpdir)

    assert p.returncode == 0
    assert pcb_file.exists()
    # print(pcb_file.read_text(encoding="utf-8"))

    assert summarize_pcb_file(pcb_file) == PcbSummary(
        num_layers=29, nets=["SCL", "SDA"], footprints=["R1"]
    )
