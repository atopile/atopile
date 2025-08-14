# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""Implementation of tool support over LSP."""

from __future__ import annotations

import contextvars
import copy
import json
import logging
import os
import pathlib
import sys
import traceback
from dataclasses import dataclass, field
from importlib.metadata import version as get_package_version
from pathlib import Path
from typing import Any, Optional, Protocol, Sequence

from atopile import front_end
from atopile.config import find_project_dir
from atopile.datatypes import TypeRef
from atopile.errors import UserException
from atopile.parse_utils import get_src_info_from_token
from atopile.parser import AtoParser as ap
from faebryk.core.node import Node
from faebryk.libs.exceptions import DowngradedExceptionCollector, iter_leaf_exceptions

# **********************************************************
# Utils for interacting with the atopile front-end
# **********************************************************


def init_atopile_config(working_dir: Path) -> None:
    from atopile.config import config

    config.apply_options(entry=None, working_dir=working_dir)


# **********************************************************
# Update sys.path before importing any bundled libraries.
# **********************************************************
def update_sys_path(path_to_add: str, strategy: str) -> None:
    """Add given path to `sys.path`."""
    if path_to_add not in sys.path and os.path.isdir(path_to_add):
        if strategy == "useBundled":
            sys.path.insert(0, path_to_add)
        elif strategy == "fromEnvironment":
            sys.path.append(path_to_add)


# Ensure that we can import LSP libraries, and other bundled libraries.
update_sys_path(
    os.fspath(pathlib.Path(__file__).parent.parent / "libs"),
    os.getenv("LS_IMPORT_STRATEGY", "useBundled"),
)

# **********************************************************
# Imports needed for the language server goes below this.
# **********************************************************
# pylint: disable=wrong-import-position,import-error

import lsprotocol.types as lsp  # noqa: E402
from pygls import server, uris, workspace  # noqa: E402

import atopile.lsp.lsp_jsonrpc as jsonrpc  # noqa: E402
import atopile.lsp.lsp_utils as utils  # noqa: E402

WORKSPACE_SETTINGS = {}
GLOBAL_SETTINGS = {}
RUNNER = pathlib.Path(__file__).parent / "lsp_runner.py"
DISTRIBUTION_NAME = "atopile"

MAX_WORKERS = 5
# TODO: Update the language server name and version.
LSP_SERVER = server.LanguageServer(
    name=DISTRIBUTION_NAME,
    version=get_package_version(DISTRIBUTION_NAME),
    max_workers=MAX_WORKERS,
    # we don't have incremental parsing yet
    text_document_sync_kind=lsp.TextDocumentSyncKind.Full,
)


# **********************************************************
# Tool specific code goes below this.
# **********************************************************

# Reference:
#  LS Protocol:
#  https://microsoft.github.io/language-server-protocol/specifications/specification-3-16/
#
#  Sample implementations:
#  Pylint: https://github.com/microsoft/vscode-pylint/blob/main/bundled/tool
#  Black: https://github.com/microsoft/vscode-black-formatter/blob/main/bundled/tool
#  isort: https://github.com/microsoft/vscode-isort/blob/main/bundled/tool

# e.g, TOOL_MODULE = "pylint"
TOOL_MODULE = "atopile"

# e.g, TOOL_DISPLAY = "Pylint"
TOOL_DISPLAY = "atopile"

# all scenarios.
TOOL_ARGS = []  # default arguments always passed to your tool.


class URIProtocol(Protocol):
    class TextDocument:
        uri: str

    text_document: TextDocument


def get_file(uri: str) -> Path:
    document = LSP_SERVER.workspace.get_text_document(uri)
    return Path(document.path)


def get_file_contents(uri: str) -> tuple[Path, str]:
    document = LSP_SERVER.workspace.get_text_document(uri)
    file_path = Path(document.path)
    source_text = document.source
    return file_path, source_text


def log(msg: Any):
    print(msg, file=sys.stderr)


# **********************************************************
# Linting features start here
# **********************************************************

GRAPHS: dict[str, dict[TypeRef, Node]] = {}
ACTIVE_BUILD_TARGET: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "ACTIVE_BUILD_TARGET", default=None
)


