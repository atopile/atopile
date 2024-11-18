import pytest

from atopile import telemetry


@pytest.mark.parametrize(
    ("git_remote",),
    [
        ("https://github.com/atopile/atopile.git",),
        ("git@github.com:atopile/atopile.git",),
    ],
)
def test_commonise_project_url(git_remote):
    assert telemetry.commonise_project_url(git_remote) == "github.com/atopile/atopile"
