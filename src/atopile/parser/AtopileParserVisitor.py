# Generated from AtopileParser.g4 by ANTLR 4.12.0
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .AtopileParser import AtopileParser
else:
    from AtopileParser import AtopileParser

# This class defines a complete generic visitor for a parse tree produced by AtopileParser.

class AtopileParserVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by AtopileParser#file_input.
    def visitFile_input(self, ctx:AtopileParser.File_inputContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#stmt.
    def visitStmt(self, ctx:AtopileParser.StmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#block_def.
    def visitBlock_def(self, ctx:AtopileParser.Block_defContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#block.
    def visitBlock(self, ctx:AtopileParser.BlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#assign_stmt.
    def visitAssign_stmt(self, ctx:AtopileParser.Assign_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#connect_stmt.
    def visitConnect_stmt(self, ctx:AtopileParser.Connect_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#def_stmt.
    def visitDef_stmt(self, ctx:AtopileParser.Def_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#paramatised_stmt.
    def visitParamatised_stmt(self, ctx:AtopileParser.Paramatised_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#assign_value.
    def visitAssign_value(self, ctx:AtopileParser.Assign_valueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#name_or_attr.
    def visitName_or_attr(self, ctx:AtopileParser.Name_or_attrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#attr.
    def visitAttr(self, ctx:AtopileParser.AttrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#name.
    def visitName(self, ctx:AtopileParser.NameContext):
        return self.visitChildren(ctx)



del AtopileParser