def _convert_exc_to_diagnostic(
    exc: UserException, severity: lsp.DiagnosticSeverity = lsp.DiagnosticSeverity.Error
) -> tuple[Path | None, lsp.Diagnostic]:
    # default to the start of the file
    start_file_path = None
    start_line, start_col = 0, 0
    stop_line, stop_col = 0, 0

    if exc.origin_start is not None:
        start_file_path, start_line, start_col = get_src_info_from_token(
            exc.origin_start
        )

        if exc.origin_stop is not None:
            stop_line, stop_col = (
                exc.origin_stop.line,
                exc.origin_stop.column + len(exc.origin_stop.text),
            )
        else:
            # just extend to the next line
            stop_line, stop_col = start_line + 1, 0

    # convert from 1-indexed (ANTLR) to 0-indexed (LSP)
    start_line = max(start_line - 1, 0)
    stop_line = max(stop_line - 1, 0)

    return Path(start_file_path) if start_file_path else None, lsp.Diagnostic(
        range=lsp.Range(
            start=lsp.Position(line=start_line, character=start_col),
            end=lsp.Position(line=stop_line, character=stop_col),
        ),
        message=exc.message,
        severity=severity,
        code=exc.code,
        source=TOOL_DISPLAY,
        # TODO: tags
    )


def _paths_are_equivalent(path1: Path, path2: Path) -> bool:
    return path1.resolve() == path2.resolve()


def _get_diagnostics(uri: str, identifier: str | None = None) -> list[lsp.Diagnostic]:
    """
    Get static diagnostics for a given URI and identifier.

    TODO: caching
    FIXME: combine with _build_document
    """
    file_path, source_text = get_file_contents(uri)
    exc_diagnostics = []

    with DowngradedExceptionCollector(UserException) as collector:
        try:
            front_end.bob.try_build_all_from_text(source_text, file_path)
        except* UserException as e:
            exc_diagnostics = [
                _convert_exc_to_diagnostic(error) for error in iter_leaf_exceptions(e)
            ]

        warning_diagnostics = [
            _convert_exc_to_diagnostic(error, severity=lsp.DiagnosticSeverity.Warning)
            for error, severity in collector
            if severity == logging.WARNING
        ]

    document_file_path = get_file(uri)

    return [
        diag
        for diag_file_path, diag in exc_diagnostics + warning_diagnostics
        if diag_file_path is None
        or _paths_are_equivalent(document_file_path, diag_file_path)
    ]


def _build_document(uri: str, text: str) -> None:
    file_path = get_file(uri)
    init_atopile_config(file_path.parent)

    context = front_end.bob.index_text(text, file_path)

    # TOOD: do something smarter here (only distinct trees?)
    GRAPHS.setdefault(uri, {})
    for ref, ctx in context.refs.items():
        match ctx:
            case ap.AtoParser.BlockdefContext():
                try:
                    # try the single-node version first, in case that's all we can build
                    GRAPHS[uri][TypeRef.from_one("__" + str(ref))] = (
                        front_end.bob.build_node(text, file_path, ref)
                    )

                    front_end.bob.reset()

                    GRAPHS[uri][ref] = front_end.bob.build_text(text, file_path, ref)
                except* UserException as excs:
                    msg = f"Error(s) building {uri}:{ref}:\n"
                    for exc in iter_leaf_exceptions(excs):
                        msg += f"  {exc.message}\n"
                    log_error(msg)
                except* Exception:
                    import traceback

                    log_error(f"Error building {uri}:{ref}:\n{traceback.format_exc()}")
                finally:
                    front_end.bob.reset()

            case _:  # Node or ImportPlaceholder
                try:
                    GRAPHS[uri][TypeRef.from_one(name="__import__" + str(ref))] = (
                        front_end.bob.build_node(text, file_path, ref)
                    )
                except TypeError as ex:
                    if "missing" not in str(ex):
                        raise
                    pass
                except Exception:
                    import traceback

                    log_error(f"Error building {uri}:{ref}:\n{traceback.format_exc()}")
                finally:
                    front_end.bob.reset()


@dataclass
class DidChangeBuildTargetParams:
    buildTarget: str | None = field(default=None)


# TODO: implement something useful
@LSP_SERVER.feature("atopile/didChangeBuildTarget")
def on_did_change_build_target(params: DidChangeBuildTargetParams) -> None: ...


