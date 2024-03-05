# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""Implementation of tool support over LSP."""
from __future__ import annotations

import copy
import json
import os
import pathlib
import sys
import traceback
from pathlib import Path
from typing import Any, Optional, Sequence

import atopile.address
import atopile.config
import atopile.datatypes
import atopile.errors
import atopile.front_end
import atopile.parse
import atopile.parse_utils

# **********************************************************
# Utils for interacting with the atopile front-end
# **********************************************************

_line_to_def_block: dict[Path, dict[int, atopile.address.AddrStr]] = {}


def _reset_caches(file: Path):
    """Remove a file from the cache."""
    if file in atopile.parse.parser.cache:
        del atopile.parse.parser.cache[file]

    if file in _line_to_def_block:
        del _line_to_def_block[file]

    # TODO: only clear these caches of what's been invalidated
    file_str = str(file)
    to_clear = [addr for addr in atopile.front_end.scoop._output_cache if addr.startswith(file_str)]
    for addr in to_clear:
        del atopile.front_end.scoop._output_cache[addr]

    to_clear = [addr for addr in atopile.front_end.dizzy._output_cache if addr.startswith(file_str)]
    for addr in to_clear:
        del atopile.front_end.dizzy._output_cache[addr]

    atopile.front_end.lofty._output_cache.clear()


def _index_class_defs_by_line(file: Path):
    """Index class definitions in a given file by the line number"""
    _line_to_def_block[file] = {}
    addrs = atopile.front_end.scoop.ingest_file(file)

    for addr in addrs:
        if addr == str(file):
            continue
        try:
            atopile.front_end.lofty.get_instance(addr)
        except atopile.errors.AtoError as ex:
            log_warning(str(ex))
            continue

        # FIXME: we shouldn't be entangling this
        # code w/ the front-end so much
        try:
            cls_def = atopile.front_end.scoop.get_obj_def(addr)
            _, start_line, _, stop_line, _ = atopile.parse_utils.get_src_info_from_ctx(
                cls_def.src_ctx.block()
            )
        except AttributeError:
            continue

        for i in range(start_line + 1, stop_line + 1):
            _line_to_def_block[file][i] = cls_def.address


def _get_def_addr_from_line(file: Path, line: int) -> Optional[atopile.address.AddrStr]:
    """Get the class definition from a line number"""
    if file not in _line_to_def_block or not _line_to_def_block[file]:
        _index_class_defs_by_line(file)
    return _line_to_def_block[file].get(line, None)


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
import lsp_jsonrpc as jsonrpc  # noqa: E402
import lsp_utils as utils  # noqa: E402
import lsprotocol.types as lsp  # noqa: E402
from pygls import server, uris, workspace  # noqa: E402

WORKSPACE_SETTINGS = {}
GLOBAL_SETTINGS = {}
RUNNER = pathlib.Path(__file__).parent / "lsp_runner.py"

