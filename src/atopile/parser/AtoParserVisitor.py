# Generated from AtoParser.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .AtoParser import AtoParser
else:
    from AtoParser import AtoParser

# This class defines a complete generic visitor for a parse tree produced by AtoParser.

class AtoParserVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by AtoParser#file_input.
    def visitFile_input(self, ctx:AtoParser.File_inputContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#stmt.
    def visitStmt(self, ctx:AtoParser.StmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#simple_stmts.
    def visitSimple_stmts(self, ctx:AtoParser.Simple_stmtsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#simple_stmt.
    def visitSimple_stmt(self, ctx:AtoParser.Simple_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#compound_stmt.
    def visitCompound_stmt(self, ctx:AtoParser.Compound_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#blockdef.
    def visitBlockdef(self, ctx:AtoParser.BlockdefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#blockdef_super.
    def visitBlockdef_super(self, ctx:AtoParser.Blockdef_superContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#blocktype.
    def visitBlocktype(self, ctx:AtoParser.BlocktypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#block.
    def visitBlock(self, ctx:AtoParser.BlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#dep_import_stmt.
    def visitDep_import_stmt(self, ctx:AtoParser.Dep_import_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#import_stmt.
    def visitImport_stmt(self, ctx:AtoParser.Import_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#declaration_stmt.
    def visitDeclaration_stmt(self, ctx:AtoParser.Declaration_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#assign_stmt.
    def visitAssign_stmt(self, ctx:AtoParser.Assign_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#cum_assign_stmt.
    def visitCum_assign_stmt(self, ctx:AtoParser.Cum_assign_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#set_assign_stmt.
    def visitSet_assign_stmt(self, ctx:AtoParser.Set_assign_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#cum_operator.
    def visitCum_operator(self, ctx:AtoParser.Cum_operatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#cum_assignable.
    def visitCum_assignable(self, ctx:AtoParser.Cum_assignableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#assignable.
    def visitAssignable(self, ctx:AtoParser.AssignableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#retype_stmt.
    def visitRetype_stmt(self, ctx:AtoParser.Retype_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#connect_stmt.
    def visitConnect_stmt(self, ctx:AtoParser.Connect_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#connectable.
    def visitConnectable(self, ctx:AtoParser.ConnectableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#signaldef_stmt.
    def visitSignaldef_stmt(self, ctx:AtoParser.Signaldef_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#pindef_stmt.
    def visitPindef_stmt(self, ctx:AtoParser.Pindef_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#new_stmt.
    def visitNew_stmt(self, ctx:AtoParser.New_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#string_stmt.
    def visitString_stmt(self, ctx:AtoParser.String_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#pass_stmt.
    def visitPass_stmt(self, ctx:AtoParser.Pass_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#assert_stmt.
    def visitAssert_stmt(self, ctx:AtoParser.Assert_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#comparison.
    def visitComparison(self, ctx:AtoParser.ComparisonContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#compare_op_pair.
    def visitCompare_op_pair(self, ctx:AtoParser.Compare_op_pairContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#lt_arithmetic_or.
    def visitLt_arithmetic_or(self, ctx:AtoParser.Lt_arithmetic_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#gt_arithmetic_or.
    def visitGt_arithmetic_or(self, ctx:AtoParser.Gt_arithmetic_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#lt_eq_arithmetic_or.
    def visitLt_eq_arithmetic_or(self, ctx:AtoParser.Lt_eq_arithmetic_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#gt_eq_arithmetic_or.
    def visitGt_eq_arithmetic_or(self, ctx:AtoParser.Gt_eq_arithmetic_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#in_arithmetic_or.
    def visitIn_arithmetic_or(self, ctx:AtoParser.In_arithmetic_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#arithmetic_expression.
    def visitArithmetic_expression(self, ctx:AtoParser.Arithmetic_expressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#sum.
    def visitSum(self, ctx:AtoParser.SumContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#term.
    def visitTerm(self, ctx:AtoParser.TermContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#power.
    def visitPower(self, ctx:AtoParser.PowerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#functional.
    def visitFunctional(self, ctx:AtoParser.FunctionalContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#bound.
    def visitBound(self, ctx:AtoParser.BoundContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#atom.
    def visitAtom(self, ctx:AtoParser.AtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#arithmetic_group.
    def visitArithmetic_group(self, ctx:AtoParser.Arithmetic_groupContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#literal_physical.
    def visitLiteral_physical(self, ctx:AtoParser.Literal_physicalContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#bound_quantity.
    def visitBound_quantity(self, ctx:AtoParser.Bound_quantityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#bilateral_quantity.
    def visitBilateral_quantity(self, ctx:AtoParser.Bilateral_quantityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#quantity.
    def visitQuantity(self, ctx:AtoParser.QuantityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#bilateral_tolerance.
    def visitBilateral_tolerance(self, ctx:AtoParser.Bilateral_toleranceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#name_or_attr.
    def visitName_or_attr(self, ctx:AtoParser.Name_or_attrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#type_info.
    def visitType_info(self, ctx:AtoParser.Type_infoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#numerical_pin_ref.
    def visitNumerical_pin_ref(self, ctx:AtoParser.Numerical_pin_refContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#attr.
    def visitAttr(self, ctx:AtoParser.AttrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#totally_an_integer.
    def visitTotally_an_integer(self, ctx:AtoParser.Totally_an_integerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#name.
    def visitName(self, ctx:AtoParser.NameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#string.
    def visitString(self, ctx:AtoParser.StringContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtoParser#boolean_.
    def visitBoolean_(self, ctx:AtoParser.Boolean_Context):
        return self.visitChildren(ctx)



del AtoParser