@LSP_SERVER.feature(
    lsp.TEXT_DOCUMENT_DIAGNOSTIC,
    lsp.DiagnosticOptions(
        identifier=TOOL_DISPLAY,
        inter_file_dependencies=True,
        workspace_diagnostics=False,
    ),
)
def on_document_diagnostic(params: lsp.DocumentDiagnosticParams) -> None:
    """Handle document diagnostic request."""
    LSP_SERVER.publish_diagnostics(
        params.text_document.uri, _get_diagnostics(params.text_document.uri)
    )


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def on_document_did_open(params: lsp.DidOpenTextDocumentParams) -> None:
    """Handle document open request."""
    _build_document(params.text_document.uri, params.text_document.text)
    LSP_SERVER.publish_diagnostics(
        params.text_document.uri, _get_diagnostics(params.text_document.uri)
    )


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def on_document_did_change(params: lsp.DidChangeTextDocumentParams) -> None:
    """Handle document change request."""
    _build_document(
        params.text_document.uri,
        LSP_SERVER.workspace.get_text_document(params.text_document.uri).source,
    )
    # TODO: debounce
    LSP_SERVER.publish_diagnostics(
        params.text_document.uri, _get_diagnostics(params.text_document.uri)
    )


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def on_document_did_save(params: lsp.DidSaveTextDocumentParams) -> None:
    """Handle document save request."""
    LSP_SERVER.publish_diagnostics(
        params.text_document.uri, _get_diagnostics(params.text_document.uri)
    )


def _span_to_lsp_range(span: front_end.Span) -> lsp.Range:
    return lsp.Range(
        start=lsp.Position(line=span.start.line - 1, character=span.start.col),
        end=lsp.Position(line=span.end.line - 1, character=span.end.col),
    )


def _query_params(params: lsp.HoverParams | lsp.DefinitionParams) -> dict[str, Any]:
    return {
        "file_path": f"file:{get_file(params.text_document.uri)}",
        "line": params.position.line + 1,  # 0-indexed -> 1-indexed
        "col": params.position.character,
    }


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_HOVER)
def on_document_hover(params: lsp.HoverParams) -> lsp.Hover | None:
    """Handle document hover request."""
    for root in GRAPHS.get(params.text_document.uri, {}).values():
        for _, trait in root.iter_children_with_trait(front_end.from_dsl):
            if (span := trait.query_references(**_query_params(params))) is not None:
                return lsp.Hover(
                    contents=lsp.MarkupContent(
                        kind=lsp.MarkupKind.Markdown, value=trait.hover_text
                    ),
                    range=_span_to_lsp_range(span),
                )


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DEFINITION)
def on_document_definition(params: lsp.DefinitionParams) -> lsp.LocationLink | None:
    """Handle document definition request."""
    for root in GRAPHS.get(params.text_document.uri, {}).values():
        for _, trait in root.iter_children_with_trait(front_end.from_dsl):
            if (spans := trait.query_definition(**_query_params(params))) is not None:
                origin_span, target_span, target_selection_span = spans
                return lsp.LocationLink(
                    target_uri=target_span.start.file,
                    target_range=_span_to_lsp_range(target_span),
                    target_selection_range=_span_to_lsp_range(target_selection_span),
                    origin_selection_range=_span_to_lsp_range(origin_span),
                )


# TODO: if you want to handle setting specific severity for your linter
# in a user configurable way, then look at look at how it is implemented
# for `pylint` extension from our team.
# Pylint: https://github.com/microsoft/vscode-pylint
# Follow the flow of severity from the settings in package.json to the server.
def _get_severity(*_codes: list[str]) -> lsp.DiagnosticSeverity:
    # TODO: All reported issues from linter are treated as warning.
    # change it as appropriate for your linter.
    return lsp.DiagnosticSeverity.Error


