import logging
import os
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from atopile.dataclasses import LogRow
from atopile.logging import AtoLogger, DBLogHandler

pytestmark = [
    pytest.mark.ato_logging(reset_root=True),
]


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
    AtoLogger._active_unscoped_logger = logger
    db_handler = DBLogHandler(level=logging.DEBUG)
    root.addHandler(db_handler)
    root.setLevel(logging.DEBUG)
    try:
        logger.info("unscoped")
        logger.db_flush()
    finally:
        root.removeHandler(db_handler)

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

    AtoLogger._active_build_logger = active_logger

    root = logging.getLogger()
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

    assert len(captured) >= 1
    row = captured[-1]
    assert row.build_id == "build-1"
    assert row.stage == "stage-a"
    assert row.logger_name == plain.name
    assert row.message == "from third-party logger"


def test_db_handler_defaults_to_unscoped_without_active_context():
    captured: list[LogRow] = []
    default_unscoped = AtoLogger._make_db_logger(
        identifier="",
        context="",
        writer=lambda rows: captured.extend(rows),
        row_class=LogRow,
        id_field="build_id",
        context_field="stage",
        logger_name=f"atopile.db.test.default.{uuid.uuid4().hex}",
    )
    root = logging.getLogger()
    db_handler = DBLogHandler(level=logging.DEBUG)
    root.addHandler(db_handler)
    root.setLevel(logging.DEBUG)
    try:
        with patch.object(
            AtoLogger, "activate_unscoped", return_value=default_unscoped
        ):
            source_logger = logging.getLogger(f"noctx.test.{uuid.uuid4().hex}")
            source_logger.setLevel(logging.INFO)
            source_logger.info("should route to default unscoped")
        default_unscoped.db_flush()
    finally:
        root.removeHandler(db_handler)

    assert len(captured) >= 1
    row = captured[-1]
    assert row.build_id == ""
    assert row.message == "should route to default unscoped"


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
    test_logger = AtoLogger._make_db_logger(
        identifier="test-x",
        context="test-stage",
        writer=lambda rows: captured.extend(rows),
        row_class=LogRow,
        id_field="build_id",
        context_field="stage",
        logger_name=f"atopile.db.test.multictx.test.{uuid.uuid4().hex}",
    )

    root = logging.getLogger()
    db_handler = DBLogHandler(level=logging.DEBUG)
    AtoLogger._active_build_logger = build_logger
    AtoLogger._active_test_logger = test_logger
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


def test_activate_build_defaults_stage_to_blank():
    prev_build_id = os.environ.get("ATO_BUILD_ID")
    prev_timestamp = os.environ.get("ATO_BUILD_TIMESTAMP")
    os.environ["ATO_BUILD_ID"] = f"build-{uuid.uuid4().hex}"
    os.environ["ATO_BUILD_TIMESTAMP"] = "2026-02-14_00-00-00"

    try:
        logger = AtoLogger.activate_build(enable_database=True, stage=None)

        assert logger is not None
        assert logger.build_id == os.environ["ATO_BUILD_ID"]
        assert logger.stage_or_test_name == ""
        assert AtoLogger._active_build_logger is logger
        assert AtoLogger._active_test_logger is None
        assert AtoLogger._active_unscoped_logger is None
    finally:
        if prev_build_id is None:
            os.environ.pop("ATO_BUILD_ID", None)
        else:
            os.environ["ATO_BUILD_ID"] = prev_build_id
        if prev_timestamp is None:
            os.environ.pop("ATO_BUILD_TIMESTAMP", None)
        else:
            os.environ["ATO_BUILD_TIMESTAMP"] = prev_timestamp


def test_source_file_reports_original_callsite():
    captured: list[LogRow] = []
    logger = AtoLogger._make_db_logger(
        identifier="",
        context="source",
        writer=lambda rows: captured.extend(rows),
        row_class=LogRow,
        id_field="build_id",
        context_field="stage",
        logger_name=f"atopile.db.test.source.{uuid.uuid4().hex}",
    )
    logger.setLevel(logging.INFO)

    AtoLogger._active_unscoped_logger = logger

    root = logging.getLogger()
    db_handler = DBLogHandler(level=logging.DEBUG)
    root.addHandler(db_handler)
    root.setLevel(logging.DEBUG)
    try:
        logger.info("callsite check")
        logger.db_flush()
    finally:
        root.removeHandler(db_handler)

    assert len(captured) >= 1
    rows = [r for r in captured if r.message == "callsite check"]
    assert rows
    for row in rows:
        assert row.source_file is not None
        assert Path(row.source_file).name == "test_logging_db.py"
        assert row.source_line is not None
