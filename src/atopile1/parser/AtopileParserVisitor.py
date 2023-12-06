# Generated from AtopileParser.g4 by ANTLR 4.13.0
from antlr4 import *
if "." in __name__:
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


    # Visit a parse tree produced by AtopileParser#simple_stmts.
    def visitSimple_stmts(self, ctx:AtopileParser.Simple_stmtsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#simple_stmt.
    def visitSimple_stmt(self, ctx:AtopileParser.Simple_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#compound_stmt.
    def visitCompound_stmt(self, ctx:AtopileParser.Compound_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#block.
    def visitBlock(self, ctx:AtopileParser.BlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#blockdef.
    def visitBlockdef(self, ctx:AtopileParser.BlockdefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#blocktype.
    def visitBlocktype(self, ctx:AtopileParser.BlocktypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#import_stmt.
    def visitImport_stmt(self, ctx:AtopileParser.Import_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#assign_stmt.
    def visitAssign_stmt(self, ctx:AtopileParser.Assign_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#assignable.
    def visitAssignable(self, ctx:AtopileParser.AssignableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#retype_stmt.
    def visitRetype_stmt(self, ctx:AtopileParser.Retype_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#connect_stmt.
    def visitConnect_stmt(self, ctx:AtopileParser.Connect_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#connectable.
    def visitConnectable(self, ctx:AtopileParser.ConnectableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#signaldef_stmt.
    def visitSignaldef_stmt(self, ctx:AtopileParser.Signaldef_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#pindef_stmt.
    def visitPindef_stmt(self, ctx:AtopileParser.Pindef_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#with_stmt.
    def visitWith_stmt(self, ctx:AtopileParser.With_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#new_stmt.
    def visitNew_stmt(self, ctx:AtopileParser.New_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#name_or_attr.
    def visitName_or_attr(self, ctx:AtopileParser.Name_or_attrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#numerical_pin_ref.
    def visitNumerical_pin_ref(self, ctx:AtopileParser.Numerical_pin_refContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#attr.
    def visitAttr(self, ctx:AtopileParser.AttrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#totally_an_integer.
    def visitTotally_an_integer(self, ctx:AtopileParser.Totally_an_integerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#name.
    def visitName(self, ctx:AtopileParser.NameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#string.
    def visitString(self, ctx:AtopileParser.StringContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#boolean_.
    def visitBoolean_(self, ctx:AtopileParser.Boolean_Context):
        return self.visitChildren(ctx)



del AtopileParser