MAX_WORKERS = 5
# TODO: Update the language server name and version.
LSP_SERVER = server.LanguageServer(
    name="atopile", version="<server version>", max_workers=MAX_WORKERS
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


# TODO: If your tool is a linter then update this section.
# Delete "Linting features" section if your tool is NOT a linter.
# **********************************************************
# Linting features start here
# **********************************************************

#  See `pylint` implementation for a full featured linter extension:
#  Pylint: https://github.com/microsoft/vscode-pylint/blob/main/bundled/tool


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_COMPLETION, lsp.CompletionOptions(trigger_characters=["."]),)
def completions(params: Optional[lsp.CompletionParams] = None) -> lsp.CompletionList:
    """Handler for completion requests."""
    if not params.text_document.uri.startswith("file://"):
        return lsp.CompletionList(is_incomplete=False, items=[])

    document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)

    file = Path(document.path)
    try:
        atopile.config.get_project_context()
    except ValueError:
        atopile.config.set_project_context(atopile.config.ProjectContext.from_path(file))

    word = utils.cursor_word(document, params.position)
    class_addr = _get_def_addr_from_line(file, params.position.line) or str(file)
    items: list[lsp.CompletionItem] = []

    instance_addr = atopile.address.add_instances(class_addr, word.split(".")[:-1])
    try:
        instance = atopile.front_end.lofty.get_instance(instance_addr)
    except (KeyError, atopile.errors.AtoError):
        pass
    else:
        for child, assignment in instance.assignments.items():
            items.append(lsp.CompletionItem(label=child, kind=lsp.CompletionItemKind.Property, detail=assignment[0].given_type))

        for child in instance.children:
            items.append(lsp.CompletionItem(label=child, kind=lsp.CompletionItemKind.Method))

    # Class Defs
    # FIXME: this is a hack to check whether something could not be class-def
    if "." not in word:
        try:
            class_ctx = atopile.front_end.scoop.get_obj_def(class_addr)
        except (KeyError, atopile.errors.AtoError):
            pass
        else:
            closure_contexts = [class_ctx]
            if class_ctx.closure:
                closure_contexts.extend(class_ctx.closure)

            for closure_ctx in closure_contexts:

                for cls_ref in closure_ctx.local_defs:
                    items.append(lsp.CompletionItem(label=cls_ref[0], kind=lsp.CompletionItemKind.Class))

                for imp_ref in closure_ctx.imports:
                    items.append(lsp.CompletionItem(label=imp_ref[0], kind=lsp.CompletionItemKind.Class))

    return lsp.CompletionList(is_incomplete=False, items=items,)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DEFINITION)
def goto_definition(params: Optional[lsp.DefinitionParams] = None) -> Optional[lsp.Location]:
    """Handler for goto definition."""
    if not params.text_document.uri.startswith("file://"):
        return lsp.CompletionList(is_incomplete=False, items=[])

    document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)

    file = Path(document.path)
    try:
        atopile.config.get_project_context()
    except ValueError:
        atopile.config.set_project_context(atopile.config.ProjectContext.from_path(file))

    class_addr = _get_def_addr_from_line(file, params.position.line)
    if not class_addr:
        class_addr = str(file)

    word, range_ = utils.cursor_word_and_range(document, params.position)
    try:
        word = word[:word.index(".", params.position.character - range_.start.character)]
    except ValueError:
        pass

    # See if it's an instance
    instance_addr = atopile.address.add_instances(class_addr, word.split("."))
    src_ctx = None
    try:
        src_ctx = atopile.front_end.lofty.get_instance(instance_addr).src_ctx
    except (KeyError, atopile.errors.AtoError, AttributeError):
        # See if it's a Class instead
        pass

    # See if it's a class
    try:
        src_ctx = atopile.front_end.scoop.get_obj_def(
            atopile.front_end.lookup_class_in_closure(
                atopile.front_end.scoop.get_obj_def(class_addr),
                atopile.datatypes.Ref(word.split("."))
            )
        ).src_ctx
    except (KeyError, atopile.errors.AtoError, AttributeError):
        pass

    try:
        file_path, start_line, start_col, stop_line, stop_col = atopile.parse_utils.get_src_info_from_ctx(src_ctx)
    except AttributeError:
        return
    else:
        return lsp.Location(
            "file://" + str(file_path),
            lsp.Range(
                lsp.Position(start_line - 1, start_col),
                lsp.Position(stop_line - 1, stop_col)
            )
        )


# TODO: we don't currently have good enough cache management to support dynamic parsing
# @LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
# def did_change(params: lsp.DidChangeTextDocumentParams) -> None:
#     """LSP handler for textDocument/didOpen request."""
#     document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)

