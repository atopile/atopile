import logging
from pathlib import Path

from antlr4 import CommonTokenStream, FileStream

from atopile.model.model2 import EdgeType, Model, VertexType
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

        self.current_parent = block_path
        internals = super().visitChildren(ctx)
        self.current_parent = original_parent
        return internals

    def visitComponentdef(self, ctx):
        return self.define_block(ctx, VertexType.component)

    def visitModuledef(self, ctx):
        return self.define_block(ctx, VertexType.module)

    def visitPindef_stmt(self, ctx):
        name = ctx.name().getText()
        pin_path = self.model.new_vertex(
            VertexType.pin,
            name,
            part_of=self.current_parent
        )

        return super().visitPindef_stmt(ctx)

    def visitSignaldef_stmt(self, ctx):
        name = ctx.name().getText()
        signal_path = self.model.new_vertex(
            VertexType.signal,
            name,
            part_of=self.current_parent
        )

        return super().visitSignaldef_stmt(ctx)

    def visitConnect_stmt(self, ctx):
        from_ref = ctx.name_or_attr(0).getText()
        to_ref = ctx.name_or_attr(1).getText()

        _, from_path = self.model.find_ref(from_ref, self.current_parent)
        _, to_path = self.model.find_ref(to_ref, self.current_parent)

        self.model.new_edge(EdgeType.connects_to, from_path, to_path)

        return super().visitConnect_stmt(ctx)

    def visitWith_stmt(self, ctx):
        with_ref = ctx.name_or_attr().getText()
        _, with_path = self.model.find_ref(with_ref, self.current_parent)

        self.model.enable_option(with_path)

        return super().visitWith_stmt(ctx)

    def visitNew_element(self, ctx):
        class_ref = ctx.name_or_attr().getText()
        instance_ref = ctx.parentCtx.name_or_attr(0).getText()  # FIXME: this parent reference assumes there's only one way to instantiate a class
        _, class_path = self.model.find_ref(class_ref, self.current_parent)

        self.model.instantiate_block(class_path, instance_ref, self.current_parent)

        return super().visitNew_element(ctx)

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
