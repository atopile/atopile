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
import re
import sys
import traceback
from dataclasses import dataclass, field
from importlib.metadata import version as get_package_version
from pathlib import Path
from typing import Any, Optional, Protocol, Sequence

from atopile import front_end
from atopile.config import find_project_dir
from atopile.datatypes import FieldRef, ReferencePartType, TypeRef
from atopile.errors import UserException
from atopile.parse_utils import get_src_info_from_token
from atopile.parser import AtoParser as ap
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.core.parameter import Parameter
from faebryk.core.trait import Trait, TraitImpl
from faebryk.libs.exceptions import DowngradedExceptionCollector, iter_leaf_exceptions
from faebryk.libs.util import debounce, not_none, once

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
from pygls import uris, workspace  # noqa: E402
from pygls.lsp.server import LanguageServer  # noqa: E402

import atopile.lsp.lsp_jsonrpc as jsonrpc  # noqa: E402
import atopile.lsp.lsp_utils as utils  # noqa: E402

WORKSPACE_SETTINGS = {}
GLOBAL_SETTINGS = {}
RUNNER = pathlib.Path(__file__).parent / "lsp_runner.py"
DISTRIBUTION_NAME = "atopile"

MAX_WORKERS = 5
# TODO: Update the language server name and version.
LSP_SERVER = LanguageServer(
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
    try:
        path = Path(uri)
        if path.exists():
            return path
    except Exception:
        pass
    document = LSP_SERVER.workspace.get_text_document(uri)
    return Path(document.path)


def get_file_contents(uri: str) -> tuple[Path, str]:
    try:
        path = Path(uri)
        if path.exists():
            return path, path.read_text(encoding="utf-8")
    except Exception:
        pass
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
    log_warning(f"rebuilding document {uri}")

    try:
        init_atopile_config(file_path.parent)
    except Exception:
        # log_warning(f"Error initializing atopile config: {e}")
        pass

    context = front_end.bob.index_text(text, file_path)

    # TOOD: do something smarter here (only distinct trees?)
    GRAPHS.setdefault(uri, {})
    for ref, ctx in context.refs.items():
        match ctx:
            case ap.AtoParser.BlockdefContext():
                try:
                    # try the single-node version first, in case that's all we can build
                    GRAPHS[uri][TypeRef.from_one("__node_" + str(ref))] = (
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
    LSP_SERVER.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(
            params.text_document.uri, _get_diagnostics(params.text_document.uri)
        )
    )


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def on_document_did_open(params: lsp.DidOpenTextDocumentParams) -> None:
    """Handle document open request."""
    _build_document(params.text_document.uri, params.text_document.text)
    LSP_SERVER.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(
            params.text_document.uri, _get_diagnostics(params.text_document.uri)
        )
    )


# TODO debounce per file
@debounce(2)
def _handle_document_did_change(params: lsp.DidChangeTextDocumentParams) -> None:
    try:
        _build_document(
            params.text_document.uri,
            LSP_SERVER.workspace.get_text_document(params.text_document.uri).source,
        )
        LSP_SERVER.text_document_publish_diagnostics(
            lsp.PublishDiagnosticsParams(
                params.text_document.uri, _get_diagnostics(params.text_document.uri)
            )
        )
    except Exception:
        pass


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def on_document_did_change(params: lsp.DidChangeTextDocumentParams) -> None:
    """Handle document change request."""
    _handle_document_did_change(params)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def on_document_did_save(params: lsp.DidSaveTextDocumentParams) -> None:
    """Handle document save request."""
    _build_document(
        params.text_document.uri,
        LSP_SERVER.workspace.get_text_document(params.text_document.uri).source,
    )
    LSP_SERVER.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(
            params.text_document.uri, _get_diagnostics(params.text_document.uri)
        )
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


