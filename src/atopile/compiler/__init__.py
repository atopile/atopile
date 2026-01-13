from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

from rich.console import Console, ConsoleOptions, ConsoleRenderable
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text

import atopile.compiler.ast_types as AST
import faebryk.core.node as fabll


def _try_relative_path(path: Path | None) -> str:
    """Try to make a path relative to cwd, fall back to absolute path."""
    if path is None:
        return "<memory>"
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


class CompilerException(Exception):
    """Exception raised for internal compiler failures (implementation errors)."""


@dataclass
class DSLTracebackFrame:
    """A single frame in the DSL traceback."""

    source_node: fabll.Node  # AST node with .source child
    file_path: Path | None


class DSLTracebackStack:
    """Maintains DSL traceback during AST traversal."""

    def __init__(self, file_path: Path | None = None):
        self._stack: list[fabll.Node] = []
        self._file_path = file_path

    @contextmanager
    def enter(self, node: fabll.Node) -> Generator[None, None, None]:
        self._stack.append(node)
        try:
            yield
        finally:
            self._stack.pop()

    def get_frames(self) -> list[DSLTracebackFrame]:
        """Return current traceback as frames, deduplicated by node identity."""
        seen: dict[int, DSLTracebackFrame] = {}
        for node in self._stack:
            key = id(node.instance)
            if key not in seen:
                seen[key] = DSLTracebackFrame(
                    source_node=node, file_path=self._file_path
                )
        return list(seen.values())


class DslException(Exception):
    """Bare exception for DSL errors. Raised where context is unavailable."""

    pass


# Subtypes for UI display (title derived from class name)
class DslSyntaxError(DslException):
    pass


class DslKeyError(DslException):
    pass


class DslTypeError(DslException):
    pass


class DslValueError(DslException):
    pass


class DslImportError(DslException):
    pass


class DslNotImplementedError(DslException):
    pass


class DslFeatureNotEnabledError(DslException):
    pass


class DslUndefinedSymbolError(DslException):
    pass


# ... map remaining User* types


class DslRichException(DslException):
    """Exception with full DSL context. Created by enriching DslException."""

    def __init__(
        self,
        message: str,
        *,
        traceback: list[DSLTracebackFrame] | None = None,
        original: DslException | None = None,
        source_node: fabll.Node | None = None,
        file_path: Path | None = None,
        code: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.original = original
        self.source_node = source_node
        self.file_path = file_path
        self.traceback = traceback or []

    @property
    def title(self) -> str:
        """Use original exception's class name for UI."""
        if self.original:
            return type(self.original).__name__.removeprefix("Dsl")
        return "Exception"

    def add_import_frame(self, import_node: fabll.Node, file_path: Path) -> None:
        """Add an import frame when exception propagates across file boundary."""
        self.traceback.append(
            DSLTracebackFrame(source_node=import_node, file_path=file_path)
        )

    def _render_ast_source(
        self, source_chunk: AST.SourceChunk, file_path: Path | None
    ) -> list[ConsoleRenderable]:
        loc = source_chunk.loc.get()
        start_line = loc.get_start_line()
        end_line = loc.get_end_line()

        code = None
        if file_path is not None:
            try:
                with open(file_path, "r") as f:
                    code = f.read()
            except FileNotFoundError:
                pass

        if code is None:
            # Fallback to the text stored in the SourceChunk
            code = source_chunk.get_text()
            display_path = str(file_path) if file_path else "memory"

            header = Text("  File ", style="dim")
            header.append(f'"{display_path}"', style="dim")
            header.append(f", line {start_line}", style="dim")

            return [
                header,
                Syntax(
                    code,
                    "python",
                    line_numbers=True,
                    start_line=start_line,
                    highlight_lines={
                        line_no for line_no in range(start_line, end_line + 1)
                    },
                    background_color="default",
                ),
            ]

        display_path = _try_relative_path(file_path)
        header = Text("  File ", style="dim")
        header.append(f'"{display_path}"', style="dim")
        header.append(f", line {start_line}", style="dim")

        return [
            header,
            Syntax(
                code,
                "python",
                line_numbers=True,
                line_range=(max(1, start_line - 2), end_line + 2),
                highlight_lines={
                    line_no for line_no in range(start_line, end_line + 1)
                },
                background_color="default",
            ),
        ]

    def _render_traceback_frame(
        self, frame: DSLTracebackFrame
    ) -> list[ConsoleRenderable]:
        """Render a single traceback frame with Python-like format."""
        from atopile.compiler.ast_visitor import ASTVisitor

        # Get the source chunk for this frame
        source_chunk = ASTVisitor.get_source_chunk(frame.source_node.instance)
        if source_chunk is None:
            return [
                Text(
                    f'  File "{_try_relative_path(frame.file_path) if frame.file_path else "<memory>"}"',  # noqa: E501
                    style="dim italic",
                )
            ]

        loc = source_chunk.loc.get()
        start_line = loc.get_start_line()

        # Create the file/line header (first line of frame)
        file_part = f'"{_try_relative_path(frame.file_path)}"'
        header = Text(f"  File {file_part}, line {start_line}", style="dim italic")

        # Get the source code for this frame
        source_text = source_chunk.get_text()
        lines = source_text.splitlines()

        # The source chunk contains the text for this specific AST node
        # Usually it's a single line or a small block
        if lines:
            # Show the first non-empty line of the source chunk
            code_line = ""
            for line in lines:
                line = line.strip()
                if line:
                    code_line = line
                    break
            if not code_line and lines:
                code_line = lines[0].strip()

            code_display = Text(f"    {code_line}", style="dim")
        else:
            code_display = Text("    <no source text>", style="dim")

        return [header, code_display]

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> Generator[ConsoleRenderable, None, None]:
        yield Text(self.title, style="bold red")
        yield Markdown(self.message)

        from atopile.compiler.ast_visitor import ASTVisitor

        if self.traceback:
            yield Text("\nTraceback (most recent call last):", style="bold")
            for frame in self.traceback:
                yield from self._render_traceback_frame(frame)

        if self.source_node:
            source_chunk = ASTVisitor.get_source_chunk(self.source_node.instance)
            yield Text("\nCode causing the error:", style="bold")
            if source_chunk is None:
                yield Text(
                    f"Source not available for {self.source_node}", style="dim italic"
                )
            else:
                yield from self._render_ast_source(source_chunk, self.file_path)
