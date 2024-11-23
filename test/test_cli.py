from typer.testing import CliRunner

from atopile.cli.cli import app

runner = CliRunner()


def test_app():
    result = runner.invoke(app, ["build", "examples/project"])
    assert result.exit_code == 0
    # TODO: figure out how to get logging onto stdout/stderr
    # assert "Build complete!" in result.stdout
    # assert "ERROR" not in result.stdout