# **********************************************************
# Required Language Server Initialization and Exit handlers.
# **********************************************************
@LSP_SERVER.feature(lsp.INITIALIZE)
def initialize(params: lsp.InitializeParams) -> None:
    """LSP handler for initialize request."""
    log_to_output(f"CWD: {os.getcwd()}")

    paths = "\r\n   ".join(sys.path)
    log_to_output(f"sys.path used to run:\r\n   {paths}")

    if params.initialization_options is not None:
        GLOBAL_SETTINGS.update(
            **params.initialization_options.get("globalSettings", {})
        )

        settings = params.initialization_options["settings"]
        _update_workspace_settings(settings)
        log_to_output(
            f"Settings used to run:{json.dumps(settings, indent=4, ensure_ascii=False)}"
        )

    log_to_output(
        f"Global settings:{json.dumps(GLOBAL_SETTINGS, indent=4, ensure_ascii=False)}"
    )

    log_to_output(
        f"Workspace settings:"
        f"{json.dumps(WORKSPACE_SETTINGS, indent=4, ensure_ascii=False)}"
    )

    workspace_dir = Path(WORKSPACE_SETTINGS.get("workspaceFS", os.getcwd()))
    project_dir = find_project_dir(start=workspace_dir)
    working_dir = project_dir or workspace_dir

    log_to_output(f"Initializing atopile config for `{working_dir}`")
    init_atopile_config(working_dir)


@LSP_SERVER.feature(lsp.EXIT)
def on_exit(_params: Optional[Any] = None) -> None:
    """Handle clean up on exit."""
    jsonrpc.shutdown_json_rpc()


@LSP_SERVER.feature(lsp.SHUTDOWN)
def on_shutdown(_params: Optional[Any] = None) -> None:
    """Handle clean up on shutdown."""
    jsonrpc.shutdown_json_rpc()


def _get_global_defaults():
    return {
        "path": GLOBAL_SETTINGS.get("path", []),
        "interpreter": GLOBAL_SETTINGS.get("interpreter", [sys.executable]),
        "args": GLOBAL_SETTINGS.get("args", []),
        "importStrategy": GLOBAL_SETTINGS.get("importStrategy", "useBundled"),
        "showNotifications": GLOBAL_SETTINGS.get("showNotifications", "off"),
    }


def _update_workspace_settings(settings):
    if not settings:
        key = os.getcwd()
        WORKSPACE_SETTINGS[key] = {
            "cwd": key,
            "workspaceFS": key,
            "workspace": uris.from_fs_path(key),
            **_get_global_defaults(),
        }
        return

    for setting in settings:
        key = uris.to_fs_path(setting["workspace"])
        WORKSPACE_SETTINGS[key] = {
            "cwd": key,
            **setting,
            "workspaceFS": key,
        }


def _get_settings_by_path(file_path: pathlib.Path):
    workspaces = {s["workspaceFS"] for s in WORKSPACE_SETTINGS.values()}

    while file_path != file_path.parent:
        str_file_path = str(file_path)
        if str_file_path in workspaces:
            return WORKSPACE_SETTINGS[str_file_path]
        file_path = file_path.parent

    setting_values = list(WORKSPACE_SETTINGS.values())
    return setting_values[0]


def _get_document_key(document: workspace.Document):
    if WORKSPACE_SETTINGS:
        document_workspace = pathlib.Path(document.path)
        workspaces = {s["workspaceFS"] for s in WORKSPACE_SETTINGS.values()}

        # Find workspace settings for the given file.
        while document_workspace != document_workspace.parent:
            if str(document_workspace) in workspaces:
                return str(document_workspace)
            document_workspace = document_workspace.parent

    return None


def _get_settings_by_document(document: workspace.Document | None):
    if document is None or document.path is None:
        return list(WORKSPACE_SETTINGS.values())[0]

    key = _get_document_key(document)
    if key is None:
        # This is either a non-workspace file or there is no workspace.
        key = os.fspath(pathlib.Path(document.path).parent)
        return {
            "cwd": key,
            "workspaceFS": key,
            "workspace": uris.from_fs_path(key),
            **_get_global_defaults(),
        }

    return WORKSPACE_SETTINGS[str(key)]


