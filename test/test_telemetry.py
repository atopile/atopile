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


def test_init_client():
    assert isinstance(telemetry.client, telemetry.Posthog)


def test_capture_event():
    @telemetry.capture(
        "test_start",
        "test_end",
        {"test_property": "test_value"},
    )
    def test_capture_event():
        pass

    test_capture_event()


def test_capture_exception():
    try:
        raise Exception("test_exception")
    except Exception as e:
        telemetry.capture_exception(e, {"test_property": "test_value"})
