import pytest

from atopile.model2.errors import ErrorHandler, AtoError, AtoFatalError, DONT_FILL
from unittest.mock import MagicMock


def test_handle():
    log = MagicMock()
    handler = ErrorHandler(log)

    error = Exception("test error")
    with pytest.raises(Exception):
        handler.handle(error)

    assert len(handler.errors) == 1

    error = AtoError("test error")
    handler.handle(error)

    assert len(handler.errors) == 2
    assert log.error.call_count == 2


def test_assert_no_errors():
    log = MagicMock()
    handler = ErrorHandler(log)

    handler.assert_no_errors()

    error = AtoError("test error")
    handler.handle(error)

    with pytest.raises(AtoFatalError):
        handler.assert_no_errors()