def _find_type_ref(uri: str, pos: front_end.Position):
    nodes = GRAPHS.get(uri, {}).items()
    ato_block_nodes = [n for n in nodes if n[0][0].startswith("__node_")]

    for _, root in ato_block_nodes:
        for _, trait in root.iter_children_with_trait(
            front_end.from_dsl, include_self=False
        ):
            if front_end.Span.from_ctx(trait.src_ctx).contains(pos) and isinstance(
                trait.src_ctx, front_end.ap.Type_referenceContext
            ):
                return root, trait, trait.src_ctx

    return None


def _find_field_ref(uri: str, text: str, pos: lsp.Position):
    # TODO use ast instead
    line = text.splitlines()[pos.line]

    def _str_rev(a: str):
        return "".join(reversed(a))

    token_r = r"a-zA-Z0-9_\[\]"
    trail_match = re.match(rf"([{token_r}]+)[^{token_r}]", line[pos.character :])
    if not trail_match:
        return None
    trailer = trail_match.group(1)
    head_match = re.match(
        rf"([{token_r}.]+)[^{token_r}.]", _str_rev(line[: pos.character])
    )
    header = _str_rev(head_match.group(1)) if head_match else ""
    return header + trailer, (pos.character - len(header), pos.character + len(trailer))


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DEFINITION)
def on_document_definition(params: lsp.DefinitionParams) -> lsp.LocationLink | None:
    """Handle document definition request."""
    pos = front_end.Position(
        str(get_file(params.text_document.uri)),
        params.position.line + 1,
        params.position.character + 1,
    )
    Gs = GRAPHS.get(params.text_document.uri, {})

    # check if new stmt typeref
    if typeref := _find_type_ref(params.text_document.uri, pos):
        # go find source
        _, _, ref = typeref
        search = ref.name()[0].NAME()
        if target := Gs.get(front_end.TypeRef.from_one(f"__import__{search}")):
            dsl = target.get_trait(front_end.from_dsl)
        elif target := Gs.get(front_end.TypeRef.from_one(f"__node_{search}")):
            dsl = target.get_trait(front_end.from_dsl)
        else:
            log_warning("Didn't find typeref target")
            return

        if dsl.definition_ctx is None:
            return

        d_span = front_end.from_dsl._ctx_or_type_to_span(dsl.definition_ctx)
        lsp_d_span = _span_to_lsp_range(d_span)
        return lsp.LocationLink(
            target_uri=d_span.start.file,
            target_range=lsp_d_span,
            target_selection_range=lsp_d_span,
            origin_selection_range=_span_to_lsp_range(
                front_end.Span.from_ctx(ref.getRuleContext())
            ),
        )

    # check if field ref
    document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
    if node := _get_node_from_row(params.text_document.uri, params.position.line):
        dsl = node.get_trait(front_end.from_dsl)
        if _field_ref := _find_field_ref(
            params.text_document.uri, document.source, params.position
        ):
            field_ref, pos = _field_ref
            target = _find_field_reference_node(
                params.text_document.uri,
                document.source,
                str(field_ref),
                params.position.line,
            )
            if target is not None and (
                target_dsl := target.get_trait(front_end.from_dsl)
            ):
                s_span = front_end.from_dsl._ctx_or_type_to_span(target_dsl.src_ctx)
                lsp_d_span = _span_to_lsp_range(s_span)
                return lsp.LocationLink(
                    target_uri=s_span.start.file,
                    target_range=lsp_d_span,
                    target_selection_range=lsp_d_span,
                    origin_selection_range=lsp.Range(
                        lsp.Position(line=params.position.line, character=pos[0]),
                        lsp.Position(line=params.position.line, character=pos[1]),
                    ),
                )


