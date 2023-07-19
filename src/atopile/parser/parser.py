import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import List

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from atopile.model.model import EdgeType, Model, VertexType
from atopile.model.utils import generate_edge_uid
from atopile.parser.AtopileLexer import AtopileLexer
from atopile.parser.AtopileParser import AtopileParser
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor
from atopile.project.config import BuildConfig
from atopile.project.project import Project
from atopile.utils import profile

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class LanguageError(Exception):
    """
    This exception is thrown when there's an error in the syntax of the language
    """

    def __init__(self, message: str, filepath: Path, line: int, column: int) -> None:
        super().__init__(message)
        self.message = message
        self.filepath = filepath
        self.line = line
        self.column = column


class ParserErrorListener(ErrorListener):
    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise LanguageError(f"Syntax error: '{msg}'", self.filepath, line, column)


class Builder(AtopileParserVisitor):
    def __init__(self, project: Project) -> None:
        self.model = Model()
        self.project = project

        self._block_stack: List[str] = []
        self._file_stack: List[str] = []

        self._tree_cache = {}

        # if something's in parsed files, we must skip building it a second time
        super().__init__()

    @property
    def current_block(self) -> str:
        return self._block_stack[-1]

    @property
    def current_file(self):
        return self._file_stack[0]

    @contextmanager
    def working_block(self, ref: str):
        self._block_stack.append(ref)
        yield
        self._block_stack.pop()

    @contextmanager
    def working_file(self, abs_path: Path):
        std_path = self.project.standardise_import_path(abs_path)
        self._file_stack.append(abs_path)
        with self.working_block(str(std_path)):
            yield
        self._file_stack.pop()
        self.model.src_files.append(std_path)

    def parse_file(self, abs_path: Path):
        if str(abs_path) in self._tree_cache:
            return self._tree_cache[str(abs_path)]

        error_listener = ParserErrorListener(abs_path)

        # FIXME: hacky performance improvement by avoiding jittery read
        with abs_path.open("r", encoding="utf-8") as f:
            input = InputStream(f.read())

        lexer = AtopileLexer(input)
        stream = CommonTokenStream(lexer)
        parser = AtopileParser(stream)
        parser.removeErrorListeners()
        parser.addErrorListener(error_listener)
        tree = parser.file_input()
        self._tree_cache[str(abs_path)] = tree
        return tree

    def build(self, path: Path) -> Model:
        """
        Start the build from the specified file.
        """
        if not path.exists():
            raise FileNotFoundError(path)

        abs_path = path.resolve().absolute()

        std_path = self.project.standardise_import_path(abs_path)
        std_path_str = str(std_path)

        tree = self.parse_file(abs_path)

        self.model.new_vertex(VertexType.file, std_path_str)
        self.model.data[std_path_str] = {}

        with self.working_file(abs_path):
            self.visit(tree)

        return self.model

    def visitImport_stmt(self, ctx: AtopileParser.Import_stmtContext):
        import_filename = self.get_string(ctx.string())

        abs_path, std_path = self.project.resolve_import(
            import_filename, self.current_file
        )

        if std_path in self._file_stack:
            raise LanguageError(
                f"Circular import detected: {std_path}",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        if std_path not in self.model.src_files:
            # do the actual import, parsing etc...
            with self.working_file(abs_path):
                tree = self.parse_file(abs_path)
                self.model.new_vertex(VertexType.file, import_filename)
                self.model.data[import_filename] = {}
                super().visit(tree)

        # link the import to the current block
        to_import = ctx.name_or_attr().getText()
        graph_path, data_path = self.model.find_ref(to_import, import_filename)
        if data_path:
            raise LanguageError(
                f"Cannot import data path {data_path}",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        self.model.new_edge(EdgeType.imported_to, graph_path, self.current_block)

        # the super().visit() in the new file import section should
        # handle all depth required. From here, we always want to go back up
        return None

    def define_block(self, ctx, block_type: VertexType):
        name = ctx.name().getText()

        if ctx.OPTIONAL():
            block_path = self.model.new_vertex(
                block_type, name, option_of=self.current_block
            )
        else:
            block_path = self.model.new_vertex(
                block_type, name, part_of=self.current_block
            )

        self.model.data[block_path] = {}

        with self.working_block(block_path):
            return super().visitChildren(ctx)

    def visitComponentdef(self, ctx: AtopileParser.ComponentdefContext):
        return self.define_block(ctx, VertexType.component)

    def visitModuledef(self, ctx: AtopileParser.ModuledefContext):
        return self.define_block(ctx, VertexType.module)

    def visitPindef_stmt(self, ctx: AtopileParser.Pindef_stmtContext):
        if ctx.name() is not None:
            name = ctx.name().getText()
        elif ctx.totally_an_integer() is not None:
            name = ctx.totally_an_integer().getText()
            try:
                int(name)
            except ValueError as ex:
                raise LanguageError(
                    "Pindef_stmt must have a name or integer",
                    self.current_file,
                    ctx.start.line,
                    ctx.start.column,
                ) from ex

        else:
            raise LanguageError(
                "Pindef_stmt must have a name or integer",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        pin_path = self.model.new_vertex(
            VertexType.pin, name, part_of=self.current_block
        )
        self.model.data[pin_path] = {}

        return super().visitPindef_stmt(ctx)

    def visitSignaldef_stmt(self, ctx: AtopileParser.Signaldef_stmtContext):
        name = ctx.name().getText()

        if ctx.PRIVATE():
            private = True
        else:
            private = False

        signal_path = self.model.new_vertex(
            VertexType.signal, name, part_of=self.current_block
        )
        self.model.data[signal_path] = {
            "private": private,
        }

        return super().visitSignaldef_stmt(ctx)

    def deref_totally_an_integer(
        self, ctx: AtopileParser.Totally_an_integerContext
    ) -> str:
        try:
            int(ctx.getText())
        except ValueError as ex:
            raise LanguageError(
                "Numerical pin reference must be an integer, but seems you stuck something else in there somehow?",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            ) from ex
        return ctx.getText()

    def deref_connectable(self, ctx: AtopileParser.ConnectableContext) -> str:
        if ctx.name_or_attr():
            ref = ctx.name_or_attr().getText()
        elif ctx.signaldef_stmt():
            ref = ctx.signaldef_stmt().name().getText()
        elif ctx.pindef_stmt():
            if ctx.pindef_stmt().name():
                ref = ctx.pindef_stmt().name().getText()
            elif ctx.pindef_stmt().totally_an_integer():
                # here we don't care about the result, we're just using the function to check it's an integer
                self.deref_totally_an_integer(ctx.pindef_stmt().totally_an_integer())
                ref = ctx.pindef_stmt().totally_an_integer().getText()
            else:
                raise LanguageError(
                    "Cannot connect to this type of object",
                    self.current_file,
                    ctx.start.line,
                    ctx.start.column,
                )
        elif ctx.numerical_pin_ref():
            # same as above, we don't care about the result
            self.deref_totally_an_integer(ctx.numerical_pin_ref().totally_an_integer())
            ref = ctx.numerical_pin_ref().getText()
        else:
            raise LanguageError(
                "Cannot connect to this type of object",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        try:
            cn_path, cn_data = self.model.find_ref(ref, self.current_block)
        except KeyError as ex:
            raise LanguageError(
                f"Cannot connect to non-existent object {ref}",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            ) from ex

        if cn_data:
            raise LanguageError(
                f"Cannot connect to data object {ref}",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )
        return cn_path

    def visitConnect_stmt(self, ctx: AtopileParser.Connect_stmtContext):
        # visit the connectables now before attempting to make a connection
        result = self.visitChildren(ctx)
        connectables = ctx.connectable()

        if len(connectables) < 2:
            raise LanguageError(
                "Connect statement must have at least two connectables",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        from_path = self.deref_connectable(ctx.connectable(0))
        to_path = self.deref_connectable(ctx.connectable(1))
        uid = generate_edge_uid(from_path, to_path, self.current_block)
        self.model.new_edge(EdgeType.connects_to, from_path, to_path, uid=uid)
        self.model.data[uid] = {
            "defining_block": self.current_block,
        }

        # children are already vistited
        return result

    def visitWith_stmt(self, ctx: AtopileParser.With_stmtContext):
        with_ref = ctx.name_or_attr().getText()
        with_path, _ = self.model.find_ref(with_ref, self.current_block)

        self.model.enable_option(with_path)

        return super().visitWith_stmt(ctx)

    def visitAssign_stmt(self, ctx: AtopileParser.Assign_stmtContext):
        assignee = ctx.name_or_attr().getText()
        assignable: AtopileParser.AssignableContext = ctx.assignable()

        if assignable.new_stmt():
            class_ref = assignable.new_stmt().name_or_attr().getText()
            class_path, _ = self.model.find_ref(class_ref, self.current_block)
            # FIXME: this probably throws a dud error if the name is an attr
            # NOTE: we're not using the assignee here because we actually want that error until this is fixed properly
            instance_name = ctx.name_or_attr().name().getText()
            self.model.instantiate_block(class_path, instance_name, self.current_block)
        else:
            if assignable.string():
                value = self.get_string(assignable.string())
            elif assignable.NUMBER():
                value = float(assignable.NUMBER().getText())
            elif assignable.boolean_():
                value = bool(assignable.boolean_().getText())
            else:
                raise LanguageError(
                    "Only strings and numbers are supported",
                    self.current_file,
                    ctx.start.line,
                    ctx.start.column,
                )

            graph_path, existing_data_path, remaining_parts = self.model.find_ref(
                assignee, self.current_block, return_unfound=True
            )
            data_path = existing_data_path + remaining_parts
            data = self.model.data[graph_path]
            for p in data_path[:-1]:
                data = data.setdefault(p, {})

            data[data_path[-1]] = value

        return super().visitAssign_stmt(ctx)

    def get_string(self, ctx: AtopileParser.StringContext) -> str:
        return ctx.getText().strip("\"'")


def build_model(project: Project, config: BuildConfig) -> Model:
    log.info("Building model")
    skip_profiler = log.getEffectiveLevel() > logging.DEBUG

    with profile(profile_log=log, skip=skip_profiler):
        bob = Builder(project)
        try:
            model = bob.build(config.root_file)
        except LanguageError as ex:
            log.error(
                f"Language error @ {ex.filepath}:{ex.line}:{ex.column}: {ex.message}"
            )
            log.error("Stopping due to error.")
            sys.exit(1)

    return model