#     # naive method to real-time lint on every keypress
#     _linting_helper(document)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(params: lsp.DidOpenTextDocumentParams) -> None:
    """LSP handler for textDocument/didOpen request."""
    if not params.text_document.uri.startswith("file://"):
        return lsp.CompletionList(is_incomplete=False, items=[])

    document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)

    file = Path(document.path)
    try:
        atopile.config.get_project_context()
    except ValueError:
        atopile.config.set_project_context(atopile.config.ProjectContext.from_path(file))

    _index_class_defs_by_line(file)


# TODO: remove me if we don't have a purpose for it
# @LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
# def did_close(params: lsp.DidCloseTextDocumentParams) -> None:
#     """LSP handler for textDocument/didClose request."""
#     #document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
#     # Publishing empty diagnostics to clear the entries for this file.
#     #LSP_SERVER.publish_diagnostics(document.uri, [])
#     log_to_output("did close")


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def did_save(params: lsp.DidSaveTextDocumentParams) -> None:
    """LSP handler for textDocument/didSave request."""
    if not params.text_document.uri.startswith("file://"):
        return lsp.CompletionList(is_incomplete=False, items=[])

    document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)

    file = Path(document.path)

    _reset_caches(file)
    _index_class_defs_by_line(file)


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
    log_to_output(f"CWD Server: {os.getcwd()}")

    paths = "\r\n   ".join(sys.path)
    log_to_output(f"sys.path used to run Server:\r\n   {paths}")

    GLOBAL_SETTINGS.update(**params.initialization_options.get("globalSettings", {}))

    settings = params.initialization_options["settings"]
    _update_workspace_settings(settings)
    log_to_output(
        f"Settings used to run Server:\r\n{json.dumps(settings, indent=4, ensure_ascii=False)}\r\n"
    )
    log_to_output(
        f"Global settings:\r\n{json.dumps(GLOBAL_SETTINGS, indent=4, ensure_ascii=False)}\r\n"
    )


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
        # TODO: update these to pass the appropriate arguments to provide document contents
        # to tool via stdin.
        # For example, for pylint args for stdin looks like this:
        #     pylint --from-stdin <path>
        # Here `--from-stdin` path is used by pylint to make decisions on the file contents
        # that are being processed. Like, applying exclusion rules.
        # It should look like this when you pass it:
        #     argv += ["--from-stdin", document.path]
        # Read up on how your tool handles contents via stdin. If stdin is not supported use
        # set use_stdin to False, or provide path, what ever is appropriate for your tool.
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
        # In this mode the tool is run as a module in the same process as the language server.
        log_to_output(" ".join([sys.executable, "-m"] + argv))
        log_to_output(f"CWD Linter: {cwd}")
        # This is needed to preserve sys.path, in cases where the tool modifies
        # sys.path and that might not work for this scenario next time around.

        # with utils.substitute_attr(sys, "path", sys.path[:]):
        #     try:
        #         # TODO: `utils.run_module` is equivalent to running `python -m atopile`.
        #         # If your tool supports a programmatic API then replace the function below
        #         # with code for your tool. You can also use `utils.run_api` helper, which
        #         # handles changing working directories, managing io streams, etc.
        #         # Also update `_run_tool` function and `utils.run_module` in `lsp_runner.py`.
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
        # In this mode the tool is run as a module in the same process as the language server.
        log_to_output(" ".join([sys.executable, "-m"] + argv))
        log_to_output(f"CWD Linter: {cwd}")
        # This is needed to preserve sys.path, in cases where the tool modifies
        # sys.path and that might not work for this scenario next time around.
        with utils.substitute_attr(sys, "path", sys.path[:]):
            try:
                # TODO: `utils.run_module` is equivalent to running `python -m atopile`.
                # If your tool supports a programmatic API then replace the function below
                # with code for your tool. You can also use `utils.run_api` helper, which
                # handles changing working directories, managing io streams, etc.
                # Also update `_run_tool_on_document` function and `utils.run_module` in `lsp_runner.py`.
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
    LSP_SERVER.show_message_log(message, msg_type)


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