def _get_available_types(
    uri: str, text: str, current_line: int | None, local_only: bool
) -> dict[str, Node]:
    """
    Get available symbols in file
    """
    # TODO: handle python files
    if not uri.endswith(".ato"):
        return {}

    try:
        # Build the document to ensure graphs are populated
        _build_incomplete_document(uri, text, hint_current_line=current_line)

        # Get all graphs for this document
        graphs = GRAPHS.get(uri, {})
        if not graphs:
            return {}

        node_types = {
            typename: root
            for root in graphs.values()
            if not (typename := type(root).__name__).startswith("_")
            and isinstance(root, Node)
        }

        if local_only:
            node_types = {
                typename: node_type
                for typename, node_type in node_types.items()
                if (from_dsl := node_type.get_trait(front_end.from_dsl))
                and from_dsl.definition_ctx is None
            }

        return node_types

    except Exception as e:
        log_warning(f"Error getting available types: {e}")
        # Fallback to empty list - user won't get completions but LSP won't crash

    return {}


def _get_importable_paths(uri: str) -> list[Path]:
    """
    All possible paths of ato files to import from
    If file part of project, glob from project root else from parent dir of current file
    """
    file_path = get_file(uri)
    root = file_path.parent

    prj_root = find_project_dir(root)
    if prj_root:
        root = prj_root

    ato_files = list(root.rglob("**/*.ato")) + list(root.rglob("**/*.py"))
    ato_files = [
        path.relative_to(root)
        for path in ato_files
        if path.is_file() and path != file_path
    ]

    if prj_root:
        # remove prefix .ato/modules
        ato_files = [
            path if not path.parts[:2] == (".ato", "modules") else Path(*path.parts[2:])
            for path in ato_files
        ]

    return ato_files


def _extract_field_reference_before_dot(line: str, position: int) -> str | None:
    """
    Extract a field reference before a dot at the given position.
    For example, if line is "mymodule.instance." and position is at the end,
    returns "mymodule.instance".

    This function handles two cases:
    1. Cursor right after dot: "resistor.|" (position after dot)
    2. Cursor after typing: "resistor.res|" (position after partial text)
    """
    # Check if we're right after a dot
    if position > 0 and position <= len(line) and line[position - 1] == ".":
        # We're right after a dot, extract the field reference before it
        dot_position = position - 1
    else:
        # Look backwards to find the most recent dot
        dot_position = -1
        for i in range(min(position - 1, len(line) - 1), -1, -1):
            if line[i] == ".":
                dot_position = i
                break

        if dot_position == -1:
            return None

    # Find the start of the field reference by walking backwards from the dot
    start = dot_position
    while start > 0:
        char = line[start - 1]
        # Allow alphanumeric, dots, underscores, and brackets in field references
        if char.isalnum() or char in "._[]":
            start -= 1
        else:
            break

    field_ref = line[start:dot_position].strip()
    return field_ref if field_ref else None


def _get_node_completions(node: Node) -> list[lsp.CompletionItem]:
    """
    Extract completion items from a faebryk node.
    Returns parameters, sub-modules, and interfaces as completion items.
    """
    from faebryk.core.module import Module
    from faebryk.core.moduleinterface import ModuleInterface
    from faebryk.core.parameter import Parameter

    completion_items = []

    try:
        # Get all child nodes using the node's get_children method
        children = node.get_children(direct_only=True, types=Node)

        for child in children:
            try:
                # Get the child's name from its parent relationship
                child_name = child.get_name()
                class_name = child.__class__.__name__

                # don't show anonymous children
                if child in node.runtime_anon:
                    continue

                # don't show internal children
                if child_name.startswith("_"):
                    continue

                # Determine the completion item kind based on the node type
                if isinstance(child, Module):
                    kind = lsp.CompletionItemKind.Field
                    detail = f"Module: {class_name}"
                elif isinstance(child, ModuleInterface):
                    kind = lsp.CompletionItemKind.Interface
                    detail = f"Interface: {class_name}"
                elif isinstance(child, Parameter):
                    kind = lsp.CompletionItemKind.Unit
                    detail = f"Parameter: {child.units}"
                else:
                    continue

                completion_items.append(
                    lsp.CompletionItem(
                        label=child_name,
                        kind=kind,
                        detail=detail,
                        documentation=lsp.MarkupContent(
                            kind=lsp.MarkupKind.Markdown,
                            value=f"**{child_name}**: {detail}",
                        ),
                    )
                )

            except Exception:
                # Skip children that can't be accessed or named
                continue

    except Exception as e:
        log_error(f"Error extracting completions from node: {e}")

    return completion_items


