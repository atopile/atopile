# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""
Test for linting over LSP.
"""

from threading import Event

from hamcrest import assert_that, is_

from .lsp_test_client import constants, defaults, session, utils

TEST_FILE_PATH = constants.TEST_DATA / "sample1" / "sample.py"
TEST_FILE_URI = utils.as_uri(str(TEST_FILE_PATH))
SERVER_INFO = utils.get_server_info_defaults()
TIMEOUT = 10  # 10 seconds


def test_linting_example():
    """Test to linting on file open."""
    contents = TEST_FILE_PATH.read_text()

    actual = []
    with session.LspSession() as ls_session:
        ls_session.initialize(defaults.VSCODE_DEFAULT_INITIALIZE)

        done = Event()

        def _handler(params):
            nonlocal actual
            actual = params
            done.set()

        ls_session.set_notification_callback(session.PUBLISH_DIAGNOSTICS, _handler)

        ls_session.notify_did_open(
            {
                "textDocument": {
                    "uri": TEST_FILE_URI,
                    "languageId": "python",
                    "version": 1,
                    "text": contents,
                }
            }
        )

        # wait for some time to receive all notifications
        done.wait(TIMEOUT)

        # TODO: Add your linter specific diagnostic result here
        expected = {
            "uri": TEST_FILE_URI,
            "diagnostics": [
                {
                    # "range": {
                    #     "start": {"line": 0, "character": 0},
                    #     "end": {"line": 0, "character": 0},
                    # },
                    # "message": "Missing module docstring",
                    # "severity": 3,
                    # "code": "C0114:missing-module-docstring",
                    "source": SERVER_INFO["name"],
                },
                {
                    # "range": {
                    #     "start": {"line": 2, "character": 6},
                    #     "end": {
                    #         "line": 2,
                    #         "character": 7,
                    #     },
                    # },
                    # "message": "Undefined variable 'x'",
                    # "severity": 1,
                    # "code": "E0602:undefined-variable",
                    "source": SERVER_INFO["name"],
                },
                {
                    # "range": {
                    #     "start": {"line": 0, "character": 0},
                    #     "end": {
                    #         "line": 0,
                    #         "character": 10,
                    #     },
                    # },
                    # "message": "Unused import sys",
                    # "severity": 2,
                    # "code": "W0611:unused-import",
                    "source": SERVER_INFO["name"],
                },
            ],
        }

    assert_that(actual, is_(expected))


def test_formatting_example():
    """Test formatting a python file."""
    FORMATTED_TEST_FILE_PATH = constants.TEST_DATA / "sample1" / "sample.py"
    UNFORMATTED_TEST_FILE_PATH = constants.TEST_DATA / "sample1" / "sample.unformatted"

    contents = UNFORMATTED_TEST_FILE_PATH.read_text()
    lines = contents.splitlines(keepends=False)

    actual = []
    with utils.PythonFile(contents, UNFORMATTED_TEST_FILE_PATH.parent) as pf:
        uri = utils.as_uri(str(pf.fullpath))

        with session.LspSession() as ls_session:
            ls_session.initialize()
            ls_session.notify_did_open(
                {
                    "textDocument": {
                        "uri": uri,
                        "languageId": "python",
                        "version": 1,
                        "text": contents,
                    }
                }
            )
            actual = ls_session.text_document_formatting(
                {
                    "textDocument": {"uri": uri},
                    # `options` is not used by black
                    "options": {"tabSize": 4, "insertSpaces": True},
                }
            )

    expected = [
        {
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": len(lines), "character": 0},
            },
            "newText": FORMATTED_TEST_FILE_PATH.read_text(),
        }
    ]

    assert_that(actual, is_(expected))