# *****************************************************
# Internal execution APIs.
# *****************************************************
def _run_tool_on_document(
    document: workspace.Document,
    use_stdin: bool = False,
    extra_args: Optional[Sequence[str]] = None,
) -> utils.RunResult | None:
    """Runs tool on the given document.

    if use_stdin is true then contents of the document is passed to the
    tool via stdin.
    """
    if extra_args is None:
        extra_args = []
    if str(document.uri).startswith("vscode-notebook-cell"):
        # TODO: Decide on if you want to skip notebook cells.
        # Skip notebook cells
        return None

    if utils.is_stdlib_file(document.path):
        # TODO: Decide on if you want to skip standard library files.
        # Skip standard library python files.
        return None

    # deep copy here to prevent accidentally updating global settings.
    settings = copy.deepcopy(_get_settings_by_document(document))

    code_workspace = settings["workspaceFS"]
    cwd = settings["cwd"]

    use_path = False
    use_rpc = False
    if settings["path"]:
        # 'path' setting takes priority over everything.
        use_path = True
        argv = settings["path"]
    elif settings["interpreter"] and not utils.is_current_interpreter(
        settings["interpreter"][0]
    ):
        # If there is a different interpreter set use JSON-RPC to the subprocess
        # running under that interpreter.
        argv = [TOOL_MODULE]
        use_rpc = True
    else:
        # if the interpreter is same as the interpreter running this
        # process then run as module.
        argv = [TOOL_MODULE]

    argv += TOOL_ARGS + settings["args"] + extra_args

    if use_stdin:
        # TODO: update these to pass the appropriate arguments to provide document contents # noqa: E501  # pre-existing
        # to tool via stdin.
        # For example, for pylint args for stdin looks like this:
        #     pylint --from-stdin <path>
        # Here `--from-stdin` path is used by pylint to make decisions on the file contents # noqa: E501  # pre-existing
        # that are being processed. Like, applying exclusion rules.
        # It should look like this when you pass it:
        #     argv += ["--from-stdin", document.path]
        # Read up on how your tool handles contents via stdin. If stdin is not supported use # noqa: E501  # pre-existing
        # set use_stdin to False, or provide path, what ever is appropriate for your tool. # noqa: E501  # pre-existing
        argv += []
    else:
        argv += [document.path]

    if use_path:
        # This mode is used when running executables.
        log_to_output(" ".join(argv))
        log_to_output(f"CWD Server: {cwd}")
        result = utils.run_path(
            argv=argv,
            use_stdin=use_stdin,
            cwd=cwd,
            source=document.source.replace("\r\n", "\n"),
        )
        if result.stderr:
            log_to_output(result.stderr)
    elif use_rpc:
        # This mode is used if the interpreter running this server is different from
        # the interpreter used for running this server.
        log_to_output(" ".join(settings["interpreter"] + ["-m"] + argv))
        log_to_output(f"CWD Linter: {cwd}")

        result = jsonrpc.run_over_json_rpc(
            workspace=code_workspace,
            interpreter=settings["interpreter"],
            module=TOOL_MODULE,
            argv=argv,
            use_stdin=use_stdin,
            cwd=cwd,
            source=document.source,
        )
        if result.exception:
            log_error(result.exception)
            result = utils.RunResult(result.stdout, result.stderr)
        elif result.stderr:
            log_to_output(result.stderr)
    else:
        # In this mode the tool is run as a module in the same process as the language server. # noqa: E501  # pre-existing
        log_to_output(" ".join([sys.executable, "-m"] + argv))
        log_to_output(f"CWD Linter: {cwd}")
        # This is needed to preserve sys.path, in cases where the tool modifies
        # sys.path and that might not work for this scenario next time around.

        # with utils.substitute_attr(sys, "path", sys.path[:]):
        #     try:
        #         # TODO: `utils.run_module` is equivalent to running `python -m atopile`. # noqa: E501  # pre-existing
        #         # If your tool supports a programmatic API then replace the function below # noqa: E501  # pre-existing
        #         # with code for your tool. You can also use `utils.run_api` helper, which # noqa: E501  # pre-existing
        #         # handles changing working directories, managing io streams, etc.
        #         # Also update `_run_tool` function and `utils.run_module` in `lsp_runner.py`. # noqa: E501  # pre-existing
        #         result = utils.run_module(
        #             module=TOOL_MODULE,
        #             argv=argv,
        #             use_stdin=use_stdin,
        #             cwd=cwd,
        #             source=document.source,
        #         )
        #     except Exception:
        #         log_error(traceback.format_exc(chain=True))
        #         raise

        if result.stderr:
            log_to_output(result.stderr)

    log_to_output(f"{document.uri} :\r\n{result.stdout}")
    return result