def _build_incomplete_document(
    uri: str, text: str, hint_current_line: int | None
) -> None:
    """
    Create a temporary version of the document with the incomplete line removed
    This allows us to build the document even when the user is typing
    an incomplete expression
    """

    if hint_current_line is not None:
        lines = text.split("\n")
        if hint_current_line is not None:
            lines[hint_current_line] = ""

        text = "\n".join(lines)

    _build_document(uri, text)


def _get_node_from_row(uri: str, row: int) -> Node | None:
    """
    Get the node from the row of the document.
    """
    file_path = get_file(uri)
    pos = front_end.Position(str(file_path), row + 1, 0)

    graphs = GRAPHS.get(uri, {})
    for root_node in graphs.values():
        if t := root_node.get_trait(front_end.from_dsl):
            if front_end.Span.from_ctx(t.src_ctx).contains(pos):
                return root_node
    return None


def _find_field_reference_node(
    uri: str, text: str, field_ref_str: str, row: int
) -> Node | None:
    """
    Find the node corresponding to a field reference string in the given document.
    Uses from_dsl trait to find the specific context node at the cursor position.
    """
    try:
        # Build the document if needed
        try:
            _build_incomplete_document(uri, text, hint_current_line=row)
        except Exception as e:
            log_error(f"Failed to build document for completion: {e}")
            # Even if build fails, continue -
            #  we might have cached graphs from previous builds
            pass

        # Use from_dsl trait to find the node that contains the cursor position
        context_node = _get_node_from_row(uri, row)

        if not context_node:
            log_warning("No node found containing field ref")
            return None

        # Parse the field reference string into a FieldRef object
        parts = []
        for part_str in field_ref_str.split("."):
            if "[" in part_str and "]" in part_str:
                # Handle array indexing like "resistors[0]"
                name, key_part = part_str.split("[", 1)
                key = key_part.rstrip("]")
                # Try to convert key to int if possible
                try:
                    key = int(key)
                except ValueError:
                    pass
                parts.append(ReferencePartType(name, key))
            else:
                parts.append(ReferencePartType(part_str))

        field_ref = FieldRef(parts)

        try:
            # Use the Bob instance to resolve the field reference
            bob_instance = front_end.bob
            resolved_field = bob_instance.resolve_node_field(context_node, field_ref)

            # If it's a node, return it
            if isinstance(resolved_field, Node):
                return resolved_field

        except (AttributeError, TypeError, ValueError) as e:
            log_warning(f"Failed to resolve field reference: {e}")

    except Exception as e:
        log_error(f"Error resolving field reference '{field_ref_str}': {e}")

    return None


@once
def _get_stdlib_types():
    import faebryk.library._F as F

    symbols = vars(F).values()
    return [s for s in symbols if isinstance(s, type) and issubclass(s, Node)]


def _node_type_to_completion_item(node_type: type[Node]) -> lsp.CompletionItem:
    if issubclass(node_type, Module):
        kind = lsp.CompletionItemKind.Field
    elif issubclass(node_type, ModuleInterface):
        kind = lsp.CompletionItemKind.Interface
    elif issubclass(node_type, Parameter):
        kind = lsp.CompletionItemKind.Unit
    elif issubclass(node_type, Trait):
        kind = lsp.CompletionItemKind.Operator
    elif issubclass(node_type, TraitImpl):
        kind = lsp.CompletionItemKind.Operator
    elif issubclass(node_type, Node):
        kind = lsp.CompletionItemKind.Class
    else:
        assert False, f"Unexpected node type: {node_type}"

    base_class = node_type.mro()[1]
    type_name = node_type.__name__

    return lsp.CompletionItem(
        label=type_name,
        kind=kind,
        detail=f"Base: {base_class.__name__}",
        documentation=lsp.MarkupContent(
            kind=lsp.MarkupKind.Markdown,
            value=not_none(node_type.__doc__),
        )
        if node_type.__doc__
        else None,
    )


