from unittest.mock import MagicMock

import pytest

from atopile.errors import (
    UserException,
)
from faebryk.libs.exceptions import (
    accumulate,
    downgrade,
    iter_through_errors,
)


def test_ExceptionAccumulator():
    with pytest.raises(UserException):
        with accumulate() as error_collector:
            with error_collector.collect():
                raise UserException("test error")

            raise UserException("test error 2")


def test_iter_through_errors():
    try:
        for cltr, i in iter_through_errors(range(4)):
            with cltr():
                if i == 1:
                    raise UserException("test error")
                if i == 2:
                    raise UserException("test error 2")

    except ExceptionGroup as ex:
        assert len(ex.exceptions) == 2
        ex_1, ex_2 = ex.exceptions
        assert ex_1.message == "test error"
        assert ex_2.message == "test error 2"

    else:
        raise AssertionError("Expected an ExceptionGroup to be raised")


def test_downgrade_context():
    logger = MagicMock()
    with downgrade(ValueError, logger=logger):
        raise ValueError()

    logger.log.assert_called_once()


def test_downgrade_decorator():
    logger = MagicMock()

    @downgrade(ValueError, logger=logger)
    def foo():
        raise ValueError()

    a = foo()
    assert a is None
    logger.log.assert_called_once()


def test_downgrade_decorator_with_default():
    logger = MagicMock()

    @downgrade(ValueError, default=2, logger=logger)
    def foo():
        raise ValueError()

    a = foo()
    assert a == 2
    logger.log.assert_called_once()
