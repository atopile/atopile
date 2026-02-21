import logging
import os
import uuid
from contextlib import contextmanager
from pathlib import Path

import pytest

from atopile.dataclasses import LogRow
from atopile.logging import AtoLogger, DBLogHandler

pytestmark = [
    pytest.mark.ato_logging(kind=None, reset_root=True),
]


def _make_test_db_logger(
    captured: list[LogRow],
    *,
    identifier: str,
    context: str,
    logger_name_prefix: str,
):
    return AtoLogger._make_db_logger(
        identifier=identifier,
        context=context,
        writer=lambda rows: captured.extend(rows),
        row_class=LogRow,
        id_field="build_id",
        context_field="stage",
        logger_name=f"{logger_name_prefix}.{uuid.uuid4().hex}",
    )


@contextmanager
def _db_handler_context():
    root = logging.getLogger()
    db_handler = DBLogHandler(level=logging.DEBUG)
    root.addHandler(db_handler)
    root.setLevel(logging.DEBUG)
    try:
        yield
    finally:
        root.removeHandler(db_handler)


def test_unscoped_logger_uses_empty_build_id():
    captured: list[LogRow] = []
    logger = _make_test_db_logger(
        captured,
        identifier="",
        context="install",
        logger_name_prefix="atopile.db.test.unscoped",
    )
    logger.setLevel(logging.INFO)

    AtoLogger._active_build_logger = AtoLogger._active_test_logger = None
    AtoLogger._active_unscoped_logger = logger
    with _db_handler_context():
        logger.info("unscoped")
        logger.db_flush()

    assert len(captured) == 1
    assert captured[0].build_id == ""
    assert captured[0].stage == "install"


def test_alert_logs_persist_as_alert_level():
    captured: list[LogRow] = []
    logger = _make_test_db_logger(
        captured,
        identifier="",
        context="alerts",
        logger_name_prefix="atopile.db.test.alert",
    )
    logger.setLevel(logging.INFO)

    AtoLogger._active_build_logger = AtoLogger._active_test_logger = None
    AtoLogger._active_unscoped_logger = logger
    with _db_handler_context():
        logger.alert("alert")
        logger.db_flush()

    assert len(captured) >= 1
    assert captured[-1].level == "ALERT"


def test_non_db_logger_routes_to_active_db_context():
    captured: list[LogRow] = []
    active_logger = _make_test_db_logger(
        captured,
        identifier="build-1",
        context="stage-a",
        logger_name_prefix="atopile.db.test.active",
    )
    active_logger.setLevel(logging.INFO)

    AtoLogger._active_build_logger = active_logger

    with _db_handler_context():
        plain = logging.getLogger(f"thirdparty.test.{uuid.uuid4().hex}")
        plain.setLevel(logging.INFO)
        plain.info("from third-party logger")
        active_logger.db_flush()

    assert len(captured) >= 1
    row = captured[-1]
    assert row.build_id == "build-1"
    assert row.stage == "stage-a"
    assert row.logger_name == plain.name
    assert row.message == "from third-party logger"


def test_db_handler_uses_implicit_unscoped_without_build_or_test_context():
    AtoLogger._set_active_loggers()

    resolved = DBLogHandler._resolve_db_target()

    assert resolved is AtoLogger._active_unscoped_logger
    assert resolved.build_id == ""


def test_db_handler_raises_with_multiple_active_contexts():
    captured: list[LogRow] = []
    build_logger = _make_test_db_logger(
        captured,
        identifier="build-x",
        context="build-stage",
        logger_name_prefix="atopile.db.test.multictx.build",
    )
    unscoped_logger = _make_test_db_logger(
        captured,
        identifier="",
        context="unscoped-stage",
        logger_name_prefix="atopile.db.test.multictx.unscoped",
    )
    test_logger = _make_test_db_logger(
        captured,
        identifier="test-x",
        context="test-stage",
        logger_name_prefix="atopile.db.test.multictx.test",
    )

    AtoLogger._active_build_logger = build_logger
    AtoLogger._active_test_logger = test_logger
    AtoLogger._active_unscoped_logger = unscoped_logger
    with _db_handler_context():
        failing_logger = logging.getLogger(f"multictx.test.{uuid.uuid4().hex}")
        failing_logger.setLevel(logging.INFO)
        with pytest.raises(
            RuntimeError,
            match="Build and test DB logging contexts active simultaneously",
        ):
            failing_logger.info("should fail")


def test_activate_build_defaults_stage_to_blank():
    prev_build_id = os.environ.get("ATO_BUILD_ID")
    os.environ["ATO_BUILD_ID"] = f"build-{uuid.uuid4().hex}"

    try:
        logger = AtoLogger.activate_build(stage="")

        assert logger.build_id == os.environ["ATO_BUILD_ID"]
        assert logger.stage_or_test_name == ""
        assert AtoLogger._active_build_logger is logger
        assert AtoLogger._active_test_logger is None
        assert AtoLogger._active_unscoped_logger is not None
    finally:
        if prev_build_id is None:
            os.environ.pop("ATO_BUILD_ID", None)
        else:
            os.environ["ATO_BUILD_ID"] = prev_build_id


def test_activate_build_requires_ato_build_id():
    prev_build_id = os.environ.get("ATO_BUILD_ID")
    os.environ.pop("ATO_BUILD_ID", None)

    try:
        with pytest.raises(KeyError):
            AtoLogger.activate_build(stage="")
    finally:
        if prev_build_id is None:
            os.environ.pop("ATO_BUILD_ID", None)
        else:
            os.environ["ATO_BUILD_ID"] = prev_build_id


def test_source_file_reports_original_callsite():
    captured: list[LogRow] = []
    logger = _make_test_db_logger(
        captured,
        identifier="",
        context="source",
        logger_name_prefix="atopile.db.test.source",
    )
    logger.setLevel(logging.INFO)

    AtoLogger._active_build_logger = AtoLogger._active_test_logger = None
    AtoLogger._active_unscoped_logger = logger

    with _db_handler_context():
        logger.info("callsite check")
        logger.db_flush()

    assert len(captured) >= 1
    rows = [r for r in captured if r.message == "callsite check"]
    assert rows
    for row in rows:
        assert row.source_file is not None
        assert Path(row.source_file).name == "test_logging_db.py"
        assert row.source_line is not None
