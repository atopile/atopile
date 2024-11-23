import pytest
from typer.testing import CliRunner

from atopile.cli.cli import app

runner = CliRunner()


# FIXME: this test is broken in CI
@pytest.mark.not_in_ci
def test_app():
    result = runner.invoke(app, ["build", "examples/project"])
    assert result.exit_code == 0
    # TODO: figure out how to get logging onto stdout/stderr
    # assert "Build complete!" in result.stdout
    # assert "ERROR" not in result.stdout
