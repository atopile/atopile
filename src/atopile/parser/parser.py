import logging
from pathlib import Path
from contextlib import contextmanager

from antlr4 import CommonTokenStream, FileStream

from atopile.model.model import EdgeType, Model, VertexType
from atopile.parser.AtopileLexer import AtopileLexer
from atopile.parser.AtopileParser import AtopileParser
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor
from atopile.project.project import Project

log = logging.getLogger(__name__)


def parse_file(path: Path):
    input = FileStream(path)
    lexer = AtopileLexer(input)
    stream = CommonTokenStream(lexer)
    parser = AtopileParser(stream)
    tree = parser.file_input()
    return tree

class Builder(AtopileParserVisitor):
    def __init__(self, project: Project) -> None:
        self.model = Model()
        self.project = project

        self._block_stack = []
        self._file_stack = []

        # if something's in parsed files, we must skip building it a second time
        super().__init__()

    @property
    def current_block(self):
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

    def build(self, path: Path) -> Model:
        """
        Start the build from the specified file.
        """
        if not path.exists():
            raise FileNotFoundError(path)

        abs_path = path.resolve().absolute()

        std_path = self.project.standardise_import_path(abs_path)
        std_path_str = str(std_path)

        tree = parse_file(abs_path)

        self.model.new_vertex(VertexType.file, std_path_str)
        self.model.data[std_path_str] = {}

        with self.working_file(abs_path):
            self.visit(tree)

        return self.model

    def visitImport_stmt(self, ctx: AtopileParser.Import_stmtContext):
        import_filename = ctx.STRING().getText().strip('"')

        abs_path, std_path = self.project.resolve_import(import_filename, self.current_file)

        if std_path in self._file_stack:
            raise RuntimeError(f"Circular import detected: {std_path}")

        if std_path not in self.model.src_files:
            # do the actual import, parsing etc...
            with self.working_file(abs_path):
                tree = parse_file(abs_path)
                self.model.new_vertex(VertexType.file, import_filename)
                self.model.data[import_filename] = {}
                import_ = super().visit(tree)

        # link the import to the current block
        to_import = ctx.name_or_attr().getText()
        graph_path, data_path = self.model.find_ref(to_import, import_filename)
        if data_path:
            raise RuntimeError(f"Cannot import data path {data_path}")

        self.model.new_edge(
            EdgeType.imported_to,
            graph_path,
            self.current_block
        )

        return import_

    def define_block(self, ctx, block_type: VertexType):
        name = ctx.name().getText()

        if ctx.OPTIONAL():
            block_path = self.model.new_vertex(
                block_type,
                name,
                option_of=self.current_block
            )
        else:
            block_path = self.model.new_vertex(
                block_type,
                name,
                part_of=self.current_block
            )

        self.model.data[block_path] = {}

        with self.working_block(block_path):
            return super().visitChildren(ctx)

    def visitComponentdef(self, ctx: AtopileParser.ComponentdefContext):
        return self.define_block(ctx, VertexType.component)

    def visitModuledef(self, ctx: AtopileParser.ModuledefContext):
        return self.define_block(ctx, VertexType.module)

    def visitPindef_stmt(self, ctx: AtopileParser.Pindef_stmtContext):
        name = ctx.name().getText()
        pin_path = self.model.new_vertex(
            VertexType.pin,
            name,
            part_of=self.current_block
        )
        self.model.data[pin_path] = {}

        return super().visitPindef_stmt(ctx)

    def visitSignaldef_stmt(self, ctx: AtopileParser.Signaldef_stmtContext):
        name = ctx.name().getText()
        signal_path = self.model.new_vertex(
            VertexType.signal,
            name,
            part_of=self.current_block
        )
        self.model.data[signal_path] = {}

        return super().visitSignaldef_stmt(ctx)

    def visitConnect_stmt(self, ctx: AtopileParser.Connect_stmtContext):
        from_ref = ctx.name_or_attr(0).getText()
        to_ref = ctx.name_or_attr(1).getText()

        from_path, from_data_path = self.model.find_ref(from_ref, self.current_block)
        to_path, to_data_path = self.model.find_ref(to_ref, self.current_block)

        if from_data_path or to_data_path:
            raise AttributeError("Cannot connect to data object")

        self.model.new_edge(EdgeType.connects_to, from_path, to_path)

        return super().visitConnect_stmt(ctx)

    def visitWith_stmt(self, ctx: AtopileParser.With_stmtContext):
        with_ref = ctx.name_or_attr().getText()
        with_path, _ = self.model.find_ref(with_ref, self.current_block)

        self.model.enable_option(with_path)

        return super().visitWith_stmt(ctx)

    def visitAssign_stmt(self, ctx:AtopileParser.Assign_stmtContext):
        assignee = ctx.name_or_attr(0).getText()
        if ctx.new_element():
            class_ref = ctx.new_element().name_or_attr().getText()
            class_path, _ = self.model.find_ref(class_ref, self.current_block)
            # FIXME: this probably throws a dud error if the name is an attr
            instance_name = ctx.name_or_attr(0).name().getText()
            self.model.instantiate_block(class_path, instance_name, self.current_block)
        else:
            if ctx.STRING():
                value = ctx.STRING().getText().strip("\"\'")

            elif ctx.NUMBER():
                value = float(ctx.NUMBER().getText())
            else:
                raise NotImplementedError("Only strings and numbers are supported")

            graph_path, existing_data_path, remaining_parts = self.model.find_ref(assignee, self.current_block, return_unfound=True)
            data_path = existing_data_path + remaining_parts
            data = self.model.data[graph_path]
            for p in data_path[:-1]:
                data = data.setdefault(p, {})

            data[data_path[-1]] = value

        return super().visitAssign_stmt(ctx)
