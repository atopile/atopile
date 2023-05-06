# Generated from AtopileParser.g4 by ANTLR 4.12.0
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .AtopileParser import AtopileParser
else:
    from AtopileParser import AtopileParser

# This class defines a complete generic visitor for a parse tree produced by AtopileParser.

class AtopileParserVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by AtopileParser#single_input.
    def visitSingle_input(self, ctx:AtopileParser.Single_inputContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#file_input.
    def visitFile_input(self, ctx:AtopileParser.File_inputContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#eval_input.
    def visitEval_input(self, ctx:AtopileParser.Eval_inputContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#decorator.
    def visitDecorator(self, ctx:AtopileParser.DecoratorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#decorators.
    def visitDecorators(self, ctx:AtopileParser.DecoratorsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#decorated.
    def visitDecorated(self, ctx:AtopileParser.DecoratedContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#async_funcdef.
    def visitAsync_funcdef(self, ctx:AtopileParser.Async_funcdefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#funcdef.
    def visitFuncdef(self, ctx:AtopileParser.FuncdefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#parameters.
    def visitParameters(self, ctx:AtopileParser.ParametersContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#typedargslist.
    def visitTypedargslist(self, ctx:AtopileParser.TypedargslistContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#tfpdef.
    def visitTfpdef(self, ctx:AtopileParser.TfpdefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#varargslist.
    def visitVarargslist(self, ctx:AtopileParser.VarargslistContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#vfpdef.
    def visitVfpdef(self, ctx:AtopileParser.VfpdefContext):
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


    # Visit a parse tree produced by AtopileParser#expr_stmt.
    def visitExpr_stmt(self, ctx:AtopileParser.Expr_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#annassign.
    def visitAnnassign(self, ctx:AtopileParser.AnnassignContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#testlist_star_expr.
    def visitTestlist_star_expr(self, ctx:AtopileParser.Testlist_star_exprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#augassign.
    def visitAugassign(self, ctx:AtopileParser.AugassignContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#del_stmt.
    def visitDel_stmt(self, ctx:AtopileParser.Del_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#pass_stmt.
    def visitPass_stmt(self, ctx:AtopileParser.Pass_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#flow_stmt.
    def visitFlow_stmt(self, ctx:AtopileParser.Flow_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#break_stmt.
    def visitBreak_stmt(self, ctx:AtopileParser.Break_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#continue_stmt.
    def visitContinue_stmt(self, ctx:AtopileParser.Continue_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#return_stmt.
    def visitReturn_stmt(self, ctx:AtopileParser.Return_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#yield_stmt.
    def visitYield_stmt(self, ctx:AtopileParser.Yield_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#raise_stmt.
    def visitRaise_stmt(self, ctx:AtopileParser.Raise_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#import_stmt.
    def visitImport_stmt(self, ctx:AtopileParser.Import_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#import_name.
    def visitImport_name(self, ctx:AtopileParser.Import_nameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#import_from.
    def visitImport_from(self, ctx:AtopileParser.Import_fromContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#import_as_name.
    def visitImport_as_name(self, ctx:AtopileParser.Import_as_nameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#dotted_as_name.
    def visitDotted_as_name(self, ctx:AtopileParser.Dotted_as_nameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#import_as_names.
    def visitImport_as_names(self, ctx:AtopileParser.Import_as_namesContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#dotted_as_names.
    def visitDotted_as_names(self, ctx:AtopileParser.Dotted_as_namesContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#dotted_name.
    def visitDotted_name(self, ctx:AtopileParser.Dotted_nameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#global_stmt.
    def visitGlobal_stmt(self, ctx:AtopileParser.Global_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#nonlocal_stmt.
    def visitNonlocal_stmt(self, ctx:AtopileParser.Nonlocal_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#assert_stmt.
    def visitAssert_stmt(self, ctx:AtopileParser.Assert_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#compound_stmt.
    def visitCompound_stmt(self, ctx:AtopileParser.Compound_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#async_stmt.
    def visitAsync_stmt(self, ctx:AtopileParser.Async_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#if_stmt.
    def visitIf_stmt(self, ctx:AtopileParser.If_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#while_stmt.
    def visitWhile_stmt(self, ctx:AtopileParser.While_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#for_stmt.
    def visitFor_stmt(self, ctx:AtopileParser.For_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#try_stmt.
    def visitTry_stmt(self, ctx:AtopileParser.Try_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#with_stmt.
    def visitWith_stmt(self, ctx:AtopileParser.With_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#with_item.
    def visitWith_item(self, ctx:AtopileParser.With_itemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#except_clause.
    def visitExcept_clause(self, ctx:AtopileParser.Except_clauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#block.
    def visitBlock(self, ctx:AtopileParser.BlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#match_stmt.
    def visitMatch_stmt(self, ctx:AtopileParser.Match_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#subject_expr.
    def visitSubject_expr(self, ctx:AtopileParser.Subject_exprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#star_named_expressions.
    def visitStar_named_expressions(self, ctx:AtopileParser.Star_named_expressionsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#star_named_expression.
    def visitStar_named_expression(self, ctx:AtopileParser.Star_named_expressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#case_block.
    def visitCase_block(self, ctx:AtopileParser.Case_blockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#guard.
    def visitGuard(self, ctx:AtopileParser.GuardContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#patterns.
    def visitPatterns(self, ctx:AtopileParser.PatternsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#pattern.
    def visitPattern(self, ctx:AtopileParser.PatternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#as_pattern.
    def visitAs_pattern(self, ctx:AtopileParser.As_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#or_pattern.
    def visitOr_pattern(self, ctx:AtopileParser.Or_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#closed_pattern.
    def visitClosed_pattern(self, ctx:AtopileParser.Closed_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#literal_pattern.
    def visitLiteral_pattern(self, ctx:AtopileParser.Literal_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#literal_expr.
    def visitLiteral_expr(self, ctx:AtopileParser.Literal_exprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#complex_number.
    def visitComplex_number(self, ctx:AtopileParser.Complex_numberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#signed_number.
    def visitSigned_number(self, ctx:AtopileParser.Signed_numberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#signed_real_number.
    def visitSigned_real_number(self, ctx:AtopileParser.Signed_real_numberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#real_number.
    def visitReal_number(self, ctx:AtopileParser.Real_numberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#imaginary_number.
    def visitImaginary_number(self, ctx:AtopileParser.Imaginary_numberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#capture_pattern.
    def visitCapture_pattern(self, ctx:AtopileParser.Capture_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#pattern_capture_target.
    def visitPattern_capture_target(self, ctx:AtopileParser.Pattern_capture_targetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#wildcard_pattern.
    def visitWildcard_pattern(self, ctx:AtopileParser.Wildcard_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#value_pattern.
    def visitValue_pattern(self, ctx:AtopileParser.Value_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#attr.
    def visitAttr(self, ctx:AtopileParser.AttrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#name_or_attr.
    def visitName_or_attr(self, ctx:AtopileParser.Name_or_attrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#group_pattern.
    def visitGroup_pattern(self, ctx:AtopileParser.Group_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#sequence_pattern.
    def visitSequence_pattern(self, ctx:AtopileParser.Sequence_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#open_sequence_pattern.
    def visitOpen_sequence_pattern(self, ctx:AtopileParser.Open_sequence_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#maybe_sequence_pattern.
    def visitMaybe_sequence_pattern(self, ctx:AtopileParser.Maybe_sequence_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#maybe_star_pattern.
    def visitMaybe_star_pattern(self, ctx:AtopileParser.Maybe_star_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#star_pattern.
    def visitStar_pattern(self, ctx:AtopileParser.Star_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#mapping_pattern.
    def visitMapping_pattern(self, ctx:AtopileParser.Mapping_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#items_pattern.
    def visitItems_pattern(self, ctx:AtopileParser.Items_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#key_value_pattern.
    def visitKey_value_pattern(self, ctx:AtopileParser.Key_value_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#double_star_pattern.
    def visitDouble_star_pattern(self, ctx:AtopileParser.Double_star_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#class_pattern.
    def visitClass_pattern(self, ctx:AtopileParser.Class_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#positional_patterns.
    def visitPositional_patterns(self, ctx:AtopileParser.Positional_patternsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#keyword_patterns.
    def visitKeyword_patterns(self, ctx:AtopileParser.Keyword_patternsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#keyword_pattern.
    def visitKeyword_pattern(self, ctx:AtopileParser.Keyword_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#test.
    def visitTest(self, ctx:AtopileParser.TestContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#test_nocond.
    def visitTest_nocond(self, ctx:AtopileParser.Test_nocondContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#lambdef.
    def visitLambdef(self, ctx:AtopileParser.LambdefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#lambdef_nocond.
    def visitLambdef_nocond(self, ctx:AtopileParser.Lambdef_nocondContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#or_test.
    def visitOr_test(self, ctx:AtopileParser.Or_testContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#and_test.
    def visitAnd_test(self, ctx:AtopileParser.And_testContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#not_test.
    def visitNot_test(self, ctx:AtopileParser.Not_testContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#comparison.
    def visitComparison(self, ctx:AtopileParser.ComparisonContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#comp_op.
    def visitComp_op(self, ctx:AtopileParser.Comp_opContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#star_expr.
    def visitStar_expr(self, ctx:AtopileParser.Star_exprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#expr.
    def visitExpr(self, ctx:AtopileParser.ExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#xor_expr.
    def visitXor_expr(self, ctx:AtopileParser.Xor_exprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#and_expr.
    def visitAnd_expr(self, ctx:AtopileParser.And_exprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#shift_expr.
    def visitShift_expr(self, ctx:AtopileParser.Shift_exprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#arith_expr.
    def visitArith_expr(self, ctx:AtopileParser.Arith_exprContext):
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


    # Visit a parse tree produced by AtopileParser#atom_expr.
    def visitAtom_expr(self, ctx:AtopileParser.Atom_exprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#atom.
    def visitAtom(self, ctx:AtopileParser.AtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#name.
    def visitName(self, ctx:AtopileParser.NameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#testlist_comp.
    def visitTestlist_comp(self, ctx:AtopileParser.Testlist_compContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#trailer.
    def visitTrailer(self, ctx:AtopileParser.TrailerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#subscriptlist.
    def visitSubscriptlist(self, ctx:AtopileParser.SubscriptlistContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#subscript_.
    def visitSubscript_(self, ctx:AtopileParser.Subscript_Context):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#sliceop.
    def visitSliceop(self, ctx:AtopileParser.SliceopContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#exprlist.
    def visitExprlist(self, ctx:AtopileParser.ExprlistContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#testlist.
    def visitTestlist(self, ctx:AtopileParser.TestlistContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#dictorsetmaker.
    def visitDictorsetmaker(self, ctx:AtopileParser.DictorsetmakerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#classdef.
    def visitClassdef(self, ctx:AtopileParser.ClassdefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#arglist.
    def visitArglist(self, ctx:AtopileParser.ArglistContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#argument.
    def visitArgument(self, ctx:AtopileParser.ArgumentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#comp_iter.
    def visitComp_iter(self, ctx:AtopileParser.Comp_iterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#comp_for.
    def visitComp_for(self, ctx:AtopileParser.Comp_forContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#comp_if.
    def visitComp_if(self, ctx:AtopileParser.Comp_ifContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#encoding_decl.
    def visitEncoding_decl(self, ctx:AtopileParser.Encoding_declContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#yield_expr.
    def visitYield_expr(self, ctx:AtopileParser.Yield_exprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#yield_arg.
    def visitYield_arg(self, ctx:AtopileParser.Yield_argContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by AtopileParser#strings.
    def visitStrings(self, ctx:AtopileParser.StringsContext):
        return self.visitChildren(ctx)



del AtopileParser