def _run_tool(extra_args: Sequence[str]) -> utils.RunResult:
    """Runs tool."""
    # deep copy here to prevent accidentally updating global settings.
    settings = copy.deepcopy(_get_settings_by_document(None))

    code_workspace = settings["workspaceFS"]
    cwd = settings["workspaceFS"]

    use_path = False
    use_rpc = False
    if len(settings["path"]) > 0:
        # 'path' setting takes priority over everything.
        use_path = True
        argv = settings["path"]
    elif len(settings["interpreter"]) > 0 and not utils.is_current_interpreter(
        settings["interpreter"][0]
    ):
        # If there is a different interpreter set use JSON-RPC to the subprocess
        # running under that interpreter.
        argv = [TOOL_MODULE]
        use_rpc = True
    else:
        # if the interpreter is same as the interpreter running this
        # process then run as module.
        argv = [TOOL_MODULE]

    argv += extra_args

    if use_path:
        # This mode is used when running executables.
        log_to_output(" ".join(argv))
        log_to_output(f"CWD Server: {cwd}")
        result = utils.run_path(argv=argv, use_stdin=True, cwd=cwd)
        if result.stderr:
            log_to_output(result.stderr)
    elif use_rpc:
        # This mode is used if the interpreter running this server is different from
        # the interpreter used for running this server.
        log_to_output(" ".join(settings["interpreter"] + ["-m"] + argv))
        log_to_output(f"CWD Linter: {cwd}")
        result = jsonrpc.run_over_json_rpc(
            workspace=code_workspace,
            interpreter=settings["interpreter"],
            module=TOOL_MODULE,
            argv=argv,
            use_stdin=True,
            cwd=cwd,
        )
        if result.exception:
            log_error(result.exception)
            result = utils.RunResult(result.stdout, result.stderr)
        elif result.stderr:
            log_to_output(result.stderr)
    else:
        # In this mode the tool is run as a module in the same process as the language server. # noqa: E501  # pre-existing
        log_to_output(" ".join([sys.executable, "-m"] + argv))
        log_to_output(f"CWD Linter: {cwd}")
        # This is needed to preserve sys.path, in cases where the tool modifies
        # sys.path and that might not work for this scenario next time around.
        with utils.substitute_attr(sys, "path", sys.path[:]):
            try:
                # TODO: `utils.run_module` is equivalent to running `python -m atopile`.
                # If your tool supports a programmatic API then replace the function below # noqa: E501  # pre-existing
                # with code for your tool. You can also use `utils.run_api` helper, which # noqa: E501  # pre-existing
                # handles changing working directories, managing io streams, etc.
                # Also update `_run_tool_on_document` function and `utils.run_module` in `lsp_runner.py`. # noqa: E501  # pre-existing
                result = utils.run_module(
                    module=TOOL_MODULE, argv=argv, use_stdin=True, cwd=cwd
                )
            except Exception:
                log_error(traceback.format_exc(chain=True))
                raise
        if result.stderr:
            log_to_output(result.stderr)

    log_to_output(f"\r\n{result.stdout}\r\n")
    return result


# *****************************************************
# Logging and notification.
# *****************************************************
def log_to_output(
    message: str, msg_type: lsp.MessageType = lsp.MessageType.Log
) -> None:
    LSP_SERVER.show_message_log("LSP: " + message, msg_type)


def log_error(message: str) -> None:
    LSP_SERVER.show_message_log(message, lsp.MessageType.Error)
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["onError", "onWarning", "always"]:
        LSP_SERVER.show_message(message, lsp.MessageType.Error)


def log_warning(message: str) -> None:
    LSP_SERVER.show_message_log(message, lsp.MessageType.Warning)
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["onWarning", "always"]:
        LSP_SERVER.show_message(message, lsp.MessageType.Warning)


def log_always(message: str) -> None:
    LSP_SERVER.show_message_log(message, lsp.MessageType.Info)
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["always"]:
        LSP_SERVER.show_message(message, lsp.MessageType.Info)


# *****************************************************
# Start the server.
# *****************************************************
if __name__ == "__main__":
    LSP_SERVER.start_io()