def _resolve_import_path(document: workspace.TextDocument, path: str) -> Path:
    """
    Resolve the import path for a given document and path.
    """
    try:
        init_atopile_config(Path(document.path).parent)
        from atopile.config import config

        in_project = config.has_project
    except Exception:
        in_project = False

    doc_path = Path(document.path)
    import_path_stmt = Path(path)

    if in_project:
        bob_stup = front_end.Bob()

        context = front_end.Context(
            file_path=doc_path,
            scope_ctx=None,
            refs={},
            ref_ctxs={},
        )

        item = front_end.Context.ImportPlaceholder(
            original_ctx=None,
            from_path=path,
            ref=None,
        )

        return bob_stup._find_import_path(context, item)

    return (
        doc_path.parent / import_path_stmt
        if not import_path_stmt.is_absolute()
        else import_path_stmt
    )


def _handle_dot_completion(
    params: lsp.CompletionParams, line: str, document: workspace.TextDocument
) -> lsp.CompletionList | None:
    # Extract field reference before the dot
    field_ref_str = _extract_field_reference_before_dot(line, params.position.character)

    if not field_ref_str:
        log_warning("No field reference found")
        return None

    # Find the node corresponding to this field reference
    target_node = _find_field_reference_node(
        params.text_document.uri,
        document.source,
        field_ref_str,
        params.position.line,
    )

    if not target_node:
        log_warning("No target node found")
        return None

    # Get completion items from the node
    completion_items = _get_node_completions(target_node)

    # Filter completion items if user has already started typing after the dot
    typed_text = ""
    if params.position.character < len(line):
        # Look for any text after the most recent dot
        dot_pos = -1
        for i in range(params.position.character - 1, -1, -1):
            if line[i] == ".":
                dot_pos = i
                break

        if dot_pos != -1 and dot_pos + 1 < params.position.character:
            typed_text = line[dot_pos + 1 : params.position.character].strip()

    # Filter items if user has started typing
    if typed_text:
        filtered_items = [
            item
            for item in completion_items
            if item.label.lower().startswith(typed_text.lower())
        ]
        completion_items = filtered_items

    return lsp.CompletionList(is_incomplete=False, items=completion_items)


def _handle_new_keyword_completion(
    params: lsp.CompletionParams, line: str, document: workspace.TextDocument
) -> lsp.CompletionList | None:
    node_types = _get_available_types(
        params.text_document.uri,
        document.source,
        params.position.line,
        local_only=False,
    )

    completion_items = [
        _node_type_to_completion_item(type(node))
        for node in node_types.values()
        if isinstance(node, (Module, ModuleInterface))
    ]

    return lsp.CompletionList(is_incomplete=False, items=completion_items)


def _handle_stdlib_import_keyword_completion(
    params: lsp.CompletionParams, line: str, document: workspace.TextDocument
) -> lsp.CompletionList | None:
    node_types = _get_stdlib_types()

    completion_items = [
        _node_type_to_completion_item(type)
        for type in node_types
        # don't need traits atm in ato
        if not issubclass(type, Trait) or TraitImpl.is_traitimpl_type(type)
    ]

    return lsp.CompletionList(is_incomplete=False, items=completion_items)


def _handle_from_keyword_completion(
    params: lsp.CompletionParams, line: str, document: workspace.TextDocument
) -> lsp.CompletionList | None:
    paths = _get_importable_paths(params.text_document.uri)
    completion_items = [
        lsp.CompletionItem(
            label=f'"{path.as_posix()}"',
            kind=lsp.CompletionItemKind.File,
        )
        for path in paths
    ]

    return lsp.CompletionList(is_incomplete=False, items=completion_items)


