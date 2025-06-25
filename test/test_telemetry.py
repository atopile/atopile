import pytest

from atopile import telemetry


@pytest.mark.parametrize(
    ("git_remote",),
    [
        ("https://github.com/atopile/atopile.git",),
        ("git@github.com:atopile/atopile.git",),
    ],
)
def test_normalize_git_remote_url(git_remote):
    assert (
        telemetry._normalize_git_remote_url(git_remote) == "github.com/atopile/atopile"
    )
