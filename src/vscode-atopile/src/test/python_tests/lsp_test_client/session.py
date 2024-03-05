# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""
LSP session client for testing.
"""

import os
import subprocess
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event

from pyls_jsonrpc.dispatchers import MethodDispatcher
from pyls_jsonrpc.endpoint import Endpoint
from pyls_jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter

from .constants import PROJECT_ROOT
from .defaults import VSCODE_DEFAULT_INITIALIZE

LSP_EXIT_TIMEOUT = 5000


PUBLISH_DIAGNOSTICS = "textDocument/publishDiagnostics"
WINDOW_LOG_MESSAGE = "window/logMessage"
WINDOW_SHOW_MESSAGE = "window/showMessage"


# pylint: disable=too-many-instance-attributes
class LspSession(MethodDispatcher):
    """Send and Receive messages over LSP as a test LS Client."""

    def __init__(self, cwd=None, script=None):
        self.cwd = cwd if cwd else os.getcwd()
        # pylint: disable=consider-using-with
        self._thread_pool = ThreadPoolExecutor()
        self._sub = None
        self._writer = None
        self._reader = None
        self._endpoint = None
        self._notification_callbacks = {}
        self.script = (
            script if script else (PROJECT_ROOT / "bundled" / "tool" / "lsp_server.py")
        )

    def __enter__(self):
        """Context manager entrypoint.

        shell=True needed for pytest-cov to work in subprocess.
        """
        # pylint: disable=consider-using-with
        self._sub = subprocess.Popen(
            [sys.executable, str(self.script)],
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            bufsize=0,
            cwd=self.cwd,
            env=os.environ,
            shell="WITH_COVERAGE" in os.environ,
        )

        self._writer = JsonRpcStreamWriter(os.fdopen(self._sub.stdin.fileno(), "wb"))
        self._reader = JsonRpcStreamReader(os.fdopen(self._sub.stdout.fileno(), "rb"))

        dispatcher = {
            PUBLISH_DIAGNOSTICS: self._publish_diagnostics,
            WINDOW_SHOW_MESSAGE: self._window_show_message,
            WINDOW_LOG_MESSAGE: self._window_log_message,
        }
        self._endpoint = Endpoint(dispatcher, self._writer.write)
        self._thread_pool.submit(self._reader.listen, self._endpoint.consume)
        return self

    def __exit__(self, typ, value, _tb):
        self.shutdown(True)
        try:
            self._sub.terminate()
        except Exception:  # pylint:disable=broad-except
            pass
        self._endpoint.shutdown()
        self._thread_pool.shutdown()

    def initialize(
        self,
        initialize_params=None,
        process_server_capabilities=None,
    ):
        """Sends the initialize request to LSP server."""
        if initialize_params is None:
            initialize_params = VSCODE_DEFAULT_INITIALIZE
        server_initialized = Event()

        def _after_initialize(fut):
            if process_server_capabilities:
                process_server_capabilities(fut.result())
            self.initialized()
            server_initialized.set()

        self._send_request(
            "initialize",
            params=(
                initialize_params
                if initialize_params is not None
                else VSCODE_DEFAULT_INITIALIZE
            ),
            handle_response=_after_initialize,
        )

        server_initialized.wait()

    def initialized(self, initialized_params=None):
        """Sends the initialized notification to LSP server."""
        self._endpoint.notify("initialized", initialized_params or {})

    def shutdown(self, should_exit, exit_timeout=LSP_EXIT_TIMEOUT):
        """Sends the shutdown request to LSP server."""

        def _after_shutdown(_):
            if should_exit:
                self.exit_lsp(exit_timeout)

        self._send_request("shutdown", handle_response=_after_shutdown)

    def exit_lsp(self, exit_timeout=LSP_EXIT_TIMEOUT):
        """Handles LSP server process exit."""
        self._endpoint.notify("exit")
        assert self._sub.wait(exit_timeout) == 0

    def notify_did_change(self, did_change_params):
        """Sends did change notification to LSP Server."""
        self._send_notification("textDocument/didChange", params=did_change_params)

    def notify_did_save(self, did_save_params):
        """Sends did save notification to LSP Server."""
        self._send_notification("textDocument/didSave", params=did_save_params)

    def notify_did_open(self, did_open_params):
        """Sends did open notification to LSP Server."""
        self._send_notification("textDocument/didOpen", params=did_open_params)

    def notify_did_close(self, did_close_params):
        """Sends did close notification to LSP Server."""
        self._send_notification("textDocument/didClose", params=did_close_params)

    def text_document_formatting(self, formatting_params):
        """Sends text document references request to LSP server."""
        fut = self._send_request("textDocument/formatting", params=formatting_params)
        return fut.result()

    def text_document_code_action(self, code_action_params):
        """Sends text document code actions request to LSP server."""
        fut = self._send_request("textDocument/codeAction", params=code_action_params)
        return fut.result()

    def code_action_resolve(self, code_action_resolve_params):
        """Sends text document code actions resolve request to LSP server."""
        fut = self._send_request(
            "codeAction/resolve", params=code_action_resolve_params
        )
        return fut.result()

    def set_notification_callback(self, notification_name, callback):
        """Set custom LS notification handler."""
        self._notification_callbacks[notification_name] = callback

    def get_notification_callback(self, notification_name):
        """Gets callback if set or default callback for a given LS
        notification."""
        try:
            return self._notification_callbacks[notification_name]
        except KeyError:

            def _default_handler(_params):
                """Default notification handler."""

            return _default_handler

    def _publish_diagnostics(self, publish_diagnostics_params):
        """Internal handler for text document publish diagnostics."""
        return self._handle_notification(
            PUBLISH_DIAGNOSTICS, publish_diagnostics_params
        )

    def _window_log_message(self, window_log_message_params):
        """Internal handler for window log message."""
        return self._handle_notification(WINDOW_LOG_MESSAGE, window_log_message_params)

    def _window_show_message(self, window_show_message_params):
        """Internal handler for window show message."""
        return self._handle_notification(
            WINDOW_SHOW_MESSAGE, window_show_message_params
        )

    def _handle_notification(self, notification_name, params):
        """Internal handler for notifications."""
        fut = Future()

        def _handler():
            callback = self.get_notification_callback(notification_name)
            callback(params)
            fut.set_result(None)

        self._thread_pool.submit(_handler)
        return fut

    def _send_request(self, name, params=None, handle_response=lambda f: f.done()):
        """Sends {name} request to the LSP server."""
        fut = self._endpoint.request(name, params)
        fut.add_done_callback(handle_response)
        return fut

    def _send_notification(self, name, params=None):
        """Sends {name} notification to the LSP server."""
        self._endpoint.notify(name, params)