def _handle_from_import_keyword_completion(
    params: lsp.CompletionParams, line: str, document: workspace.TextDocument
) -> lsp.CompletionList | None:
    match = re.match(r"from\s+['\"](.*)['\"]", line)
    if not match:
        return None

    path = match.group(1)
    import_uri = str(_resolve_import_path(document, path))
    import_text = get_file_contents(import_uri)[1]
    node_types = _get_available_types(import_uri, import_text, None, local_only=True)
    completion_items = [
        _node_type_to_completion_item(type(node))
        for node in node_types.values()
        # don't need traits atm in ato
        if not issubclass(type, Trait) or TraitImpl.is_traitimpl_type(type)
    ]

    return lsp.CompletionList(is_incomplete=False, items=completion_items)


@LSP_SERVER.feature(
    lsp.TEXT_DOCUMENT_COMPLETION,
    lsp.CompletionOptions(
        trigger_characters=[".", " "],
        resolve_provider=False,
    ),
)
def on_document_completion(params: lsp.CompletionParams) -> lsp.CompletionList | None:
    """Handle document completion request for field references ending with '.'
    and type completion after 'new'"""
    try:
        document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
        line = utils.cursor_line(document, params.position)

        char = line[: params.position.character]
        stripped = char.rstrip()
        if char.endswith("."):
            log_warning(f"dot_completion: '{char}'")
            return _handle_dot_completion(params, line, document)
        elif stripped.endswith("new"):
            log_warning(f"new_keyword_completion: '{char}'")
            return _handle_new_keyword_completion(params, line, document)
        elif stripped.endswith("import") or (
            "import " in char and stripped.endswith(",")
        ):
            if "from" in char:
                log_warning(f"from_import_keyword_completion: '{char}'")
                return _handle_from_import_keyword_completion(params, line, document)
            else:
                log_warning(f"stdlib_import_keyword_completion: '{char}'")
                return _handle_stdlib_import_keyword_completion(params, line, document)
        elif stripped.endswith("from"):
            log_warning(f"from_keyword_completion: '{char}'")
            return _handle_from_keyword_completion(params, line, document)

    except Exception as e:
        log_error(f"Error in completion handler: {e}")
        return None


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


def _get_document_key(document: workspace.TextDocument):
    if WORKSPACE_SETTINGS:
        document_workspace = pathlib.Path(document.path)
        workspaces = {s["workspaceFS"] for s in WORKSPACE_SETTINGS.values()}

        # Find workspace settings for the given file.
        while document_workspace != document_workspace.parent:
            if str(document_workspace) in workspaces:
                return str(document_workspace)
            document_workspace = document_workspace.parent

    return None


def _get_settings_by_document(document: workspace.TextDocument | None):
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
    document: workspace.TextDocument,
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
    LSP_SERVER.window_log_message(lsp.LogMessageParams(msg_type, "LSP: " + message))


def log_error(message: str) -> None:
    LSP_SERVER.window_log_message(lsp.LogMessageParams(lsp.MessageType.Error, message))
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["onError", "onWarning", "always"]:
        LSP_SERVER.show_message(message, lsp.MessageType.Error)


def log_warning(message: str) -> None:
    LSP_SERVER.window_log_message(
        lsp.LogMessageParams(lsp.MessageType.Warning, message)
    )
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["onWarning", "always"]:
        LSP_SERVER.show_message(message, lsp.MessageType.Warning)


def log_always(message: str) -> None:
    LSP_SERVER.window_log_message(lsp.LogMessageParams(lsp.MessageType.Info, message))
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["always"]:
        LSP_SERVER.show_message(message, lsp.MessageType.Info)


# *****************************************************
# Start the server.
# *****************************************************
if __name__ == "__main__":
    LSP_SERVER.start_io()
