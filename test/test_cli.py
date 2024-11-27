import pytest
from typer.testing import CliRunner

from atopile.cli.cli import app

runner = CliRunner()


# FIXME: this test is broken in CI
@pytest.mark.not_in_ci
@pytest.mark.parametrize("config", ["ato", "faebryk"])
def test_app(config):
    result = runner.invoke(app, ["build", "examples/project", "-b", config])
    assert result.exit_code == 0
    # TODO: figure out how to get logging onto stdout/stderr
    # assert "Build complete!" in result.stdout
    # assert "ERROR" not in result.stdout
