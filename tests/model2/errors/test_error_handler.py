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


def test_map_filtering_errors():
    log = MagicMock()
    handler = ErrorHandler(log)

    def func(x):
        if issubclass(x, Exception) or isinstance(x, Exception):
            raise x
        return x

    assert list(handler.map_filtering_errors(func, [1, 2, 3])) == [1, 2, 3]

    # assert list(handler.map_filtering_errors(func, [1, AtoError, 3])) == [1, 3]

    with pytest.raises(TypeError):
        list(handler.map_filtering_errors(func, [1, TypeError, 3]))



filter()