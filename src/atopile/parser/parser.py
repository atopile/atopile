import logging
from pathlib import Path

from antlr4 import CommonTokenStream, FileStream

from atopile.model.model import EdgeType, Model, VertexType
from atopile.parser.AtopileLexer import AtopileLexer
from atopile.parser.AtopileParser import AtopileParser
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor

log = logging.getLogger(__name__)


class ModelBuildingVisitor(AtopileParserVisitor):
    def __init__(self, model: Model, filename: str) -> None:
        super().__init__()
        self._been_run = False
        self.model = model

        # start the build from the first file passed in
        self.model.new_vertex(VertexType.file, filename)
        self.model.data[filename] = {}
        self.current_parent = filename

    def visit(self, tree):
        if self._been_run:
            raise RuntimeError("Visitor has already been used")
        self._been_run = True
        return super().visit(tree)

    def define_block(self, ctx, block_type: VertexType):
        original_parent = self.current_parent
        name = ctx.name().getText()

        if ctx.OPTIONAL():
            block_path = self.model.new_vertex(
                block_type,
                name,
                option_of=self.current_parent
            )
        else:
            block_path = self.model.new_vertex(
                block_type,
                name,
                part_of=self.current_parent
            )

        self.model.data[block_path] = {}

        self.current_parent = block_path
        internals = super().visitChildren(ctx)
        self.current_parent = original_parent
        return internals

    def visitComponentdef(self, ctx: AtopileParser.ComponentdefContext):
        return self.define_block(ctx, VertexType.component)

    def visitModuledef(self, ctx: AtopileParser.ModuledefContext):
        return self.define_block(ctx, VertexType.module)

    def visitPindef_stmt(self, ctx: AtopileParser.Pindef_stmtContext):
        name = ctx.name().getText()
        pin_path = self.model.new_vertex(
            VertexType.pin,
            name,
            part_of=self.current_parent
        )
        self.model.data[pin_path] = {}

        return super().visitPindef_stmt(ctx)

    def visitSignaldef_stmt(self, ctx: AtopileParser.Signaldef_stmtContext):
        name = ctx.name().getText()
        signal_path = self.model.new_vertex(
            VertexType.signal,
            name,
            part_of=self.current_parent
        )
        self.model.data[signal_path] = {}

        return super().visitSignaldef_stmt(ctx)

    def visitConnect_stmt(self, ctx: AtopileParser.Connect_stmtContext):
        from_ref = ctx.name_or_attr(0).getText()
        to_ref = ctx.name_or_attr(1).getText()

        from_path, from_data_path = self.model.find_ref(from_ref, self.current_parent)
        to_path, to_data_path = self.model.find_ref(to_ref, self.current_parent)

        if from_data_path or to_data_path:
            raise AttributeError("Cannot connect to data object")

        self.model.new_edge(EdgeType.connects_to, from_path, to_path)

        return super().visitConnect_stmt(ctx)

    def visitWith_stmt(self, ctx: AtopileParser.With_stmtContext):
        with_ref = ctx.name_or_attr().getText()
        with_path, _ = self.model.find_ref(with_ref, self.current_parent)

        self.model.enable_option(with_path)

        return super().visitWith_stmt(ctx)

    def visitAssign_stmt(self, ctx:AtopileParser.Assign_stmtContext):
        assignee = ctx.name_or_attr(0).getText()
        if ctx.new_element():
            class_ref = ctx.new_element().name_or_attr().getText()
            class_path, _ = self.model.find_ref(class_ref, self.current_parent)
            # FIXME: this probably throws a dud error if the name is an attr
            instance_name = ctx.name_or_attr(0).name().getText()
            self.model.instantiate_block(class_path, instance_name, self.current_parent)
        else:
            if ctx.STRING():
                value = ctx.STRING().getText().strip("\"\'")

            elif ctx.NUMBER():
                value = float(ctx.NUMBER().getText())
            else:
                raise NotImplementedError("Only strings and numbers are supported")

            graph_path, existing_data_path, remaining_parts = self.model.find_ref(assignee, self.current_parent, return_unfound=True)
            data_path = existing_data_path + remaining_parts
            data = self.model.data[graph_path]
            for p in data_path[:-1]:
                data = data.setdefault(p, {})

            data[data_path[-1]] = value

        return super().visitAssign_stmt(ctx)

def parse_file(path: Path) -> Model:
    input = FileStream(path)
    lexer = AtopileLexer(input)
    stream = CommonTokenStream(lexer)
    parser = AtopileParser(stream)
    tree = parser.file_input()
    m = Model()
    builder = ModelBuildingVisitor(m, str(path))
    builder.visit(tree)
    return m
