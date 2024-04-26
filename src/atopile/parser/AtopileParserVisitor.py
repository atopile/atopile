# Generated from AtopileParser.g4 by ANTLR 4.13.1
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


    # Visit a parse tree produced by AtopileParser#blockdef.
    def visitBlockdef(self, ctx:AtopileParser.BlockdefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#blocktype.
    def visitBlocktype(self, ctx:AtopileParser.BlocktypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#block.
    def visitBlock(self, ctx:AtopileParser.BlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#dep_import_stmt.
    def visitDep_import_stmt(self, ctx:AtopileParser.Dep_import_stmtContext):
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


    # Visit a parse tree produced by AtopileParser#declaration_stmt.
    def visitDeclaration_stmt(self, ctx:AtopileParser.Declaration_stmtContext):
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


    # Visit a parse tree produced by AtopileParser#new_stmt.
    def visitNew_stmt(self, ctx:AtopileParser.New_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#string_stmt.
    def visitString_stmt(self, ctx:AtopileParser.String_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#assert_stmt.
    def visitAssert_stmt(self, ctx:AtopileParser.Assert_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#comparison.
    def visitComparison(self, ctx:AtopileParser.ComparisonContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#compare_op_pair.
    def visitCompare_op_pair(self, ctx:AtopileParser.Compare_op_pairContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#lt_arithmetic_or.
    def visitLt_arithmetic_or(self, ctx:AtopileParser.Lt_arithmetic_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#gt_arithmetic_or.
    def visitGt_arithmetic_or(self, ctx:AtopileParser.Gt_arithmetic_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#in_arithmetic_or.
    def visitIn_arithmetic_or(self, ctx:AtopileParser.In_arithmetic_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#arithmetic_expression.
    def visitArithmetic_expression(self, ctx:AtopileParser.Arithmetic_expressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#term.
    def visitTerm(self, ctx:AtopileParser.TermContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#factor.
    def visitFactor(self, ctx:AtopileParser.FactorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#power.
    def visitPower(self, ctx:AtopileParser.PowerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#atom.
    def visitAtom(self, ctx:AtopileParser.AtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#arithmetic_group.
    def visitArithmetic_group(self, ctx:AtopileParser.Arithmetic_groupContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#literal_physical.
    def visitLiteral_physical(self, ctx:AtopileParser.Literal_physicalContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#bound_quantity.
    def visitBound_quantity(self, ctx:AtopileParser.Bound_quantityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#quantity_end.
    def visitQuantity_end(self, ctx:AtopileParser.Quantity_endContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#bilateral_quantity.
    def visitBilateral_quantity(self, ctx:AtopileParser.Bilateral_quantityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#implicit_quantity.
    def visitImplicit_quantity(self, ctx:AtopileParser.Implicit_quantityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#bilateral_nominal.
    def visitBilateral_nominal(self, ctx:AtopileParser.Bilateral_nominalContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#bilateral_tolerance.
    def visitBilateral_tolerance(self, ctx:AtopileParser.Bilateral_toleranceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#name_or_attr.
    def visitName_or_attr(self, ctx:AtopileParser.Name_or_attrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#type_info.
    def visitType_info(self, ctx:AtopileParser.Type_infoContext):
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