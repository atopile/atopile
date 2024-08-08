# Generated from PythonParser.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .PythonParser import PythonParser
else:
    from PythonParser import PythonParser

# This class defines a complete generic visitor for a parse tree produced by PythonParser.

class PythonParserVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by PythonParser#file_input.
    def visitFile_input(self, ctx:PythonParser.File_inputContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#interactive.
    def visitInteractive(self, ctx:PythonParser.InteractiveContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#eval.
    def visitEval(self, ctx:PythonParser.EvalContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#func_type.
    def visitFunc_type(self, ctx:PythonParser.Func_typeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#fstring_input.
    def visitFstring_input(self, ctx:PythonParser.Fstring_inputContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#statements.
    def visitStatements(self, ctx:PythonParser.StatementsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#statement.
    def visitStatement(self, ctx:PythonParser.StatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#statement_newline.
    def visitStatement_newline(self, ctx:PythonParser.Statement_newlineContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#simple_stmts.
    def visitSimple_stmts(self, ctx:PythonParser.Simple_stmtsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#simple_stmt.
    def visitSimple_stmt(self, ctx:PythonParser.Simple_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#compound_stmt.
    def visitCompound_stmt(self, ctx:PythonParser.Compound_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#assignment.
    def visitAssignment(self, ctx:PythonParser.AssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#annotated_rhs.
    def visitAnnotated_rhs(self, ctx:PythonParser.Annotated_rhsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#augassign.
    def visitAugassign(self, ctx:PythonParser.AugassignContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#return_stmt.
    def visitReturn_stmt(self, ctx:PythonParser.Return_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#raise_stmt.
    def visitRaise_stmt(self, ctx:PythonParser.Raise_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#global_stmt.
    def visitGlobal_stmt(self, ctx:PythonParser.Global_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#nonlocal_stmt.
    def visitNonlocal_stmt(self, ctx:PythonParser.Nonlocal_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#del_stmt.
    def visitDel_stmt(self, ctx:PythonParser.Del_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#yield_stmt.
    def visitYield_stmt(self, ctx:PythonParser.Yield_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#assert_stmt.
    def visitAssert_stmt(self, ctx:PythonParser.Assert_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#import_stmt.
    def visitImport_stmt(self, ctx:PythonParser.Import_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#import_name.
    def visitImport_name(self, ctx:PythonParser.Import_nameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#import_from.
    def visitImport_from(self, ctx:PythonParser.Import_fromContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#import_from_targets.
    def visitImport_from_targets(self, ctx:PythonParser.Import_from_targetsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#import_from_as_names.
    def visitImport_from_as_names(self, ctx:PythonParser.Import_from_as_namesContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#import_from_as_name.
    def visitImport_from_as_name(self, ctx:PythonParser.Import_from_as_nameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#dotted_as_names.
    def visitDotted_as_names(self, ctx:PythonParser.Dotted_as_namesContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#dotted_as_name.
    def visitDotted_as_name(self, ctx:PythonParser.Dotted_as_nameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#dotted_name.
    def visitDotted_name(self, ctx:PythonParser.Dotted_nameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#block.
    def visitBlock(self, ctx:PythonParser.BlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#decorators.
    def visitDecorators(self, ctx:PythonParser.DecoratorsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#class_def.
    def visitClass_def(self, ctx:PythonParser.Class_defContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#class_def_raw.
    def visitClass_def_raw(self, ctx:PythonParser.Class_def_rawContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#function_def.
    def visitFunction_def(self, ctx:PythonParser.Function_defContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#function_def_raw.
    def visitFunction_def_raw(self, ctx:PythonParser.Function_def_rawContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#params.
    def visitParams(self, ctx:PythonParser.ParamsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#parameters.
    def visitParameters(self, ctx:PythonParser.ParametersContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#slash_no_default.
    def visitSlash_no_default(self, ctx:PythonParser.Slash_no_defaultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#slash_with_default.
    def visitSlash_with_default(self, ctx:PythonParser.Slash_with_defaultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#star_etc.
    def visitStar_etc(self, ctx:PythonParser.Star_etcContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#kwds.
    def visitKwds(self, ctx:PythonParser.KwdsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#param_no_default.
    def visitParam_no_default(self, ctx:PythonParser.Param_no_defaultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#param_no_default_star_annotation.
    def visitParam_no_default_star_annotation(self, ctx:PythonParser.Param_no_default_star_annotationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#param_with_default.
    def visitParam_with_default(self, ctx:PythonParser.Param_with_defaultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#param_maybe_default.
    def visitParam_maybe_default(self, ctx:PythonParser.Param_maybe_defaultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#param.
    def visitParam(self, ctx:PythonParser.ParamContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#param_star_annotation.
    def visitParam_star_annotation(self, ctx:PythonParser.Param_star_annotationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#annotation.
    def visitAnnotation(self, ctx:PythonParser.AnnotationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#star_annotation.
    def visitStar_annotation(self, ctx:PythonParser.Star_annotationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#default_assignment.
    def visitDefault_assignment(self, ctx:PythonParser.Default_assignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#if_stmt.
    def visitIf_stmt(self, ctx:PythonParser.If_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#elif_stmt.
    def visitElif_stmt(self, ctx:PythonParser.Elif_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#else_block.
    def visitElse_block(self, ctx:PythonParser.Else_blockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#while_stmt.
    def visitWhile_stmt(self, ctx:PythonParser.While_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#for_stmt.
    def visitFor_stmt(self, ctx:PythonParser.For_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#with_stmt.
    def visitWith_stmt(self, ctx:PythonParser.With_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#with_item.
    def visitWith_item(self, ctx:PythonParser.With_itemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#try_stmt.
    def visitTry_stmt(self, ctx:PythonParser.Try_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#except_block.
    def visitExcept_block(self, ctx:PythonParser.Except_blockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#except_star_block.
    def visitExcept_star_block(self, ctx:PythonParser.Except_star_blockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#finally_block.
    def visitFinally_block(self, ctx:PythonParser.Finally_blockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#match_stmt.
    def visitMatch_stmt(self, ctx:PythonParser.Match_stmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#subject_expr.
    def visitSubject_expr(self, ctx:PythonParser.Subject_exprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#case_block.
    def visitCase_block(self, ctx:PythonParser.Case_blockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#guard.
    def visitGuard(self, ctx:PythonParser.GuardContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#patterns.
    def visitPatterns(self, ctx:PythonParser.PatternsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#pattern.
    def visitPattern(self, ctx:PythonParser.PatternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#as_pattern.
    def visitAs_pattern(self, ctx:PythonParser.As_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#or_pattern.
    def visitOr_pattern(self, ctx:PythonParser.Or_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#closed_pattern.
    def visitClosed_pattern(self, ctx:PythonParser.Closed_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#literal_pattern.
    def visitLiteral_pattern(self, ctx:PythonParser.Literal_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#literal_expr.
    def visitLiteral_expr(self, ctx:PythonParser.Literal_exprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#complex_number.
    def visitComplex_number(self, ctx:PythonParser.Complex_numberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#signed_number.
    def visitSigned_number(self, ctx:PythonParser.Signed_numberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#signed_real_number.
    def visitSigned_real_number(self, ctx:PythonParser.Signed_real_numberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#real_number.
    def visitReal_number(self, ctx:PythonParser.Real_numberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#imaginary_number.
    def visitImaginary_number(self, ctx:PythonParser.Imaginary_numberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#capture_pattern.
    def visitCapture_pattern(self, ctx:PythonParser.Capture_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#pattern_capture_target.
    def visitPattern_capture_target(self, ctx:PythonParser.Pattern_capture_targetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#wildcard_pattern.
    def visitWildcard_pattern(self, ctx:PythonParser.Wildcard_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#value_pattern.
    def visitValue_pattern(self, ctx:PythonParser.Value_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#attr.
    def visitAttr(self, ctx:PythonParser.AttrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#name_or_attr.
    def visitName_or_attr(self, ctx:PythonParser.Name_or_attrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#group_pattern.
    def visitGroup_pattern(self, ctx:PythonParser.Group_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#sequence_pattern.
    def visitSequence_pattern(self, ctx:PythonParser.Sequence_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#open_sequence_pattern.
    def visitOpen_sequence_pattern(self, ctx:PythonParser.Open_sequence_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#maybe_sequence_pattern.
    def visitMaybe_sequence_pattern(self, ctx:PythonParser.Maybe_sequence_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#maybe_star_pattern.
    def visitMaybe_star_pattern(self, ctx:PythonParser.Maybe_star_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#star_pattern.
    def visitStar_pattern(self, ctx:PythonParser.Star_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#mapping_pattern.
    def visitMapping_pattern(self, ctx:PythonParser.Mapping_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#items_pattern.
    def visitItems_pattern(self, ctx:PythonParser.Items_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#key_value_pattern.
    def visitKey_value_pattern(self, ctx:PythonParser.Key_value_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#double_star_pattern.
    def visitDouble_star_pattern(self, ctx:PythonParser.Double_star_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#class_pattern.
    def visitClass_pattern(self, ctx:PythonParser.Class_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#positional_patterns.
    def visitPositional_patterns(self, ctx:PythonParser.Positional_patternsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#keyword_patterns.
    def visitKeyword_patterns(self, ctx:PythonParser.Keyword_patternsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#keyword_pattern.
    def visitKeyword_pattern(self, ctx:PythonParser.Keyword_patternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#type_alias.
    def visitType_alias(self, ctx:PythonParser.Type_aliasContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#type_params.
    def visitType_params(self, ctx:PythonParser.Type_paramsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#type_param_seq.
    def visitType_param_seq(self, ctx:PythonParser.Type_param_seqContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#type_param.
    def visitType_param(self, ctx:PythonParser.Type_paramContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#type_param_bound.
    def visitType_param_bound(self, ctx:PythonParser.Type_param_boundContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#expressions.
    def visitExpressions(self, ctx:PythonParser.ExpressionsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#expression.
    def visitExpression(self, ctx:PythonParser.ExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#yield_expr.
    def visitYield_expr(self, ctx:PythonParser.Yield_exprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#star_expressions.
    def visitStar_expressions(self, ctx:PythonParser.Star_expressionsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#star_expression.
    def visitStar_expression(self, ctx:PythonParser.Star_expressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#star_named_expressions.
    def visitStar_named_expressions(self, ctx:PythonParser.Star_named_expressionsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#star_named_expression.
    def visitStar_named_expression(self, ctx:PythonParser.Star_named_expressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#assignment_expression.
    def visitAssignment_expression(self, ctx:PythonParser.Assignment_expressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#named_expression.
    def visitNamed_expression(self, ctx:PythonParser.Named_expressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#disjunction.
    def visitDisjunction(self, ctx:PythonParser.DisjunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#conjunction.
    def visitConjunction(self, ctx:PythonParser.ConjunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#inversion.
    def visitInversion(self, ctx:PythonParser.InversionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#comparison.
    def visitComparison(self, ctx:PythonParser.ComparisonContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#compare_op_bitwise_or_pair.
    def visitCompare_op_bitwise_or_pair(self, ctx:PythonParser.Compare_op_bitwise_or_pairContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#eq_bitwise_or.
    def visitEq_bitwise_or(self, ctx:PythonParser.Eq_bitwise_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#noteq_bitwise_or.
    def visitNoteq_bitwise_or(self, ctx:PythonParser.Noteq_bitwise_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#lte_bitwise_or.
    def visitLte_bitwise_or(self, ctx:PythonParser.Lte_bitwise_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#lt_bitwise_or.
    def visitLt_bitwise_or(self, ctx:PythonParser.Lt_bitwise_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#gte_bitwise_or.
    def visitGte_bitwise_or(self, ctx:PythonParser.Gte_bitwise_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#gt_bitwise_or.
    def visitGt_bitwise_or(self, ctx:PythonParser.Gt_bitwise_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#notin_bitwise_or.
    def visitNotin_bitwise_or(self, ctx:PythonParser.Notin_bitwise_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#in_bitwise_or.
    def visitIn_bitwise_or(self, ctx:PythonParser.In_bitwise_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#isnot_bitwise_or.
    def visitIsnot_bitwise_or(self, ctx:PythonParser.Isnot_bitwise_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#is_bitwise_or.
    def visitIs_bitwise_or(self, ctx:PythonParser.Is_bitwise_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#bitwise_or.
    def visitBitwise_or(self, ctx:PythonParser.Bitwise_orContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#bitwise_xor.
    def visitBitwise_xor(self, ctx:PythonParser.Bitwise_xorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#bitwise_and.
    def visitBitwise_and(self, ctx:PythonParser.Bitwise_andContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#shift_expr.
    def visitShift_expr(self, ctx:PythonParser.Shift_exprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#sum.
    def visitSum(self, ctx:PythonParser.SumContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#term.
    def visitTerm(self, ctx:PythonParser.TermContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#factor.
    def visitFactor(self, ctx:PythonParser.FactorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#power.
    def visitPower(self, ctx:PythonParser.PowerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#await_primary.
    def visitAwait_primary(self, ctx:PythonParser.Await_primaryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#primary.
    def visitPrimary(self, ctx:PythonParser.PrimaryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#slices.
    def visitSlices(self, ctx:PythonParser.SlicesContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#slice.
    def visitSlice(self, ctx:PythonParser.SliceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#atom.
    def visitAtom(self, ctx:PythonParser.AtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#group.
    def visitGroup(self, ctx:PythonParser.GroupContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#lambdef.
    def visitLambdef(self, ctx:PythonParser.LambdefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#lambda_params.
    def visitLambda_params(self, ctx:PythonParser.Lambda_paramsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#lambda_parameters.
    def visitLambda_parameters(self, ctx:PythonParser.Lambda_parametersContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#lambda_slash_no_default.
    def visitLambda_slash_no_default(self, ctx:PythonParser.Lambda_slash_no_defaultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#lambda_slash_with_default.
    def visitLambda_slash_with_default(self, ctx:PythonParser.Lambda_slash_with_defaultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#lambda_star_etc.
    def visitLambda_star_etc(self, ctx:PythonParser.Lambda_star_etcContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#lambda_kwds.
    def visitLambda_kwds(self, ctx:PythonParser.Lambda_kwdsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#lambda_param_no_default.
    def visitLambda_param_no_default(self, ctx:PythonParser.Lambda_param_no_defaultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#lambda_param_with_default.
    def visitLambda_param_with_default(self, ctx:PythonParser.Lambda_param_with_defaultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#lambda_param_maybe_default.
    def visitLambda_param_maybe_default(self, ctx:PythonParser.Lambda_param_maybe_defaultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#lambda_param.
    def visitLambda_param(self, ctx:PythonParser.Lambda_paramContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#fstring_middle.
    def visitFstring_middle(self, ctx:PythonParser.Fstring_middleContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#fstring_replacement_field.
    def visitFstring_replacement_field(self, ctx:PythonParser.Fstring_replacement_fieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#fstring_conversion.
    def visitFstring_conversion(self, ctx:PythonParser.Fstring_conversionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#fstring_full_format_spec.
    def visitFstring_full_format_spec(self, ctx:PythonParser.Fstring_full_format_specContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#fstring_format_spec.
    def visitFstring_format_spec(self, ctx:PythonParser.Fstring_format_specContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#fstring.
    def visitFstring(self, ctx:PythonParser.FstringContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#string.
    def visitString(self, ctx:PythonParser.StringContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#strings.
    def visitStrings(self, ctx:PythonParser.StringsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#list.
    def visitList(self, ctx:PythonParser.ListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#tuple.
    def visitTuple(self, ctx:PythonParser.TupleContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#set.
    def visitSet(self, ctx:PythonParser.SetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#dict.
    def visitDict(self, ctx:PythonParser.DictContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#double_starred_kvpairs.
    def visitDouble_starred_kvpairs(self, ctx:PythonParser.Double_starred_kvpairsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#double_starred_kvpair.
    def visitDouble_starred_kvpair(self, ctx:PythonParser.Double_starred_kvpairContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#kvpair.
    def visitKvpair(self, ctx:PythonParser.KvpairContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#for_if_clauses.
    def visitFor_if_clauses(self, ctx:PythonParser.For_if_clausesContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#for_if_clause.
    def visitFor_if_clause(self, ctx:PythonParser.For_if_clauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#listcomp.
    def visitListcomp(self, ctx:PythonParser.ListcompContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#setcomp.
    def visitSetcomp(self, ctx:PythonParser.SetcompContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#genexp.
    def visitGenexp(self, ctx:PythonParser.GenexpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#dictcomp.
    def visitDictcomp(self, ctx:PythonParser.DictcompContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#arguments.
    def visitArguments(self, ctx:PythonParser.ArgumentsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#args.
    def visitArgs(self, ctx:PythonParser.ArgsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#kwargs.
    def visitKwargs(self, ctx:PythonParser.KwargsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#starred_expression.
    def visitStarred_expression(self, ctx:PythonParser.Starred_expressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#kwarg_or_starred.
    def visitKwarg_or_starred(self, ctx:PythonParser.Kwarg_or_starredContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#kwarg_or_double_starred.
    def visitKwarg_or_double_starred(self, ctx:PythonParser.Kwarg_or_double_starredContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#star_targets.
    def visitStar_targets(self, ctx:PythonParser.Star_targetsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#star_targets_list_seq.
    def visitStar_targets_list_seq(self, ctx:PythonParser.Star_targets_list_seqContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#star_targets_tuple_seq.
    def visitStar_targets_tuple_seq(self, ctx:PythonParser.Star_targets_tuple_seqContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#star_target.
    def visitStar_target(self, ctx:PythonParser.Star_targetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#target_with_star_atom.
    def visitTarget_with_star_atom(self, ctx:PythonParser.Target_with_star_atomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#star_atom.
    def visitStar_atom(self, ctx:PythonParser.Star_atomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#single_target.
    def visitSingle_target(self, ctx:PythonParser.Single_targetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#single_subscript_attribute_target.
    def visitSingle_subscript_attribute_target(self, ctx:PythonParser.Single_subscript_attribute_targetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#t_primary.
    def visitT_primary(self, ctx:PythonParser.T_primaryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#del_targets.
    def visitDel_targets(self, ctx:PythonParser.Del_targetsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#del_target.
    def visitDel_target(self, ctx:PythonParser.Del_targetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#del_t_atom.
    def visitDel_t_atom(self, ctx:PythonParser.Del_t_atomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#type_expressions.
    def visitType_expressions(self, ctx:PythonParser.Type_expressionsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#func_type_comment.
    def visitFunc_type_comment(self, ctx:PythonParser.Func_type_commentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#soft_kw_type.
    def visitSoft_kw_type(self, ctx:PythonParser.Soft_kw_typeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#soft_kw_match.
    def visitSoft_kw_match(self, ctx:PythonParser.Soft_kw_matchContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#soft_kw_case.
    def visitSoft_kw_case(self, ctx:PythonParser.Soft_kw_caseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#soft_kw_wildcard.
    def visitSoft_kw_wildcard(self, ctx:PythonParser.Soft_kw_wildcardContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PythonParser#soft_kw__not__wildcard.
    def visitSoft_kw__not__wildcard(self, ctx:PythonParser.Soft_kw__not__wildcardContext):
        return self.visitChildren(ctx)



del PythonParser