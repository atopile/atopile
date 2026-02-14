import logging
import os
import uuid
from unittest.mock import patch

from atopile.dataclasses import LogRow
from atopile.logging import AtoLogger, DBLogHandler


def test_unscoped_logger_uses_empty_build_id():
    captured: list[LogRow] = []
    logger = AtoLogger._make_db_logger(
        identifier="",
        context="install",
        writer=lambda rows: captured.extend(rows),
        row_class=LogRow,
        id_field="build_id",
        context_field="stage",
        logger_name=f"atopile.db.test.unscoped.{uuid.uuid4().hex}",
    )
    logger.setLevel(logging.INFO)

    root = logging.getLogger()
    prev_level = root.level
    prev_active_unscoped = AtoLogger._active_unscoped_logger
    AtoLogger._active_unscoped_logger = logger
    db_handler = DBLogHandler(level=logging.DEBUG)
    root.addHandler(db_handler)
    root.setLevel(logging.DEBUG)
    try:
        logger.info("unscoped")
        logger.db_flush()
    finally:
        root.removeHandler(db_handler)
        root.setLevel(prev_level)
        AtoLogger._active_unscoped_logger = prev_active_unscoped

    assert len(captured) == 1
    assert captured[0].build_id == ""
    assert captured[0].stage == "install"


def test_non_db_logger_routes_to_active_db_context():
    captured: list[LogRow] = []
    active_logger = AtoLogger._make_db_logger(
        identifier="build-1",
        context="stage-a",
        writer=lambda rows: captured.extend(rows),
        row_class=LogRow,
        id_field="build_id",
        context_field="stage",
        logger_name=f"atopile.db.test.active.{uuid.uuid4().hex}",
    )
    active_logger.setLevel(logging.INFO)

    prev_active_build = AtoLogger._active_build_logger
    prev_active_test = AtoLogger._active_test_logger
    AtoLogger._active_build_logger = active_logger
    AtoLogger._active_test_logger = None

    root = logging.getLogger()
    prev_level = root.level
    db_handler = DBLogHandler(level=logging.DEBUG)
    root.addHandler(db_handler)
    root.setLevel(logging.DEBUG)
    try:
        plain = logging.getLogger(f"thirdparty.test.{uuid.uuid4().hex}")
        plain.setLevel(logging.INFO)
        plain.info("from third-party logger")
        active_logger.db_flush()
    finally:
        root.removeHandler(db_handler)
        root.setLevel(prev_level)
        AtoLogger._active_build_logger = prev_active_build
        AtoLogger._active_test_logger = prev_active_test

    assert len(captured) >= 1
    row = captured[-1]
    assert row.build_id == "build-1"
    assert row.stage == "stage-a"
    assert row.logger_name == plain.name
    assert row.message == "from third-party logger"


def test_db_handler_raises_without_active_context():
    root = logging.getLogger()
    prev_level = root.level
    db_handler = DBLogHandler(level=logging.DEBUG)
    prev_active_build = AtoLogger._active_build_logger
    prev_active_test = AtoLogger._active_test_logger
    prev_active_unscoped = AtoLogger._active_unscoped_logger
    AtoLogger._active_build_logger = None
    AtoLogger._active_test_logger = None
    AtoLogger._active_unscoped_logger = None
    root.addHandler(db_handler)
    root.setLevel(logging.DEBUG)
    try:
        failing_logger = logging.getLogger(f"noctx.test.{uuid.uuid4().hex}")
        failing_logger.setLevel(logging.INFO)
        try:
            failing_logger.info("should fail")
            raise AssertionError("Expected RuntimeError for missing active context")
        except RuntimeError:
            pass
    finally:
        root.removeHandler(db_handler)
        root.setLevel(prev_level)
        AtoLogger._active_build_logger = prev_active_build
        AtoLogger._active_test_logger = prev_active_test
        AtoLogger._active_unscoped_logger = prev_active_unscoped


def test_db_handler_raises_with_multiple_active_contexts():
    captured: list[LogRow] = []
    build_logger = AtoLogger._make_db_logger(
        identifier="build-x",
        context="build-stage",
        writer=lambda rows: captured.extend(rows),
        row_class=LogRow,
        id_field="build_id",
        context_field="stage",
        logger_name=f"atopile.db.test.multictx.build.{uuid.uuid4().hex}",
    )
    unscoped_logger = AtoLogger._make_db_logger(
        identifier="",
        context="unscoped-stage",
        writer=lambda rows: captured.extend(rows),
        row_class=LogRow,
        id_field="build_id",
        context_field="stage",
        logger_name=f"atopile.db.test.multictx.unscoped.{uuid.uuid4().hex}",
    )

    root = logging.getLogger()
    prev_level = root.level
    db_handler = DBLogHandler(level=logging.DEBUG)
    prev_active_build = AtoLogger._active_build_logger
    prev_active_test = AtoLogger._active_test_logger
    prev_active_unscoped = AtoLogger._active_unscoped_logger
    AtoLogger._active_build_logger = build_logger
    AtoLogger._active_test_logger = None
    AtoLogger._active_unscoped_logger = unscoped_logger
    root.addHandler(db_handler)
    root.setLevel(logging.DEBUG)
    try:
        failing_logger = logging.getLogger(f"multictx.test.{uuid.uuid4().hex}")
        failing_logger.setLevel(logging.INFO)
        try:
            failing_logger.info("should fail")
            raise AssertionError("Expected RuntimeError for multiple active contexts")
        except RuntimeError:
            pass
    finally:
        root.removeHandler(db_handler)
        root.setLevel(prev_level)
        AtoLogger._active_build_logger = prev_active_build
        AtoLogger._active_test_logger = prev_active_test
        AtoLogger._active_unscoped_logger = prev_active_unscoped


def test_setup_build_logging_defaults_stage_to_blank():
    prev_build_id = os.environ.get("ATO_BUILD_ID")
    prev_timestamp = os.environ.get("ATO_BUILD_TIMESTAMP")
    os.environ["ATO_BUILD_ID"] = f"build-{uuid.uuid4().hex}"
    os.environ["ATO_BUILD_TIMESTAMP"] = "2026-02-14_00-00-00"

    prev_active_build = AtoLogger._active_build_logger
    prev_active_test = AtoLogger._active_test_logger
    prev_active_unscoped = AtoLogger._active_unscoped_logger
    expected = AtoLogger._make_db_logger(
        identifier="build-test",
        context="",
        writer=lambda _rows: None,
        row_class=LogRow,
        id_field="build_id",
        context_field="stage",
        logger_name=f"atopile.db.test.setup.{uuid.uuid4().hex}",
    )
    try:
        with patch.object(AtoLogger, "get_build", return_value=expected) as get_build:
            logger = AtoLogger.setup_build_logging(enable_database=True, stage=None)

        assert logger is expected
        assert get_build.call_count == 1
        _, kwargs = get_build.call_args
        assert kwargs["stage"] == ""
        assert kwargs["build_id"] == os.environ["ATO_BUILD_ID"]
        assert AtoLogger._active_build_logger is expected
        assert AtoLogger._active_test_logger is None
        assert AtoLogger._active_unscoped_logger is None
    finally:
        AtoLogger._active_build_logger = prev_active_build
        AtoLogger._active_test_logger = prev_active_test
        AtoLogger._active_unscoped_logger = prev_active_unscoped
        if prev_build_id is None:
            os.environ.pop("ATO_BUILD_ID", None)
        else:
            os.environ["ATO_BUILD_ID"] = prev_build_id
        if prev_timestamp is None:
            os.environ.pop("ATO_BUILD_TIMESTAMP", None)
        else:
            os.environ["ATO_BUILD_TIMESTAMP"] = prev_timestamp
