// Generated from /Users/mattwildoer/Projects/atopile-workspace/atopile/sandbox/atx/PythonParser.g4 by ANTLR 4.13.1
import org.antlr.v4.runtime.atn.*;
import org.antlr.v4.runtime.dfa.DFA;
import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.misc.*;
import org.antlr.v4.runtime.tree.*;
import java.util.List;
import java.util.Iterator;
import java.util.ArrayList;

@SuppressWarnings({"all", "warnings", "unchecked", "unused", "cast", "CheckReturnValue"})
public class PythonParser extends PythonParserBase {
	static { RuntimeMetaData.checkVersion("4.13.1", RuntimeMetaData.VERSION); }

	protected static final DFA[] _decisionToDFA;
	protected static final PredictionContextCache _sharedContextCache =
		new PredictionContextCache();
	public static final int
		INDENT=1, DEDENT=2, FSTRING_START=3, FSTRING_MIDDLE=4, FSTRING_END=5, 
		FALSE=6, AWAIT=7, ELSE=8, IMPORT=9, PASS=10, NONE=11, BREAK=12, EXCEPT=13, 
		IN=14, RAISE=15, TRUE=16, CLASS=17, FINALLY=18, IS=19, RETURN=20, AND=21, 
		CONTINUE=22, FOR=23, LAMBDA=24, TRY=25, AS=26, DEF=27, FROM=28, NONLOCAL=29, 
		WHILE=30, ASSERT=31, DEL=32, GLOBAL=33, NOT=34, WITH=35, ASYNC=36, ELIF=37, 
		IF=38, OR=39, YIELD=40, WITHIN=41, TO=42, LPAR=43, LSQB=44, LBRACE=45, 
		RPAR=46, RSQB=47, RBRACE=48, DOT=49, COLON=50, COMMA=51, SEMI=52, PLUS=53, 
		MINUS=54, STAR=55, SLASH=56, VBAR=57, AMPER=58, LESS=59, GREATER=60, EQUAL=61, 
		PERCENT=62, EQEQUAL=63, NOTEQUAL=64, LESSEQUAL=65, GREATEREQUAL=66, TILDE=67, 
		CIRCUMFLEX=68, LEFTSHIFT=69, RIGHTSHIFT=70, DOUBLESTAR=71, PLUSEQUAL=72, 
		MINEQUAL=73, STAREQUAL=74, SLASHEQUAL=75, PERCENTEQUAL=76, AMPEREQUAL=77, 
		VBAREQUAL=78, CIRCUMFLEXEQUAL=79, LEFTSHIFTEQUAL=80, RIGHTSHIFTEQUAL=81, 
		DOUBLESTAREQUAL=82, DOUBLESLASH=83, DOUBLESLASHEQUAL=84, AT=85, ATEQUAL=86, 
		RARROW=87, ELLIPSIS=88, COLONEQUAL=89, EXCLAMATION=90, PLUS_OR_MINUS=91, 
		PLUS_OR_MINU2=92, NAME=93, NUMBER=94, STRING=95, TYPE_COMMENT=96, NEWLINE=97, 
		COMMENT=98, WS=99, EXPLICIT_LINE_JOINING=100, ERROR_TOKEN=101;
	public static final int
		RULE_file_input = 0, RULE_interactive = 1, RULE_eval = 2, RULE_func_type = 3, 
		RULE_fstring_input = 4, RULE_statements = 5, RULE_statement = 6, RULE_statement_newline = 7, 
		RULE_simple_stmts = 8, RULE_simple_stmt = 9, RULE_compound_stmt = 10, 
		RULE_assignment = 11, RULE_annotated_rhs = 12, RULE_augassign = 13, RULE_return_stmt = 14, 
		RULE_raise_stmt = 15, RULE_global_stmt = 16, RULE_nonlocal_stmt = 17, 
		RULE_del_stmt = 18, RULE_yield_stmt = 19, RULE_assert_stmt = 20, RULE_import_stmt = 21, 
		RULE_connect_stmt = 22, RULE_import_name = 23, RULE_import_from = 24, 
		RULE_import_from_targets = 25, RULE_import_from_as_names = 26, RULE_import_from_as_name = 27, 
		RULE_dotted_as_names = 28, RULE_dotted_as_name = 29, RULE_dotted_name = 30, 
		RULE_block = 31, RULE_decorators = 32, RULE_class_def = 33, RULE_class_def_raw = 34, 
		RULE_function_def = 35, RULE_function_def_raw = 36, RULE_params = 37, 
		RULE_parameters = 38, RULE_slash_no_default = 39, RULE_slash_with_default = 40, 
		RULE_star_etc = 41, RULE_kwds = 42, RULE_param_no_default = 43, RULE_param_no_default_star_annotation = 44, 
		RULE_param_with_default = 45, RULE_param_maybe_default = 46, RULE_param = 47, 
		RULE_param_star_annotation = 48, RULE_annotation = 49, RULE_star_annotation = 50, 
		RULE_default_assignment = 51, RULE_if_stmt = 52, RULE_elif_stmt = 53, 
		RULE_else_block = 54, RULE_while_stmt = 55, RULE_for_stmt = 56, RULE_with_stmt = 57, 
		RULE_with_item = 58, RULE_try_stmt = 59, RULE_except_block = 60, RULE_except_star_block = 61, 
		RULE_finally_block = 62, RULE_match_stmt = 63, RULE_subject_expr = 64, 
		RULE_case_block = 65, RULE_guard = 66, RULE_patterns = 67, RULE_pattern = 68, 
		RULE_as_pattern = 69, RULE_or_pattern = 70, RULE_closed_pattern = 71, 
		RULE_literal_pattern = 72, RULE_literal_expr = 73, RULE_signed_dimensioned_number = 74, 
		RULE_complex_number = 75, RULE_signed_number = 76, RULE_signed_real_number = 77, 
		RULE_real_number = 78, RULE_imaginary_number = 79, RULE_capture_pattern = 80, 
		RULE_pattern_capture_target = 81, RULE_wildcard_pattern = 82, RULE_value_pattern = 83, 
		RULE_attr = 84, RULE_name_or_attr = 85, RULE_group_pattern = 86, RULE_sequence_pattern = 87, 
		RULE_open_sequence_pattern = 88, RULE_maybe_sequence_pattern = 89, RULE_maybe_star_pattern = 90, 
		RULE_star_pattern = 91, RULE_mapping_pattern = 92, RULE_items_pattern = 93, 
		RULE_key_value_pattern = 94, RULE_double_star_pattern = 95, RULE_class_pattern = 96, 
		RULE_positional_patterns = 97, RULE_keyword_patterns = 98, RULE_keyword_pattern = 99, 
		RULE_type_alias = 100, RULE_type_params = 101, RULE_type_param_seq = 102, 
		RULE_type_param = 103, RULE_type_param_bound = 104, RULE_expressions = 105, 
		RULE_expression = 106, RULE_yield_expr = 107, RULE_star_expressions = 108, 
		RULE_star_expression = 109, RULE_star_named_expressions = 110, RULE_star_named_expression = 111, 
		RULE_assignment_expression = 112, RULE_named_expression = 113, RULE_disjunction = 114, 
		RULE_conjunction = 115, RULE_inversion = 116, RULE_comparison = 117, RULE_compare_op_bitwise_or_pair = 118, 
		RULE_eq_bitwise_or = 119, RULE_noteq_bitwise_or = 120, RULE_lte_bitwise_or = 121, 
		RULE_lt_bitwise_or = 122, RULE_gte_bitwise_or = 123, RULE_gt_bitwise_or = 124, 
		RULE_notin_bitwise_or = 125, RULE_in_bitwise_or = 126, RULE_isnot_bitwise_or = 127, 
		RULE_is_bitwise_or = 128, RULE_bitwise_or = 129, RULE_bitwise_xor = 130, 
		RULE_bitwise_and = 131, RULE_shift_expr = 132, RULE_sum = 133, RULE_term = 134, 
		RULE_tolerance = 135, RULE_factor = 136, RULE_power = 137, RULE_await_primary = 138, 
		RULE_primary = 139, RULE_slices = 140, RULE_slice = 141, RULE_atom = 142, 
		RULE_dimensioned_number = 143, RULE_group = 144, RULE_lambdef = 145, RULE_lambda_params = 146, 
		RULE_lambda_parameters = 147, RULE_lambda_slash_no_default = 148, RULE_lambda_slash_with_default = 149, 
		RULE_lambda_star_etc = 150, RULE_lambda_kwds = 151, RULE_lambda_param_no_default = 152, 
		RULE_lambda_param_with_default = 153, RULE_lambda_param_maybe_default = 154, 
		RULE_lambda_param = 155, RULE_fstring_middle = 156, RULE_fstring_replacement_field = 157, 
		RULE_fstring_conversion = 158, RULE_fstring_full_format_spec = 159, RULE_fstring_format_spec = 160, 
		RULE_fstring = 161, RULE_string = 162, RULE_strings = 163, RULE_list = 164, 
		RULE_tuple = 165, RULE_set = 166, RULE_dict = 167, RULE_double_starred_kvpairs = 168, 
		RULE_double_starred_kvpair = 169, RULE_kvpair = 170, RULE_for_if_clauses = 171, 
		RULE_for_if_clause = 172, RULE_listcomp = 173, RULE_setcomp = 174, RULE_genexp = 175, 
		RULE_dictcomp = 176, RULE_arguments = 177, RULE_args = 178, RULE_kwargs = 179, 
		RULE_starred_expression = 180, RULE_kwarg_or_starred = 181, RULE_kwarg_or_double_starred = 182, 
		RULE_star_targets = 183, RULE_star_targets_list_seq = 184, RULE_star_targets_tuple_seq = 185, 
		RULE_star_target = 186, RULE_target_with_star_atom = 187, RULE_star_atom = 188, 
		RULE_single_target = 189, RULE_single_subscript_attribute_target = 190, 
		RULE_t_primary = 191, RULE_del_targets = 192, RULE_del_target = 193, RULE_del_t_atom = 194, 
		RULE_type_expressions = 195, RULE_func_type_comment = 196, RULE_soft_kw_type = 197, 
		RULE_soft_kw_match = 198, RULE_soft_kw_case = 199, RULE_soft_kw_wildcard = 200, 
		RULE_soft_kw__not__wildcard = 201;
	private static String[] makeRuleNames() {
		return new String[] {
			"file_input", "interactive", "eval", "func_type", "fstring_input", "statements", 
			"statement", "statement_newline", "simple_stmts", "simple_stmt", "compound_stmt", 
			"assignment", "annotated_rhs", "augassign", "return_stmt", "raise_stmt", 
			"global_stmt", "nonlocal_stmt", "del_stmt", "yield_stmt", "assert_stmt", 
			"import_stmt", "connect_stmt", "import_name", "import_from", "import_from_targets", 
			"import_from_as_names", "import_from_as_name", "dotted_as_names", "dotted_as_name", 
			"dotted_name", "block", "decorators", "class_def", "class_def_raw", "function_def", 
			"function_def_raw", "params", "parameters", "slash_no_default", "slash_with_default", 
			"star_etc", "kwds", "param_no_default", "param_no_default_star_annotation", 
			"param_with_default", "param_maybe_default", "param", "param_star_annotation", 
			"annotation", "star_annotation", "default_assignment", "if_stmt", "elif_stmt", 
			"else_block", "while_stmt", "for_stmt", "with_stmt", "with_item", "try_stmt", 
			"except_block", "except_star_block", "finally_block", "match_stmt", "subject_expr", 
			"case_block", "guard", "patterns", "pattern", "as_pattern", "or_pattern", 
			"closed_pattern", "literal_pattern", "literal_expr", "signed_dimensioned_number", 
			"complex_number", "signed_number", "signed_real_number", "real_number", 
			"imaginary_number", "capture_pattern", "pattern_capture_target", "wildcard_pattern", 
			"value_pattern", "attr", "name_or_attr", "group_pattern", "sequence_pattern", 
			"open_sequence_pattern", "maybe_sequence_pattern", "maybe_star_pattern", 
			"star_pattern", "mapping_pattern", "items_pattern", "key_value_pattern", 
			"double_star_pattern", "class_pattern", "positional_patterns", "keyword_patterns", 
			"keyword_pattern", "type_alias", "type_params", "type_param_seq", "type_param", 
			"type_param_bound", "expressions", "expression", "yield_expr", "star_expressions", 
			"star_expression", "star_named_expressions", "star_named_expression", 
			"assignment_expression", "named_expression", "disjunction", "conjunction", 
			"inversion", "comparison", "compare_op_bitwise_or_pair", "eq_bitwise_or", 
			"noteq_bitwise_or", "lte_bitwise_or", "lt_bitwise_or", "gte_bitwise_or", 
			"gt_bitwise_or", "notin_bitwise_or", "in_bitwise_or", "isnot_bitwise_or", 
			"is_bitwise_or", "bitwise_or", "bitwise_xor", "bitwise_and", "shift_expr", 
			"sum", "term", "tolerance", "factor", "power", "await_primary", "primary", 
			"slices", "slice", "atom", "dimensioned_number", "group", "lambdef", 
			"lambda_params", "lambda_parameters", "lambda_slash_no_default", "lambda_slash_with_default", 
			"lambda_star_etc", "lambda_kwds", "lambda_param_no_default", "lambda_param_with_default", 
			"lambda_param_maybe_default", "lambda_param", "fstring_middle", "fstring_replacement_field", 
			"fstring_conversion", "fstring_full_format_spec", "fstring_format_spec", 
			"fstring", "string", "strings", "list", "tuple", "set", "dict", "double_starred_kvpairs", 
			"double_starred_kvpair", "kvpair", "for_if_clauses", "for_if_clause", 
			"listcomp", "setcomp", "genexp", "dictcomp", "arguments", "args", "kwargs", 
			"starred_expression", "kwarg_or_starred", "kwarg_or_double_starred", 
			"star_targets", "star_targets_list_seq", "star_targets_tuple_seq", "star_target", 
			"target_with_star_atom", "star_atom", "single_target", "single_subscript_attribute_target", 
			"t_primary", "del_targets", "del_target", "del_t_atom", "type_expressions", 
			"func_type_comment", "soft_kw_type", "soft_kw_match", "soft_kw_case", 
			"soft_kw_wildcard", "soft_kw__not__wildcard"
		};
	}
	public static final String[] ruleNames = makeRuleNames();

	private static String[] makeLiteralNames() {
		return new String[] {
			null, null, null, null, null, null, "'False'", "'await'", "'else'", "'import'", 
			"'pass'", "'None'", "'break'", "'except'", "'in'", "'raise'", "'True'", 
			"'class'", "'finally'", "'is'", "'return'", "'and'", "'continue'", "'for'", 
			"'lambda'", "'try'", "'as'", "'def'", "'from'", "'nonlocal'", "'while'", 
			"'assert'", "'del'", "'global'", "'not'", "'with'", "'async'", "'elif'", 
			"'if'", "'or'", "'yield'", "'within'", "'to'", "'('", "'['", null, "')'", 
			"']'", null, "'.'", "':'", "','", "';'", "'+'", "'-'", "'*'", "'/'", 
			"'|'", "'&'", "'<'", "'>'", "'='", "'%'", "'=='", "'!='", "'<='", "'>='", 
			"'~'", "'^'", "'<<'", "'>>'", "'**'", "'+='", "'-='", "'*='", "'/='", 
			"'%='", "'&='", "'|='", "'^='", "'<<='", "'>>='", "'**='", "'//'", "'//='", 
			"'@'", "'@='", "'->'", "'...'", "':='", "'!'", "'+/-'", "'\\u00B1'"
		};
	}
	private static final String[] _LITERAL_NAMES = makeLiteralNames();
	private static String[] makeSymbolicNames() {
		return new String[] {
			null, "INDENT", "DEDENT", "FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END", 
			"FALSE", "AWAIT", "ELSE", "IMPORT", "PASS", "NONE", "BREAK", "EXCEPT", 
			"IN", "RAISE", "TRUE", "CLASS", "FINALLY", "IS", "RETURN", "AND", "CONTINUE", 
			"FOR", "LAMBDA", "TRY", "AS", "DEF", "FROM", "NONLOCAL", "WHILE", "ASSERT", 
			"DEL", "GLOBAL", "NOT", "WITH", "ASYNC", "ELIF", "IF", "OR", "YIELD", 
			"WITHIN", "TO", "LPAR", "LSQB", "LBRACE", "RPAR", "RSQB", "RBRACE", "DOT", 
			"COLON", "COMMA", "SEMI", "PLUS", "MINUS", "STAR", "SLASH", "VBAR", "AMPER", 
			"LESS", "GREATER", "EQUAL", "PERCENT", "EQEQUAL", "NOTEQUAL", "LESSEQUAL", 
			"GREATEREQUAL", "TILDE", "CIRCUMFLEX", "LEFTSHIFT", "RIGHTSHIFT", "DOUBLESTAR", 
			"PLUSEQUAL", "MINEQUAL", "STAREQUAL", "SLASHEQUAL", "PERCENTEQUAL", "AMPEREQUAL", 
			"VBAREQUAL", "CIRCUMFLEXEQUAL", "LEFTSHIFTEQUAL", "RIGHTSHIFTEQUAL", 
			"DOUBLESTAREQUAL", "DOUBLESLASH", "DOUBLESLASHEQUAL", "AT", "ATEQUAL", 
			"RARROW", "ELLIPSIS", "COLONEQUAL", "EXCLAMATION", "PLUS_OR_MINUS", "PLUS_OR_MINU2", 
			"NAME", "NUMBER", "STRING", "TYPE_COMMENT", "NEWLINE", "COMMENT", "WS", 
			"EXPLICIT_LINE_JOINING", "ERROR_TOKEN"
		};
	}
	private static final String[] _SYMBOLIC_NAMES = makeSymbolicNames();
	public static final Vocabulary VOCABULARY = new VocabularyImpl(_LITERAL_NAMES, _SYMBOLIC_NAMES);

	/**
	 * @deprecated Use {@link #VOCABULARY} instead.
	 */
	@Deprecated
	public static final String[] tokenNames;
	static {
		tokenNames = new String[_SYMBOLIC_NAMES.length];
		for (int i = 0; i < tokenNames.length; i++) {
			tokenNames[i] = VOCABULARY.getLiteralName(i);
			if (tokenNames[i] == null) {
				tokenNames[i] = VOCABULARY.getSymbolicName(i);
			}

			if (tokenNames[i] == null) {
				tokenNames[i] = "<INVALID>";
			}
		}
	}

	@Override
	@Deprecated
	public String[] getTokenNames() {
		return tokenNames;
	}

	@Override

	public Vocabulary getVocabulary() {
		return VOCABULARY;
	}

	@Override
	public String getGrammarFileName() { return "PythonParser.g4"; }

	@Override
	public String[] getRuleNames() { return ruleNames; }

	@Override
	public String getSerializedATN() { return _serializedATN; }

	@Override
	public ATN getATN() { return _ATN; }

	public PythonParser(TokenStream input) {
		super(input);
		_interp = new ParserATNSimulator(this,_ATN,_decisionToDFA,_sharedContextCache);
	}

	@SuppressWarnings("CheckReturnValue")
	public static class File_inputContext extends ParserRuleContext {
		public TerminalNode EOF() { return getToken(PythonParser.EOF, 0); }
		public StatementsContext statements() {
			return getRuleContext(StatementsContext.class,0);
		}
		public File_inputContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_file_input; }
	}

	public final File_inputContext file_input() throws RecognitionException {
		File_inputContext _localctx = new File_inputContext(_ctx, getState());
		enterRule(_localctx, 0, RULE_file_input);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(405);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,0,_ctx) ) {
			case 1:
				{
				setState(404);
				statements();
				}
				break;
			}
			setState(407);
			match(EOF);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class InteractiveContext extends ParserRuleContext {
		public Statement_newlineContext statement_newline() {
			return getRuleContext(Statement_newlineContext.class,0);
		}
		public InteractiveContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_interactive; }
	}

	public final InteractiveContext interactive() throws RecognitionException {
		InteractiveContext _localctx = new InteractiveContext(_ctx, getState());
		enterRule(_localctx, 2, RULE_interactive);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(409);
			statement_newline();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class EvalContext extends ParserRuleContext {
		public ExpressionsContext expressions() {
			return getRuleContext(ExpressionsContext.class,0);
		}
		public TerminalNode EOF() { return getToken(PythonParser.EOF, 0); }
		public List<TerminalNode> NEWLINE() { return getTokens(PythonParser.NEWLINE); }
		public TerminalNode NEWLINE(int i) {
			return getToken(PythonParser.NEWLINE, i);
		}
		public EvalContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_eval; }
	}

	public final EvalContext eval() throws RecognitionException {
		EvalContext _localctx = new EvalContext(_ctx, getState());
		enterRule(_localctx, 4, RULE_eval);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(411);
			expressions();
			setState(415);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==NEWLINE) {
				{
				{
				setState(412);
				match(NEWLINE);
				}
				}
				setState(417);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			setState(418);
			match(EOF);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Func_typeContext extends ParserRuleContext {
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public TerminalNode RARROW() { return getToken(PythonParser.RARROW, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public TerminalNode EOF() { return getToken(PythonParser.EOF, 0); }
		public Type_expressionsContext type_expressions() {
			return getRuleContext(Type_expressionsContext.class,0);
		}
		public List<TerminalNode> NEWLINE() { return getTokens(PythonParser.NEWLINE); }
		public TerminalNode NEWLINE(int i) {
			return getToken(PythonParser.NEWLINE, i);
		}
		public Func_typeContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_func_type; }
	}

	public final Func_typeContext func_type() throws RecognitionException {
		Func_typeContext _localctx = new Func_typeContext(_ctx, getState());
		enterRule(_localctx, 6, RULE_func_type);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(420);
			match(LPAR);
			setState(422);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 63111984631056584L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859217L) != 0)) {
				{
				setState(421);
				type_expressions();
				}
			}

			setState(424);
			match(RPAR);
			setState(425);
			match(RARROW);
			setState(426);
			expression();
			setState(430);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==NEWLINE) {
				{
				{
				setState(427);
				match(NEWLINE);
				}
				}
				setState(432);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			setState(433);
			match(EOF);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Fstring_inputContext extends ParserRuleContext {
		public Star_expressionsContext star_expressions() {
			return getRuleContext(Star_expressionsContext.class,0);
		}
		public Fstring_inputContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_fstring_input; }
	}

	public final Fstring_inputContext fstring_input() throws RecognitionException {
		Fstring_inputContext _localctx = new Fstring_inputContext(_ctx, getState());
		enterRule(_localctx, 8, RULE_fstring_input);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(435);
			star_expressions();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class StatementsContext extends ParserRuleContext {
		public List<StatementContext> statement() {
			return getRuleContexts(StatementContext.class);
		}
		public StatementContext statement(int i) {
			return getRuleContext(StatementContext.class,i);
		}
		public StatementsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_statements; }
	}

	public final StatementsContext statements() throws RecognitionException {
		StatementsContext _localctx = new StatementsContext(_ctx, getState());
		enterRule(_localctx, 10, RULE_statements);
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(438); 
			_errHandler.sync(this);
			_alt = 1;
			do {
				switch (_alt) {
				case 1:
					{
					{
					setState(437);
					statement();
					}
					}
					break;
				default:
					throw new NoViableAltException(this);
				}
				setState(440); 
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,4,_ctx);
			} while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER );
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class StatementContext extends ParserRuleContext {
		public Compound_stmtContext compound_stmt() {
			return getRuleContext(Compound_stmtContext.class,0);
		}
		public Simple_stmtsContext simple_stmts() {
			return getRuleContext(Simple_stmtsContext.class,0);
		}
		public StatementContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_statement; }
	}

	public final StatementContext statement() throws RecognitionException {
		StatementContext _localctx = new StatementContext(_ctx, getState());
		enterRule(_localctx, 12, RULE_statement);
		try {
			setState(444);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,5,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(442);
				compound_stmt();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(443);
				simple_stmts();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Statement_newlineContext extends ParserRuleContext {
		public Compound_stmtContext compound_stmt() {
			return getRuleContext(Compound_stmtContext.class,0);
		}
		public TerminalNode NEWLINE() { return getToken(PythonParser.NEWLINE, 0); }
		public Simple_stmtsContext simple_stmts() {
			return getRuleContext(Simple_stmtsContext.class,0);
		}
		public TerminalNode EOF() { return getToken(PythonParser.EOF, 0); }
		public Statement_newlineContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_statement_newline; }
	}

	public final Statement_newlineContext statement_newline() throws RecognitionException {
		Statement_newlineContext _localctx = new Statement_newlineContext(_ctx, getState());
		enterRule(_localctx, 14, RULE_statement_newline);
		try {
			setState(452);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,6,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(446);
				compound_stmt();
				setState(447);
				match(NEWLINE);
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(449);
				simple_stmts();
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(450);
				match(NEWLINE);
				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(451);
				match(EOF);
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Simple_stmtsContext extends ParserRuleContext {
		public List<Simple_stmtContext> simple_stmt() {
			return getRuleContexts(Simple_stmtContext.class);
		}
		public Simple_stmtContext simple_stmt(int i) {
			return getRuleContext(Simple_stmtContext.class,i);
		}
		public TerminalNode NEWLINE() { return getToken(PythonParser.NEWLINE, 0); }
		public List<TerminalNode> SEMI() { return getTokens(PythonParser.SEMI); }
		public TerminalNode SEMI(int i) {
			return getToken(PythonParser.SEMI, i);
		}
		public Simple_stmtsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_simple_stmts; }
	}

	public final Simple_stmtsContext simple_stmts() throws RecognitionException {
		Simple_stmtsContext _localctx = new Simple_stmtsContext(_ctx, getState());
		enterRule(_localctx, 16, RULE_simple_stmts);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(454);
			simple_stmt();
			setState(459);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,7,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(455);
					match(SEMI);
					setState(456);
					simple_stmt();
					}
					} 
				}
				setState(461);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,7,_ctx);
			}
			setState(463);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==SEMI) {
				{
				setState(462);
				match(SEMI);
				}
			}

			setState(465);
			match(NEWLINE);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Simple_stmtContext extends ParserRuleContext {
		public AssignmentContext assignment() {
			return getRuleContext(AssignmentContext.class,0);
		}
		public Type_aliasContext type_alias() {
			return getRuleContext(Type_aliasContext.class,0);
		}
		public Star_expressionsContext star_expressions() {
			return getRuleContext(Star_expressionsContext.class,0);
		}
		public Return_stmtContext return_stmt() {
			return getRuleContext(Return_stmtContext.class,0);
		}
		public Import_stmtContext import_stmt() {
			return getRuleContext(Import_stmtContext.class,0);
		}
		public Raise_stmtContext raise_stmt() {
			return getRuleContext(Raise_stmtContext.class,0);
		}
		public TerminalNode PASS() { return getToken(PythonParser.PASS, 0); }
		public Del_stmtContext del_stmt() {
			return getRuleContext(Del_stmtContext.class,0);
		}
		public Yield_stmtContext yield_stmt() {
			return getRuleContext(Yield_stmtContext.class,0);
		}
		public Assert_stmtContext assert_stmt() {
			return getRuleContext(Assert_stmtContext.class,0);
		}
		public TerminalNode BREAK() { return getToken(PythonParser.BREAK, 0); }
		public TerminalNode CONTINUE() { return getToken(PythonParser.CONTINUE, 0); }
		public Global_stmtContext global_stmt() {
			return getRuleContext(Global_stmtContext.class,0);
		}
		public Nonlocal_stmtContext nonlocal_stmt() {
			return getRuleContext(Nonlocal_stmtContext.class,0);
		}
		public Connect_stmtContext connect_stmt() {
			return getRuleContext(Connect_stmtContext.class,0);
		}
		public Simple_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_simple_stmt; }
	}

	public final Simple_stmtContext simple_stmt() throws RecognitionException {
		Simple_stmtContext _localctx = new Simple_stmtContext(_ctx, getState());
		enterRule(_localctx, 18, RULE_simple_stmt);
		try {
			setState(482);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,9,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(467);
				assignment();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(468);
				type_alias();
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(469);
				star_expressions();
				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(470);
				return_stmt();
				}
				break;
			case 5:
				enterOuterAlt(_localctx, 5);
				{
				setState(471);
				import_stmt();
				}
				break;
			case 6:
				enterOuterAlt(_localctx, 6);
				{
				setState(472);
				raise_stmt();
				}
				break;
			case 7:
				enterOuterAlt(_localctx, 7);
				{
				setState(473);
				match(PASS);
				}
				break;
			case 8:
				enterOuterAlt(_localctx, 8);
				{
				setState(474);
				del_stmt();
				}
				break;
			case 9:
				enterOuterAlt(_localctx, 9);
				{
				setState(475);
				yield_stmt();
				}
				break;
			case 10:
				enterOuterAlt(_localctx, 10);
				{
				setState(476);
				assert_stmt();
				}
				break;
			case 11:
				enterOuterAlt(_localctx, 11);
				{
				setState(477);
				match(BREAK);
				}
				break;
			case 12:
				enterOuterAlt(_localctx, 12);
				{
				setState(478);
				match(CONTINUE);
				}
				break;
			case 13:
				enterOuterAlt(_localctx, 13);
				{
				setState(479);
				global_stmt();
				}
				break;
			case 14:
				enterOuterAlt(_localctx, 14);
				{
				setState(480);
				nonlocal_stmt();
				}
				break;
			case 15:
				enterOuterAlt(_localctx, 15);
				{
				setState(481);
				connect_stmt();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Compound_stmtContext extends ParserRuleContext {
		public Function_defContext function_def() {
			return getRuleContext(Function_defContext.class,0);
		}
		public If_stmtContext if_stmt() {
			return getRuleContext(If_stmtContext.class,0);
		}
		public Class_defContext class_def() {
			return getRuleContext(Class_defContext.class,0);
		}
		public With_stmtContext with_stmt() {
			return getRuleContext(With_stmtContext.class,0);
		}
		public For_stmtContext for_stmt() {
			return getRuleContext(For_stmtContext.class,0);
		}
		public Try_stmtContext try_stmt() {
			return getRuleContext(Try_stmtContext.class,0);
		}
		public While_stmtContext while_stmt() {
			return getRuleContext(While_stmtContext.class,0);
		}
		public Match_stmtContext match_stmt() {
			return getRuleContext(Match_stmtContext.class,0);
		}
		public Compound_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_compound_stmt; }
	}

	public final Compound_stmtContext compound_stmt() throws RecognitionException {
		Compound_stmtContext _localctx = new Compound_stmtContext(_ctx, getState());
		enterRule(_localctx, 20, RULE_compound_stmt);
		try {
			setState(492);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,10,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(484);
				function_def();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(485);
				if_stmt();
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(486);
				class_def();
				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(487);
				with_stmt();
				}
				break;
			case 5:
				enterOuterAlt(_localctx, 5);
				{
				setState(488);
				for_stmt();
				}
				break;
			case 6:
				enterOuterAlt(_localctx, 6);
				{
				setState(489);
				try_stmt();
				}
				break;
			case 7:
				enterOuterAlt(_localctx, 7);
				{
				setState(490);
				while_stmt();
				}
				break;
			case 8:
				enterOuterAlt(_localctx, 8);
				{
				setState(491);
				match_stmt();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class AssignmentContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public List<TerminalNode> EQUAL() { return getTokens(PythonParser.EQUAL); }
		public TerminalNode EQUAL(int i) {
			return getToken(PythonParser.EQUAL, i);
		}
		public Annotated_rhsContext annotated_rhs() {
			return getRuleContext(Annotated_rhsContext.class,0);
		}
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public Single_targetContext single_target() {
			return getRuleContext(Single_targetContext.class,0);
		}
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public Single_subscript_attribute_targetContext single_subscript_attribute_target() {
			return getRuleContext(Single_subscript_attribute_targetContext.class,0);
		}
		public Yield_exprContext yield_expr() {
			return getRuleContext(Yield_exprContext.class,0);
		}
		public Star_expressionsContext star_expressions() {
			return getRuleContext(Star_expressionsContext.class,0);
		}
		public List<Star_targetsContext> star_targets() {
			return getRuleContexts(Star_targetsContext.class);
		}
		public Star_targetsContext star_targets(int i) {
			return getRuleContext(Star_targetsContext.class,i);
		}
		public TerminalNode TYPE_COMMENT() { return getToken(PythonParser.TYPE_COMMENT, 0); }
		public AugassignContext augassign() {
			return getRuleContext(AugassignContext.class,0);
		}
		public AssignmentContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_assignment; }
	}

	public final AssignmentContext assignment() throws RecognitionException {
		AssignmentContext _localctx = new AssignmentContext(_ctx, getState());
		enterRule(_localctx, 22, RULE_assignment);
		int _la;
		try {
			int _alt;
			setState(534);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,18,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(494);
				match(NAME);
				setState(495);
				match(COLON);
				setState(496);
				expression();
				setState(499);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==EQUAL) {
					{
					setState(497);
					match(EQUAL);
					setState(498);
					annotated_rhs();
					}
				}

				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(506);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,12,_ctx) ) {
				case 1:
					{
					setState(501);
					match(LPAR);
					setState(502);
					single_target();
					setState(503);
					match(RPAR);
					}
					break;
				case 2:
					{
					setState(505);
					single_subscript_attribute_target();
					}
					break;
				}
				setState(508);
				match(COLON);
				setState(509);
				expression();
				setState(512);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==EQUAL) {
					{
					setState(510);
					match(EQUAL);
					setState(511);
					annotated_rhs();
					}
				}

				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(517); 
				_errHandler.sync(this);
				_alt = 1;
				do {
					switch (_alt) {
					case 1:
						{
						{
						setState(514);
						star_targets();
						setState(515);
						match(EQUAL);
						}
						}
						break;
					default:
						throw new NoViableAltException(this);
					}
					setState(519); 
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,14,_ctx);
				} while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER );
				setState(523);
				_errHandler.sync(this);
				switch (_input.LA(1)) {
				case YIELD:
					{
					setState(521);
					yield_expr();
					}
					break;
				case FSTRING_START:
				case FALSE:
				case AWAIT:
				case NONE:
				case TRUE:
				case LAMBDA:
				case NOT:
				case LPAR:
				case LSQB:
				case LBRACE:
				case PLUS:
				case MINUS:
				case STAR:
				case TILDE:
				case ELLIPSIS:
				case NAME:
				case NUMBER:
				case STRING:
					{
					setState(522);
					star_expressions();
					}
					break;
				default:
					throw new NoViableAltException(this);
				}
				setState(526);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==TYPE_COMMENT) {
					{
					setState(525);
					match(TYPE_COMMENT);
					}
				}

				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(528);
				single_target();
				setState(529);
				augassign();
				setState(532);
				_errHandler.sync(this);
				switch (_input.LA(1)) {
				case YIELD:
					{
					setState(530);
					yield_expr();
					}
					break;
				case FSTRING_START:
				case FALSE:
				case AWAIT:
				case NONE:
				case TRUE:
				case LAMBDA:
				case NOT:
				case LPAR:
				case LSQB:
				case LBRACE:
				case PLUS:
				case MINUS:
				case STAR:
				case TILDE:
				case ELLIPSIS:
				case NAME:
				case NUMBER:
				case STRING:
					{
					setState(531);
					star_expressions();
					}
					break;
				default:
					throw new NoViableAltException(this);
				}
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Annotated_rhsContext extends ParserRuleContext {
		public Yield_exprContext yield_expr() {
			return getRuleContext(Yield_exprContext.class,0);
		}
		public Star_expressionsContext star_expressions() {
			return getRuleContext(Star_expressionsContext.class,0);
		}
		public Annotated_rhsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_annotated_rhs; }
	}

	public final Annotated_rhsContext annotated_rhs() throws RecognitionException {
		Annotated_rhsContext _localctx = new Annotated_rhsContext(_ctx, getState());
		enterRule(_localctx, 24, RULE_annotated_rhs);
		try {
			setState(538);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case YIELD:
				enterOuterAlt(_localctx, 1);
				{
				setState(536);
				yield_expr();
				}
				break;
			case FSTRING_START:
			case FALSE:
			case AWAIT:
			case NONE:
			case TRUE:
			case LAMBDA:
			case NOT:
			case LPAR:
			case LSQB:
			case LBRACE:
			case PLUS:
			case MINUS:
			case STAR:
			case TILDE:
			case ELLIPSIS:
			case NAME:
			case NUMBER:
			case STRING:
				enterOuterAlt(_localctx, 2);
				{
				setState(537);
				star_expressions();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class AugassignContext extends ParserRuleContext {
		public TerminalNode PLUSEQUAL() { return getToken(PythonParser.PLUSEQUAL, 0); }
		public TerminalNode MINEQUAL() { return getToken(PythonParser.MINEQUAL, 0); }
		public TerminalNode STAREQUAL() { return getToken(PythonParser.STAREQUAL, 0); }
		public TerminalNode ATEQUAL() { return getToken(PythonParser.ATEQUAL, 0); }
		public TerminalNode SLASHEQUAL() { return getToken(PythonParser.SLASHEQUAL, 0); }
		public TerminalNode PERCENTEQUAL() { return getToken(PythonParser.PERCENTEQUAL, 0); }
		public TerminalNode AMPEREQUAL() { return getToken(PythonParser.AMPEREQUAL, 0); }
		public TerminalNode VBAREQUAL() { return getToken(PythonParser.VBAREQUAL, 0); }
		public TerminalNode CIRCUMFLEXEQUAL() { return getToken(PythonParser.CIRCUMFLEXEQUAL, 0); }
		public TerminalNode LEFTSHIFTEQUAL() { return getToken(PythonParser.LEFTSHIFTEQUAL, 0); }
		public TerminalNode RIGHTSHIFTEQUAL() { return getToken(PythonParser.RIGHTSHIFTEQUAL, 0); }
		public TerminalNode DOUBLESTAREQUAL() { return getToken(PythonParser.DOUBLESTAREQUAL, 0); }
		public TerminalNode DOUBLESLASHEQUAL() { return getToken(PythonParser.DOUBLESLASHEQUAL, 0); }
		public AugassignContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_augassign; }
	}

	public final AugassignContext augassign() throws RecognitionException {
		AugassignContext _localctx = new AugassignContext(_ctx, getState());
		enterRule(_localctx, 26, RULE_augassign);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(540);
			_la = _input.LA(1);
			if ( !(((((_la - 72)) & ~0x3f) == 0 && ((1L << (_la - 72)) & 22527L) != 0)) ) {
			_errHandler.recoverInline(this);
			}
			else {
				if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
				_errHandler.reportMatch(this);
				consume();
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Return_stmtContext extends ParserRuleContext {
		public TerminalNode RETURN() { return getToken(PythonParser.RETURN, 0); }
		public Star_expressionsContext star_expressions() {
			return getRuleContext(Star_expressionsContext.class,0);
		}
		public Return_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_return_stmt; }
	}

	public final Return_stmtContext return_stmt() throws RecognitionException {
		Return_stmtContext _localctx = new Return_stmtContext(_ctx, getState());
		enterRule(_localctx, 28, RULE_return_stmt);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(542);
			match(RETURN);
			setState(544);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 63111984631056584L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859201L) != 0)) {
				{
				setState(543);
				star_expressions();
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Raise_stmtContext extends ParserRuleContext {
		public TerminalNode RAISE() { return getToken(PythonParser.RAISE, 0); }
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public TerminalNode FROM() { return getToken(PythonParser.FROM, 0); }
		public Raise_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_raise_stmt; }
	}

	public final Raise_stmtContext raise_stmt() throws RecognitionException {
		Raise_stmtContext _localctx = new Raise_stmtContext(_ctx, getState());
		enterRule(_localctx, 30, RULE_raise_stmt);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(546);
			match(RAISE);
			setState(552);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 27083187612092616L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859201L) != 0)) {
				{
				setState(547);
				expression();
				setState(550);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==FROM) {
					{
					setState(548);
					match(FROM);
					setState(549);
					expression();
					}
				}

				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Global_stmtContext extends ParserRuleContext {
		public TerminalNode GLOBAL() { return getToken(PythonParser.GLOBAL, 0); }
		public List<TerminalNode> NAME() { return getTokens(PythonParser.NAME); }
		public TerminalNode NAME(int i) {
			return getToken(PythonParser.NAME, i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Global_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_global_stmt; }
	}

	public final Global_stmtContext global_stmt() throws RecognitionException {
		Global_stmtContext _localctx = new Global_stmtContext(_ctx, getState());
		enterRule(_localctx, 32, RULE_global_stmt);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(554);
			match(GLOBAL);
			setState(555);
			match(NAME);
			setState(560);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==COMMA) {
				{
				{
				setState(556);
				match(COMMA);
				setState(557);
				match(NAME);
				}
				}
				setState(562);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Nonlocal_stmtContext extends ParserRuleContext {
		public TerminalNode NONLOCAL() { return getToken(PythonParser.NONLOCAL, 0); }
		public List<TerminalNode> NAME() { return getTokens(PythonParser.NAME); }
		public TerminalNode NAME(int i) {
			return getToken(PythonParser.NAME, i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Nonlocal_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_nonlocal_stmt; }
	}

	public final Nonlocal_stmtContext nonlocal_stmt() throws RecognitionException {
		Nonlocal_stmtContext _localctx = new Nonlocal_stmtContext(_ctx, getState());
		enterRule(_localctx, 34, RULE_nonlocal_stmt);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(563);
			match(NONLOCAL);
			setState(564);
			match(NAME);
			setState(569);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==COMMA) {
				{
				{
				setState(565);
				match(COMMA);
				setState(566);
				match(NAME);
				}
				}
				setState(571);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Del_stmtContext extends ParserRuleContext {
		public TerminalNode DEL() { return getToken(PythonParser.DEL, 0); }
		public Del_targetsContext del_targets() {
			return getRuleContext(Del_targetsContext.class,0);
		}
		public Del_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_del_stmt; }
	}

	public final Del_stmtContext del_stmt() throws RecognitionException {
		Del_stmtContext _localctx = new Del_stmtContext(_ctx, getState());
		enterRule(_localctx, 36, RULE_del_stmt);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(572);
			match(DEL);
			setState(573);
			del_targets();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Yield_stmtContext extends ParserRuleContext {
		public Yield_exprContext yield_expr() {
			return getRuleContext(Yield_exprContext.class,0);
		}
		public Yield_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_yield_stmt; }
	}

	public final Yield_stmtContext yield_stmt() throws RecognitionException {
		Yield_stmtContext _localctx = new Yield_stmtContext(_ctx, getState());
		enterRule(_localctx, 38, RULE_yield_stmt);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(575);
			yield_expr();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Assert_stmtContext extends ParserRuleContext {
		public TerminalNode ASSERT() { return getToken(PythonParser.ASSERT, 0); }
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public Assert_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_assert_stmt; }
	}

	public final Assert_stmtContext assert_stmt() throws RecognitionException {
		Assert_stmtContext _localctx = new Assert_stmtContext(_ctx, getState());
		enterRule(_localctx, 40, RULE_assert_stmt);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(577);
			match(ASSERT);
			setState(578);
			expression();
			setState(581);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(579);
				match(COMMA);
				setState(580);
				expression();
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Import_stmtContext extends ParserRuleContext {
		public Import_nameContext import_name() {
			return getRuleContext(Import_nameContext.class,0);
		}
		public Import_fromContext import_from() {
			return getRuleContext(Import_fromContext.class,0);
		}
		public Import_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_import_stmt; }
	}

	public final Import_stmtContext import_stmt() throws RecognitionException {
		Import_stmtContext _localctx = new Import_stmtContext(_ctx, getState());
		enterRule(_localctx, 42, RULE_import_stmt);
		try {
			setState(585);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case IMPORT:
				enterOuterAlt(_localctx, 1);
				{
				setState(583);
				import_name();
				}
				break;
			case FROM:
				enterOuterAlt(_localctx, 2);
				{
				setState(584);
				import_from();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Connect_stmtContext extends ParserRuleContext {
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public List<TerminalNode> TILDE() { return getTokens(PythonParser.TILDE); }
		public TerminalNode TILDE(int i) {
			return getToken(PythonParser.TILDE, i);
		}
		public Connect_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_connect_stmt; }
	}

	public final Connect_stmtContext connect_stmt() throws RecognitionException {
		Connect_stmtContext _localctx = new Connect_stmtContext(_ctx, getState());
		enterRule(_localctx, 44, RULE_connect_stmt);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(587);
			expression();
			setState(590); 
			_errHandler.sync(this);
			_la = _input.LA(1);
			do {
				{
				{
				setState(588);
				match(TILDE);
				setState(589);
				expression();
				}
				}
				setState(592); 
				_errHandler.sync(this);
				_la = _input.LA(1);
			} while ( _la==TILDE );
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Import_nameContext extends ParserRuleContext {
		public TerminalNode IMPORT() { return getToken(PythonParser.IMPORT, 0); }
		public Dotted_as_namesContext dotted_as_names() {
			return getRuleContext(Dotted_as_namesContext.class,0);
		}
		public Import_nameContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_import_name; }
	}

	public final Import_nameContext import_name() throws RecognitionException {
		Import_nameContext _localctx = new Import_nameContext(_ctx, getState());
		enterRule(_localctx, 46, RULE_import_name);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(594);
			match(IMPORT);
			setState(595);
			dotted_as_names();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Import_fromContext extends ParserRuleContext {
		public TerminalNode FROM() { return getToken(PythonParser.FROM, 0); }
		public Dotted_nameContext dotted_name() {
			return getRuleContext(Dotted_nameContext.class,0);
		}
		public TerminalNode IMPORT() { return getToken(PythonParser.IMPORT, 0); }
		public Import_from_targetsContext import_from_targets() {
			return getRuleContext(Import_from_targetsContext.class,0);
		}
		public List<TerminalNode> DOT() { return getTokens(PythonParser.DOT); }
		public TerminalNode DOT(int i) {
			return getToken(PythonParser.DOT, i);
		}
		public List<TerminalNode> ELLIPSIS() { return getTokens(PythonParser.ELLIPSIS); }
		public TerminalNode ELLIPSIS(int i) {
			return getToken(PythonParser.ELLIPSIS, i);
		}
		public Import_fromContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_import_from; }
	}

	public final Import_fromContext import_from() throws RecognitionException {
		Import_fromContext _localctx = new Import_fromContext(_ctx, getState());
		enterRule(_localctx, 48, RULE_import_from);
		int _la;
		try {
			setState(616);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,30,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(597);
				match(FROM);
				setState(601);
				_errHandler.sync(this);
				_la = _input.LA(1);
				while (_la==DOT || _la==ELLIPSIS) {
					{
					{
					setState(598);
					_la = _input.LA(1);
					if ( !(_la==DOT || _la==ELLIPSIS) ) {
					_errHandler.recoverInline(this);
					}
					else {
						if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
						_errHandler.reportMatch(this);
						consume();
					}
					}
					}
					setState(603);
					_errHandler.sync(this);
					_la = _input.LA(1);
				}
				setState(604);
				dotted_name(0);
				setState(605);
				match(IMPORT);
				setState(606);
				import_from_targets();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(608);
				match(FROM);
				setState(610); 
				_errHandler.sync(this);
				_la = _input.LA(1);
				do {
					{
					{
					setState(609);
					_la = _input.LA(1);
					if ( !(_la==DOT || _la==ELLIPSIS) ) {
					_errHandler.recoverInline(this);
					}
					else {
						if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
						_errHandler.reportMatch(this);
						consume();
					}
					}
					}
					setState(612); 
					_errHandler.sync(this);
					_la = _input.LA(1);
				} while ( _la==DOT || _la==ELLIPSIS );
				setState(614);
				match(IMPORT);
				setState(615);
				import_from_targets();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Import_from_targetsContext extends ParserRuleContext {
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public Import_from_as_namesContext import_from_as_names() {
			return getRuleContext(Import_from_as_namesContext.class,0);
		}
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public TerminalNode STAR() { return getToken(PythonParser.STAR, 0); }
		public Import_from_targetsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_import_from_targets; }
	}

	public final Import_from_targetsContext import_from_targets() throws RecognitionException {
		Import_from_targetsContext _localctx = new Import_from_targetsContext(_ctx, getState());
		enterRule(_localctx, 50, RULE_import_from_targets);
		int _la;
		try {
			setState(627);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case LPAR:
				enterOuterAlt(_localctx, 1);
				{
				setState(618);
				match(LPAR);
				setState(619);
				import_from_as_names();
				setState(621);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==COMMA) {
					{
					setState(620);
					match(COMMA);
					}
				}

				setState(623);
				match(RPAR);
				}
				break;
			case NAME:
				enterOuterAlt(_localctx, 2);
				{
				setState(625);
				import_from_as_names();
				}
				break;
			case STAR:
				enterOuterAlt(_localctx, 3);
				{
				setState(626);
				match(STAR);
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Import_from_as_namesContext extends ParserRuleContext {
		public List<Import_from_as_nameContext> import_from_as_name() {
			return getRuleContexts(Import_from_as_nameContext.class);
		}
		public Import_from_as_nameContext import_from_as_name(int i) {
			return getRuleContext(Import_from_as_nameContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Import_from_as_namesContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_import_from_as_names; }
	}

	public final Import_from_as_namesContext import_from_as_names() throws RecognitionException {
		Import_from_as_namesContext _localctx = new Import_from_as_namesContext(_ctx, getState());
		enterRule(_localctx, 52, RULE_import_from_as_names);
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(629);
			import_from_as_name();
			setState(634);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,33,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(630);
					match(COMMA);
					setState(631);
					import_from_as_name();
					}
					} 
				}
				setState(636);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,33,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Import_from_as_nameContext extends ParserRuleContext {
		public List<TerminalNode> NAME() { return getTokens(PythonParser.NAME); }
		public TerminalNode NAME(int i) {
			return getToken(PythonParser.NAME, i);
		}
		public TerminalNode AS() { return getToken(PythonParser.AS, 0); }
		public Import_from_as_nameContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_import_from_as_name; }
	}

	public final Import_from_as_nameContext import_from_as_name() throws RecognitionException {
		Import_from_as_nameContext _localctx = new Import_from_as_nameContext(_ctx, getState());
		enterRule(_localctx, 54, RULE_import_from_as_name);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(637);
			match(NAME);
			setState(640);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==AS) {
				{
				setState(638);
				match(AS);
				setState(639);
				match(NAME);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Dotted_as_namesContext extends ParserRuleContext {
		public List<Dotted_as_nameContext> dotted_as_name() {
			return getRuleContexts(Dotted_as_nameContext.class);
		}
		public Dotted_as_nameContext dotted_as_name(int i) {
			return getRuleContext(Dotted_as_nameContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Dotted_as_namesContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_dotted_as_names; }
	}

	public final Dotted_as_namesContext dotted_as_names() throws RecognitionException {
		Dotted_as_namesContext _localctx = new Dotted_as_namesContext(_ctx, getState());
		enterRule(_localctx, 56, RULE_dotted_as_names);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(642);
			dotted_as_name();
			setState(647);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==COMMA) {
				{
				{
				setState(643);
				match(COMMA);
				setState(644);
				dotted_as_name();
				}
				}
				setState(649);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Dotted_as_nameContext extends ParserRuleContext {
		public Dotted_nameContext dotted_name() {
			return getRuleContext(Dotted_nameContext.class,0);
		}
		public TerminalNode AS() { return getToken(PythonParser.AS, 0); }
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public Dotted_as_nameContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_dotted_as_name; }
	}

	public final Dotted_as_nameContext dotted_as_name() throws RecognitionException {
		Dotted_as_nameContext _localctx = new Dotted_as_nameContext(_ctx, getState());
		enterRule(_localctx, 58, RULE_dotted_as_name);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(650);
			dotted_name(0);
			setState(653);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==AS) {
				{
				setState(651);
				match(AS);
				setState(652);
				match(NAME);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Dotted_nameContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public Dotted_nameContext dotted_name() {
			return getRuleContext(Dotted_nameContext.class,0);
		}
		public TerminalNode DOT() { return getToken(PythonParser.DOT, 0); }
		public Dotted_nameContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_dotted_name; }
	}

	public final Dotted_nameContext dotted_name() throws RecognitionException {
		return dotted_name(0);
	}

	private Dotted_nameContext dotted_name(int _p) throws RecognitionException {
		ParserRuleContext _parentctx = _ctx;
		int _parentState = getState();
		Dotted_nameContext _localctx = new Dotted_nameContext(_ctx, _parentState);
		Dotted_nameContext _prevctx = _localctx;
		int _startState = 60;
		enterRecursionRule(_localctx, 60, RULE_dotted_name, _p);
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			{
			setState(656);
			match(NAME);
			}
			_ctx.stop = _input.LT(-1);
			setState(663);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,37,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					if ( _parseListeners!=null ) triggerExitRuleEvent();
					_prevctx = _localctx;
					{
					{
					_localctx = new Dotted_nameContext(_parentctx, _parentState);
					pushNewRecursionContext(_localctx, _startState, RULE_dotted_name);
					setState(658);
					if (!(precpred(_ctx, 2))) throw new FailedPredicateException(this, "precpred(_ctx, 2)");
					setState(659);
					match(DOT);
					setState(660);
					match(NAME);
					}
					} 
				}
				setState(665);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,37,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			unrollRecursionContexts(_parentctx);
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class BlockContext extends ParserRuleContext {
		public TerminalNode NEWLINE() { return getToken(PythonParser.NEWLINE, 0); }
		public TerminalNode INDENT() { return getToken(PythonParser.INDENT, 0); }
		public StatementsContext statements() {
			return getRuleContext(StatementsContext.class,0);
		}
		public TerminalNode DEDENT() { return getToken(PythonParser.DEDENT, 0); }
		public Simple_stmtsContext simple_stmts() {
			return getRuleContext(Simple_stmtsContext.class,0);
		}
		public BlockContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_block; }
	}

	public final BlockContext block() throws RecognitionException {
		BlockContext _localctx = new BlockContext(_ctx, getState());
		enterRule(_localctx, 62, RULE_block);
		try {
			setState(672);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,38,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(666);
				match(NEWLINE);
				setState(667);
				match(INDENT);
				setState(668);
				statements();
				setState(669);
				match(DEDENT);
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(671);
				simple_stmts();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class DecoratorsContext extends ParserRuleContext {
		public List<TerminalNode> AT() { return getTokens(PythonParser.AT); }
		public TerminalNode AT(int i) {
			return getToken(PythonParser.AT, i);
		}
		public List<Named_expressionContext> named_expression() {
			return getRuleContexts(Named_expressionContext.class);
		}
		public Named_expressionContext named_expression(int i) {
			return getRuleContext(Named_expressionContext.class,i);
		}
		public List<TerminalNode> NEWLINE() { return getTokens(PythonParser.NEWLINE); }
		public TerminalNode NEWLINE(int i) {
			return getToken(PythonParser.NEWLINE, i);
		}
		public DecoratorsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_decorators; }
	}

	public final DecoratorsContext decorators() throws RecognitionException {
		DecoratorsContext _localctx = new DecoratorsContext(_ctx, getState());
		enterRule(_localctx, 64, RULE_decorators);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(678); 
			_errHandler.sync(this);
			_la = _input.LA(1);
			do {
				{
				{
				setState(674);
				match(AT);
				setState(675);
				named_expression();
				setState(676);
				match(NEWLINE);
				}
				}
				setState(680); 
				_errHandler.sync(this);
				_la = _input.LA(1);
			} while ( _la==AT );
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Class_defContext extends ParserRuleContext {
		public DecoratorsContext decorators() {
			return getRuleContext(DecoratorsContext.class,0);
		}
		public Class_def_rawContext class_def_raw() {
			return getRuleContext(Class_def_rawContext.class,0);
		}
		public Class_defContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_class_def; }
	}

	public final Class_defContext class_def() throws RecognitionException {
		Class_defContext _localctx = new Class_defContext(_ctx, getState());
		enterRule(_localctx, 66, RULE_class_def);
		try {
			setState(686);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case AT:
				enterOuterAlt(_localctx, 1);
				{
				setState(682);
				decorators();
				setState(683);
				class_def_raw();
				}
				break;
			case CLASS:
				enterOuterAlt(_localctx, 2);
				{
				setState(685);
				class_def_raw();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Class_def_rawContext extends ParserRuleContext {
		public TerminalNode CLASS() { return getToken(PythonParser.CLASS, 0); }
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public Type_paramsContext type_params() {
			return getRuleContext(Type_paramsContext.class,0);
		}
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public ArgumentsContext arguments() {
			return getRuleContext(ArgumentsContext.class,0);
		}
		public Class_def_rawContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_class_def_raw; }
	}

	public final Class_def_rawContext class_def_raw() throws RecognitionException {
		Class_def_rawContext _localctx = new Class_def_rawContext(_ctx, getState());
		enterRule(_localctx, 68, RULE_class_def_raw);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(688);
			match(CLASS);
			setState(689);
			match(NAME);
			setState(691);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==LSQB) {
				{
				setState(690);
				type_params();
				}
			}

			setState(698);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==LPAR) {
				{
				setState(693);
				match(LPAR);
				setState(695);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 63111984631056584L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859217L) != 0)) {
					{
					setState(694);
					arguments();
					}
				}

				setState(697);
				match(RPAR);
				}
			}

			setState(700);
			match(COLON);
			setState(701);
			block();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Function_defContext extends ParserRuleContext {
		public DecoratorsContext decorators() {
			return getRuleContext(DecoratorsContext.class,0);
		}
		public Function_def_rawContext function_def_raw() {
			return getRuleContext(Function_def_rawContext.class,0);
		}
		public Function_defContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_function_def; }
	}

	public final Function_defContext function_def() throws RecognitionException {
		Function_defContext _localctx = new Function_defContext(_ctx, getState());
		enterRule(_localctx, 70, RULE_function_def);
		try {
			setState(707);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case AT:
				enterOuterAlt(_localctx, 1);
				{
				setState(703);
				decorators();
				setState(704);
				function_def_raw();
				}
				break;
			case DEF:
			case ASYNC:
				enterOuterAlt(_localctx, 2);
				{
				setState(706);
				function_def_raw();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Function_def_rawContext extends ParserRuleContext {
		public TerminalNode DEF() { return getToken(PythonParser.DEF, 0); }
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public Type_paramsContext type_params() {
			return getRuleContext(Type_paramsContext.class,0);
		}
		public ParamsContext params() {
			return getRuleContext(ParamsContext.class,0);
		}
		public TerminalNode RARROW() { return getToken(PythonParser.RARROW, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public Func_type_commentContext func_type_comment() {
			return getRuleContext(Func_type_commentContext.class,0);
		}
		public TerminalNode ASYNC() { return getToken(PythonParser.ASYNC, 0); }
		public Function_def_rawContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_function_def_raw; }
	}

	public final Function_def_rawContext function_def_raw() throws RecognitionException {
		Function_def_rawContext _localctx = new Function_def_rawContext(_ctx, getState());
		enterRule(_localctx, 72, RULE_function_def_raw);
		int _la;
		try {
			setState(748);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case DEF:
				enterOuterAlt(_localctx, 1);
				{
				setState(709);
				match(DEF);
				setState(710);
				match(NAME);
				setState(712);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==LSQB) {
					{
					setState(711);
					type_params();
					}
				}

				setState(714);
				match(LPAR);
				setState(716);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (((((_la - 55)) & ~0x3f) == 0 && ((1L << (_la - 55)) & 274877972481L) != 0)) {
					{
					setState(715);
					params();
					}
				}

				setState(718);
				match(RPAR);
				setState(721);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==RARROW) {
					{
					setState(719);
					match(RARROW);
					setState(720);
					expression();
					}
				}

				setState(723);
				match(COLON);
				setState(725);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,48,_ctx) ) {
				case 1:
					{
					setState(724);
					func_type_comment();
					}
					break;
				}
				setState(727);
				block();
				}
				break;
			case ASYNC:
				enterOuterAlt(_localctx, 2);
				{
				setState(728);
				match(ASYNC);
				setState(729);
				match(DEF);
				setState(730);
				match(NAME);
				setState(732);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==LSQB) {
					{
					setState(731);
					type_params();
					}
				}

				setState(734);
				match(LPAR);
				setState(736);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (((((_la - 55)) & ~0x3f) == 0 && ((1L << (_la - 55)) & 274877972481L) != 0)) {
					{
					setState(735);
					params();
					}
				}

				setState(738);
				match(RPAR);
				setState(741);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==RARROW) {
					{
					setState(739);
					match(RARROW);
					setState(740);
					expression();
					}
				}

				setState(743);
				match(COLON);
				setState(745);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,52,_ctx) ) {
				case 1:
					{
					setState(744);
					func_type_comment();
					}
					break;
				}
				setState(747);
				block();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ParamsContext extends ParserRuleContext {
		public ParametersContext parameters() {
			return getRuleContext(ParametersContext.class,0);
		}
		public ParamsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_params; }
	}

	public final ParamsContext params() throws RecognitionException {
		ParamsContext _localctx = new ParamsContext(_ctx, getState());
		enterRule(_localctx, 74, RULE_params);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(750);
			parameters();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ParametersContext extends ParserRuleContext {
		public Slash_no_defaultContext slash_no_default() {
			return getRuleContext(Slash_no_defaultContext.class,0);
		}
		public List<Param_no_defaultContext> param_no_default() {
			return getRuleContexts(Param_no_defaultContext.class);
		}
		public Param_no_defaultContext param_no_default(int i) {
			return getRuleContext(Param_no_defaultContext.class,i);
		}
		public List<Param_with_defaultContext> param_with_default() {
			return getRuleContexts(Param_with_defaultContext.class);
		}
		public Param_with_defaultContext param_with_default(int i) {
			return getRuleContext(Param_with_defaultContext.class,i);
		}
		public Star_etcContext star_etc() {
			return getRuleContext(Star_etcContext.class,0);
		}
		public Slash_with_defaultContext slash_with_default() {
			return getRuleContext(Slash_with_defaultContext.class,0);
		}
		public ParametersContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_parameters; }
	}

	public final ParametersContext parameters() throws RecognitionException {
		ParametersContext _localctx = new ParametersContext(_ctx, getState());
		enterRule(_localctx, 76, RULE_parameters);
		int _la;
		try {
			int _alt;
			setState(801);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,64,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(752);
				slash_no_default();
				setState(756);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,54,_ctx);
				while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
					if ( _alt==1 ) {
						{
						{
						setState(753);
						param_no_default();
						}
						} 
					}
					setState(758);
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,54,_ctx);
				}
				setState(762);
				_errHandler.sync(this);
				_la = _input.LA(1);
				while (_la==NAME) {
					{
					{
					setState(759);
					param_with_default();
					}
					}
					setState(764);
					_errHandler.sync(this);
					_la = _input.LA(1);
				}
				setState(766);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==STAR || _la==DOUBLESTAR) {
					{
					setState(765);
					star_etc();
					}
				}

				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(768);
				slash_with_default();
				setState(772);
				_errHandler.sync(this);
				_la = _input.LA(1);
				while (_la==NAME) {
					{
					{
					setState(769);
					param_with_default();
					}
					}
					setState(774);
					_errHandler.sync(this);
					_la = _input.LA(1);
				}
				setState(776);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==STAR || _la==DOUBLESTAR) {
					{
					setState(775);
					star_etc();
					}
				}

				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(779); 
				_errHandler.sync(this);
				_alt = 1;
				do {
					switch (_alt) {
					case 1:
						{
						{
						setState(778);
						param_no_default();
						}
						}
						break;
					default:
						throw new NoViableAltException(this);
					}
					setState(781); 
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,59,_ctx);
				} while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER );
				setState(786);
				_errHandler.sync(this);
				_la = _input.LA(1);
				while (_la==NAME) {
					{
					{
					setState(783);
					param_with_default();
					}
					}
					setState(788);
					_errHandler.sync(this);
					_la = _input.LA(1);
				}
				setState(790);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==STAR || _la==DOUBLESTAR) {
					{
					setState(789);
					star_etc();
					}
				}

				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(793); 
				_errHandler.sync(this);
				_la = _input.LA(1);
				do {
					{
					{
					setState(792);
					param_with_default();
					}
					}
					setState(795); 
					_errHandler.sync(this);
					_la = _input.LA(1);
				} while ( _la==NAME );
				setState(798);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==STAR || _la==DOUBLESTAR) {
					{
					setState(797);
					star_etc();
					}
				}

				}
				break;
			case 5:
				enterOuterAlt(_localctx, 5);
				{
				setState(800);
				star_etc();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Slash_no_defaultContext extends ParserRuleContext {
		public TerminalNode SLASH() { return getToken(PythonParser.SLASH, 0); }
		public List<Param_no_defaultContext> param_no_default() {
			return getRuleContexts(Param_no_defaultContext.class);
		}
		public Param_no_defaultContext param_no_default(int i) {
			return getRuleContext(Param_no_defaultContext.class,i);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public Slash_no_defaultContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_slash_no_default; }
	}

	public final Slash_no_defaultContext slash_no_default() throws RecognitionException {
		Slash_no_defaultContext _localctx = new Slash_no_defaultContext(_ctx, getState());
		enterRule(_localctx, 78, RULE_slash_no_default);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(804); 
			_errHandler.sync(this);
			_la = _input.LA(1);
			do {
				{
				{
				setState(803);
				param_no_default();
				}
				}
				setState(806); 
				_errHandler.sync(this);
				_la = _input.LA(1);
			} while ( _la==NAME );
			setState(808);
			match(SLASH);
			setState(810);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(809);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Slash_with_defaultContext extends ParserRuleContext {
		public TerminalNode SLASH() { return getToken(PythonParser.SLASH, 0); }
		public List<Param_no_defaultContext> param_no_default() {
			return getRuleContexts(Param_no_defaultContext.class);
		}
		public Param_no_defaultContext param_no_default(int i) {
			return getRuleContext(Param_no_defaultContext.class,i);
		}
		public List<Param_with_defaultContext> param_with_default() {
			return getRuleContexts(Param_with_defaultContext.class);
		}
		public Param_with_defaultContext param_with_default(int i) {
			return getRuleContext(Param_with_defaultContext.class,i);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public Slash_with_defaultContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_slash_with_default; }
	}

	public final Slash_with_defaultContext slash_with_default() throws RecognitionException {
		Slash_with_defaultContext _localctx = new Slash_with_defaultContext(_ctx, getState());
		enterRule(_localctx, 80, RULE_slash_with_default);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(815);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,67,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(812);
					param_no_default();
					}
					} 
				}
				setState(817);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,67,_ctx);
			}
			setState(819); 
			_errHandler.sync(this);
			_la = _input.LA(1);
			do {
				{
				{
				setState(818);
				param_with_default();
				}
				}
				setState(821); 
				_errHandler.sync(this);
				_la = _input.LA(1);
			} while ( _la==NAME );
			setState(823);
			match(SLASH);
			setState(825);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(824);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Star_etcContext extends ParserRuleContext {
		public TerminalNode STAR() { return getToken(PythonParser.STAR, 0); }
		public Param_no_defaultContext param_no_default() {
			return getRuleContext(Param_no_defaultContext.class,0);
		}
		public List<Param_maybe_defaultContext> param_maybe_default() {
			return getRuleContexts(Param_maybe_defaultContext.class);
		}
		public Param_maybe_defaultContext param_maybe_default(int i) {
			return getRuleContext(Param_maybe_defaultContext.class,i);
		}
		public KwdsContext kwds() {
			return getRuleContext(KwdsContext.class,0);
		}
		public Param_no_default_star_annotationContext param_no_default_star_annotation() {
			return getRuleContext(Param_no_default_star_annotationContext.class,0);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public Star_etcContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_star_etc; }
	}

	public final Star_etcContext star_etc() throws RecognitionException {
		Star_etcContext _localctx = new Star_etcContext(_ctx, getState());
		enterRule(_localctx, 82, RULE_star_etc);
		int _la;
		try {
			setState(860);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,76,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(827);
				match(STAR);
				setState(828);
				param_no_default();
				setState(832);
				_errHandler.sync(this);
				_la = _input.LA(1);
				while (_la==NAME) {
					{
					{
					setState(829);
					param_maybe_default();
					}
					}
					setState(834);
					_errHandler.sync(this);
					_la = _input.LA(1);
				}
				setState(836);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==DOUBLESTAR) {
					{
					setState(835);
					kwds();
					}
				}

				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(838);
				match(STAR);
				setState(839);
				param_no_default_star_annotation();
				setState(843);
				_errHandler.sync(this);
				_la = _input.LA(1);
				while (_la==NAME) {
					{
					{
					setState(840);
					param_maybe_default();
					}
					}
					setState(845);
					_errHandler.sync(this);
					_la = _input.LA(1);
				}
				setState(847);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==DOUBLESTAR) {
					{
					setState(846);
					kwds();
					}
				}

				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(849);
				match(STAR);
				setState(850);
				match(COMMA);
				setState(852); 
				_errHandler.sync(this);
				_la = _input.LA(1);
				do {
					{
					{
					setState(851);
					param_maybe_default();
					}
					}
					setState(854); 
					_errHandler.sync(this);
					_la = _input.LA(1);
				} while ( _la==NAME );
				setState(857);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==DOUBLESTAR) {
					{
					setState(856);
					kwds();
					}
				}

				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(859);
				kwds();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class KwdsContext extends ParserRuleContext {
		public TerminalNode DOUBLESTAR() { return getToken(PythonParser.DOUBLESTAR, 0); }
		public Param_no_defaultContext param_no_default() {
			return getRuleContext(Param_no_defaultContext.class,0);
		}
		public KwdsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_kwds; }
	}

	public final KwdsContext kwds() throws RecognitionException {
		KwdsContext _localctx = new KwdsContext(_ctx, getState());
		enterRule(_localctx, 84, RULE_kwds);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(862);
			match(DOUBLESTAR);
			setState(863);
			param_no_default();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Param_no_defaultContext extends ParserRuleContext {
		public ParamContext param() {
			return getRuleContext(ParamContext.class,0);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public TerminalNode TYPE_COMMENT() { return getToken(PythonParser.TYPE_COMMENT, 0); }
		public Param_no_defaultContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_param_no_default; }
	}

	public final Param_no_defaultContext param_no_default() throws RecognitionException {
		Param_no_defaultContext _localctx = new Param_no_defaultContext(_ctx, getState());
		enterRule(_localctx, 86, RULE_param_no_default);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(865);
			param();
			setState(867);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(866);
				match(COMMA);
				}
			}

			setState(870);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==TYPE_COMMENT) {
				{
				setState(869);
				match(TYPE_COMMENT);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Param_no_default_star_annotationContext extends ParserRuleContext {
		public Param_star_annotationContext param_star_annotation() {
			return getRuleContext(Param_star_annotationContext.class,0);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public TerminalNode TYPE_COMMENT() { return getToken(PythonParser.TYPE_COMMENT, 0); }
		public Param_no_default_star_annotationContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_param_no_default_star_annotation; }
	}

	public final Param_no_default_star_annotationContext param_no_default_star_annotation() throws RecognitionException {
		Param_no_default_star_annotationContext _localctx = new Param_no_default_star_annotationContext(_ctx, getState());
		enterRule(_localctx, 88, RULE_param_no_default_star_annotation);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(872);
			param_star_annotation();
			setState(874);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(873);
				match(COMMA);
				}
			}

			setState(877);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==TYPE_COMMENT) {
				{
				setState(876);
				match(TYPE_COMMENT);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Param_with_defaultContext extends ParserRuleContext {
		public ParamContext param() {
			return getRuleContext(ParamContext.class,0);
		}
		public Default_assignmentContext default_assignment() {
			return getRuleContext(Default_assignmentContext.class,0);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public TerminalNode TYPE_COMMENT() { return getToken(PythonParser.TYPE_COMMENT, 0); }
		public Param_with_defaultContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_param_with_default; }
	}

	public final Param_with_defaultContext param_with_default() throws RecognitionException {
		Param_with_defaultContext _localctx = new Param_with_defaultContext(_ctx, getState());
		enterRule(_localctx, 90, RULE_param_with_default);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(879);
			param();
			setState(880);
			default_assignment();
			setState(882);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(881);
				match(COMMA);
				}
			}

			setState(885);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==TYPE_COMMENT) {
				{
				setState(884);
				match(TYPE_COMMENT);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Param_maybe_defaultContext extends ParserRuleContext {
		public ParamContext param() {
			return getRuleContext(ParamContext.class,0);
		}
		public Default_assignmentContext default_assignment() {
			return getRuleContext(Default_assignmentContext.class,0);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public TerminalNode TYPE_COMMENT() { return getToken(PythonParser.TYPE_COMMENT, 0); }
		public Param_maybe_defaultContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_param_maybe_default; }
	}

	public final Param_maybe_defaultContext param_maybe_default() throws RecognitionException {
		Param_maybe_defaultContext _localctx = new Param_maybe_defaultContext(_ctx, getState());
		enterRule(_localctx, 92, RULE_param_maybe_default);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(887);
			param();
			setState(889);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==EQUAL) {
				{
				setState(888);
				default_assignment();
				}
			}

			setState(892);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(891);
				match(COMMA);
				}
			}

			setState(895);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==TYPE_COMMENT) {
				{
				setState(894);
				match(TYPE_COMMENT);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ParamContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public AnnotationContext annotation() {
			return getRuleContext(AnnotationContext.class,0);
		}
		public ParamContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_param; }
	}

	public final ParamContext param() throws RecognitionException {
		ParamContext _localctx = new ParamContext(_ctx, getState());
		enterRule(_localctx, 94, RULE_param);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(897);
			match(NAME);
			setState(899);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COLON) {
				{
				setState(898);
				annotation();
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Param_star_annotationContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public Star_annotationContext star_annotation() {
			return getRuleContext(Star_annotationContext.class,0);
		}
		public Param_star_annotationContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_param_star_annotation; }
	}

	public final Param_star_annotationContext param_star_annotation() throws RecognitionException {
		Param_star_annotationContext _localctx = new Param_star_annotationContext(_ctx, getState());
		enterRule(_localctx, 96, RULE_param_star_annotation);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(901);
			match(NAME);
			setState(902);
			star_annotation();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class AnnotationContext extends ParserRuleContext {
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public AnnotationContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_annotation; }
	}

	public final AnnotationContext annotation() throws RecognitionException {
		AnnotationContext _localctx = new AnnotationContext(_ctx, getState());
		enterRule(_localctx, 98, RULE_annotation);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(904);
			match(COLON);
			setState(905);
			expression();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Star_annotationContext extends ParserRuleContext {
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public Star_expressionContext star_expression() {
			return getRuleContext(Star_expressionContext.class,0);
		}
		public Star_annotationContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_star_annotation; }
	}

	public final Star_annotationContext star_annotation() throws RecognitionException {
		Star_annotationContext _localctx = new Star_annotationContext(_ctx, getState());
		enterRule(_localctx, 100, RULE_star_annotation);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(907);
			match(COLON);
			setState(908);
			star_expression();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Default_assignmentContext extends ParserRuleContext {
		public TerminalNode EQUAL() { return getToken(PythonParser.EQUAL, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public Default_assignmentContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_default_assignment; }
	}

	public final Default_assignmentContext default_assignment() throws RecognitionException {
		Default_assignmentContext _localctx = new Default_assignmentContext(_ctx, getState());
		enterRule(_localctx, 102, RULE_default_assignment);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(910);
			match(EQUAL);
			setState(911);
			expression();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class If_stmtContext extends ParserRuleContext {
		public TerminalNode IF() { return getToken(PythonParser.IF, 0); }
		public Named_expressionContext named_expression() {
			return getRuleContext(Named_expressionContext.class,0);
		}
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public Elif_stmtContext elif_stmt() {
			return getRuleContext(Elif_stmtContext.class,0);
		}
		public Else_blockContext else_block() {
			return getRuleContext(Else_blockContext.class,0);
		}
		public If_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_if_stmt; }
	}

	public final If_stmtContext if_stmt() throws RecognitionException {
		If_stmtContext _localctx = new If_stmtContext(_ctx, getState());
		enterRule(_localctx, 104, RULE_if_stmt);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(913);
			match(IF);
			setState(914);
			named_expression();
			setState(915);
			match(COLON);
			setState(916);
			block();
			setState(921);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,88,_ctx) ) {
			case 1:
				{
				setState(917);
				elif_stmt();
				}
				break;
			case 2:
				{
				setState(919);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,87,_ctx) ) {
				case 1:
					{
					setState(918);
					else_block();
					}
					break;
				}
				}
				break;
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Elif_stmtContext extends ParserRuleContext {
		public TerminalNode ELIF() { return getToken(PythonParser.ELIF, 0); }
		public Named_expressionContext named_expression() {
			return getRuleContext(Named_expressionContext.class,0);
		}
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public Elif_stmtContext elif_stmt() {
			return getRuleContext(Elif_stmtContext.class,0);
		}
		public Else_blockContext else_block() {
			return getRuleContext(Else_blockContext.class,0);
		}
		public Elif_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_elif_stmt; }
	}

	public final Elif_stmtContext elif_stmt() throws RecognitionException {
		Elif_stmtContext _localctx = new Elif_stmtContext(_ctx, getState());
		enterRule(_localctx, 106, RULE_elif_stmt);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(923);
			match(ELIF);
			setState(924);
			named_expression();
			setState(925);
			match(COLON);
			setState(926);
			block();
			setState(931);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,90,_ctx) ) {
			case 1:
				{
				setState(927);
				elif_stmt();
				}
				break;
			case 2:
				{
				setState(929);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,89,_ctx) ) {
				case 1:
					{
					setState(928);
					else_block();
					}
					break;
				}
				}
				break;
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Else_blockContext extends ParserRuleContext {
		public TerminalNode ELSE() { return getToken(PythonParser.ELSE, 0); }
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public Else_blockContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_else_block; }
	}

	public final Else_blockContext else_block() throws RecognitionException {
		Else_blockContext _localctx = new Else_blockContext(_ctx, getState());
		enterRule(_localctx, 108, RULE_else_block);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(933);
			match(ELSE);
			setState(934);
			match(COLON);
			setState(935);
			block();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class While_stmtContext extends ParserRuleContext {
		public TerminalNode WHILE() { return getToken(PythonParser.WHILE, 0); }
		public Named_expressionContext named_expression() {
			return getRuleContext(Named_expressionContext.class,0);
		}
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public Else_blockContext else_block() {
			return getRuleContext(Else_blockContext.class,0);
		}
		public While_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_while_stmt; }
	}

	public final While_stmtContext while_stmt() throws RecognitionException {
		While_stmtContext _localctx = new While_stmtContext(_ctx, getState());
		enterRule(_localctx, 110, RULE_while_stmt);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(937);
			match(WHILE);
			setState(938);
			named_expression();
			setState(939);
			match(COLON);
			setState(940);
			block();
			setState(942);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,91,_ctx) ) {
			case 1:
				{
				setState(941);
				else_block();
				}
				break;
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class For_stmtContext extends ParserRuleContext {
		public TerminalNode FOR() { return getToken(PythonParser.FOR, 0); }
		public Star_targetsContext star_targets() {
			return getRuleContext(Star_targetsContext.class,0);
		}
		public TerminalNode IN() { return getToken(PythonParser.IN, 0); }
		public Star_expressionsContext star_expressions() {
			return getRuleContext(Star_expressionsContext.class,0);
		}
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public TerminalNode ASYNC() { return getToken(PythonParser.ASYNC, 0); }
		public TerminalNode TYPE_COMMENT() { return getToken(PythonParser.TYPE_COMMENT, 0); }
		public Else_blockContext else_block() {
			return getRuleContext(Else_blockContext.class,0);
		}
		public For_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_for_stmt; }
	}

	public final For_stmtContext for_stmt() throws RecognitionException {
		For_stmtContext _localctx = new For_stmtContext(_ctx, getState());
		enterRule(_localctx, 112, RULE_for_stmt);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(945);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==ASYNC) {
				{
				setState(944);
				match(ASYNC);
				}
			}

			setState(947);
			match(FOR);
			setState(948);
			star_targets();
			setState(949);
			match(IN);
			setState(950);
			star_expressions();
			setState(951);
			match(COLON);
			setState(953);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,93,_ctx) ) {
			case 1:
				{
				setState(952);
				match(TYPE_COMMENT);
				}
				break;
			}
			setState(955);
			block();
			setState(957);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,94,_ctx) ) {
			case 1:
				{
				setState(956);
				else_block();
				}
				break;
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class With_stmtContext extends ParserRuleContext {
		public TerminalNode WITH() { return getToken(PythonParser.WITH, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public List<With_itemContext> with_item() {
			return getRuleContexts(With_itemContext.class);
		}
		public With_itemContext with_item(int i) {
			return getRuleContext(With_itemContext.class,i);
		}
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public TerminalNode ASYNC() { return getToken(PythonParser.ASYNC, 0); }
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public TerminalNode TYPE_COMMENT() { return getToken(PythonParser.TYPE_COMMENT, 0); }
		public With_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_with_stmt; }
	}

	public final With_stmtContext with_stmt() throws RecognitionException {
		With_stmtContext _localctx = new With_stmtContext(_ctx, getState());
		enterRule(_localctx, 114, RULE_with_stmt);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(960);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==ASYNC) {
				{
				setState(959);
				match(ASYNC);
				}
			}

			setState(962);
			match(WITH);
			setState(990);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,100,_ctx) ) {
			case 1:
				{
				setState(963);
				match(LPAR);
				setState(964);
				with_item();
				setState(969);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,96,_ctx);
				while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
					if ( _alt==1 ) {
						{
						{
						setState(965);
						match(COMMA);
						setState(966);
						with_item();
						}
						} 
					}
					setState(971);
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,96,_ctx);
				}
				setState(973);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==COMMA) {
					{
					setState(972);
					match(COMMA);
					}
				}

				setState(975);
				match(RPAR);
				setState(976);
				match(COLON);
				}
				break;
			case 2:
				{
				setState(978);
				with_item();
				setState(983);
				_errHandler.sync(this);
				_la = _input.LA(1);
				while (_la==COMMA) {
					{
					{
					setState(979);
					match(COMMA);
					setState(980);
					with_item();
					}
					}
					setState(985);
					_errHandler.sync(this);
					_la = _input.LA(1);
				}
				setState(986);
				match(COLON);
				setState(988);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,99,_ctx) ) {
				case 1:
					{
					setState(987);
					match(TYPE_COMMENT);
					}
					break;
				}
				}
				break;
			}
			setState(992);
			block();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class With_itemContext extends ParserRuleContext {
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public TerminalNode AS() { return getToken(PythonParser.AS, 0); }
		public Star_targetContext star_target() {
			return getRuleContext(Star_targetContext.class,0);
		}
		public With_itemContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_with_item; }
	}

	public final With_itemContext with_item() throws RecognitionException {
		With_itemContext _localctx = new With_itemContext(_ctx, getState());
		enterRule(_localctx, 116, RULE_with_item);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(994);
			expression();
			setState(997);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==AS) {
				{
				setState(995);
				match(AS);
				setState(996);
				star_target();
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Try_stmtContext extends ParserRuleContext {
		public TerminalNode TRY() { return getToken(PythonParser.TRY, 0); }
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public Finally_blockContext finally_block() {
			return getRuleContext(Finally_blockContext.class,0);
		}
		public List<Except_blockContext> except_block() {
			return getRuleContexts(Except_blockContext.class);
		}
		public Except_blockContext except_block(int i) {
			return getRuleContext(Except_blockContext.class,i);
		}
		public Else_blockContext else_block() {
			return getRuleContext(Else_blockContext.class,0);
		}
		public List<Except_star_blockContext> except_star_block() {
			return getRuleContexts(Except_star_blockContext.class);
		}
		public Except_star_blockContext except_star_block(int i) {
			return getRuleContext(Except_star_blockContext.class,i);
		}
		public Try_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_try_stmt; }
	}

	public final Try_stmtContext try_stmt() throws RecognitionException {
		Try_stmtContext _localctx = new Try_stmtContext(_ctx, getState());
		enterRule(_localctx, 118, RULE_try_stmt);
		try {
			int _alt;
			setState(1032);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,108,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(999);
				match(TRY);
				setState(1000);
				match(COLON);
				setState(1001);
				block();
				setState(1002);
				finally_block();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1004);
				match(TRY);
				setState(1005);
				match(COLON);
				setState(1006);
				block();
				setState(1008); 
				_errHandler.sync(this);
				_alt = 1;
				do {
					switch (_alt) {
					case 1:
						{
						{
						setState(1007);
						except_block();
						}
						}
						break;
					default:
						throw new NoViableAltException(this);
					}
					setState(1010); 
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,102,_ctx);
				} while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER );
				setState(1013);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,103,_ctx) ) {
				case 1:
					{
					setState(1012);
					else_block();
					}
					break;
				}
				setState(1016);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,104,_ctx) ) {
				case 1:
					{
					setState(1015);
					finally_block();
					}
					break;
				}
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(1018);
				match(TRY);
				setState(1019);
				match(COLON);
				setState(1020);
				block();
				setState(1022); 
				_errHandler.sync(this);
				_alt = 1;
				do {
					switch (_alt) {
					case 1:
						{
						{
						setState(1021);
						except_star_block();
						}
						}
						break;
					default:
						throw new NoViableAltException(this);
					}
					setState(1024); 
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,105,_ctx);
				} while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER );
				setState(1027);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,106,_ctx) ) {
				case 1:
					{
					setState(1026);
					else_block();
					}
					break;
				}
				setState(1030);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,107,_ctx) ) {
				case 1:
					{
					setState(1029);
					finally_block();
					}
					break;
				}
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Except_blockContext extends ParserRuleContext {
		public TerminalNode EXCEPT() { return getToken(PythonParser.EXCEPT, 0); }
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public TerminalNode AS() { return getToken(PythonParser.AS, 0); }
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public Except_blockContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_except_block; }
	}

	public final Except_blockContext except_block() throws RecognitionException {
		Except_blockContext _localctx = new Except_blockContext(_ctx, getState());
		enterRule(_localctx, 120, RULE_except_block);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1034);
			match(EXCEPT);
			setState(1040);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 27083187612092616L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859201L) != 0)) {
				{
				setState(1035);
				expression();
				setState(1038);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==AS) {
					{
					setState(1036);
					match(AS);
					setState(1037);
					match(NAME);
					}
				}

				}
			}

			setState(1042);
			match(COLON);
			setState(1043);
			block();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Except_star_blockContext extends ParserRuleContext {
		public TerminalNode EXCEPT() { return getToken(PythonParser.EXCEPT, 0); }
		public TerminalNode STAR() { return getToken(PythonParser.STAR, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public TerminalNode AS() { return getToken(PythonParser.AS, 0); }
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public Except_star_blockContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_except_star_block; }
	}

	public final Except_star_blockContext except_star_block() throws RecognitionException {
		Except_star_blockContext _localctx = new Except_star_blockContext(_ctx, getState());
		enterRule(_localctx, 122, RULE_except_star_block);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1045);
			match(EXCEPT);
			setState(1046);
			match(STAR);
			setState(1047);
			expression();
			setState(1050);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==AS) {
				{
				setState(1048);
				match(AS);
				setState(1049);
				match(NAME);
				}
			}

			setState(1052);
			match(COLON);
			setState(1053);
			block();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Finally_blockContext extends ParserRuleContext {
		public TerminalNode FINALLY() { return getToken(PythonParser.FINALLY, 0); }
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public Finally_blockContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_finally_block; }
	}

	public final Finally_blockContext finally_block() throws RecognitionException {
		Finally_blockContext _localctx = new Finally_blockContext(_ctx, getState());
		enterRule(_localctx, 124, RULE_finally_block);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1055);
			match(FINALLY);
			setState(1056);
			match(COLON);
			setState(1057);
			block();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Match_stmtContext extends ParserRuleContext {
		public Soft_kw_matchContext soft_kw_match() {
			return getRuleContext(Soft_kw_matchContext.class,0);
		}
		public Subject_exprContext subject_expr() {
			return getRuleContext(Subject_exprContext.class,0);
		}
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public TerminalNode NEWLINE() { return getToken(PythonParser.NEWLINE, 0); }
		public TerminalNode INDENT() { return getToken(PythonParser.INDENT, 0); }
		public TerminalNode DEDENT() { return getToken(PythonParser.DEDENT, 0); }
		public List<Case_blockContext> case_block() {
			return getRuleContexts(Case_blockContext.class);
		}
		public Case_blockContext case_block(int i) {
			return getRuleContext(Case_blockContext.class,i);
		}
		public Match_stmtContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_match_stmt; }
	}

	public final Match_stmtContext match_stmt() throws RecognitionException {
		Match_stmtContext _localctx = new Match_stmtContext(_ctx, getState());
		enterRule(_localctx, 126, RULE_match_stmt);
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(1059);
			soft_kw_match();
			setState(1060);
			subject_expr();
			setState(1061);
			match(COLON);
			setState(1062);
			match(NEWLINE);
			setState(1063);
			match(INDENT);
			setState(1065); 
			_errHandler.sync(this);
			_alt = 1;
			do {
				switch (_alt) {
				case 1:
					{
					{
					setState(1064);
					case_block();
					}
					}
					break;
				default:
					throw new NoViableAltException(this);
				}
				setState(1067); 
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,112,_ctx);
			} while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER );
			setState(1069);
			match(DEDENT);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Subject_exprContext extends ParserRuleContext {
		public Star_named_expressionContext star_named_expression() {
			return getRuleContext(Star_named_expressionContext.class,0);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public Star_named_expressionsContext star_named_expressions() {
			return getRuleContext(Star_named_expressionsContext.class,0);
		}
		public Named_expressionContext named_expression() {
			return getRuleContext(Named_expressionContext.class,0);
		}
		public Subject_exprContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_subject_expr; }
	}

	public final Subject_exprContext subject_expr() throws RecognitionException {
		Subject_exprContext _localctx = new Subject_exprContext(_ctx, getState());
		enterRule(_localctx, 128, RULE_subject_expr);
		int _la;
		try {
			setState(1077);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,114,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1071);
				star_named_expression();
				setState(1072);
				match(COMMA);
				setState(1074);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 63111984631056584L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859201L) != 0)) {
					{
					setState(1073);
					star_named_expressions();
					}
				}

				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1076);
				named_expression();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Case_blockContext extends ParserRuleContext {
		public Soft_kw_caseContext soft_kw_case() {
			return getRuleContext(Soft_kw_caseContext.class,0);
		}
		public PatternsContext patterns() {
			return getRuleContext(PatternsContext.class,0);
		}
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public GuardContext guard() {
			return getRuleContext(GuardContext.class,0);
		}
		public Case_blockContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_case_block; }
	}

	public final Case_blockContext case_block() throws RecognitionException {
		Case_blockContext _localctx = new Case_blockContext(_ctx, getState());
		enterRule(_localctx, 130, RULE_case_block);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1079);
			soft_kw_case();
			setState(1080);
			patterns();
			setState(1082);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==IF) {
				{
				setState(1081);
				guard();
				}
			}

			setState(1084);
			match(COLON);
			setState(1085);
			block();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class GuardContext extends ParserRuleContext {
		public TerminalNode IF() { return getToken(PythonParser.IF, 0); }
		public Named_expressionContext named_expression() {
			return getRuleContext(Named_expressionContext.class,0);
		}
		public GuardContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_guard; }
	}

	public final GuardContext guard() throws RecognitionException {
		GuardContext _localctx = new GuardContext(_ctx, getState());
		enterRule(_localctx, 132, RULE_guard);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1087);
			match(IF);
			setState(1088);
			named_expression();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class PatternsContext extends ParserRuleContext {
		public Open_sequence_patternContext open_sequence_pattern() {
			return getRuleContext(Open_sequence_patternContext.class,0);
		}
		public PatternContext pattern() {
			return getRuleContext(PatternContext.class,0);
		}
		public PatternsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_patterns; }
	}

	public final PatternsContext patterns() throws RecognitionException {
		PatternsContext _localctx = new PatternsContext(_ctx, getState());
		enterRule(_localctx, 134, RULE_patterns);
		try {
			setState(1092);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,116,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1090);
				open_sequence_pattern();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1091);
				pattern();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class PatternContext extends ParserRuleContext {
		public As_patternContext as_pattern() {
			return getRuleContext(As_patternContext.class,0);
		}
		public Or_patternContext or_pattern() {
			return getRuleContext(Or_patternContext.class,0);
		}
		public PatternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_pattern; }
	}

	public final PatternContext pattern() throws RecognitionException {
		PatternContext _localctx = new PatternContext(_ctx, getState());
		enterRule(_localctx, 136, RULE_pattern);
		try {
			setState(1096);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,117,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1094);
				as_pattern();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1095);
				or_pattern();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class As_patternContext extends ParserRuleContext {
		public Or_patternContext or_pattern() {
			return getRuleContext(Or_patternContext.class,0);
		}
		public TerminalNode AS() { return getToken(PythonParser.AS, 0); }
		public Pattern_capture_targetContext pattern_capture_target() {
			return getRuleContext(Pattern_capture_targetContext.class,0);
		}
		public As_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_as_pattern; }
	}

	public final As_patternContext as_pattern() throws RecognitionException {
		As_patternContext _localctx = new As_patternContext(_ctx, getState());
		enterRule(_localctx, 138, RULE_as_pattern);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1098);
			or_pattern();
			setState(1099);
			match(AS);
			setState(1100);
			pattern_capture_target();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Or_patternContext extends ParserRuleContext {
		public List<Closed_patternContext> closed_pattern() {
			return getRuleContexts(Closed_patternContext.class);
		}
		public Closed_patternContext closed_pattern(int i) {
			return getRuleContext(Closed_patternContext.class,i);
		}
		public List<TerminalNode> VBAR() { return getTokens(PythonParser.VBAR); }
		public TerminalNode VBAR(int i) {
			return getToken(PythonParser.VBAR, i);
		}
		public Or_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_or_pattern; }
	}

	public final Or_patternContext or_pattern() throws RecognitionException {
		Or_patternContext _localctx = new Or_patternContext(_ctx, getState());
		enterRule(_localctx, 140, RULE_or_pattern);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1102);
			closed_pattern();
			setState(1107);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==VBAR) {
				{
				{
				setState(1103);
				match(VBAR);
				setState(1104);
				closed_pattern();
				}
				}
				setState(1109);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Closed_patternContext extends ParserRuleContext {
		public Literal_patternContext literal_pattern() {
			return getRuleContext(Literal_patternContext.class,0);
		}
		public Capture_patternContext capture_pattern() {
			return getRuleContext(Capture_patternContext.class,0);
		}
		public Wildcard_patternContext wildcard_pattern() {
			return getRuleContext(Wildcard_patternContext.class,0);
		}
		public Value_patternContext value_pattern() {
			return getRuleContext(Value_patternContext.class,0);
		}
		public Group_patternContext group_pattern() {
			return getRuleContext(Group_patternContext.class,0);
		}
		public Sequence_patternContext sequence_pattern() {
			return getRuleContext(Sequence_patternContext.class,0);
		}
		public Mapping_patternContext mapping_pattern() {
			return getRuleContext(Mapping_patternContext.class,0);
		}
		public Class_patternContext class_pattern() {
			return getRuleContext(Class_patternContext.class,0);
		}
		public Closed_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_closed_pattern; }
	}

	public final Closed_patternContext closed_pattern() throws RecognitionException {
		Closed_patternContext _localctx = new Closed_patternContext(_ctx, getState());
		enterRule(_localctx, 142, RULE_closed_pattern);
		try {
			setState(1118);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,119,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1110);
				literal_pattern();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1111);
				capture_pattern();
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(1112);
				wildcard_pattern();
				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(1113);
				value_pattern();
				}
				break;
			case 5:
				enterOuterAlt(_localctx, 5);
				{
				setState(1114);
				group_pattern();
				}
				break;
			case 6:
				enterOuterAlt(_localctx, 6);
				{
				setState(1115);
				sequence_pattern();
				}
				break;
			case 7:
				enterOuterAlt(_localctx, 7);
				{
				setState(1116);
				mapping_pattern();
				}
				break;
			case 8:
				enterOuterAlt(_localctx, 8);
				{
				setState(1117);
				class_pattern();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Literal_patternContext extends ParserRuleContext {
		public Signed_numberContext signed_number() {
			return getRuleContext(Signed_numberContext.class,0);
		}
		public Signed_dimensioned_numberContext signed_dimensioned_number() {
			return getRuleContext(Signed_dimensioned_numberContext.class,0);
		}
		public Complex_numberContext complex_number() {
			return getRuleContext(Complex_numberContext.class,0);
		}
		public StringsContext strings() {
			return getRuleContext(StringsContext.class,0);
		}
		public TerminalNode NONE() { return getToken(PythonParser.NONE, 0); }
		public TerminalNode TRUE() { return getToken(PythonParser.TRUE, 0); }
		public TerminalNode FALSE() { return getToken(PythonParser.FALSE, 0); }
		public Literal_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_literal_pattern; }
	}

	public final Literal_patternContext literal_pattern() throws RecognitionException {
		Literal_patternContext _localctx = new Literal_patternContext(_ctx, getState());
		enterRule(_localctx, 144, RULE_literal_pattern);
		try {
			setState(1127);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,120,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1120);
				signed_number();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1121);
				signed_dimensioned_number();
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(1122);
				complex_number();
				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(1123);
				strings();
				}
				break;
			case 5:
				enterOuterAlt(_localctx, 5);
				{
				setState(1124);
				match(NONE);
				}
				break;
			case 6:
				enterOuterAlt(_localctx, 6);
				{
				setState(1125);
				match(TRUE);
				}
				break;
			case 7:
				enterOuterAlt(_localctx, 7);
				{
				setState(1126);
				match(FALSE);
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Literal_exprContext extends ParserRuleContext {
		public Signed_numberContext signed_number() {
			return getRuleContext(Signed_numberContext.class,0);
		}
		public Signed_dimensioned_numberContext signed_dimensioned_number() {
			return getRuleContext(Signed_dimensioned_numberContext.class,0);
		}
		public Complex_numberContext complex_number() {
			return getRuleContext(Complex_numberContext.class,0);
		}
		public StringsContext strings() {
			return getRuleContext(StringsContext.class,0);
		}
		public TerminalNode NONE() { return getToken(PythonParser.NONE, 0); }
		public TerminalNode TRUE() { return getToken(PythonParser.TRUE, 0); }
		public TerminalNode FALSE() { return getToken(PythonParser.FALSE, 0); }
		public Literal_exprContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_literal_expr; }
	}

	public final Literal_exprContext literal_expr() throws RecognitionException {
		Literal_exprContext _localctx = new Literal_exprContext(_ctx, getState());
		enterRule(_localctx, 146, RULE_literal_expr);
		try {
			setState(1136);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,121,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1129);
				signed_number();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1130);
				signed_dimensioned_number();
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(1131);
				complex_number();
				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(1132);
				strings();
				}
				break;
			case 5:
				enterOuterAlt(_localctx, 5);
				{
				setState(1133);
				match(NONE);
				}
				break;
			case 6:
				enterOuterAlt(_localctx, 6);
				{
				setState(1134);
				match(TRUE);
				}
				break;
			case 7:
				enterOuterAlt(_localctx, 7);
				{
				setState(1135);
				match(FALSE);
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Signed_dimensioned_numberContext extends ParserRuleContext {
		public TerminalNode NUMBER() { return getToken(PythonParser.NUMBER, 0); }
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode STRING() { return getToken(PythonParser.STRING, 0); }
		public TerminalNode MINUS() { return getToken(PythonParser.MINUS, 0); }
		public Signed_dimensioned_numberContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_signed_dimensioned_number; }
	}

	public final Signed_dimensioned_numberContext signed_dimensioned_number() throws RecognitionException {
		Signed_dimensioned_numberContext _localctx = new Signed_dimensioned_numberContext(_ctx, getState());
		enterRule(_localctx, 148, RULE_signed_dimensioned_number);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1139);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==MINUS) {
				{
				setState(1138);
				match(MINUS);
				}
			}

			setState(1141);
			match(NUMBER);
			setState(1142);
			_la = _input.LA(1);
			if ( !(_la==NAME || _la==STRING) ) {
			_errHandler.recoverInline(this);
			}
			else {
				if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
				_errHandler.reportMatch(this);
				consume();
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Complex_numberContext extends ParserRuleContext {
		public Signed_real_numberContext signed_real_number() {
			return getRuleContext(Signed_real_numberContext.class,0);
		}
		public Imaginary_numberContext imaginary_number() {
			return getRuleContext(Imaginary_numberContext.class,0);
		}
		public TerminalNode PLUS() { return getToken(PythonParser.PLUS, 0); }
		public TerminalNode MINUS() { return getToken(PythonParser.MINUS, 0); }
		public Complex_numberContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_complex_number; }
	}

	public final Complex_numberContext complex_number() throws RecognitionException {
		Complex_numberContext _localctx = new Complex_numberContext(_ctx, getState());
		enterRule(_localctx, 150, RULE_complex_number);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1144);
			signed_real_number();
			setState(1145);
			_la = _input.LA(1);
			if ( !(_la==PLUS || _la==MINUS) ) {
			_errHandler.recoverInline(this);
			}
			else {
				if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
				_errHandler.reportMatch(this);
				consume();
			}
			setState(1146);
			imaginary_number();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Signed_numberContext extends ParserRuleContext {
		public TerminalNode NUMBER() { return getToken(PythonParser.NUMBER, 0); }
		public TerminalNode MINUS() { return getToken(PythonParser.MINUS, 0); }
		public Signed_numberContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_signed_number; }
	}

	public final Signed_numberContext signed_number() throws RecognitionException {
		Signed_numberContext _localctx = new Signed_numberContext(_ctx, getState());
		enterRule(_localctx, 152, RULE_signed_number);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1149);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==MINUS) {
				{
				setState(1148);
				match(MINUS);
				}
			}

			setState(1151);
			match(NUMBER);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Signed_real_numberContext extends ParserRuleContext {
		public Real_numberContext real_number() {
			return getRuleContext(Real_numberContext.class,0);
		}
		public TerminalNode MINUS() { return getToken(PythonParser.MINUS, 0); }
		public Signed_real_numberContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_signed_real_number; }
	}

	public final Signed_real_numberContext signed_real_number() throws RecognitionException {
		Signed_real_numberContext _localctx = new Signed_real_numberContext(_ctx, getState());
		enterRule(_localctx, 154, RULE_signed_real_number);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1154);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==MINUS) {
				{
				setState(1153);
				match(MINUS);
				}
			}

			setState(1156);
			real_number();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Real_numberContext extends ParserRuleContext {
		public TerminalNode NUMBER() { return getToken(PythonParser.NUMBER, 0); }
		public Real_numberContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_real_number; }
	}

	public final Real_numberContext real_number() throws RecognitionException {
		Real_numberContext _localctx = new Real_numberContext(_ctx, getState());
		enterRule(_localctx, 156, RULE_real_number);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1158);
			match(NUMBER);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Imaginary_numberContext extends ParserRuleContext {
		public TerminalNode NUMBER() { return getToken(PythonParser.NUMBER, 0); }
		public Imaginary_numberContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_imaginary_number; }
	}

	public final Imaginary_numberContext imaginary_number() throws RecognitionException {
		Imaginary_numberContext _localctx = new Imaginary_numberContext(_ctx, getState());
		enterRule(_localctx, 158, RULE_imaginary_number);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1160);
			match(NUMBER);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Capture_patternContext extends ParserRuleContext {
		public Pattern_capture_targetContext pattern_capture_target() {
			return getRuleContext(Pattern_capture_targetContext.class,0);
		}
		public Capture_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_capture_pattern; }
	}

	public final Capture_patternContext capture_pattern() throws RecognitionException {
		Capture_patternContext _localctx = new Capture_patternContext(_ctx, getState());
		enterRule(_localctx, 160, RULE_capture_pattern);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1162);
			pattern_capture_target();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Pattern_capture_targetContext extends ParserRuleContext {
		public Soft_kw__not__wildcardContext soft_kw__not__wildcard() {
			return getRuleContext(Soft_kw__not__wildcardContext.class,0);
		}
		public Pattern_capture_targetContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_pattern_capture_target; }
	}

	public final Pattern_capture_targetContext pattern_capture_target() throws RecognitionException {
		Pattern_capture_targetContext _localctx = new Pattern_capture_targetContext(_ctx, getState());
		enterRule(_localctx, 162, RULE_pattern_capture_target);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1164);
			soft_kw__not__wildcard();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Wildcard_patternContext extends ParserRuleContext {
		public Soft_kw_wildcardContext soft_kw_wildcard() {
			return getRuleContext(Soft_kw_wildcardContext.class,0);
		}
		public Wildcard_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_wildcard_pattern; }
	}

	public final Wildcard_patternContext wildcard_pattern() throws RecognitionException {
		Wildcard_patternContext _localctx = new Wildcard_patternContext(_ctx, getState());
		enterRule(_localctx, 164, RULE_wildcard_pattern);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1166);
			soft_kw_wildcard();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Value_patternContext extends ParserRuleContext {
		public AttrContext attr() {
			return getRuleContext(AttrContext.class,0);
		}
		public Value_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_value_pattern; }
	}

	public final Value_patternContext value_pattern() throws RecognitionException {
		Value_patternContext _localctx = new Value_patternContext(_ctx, getState());
		enterRule(_localctx, 166, RULE_value_pattern);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1168);
			attr();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class AttrContext extends ParserRuleContext {
		public List<TerminalNode> NAME() { return getTokens(PythonParser.NAME); }
		public TerminalNode NAME(int i) {
			return getToken(PythonParser.NAME, i);
		}
		public List<TerminalNode> DOT() { return getTokens(PythonParser.DOT); }
		public TerminalNode DOT(int i) {
			return getToken(PythonParser.DOT, i);
		}
		public AttrContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_attr; }
	}

	public final AttrContext attr() throws RecognitionException {
		AttrContext _localctx = new AttrContext(_ctx, getState());
		enterRule(_localctx, 168, RULE_attr);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1170);
			match(NAME);
			setState(1173); 
			_errHandler.sync(this);
			_la = _input.LA(1);
			do {
				{
				{
				setState(1171);
				match(DOT);
				setState(1172);
				match(NAME);
				}
				}
				setState(1175); 
				_errHandler.sync(this);
				_la = _input.LA(1);
			} while ( _la==DOT );
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Name_or_attrContext extends ParserRuleContext {
		public List<TerminalNode> NAME() { return getTokens(PythonParser.NAME); }
		public TerminalNode NAME(int i) {
			return getToken(PythonParser.NAME, i);
		}
		public List<TerminalNode> DOT() { return getTokens(PythonParser.DOT); }
		public TerminalNode DOT(int i) {
			return getToken(PythonParser.DOT, i);
		}
		public Name_or_attrContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_name_or_attr; }
	}

	public final Name_or_attrContext name_or_attr() throws RecognitionException {
		Name_or_attrContext _localctx = new Name_or_attrContext(_ctx, getState());
		enterRule(_localctx, 170, RULE_name_or_attr);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1177);
			match(NAME);
			setState(1182);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==DOT) {
				{
				{
				setState(1178);
				match(DOT);
				setState(1179);
				match(NAME);
				}
				}
				setState(1184);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Group_patternContext extends ParserRuleContext {
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public PatternContext pattern() {
			return getRuleContext(PatternContext.class,0);
		}
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public Group_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_group_pattern; }
	}

	public final Group_patternContext group_pattern() throws RecognitionException {
		Group_patternContext _localctx = new Group_patternContext(_ctx, getState());
		enterRule(_localctx, 172, RULE_group_pattern);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1185);
			match(LPAR);
			setState(1186);
			pattern();
			setState(1187);
			match(RPAR);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Sequence_patternContext extends ParserRuleContext {
		public TerminalNode LSQB() { return getToken(PythonParser.LSQB, 0); }
		public TerminalNode RSQB() { return getToken(PythonParser.RSQB, 0); }
		public Maybe_sequence_patternContext maybe_sequence_pattern() {
			return getRuleContext(Maybe_sequence_patternContext.class,0);
		}
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public Open_sequence_patternContext open_sequence_pattern() {
			return getRuleContext(Open_sequence_patternContext.class,0);
		}
		public Sequence_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_sequence_pattern; }
	}

	public final Sequence_patternContext sequence_pattern() throws RecognitionException {
		Sequence_patternContext _localctx = new Sequence_patternContext(_ctx, getState());
		enterRule(_localctx, 174, RULE_sequence_pattern);
		try {
			setState(1199);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case LSQB:
				enterOuterAlt(_localctx, 1);
				{
				setState(1189);
				match(LSQB);
				setState(1191);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,127,_ctx) ) {
				case 1:
					{
					setState(1190);
					maybe_sequence_pattern();
					}
					break;
				}
				setState(1193);
				match(RSQB);
				}
				break;
			case LPAR:
				enterOuterAlt(_localctx, 2);
				{
				setState(1194);
				match(LPAR);
				setState(1196);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,128,_ctx) ) {
				case 1:
					{
					setState(1195);
					open_sequence_pattern();
					}
					break;
				}
				setState(1198);
				match(RPAR);
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Open_sequence_patternContext extends ParserRuleContext {
		public Maybe_star_patternContext maybe_star_pattern() {
			return getRuleContext(Maybe_star_patternContext.class,0);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public Maybe_sequence_patternContext maybe_sequence_pattern() {
			return getRuleContext(Maybe_sequence_patternContext.class,0);
		}
		public Open_sequence_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_open_sequence_pattern; }
	}

	public final Open_sequence_patternContext open_sequence_pattern() throws RecognitionException {
		Open_sequence_patternContext _localctx = new Open_sequence_patternContext(_ctx, getState());
		enterRule(_localctx, 176, RULE_open_sequence_pattern);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1201);
			maybe_star_pattern();
			setState(1202);
			match(COMMA);
			setState(1204);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,130,_ctx) ) {
			case 1:
				{
				setState(1203);
				maybe_sequence_pattern();
				}
				break;
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Maybe_sequence_patternContext extends ParserRuleContext {
		public List<Maybe_star_patternContext> maybe_star_pattern() {
			return getRuleContexts(Maybe_star_patternContext.class);
		}
		public Maybe_star_patternContext maybe_star_pattern(int i) {
			return getRuleContext(Maybe_star_patternContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Maybe_sequence_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_maybe_sequence_pattern; }
	}

	public final Maybe_sequence_patternContext maybe_sequence_pattern() throws RecognitionException {
		Maybe_sequence_patternContext _localctx = new Maybe_sequence_patternContext(_ctx, getState());
		enterRule(_localctx, 178, RULE_maybe_sequence_pattern);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(1206);
			maybe_star_pattern();
			setState(1211);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,131,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(1207);
					match(COMMA);
					setState(1208);
					maybe_star_pattern();
					}
					} 
				}
				setState(1213);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,131,_ctx);
			}
			setState(1215);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(1214);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Maybe_star_patternContext extends ParserRuleContext {
		public Star_patternContext star_pattern() {
			return getRuleContext(Star_patternContext.class,0);
		}
		public PatternContext pattern() {
			return getRuleContext(PatternContext.class,0);
		}
		public Maybe_star_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_maybe_star_pattern; }
	}

	public final Maybe_star_patternContext maybe_star_pattern() throws RecognitionException {
		Maybe_star_patternContext _localctx = new Maybe_star_patternContext(_ctx, getState());
		enterRule(_localctx, 180, RULE_maybe_star_pattern);
		try {
			setState(1219);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,133,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1217);
				star_pattern();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1218);
				pattern();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Star_patternContext extends ParserRuleContext {
		public TerminalNode STAR() { return getToken(PythonParser.STAR, 0); }
		public Pattern_capture_targetContext pattern_capture_target() {
			return getRuleContext(Pattern_capture_targetContext.class,0);
		}
		public Wildcard_patternContext wildcard_pattern() {
			return getRuleContext(Wildcard_patternContext.class,0);
		}
		public Star_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_star_pattern; }
	}

	public final Star_patternContext star_pattern() throws RecognitionException {
		Star_patternContext _localctx = new Star_patternContext(_ctx, getState());
		enterRule(_localctx, 182, RULE_star_pattern);
		try {
			setState(1225);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,134,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1221);
				match(STAR);
				setState(1222);
				pattern_capture_target();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1223);
				match(STAR);
				setState(1224);
				wildcard_pattern();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Mapping_patternContext extends ParserRuleContext {
		public TerminalNode LBRACE() { return getToken(PythonParser.LBRACE, 0); }
		public TerminalNode RBRACE() { return getToken(PythonParser.RBRACE, 0); }
		public Double_star_patternContext double_star_pattern() {
			return getRuleContext(Double_star_patternContext.class,0);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Items_patternContext items_pattern() {
			return getRuleContext(Items_patternContext.class,0);
		}
		public Mapping_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_mapping_pattern; }
	}

	public final Mapping_patternContext mapping_pattern() throws RecognitionException {
		Mapping_patternContext _localctx = new Mapping_patternContext(_ctx, getState());
		enterRule(_localctx, 184, RULE_mapping_pattern);
		int _la;
		try {
			setState(1247);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,138,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1227);
				match(LBRACE);
				setState(1228);
				match(RBRACE);
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1229);
				match(LBRACE);
				setState(1230);
				double_star_pattern();
				setState(1232);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==COMMA) {
					{
					setState(1231);
					match(COMMA);
					}
				}

				setState(1234);
				match(RBRACE);
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(1236);
				match(LBRACE);
				setState(1237);
				items_pattern();
				setState(1240);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,136,_ctx) ) {
				case 1:
					{
					setState(1238);
					match(COMMA);
					setState(1239);
					double_star_pattern();
					}
					break;
				}
				setState(1243);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==COMMA) {
					{
					setState(1242);
					match(COMMA);
					}
				}

				setState(1245);
				match(RBRACE);
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Items_patternContext extends ParserRuleContext {
		public List<Key_value_patternContext> key_value_pattern() {
			return getRuleContexts(Key_value_patternContext.class);
		}
		public Key_value_patternContext key_value_pattern(int i) {
			return getRuleContext(Key_value_patternContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Items_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_items_pattern; }
	}

	public final Items_patternContext items_pattern() throws RecognitionException {
		Items_patternContext _localctx = new Items_patternContext(_ctx, getState());
		enterRule(_localctx, 186, RULE_items_pattern);
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(1249);
			key_value_pattern();
			setState(1254);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,139,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(1250);
					match(COMMA);
					setState(1251);
					key_value_pattern();
					}
					} 
				}
				setState(1256);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,139,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Key_value_patternContext extends ParserRuleContext {
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public PatternContext pattern() {
			return getRuleContext(PatternContext.class,0);
		}
		public Literal_exprContext literal_expr() {
			return getRuleContext(Literal_exprContext.class,0);
		}
		public AttrContext attr() {
			return getRuleContext(AttrContext.class,0);
		}
		public Key_value_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_key_value_pattern; }
	}

	public final Key_value_patternContext key_value_pattern() throws RecognitionException {
		Key_value_patternContext _localctx = new Key_value_patternContext(_ctx, getState());
		enterRule(_localctx, 188, RULE_key_value_pattern);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1259);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case FSTRING_START:
			case FALSE:
			case NONE:
			case TRUE:
			case MINUS:
			case NUMBER:
			case STRING:
				{
				setState(1257);
				literal_expr();
				}
				break;
			case NAME:
				{
				setState(1258);
				attr();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
			setState(1261);
			match(COLON);
			setState(1262);
			pattern();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Double_star_patternContext extends ParserRuleContext {
		public TerminalNode DOUBLESTAR() { return getToken(PythonParser.DOUBLESTAR, 0); }
		public Pattern_capture_targetContext pattern_capture_target() {
			return getRuleContext(Pattern_capture_targetContext.class,0);
		}
		public Double_star_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_double_star_pattern; }
	}

	public final Double_star_patternContext double_star_pattern() throws RecognitionException {
		Double_star_patternContext _localctx = new Double_star_patternContext(_ctx, getState());
		enterRule(_localctx, 190, RULE_double_star_pattern);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1264);
			match(DOUBLESTAR);
			setState(1265);
			pattern_capture_target();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Class_patternContext extends ParserRuleContext {
		public Name_or_attrContext name_or_attr() {
			return getRuleContext(Name_or_attrContext.class,0);
		}
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public Positional_patternsContext positional_patterns() {
			return getRuleContext(Positional_patternsContext.class,0);
		}
		public Keyword_patternsContext keyword_patterns() {
			return getRuleContext(Keyword_patternsContext.class,0);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Class_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_class_pattern; }
	}

	public final Class_patternContext class_pattern() throws RecognitionException {
		Class_patternContext _localctx = new Class_patternContext(_ctx, getState());
		enterRule(_localctx, 192, RULE_class_pattern);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1267);
			name_or_attr();
			setState(1268);
			match(LPAR);
			setState(1280);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,144,_ctx) ) {
			case 1:
				{
				setState(1275);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,142,_ctx) ) {
				case 1:
					{
					setState(1269);
					positional_patterns();
					setState(1272);
					_errHandler.sync(this);
					switch ( getInterpreter().adaptivePredict(_input,141,_ctx) ) {
					case 1:
						{
						setState(1270);
						match(COMMA);
						setState(1271);
						keyword_patterns();
						}
						break;
					}
					}
					break;
				case 2:
					{
					setState(1274);
					keyword_patterns();
					}
					break;
				}
				setState(1278);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==COMMA) {
					{
					setState(1277);
					match(COMMA);
					}
				}

				}
				break;
			}
			setState(1282);
			match(RPAR);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Positional_patternsContext extends ParserRuleContext {
		public List<PatternContext> pattern() {
			return getRuleContexts(PatternContext.class);
		}
		public PatternContext pattern(int i) {
			return getRuleContext(PatternContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Positional_patternsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_positional_patterns; }
	}

	public final Positional_patternsContext positional_patterns() throws RecognitionException {
		Positional_patternsContext _localctx = new Positional_patternsContext(_ctx, getState());
		enterRule(_localctx, 194, RULE_positional_patterns);
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(1284);
			pattern();
			setState(1289);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,145,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(1285);
					match(COMMA);
					setState(1286);
					pattern();
					}
					} 
				}
				setState(1291);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,145,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Keyword_patternsContext extends ParserRuleContext {
		public List<Keyword_patternContext> keyword_pattern() {
			return getRuleContexts(Keyword_patternContext.class);
		}
		public Keyword_patternContext keyword_pattern(int i) {
			return getRuleContext(Keyword_patternContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Keyword_patternsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_keyword_patterns; }
	}

	public final Keyword_patternsContext keyword_patterns() throws RecognitionException {
		Keyword_patternsContext _localctx = new Keyword_patternsContext(_ctx, getState());
		enterRule(_localctx, 196, RULE_keyword_patterns);
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(1292);
			keyword_pattern();
			setState(1297);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,146,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(1293);
					match(COMMA);
					setState(1294);
					keyword_pattern();
					}
					} 
				}
				setState(1299);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,146,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Keyword_patternContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode EQUAL() { return getToken(PythonParser.EQUAL, 0); }
		public PatternContext pattern() {
			return getRuleContext(PatternContext.class,0);
		}
		public Keyword_patternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_keyword_pattern; }
	}

	public final Keyword_patternContext keyword_pattern() throws RecognitionException {
		Keyword_patternContext _localctx = new Keyword_patternContext(_ctx, getState());
		enterRule(_localctx, 198, RULE_keyword_pattern);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1300);
			match(NAME);
			setState(1301);
			match(EQUAL);
			setState(1302);
			pattern();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Type_aliasContext extends ParserRuleContext {
		public Soft_kw_typeContext soft_kw_type() {
			return getRuleContext(Soft_kw_typeContext.class,0);
		}
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode EQUAL() { return getToken(PythonParser.EQUAL, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public Type_paramsContext type_params() {
			return getRuleContext(Type_paramsContext.class,0);
		}
		public Type_aliasContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_type_alias; }
	}

	public final Type_aliasContext type_alias() throws RecognitionException {
		Type_aliasContext _localctx = new Type_aliasContext(_ctx, getState());
		enterRule(_localctx, 200, RULE_type_alias);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1304);
			soft_kw_type();
			setState(1305);
			match(NAME);
			setState(1307);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==LSQB) {
				{
				setState(1306);
				type_params();
				}
			}

			setState(1309);
			match(EQUAL);
			setState(1310);
			expression();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Type_paramsContext extends ParserRuleContext {
		public TerminalNode LSQB() { return getToken(PythonParser.LSQB, 0); }
		public Type_param_seqContext type_param_seq() {
			return getRuleContext(Type_param_seqContext.class,0);
		}
		public TerminalNode RSQB() { return getToken(PythonParser.RSQB, 0); }
		public Type_paramsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_type_params; }
	}

	public final Type_paramsContext type_params() throws RecognitionException {
		Type_paramsContext _localctx = new Type_paramsContext(_ctx, getState());
		enterRule(_localctx, 202, RULE_type_params);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1312);
			match(LSQB);
			setState(1313);
			type_param_seq();
			setState(1314);
			match(RSQB);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Type_param_seqContext extends ParserRuleContext {
		public List<Type_paramContext> type_param() {
			return getRuleContexts(Type_paramContext.class);
		}
		public Type_paramContext type_param(int i) {
			return getRuleContext(Type_paramContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Type_param_seqContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_type_param_seq; }
	}

	public final Type_param_seqContext type_param_seq() throws RecognitionException {
		Type_param_seqContext _localctx = new Type_param_seqContext(_ctx, getState());
		enterRule(_localctx, 204, RULE_type_param_seq);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(1316);
			type_param();
			setState(1321);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,148,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(1317);
					match(COMMA);
					setState(1318);
					type_param();
					}
					} 
				}
				setState(1323);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,148,_ctx);
			}
			setState(1325);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(1324);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Type_paramContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public Type_param_boundContext type_param_bound() {
			return getRuleContext(Type_param_boundContext.class,0);
		}
		public TerminalNode STAR() { return getToken(PythonParser.STAR, 0); }
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public TerminalNode DOUBLESTAR() { return getToken(PythonParser.DOUBLESTAR, 0); }
		public Type_paramContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_type_param; }
	}

	public final Type_paramContext type_param() throws RecognitionException {
		Type_paramContext _localctx = new Type_paramContext(_ctx, getState());
		enterRule(_localctx, 206, RULE_type_param);
		int _la;
		try {
			setState(1343);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case NAME:
				enterOuterAlt(_localctx, 1);
				{
				setState(1327);
				match(NAME);
				setState(1329);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==COLON) {
					{
					setState(1328);
					type_param_bound();
					}
				}

				}
				break;
			case STAR:
				enterOuterAlt(_localctx, 2);
				{
				setState(1331);
				match(STAR);
				setState(1332);
				match(NAME);
				setState(1335);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==COLON) {
					{
					setState(1333);
					match(COLON);
					setState(1334);
					expression();
					}
				}

				}
				break;
			case DOUBLESTAR:
				enterOuterAlt(_localctx, 3);
				{
				setState(1337);
				match(DOUBLESTAR);
				setState(1338);
				match(NAME);
				setState(1341);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==COLON) {
					{
					setState(1339);
					match(COLON);
					setState(1340);
					expression();
					}
				}

				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Type_param_boundContext extends ParserRuleContext {
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public Type_param_boundContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_type_param_bound; }
	}

	public final Type_param_boundContext type_param_bound() throws RecognitionException {
		Type_param_boundContext _localctx = new Type_param_boundContext(_ctx, getState());
		enterRule(_localctx, 208, RULE_type_param_bound);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1345);
			match(COLON);
			setState(1346);
			expression();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ExpressionsContext extends ParserRuleContext {
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public ExpressionsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_expressions; }
	}

	public final ExpressionsContext expressions() throws RecognitionException {
		ExpressionsContext _localctx = new ExpressionsContext(_ctx, getState());
		enterRule(_localctx, 210, RULE_expressions);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(1348);
			expression();
			setState(1353);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,154,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(1349);
					match(COMMA);
					setState(1350);
					expression();
					}
					} 
				}
				setState(1355);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,154,_ctx);
			}
			setState(1357);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(1356);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ExpressionContext extends ParserRuleContext {
		public List<DisjunctionContext> disjunction() {
			return getRuleContexts(DisjunctionContext.class);
		}
		public DisjunctionContext disjunction(int i) {
			return getRuleContext(DisjunctionContext.class,i);
		}
		public TerminalNode IF() { return getToken(PythonParser.IF, 0); }
		public TerminalNode ELSE() { return getToken(PythonParser.ELSE, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public LambdefContext lambdef() {
			return getRuleContext(LambdefContext.class,0);
		}
		public ExpressionContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_expression; }
	}

	public final ExpressionContext expression() throws RecognitionException {
		ExpressionContext _localctx = new ExpressionContext(_ctx, getState());
		enterRule(_localctx, 212, RULE_expression);
		int _la;
		try {
			setState(1368);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case FSTRING_START:
			case FALSE:
			case AWAIT:
			case NONE:
			case TRUE:
			case NOT:
			case LPAR:
			case LSQB:
			case LBRACE:
			case PLUS:
			case MINUS:
			case TILDE:
			case ELLIPSIS:
			case NAME:
			case NUMBER:
			case STRING:
				enterOuterAlt(_localctx, 1);
				{
				setState(1359);
				disjunction();
				setState(1365);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==IF) {
					{
					setState(1360);
					match(IF);
					setState(1361);
					disjunction();
					setState(1362);
					match(ELSE);
					setState(1363);
					expression();
					}
				}

				}
				break;
			case LAMBDA:
				enterOuterAlt(_localctx, 2);
				{
				setState(1367);
				lambdef();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Yield_exprContext extends ParserRuleContext {
		public TerminalNode YIELD() { return getToken(PythonParser.YIELD, 0); }
		public TerminalNode FROM() { return getToken(PythonParser.FROM, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public Star_expressionsContext star_expressions() {
			return getRuleContext(Star_expressionsContext.class,0);
		}
		public Yield_exprContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_yield_expr; }
	}

	public final Yield_exprContext yield_expr() throws RecognitionException {
		Yield_exprContext _localctx = new Yield_exprContext(_ctx, getState());
		enterRule(_localctx, 214, RULE_yield_expr);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1370);
			match(YIELD);
			setState(1376);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case FROM:
				{
				setState(1371);
				match(FROM);
				setState(1372);
				expression();
				}
				break;
			case FSTRING_START:
			case FALSE:
			case AWAIT:
			case NONE:
			case TRUE:
			case LAMBDA:
			case NOT:
			case LPAR:
			case LSQB:
			case LBRACE:
			case RPAR:
			case RBRACE:
			case COLON:
			case SEMI:
			case PLUS:
			case MINUS:
			case STAR:
			case EQUAL:
			case TILDE:
			case ELLIPSIS:
			case EXCLAMATION:
			case NAME:
			case NUMBER:
			case STRING:
			case TYPE_COMMENT:
			case NEWLINE:
				{
				setState(1374);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 63111984631056584L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859201L) != 0)) {
					{
					setState(1373);
					star_expressions();
					}
				}

				}
				break;
			default:
				throw new NoViableAltException(this);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Star_expressionsContext extends ParserRuleContext {
		public List<Star_expressionContext> star_expression() {
			return getRuleContexts(Star_expressionContext.class);
		}
		public Star_expressionContext star_expression(int i) {
			return getRuleContext(Star_expressionContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Star_expressionsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_star_expressions; }
	}

	public final Star_expressionsContext star_expressions() throws RecognitionException {
		Star_expressionsContext _localctx = new Star_expressionsContext(_ctx, getState());
		enterRule(_localctx, 216, RULE_star_expressions);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(1378);
			star_expression();
			setState(1383);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,160,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(1379);
					match(COMMA);
					setState(1380);
					star_expression();
					}
					} 
				}
				setState(1385);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,160,_ctx);
			}
			setState(1387);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(1386);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Star_expressionContext extends ParserRuleContext {
		public TerminalNode STAR() { return getToken(PythonParser.STAR, 0); }
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public Star_expressionContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_star_expression; }
	}

	public final Star_expressionContext star_expression() throws RecognitionException {
		Star_expressionContext _localctx = new Star_expressionContext(_ctx, getState());
		enterRule(_localctx, 218, RULE_star_expression);
		try {
			setState(1392);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case STAR:
				enterOuterAlt(_localctx, 1);
				{
				setState(1389);
				match(STAR);
				setState(1390);
				bitwise_or(0);
				}
				break;
			case FSTRING_START:
			case FALSE:
			case AWAIT:
			case NONE:
			case TRUE:
			case LAMBDA:
			case NOT:
			case LPAR:
			case LSQB:
			case LBRACE:
			case PLUS:
			case MINUS:
			case TILDE:
			case ELLIPSIS:
			case NAME:
			case NUMBER:
			case STRING:
				enterOuterAlt(_localctx, 2);
				{
				setState(1391);
				expression();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Star_named_expressionsContext extends ParserRuleContext {
		public List<Star_named_expressionContext> star_named_expression() {
			return getRuleContexts(Star_named_expressionContext.class);
		}
		public Star_named_expressionContext star_named_expression(int i) {
			return getRuleContext(Star_named_expressionContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Star_named_expressionsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_star_named_expressions; }
	}

	public final Star_named_expressionsContext star_named_expressions() throws RecognitionException {
		Star_named_expressionsContext _localctx = new Star_named_expressionsContext(_ctx, getState());
		enterRule(_localctx, 220, RULE_star_named_expressions);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(1394);
			star_named_expression();
			setState(1399);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,163,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(1395);
					match(COMMA);
					setState(1396);
					star_named_expression();
					}
					} 
				}
				setState(1401);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,163,_ctx);
			}
			setState(1403);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(1402);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Star_named_expressionContext extends ParserRuleContext {
		public TerminalNode STAR() { return getToken(PythonParser.STAR, 0); }
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public Named_expressionContext named_expression() {
			return getRuleContext(Named_expressionContext.class,0);
		}
		public Star_named_expressionContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_star_named_expression; }
	}

	public final Star_named_expressionContext star_named_expression() throws RecognitionException {
		Star_named_expressionContext _localctx = new Star_named_expressionContext(_ctx, getState());
		enterRule(_localctx, 222, RULE_star_named_expression);
		try {
			setState(1408);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case STAR:
				enterOuterAlt(_localctx, 1);
				{
				setState(1405);
				match(STAR);
				setState(1406);
				bitwise_or(0);
				}
				break;
			case FSTRING_START:
			case FALSE:
			case AWAIT:
			case NONE:
			case TRUE:
			case LAMBDA:
			case NOT:
			case LPAR:
			case LSQB:
			case LBRACE:
			case PLUS:
			case MINUS:
			case TILDE:
			case ELLIPSIS:
			case NAME:
			case NUMBER:
			case STRING:
				enterOuterAlt(_localctx, 2);
				{
				setState(1407);
				named_expression();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Assignment_expressionContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode COLONEQUAL() { return getToken(PythonParser.COLONEQUAL, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public Assignment_expressionContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_assignment_expression; }
	}

	public final Assignment_expressionContext assignment_expression() throws RecognitionException {
		Assignment_expressionContext _localctx = new Assignment_expressionContext(_ctx, getState());
		enterRule(_localctx, 224, RULE_assignment_expression);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1410);
			match(NAME);
			setState(1411);
			match(COLONEQUAL);
			setState(1412);
			expression();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Named_expressionContext extends ParserRuleContext {
		public Assignment_expressionContext assignment_expression() {
			return getRuleContext(Assignment_expressionContext.class,0);
		}
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public Named_expressionContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_named_expression; }
	}

	public final Named_expressionContext named_expression() throws RecognitionException {
		Named_expressionContext _localctx = new Named_expressionContext(_ctx, getState());
		enterRule(_localctx, 226, RULE_named_expression);
		try {
			setState(1416);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,166,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1414);
				assignment_expression();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1415);
				expression();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class DisjunctionContext extends ParserRuleContext {
		public List<ConjunctionContext> conjunction() {
			return getRuleContexts(ConjunctionContext.class);
		}
		public ConjunctionContext conjunction(int i) {
			return getRuleContext(ConjunctionContext.class,i);
		}
		public List<TerminalNode> OR() { return getTokens(PythonParser.OR); }
		public TerminalNode OR(int i) {
			return getToken(PythonParser.OR, i);
		}
		public DisjunctionContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_disjunction; }
	}

	public final DisjunctionContext disjunction() throws RecognitionException {
		DisjunctionContext _localctx = new DisjunctionContext(_ctx, getState());
		enterRule(_localctx, 228, RULE_disjunction);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1418);
			conjunction();
			setState(1423);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==OR) {
				{
				{
				setState(1419);
				match(OR);
				setState(1420);
				conjunction();
				}
				}
				setState(1425);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ConjunctionContext extends ParserRuleContext {
		public List<InversionContext> inversion() {
			return getRuleContexts(InversionContext.class);
		}
		public InversionContext inversion(int i) {
			return getRuleContext(InversionContext.class,i);
		}
		public List<TerminalNode> AND() { return getTokens(PythonParser.AND); }
		public TerminalNode AND(int i) {
			return getToken(PythonParser.AND, i);
		}
		public ConjunctionContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_conjunction; }
	}

	public final ConjunctionContext conjunction() throws RecognitionException {
		ConjunctionContext _localctx = new ConjunctionContext(_ctx, getState());
		enterRule(_localctx, 230, RULE_conjunction);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1426);
			inversion();
			setState(1431);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==AND) {
				{
				{
				setState(1427);
				match(AND);
				setState(1428);
				inversion();
				}
				}
				setState(1433);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class InversionContext extends ParserRuleContext {
		public TerminalNode NOT() { return getToken(PythonParser.NOT, 0); }
		public InversionContext inversion() {
			return getRuleContext(InversionContext.class,0);
		}
		public ComparisonContext comparison() {
			return getRuleContext(ComparisonContext.class,0);
		}
		public InversionContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_inversion; }
	}

	public final InversionContext inversion() throws RecognitionException {
		InversionContext _localctx = new InversionContext(_ctx, getState());
		enterRule(_localctx, 232, RULE_inversion);
		try {
			setState(1437);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case NOT:
				enterOuterAlt(_localctx, 1);
				{
				setState(1434);
				match(NOT);
				setState(1435);
				inversion();
				}
				break;
			case FSTRING_START:
			case FALSE:
			case AWAIT:
			case NONE:
			case TRUE:
			case LPAR:
			case LSQB:
			case LBRACE:
			case PLUS:
			case MINUS:
			case TILDE:
			case ELLIPSIS:
			case NAME:
			case NUMBER:
			case STRING:
				enterOuterAlt(_localctx, 2);
				{
				setState(1436);
				comparison();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ComparisonContext extends ParserRuleContext {
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public List<Compare_op_bitwise_or_pairContext> compare_op_bitwise_or_pair() {
			return getRuleContexts(Compare_op_bitwise_or_pairContext.class);
		}
		public Compare_op_bitwise_or_pairContext compare_op_bitwise_or_pair(int i) {
			return getRuleContext(Compare_op_bitwise_or_pairContext.class,i);
		}
		public ComparisonContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_comparison; }
	}

	public final ComparisonContext comparison() throws RecognitionException {
		ComparisonContext _localctx = new ComparisonContext(_ctx, getState());
		enterRule(_localctx, 234, RULE_comparison);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1439);
			bitwise_or(0);
			setState(1443);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (((((_la - 14)) & ~0x3f) == 0 && ((1L << (_la - 14)) & 8549802418634785L) != 0)) {
				{
				{
				setState(1440);
				compare_op_bitwise_or_pair();
				}
				}
				setState(1445);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Compare_op_bitwise_or_pairContext extends ParserRuleContext {
		public Eq_bitwise_orContext eq_bitwise_or() {
			return getRuleContext(Eq_bitwise_orContext.class,0);
		}
		public Noteq_bitwise_orContext noteq_bitwise_or() {
			return getRuleContext(Noteq_bitwise_orContext.class,0);
		}
		public Lte_bitwise_orContext lte_bitwise_or() {
			return getRuleContext(Lte_bitwise_orContext.class,0);
		}
		public Lt_bitwise_orContext lt_bitwise_or() {
			return getRuleContext(Lt_bitwise_orContext.class,0);
		}
		public Gte_bitwise_orContext gte_bitwise_or() {
			return getRuleContext(Gte_bitwise_orContext.class,0);
		}
		public Gt_bitwise_orContext gt_bitwise_or() {
			return getRuleContext(Gt_bitwise_orContext.class,0);
		}
		public Notin_bitwise_orContext notin_bitwise_or() {
			return getRuleContext(Notin_bitwise_orContext.class,0);
		}
		public In_bitwise_orContext in_bitwise_or() {
			return getRuleContext(In_bitwise_orContext.class,0);
		}
		public Isnot_bitwise_orContext isnot_bitwise_or() {
			return getRuleContext(Isnot_bitwise_orContext.class,0);
		}
		public Is_bitwise_orContext is_bitwise_or() {
			return getRuleContext(Is_bitwise_orContext.class,0);
		}
		public Compare_op_bitwise_or_pairContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_compare_op_bitwise_or_pair; }
	}

	public final Compare_op_bitwise_or_pairContext compare_op_bitwise_or_pair() throws RecognitionException {
		Compare_op_bitwise_or_pairContext _localctx = new Compare_op_bitwise_or_pairContext(_ctx, getState());
		enterRule(_localctx, 236, RULE_compare_op_bitwise_or_pair);
		try {
			setState(1456);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,171,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1446);
				eq_bitwise_or();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1447);
				noteq_bitwise_or();
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(1448);
				lte_bitwise_or();
				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(1449);
				lt_bitwise_or();
				}
				break;
			case 5:
				enterOuterAlt(_localctx, 5);
				{
				setState(1450);
				gte_bitwise_or();
				}
				break;
			case 6:
				enterOuterAlt(_localctx, 6);
				{
				setState(1451);
				gt_bitwise_or();
				}
				break;
			case 7:
				enterOuterAlt(_localctx, 7);
				{
				setState(1452);
				notin_bitwise_or();
				}
				break;
			case 8:
				enterOuterAlt(_localctx, 8);
				{
				setState(1453);
				in_bitwise_or();
				}
				break;
			case 9:
				enterOuterAlt(_localctx, 9);
				{
				setState(1454);
				isnot_bitwise_or();
				}
				break;
			case 10:
				enterOuterAlt(_localctx, 10);
				{
				setState(1455);
				is_bitwise_or();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Eq_bitwise_orContext extends ParserRuleContext {
		public TerminalNode EQEQUAL() { return getToken(PythonParser.EQEQUAL, 0); }
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public Eq_bitwise_orContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_eq_bitwise_or; }
	}

	public final Eq_bitwise_orContext eq_bitwise_or() throws RecognitionException {
		Eq_bitwise_orContext _localctx = new Eq_bitwise_orContext(_ctx, getState());
		enterRule(_localctx, 238, RULE_eq_bitwise_or);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1458);
			match(EQEQUAL);
			setState(1459);
			bitwise_or(0);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Noteq_bitwise_orContext extends ParserRuleContext {
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public TerminalNode NOTEQUAL() { return getToken(PythonParser.NOTEQUAL, 0); }
		public Noteq_bitwise_orContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_noteq_bitwise_or; }
	}

	public final Noteq_bitwise_orContext noteq_bitwise_or() throws RecognitionException {
		Noteq_bitwise_orContext _localctx = new Noteq_bitwise_orContext(_ctx, getState());
		enterRule(_localctx, 240, RULE_noteq_bitwise_or);
		try {
			enterOuterAlt(_localctx, 1);
			{
			{
			setState(1461);
			match(NOTEQUAL);
			}
			setState(1462);
			bitwise_or(0);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Lte_bitwise_orContext extends ParserRuleContext {
		public TerminalNode LESSEQUAL() { return getToken(PythonParser.LESSEQUAL, 0); }
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public Lte_bitwise_orContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_lte_bitwise_or; }
	}

	public final Lte_bitwise_orContext lte_bitwise_or() throws RecognitionException {
		Lte_bitwise_orContext _localctx = new Lte_bitwise_orContext(_ctx, getState());
		enterRule(_localctx, 242, RULE_lte_bitwise_or);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1464);
			match(LESSEQUAL);
			setState(1465);
			bitwise_or(0);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Lt_bitwise_orContext extends ParserRuleContext {
		public TerminalNode LESS() { return getToken(PythonParser.LESS, 0); }
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public Lt_bitwise_orContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_lt_bitwise_or; }
	}

	public final Lt_bitwise_orContext lt_bitwise_or() throws RecognitionException {
		Lt_bitwise_orContext _localctx = new Lt_bitwise_orContext(_ctx, getState());
		enterRule(_localctx, 244, RULE_lt_bitwise_or);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1467);
			match(LESS);
			setState(1468);
			bitwise_or(0);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Gte_bitwise_orContext extends ParserRuleContext {
		public TerminalNode GREATEREQUAL() { return getToken(PythonParser.GREATEREQUAL, 0); }
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public Gte_bitwise_orContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_gte_bitwise_or; }
	}

	public final Gte_bitwise_orContext gte_bitwise_or() throws RecognitionException {
		Gte_bitwise_orContext _localctx = new Gte_bitwise_orContext(_ctx, getState());
		enterRule(_localctx, 246, RULE_gte_bitwise_or);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1470);
			match(GREATEREQUAL);
			setState(1471);
			bitwise_or(0);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Gt_bitwise_orContext extends ParserRuleContext {
		public TerminalNode GREATER() { return getToken(PythonParser.GREATER, 0); }
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public Gt_bitwise_orContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_gt_bitwise_or; }
	}

	public final Gt_bitwise_orContext gt_bitwise_or() throws RecognitionException {
		Gt_bitwise_orContext _localctx = new Gt_bitwise_orContext(_ctx, getState());
		enterRule(_localctx, 248, RULE_gt_bitwise_or);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1473);
			match(GREATER);
			setState(1474);
			bitwise_or(0);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Notin_bitwise_orContext extends ParserRuleContext {
		public TerminalNode NOT() { return getToken(PythonParser.NOT, 0); }
		public TerminalNode IN() { return getToken(PythonParser.IN, 0); }
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public Notin_bitwise_orContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_notin_bitwise_or; }
	}

	public final Notin_bitwise_orContext notin_bitwise_or() throws RecognitionException {
		Notin_bitwise_orContext _localctx = new Notin_bitwise_orContext(_ctx, getState());
		enterRule(_localctx, 250, RULE_notin_bitwise_or);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1476);
			match(NOT);
			setState(1477);
			match(IN);
			setState(1478);
			bitwise_or(0);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class In_bitwise_orContext extends ParserRuleContext {
		public TerminalNode IN() { return getToken(PythonParser.IN, 0); }
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public In_bitwise_orContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_in_bitwise_or; }
	}

	public final In_bitwise_orContext in_bitwise_or() throws RecognitionException {
		In_bitwise_orContext _localctx = new In_bitwise_orContext(_ctx, getState());
		enterRule(_localctx, 252, RULE_in_bitwise_or);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1480);
			match(IN);
			setState(1481);
			bitwise_or(0);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Isnot_bitwise_orContext extends ParserRuleContext {
		public TerminalNode IS() { return getToken(PythonParser.IS, 0); }
		public TerminalNode NOT() { return getToken(PythonParser.NOT, 0); }
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public Isnot_bitwise_orContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_isnot_bitwise_or; }
	}

	public final Isnot_bitwise_orContext isnot_bitwise_or() throws RecognitionException {
		Isnot_bitwise_orContext _localctx = new Isnot_bitwise_orContext(_ctx, getState());
		enterRule(_localctx, 254, RULE_isnot_bitwise_or);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1483);
			match(IS);
			setState(1484);
			match(NOT);
			setState(1485);
			bitwise_or(0);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Is_bitwise_orContext extends ParserRuleContext {
		public TerminalNode IS() { return getToken(PythonParser.IS, 0); }
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public Is_bitwise_orContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_is_bitwise_or; }
	}

	public final Is_bitwise_orContext is_bitwise_or() throws RecognitionException {
		Is_bitwise_orContext _localctx = new Is_bitwise_orContext(_ctx, getState());
		enterRule(_localctx, 256, RULE_is_bitwise_or);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1487);
			match(IS);
			setState(1488);
			bitwise_or(0);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Bitwise_orContext extends ParserRuleContext {
		public Bitwise_xorContext bitwise_xor() {
			return getRuleContext(Bitwise_xorContext.class,0);
		}
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public TerminalNode VBAR() { return getToken(PythonParser.VBAR, 0); }
		public Bitwise_orContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_bitwise_or; }
	}

	public final Bitwise_orContext bitwise_or() throws RecognitionException {
		return bitwise_or(0);
	}

	private Bitwise_orContext bitwise_or(int _p) throws RecognitionException {
		ParserRuleContext _parentctx = _ctx;
		int _parentState = getState();
		Bitwise_orContext _localctx = new Bitwise_orContext(_ctx, _parentState);
		Bitwise_orContext _prevctx = _localctx;
		int _startState = 258;
		enterRecursionRule(_localctx, 258, RULE_bitwise_or, _p);
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			{
			setState(1491);
			bitwise_xor(0);
			}
			_ctx.stop = _input.LT(-1);
			setState(1498);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,172,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					if ( _parseListeners!=null ) triggerExitRuleEvent();
					_prevctx = _localctx;
					{
					{
					_localctx = new Bitwise_orContext(_parentctx, _parentState);
					pushNewRecursionContext(_localctx, _startState, RULE_bitwise_or);
					setState(1493);
					if (!(precpred(_ctx, 2))) throw new FailedPredicateException(this, "precpred(_ctx, 2)");
					setState(1494);
					match(VBAR);
					setState(1495);
					bitwise_xor(0);
					}
					} 
				}
				setState(1500);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,172,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			unrollRecursionContexts(_parentctx);
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Bitwise_xorContext extends ParserRuleContext {
		public Bitwise_andContext bitwise_and() {
			return getRuleContext(Bitwise_andContext.class,0);
		}
		public Bitwise_xorContext bitwise_xor() {
			return getRuleContext(Bitwise_xorContext.class,0);
		}
		public TerminalNode CIRCUMFLEX() { return getToken(PythonParser.CIRCUMFLEX, 0); }
		public Bitwise_xorContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_bitwise_xor; }
	}

	public final Bitwise_xorContext bitwise_xor() throws RecognitionException {
		return bitwise_xor(0);
	}

	private Bitwise_xorContext bitwise_xor(int _p) throws RecognitionException {
		ParserRuleContext _parentctx = _ctx;
		int _parentState = getState();
		Bitwise_xorContext _localctx = new Bitwise_xorContext(_ctx, _parentState);
		Bitwise_xorContext _prevctx = _localctx;
		int _startState = 260;
		enterRecursionRule(_localctx, 260, RULE_bitwise_xor, _p);
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			{
			setState(1502);
			bitwise_and(0);
			}
			_ctx.stop = _input.LT(-1);
			setState(1509);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,173,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					if ( _parseListeners!=null ) triggerExitRuleEvent();
					_prevctx = _localctx;
					{
					{
					_localctx = new Bitwise_xorContext(_parentctx, _parentState);
					pushNewRecursionContext(_localctx, _startState, RULE_bitwise_xor);
					setState(1504);
					if (!(precpred(_ctx, 2))) throw new FailedPredicateException(this, "precpred(_ctx, 2)");
					setState(1505);
					match(CIRCUMFLEX);
					setState(1506);
					bitwise_and(0);
					}
					} 
				}
				setState(1511);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,173,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			unrollRecursionContexts(_parentctx);
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Bitwise_andContext extends ParserRuleContext {
		public Shift_exprContext shift_expr() {
			return getRuleContext(Shift_exprContext.class,0);
		}
		public Bitwise_andContext bitwise_and() {
			return getRuleContext(Bitwise_andContext.class,0);
		}
		public TerminalNode AMPER() { return getToken(PythonParser.AMPER, 0); }
		public Bitwise_andContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_bitwise_and; }
	}

	public final Bitwise_andContext bitwise_and() throws RecognitionException {
		return bitwise_and(0);
	}

	private Bitwise_andContext bitwise_and(int _p) throws RecognitionException {
		ParserRuleContext _parentctx = _ctx;
		int _parentState = getState();
		Bitwise_andContext _localctx = new Bitwise_andContext(_ctx, _parentState);
		Bitwise_andContext _prevctx = _localctx;
		int _startState = 262;
		enterRecursionRule(_localctx, 262, RULE_bitwise_and, _p);
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			{
			setState(1513);
			shift_expr(0);
			}
			_ctx.stop = _input.LT(-1);
			setState(1520);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,174,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					if ( _parseListeners!=null ) triggerExitRuleEvent();
					_prevctx = _localctx;
					{
					{
					_localctx = new Bitwise_andContext(_parentctx, _parentState);
					pushNewRecursionContext(_localctx, _startState, RULE_bitwise_and);
					setState(1515);
					if (!(precpred(_ctx, 2))) throw new FailedPredicateException(this, "precpred(_ctx, 2)");
					setState(1516);
					match(AMPER);
					setState(1517);
					shift_expr(0);
					}
					} 
				}
				setState(1522);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,174,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			unrollRecursionContexts(_parentctx);
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Shift_exprContext extends ParserRuleContext {
		public SumContext sum() {
			return getRuleContext(SumContext.class,0);
		}
		public Shift_exprContext shift_expr() {
			return getRuleContext(Shift_exprContext.class,0);
		}
		public TerminalNode LEFTSHIFT() { return getToken(PythonParser.LEFTSHIFT, 0); }
		public TerminalNode RIGHTSHIFT() { return getToken(PythonParser.RIGHTSHIFT, 0); }
		public Shift_exprContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_shift_expr; }
	}

	public final Shift_exprContext shift_expr() throws RecognitionException {
		return shift_expr(0);
	}

	private Shift_exprContext shift_expr(int _p) throws RecognitionException {
		ParserRuleContext _parentctx = _ctx;
		int _parentState = getState();
		Shift_exprContext _localctx = new Shift_exprContext(_ctx, _parentState);
		Shift_exprContext _prevctx = _localctx;
		int _startState = 264;
		enterRecursionRule(_localctx, 264, RULE_shift_expr, _p);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			{
			setState(1524);
			sum(0);
			}
			_ctx.stop = _input.LT(-1);
			setState(1531);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,175,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					if ( _parseListeners!=null ) triggerExitRuleEvent();
					_prevctx = _localctx;
					{
					{
					_localctx = new Shift_exprContext(_parentctx, _parentState);
					pushNewRecursionContext(_localctx, _startState, RULE_shift_expr);
					setState(1526);
					if (!(precpred(_ctx, 2))) throw new FailedPredicateException(this, "precpred(_ctx, 2)");
					setState(1527);
					_la = _input.LA(1);
					if ( !(_la==LEFTSHIFT || _la==RIGHTSHIFT) ) {
					_errHandler.recoverInline(this);
					}
					else {
						if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
						_errHandler.reportMatch(this);
						consume();
					}
					setState(1528);
					sum(0);
					}
					} 
				}
				setState(1533);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,175,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			unrollRecursionContexts(_parentctx);
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class SumContext extends ParserRuleContext {
		public TermContext term() {
			return getRuleContext(TermContext.class,0);
		}
		public SumContext sum() {
			return getRuleContext(SumContext.class,0);
		}
		public TerminalNode PLUS() { return getToken(PythonParser.PLUS, 0); }
		public TerminalNode MINUS() { return getToken(PythonParser.MINUS, 0); }
		public SumContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_sum; }
	}

	public final SumContext sum() throws RecognitionException {
		return sum(0);
	}

	private SumContext sum(int _p) throws RecognitionException {
		ParserRuleContext _parentctx = _ctx;
		int _parentState = getState();
		SumContext _localctx = new SumContext(_ctx, _parentState);
		SumContext _prevctx = _localctx;
		int _startState = 266;
		enterRecursionRule(_localctx, 266, RULE_sum, _p);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			{
			setState(1535);
			term(0);
			}
			_ctx.stop = _input.LT(-1);
			setState(1542);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,176,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					if ( _parseListeners!=null ) triggerExitRuleEvent();
					_prevctx = _localctx;
					{
					{
					_localctx = new SumContext(_parentctx, _parentState);
					pushNewRecursionContext(_localctx, _startState, RULE_sum);
					setState(1537);
					if (!(precpred(_ctx, 2))) throw new FailedPredicateException(this, "precpred(_ctx, 2)");
					setState(1538);
					_la = _input.LA(1);
					if ( !(_la==PLUS || _la==MINUS) ) {
					_errHandler.recoverInline(this);
					}
					else {
						if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
						_errHandler.reportMatch(this);
						consume();
					}
					setState(1539);
					term(0);
					}
					} 
				}
				setState(1544);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,176,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			unrollRecursionContexts(_parentctx);
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class TermContext extends ParserRuleContext {
		public ToleranceContext tolerance() {
			return getRuleContext(ToleranceContext.class,0);
		}
		public TermContext term() {
			return getRuleContext(TermContext.class,0);
		}
		public TerminalNode STAR() { return getToken(PythonParser.STAR, 0); }
		public TerminalNode SLASH() { return getToken(PythonParser.SLASH, 0); }
		public TerminalNode DOUBLESLASH() { return getToken(PythonParser.DOUBLESLASH, 0); }
		public TerminalNode PERCENT() { return getToken(PythonParser.PERCENT, 0); }
		public TerminalNode AT() { return getToken(PythonParser.AT, 0); }
		public TermContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_term; }
	}

	public final TermContext term() throws RecognitionException {
		return term(0);
	}

	private TermContext term(int _p) throws RecognitionException {
		ParserRuleContext _parentctx = _ctx;
		int _parentState = getState();
		TermContext _localctx = new TermContext(_ctx, _parentState);
		TermContext _prevctx = _localctx;
		int _startState = 268;
		enterRecursionRule(_localctx, 268, RULE_term, _p);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			{
			setState(1546);
			tolerance(0);
			}
			_ctx.stop = _input.LT(-1);
			setState(1553);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,177,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					if ( _parseListeners!=null ) triggerExitRuleEvent();
					_prevctx = _localctx;
					{
					{
					_localctx = new TermContext(_parentctx, _parentState);
					pushNewRecursionContext(_localctx, _startState, RULE_term);
					setState(1548);
					if (!(precpred(_ctx, 2))) throw new FailedPredicateException(this, "precpred(_ctx, 2)");
					setState(1549);
					_la = _input.LA(1);
					if ( !(((((_la - 55)) & ~0x3f) == 0 && ((1L << (_la - 55)) & 1342177411L) != 0)) ) {
					_errHandler.recoverInline(this);
					}
					else {
						if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
						_errHandler.reportMatch(this);
						consume();
					}
					setState(1550);
					tolerance(0);
					}
					} 
				}
				setState(1555);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,177,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			unrollRecursionContexts(_parentctx);
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ToleranceContext extends ParserRuleContext {
		public FactorContext factor() {
			return getRuleContext(FactorContext.class,0);
		}
		public ToleranceContext tolerance() {
			return getRuleContext(ToleranceContext.class,0);
		}
		public TerminalNode TO() { return getToken(PythonParser.TO, 0); }
		public TerminalNode PLUS_OR_MINUS() { return getToken(PythonParser.PLUS_OR_MINUS, 0); }
		public TerminalNode PLUS_OR_MINU2() { return getToken(PythonParser.PLUS_OR_MINU2, 0); }
		public ToleranceContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_tolerance; }
	}

	public final ToleranceContext tolerance() throws RecognitionException {
		return tolerance(0);
	}

	private ToleranceContext tolerance(int _p) throws RecognitionException {
		ParserRuleContext _parentctx = _ctx;
		int _parentState = getState();
		ToleranceContext _localctx = new ToleranceContext(_ctx, _parentState);
		ToleranceContext _prevctx = _localctx;
		int _startState = 270;
		enterRecursionRule(_localctx, 270, RULE_tolerance, _p);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			{
			setState(1557);
			factor();
			}
			_ctx.stop = _input.LT(-1);
			setState(1564);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,178,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					if ( _parseListeners!=null ) triggerExitRuleEvent();
					_prevctx = _localctx;
					{
					{
					_localctx = new ToleranceContext(_parentctx, _parentState);
					pushNewRecursionContext(_localctx, _startState, RULE_tolerance);
					setState(1559);
					if (!(precpred(_ctx, 2))) throw new FailedPredicateException(this, "precpred(_ctx, 2)");
					setState(1560);
					_la = _input.LA(1);
					if ( !(((((_la - 42)) & ~0x3f) == 0 && ((1L << (_la - 42)) & 1688849860263937L) != 0)) ) {
					_errHandler.recoverInline(this);
					}
					else {
						if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
						_errHandler.reportMatch(this);
						consume();
					}
					setState(1561);
					factor();
					}
					} 
				}
				setState(1566);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,178,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			unrollRecursionContexts(_parentctx);
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class FactorContext extends ParserRuleContext {
		public TerminalNode PLUS() { return getToken(PythonParser.PLUS, 0); }
		public FactorContext factor() {
			return getRuleContext(FactorContext.class,0);
		}
		public TerminalNode MINUS() { return getToken(PythonParser.MINUS, 0); }
		public TerminalNode TILDE() { return getToken(PythonParser.TILDE, 0); }
		public PowerContext power() {
			return getRuleContext(PowerContext.class,0);
		}
		public FactorContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_factor; }
	}

	public final FactorContext factor() throws RecognitionException {
		FactorContext _localctx = new FactorContext(_ctx, getState());
		enterRule(_localctx, 272, RULE_factor);
		try {
			setState(1574);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case PLUS:
				enterOuterAlt(_localctx, 1);
				{
				setState(1567);
				match(PLUS);
				setState(1568);
				factor();
				}
				break;
			case MINUS:
				enterOuterAlt(_localctx, 2);
				{
				setState(1569);
				match(MINUS);
				setState(1570);
				factor();
				}
				break;
			case TILDE:
				enterOuterAlt(_localctx, 3);
				{
				setState(1571);
				match(TILDE);
				setState(1572);
				factor();
				}
				break;
			case FSTRING_START:
			case FALSE:
			case AWAIT:
			case NONE:
			case TRUE:
			case LPAR:
			case LSQB:
			case LBRACE:
			case ELLIPSIS:
			case NAME:
			case NUMBER:
			case STRING:
				enterOuterAlt(_localctx, 4);
				{
				setState(1573);
				power();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class PowerContext extends ParserRuleContext {
		public Await_primaryContext await_primary() {
			return getRuleContext(Await_primaryContext.class,0);
		}
		public TerminalNode DOUBLESTAR() { return getToken(PythonParser.DOUBLESTAR, 0); }
		public FactorContext factor() {
			return getRuleContext(FactorContext.class,0);
		}
		public PowerContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_power; }
	}

	public final PowerContext power() throws RecognitionException {
		PowerContext _localctx = new PowerContext(_ctx, getState());
		enterRule(_localctx, 274, RULE_power);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1576);
			await_primary();
			setState(1579);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,180,_ctx) ) {
			case 1:
				{
				setState(1577);
				match(DOUBLESTAR);
				setState(1578);
				factor();
				}
				break;
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Await_primaryContext extends ParserRuleContext {
		public TerminalNode AWAIT() { return getToken(PythonParser.AWAIT, 0); }
		public PrimaryContext primary() {
			return getRuleContext(PrimaryContext.class,0);
		}
		public Await_primaryContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_await_primary; }
	}

	public final Await_primaryContext await_primary() throws RecognitionException {
		Await_primaryContext _localctx = new Await_primaryContext(_ctx, getState());
		enterRule(_localctx, 276, RULE_await_primary);
		try {
			setState(1584);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case AWAIT:
				enterOuterAlt(_localctx, 1);
				{
				setState(1581);
				match(AWAIT);
				setState(1582);
				primary(0);
				}
				break;
			case FSTRING_START:
			case FALSE:
			case NONE:
			case TRUE:
			case LPAR:
			case LSQB:
			case LBRACE:
			case ELLIPSIS:
			case NAME:
			case NUMBER:
			case STRING:
				enterOuterAlt(_localctx, 2);
				{
				setState(1583);
				primary(0);
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class PrimaryContext extends ParserRuleContext {
		public AtomContext atom() {
			return getRuleContext(AtomContext.class,0);
		}
		public PrimaryContext primary() {
			return getRuleContext(PrimaryContext.class,0);
		}
		public TerminalNode DOT() { return getToken(PythonParser.DOT, 0); }
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public GenexpContext genexp() {
			return getRuleContext(GenexpContext.class,0);
		}
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public TerminalNode LSQB() { return getToken(PythonParser.LSQB, 0); }
		public SlicesContext slices() {
			return getRuleContext(SlicesContext.class,0);
		}
		public TerminalNode RSQB() { return getToken(PythonParser.RSQB, 0); }
		public ArgumentsContext arguments() {
			return getRuleContext(ArgumentsContext.class,0);
		}
		public PrimaryContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_primary; }
	}

	public final PrimaryContext primary() throws RecognitionException {
		return primary(0);
	}

	private PrimaryContext primary(int _p) throws RecognitionException {
		ParserRuleContext _parentctx = _ctx;
		int _parentState = getState();
		PrimaryContext _localctx = new PrimaryContext(_ctx, _parentState);
		PrimaryContext _prevctx = _localctx;
		int _startState = 278;
		enterRecursionRule(_localctx, 278, RULE_primary, _p);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			{
			setState(1587);
			atom();
			}
			_ctx.stop = _input.LT(-1);
			setState(1606);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,184,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					if ( _parseListeners!=null ) triggerExitRuleEvent();
					_prevctx = _localctx;
					{
					{
					_localctx = new PrimaryContext(_parentctx, _parentState);
					pushNewRecursionContext(_localctx, _startState, RULE_primary);
					setState(1589);
					if (!(precpred(_ctx, 2))) throw new FailedPredicateException(this, "precpred(_ctx, 2)");
					setState(1602);
					_errHandler.sync(this);
					switch ( getInterpreter().adaptivePredict(_input,183,_ctx) ) {
					case 1:
						{
						setState(1590);
						match(DOT);
						setState(1591);
						match(NAME);
						}
						break;
					case 2:
						{
						setState(1592);
						genexp();
						}
						break;
					case 3:
						{
						setState(1593);
						match(LPAR);
						setState(1595);
						_errHandler.sync(this);
						_la = _input.LA(1);
						if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 63111984631056584L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859217L) != 0)) {
							{
							setState(1594);
							arguments();
							}
						}

						setState(1597);
						match(RPAR);
						}
						break;
					case 4:
						{
						setState(1598);
						match(LSQB);
						setState(1599);
						slices();
						setState(1600);
						match(RSQB);
						}
						break;
					}
					}
					} 
				}
				setState(1608);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,184,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			unrollRecursionContexts(_parentctx);
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class SlicesContext extends ParserRuleContext {
		public List<SliceContext> slice() {
			return getRuleContexts(SliceContext.class);
		}
		public SliceContext slice(int i) {
			return getRuleContext(SliceContext.class,i);
		}
		public List<Starred_expressionContext> starred_expression() {
			return getRuleContexts(Starred_expressionContext.class);
		}
		public Starred_expressionContext starred_expression(int i) {
			return getRuleContext(Starred_expressionContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public SlicesContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_slices; }
	}

	public final SlicesContext slices() throws RecognitionException {
		SlicesContext _localctx = new SlicesContext(_ctx, getState());
		enterRule(_localctx, 280, RULE_slices);
		int _la;
		try {
			int _alt;
			setState(1627);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,189,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1609);
				slice();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1612);
				_errHandler.sync(this);
				switch (_input.LA(1)) {
				case FSTRING_START:
				case FALSE:
				case AWAIT:
				case NONE:
				case TRUE:
				case LAMBDA:
				case NOT:
				case LPAR:
				case LSQB:
				case LBRACE:
				case COLON:
				case PLUS:
				case MINUS:
				case TILDE:
				case ELLIPSIS:
				case NAME:
				case NUMBER:
				case STRING:
					{
					setState(1610);
					slice();
					}
					break;
				case STAR:
					{
					setState(1611);
					starred_expression();
					}
					break;
				default:
					throw new NoViableAltException(this);
				}
				setState(1621);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,187,_ctx);
				while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
					if ( _alt==1 ) {
						{
						{
						setState(1614);
						match(COMMA);
						setState(1617);
						_errHandler.sync(this);
						switch (_input.LA(1)) {
						case FSTRING_START:
						case FALSE:
						case AWAIT:
						case NONE:
						case TRUE:
						case LAMBDA:
						case NOT:
						case LPAR:
						case LSQB:
						case LBRACE:
						case COLON:
						case PLUS:
						case MINUS:
						case TILDE:
						case ELLIPSIS:
						case NAME:
						case NUMBER:
						case STRING:
							{
							setState(1615);
							slice();
							}
							break;
						case STAR:
							{
							setState(1616);
							starred_expression();
							}
							break;
						default:
							throw new NoViableAltException(this);
						}
						}
						} 
					}
					setState(1623);
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,187,_ctx);
				}
				setState(1625);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==COMMA) {
					{
					setState(1624);
					match(COMMA);
					}
				}

				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class SliceContext extends ParserRuleContext {
		public List<TerminalNode> COLON() { return getTokens(PythonParser.COLON); }
		public TerminalNode COLON(int i) {
			return getToken(PythonParser.COLON, i);
		}
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public Named_expressionContext named_expression() {
			return getRuleContext(Named_expressionContext.class,0);
		}
		public SliceContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_slice; }
	}

	public final SliceContext slice() throws RecognitionException {
		SliceContext _localctx = new SliceContext(_ctx, getState());
		enterRule(_localctx, 282, RULE_slice);
		int _la;
		try {
			setState(1643);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,194,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1630);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 27083187612092616L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859201L) != 0)) {
					{
					setState(1629);
					expression();
					}
				}

				setState(1632);
				match(COLON);
				setState(1634);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 27083187612092616L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859201L) != 0)) {
					{
					setState(1633);
					expression();
					}
				}

				setState(1640);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==COLON) {
					{
					setState(1636);
					match(COLON);
					setState(1638);
					_errHandler.sync(this);
					_la = _input.LA(1);
					if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 27083187612092616L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859201L) != 0)) {
						{
						setState(1637);
						expression();
						}
					}

					}
				}

				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1642);
				named_expression();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class AtomContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode TRUE() { return getToken(PythonParser.TRUE, 0); }
		public TerminalNode FALSE() { return getToken(PythonParser.FALSE, 0); }
		public TerminalNode NONE() { return getToken(PythonParser.NONE, 0); }
		public StringsContext strings() {
			return getRuleContext(StringsContext.class,0);
		}
		public Dimensioned_numberContext dimensioned_number() {
			return getRuleContext(Dimensioned_numberContext.class,0);
		}
		public TerminalNode NUMBER() { return getToken(PythonParser.NUMBER, 0); }
		public TupleContext tuple() {
			return getRuleContext(TupleContext.class,0);
		}
		public GroupContext group() {
			return getRuleContext(GroupContext.class,0);
		}
		public GenexpContext genexp() {
			return getRuleContext(GenexpContext.class,0);
		}
		public ListContext list() {
			return getRuleContext(ListContext.class,0);
		}
		public ListcompContext listcomp() {
			return getRuleContext(ListcompContext.class,0);
		}
		public DictContext dict() {
			return getRuleContext(DictContext.class,0);
		}
		public SetContext set() {
			return getRuleContext(SetContext.class,0);
		}
		public DictcompContext dictcomp() {
			return getRuleContext(DictcompContext.class,0);
		}
		public SetcompContext setcomp() {
			return getRuleContext(SetcompContext.class,0);
		}
		public TerminalNode ELLIPSIS() { return getToken(PythonParser.ELLIPSIS, 0); }
		public AtomContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_atom; }
	}

	public final AtomContext atom() throws RecognitionException {
		AtomContext _localctx = new AtomContext(_ctx, getState());
		enterRule(_localctx, 284, RULE_atom);
		try {
			setState(1668);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,198,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1645);
				match(NAME);
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1646);
				match(TRUE);
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(1647);
				match(FALSE);
				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(1648);
				match(NONE);
				}
				break;
			case 5:
				enterOuterAlt(_localctx, 5);
				{
				setState(1649);
				strings();
				}
				break;
			case 6:
				enterOuterAlt(_localctx, 6);
				{
				setState(1650);
				dimensioned_number();
				}
				break;
			case 7:
				enterOuterAlt(_localctx, 7);
				{
				setState(1651);
				match(NUMBER);
				}
				break;
			case 8:
				enterOuterAlt(_localctx, 8);
				{
				setState(1655);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,195,_ctx) ) {
				case 1:
					{
					setState(1652);
					tuple();
					}
					break;
				case 2:
					{
					setState(1653);
					group();
					}
					break;
				case 3:
					{
					setState(1654);
					genexp();
					}
					break;
				}
				}
				break;
			case 9:
				enterOuterAlt(_localctx, 9);
				{
				setState(1659);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,196,_ctx) ) {
				case 1:
					{
					setState(1657);
					list();
					}
					break;
				case 2:
					{
					setState(1658);
					listcomp();
					}
					break;
				}
				}
				break;
			case 10:
				enterOuterAlt(_localctx, 10);
				{
				setState(1665);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,197,_ctx) ) {
				case 1:
					{
					setState(1661);
					dict();
					}
					break;
				case 2:
					{
					setState(1662);
					set();
					}
					break;
				case 3:
					{
					setState(1663);
					dictcomp();
					}
					break;
				case 4:
					{
					setState(1664);
					setcomp();
					}
					break;
				}
				}
				break;
			case 11:
				enterOuterAlt(_localctx, 11);
				{
				setState(1667);
				match(ELLIPSIS);
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Dimensioned_numberContext extends ParserRuleContext {
		public TerminalNode NUMBER() { return getToken(PythonParser.NUMBER, 0); }
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode STRING() { return getToken(PythonParser.STRING, 0); }
		public Dimensioned_numberContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_dimensioned_number; }
	}

	public final Dimensioned_numberContext dimensioned_number() throws RecognitionException {
		Dimensioned_numberContext _localctx = new Dimensioned_numberContext(_ctx, getState());
		enterRule(_localctx, 286, RULE_dimensioned_number);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1670);
			match(NUMBER);
			setState(1671);
			_la = _input.LA(1);
			if ( !(_la==NAME || _la==STRING) ) {
			_errHandler.recoverInline(this);
			}
			else {
				if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
				_errHandler.reportMatch(this);
				consume();
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class GroupContext extends ParserRuleContext {
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public Yield_exprContext yield_expr() {
			return getRuleContext(Yield_exprContext.class,0);
		}
		public Named_expressionContext named_expression() {
			return getRuleContext(Named_expressionContext.class,0);
		}
		public GroupContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_group; }
	}

	public final GroupContext group() throws RecognitionException {
		GroupContext _localctx = new GroupContext(_ctx, getState());
		enterRule(_localctx, 288, RULE_group);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1673);
			match(LPAR);
			setState(1676);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case YIELD:
				{
				setState(1674);
				yield_expr();
				}
				break;
			case FSTRING_START:
			case FALSE:
			case AWAIT:
			case NONE:
			case TRUE:
			case LAMBDA:
			case NOT:
			case LPAR:
			case LSQB:
			case LBRACE:
			case PLUS:
			case MINUS:
			case TILDE:
			case ELLIPSIS:
			case NAME:
			case NUMBER:
			case STRING:
				{
				setState(1675);
				named_expression();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
			setState(1678);
			match(RPAR);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class LambdefContext extends ParserRuleContext {
		public TerminalNode LAMBDA() { return getToken(PythonParser.LAMBDA, 0); }
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public Lambda_paramsContext lambda_params() {
			return getRuleContext(Lambda_paramsContext.class,0);
		}
		public LambdefContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_lambdef; }
	}

	public final LambdefContext lambdef() throws RecognitionException {
		LambdefContext _localctx = new LambdefContext(_ctx, getState());
		enterRule(_localctx, 290, RULE_lambdef);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1680);
			match(LAMBDA);
			setState(1682);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (((((_la - 55)) & ~0x3f) == 0 && ((1L << (_la - 55)) & 274877972481L) != 0)) {
				{
				setState(1681);
				lambda_params();
				}
			}

			setState(1684);
			match(COLON);
			setState(1685);
			expression();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Lambda_paramsContext extends ParserRuleContext {
		public Lambda_parametersContext lambda_parameters() {
			return getRuleContext(Lambda_parametersContext.class,0);
		}
		public Lambda_paramsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_lambda_params; }
	}

	public final Lambda_paramsContext lambda_params() throws RecognitionException {
		Lambda_paramsContext _localctx = new Lambda_paramsContext(_ctx, getState());
		enterRule(_localctx, 292, RULE_lambda_params);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1687);
			lambda_parameters();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Lambda_parametersContext extends ParserRuleContext {
		public Lambda_slash_no_defaultContext lambda_slash_no_default() {
			return getRuleContext(Lambda_slash_no_defaultContext.class,0);
		}
		public List<Lambda_param_no_defaultContext> lambda_param_no_default() {
			return getRuleContexts(Lambda_param_no_defaultContext.class);
		}
		public Lambda_param_no_defaultContext lambda_param_no_default(int i) {
			return getRuleContext(Lambda_param_no_defaultContext.class,i);
		}
		public List<Lambda_param_with_defaultContext> lambda_param_with_default() {
			return getRuleContexts(Lambda_param_with_defaultContext.class);
		}
		public Lambda_param_with_defaultContext lambda_param_with_default(int i) {
			return getRuleContext(Lambda_param_with_defaultContext.class,i);
		}
		public Lambda_star_etcContext lambda_star_etc() {
			return getRuleContext(Lambda_star_etcContext.class,0);
		}
		public Lambda_slash_with_defaultContext lambda_slash_with_default() {
			return getRuleContext(Lambda_slash_with_defaultContext.class,0);
		}
		public Lambda_parametersContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_lambda_parameters; }
	}

	public final Lambda_parametersContext lambda_parameters() throws RecognitionException {
		Lambda_parametersContext _localctx = new Lambda_parametersContext(_ctx, getState());
		enterRule(_localctx, 294, RULE_lambda_parameters);
		int _la;
		try {
			int _alt;
			setState(1738);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,211,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1689);
				lambda_slash_no_default();
				setState(1693);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,201,_ctx);
				while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
					if ( _alt==1 ) {
						{
						{
						setState(1690);
						lambda_param_no_default();
						}
						} 
					}
					setState(1695);
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,201,_ctx);
				}
				setState(1699);
				_errHandler.sync(this);
				_la = _input.LA(1);
				while (_la==NAME) {
					{
					{
					setState(1696);
					lambda_param_with_default();
					}
					}
					setState(1701);
					_errHandler.sync(this);
					_la = _input.LA(1);
				}
				setState(1703);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==STAR || _la==DOUBLESTAR) {
					{
					setState(1702);
					lambda_star_etc();
					}
				}

				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1705);
				lambda_slash_with_default();
				setState(1709);
				_errHandler.sync(this);
				_la = _input.LA(1);
				while (_la==NAME) {
					{
					{
					setState(1706);
					lambda_param_with_default();
					}
					}
					setState(1711);
					_errHandler.sync(this);
					_la = _input.LA(1);
				}
				setState(1713);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==STAR || _la==DOUBLESTAR) {
					{
					setState(1712);
					lambda_star_etc();
					}
				}

				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(1716); 
				_errHandler.sync(this);
				_alt = 1;
				do {
					switch (_alt) {
					case 1:
						{
						{
						setState(1715);
						lambda_param_no_default();
						}
						}
						break;
					default:
						throw new NoViableAltException(this);
					}
					setState(1718); 
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,206,_ctx);
				} while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER );
				setState(1723);
				_errHandler.sync(this);
				_la = _input.LA(1);
				while (_la==NAME) {
					{
					{
					setState(1720);
					lambda_param_with_default();
					}
					}
					setState(1725);
					_errHandler.sync(this);
					_la = _input.LA(1);
				}
				setState(1727);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==STAR || _la==DOUBLESTAR) {
					{
					setState(1726);
					lambda_star_etc();
					}
				}

				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(1730); 
				_errHandler.sync(this);
				_la = _input.LA(1);
				do {
					{
					{
					setState(1729);
					lambda_param_with_default();
					}
					}
					setState(1732); 
					_errHandler.sync(this);
					_la = _input.LA(1);
				} while ( _la==NAME );
				setState(1735);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==STAR || _la==DOUBLESTAR) {
					{
					setState(1734);
					lambda_star_etc();
					}
				}

				}
				break;
			case 5:
				enterOuterAlt(_localctx, 5);
				{
				setState(1737);
				lambda_star_etc();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Lambda_slash_no_defaultContext extends ParserRuleContext {
		public TerminalNode SLASH() { return getToken(PythonParser.SLASH, 0); }
		public List<Lambda_param_no_defaultContext> lambda_param_no_default() {
			return getRuleContexts(Lambda_param_no_defaultContext.class);
		}
		public Lambda_param_no_defaultContext lambda_param_no_default(int i) {
			return getRuleContext(Lambda_param_no_defaultContext.class,i);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public Lambda_slash_no_defaultContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_lambda_slash_no_default; }
	}

	public final Lambda_slash_no_defaultContext lambda_slash_no_default() throws RecognitionException {
		Lambda_slash_no_defaultContext _localctx = new Lambda_slash_no_defaultContext(_ctx, getState());
		enterRule(_localctx, 296, RULE_lambda_slash_no_default);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1741); 
			_errHandler.sync(this);
			_la = _input.LA(1);
			do {
				{
				{
				setState(1740);
				lambda_param_no_default();
				}
				}
				setState(1743); 
				_errHandler.sync(this);
				_la = _input.LA(1);
			} while ( _la==NAME );
			setState(1745);
			match(SLASH);
			setState(1747);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(1746);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Lambda_slash_with_defaultContext extends ParserRuleContext {
		public TerminalNode SLASH() { return getToken(PythonParser.SLASH, 0); }
		public List<Lambda_param_no_defaultContext> lambda_param_no_default() {
			return getRuleContexts(Lambda_param_no_defaultContext.class);
		}
		public Lambda_param_no_defaultContext lambda_param_no_default(int i) {
			return getRuleContext(Lambda_param_no_defaultContext.class,i);
		}
		public List<Lambda_param_with_defaultContext> lambda_param_with_default() {
			return getRuleContexts(Lambda_param_with_defaultContext.class);
		}
		public Lambda_param_with_defaultContext lambda_param_with_default(int i) {
			return getRuleContext(Lambda_param_with_defaultContext.class,i);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public Lambda_slash_with_defaultContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_lambda_slash_with_default; }
	}

	public final Lambda_slash_with_defaultContext lambda_slash_with_default() throws RecognitionException {
		Lambda_slash_with_defaultContext _localctx = new Lambda_slash_with_defaultContext(_ctx, getState());
		enterRule(_localctx, 298, RULE_lambda_slash_with_default);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(1752);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,214,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(1749);
					lambda_param_no_default();
					}
					} 
				}
				setState(1754);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,214,_ctx);
			}
			setState(1756); 
			_errHandler.sync(this);
			_la = _input.LA(1);
			do {
				{
				{
				setState(1755);
				lambda_param_with_default();
				}
				}
				setState(1758); 
				_errHandler.sync(this);
				_la = _input.LA(1);
			} while ( _la==NAME );
			setState(1760);
			match(SLASH);
			setState(1762);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(1761);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Lambda_star_etcContext extends ParserRuleContext {
		public TerminalNode STAR() { return getToken(PythonParser.STAR, 0); }
		public Lambda_param_no_defaultContext lambda_param_no_default() {
			return getRuleContext(Lambda_param_no_defaultContext.class,0);
		}
		public List<Lambda_param_maybe_defaultContext> lambda_param_maybe_default() {
			return getRuleContexts(Lambda_param_maybe_defaultContext.class);
		}
		public Lambda_param_maybe_defaultContext lambda_param_maybe_default(int i) {
			return getRuleContext(Lambda_param_maybe_defaultContext.class,i);
		}
		public Lambda_kwdsContext lambda_kwds() {
			return getRuleContext(Lambda_kwdsContext.class,0);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public Lambda_star_etcContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_lambda_star_etc; }
	}

	public final Lambda_star_etcContext lambda_star_etc() throws RecognitionException {
		Lambda_star_etcContext _localctx = new Lambda_star_etcContext(_ctx, getState());
		enterRule(_localctx, 300, RULE_lambda_star_etc);
		int _la;
		try {
			setState(1786);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,221,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1764);
				match(STAR);
				setState(1765);
				lambda_param_no_default();
				setState(1769);
				_errHandler.sync(this);
				_la = _input.LA(1);
				while (_la==NAME) {
					{
					{
					setState(1766);
					lambda_param_maybe_default();
					}
					}
					setState(1771);
					_errHandler.sync(this);
					_la = _input.LA(1);
				}
				setState(1773);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==DOUBLESTAR) {
					{
					setState(1772);
					lambda_kwds();
					}
				}

				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1775);
				match(STAR);
				setState(1776);
				match(COMMA);
				setState(1778); 
				_errHandler.sync(this);
				_la = _input.LA(1);
				do {
					{
					{
					setState(1777);
					lambda_param_maybe_default();
					}
					}
					setState(1780); 
					_errHandler.sync(this);
					_la = _input.LA(1);
				} while ( _la==NAME );
				setState(1783);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==DOUBLESTAR) {
					{
					setState(1782);
					lambda_kwds();
					}
				}

				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(1785);
				lambda_kwds();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Lambda_kwdsContext extends ParserRuleContext {
		public TerminalNode DOUBLESTAR() { return getToken(PythonParser.DOUBLESTAR, 0); }
		public Lambda_param_no_defaultContext lambda_param_no_default() {
			return getRuleContext(Lambda_param_no_defaultContext.class,0);
		}
		public Lambda_kwdsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_lambda_kwds; }
	}

	public final Lambda_kwdsContext lambda_kwds() throws RecognitionException {
		Lambda_kwdsContext _localctx = new Lambda_kwdsContext(_ctx, getState());
		enterRule(_localctx, 302, RULE_lambda_kwds);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1788);
			match(DOUBLESTAR);
			setState(1789);
			lambda_param_no_default();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Lambda_param_no_defaultContext extends ParserRuleContext {
		public Lambda_paramContext lambda_param() {
			return getRuleContext(Lambda_paramContext.class,0);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public Lambda_param_no_defaultContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_lambda_param_no_default; }
	}

	public final Lambda_param_no_defaultContext lambda_param_no_default() throws RecognitionException {
		Lambda_param_no_defaultContext _localctx = new Lambda_param_no_defaultContext(_ctx, getState());
		enterRule(_localctx, 304, RULE_lambda_param_no_default);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1791);
			lambda_param();
			setState(1793);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(1792);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Lambda_param_with_defaultContext extends ParserRuleContext {
		public Lambda_paramContext lambda_param() {
			return getRuleContext(Lambda_paramContext.class,0);
		}
		public Default_assignmentContext default_assignment() {
			return getRuleContext(Default_assignmentContext.class,0);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public Lambda_param_with_defaultContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_lambda_param_with_default; }
	}

	public final Lambda_param_with_defaultContext lambda_param_with_default() throws RecognitionException {
		Lambda_param_with_defaultContext _localctx = new Lambda_param_with_defaultContext(_ctx, getState());
		enterRule(_localctx, 306, RULE_lambda_param_with_default);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1795);
			lambda_param();
			setState(1796);
			default_assignment();
			setState(1798);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(1797);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Lambda_param_maybe_defaultContext extends ParserRuleContext {
		public Lambda_paramContext lambda_param() {
			return getRuleContext(Lambda_paramContext.class,0);
		}
		public Default_assignmentContext default_assignment() {
			return getRuleContext(Default_assignmentContext.class,0);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public Lambda_param_maybe_defaultContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_lambda_param_maybe_default; }
	}

	public final Lambda_param_maybe_defaultContext lambda_param_maybe_default() throws RecognitionException {
		Lambda_param_maybe_defaultContext _localctx = new Lambda_param_maybe_defaultContext(_ctx, getState());
		enterRule(_localctx, 308, RULE_lambda_param_maybe_default);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1800);
			lambda_param();
			setState(1802);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==EQUAL) {
				{
				setState(1801);
				default_assignment();
				}
			}

			setState(1805);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(1804);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Lambda_paramContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public Lambda_paramContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_lambda_param; }
	}

	public final Lambda_paramContext lambda_param() throws RecognitionException {
		Lambda_paramContext _localctx = new Lambda_paramContext(_ctx, getState());
		enterRule(_localctx, 310, RULE_lambda_param);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1807);
			match(NAME);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Fstring_middleContext extends ParserRuleContext {
		public Fstring_replacement_fieldContext fstring_replacement_field() {
			return getRuleContext(Fstring_replacement_fieldContext.class,0);
		}
		public TerminalNode FSTRING_MIDDLE() { return getToken(PythonParser.FSTRING_MIDDLE, 0); }
		public Fstring_middleContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_fstring_middle; }
	}

	public final Fstring_middleContext fstring_middle() throws RecognitionException {
		Fstring_middleContext _localctx = new Fstring_middleContext(_ctx, getState());
		enterRule(_localctx, 312, RULE_fstring_middle);
		try {
			setState(1811);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case LBRACE:
				enterOuterAlt(_localctx, 1);
				{
				setState(1809);
				fstring_replacement_field();
				}
				break;
			case FSTRING_MIDDLE:
				enterOuterAlt(_localctx, 2);
				{
				setState(1810);
				match(FSTRING_MIDDLE);
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Fstring_replacement_fieldContext extends ParserRuleContext {
		public TerminalNode LBRACE() { return getToken(PythonParser.LBRACE, 0); }
		public TerminalNode RBRACE() { return getToken(PythonParser.RBRACE, 0); }
		public Yield_exprContext yield_expr() {
			return getRuleContext(Yield_exprContext.class,0);
		}
		public Star_expressionsContext star_expressions() {
			return getRuleContext(Star_expressionsContext.class,0);
		}
		public TerminalNode EQUAL() { return getToken(PythonParser.EQUAL, 0); }
		public Fstring_conversionContext fstring_conversion() {
			return getRuleContext(Fstring_conversionContext.class,0);
		}
		public Fstring_full_format_specContext fstring_full_format_spec() {
			return getRuleContext(Fstring_full_format_specContext.class,0);
		}
		public Fstring_replacement_fieldContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_fstring_replacement_field; }
	}

	public final Fstring_replacement_fieldContext fstring_replacement_field() throws RecognitionException {
		Fstring_replacement_fieldContext _localctx = new Fstring_replacement_fieldContext(_ctx, getState());
		enterRule(_localctx, 314, RULE_fstring_replacement_field);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1813);
			match(LBRACE);
			setState(1816);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case YIELD:
				{
				setState(1814);
				yield_expr();
				}
				break;
			case FSTRING_START:
			case FALSE:
			case AWAIT:
			case NONE:
			case TRUE:
			case LAMBDA:
			case NOT:
			case LPAR:
			case LSQB:
			case LBRACE:
			case PLUS:
			case MINUS:
			case STAR:
			case TILDE:
			case ELLIPSIS:
			case NAME:
			case NUMBER:
			case STRING:
				{
				setState(1815);
				star_expressions();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
			setState(1819);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==EQUAL) {
				{
				setState(1818);
				match(EQUAL);
				}
			}

			setState(1822);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==EXCLAMATION) {
				{
				setState(1821);
				fstring_conversion();
				}
			}

			setState(1825);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COLON) {
				{
				setState(1824);
				fstring_full_format_spec();
				}
			}

			setState(1827);
			match(RBRACE);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Fstring_conversionContext extends ParserRuleContext {
		public TerminalNode EXCLAMATION() { return getToken(PythonParser.EXCLAMATION, 0); }
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public Fstring_conversionContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_fstring_conversion; }
	}

	public final Fstring_conversionContext fstring_conversion() throws RecognitionException {
		Fstring_conversionContext _localctx = new Fstring_conversionContext(_ctx, getState());
		enterRule(_localctx, 316, RULE_fstring_conversion);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1829);
			match(EXCLAMATION);
			setState(1830);
			match(NAME);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Fstring_full_format_specContext extends ParserRuleContext {
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public List<Fstring_format_specContext> fstring_format_spec() {
			return getRuleContexts(Fstring_format_specContext.class);
		}
		public Fstring_format_specContext fstring_format_spec(int i) {
			return getRuleContext(Fstring_format_specContext.class,i);
		}
		public Fstring_full_format_specContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_fstring_full_format_spec; }
	}

	public final Fstring_full_format_specContext fstring_full_format_spec() throws RecognitionException {
		Fstring_full_format_specContext _localctx = new Fstring_full_format_specContext(_ctx, getState());
		enterRule(_localctx, 318, RULE_fstring_full_format_spec);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1832);
			match(COLON);
			setState(1836);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==FSTRING_MIDDLE || _la==LBRACE) {
				{
				{
				setState(1833);
				fstring_format_spec();
				}
				}
				setState(1838);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Fstring_format_specContext extends ParserRuleContext {
		public TerminalNode FSTRING_MIDDLE() { return getToken(PythonParser.FSTRING_MIDDLE, 0); }
		public Fstring_replacement_fieldContext fstring_replacement_field() {
			return getRuleContext(Fstring_replacement_fieldContext.class,0);
		}
		public Fstring_format_specContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_fstring_format_spec; }
	}

	public final Fstring_format_specContext fstring_format_spec() throws RecognitionException {
		Fstring_format_specContext _localctx = new Fstring_format_specContext(_ctx, getState());
		enterRule(_localctx, 320, RULE_fstring_format_spec);
		try {
			setState(1841);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case FSTRING_MIDDLE:
				enterOuterAlt(_localctx, 1);
				{
				setState(1839);
				match(FSTRING_MIDDLE);
				}
				break;
			case LBRACE:
				enterOuterAlt(_localctx, 2);
				{
				setState(1840);
				fstring_replacement_field();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class FstringContext extends ParserRuleContext {
		public TerminalNode FSTRING_START() { return getToken(PythonParser.FSTRING_START, 0); }
		public TerminalNode FSTRING_END() { return getToken(PythonParser.FSTRING_END, 0); }
		public List<Fstring_middleContext> fstring_middle() {
			return getRuleContexts(Fstring_middleContext.class);
		}
		public Fstring_middleContext fstring_middle(int i) {
			return getRuleContext(Fstring_middleContext.class,i);
		}
		public FstringContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_fstring; }
	}

	public final FstringContext fstring() throws RecognitionException {
		FstringContext _localctx = new FstringContext(_ctx, getState());
		enterRule(_localctx, 322, RULE_fstring);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1843);
			match(FSTRING_START);
			setState(1847);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==FSTRING_MIDDLE || _la==LBRACE) {
				{
				{
				setState(1844);
				fstring_middle();
				}
				}
				setState(1849);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			setState(1850);
			match(FSTRING_END);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class StringContext extends ParserRuleContext {
		public TerminalNode STRING() { return getToken(PythonParser.STRING, 0); }
		public StringContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_string; }
	}

	public final StringContext string() throws RecognitionException {
		StringContext _localctx = new StringContext(_ctx, getState());
		enterRule(_localctx, 324, RULE_string);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1852);
			match(STRING);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class StringsContext extends ParserRuleContext {
		public List<FstringContext> fstring() {
			return getRuleContexts(FstringContext.class);
		}
		public FstringContext fstring(int i) {
			return getRuleContext(FstringContext.class,i);
		}
		public List<StringContext> string() {
			return getRuleContexts(StringContext.class);
		}
		public StringContext string(int i) {
			return getRuleContext(StringContext.class,i);
		}
		public StringsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_strings; }
	}

	public final StringsContext strings() throws RecognitionException {
		StringsContext _localctx = new StringsContext(_ctx, getState());
		enterRule(_localctx, 326, RULE_strings);
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(1856); 
			_errHandler.sync(this);
			_alt = 1;
			do {
				switch (_alt) {
				case 1:
					{
					setState(1856);
					_errHandler.sync(this);
					switch (_input.LA(1)) {
					case FSTRING_START:
						{
						setState(1854);
						fstring();
						}
						break;
					case STRING:
						{
						setState(1855);
						string();
						}
						break;
					default:
						throw new NoViableAltException(this);
					}
					}
					break;
				default:
					throw new NoViableAltException(this);
				}
				setState(1858); 
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,235,_ctx);
			} while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER );
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ListContext extends ParserRuleContext {
		public TerminalNode LSQB() { return getToken(PythonParser.LSQB, 0); }
		public TerminalNode RSQB() { return getToken(PythonParser.RSQB, 0); }
		public Star_named_expressionsContext star_named_expressions() {
			return getRuleContext(Star_named_expressionsContext.class,0);
		}
		public ListContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_list; }
	}

	public final ListContext list() throws RecognitionException {
		ListContext _localctx = new ListContext(_ctx, getState());
		enterRule(_localctx, 328, RULE_list);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1860);
			match(LSQB);
			setState(1862);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 63111984631056584L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859201L) != 0)) {
				{
				setState(1861);
				star_named_expressions();
				}
			}

			setState(1864);
			match(RSQB);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class TupleContext extends ParserRuleContext {
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public Star_named_expressionContext star_named_expression() {
			return getRuleContext(Star_named_expressionContext.class,0);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public Star_named_expressionsContext star_named_expressions() {
			return getRuleContext(Star_named_expressionsContext.class,0);
		}
		public TupleContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_tuple; }
	}

	public final TupleContext tuple() throws RecognitionException {
		TupleContext _localctx = new TupleContext(_ctx, getState());
		enterRule(_localctx, 330, RULE_tuple);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1866);
			match(LPAR);
			setState(1872);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 63111984631056584L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859201L) != 0)) {
				{
				setState(1867);
				star_named_expression();
				setState(1868);
				match(COMMA);
				setState(1870);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 63111984631056584L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859201L) != 0)) {
					{
					setState(1869);
					star_named_expressions();
					}
				}

				}
			}

			setState(1874);
			match(RPAR);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class SetContext extends ParserRuleContext {
		public TerminalNode LBRACE() { return getToken(PythonParser.LBRACE, 0); }
		public Star_named_expressionsContext star_named_expressions() {
			return getRuleContext(Star_named_expressionsContext.class,0);
		}
		public TerminalNode RBRACE() { return getToken(PythonParser.RBRACE, 0); }
		public SetContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_set; }
	}

	public final SetContext set() throws RecognitionException {
		SetContext _localctx = new SetContext(_ctx, getState());
		enterRule(_localctx, 332, RULE_set);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1876);
			match(LBRACE);
			setState(1877);
			star_named_expressions();
			setState(1878);
			match(RBRACE);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class DictContext extends ParserRuleContext {
		public TerminalNode LBRACE() { return getToken(PythonParser.LBRACE, 0); }
		public TerminalNode RBRACE() { return getToken(PythonParser.RBRACE, 0); }
		public Double_starred_kvpairsContext double_starred_kvpairs() {
			return getRuleContext(Double_starred_kvpairsContext.class,0);
		}
		public DictContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_dict; }
	}

	public final DictContext dict() throws RecognitionException {
		DictContext _localctx = new DictContext(_ctx, getState());
		enterRule(_localctx, 334, RULE_dict);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1880);
			match(LBRACE);
			setState(1882);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 27083187612092616L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859217L) != 0)) {
				{
				setState(1881);
				double_starred_kvpairs();
				}
			}

			setState(1884);
			match(RBRACE);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Double_starred_kvpairsContext extends ParserRuleContext {
		public List<Double_starred_kvpairContext> double_starred_kvpair() {
			return getRuleContexts(Double_starred_kvpairContext.class);
		}
		public Double_starred_kvpairContext double_starred_kvpair(int i) {
			return getRuleContext(Double_starred_kvpairContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Double_starred_kvpairsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_double_starred_kvpairs; }
	}

	public final Double_starred_kvpairsContext double_starred_kvpairs() throws RecognitionException {
		Double_starred_kvpairsContext _localctx = new Double_starred_kvpairsContext(_ctx, getState());
		enterRule(_localctx, 336, RULE_double_starred_kvpairs);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(1886);
			double_starred_kvpair();
			setState(1891);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,240,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(1887);
					match(COMMA);
					setState(1888);
					double_starred_kvpair();
					}
					} 
				}
				setState(1893);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,240,_ctx);
			}
			setState(1895);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(1894);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Double_starred_kvpairContext extends ParserRuleContext {
		public TerminalNode DOUBLESTAR() { return getToken(PythonParser.DOUBLESTAR, 0); }
		public Bitwise_orContext bitwise_or() {
			return getRuleContext(Bitwise_orContext.class,0);
		}
		public KvpairContext kvpair() {
			return getRuleContext(KvpairContext.class,0);
		}
		public Double_starred_kvpairContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_double_starred_kvpair; }
	}

	public final Double_starred_kvpairContext double_starred_kvpair() throws RecognitionException {
		Double_starred_kvpairContext _localctx = new Double_starred_kvpairContext(_ctx, getState());
		enterRule(_localctx, 338, RULE_double_starred_kvpair);
		try {
			setState(1900);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case DOUBLESTAR:
				enterOuterAlt(_localctx, 1);
				{
				setState(1897);
				match(DOUBLESTAR);
				setState(1898);
				bitwise_or(0);
				}
				break;
			case FSTRING_START:
			case FALSE:
			case AWAIT:
			case NONE:
			case TRUE:
			case LAMBDA:
			case NOT:
			case LPAR:
			case LSQB:
			case LBRACE:
			case PLUS:
			case MINUS:
			case TILDE:
			case ELLIPSIS:
			case NAME:
			case NUMBER:
			case STRING:
				enterOuterAlt(_localctx, 2);
				{
				setState(1899);
				kvpair();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class KvpairContext extends ParserRuleContext {
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public TerminalNode COLON() { return getToken(PythonParser.COLON, 0); }
		public KvpairContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_kvpair; }
	}

	public final KvpairContext kvpair() throws RecognitionException {
		KvpairContext _localctx = new KvpairContext(_ctx, getState());
		enterRule(_localctx, 340, RULE_kvpair);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1902);
			expression();
			setState(1903);
			match(COLON);
			setState(1904);
			expression();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class For_if_clausesContext extends ParserRuleContext {
		public List<For_if_clauseContext> for_if_clause() {
			return getRuleContexts(For_if_clauseContext.class);
		}
		public For_if_clauseContext for_if_clause(int i) {
			return getRuleContext(For_if_clauseContext.class,i);
		}
		public For_if_clausesContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_for_if_clauses; }
	}

	public final For_if_clausesContext for_if_clauses() throws RecognitionException {
		For_if_clausesContext _localctx = new For_if_clausesContext(_ctx, getState());
		enterRule(_localctx, 342, RULE_for_if_clauses);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1907); 
			_errHandler.sync(this);
			_la = _input.LA(1);
			do {
				{
				{
				setState(1906);
				for_if_clause();
				}
				}
				setState(1909); 
				_errHandler.sync(this);
				_la = _input.LA(1);
			} while ( _la==FOR || _la==ASYNC );
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class For_if_clauseContext extends ParserRuleContext {
		public TerminalNode FOR() { return getToken(PythonParser.FOR, 0); }
		public Star_targetsContext star_targets() {
			return getRuleContext(Star_targetsContext.class,0);
		}
		public TerminalNode IN() { return getToken(PythonParser.IN, 0); }
		public List<DisjunctionContext> disjunction() {
			return getRuleContexts(DisjunctionContext.class);
		}
		public DisjunctionContext disjunction(int i) {
			return getRuleContext(DisjunctionContext.class,i);
		}
		public TerminalNode ASYNC() { return getToken(PythonParser.ASYNC, 0); }
		public List<TerminalNode> IF() { return getTokens(PythonParser.IF); }
		public TerminalNode IF(int i) {
			return getToken(PythonParser.IF, i);
		}
		public For_if_clauseContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_for_if_clause; }
	}

	public final For_if_clauseContext for_if_clause() throws RecognitionException {
		For_if_clauseContext _localctx = new For_if_clauseContext(_ctx, getState());
		enterRule(_localctx, 344, RULE_for_if_clause);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1912);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==ASYNC) {
				{
				setState(1911);
				match(ASYNC);
				}
			}

			setState(1914);
			match(FOR);
			setState(1915);
			star_targets();
			setState(1916);
			match(IN);
			setState(1917);
			disjunction();
			setState(1922);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==IF) {
				{
				{
				setState(1918);
				match(IF);
				setState(1919);
				disjunction();
				}
				}
				setState(1924);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ListcompContext extends ParserRuleContext {
		public TerminalNode LSQB() { return getToken(PythonParser.LSQB, 0); }
		public Named_expressionContext named_expression() {
			return getRuleContext(Named_expressionContext.class,0);
		}
		public For_if_clausesContext for_if_clauses() {
			return getRuleContext(For_if_clausesContext.class,0);
		}
		public TerminalNode RSQB() { return getToken(PythonParser.RSQB, 0); }
		public ListcompContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_listcomp; }
	}

	public final ListcompContext listcomp() throws RecognitionException {
		ListcompContext _localctx = new ListcompContext(_ctx, getState());
		enterRule(_localctx, 346, RULE_listcomp);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1925);
			match(LSQB);
			setState(1926);
			named_expression();
			setState(1927);
			for_if_clauses();
			setState(1928);
			match(RSQB);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class SetcompContext extends ParserRuleContext {
		public TerminalNode LBRACE() { return getToken(PythonParser.LBRACE, 0); }
		public Named_expressionContext named_expression() {
			return getRuleContext(Named_expressionContext.class,0);
		}
		public For_if_clausesContext for_if_clauses() {
			return getRuleContext(For_if_clausesContext.class,0);
		}
		public TerminalNode RBRACE() { return getToken(PythonParser.RBRACE, 0); }
		public SetcompContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_setcomp; }
	}

	public final SetcompContext setcomp() throws RecognitionException {
		SetcompContext _localctx = new SetcompContext(_ctx, getState());
		enterRule(_localctx, 348, RULE_setcomp);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1930);
			match(LBRACE);
			setState(1931);
			named_expression();
			setState(1932);
			for_if_clauses();
			setState(1933);
			match(RBRACE);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class GenexpContext extends ParserRuleContext {
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public For_if_clausesContext for_if_clauses() {
			return getRuleContext(For_if_clausesContext.class,0);
		}
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public Assignment_expressionContext assignment_expression() {
			return getRuleContext(Assignment_expressionContext.class,0);
		}
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public GenexpContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_genexp; }
	}

	public final GenexpContext genexp() throws RecognitionException {
		GenexpContext _localctx = new GenexpContext(_ctx, getState());
		enterRule(_localctx, 350, RULE_genexp);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1935);
			match(LPAR);
			setState(1938);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,246,_ctx) ) {
			case 1:
				{
				setState(1936);
				assignment_expression();
				}
				break;
			case 2:
				{
				setState(1937);
				expression();
				}
				break;
			}
			setState(1940);
			for_if_clauses();
			setState(1941);
			match(RPAR);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class DictcompContext extends ParserRuleContext {
		public TerminalNode LBRACE() { return getToken(PythonParser.LBRACE, 0); }
		public KvpairContext kvpair() {
			return getRuleContext(KvpairContext.class,0);
		}
		public For_if_clausesContext for_if_clauses() {
			return getRuleContext(For_if_clausesContext.class,0);
		}
		public TerminalNode RBRACE() { return getToken(PythonParser.RBRACE, 0); }
		public DictcompContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_dictcomp; }
	}

	public final DictcompContext dictcomp() throws RecognitionException {
		DictcompContext _localctx = new DictcompContext(_ctx, getState());
		enterRule(_localctx, 352, RULE_dictcomp);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1943);
			match(LBRACE);
			setState(1944);
			kvpair();
			setState(1945);
			for_if_clauses();
			setState(1946);
			match(RBRACE);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ArgumentsContext extends ParserRuleContext {
		public ArgsContext args() {
			return getRuleContext(ArgsContext.class,0);
		}
		public TerminalNode COMMA() { return getToken(PythonParser.COMMA, 0); }
		public ArgumentsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_arguments; }
	}

	public final ArgumentsContext arguments() throws RecognitionException {
		ArgumentsContext _localctx = new ArgumentsContext(_ctx, getState());
		enterRule(_localctx, 354, RULE_arguments);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(1948);
			args();
			setState(1950);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(1949);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ArgsContext extends ParserRuleContext {
		public List<Starred_expressionContext> starred_expression() {
			return getRuleContexts(Starred_expressionContext.class);
		}
		public Starred_expressionContext starred_expression(int i) {
			return getRuleContext(Starred_expressionContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public KwargsContext kwargs() {
			return getRuleContext(KwargsContext.class,0);
		}
		public List<Assignment_expressionContext> assignment_expression() {
			return getRuleContexts(Assignment_expressionContext.class);
		}
		public Assignment_expressionContext assignment_expression(int i) {
			return getRuleContext(Assignment_expressionContext.class,i);
		}
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public ArgsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_args; }
	}

	public final ArgsContext args() throws RecognitionException {
		ArgsContext _localctx = new ArgsContext(_ctx, getState());
		enterRule(_localctx, 356, RULE_args);
		try {
			int _alt;
			setState(1977);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,254,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1957);
				_errHandler.sync(this);
				switch (_input.LA(1)) {
				case STAR:
					{
					setState(1952);
					starred_expression();
					}
					break;
				case FSTRING_START:
				case FALSE:
				case AWAIT:
				case NONE:
				case TRUE:
				case LAMBDA:
				case NOT:
				case LPAR:
				case LSQB:
				case LBRACE:
				case PLUS:
				case MINUS:
				case TILDE:
				case ELLIPSIS:
				case NAME:
				case NUMBER:
				case STRING:
					{
					setState(1955);
					_errHandler.sync(this);
					switch ( getInterpreter().adaptivePredict(_input,248,_ctx) ) {
					case 1:
						{
						setState(1953);
						assignment_expression();
						}
						break;
					case 2:
						{
						setState(1954);
						expression();
						}
						break;
					}
					}
					break;
				default:
					throw new NoViableAltException(this);
				}
				setState(1969);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,252,_ctx);
				while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
					if ( _alt==1 ) {
						{
						{
						setState(1959);
						match(COMMA);
						setState(1965);
						_errHandler.sync(this);
						switch (_input.LA(1)) {
						case STAR:
							{
							setState(1960);
							starred_expression();
							}
							break;
						case FSTRING_START:
						case FALSE:
						case AWAIT:
						case NONE:
						case TRUE:
						case LAMBDA:
						case NOT:
						case LPAR:
						case LSQB:
						case LBRACE:
						case PLUS:
						case MINUS:
						case TILDE:
						case ELLIPSIS:
						case NAME:
						case NUMBER:
						case STRING:
							{
							setState(1963);
							_errHandler.sync(this);
							switch ( getInterpreter().adaptivePredict(_input,250,_ctx) ) {
							case 1:
								{
								setState(1961);
								assignment_expression();
								}
								break;
							case 2:
								{
								setState(1962);
								expression();
								}
								break;
							}
							}
							break;
						default:
							throw new NoViableAltException(this);
						}
						}
						} 
					}
					setState(1971);
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,252,_ctx);
				}
				setState(1974);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,253,_ctx) ) {
				case 1:
					{
					setState(1972);
					match(COMMA);
					setState(1973);
					kwargs();
					}
					break;
				}
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1976);
				kwargs();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class KwargsContext extends ParserRuleContext {
		public List<Kwarg_or_starredContext> kwarg_or_starred() {
			return getRuleContexts(Kwarg_or_starredContext.class);
		}
		public Kwarg_or_starredContext kwarg_or_starred(int i) {
			return getRuleContext(Kwarg_or_starredContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public List<Kwarg_or_double_starredContext> kwarg_or_double_starred() {
			return getRuleContexts(Kwarg_or_double_starredContext.class);
		}
		public Kwarg_or_double_starredContext kwarg_or_double_starred(int i) {
			return getRuleContext(Kwarg_or_double_starredContext.class,i);
		}
		public KwargsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_kwargs; }
	}

	public final KwargsContext kwargs() throws RecognitionException {
		KwargsContext _localctx = new KwargsContext(_ctx, getState());
		enterRule(_localctx, 358, RULE_kwargs);
		try {
			int _alt;
			setState(2006);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,259,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(1979);
				kwarg_or_starred();
				setState(1984);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,255,_ctx);
				while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
					if ( _alt==1 ) {
						{
						{
						setState(1980);
						match(COMMA);
						setState(1981);
						kwarg_or_starred();
						}
						} 
					}
					setState(1986);
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,255,_ctx);
				}
				setState(1996);
				_errHandler.sync(this);
				switch ( getInterpreter().adaptivePredict(_input,257,_ctx) ) {
				case 1:
					{
					setState(1987);
					match(COMMA);
					setState(1988);
					kwarg_or_double_starred();
					setState(1993);
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,256,_ctx);
					while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
						if ( _alt==1 ) {
							{
							{
							setState(1989);
							match(COMMA);
							setState(1990);
							kwarg_or_double_starred();
							}
							} 
						}
						setState(1995);
						_errHandler.sync(this);
						_alt = getInterpreter().adaptivePredict(_input,256,_ctx);
					}
					}
					break;
				}
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(1998);
				kwarg_or_double_starred();
				setState(2003);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,258,_ctx);
				while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
					if ( _alt==1 ) {
						{
						{
						setState(1999);
						match(COMMA);
						setState(2000);
						kwarg_or_double_starred();
						}
						} 
					}
					setState(2005);
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,258,_ctx);
				}
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Starred_expressionContext extends ParserRuleContext {
		public TerminalNode STAR() { return getToken(PythonParser.STAR, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public Starred_expressionContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_starred_expression; }
	}

	public final Starred_expressionContext starred_expression() throws RecognitionException {
		Starred_expressionContext _localctx = new Starred_expressionContext(_ctx, getState());
		enterRule(_localctx, 360, RULE_starred_expression);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(2008);
			match(STAR);
			setState(2009);
			expression();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Kwarg_or_starredContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode EQUAL() { return getToken(PythonParser.EQUAL, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public Starred_expressionContext starred_expression() {
			return getRuleContext(Starred_expressionContext.class,0);
		}
		public Kwarg_or_starredContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_kwarg_or_starred; }
	}

	public final Kwarg_or_starredContext kwarg_or_starred() throws RecognitionException {
		Kwarg_or_starredContext _localctx = new Kwarg_or_starredContext(_ctx, getState());
		enterRule(_localctx, 362, RULE_kwarg_or_starred);
		try {
			setState(2015);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case NAME:
				enterOuterAlt(_localctx, 1);
				{
				setState(2011);
				match(NAME);
				setState(2012);
				match(EQUAL);
				setState(2013);
				expression();
				}
				break;
			case STAR:
				enterOuterAlt(_localctx, 2);
				{
				setState(2014);
				starred_expression();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Kwarg_or_double_starredContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode EQUAL() { return getToken(PythonParser.EQUAL, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public TerminalNode DOUBLESTAR() { return getToken(PythonParser.DOUBLESTAR, 0); }
		public Kwarg_or_double_starredContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_kwarg_or_double_starred; }
	}

	public final Kwarg_or_double_starredContext kwarg_or_double_starred() throws RecognitionException {
		Kwarg_or_double_starredContext _localctx = new Kwarg_or_double_starredContext(_ctx, getState());
		enterRule(_localctx, 364, RULE_kwarg_or_double_starred);
		try {
			setState(2022);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case NAME:
				enterOuterAlt(_localctx, 1);
				{
				setState(2017);
				match(NAME);
				setState(2018);
				match(EQUAL);
				setState(2019);
				expression();
				}
				break;
			case DOUBLESTAR:
				enterOuterAlt(_localctx, 2);
				{
				setState(2020);
				match(DOUBLESTAR);
				setState(2021);
				expression();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Star_targetsContext extends ParserRuleContext {
		public List<Star_targetContext> star_target() {
			return getRuleContexts(Star_targetContext.class);
		}
		public Star_targetContext star_target(int i) {
			return getRuleContext(Star_targetContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Star_targetsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_star_targets; }
	}

	public final Star_targetsContext star_targets() throws RecognitionException {
		Star_targetsContext _localctx = new Star_targetsContext(_ctx, getState());
		enterRule(_localctx, 366, RULE_star_targets);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(2024);
			star_target();
			setState(2029);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,262,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(2025);
					match(COMMA);
					setState(2026);
					star_target();
					}
					} 
				}
				setState(2031);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,262,_ctx);
			}
			setState(2033);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(2032);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Star_targets_list_seqContext extends ParserRuleContext {
		public List<Star_targetContext> star_target() {
			return getRuleContexts(Star_targetContext.class);
		}
		public Star_targetContext star_target(int i) {
			return getRuleContext(Star_targetContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Star_targets_list_seqContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_star_targets_list_seq; }
	}

	public final Star_targets_list_seqContext star_targets_list_seq() throws RecognitionException {
		Star_targets_list_seqContext _localctx = new Star_targets_list_seqContext(_ctx, getState());
		enterRule(_localctx, 368, RULE_star_targets_list_seq);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(2035);
			star_target();
			setState(2038); 
			_errHandler.sync(this);
			_alt = 1;
			do {
				switch (_alt) {
				case 1:
					{
					{
					setState(2036);
					match(COMMA);
					setState(2037);
					star_target();
					}
					}
					break;
				default:
					throw new NoViableAltException(this);
				}
				setState(2040); 
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,264,_ctx);
			} while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER );
			setState(2043);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(2042);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Star_targets_tuple_seqContext extends ParserRuleContext {
		public List<Star_targetContext> star_target() {
			return getRuleContexts(Star_targetContext.class);
		}
		public Star_targetContext star_target(int i) {
			return getRuleContext(Star_targetContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Star_targets_tuple_seqContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_star_targets_tuple_seq; }
	}

	public final Star_targets_tuple_seqContext star_targets_tuple_seq() throws RecognitionException {
		Star_targets_tuple_seqContext _localctx = new Star_targets_tuple_seqContext(_ctx, getState());
		enterRule(_localctx, 370, RULE_star_targets_tuple_seq);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(2045);
			star_target();
			setState(2056);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,268,_ctx) ) {
			case 1:
				{
				setState(2046);
				match(COMMA);
				}
				break;
			case 2:
				{
				setState(2049); 
				_errHandler.sync(this);
				_alt = 1;
				do {
					switch (_alt) {
					case 1:
						{
						{
						setState(2047);
						match(COMMA);
						setState(2048);
						star_target();
						}
						}
						break;
					default:
						throw new NoViableAltException(this);
					}
					setState(2051); 
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,266,_ctx);
				} while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER );
				setState(2054);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==COMMA) {
					{
					setState(2053);
					match(COMMA);
					}
				}

				}
				break;
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Star_targetContext extends ParserRuleContext {
		public TerminalNode STAR() { return getToken(PythonParser.STAR, 0); }
		public Star_targetContext star_target() {
			return getRuleContext(Star_targetContext.class,0);
		}
		public Target_with_star_atomContext target_with_star_atom() {
			return getRuleContext(Target_with_star_atomContext.class,0);
		}
		public Star_targetContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_star_target; }
	}

	public final Star_targetContext star_target() throws RecognitionException {
		Star_targetContext _localctx = new Star_targetContext(_ctx, getState());
		enterRule(_localctx, 372, RULE_star_target);
		try {
			setState(2061);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case STAR:
				enterOuterAlt(_localctx, 1);
				{
				setState(2058);
				match(STAR);
				{
				setState(2059);
				star_target();
				}
				}
				break;
			case FSTRING_START:
			case FALSE:
			case NONE:
			case TRUE:
			case LPAR:
			case LSQB:
			case LBRACE:
			case ELLIPSIS:
			case NAME:
			case NUMBER:
			case STRING:
				enterOuterAlt(_localctx, 2);
				{
				setState(2060);
				target_with_star_atom();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Target_with_star_atomContext extends ParserRuleContext {
		public T_primaryContext t_primary() {
			return getRuleContext(T_primaryContext.class,0);
		}
		public TerminalNode DOT() { return getToken(PythonParser.DOT, 0); }
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode LSQB() { return getToken(PythonParser.LSQB, 0); }
		public SlicesContext slices() {
			return getRuleContext(SlicesContext.class,0);
		}
		public TerminalNode RSQB() { return getToken(PythonParser.RSQB, 0); }
		public Star_atomContext star_atom() {
			return getRuleContext(Star_atomContext.class,0);
		}
		public Target_with_star_atomContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_target_with_star_atom; }
	}

	public final Target_with_star_atomContext target_with_star_atom() throws RecognitionException {
		Target_with_star_atomContext _localctx = new Target_with_star_atomContext(_ctx, getState());
		enterRule(_localctx, 374, RULE_target_with_star_atom);
		try {
			setState(2073);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,271,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(2063);
				t_primary(0);
				setState(2070);
				_errHandler.sync(this);
				switch (_input.LA(1)) {
				case DOT:
					{
					setState(2064);
					match(DOT);
					setState(2065);
					match(NAME);
					}
					break;
				case LSQB:
					{
					setState(2066);
					match(LSQB);
					setState(2067);
					slices();
					setState(2068);
					match(RSQB);
					}
					break;
				default:
					throw new NoViableAltException(this);
				}
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(2072);
				star_atom();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Star_atomContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public Target_with_star_atomContext target_with_star_atom() {
			return getRuleContext(Target_with_star_atomContext.class,0);
		}
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public Star_targets_tuple_seqContext star_targets_tuple_seq() {
			return getRuleContext(Star_targets_tuple_seqContext.class,0);
		}
		public TerminalNode LSQB() { return getToken(PythonParser.LSQB, 0); }
		public TerminalNode RSQB() { return getToken(PythonParser.RSQB, 0); }
		public Star_targets_list_seqContext star_targets_list_seq() {
			return getRuleContext(Star_targets_list_seqContext.class,0);
		}
		public Star_atomContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_star_atom; }
	}

	public final Star_atomContext star_atom() throws RecognitionException {
		Star_atomContext _localctx = new Star_atomContext(_ctx, getState());
		enterRule(_localctx, 376, RULE_star_atom);
		int _la;
		try {
			setState(2090);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,274,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(2075);
				match(NAME);
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(2076);
				match(LPAR);
				setState(2077);
				target_with_star_atom();
				setState(2078);
				match(RPAR);
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(2080);
				match(LPAR);
				setState(2082);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 36090369670187080L) != 0) || ((((_la - 88)) & ~0x3f) == 0 && ((1L << (_la - 88)) & 225L) != 0)) {
					{
					setState(2081);
					star_targets_tuple_seq();
					}
				}

				setState(2084);
				match(RPAR);
				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(2085);
				match(LSQB);
				setState(2087);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 36090369670187080L) != 0) || ((((_la - 88)) & ~0x3f) == 0 && ((1L << (_la - 88)) & 225L) != 0)) {
					{
					setState(2086);
					star_targets_list_seq();
					}
				}

				setState(2089);
				match(RSQB);
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Single_targetContext extends ParserRuleContext {
		public Single_subscript_attribute_targetContext single_subscript_attribute_target() {
			return getRuleContext(Single_subscript_attribute_targetContext.class,0);
		}
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public Single_targetContext single_target() {
			return getRuleContext(Single_targetContext.class,0);
		}
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public Single_targetContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_single_target; }
	}

	public final Single_targetContext single_target() throws RecognitionException {
		Single_targetContext _localctx = new Single_targetContext(_ctx, getState());
		enterRule(_localctx, 378, RULE_single_target);
		try {
			setState(2098);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,275,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(2092);
				single_subscript_attribute_target();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(2093);
				match(NAME);
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(2094);
				match(LPAR);
				setState(2095);
				single_target();
				setState(2096);
				match(RPAR);
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Single_subscript_attribute_targetContext extends ParserRuleContext {
		public T_primaryContext t_primary() {
			return getRuleContext(T_primaryContext.class,0);
		}
		public TerminalNode DOT() { return getToken(PythonParser.DOT, 0); }
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode LSQB() { return getToken(PythonParser.LSQB, 0); }
		public SlicesContext slices() {
			return getRuleContext(SlicesContext.class,0);
		}
		public TerminalNode RSQB() { return getToken(PythonParser.RSQB, 0); }
		public Single_subscript_attribute_targetContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_single_subscript_attribute_target; }
	}

	public final Single_subscript_attribute_targetContext single_subscript_attribute_target() throws RecognitionException {
		Single_subscript_attribute_targetContext _localctx = new Single_subscript_attribute_targetContext(_ctx, getState());
		enterRule(_localctx, 380, RULE_single_subscript_attribute_target);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(2100);
			t_primary(0);
			setState(2107);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case DOT:
				{
				setState(2101);
				match(DOT);
				setState(2102);
				match(NAME);
				}
				break;
			case LSQB:
				{
				setState(2103);
				match(LSQB);
				setState(2104);
				slices();
				setState(2105);
				match(RSQB);
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class T_primaryContext extends ParserRuleContext {
		public AtomContext atom() {
			return getRuleContext(AtomContext.class,0);
		}
		public T_primaryContext t_primary() {
			return getRuleContext(T_primaryContext.class,0);
		}
		public TerminalNode DOT() { return getToken(PythonParser.DOT, 0); }
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode LSQB() { return getToken(PythonParser.LSQB, 0); }
		public SlicesContext slices() {
			return getRuleContext(SlicesContext.class,0);
		}
		public TerminalNode RSQB() { return getToken(PythonParser.RSQB, 0); }
		public GenexpContext genexp() {
			return getRuleContext(GenexpContext.class,0);
		}
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public ArgumentsContext arguments() {
			return getRuleContext(ArgumentsContext.class,0);
		}
		public T_primaryContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_t_primary; }
	}

	public final T_primaryContext t_primary() throws RecognitionException {
		return t_primary(0);
	}

	private T_primaryContext t_primary(int _p) throws RecognitionException {
		ParserRuleContext _parentctx = _ctx;
		int _parentState = getState();
		T_primaryContext _localctx = new T_primaryContext(_ctx, _parentState);
		T_primaryContext _prevctx = _localctx;
		int _startState = 382;
		enterRecursionRule(_localctx, 382, RULE_t_primary, _p);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			{
			setState(2110);
			atom();
			}
			_ctx.stop = _input.LT(-1);
			setState(2129);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,279,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					if ( _parseListeners!=null ) triggerExitRuleEvent();
					_prevctx = _localctx;
					{
					{
					_localctx = new T_primaryContext(_parentctx, _parentState);
					pushNewRecursionContext(_localctx, _startState, RULE_t_primary);
					setState(2112);
					if (!(precpred(_ctx, 2))) throw new FailedPredicateException(this, "precpred(_ctx, 2)");
					setState(2125);
					_errHandler.sync(this);
					switch ( getInterpreter().adaptivePredict(_input,278,_ctx) ) {
					case 1:
						{
						setState(2113);
						match(DOT);
						setState(2114);
						match(NAME);
						}
						break;
					case 2:
						{
						setState(2115);
						match(LSQB);
						setState(2116);
						slices();
						setState(2117);
						match(RSQB);
						}
						break;
					case 3:
						{
						setState(2119);
						genexp();
						}
						break;
					case 4:
						{
						setState(2120);
						match(LPAR);
						setState(2122);
						_errHandler.sync(this);
						_la = _input.LA(1);
						if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 63111984631056584L) != 0) || ((((_la - 67)) & ~0x3f) == 0 && ((1L << (_la - 67)) & 471859217L) != 0)) {
							{
							setState(2121);
							arguments();
							}
						}

						setState(2124);
						match(RPAR);
						}
						break;
					}
					}
					} 
				}
				setState(2131);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,279,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			unrollRecursionContexts(_parentctx);
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Del_targetsContext extends ParserRuleContext {
		public List<Del_targetContext> del_target() {
			return getRuleContexts(Del_targetContext.class);
		}
		public Del_targetContext del_target(int i) {
			return getRuleContext(Del_targetContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public Del_targetsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_del_targets; }
	}

	public final Del_targetsContext del_targets() throws RecognitionException {
		Del_targetsContext _localctx = new Del_targetsContext(_ctx, getState());
		enterRule(_localctx, 384, RULE_del_targets);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(2132);
			del_target();
			setState(2137);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,280,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(2133);
					match(COMMA);
					setState(2134);
					del_target();
					}
					} 
				}
				setState(2139);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,280,_ctx);
			}
			setState(2141);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(2140);
				match(COMMA);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Del_targetContext extends ParserRuleContext {
		public T_primaryContext t_primary() {
			return getRuleContext(T_primaryContext.class,0);
		}
		public TerminalNode DOT() { return getToken(PythonParser.DOT, 0); }
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode LSQB() { return getToken(PythonParser.LSQB, 0); }
		public SlicesContext slices() {
			return getRuleContext(SlicesContext.class,0);
		}
		public TerminalNode RSQB() { return getToken(PythonParser.RSQB, 0); }
		public Del_t_atomContext del_t_atom() {
			return getRuleContext(Del_t_atomContext.class,0);
		}
		public Del_targetContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_del_target; }
	}

	public final Del_targetContext del_target() throws RecognitionException {
		Del_targetContext _localctx = new Del_targetContext(_ctx, getState());
		enterRule(_localctx, 386, RULE_del_target);
		try {
			setState(2153);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,283,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(2143);
				t_primary(0);
				setState(2150);
				_errHandler.sync(this);
				switch (_input.LA(1)) {
				case DOT:
					{
					setState(2144);
					match(DOT);
					setState(2145);
					match(NAME);
					}
					break;
				case LSQB:
					{
					setState(2146);
					match(LSQB);
					setState(2147);
					slices();
					setState(2148);
					match(RSQB);
					}
					break;
				default:
					throw new NoViableAltException(this);
				}
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(2152);
				del_t_atom();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Del_t_atomContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public TerminalNode LPAR() { return getToken(PythonParser.LPAR, 0); }
		public Del_targetContext del_target() {
			return getRuleContext(Del_targetContext.class,0);
		}
		public TerminalNode RPAR() { return getToken(PythonParser.RPAR, 0); }
		public Del_targetsContext del_targets() {
			return getRuleContext(Del_targetsContext.class,0);
		}
		public TerminalNode LSQB() { return getToken(PythonParser.LSQB, 0); }
		public TerminalNode RSQB() { return getToken(PythonParser.RSQB, 0); }
		public Del_t_atomContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_del_t_atom; }
	}

	public final Del_t_atomContext del_t_atom() throws RecognitionException {
		Del_t_atomContext _localctx = new Del_t_atomContext(_ctx, getState());
		enterRule(_localctx, 388, RULE_del_t_atom);
		int _la;
		try {
			setState(2170);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,286,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(2155);
				match(NAME);
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(2156);
				match(LPAR);
				setState(2157);
				del_target();
				setState(2158);
				match(RPAR);
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(2160);
				match(LPAR);
				setState(2162);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 61572651223112L) != 0) || ((((_la - 88)) & ~0x3f) == 0 && ((1L << (_la - 88)) & 225L) != 0)) {
					{
					setState(2161);
					del_targets();
					}
				}

				setState(2164);
				match(RPAR);
				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(2165);
				match(LSQB);
				setState(2167);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 61572651223112L) != 0) || ((((_la - 88)) & ~0x3f) == 0 && ((1L << (_la - 88)) & 225L) != 0)) {
					{
					setState(2166);
					del_targets();
					}
				}

				setState(2169);
				match(RSQB);
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Type_expressionsContext extends ParserRuleContext {
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(PythonParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(PythonParser.COMMA, i);
		}
		public TerminalNode STAR() { return getToken(PythonParser.STAR, 0); }
		public TerminalNode DOUBLESTAR() { return getToken(PythonParser.DOUBLESTAR, 0); }
		public Type_expressionsContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_type_expressions; }
	}

	public final Type_expressionsContext type_expressions() throws RecognitionException {
		Type_expressionsContext _localctx = new Type_expressionsContext(_ctx, getState());
		enterRule(_localctx, 390, RULE_type_expressions);
		int _la;
		try {
			int _alt;
			setState(2203);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case FSTRING_START:
			case FALSE:
			case AWAIT:
			case NONE:
			case TRUE:
			case LAMBDA:
			case NOT:
			case LPAR:
			case LSQB:
			case LBRACE:
			case PLUS:
			case MINUS:
			case TILDE:
			case ELLIPSIS:
			case NAME:
			case NUMBER:
			case STRING:
				enterOuterAlt(_localctx, 1);
				{
				setState(2172);
				expression();
				setState(2177);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,287,_ctx);
				while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
					if ( _alt==1 ) {
						{
						{
						setState(2173);
						match(COMMA);
						setState(2174);
						expression();
						}
						} 
					}
					setState(2179);
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,287,_ctx);
				}
				setState(2192);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==COMMA) {
					{
					setState(2180);
					match(COMMA);
					setState(2190);
					_errHandler.sync(this);
					switch (_input.LA(1)) {
					case STAR:
						{
						setState(2181);
						match(STAR);
						setState(2182);
						expression();
						setState(2186);
						_errHandler.sync(this);
						_la = _input.LA(1);
						if (_la==COMMA) {
							{
							setState(2183);
							match(COMMA);
							setState(2184);
							match(DOUBLESTAR);
							setState(2185);
							expression();
							}
						}

						}
						break;
					case DOUBLESTAR:
						{
						setState(2188);
						match(DOUBLESTAR);
						setState(2189);
						expression();
						}
						break;
					default:
						throw new NoViableAltException(this);
					}
					}
				}

				}
				break;
			case STAR:
				enterOuterAlt(_localctx, 2);
				{
				setState(2194);
				match(STAR);
				setState(2195);
				expression();
				setState(2199);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==COMMA) {
					{
					setState(2196);
					match(COMMA);
					setState(2197);
					match(DOUBLESTAR);
					setState(2198);
					expression();
					}
				}

				}
				break;
			case DOUBLESTAR:
				enterOuterAlt(_localctx, 3);
				{
				setState(2201);
				match(DOUBLESTAR);
				setState(2202);
				expression();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Func_type_commentContext extends ParserRuleContext {
		public TerminalNode NEWLINE() { return getToken(PythonParser.NEWLINE, 0); }
		public TerminalNode TYPE_COMMENT() { return getToken(PythonParser.TYPE_COMMENT, 0); }
		public Func_type_commentContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_func_type_comment; }
	}

	public final Func_type_commentContext func_type_comment() throws RecognitionException {
		Func_type_commentContext _localctx = new Func_type_commentContext(_ctx, getState());
		enterRule(_localctx, 392, RULE_func_type_comment);
		try {
			setState(2208);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case NEWLINE:
				enterOuterAlt(_localctx, 1);
				{
				setState(2205);
				match(NEWLINE);
				setState(2206);
				match(TYPE_COMMENT);
				}
				break;
			case TYPE_COMMENT:
				enterOuterAlt(_localctx, 2);
				{
				setState(2207);
				match(TYPE_COMMENT);
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Soft_kw_typeContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public Soft_kw_typeContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_soft_kw_type; }
	}

	public final Soft_kw_typeContext soft_kw_type() throws RecognitionException {
		Soft_kw_typeContext _localctx = new Soft_kw_typeContext(_ctx, getState());
		enterRule(_localctx, 394, RULE_soft_kw_type);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(2210);
			if (!(self.isEqualToCurrentTokenText("type"))) throw new FailedPredicateException(this, "self.isEqualToCurrentTokenText(\"type\")");
			setState(2211);
			match(NAME);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Soft_kw_matchContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public Soft_kw_matchContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_soft_kw_match; }
	}

	public final Soft_kw_matchContext soft_kw_match() throws RecognitionException {
		Soft_kw_matchContext _localctx = new Soft_kw_matchContext(_ctx, getState());
		enterRule(_localctx, 396, RULE_soft_kw_match);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(2213);
			if (!(self.isEqualToCurrentTokenText("match"))) throw new FailedPredicateException(this, "self.isEqualToCurrentTokenText(\"match\")");
			setState(2214);
			match(NAME);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Soft_kw_caseContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public Soft_kw_caseContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_soft_kw_case; }
	}

	public final Soft_kw_caseContext soft_kw_case() throws RecognitionException {
		Soft_kw_caseContext _localctx = new Soft_kw_caseContext(_ctx, getState());
		enterRule(_localctx, 398, RULE_soft_kw_case);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(2216);
			if (!(self.isEqualToCurrentTokenText("case"))) throw new FailedPredicateException(this, "self.isEqualToCurrentTokenText(\"case\")");
			setState(2217);
			match(NAME);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Soft_kw_wildcardContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public Soft_kw_wildcardContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_soft_kw_wildcard; }
	}

	public final Soft_kw_wildcardContext soft_kw_wildcard() throws RecognitionException {
		Soft_kw_wildcardContext _localctx = new Soft_kw_wildcardContext(_ctx, getState());
		enterRule(_localctx, 400, RULE_soft_kw_wildcard);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(2219);
			if (!(self.isEqualToCurrentTokenText("_"))) throw new FailedPredicateException(this, "self.isEqualToCurrentTokenText(\"_\")");
			setState(2220);
			match(NAME);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Soft_kw__not__wildcardContext extends ParserRuleContext {
		public TerminalNode NAME() { return getToken(PythonParser.NAME, 0); }
		public Soft_kw__not__wildcardContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_soft_kw__not__wildcard; }
	}

	public final Soft_kw__not__wildcardContext soft_kw__not__wildcard() throws RecognitionException {
		Soft_kw__not__wildcardContext _localctx = new Soft_kw__not__wildcardContext(_ctx, getState());
		enterRule(_localctx, 402, RULE_soft_kw__not__wildcard);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(2222);
			if (!(self.isnotEqualToCurrentTokenText("_"))) throw new FailedPredicateException(this, "self.isnotEqualToCurrentTokenText(\"_\")");
			setState(2223);
			match(NAME);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	public boolean sempred(RuleContext _localctx, int ruleIndex, int predIndex) {
		switch (ruleIndex) {
		case 30:
			return dotted_name_sempred((Dotted_nameContext)_localctx, predIndex);
		case 129:
			return bitwise_or_sempred((Bitwise_orContext)_localctx, predIndex);
		case 130:
			return bitwise_xor_sempred((Bitwise_xorContext)_localctx, predIndex);
		case 131:
			return bitwise_and_sempred((Bitwise_andContext)_localctx, predIndex);
		case 132:
			return shift_expr_sempred((Shift_exprContext)_localctx, predIndex);
		case 133:
			return sum_sempred((SumContext)_localctx, predIndex);
		case 134:
			return term_sempred((TermContext)_localctx, predIndex);
		case 135:
			return tolerance_sempred((ToleranceContext)_localctx, predIndex);
		case 139:
			return primary_sempred((PrimaryContext)_localctx, predIndex);
		case 191:
			return t_primary_sempred((T_primaryContext)_localctx, predIndex);
		case 197:
			return soft_kw_type_sempred((Soft_kw_typeContext)_localctx, predIndex);
		case 198:
			return soft_kw_match_sempred((Soft_kw_matchContext)_localctx, predIndex);
		case 199:
			return soft_kw_case_sempred((Soft_kw_caseContext)_localctx, predIndex);
		case 200:
			return soft_kw_wildcard_sempred((Soft_kw_wildcardContext)_localctx, predIndex);
		case 201:
			return soft_kw__not__wildcard_sempred((Soft_kw__not__wildcardContext)_localctx, predIndex);
		}
		return true;
	}
	private boolean dotted_name_sempred(Dotted_nameContext _localctx, int predIndex) {
		switch (predIndex) {
		case 0:
			return precpred(_ctx, 2);
		}
		return true;
	}
	private boolean bitwise_or_sempred(Bitwise_orContext _localctx, int predIndex) {
		switch (predIndex) {
		case 1:
			return precpred(_ctx, 2);
		}
		return true;
	}
	private boolean bitwise_xor_sempred(Bitwise_xorContext _localctx, int predIndex) {
		switch (predIndex) {
		case 2:
			return precpred(_ctx, 2);
		}
		return true;
	}
	private boolean bitwise_and_sempred(Bitwise_andContext _localctx, int predIndex) {
		switch (predIndex) {
		case 3:
			return precpred(_ctx, 2);
		}
		return true;
	}
	private boolean shift_expr_sempred(Shift_exprContext _localctx, int predIndex) {
		switch (predIndex) {
		case 4:
			return precpred(_ctx, 2);
		}
		return true;
	}
	private boolean sum_sempred(SumContext _localctx, int predIndex) {
		switch (predIndex) {
		case 5:
			return precpred(_ctx, 2);
		}
		return true;
	}
	private boolean term_sempred(TermContext _localctx, int predIndex) {
		switch (predIndex) {
		case 6:
			return precpred(_ctx, 2);
		}
		return true;
	}
	private boolean tolerance_sempred(ToleranceContext _localctx, int predIndex) {
		switch (predIndex) {
		case 7:
			return precpred(_ctx, 2);
		}
		return true;
	}
	private boolean primary_sempred(PrimaryContext _localctx, int predIndex) {
		switch (predIndex) {
		case 8:
			return precpred(_ctx, 2);
		}
		return true;
	}
	private boolean t_primary_sempred(T_primaryContext _localctx, int predIndex) {
		switch (predIndex) {
		case 9:
			return precpred(_ctx, 2);
		}
		return true;
	}
	private boolean soft_kw_type_sempred(Soft_kw_typeContext _localctx, int predIndex) {
		switch (predIndex) {
		case 10:
			return self.isEqualToCurrentTokenText("type");
		}
		return true;
	}
	private boolean soft_kw_match_sempred(Soft_kw_matchContext _localctx, int predIndex) {
		switch (predIndex) {
		case 11:
			return self.isEqualToCurrentTokenText("match");
		}
		return true;
	}
	private boolean soft_kw_case_sempred(Soft_kw_caseContext _localctx, int predIndex) {
		switch (predIndex) {
		case 12:
			return self.isEqualToCurrentTokenText("case");
		}
		return true;
	}
	private boolean soft_kw_wildcard_sempred(Soft_kw_wildcardContext _localctx, int predIndex) {
		switch (predIndex) {
		case 13:
			return self.isEqualToCurrentTokenText("_");
		}
		return true;
	}
	private boolean soft_kw__not__wildcard_sempred(Soft_kw__not__wildcardContext _localctx, int predIndex) {
		switch (predIndex) {
		case 14:
			return self.isnotEqualToCurrentTokenText("_");
		}
		return true;
	}

	public static final String _serializedATN =
		"\u0004\u0001e\u08b2\u0002\u0000\u0007\u0000\u0002\u0001\u0007\u0001\u0002"+
		"\u0002\u0007\u0002\u0002\u0003\u0007\u0003\u0002\u0004\u0007\u0004\u0002"+
		"\u0005\u0007\u0005\u0002\u0006\u0007\u0006\u0002\u0007\u0007\u0007\u0002"+
		"\b\u0007\b\u0002\t\u0007\t\u0002\n\u0007\n\u0002\u000b\u0007\u000b\u0002"+
		"\f\u0007\f\u0002\r\u0007\r\u0002\u000e\u0007\u000e\u0002\u000f\u0007\u000f"+
		"\u0002\u0010\u0007\u0010\u0002\u0011\u0007\u0011\u0002\u0012\u0007\u0012"+
		"\u0002\u0013\u0007\u0013\u0002\u0014\u0007\u0014\u0002\u0015\u0007\u0015"+
		"\u0002\u0016\u0007\u0016\u0002\u0017\u0007\u0017\u0002\u0018\u0007\u0018"+
		"\u0002\u0019\u0007\u0019\u0002\u001a\u0007\u001a\u0002\u001b\u0007\u001b"+
		"\u0002\u001c\u0007\u001c\u0002\u001d\u0007\u001d\u0002\u001e\u0007\u001e"+
		"\u0002\u001f\u0007\u001f\u0002 \u0007 \u0002!\u0007!\u0002\"\u0007\"\u0002"+
		"#\u0007#\u0002$\u0007$\u0002%\u0007%\u0002&\u0007&\u0002\'\u0007\'\u0002"+
		"(\u0007(\u0002)\u0007)\u0002*\u0007*\u0002+\u0007+\u0002,\u0007,\u0002"+
		"-\u0007-\u0002.\u0007.\u0002/\u0007/\u00020\u00070\u00021\u00071\u0002"+
		"2\u00072\u00023\u00073\u00024\u00074\u00025\u00075\u00026\u00076\u0002"+
		"7\u00077\u00028\u00078\u00029\u00079\u0002:\u0007:\u0002;\u0007;\u0002"+
		"<\u0007<\u0002=\u0007=\u0002>\u0007>\u0002?\u0007?\u0002@\u0007@\u0002"+
		"A\u0007A\u0002B\u0007B\u0002C\u0007C\u0002D\u0007D\u0002E\u0007E\u0002"+
		"F\u0007F\u0002G\u0007G\u0002H\u0007H\u0002I\u0007I\u0002J\u0007J\u0002"+
		"K\u0007K\u0002L\u0007L\u0002M\u0007M\u0002N\u0007N\u0002O\u0007O\u0002"+
		"P\u0007P\u0002Q\u0007Q\u0002R\u0007R\u0002S\u0007S\u0002T\u0007T\u0002"+
		"U\u0007U\u0002V\u0007V\u0002W\u0007W\u0002X\u0007X\u0002Y\u0007Y\u0002"+
		"Z\u0007Z\u0002[\u0007[\u0002\\\u0007\\\u0002]\u0007]\u0002^\u0007^\u0002"+
		"_\u0007_\u0002`\u0007`\u0002a\u0007a\u0002b\u0007b\u0002c\u0007c\u0002"+
		"d\u0007d\u0002e\u0007e\u0002f\u0007f\u0002g\u0007g\u0002h\u0007h\u0002"+
		"i\u0007i\u0002j\u0007j\u0002k\u0007k\u0002l\u0007l\u0002m\u0007m\u0002"+
		"n\u0007n\u0002o\u0007o\u0002p\u0007p\u0002q\u0007q\u0002r\u0007r\u0002"+
		"s\u0007s\u0002t\u0007t\u0002u\u0007u\u0002v\u0007v\u0002w\u0007w\u0002"+
		"x\u0007x\u0002y\u0007y\u0002z\u0007z\u0002{\u0007{\u0002|\u0007|\u0002"+
		"}\u0007}\u0002~\u0007~\u0002\u007f\u0007\u007f\u0002\u0080\u0007\u0080"+
		"\u0002\u0081\u0007\u0081\u0002\u0082\u0007\u0082\u0002\u0083\u0007\u0083"+
		"\u0002\u0084\u0007\u0084\u0002\u0085\u0007\u0085\u0002\u0086\u0007\u0086"+
		"\u0002\u0087\u0007\u0087\u0002\u0088\u0007\u0088\u0002\u0089\u0007\u0089"+
		"\u0002\u008a\u0007\u008a\u0002\u008b\u0007\u008b\u0002\u008c\u0007\u008c"+
		"\u0002\u008d\u0007\u008d\u0002\u008e\u0007\u008e\u0002\u008f\u0007\u008f"+
		"\u0002\u0090\u0007\u0090\u0002\u0091\u0007\u0091\u0002\u0092\u0007\u0092"+
		"\u0002\u0093\u0007\u0093\u0002\u0094\u0007\u0094\u0002\u0095\u0007\u0095"+
		"\u0002\u0096\u0007\u0096\u0002\u0097\u0007\u0097\u0002\u0098\u0007\u0098"+
		"\u0002\u0099\u0007\u0099\u0002\u009a\u0007\u009a\u0002\u009b\u0007\u009b"+
		"\u0002\u009c\u0007\u009c\u0002\u009d\u0007\u009d\u0002\u009e\u0007\u009e"+
		"\u0002\u009f\u0007\u009f\u0002\u00a0\u0007\u00a0\u0002\u00a1\u0007\u00a1"+
		"\u0002\u00a2\u0007\u00a2\u0002\u00a3\u0007\u00a3\u0002\u00a4\u0007\u00a4"+
		"\u0002\u00a5\u0007\u00a5\u0002\u00a6\u0007\u00a6\u0002\u00a7\u0007\u00a7"+
		"\u0002\u00a8\u0007\u00a8\u0002\u00a9\u0007\u00a9\u0002\u00aa\u0007\u00aa"+
		"\u0002\u00ab\u0007\u00ab\u0002\u00ac\u0007\u00ac\u0002\u00ad\u0007\u00ad"+
		"\u0002\u00ae\u0007\u00ae\u0002\u00af\u0007\u00af\u0002\u00b0\u0007\u00b0"+
		"\u0002\u00b1\u0007\u00b1\u0002\u00b2\u0007\u00b2\u0002\u00b3\u0007\u00b3"+
		"\u0002\u00b4\u0007\u00b4\u0002\u00b5\u0007\u00b5\u0002\u00b6\u0007\u00b6"+
		"\u0002\u00b7\u0007\u00b7\u0002\u00b8\u0007\u00b8\u0002\u00b9\u0007\u00b9"+
		"\u0002\u00ba\u0007\u00ba\u0002\u00bb\u0007\u00bb\u0002\u00bc\u0007\u00bc"+
		"\u0002\u00bd\u0007\u00bd\u0002\u00be\u0007\u00be\u0002\u00bf\u0007\u00bf"+
		"\u0002\u00c0\u0007\u00c0\u0002\u00c1\u0007\u00c1\u0002\u00c2\u0007\u00c2"+
		"\u0002\u00c3\u0007\u00c3\u0002\u00c4\u0007\u00c4\u0002\u00c5\u0007\u00c5"+
		"\u0002\u00c6\u0007\u00c6\u0002\u00c7\u0007\u00c7\u0002\u00c8\u0007\u00c8"+
		"\u0002\u00c9\u0007\u00c9\u0001\u0000\u0003\u0000\u0196\b\u0000\u0001\u0000"+
		"\u0001\u0000\u0001\u0001\u0001\u0001\u0001\u0002\u0001\u0002\u0005\u0002"+
		"\u019e\b\u0002\n\u0002\f\u0002\u01a1\t\u0002\u0001\u0002\u0001\u0002\u0001"+
		"\u0003\u0001\u0003\u0003\u0003\u01a7\b\u0003\u0001\u0003\u0001\u0003\u0001"+
		"\u0003\u0001\u0003\u0005\u0003\u01ad\b\u0003\n\u0003\f\u0003\u01b0\t\u0003"+
		"\u0001\u0003\u0001\u0003\u0001\u0004\u0001\u0004\u0001\u0005\u0004\u0005"+
		"\u01b7\b\u0005\u000b\u0005\f\u0005\u01b8\u0001\u0006\u0001\u0006\u0003"+
		"\u0006\u01bd\b\u0006\u0001\u0007\u0001\u0007\u0001\u0007\u0001\u0007\u0001"+
		"\u0007\u0001\u0007\u0003\u0007\u01c5\b\u0007\u0001\b\u0001\b\u0001\b\u0005"+
		"\b\u01ca\b\b\n\b\f\b\u01cd\t\b\u0001\b\u0003\b\u01d0\b\b\u0001\b\u0001"+
		"\b\u0001\t\u0001\t\u0001\t\u0001\t\u0001\t\u0001\t\u0001\t\u0001\t\u0001"+
		"\t\u0001\t\u0001\t\u0001\t\u0001\t\u0001\t\u0001\t\u0003\t\u01e3\b\t\u0001"+
		"\n\u0001\n\u0001\n\u0001\n\u0001\n\u0001\n\u0001\n\u0001\n\u0003\n\u01ed"+
		"\b\n\u0001\u000b\u0001\u000b\u0001\u000b\u0001\u000b\u0001\u000b\u0003"+
		"\u000b\u01f4\b\u000b\u0001\u000b\u0001\u000b\u0001\u000b\u0001\u000b\u0001"+
		"\u000b\u0003\u000b\u01fb\b\u000b\u0001\u000b\u0001\u000b\u0001\u000b\u0001"+
		"\u000b\u0003\u000b\u0201\b\u000b\u0001\u000b\u0001\u000b\u0001\u000b\u0004"+
		"\u000b\u0206\b\u000b\u000b\u000b\f\u000b\u0207\u0001\u000b\u0001\u000b"+
		"\u0003\u000b\u020c\b\u000b\u0001\u000b\u0003\u000b\u020f\b\u000b\u0001"+
		"\u000b\u0001\u000b\u0001\u000b\u0001\u000b\u0003\u000b\u0215\b\u000b\u0003"+
		"\u000b\u0217\b\u000b\u0001\f\u0001\f\u0003\f\u021b\b\f\u0001\r\u0001\r"+
		"\u0001\u000e\u0001\u000e\u0003\u000e\u0221\b\u000e\u0001\u000f\u0001\u000f"+
		"\u0001\u000f\u0001\u000f\u0003\u000f\u0227\b\u000f\u0003\u000f\u0229\b"+
		"\u000f\u0001\u0010\u0001\u0010\u0001\u0010\u0001\u0010\u0005\u0010\u022f"+
		"\b\u0010\n\u0010\f\u0010\u0232\t\u0010\u0001\u0011\u0001\u0011\u0001\u0011"+
		"\u0001\u0011\u0005\u0011\u0238\b\u0011\n\u0011\f\u0011\u023b\t\u0011\u0001"+
		"\u0012\u0001\u0012\u0001\u0012\u0001\u0013\u0001\u0013\u0001\u0014\u0001"+
		"\u0014\u0001\u0014\u0001\u0014\u0003\u0014\u0246\b\u0014\u0001\u0015\u0001"+
		"\u0015\u0003\u0015\u024a\b\u0015\u0001\u0016\u0001\u0016\u0001\u0016\u0004"+
		"\u0016\u024f\b\u0016\u000b\u0016\f\u0016\u0250\u0001\u0017\u0001\u0017"+
		"\u0001\u0017\u0001\u0018\u0001\u0018\u0005\u0018\u0258\b\u0018\n\u0018"+
		"\f\u0018\u025b\t\u0018\u0001\u0018\u0001\u0018\u0001\u0018\u0001\u0018"+
		"\u0001\u0018\u0001\u0018\u0004\u0018\u0263\b\u0018\u000b\u0018\f\u0018"+
		"\u0264\u0001\u0018\u0001\u0018\u0003\u0018\u0269\b\u0018\u0001\u0019\u0001"+
		"\u0019\u0001\u0019\u0003\u0019\u026e\b\u0019\u0001\u0019\u0001\u0019\u0001"+
		"\u0019\u0001\u0019\u0003\u0019\u0274\b\u0019\u0001\u001a\u0001\u001a\u0001"+
		"\u001a\u0005\u001a\u0279\b\u001a\n\u001a\f\u001a\u027c\t\u001a\u0001\u001b"+
		"\u0001\u001b\u0001\u001b\u0003\u001b\u0281\b\u001b\u0001\u001c\u0001\u001c"+
		"\u0001\u001c\u0005\u001c\u0286\b\u001c\n\u001c\f\u001c\u0289\t\u001c\u0001"+
		"\u001d\u0001\u001d\u0001\u001d\u0003\u001d\u028e\b\u001d\u0001\u001e\u0001"+
		"\u001e\u0001\u001e\u0001\u001e\u0001\u001e\u0001\u001e\u0005\u001e\u0296"+
		"\b\u001e\n\u001e\f\u001e\u0299\t\u001e\u0001\u001f\u0001\u001f\u0001\u001f"+
		"\u0001\u001f\u0001\u001f\u0001\u001f\u0003\u001f\u02a1\b\u001f\u0001 "+
		"\u0001 \u0001 \u0001 \u0004 \u02a7\b \u000b \f \u02a8\u0001!\u0001!\u0001"+
		"!\u0001!\u0003!\u02af\b!\u0001\"\u0001\"\u0001\"\u0003\"\u02b4\b\"\u0001"+
		"\"\u0001\"\u0003\"\u02b8\b\"\u0001\"\u0003\"\u02bb\b\"\u0001\"\u0001\""+
		"\u0001\"\u0001#\u0001#\u0001#\u0001#\u0003#\u02c4\b#\u0001$\u0001$\u0001"+
		"$\u0003$\u02c9\b$\u0001$\u0001$\u0003$\u02cd\b$\u0001$\u0001$\u0001$\u0003"+
		"$\u02d2\b$\u0001$\u0001$\u0003$\u02d6\b$\u0001$\u0001$\u0001$\u0001$\u0001"+
		"$\u0003$\u02dd\b$\u0001$\u0001$\u0003$\u02e1\b$\u0001$\u0001$\u0001$\u0003"+
		"$\u02e6\b$\u0001$\u0001$\u0003$\u02ea\b$\u0001$\u0003$\u02ed\b$\u0001"+
		"%\u0001%\u0001&\u0001&\u0005&\u02f3\b&\n&\f&\u02f6\t&\u0001&\u0005&\u02f9"+
		"\b&\n&\f&\u02fc\t&\u0001&\u0003&\u02ff\b&\u0001&\u0001&\u0005&\u0303\b"+
		"&\n&\f&\u0306\t&\u0001&\u0003&\u0309\b&\u0001&\u0004&\u030c\b&\u000b&"+
		"\f&\u030d\u0001&\u0005&\u0311\b&\n&\f&\u0314\t&\u0001&\u0003&\u0317\b"+
		"&\u0001&\u0004&\u031a\b&\u000b&\f&\u031b\u0001&\u0003&\u031f\b&\u0001"+
		"&\u0003&\u0322\b&\u0001\'\u0004\'\u0325\b\'\u000b\'\f\'\u0326\u0001\'"+
		"\u0001\'\u0003\'\u032b\b\'\u0001(\u0005(\u032e\b(\n(\f(\u0331\t(\u0001"+
		"(\u0004(\u0334\b(\u000b(\f(\u0335\u0001(\u0001(\u0003(\u033a\b(\u0001"+
		")\u0001)\u0001)\u0005)\u033f\b)\n)\f)\u0342\t)\u0001)\u0003)\u0345\b)"+
		"\u0001)\u0001)\u0001)\u0005)\u034a\b)\n)\f)\u034d\t)\u0001)\u0003)\u0350"+
		"\b)\u0001)\u0001)\u0001)\u0004)\u0355\b)\u000b)\f)\u0356\u0001)\u0003"+
		")\u035a\b)\u0001)\u0003)\u035d\b)\u0001*\u0001*\u0001*\u0001+\u0001+\u0003"+
		"+\u0364\b+\u0001+\u0003+\u0367\b+\u0001,\u0001,\u0003,\u036b\b,\u0001"+
		",\u0003,\u036e\b,\u0001-\u0001-\u0001-\u0003-\u0373\b-\u0001-\u0003-\u0376"+
		"\b-\u0001.\u0001.\u0003.\u037a\b.\u0001.\u0003.\u037d\b.\u0001.\u0003"+
		".\u0380\b.\u0001/\u0001/\u0003/\u0384\b/\u00010\u00010\u00010\u00011\u0001"+
		"1\u00011\u00012\u00012\u00012\u00013\u00013\u00013\u00014\u00014\u0001"+
		"4\u00014\u00014\u00014\u00034\u0398\b4\u00034\u039a\b4\u00015\u00015\u0001"+
		"5\u00015\u00015\u00015\u00035\u03a2\b5\u00035\u03a4\b5\u00016\u00016\u0001"+
		"6\u00016\u00017\u00017\u00017\u00017\u00017\u00037\u03af\b7\u00018\u0003"+
		"8\u03b2\b8\u00018\u00018\u00018\u00018\u00018\u00018\u00038\u03ba\b8\u0001"+
		"8\u00018\u00038\u03be\b8\u00019\u00039\u03c1\b9\u00019\u00019\u00019\u0001"+
		"9\u00019\u00059\u03c8\b9\n9\f9\u03cb\t9\u00019\u00039\u03ce\b9\u00019"+
		"\u00019\u00019\u00019\u00019\u00019\u00059\u03d6\b9\n9\f9\u03d9\t9\u0001"+
		"9\u00019\u00039\u03dd\b9\u00039\u03df\b9\u00019\u00019\u0001:\u0001:\u0001"+
		":\u0003:\u03e6\b:\u0001;\u0001;\u0001;\u0001;\u0001;\u0001;\u0001;\u0001"+
		";\u0001;\u0004;\u03f1\b;\u000b;\f;\u03f2\u0001;\u0003;\u03f6\b;\u0001"+
		";\u0003;\u03f9\b;\u0001;\u0001;\u0001;\u0001;\u0004;\u03ff\b;\u000b;\f"+
		";\u0400\u0001;\u0003;\u0404\b;\u0001;\u0003;\u0407\b;\u0003;\u0409\b;"+
		"\u0001<\u0001<\u0001<\u0001<\u0003<\u040f\b<\u0003<\u0411\b<\u0001<\u0001"+
		"<\u0001<\u0001=\u0001=\u0001=\u0001=\u0001=\u0003=\u041b\b=\u0001=\u0001"+
		"=\u0001=\u0001>\u0001>\u0001>\u0001>\u0001?\u0001?\u0001?\u0001?\u0001"+
		"?\u0001?\u0004?\u042a\b?\u000b?\f?\u042b\u0001?\u0001?\u0001@\u0001@\u0001"+
		"@\u0003@\u0433\b@\u0001@\u0003@\u0436\b@\u0001A\u0001A\u0001A\u0003A\u043b"+
		"\bA\u0001A\u0001A\u0001A\u0001B\u0001B\u0001B\u0001C\u0001C\u0003C\u0445"+
		"\bC\u0001D\u0001D\u0003D\u0449\bD\u0001E\u0001E\u0001E\u0001E\u0001F\u0001"+
		"F\u0001F\u0005F\u0452\bF\nF\fF\u0455\tF\u0001G\u0001G\u0001G\u0001G\u0001"+
		"G\u0001G\u0001G\u0001G\u0003G\u045f\bG\u0001H\u0001H\u0001H\u0001H\u0001"+
		"H\u0001H\u0001H\u0003H\u0468\bH\u0001I\u0001I\u0001I\u0001I\u0001I\u0001"+
		"I\u0001I\u0003I\u0471\bI\u0001J\u0003J\u0474\bJ\u0001J\u0001J\u0001J\u0001"+
		"K\u0001K\u0001K\u0001K\u0001L\u0003L\u047e\bL\u0001L\u0001L\u0001M\u0003"+
		"M\u0483\bM\u0001M\u0001M\u0001N\u0001N\u0001O\u0001O\u0001P\u0001P\u0001"+
		"Q\u0001Q\u0001R\u0001R\u0001S\u0001S\u0001T\u0001T\u0001T\u0004T\u0496"+
		"\bT\u000bT\fT\u0497\u0001U\u0001U\u0001U\u0005U\u049d\bU\nU\fU\u04a0\t"+
		"U\u0001V\u0001V\u0001V\u0001V\u0001W\u0001W\u0003W\u04a8\bW\u0001W\u0001"+
		"W\u0001W\u0003W\u04ad\bW\u0001W\u0003W\u04b0\bW\u0001X\u0001X\u0001X\u0003"+
		"X\u04b5\bX\u0001Y\u0001Y\u0001Y\u0005Y\u04ba\bY\nY\fY\u04bd\tY\u0001Y"+
		"\u0003Y\u04c0\bY\u0001Z\u0001Z\u0003Z\u04c4\bZ\u0001[\u0001[\u0001[\u0001"+
		"[\u0003[\u04ca\b[\u0001\\\u0001\\\u0001\\\u0001\\\u0001\\\u0003\\\u04d1"+
		"\b\\\u0001\\\u0001\\\u0001\\\u0001\\\u0001\\\u0001\\\u0003\\\u04d9\b\\"+
		"\u0001\\\u0003\\\u04dc\b\\\u0001\\\u0001\\\u0003\\\u04e0\b\\\u0001]\u0001"+
		"]\u0001]\u0005]\u04e5\b]\n]\f]\u04e8\t]\u0001^\u0001^\u0003^\u04ec\b^"+
		"\u0001^\u0001^\u0001^\u0001_\u0001_\u0001_\u0001`\u0001`\u0001`\u0001"+
		"`\u0001`\u0003`\u04f9\b`\u0001`\u0003`\u04fc\b`\u0001`\u0003`\u04ff\b"+
		"`\u0003`\u0501\b`\u0001`\u0001`\u0001a\u0001a\u0001a\u0005a\u0508\ba\n"+
		"a\fa\u050b\ta\u0001b\u0001b\u0001b\u0005b\u0510\bb\nb\fb\u0513\tb\u0001"+
		"c\u0001c\u0001c\u0001c\u0001d\u0001d\u0001d\u0003d\u051c\bd\u0001d\u0001"+
		"d\u0001d\u0001e\u0001e\u0001e\u0001e\u0001f\u0001f\u0001f\u0005f\u0528"+
		"\bf\nf\ff\u052b\tf\u0001f\u0003f\u052e\bf\u0001g\u0001g\u0003g\u0532\b"+
		"g\u0001g\u0001g\u0001g\u0001g\u0003g\u0538\bg\u0001g\u0001g\u0001g\u0001"+
		"g\u0003g\u053e\bg\u0003g\u0540\bg\u0001h\u0001h\u0001h\u0001i\u0001i\u0001"+
		"i\u0005i\u0548\bi\ni\fi\u054b\ti\u0001i\u0003i\u054e\bi\u0001j\u0001j"+
		"\u0001j\u0001j\u0001j\u0001j\u0003j\u0556\bj\u0001j\u0003j\u0559\bj\u0001"+
		"k\u0001k\u0001k\u0001k\u0003k\u055f\bk\u0003k\u0561\bk\u0001l\u0001l\u0001"+
		"l\u0005l\u0566\bl\nl\fl\u0569\tl\u0001l\u0003l\u056c\bl\u0001m\u0001m"+
		"\u0001m\u0003m\u0571\bm\u0001n\u0001n\u0001n\u0005n\u0576\bn\nn\fn\u0579"+
		"\tn\u0001n\u0003n\u057c\bn\u0001o\u0001o\u0001o\u0003o\u0581\bo\u0001"+
		"p\u0001p\u0001p\u0001p\u0001q\u0001q\u0003q\u0589\bq\u0001r\u0001r\u0001"+
		"r\u0005r\u058e\br\nr\fr\u0591\tr\u0001s\u0001s\u0001s\u0005s\u0596\bs"+
		"\ns\fs\u0599\ts\u0001t\u0001t\u0001t\u0003t\u059e\bt\u0001u\u0001u\u0005"+
		"u\u05a2\bu\nu\fu\u05a5\tu\u0001v\u0001v\u0001v\u0001v\u0001v\u0001v\u0001"+
		"v\u0001v\u0001v\u0001v\u0003v\u05b1\bv\u0001w\u0001w\u0001w\u0001x\u0001"+
		"x\u0001x\u0001y\u0001y\u0001y\u0001z\u0001z\u0001z\u0001{\u0001{\u0001"+
		"{\u0001|\u0001|\u0001|\u0001}\u0001}\u0001}\u0001}\u0001~\u0001~\u0001"+
		"~\u0001\u007f\u0001\u007f\u0001\u007f\u0001\u007f\u0001\u0080\u0001\u0080"+
		"\u0001\u0080\u0001\u0081\u0001\u0081\u0001\u0081\u0001\u0081\u0001\u0081"+
		"\u0001\u0081\u0005\u0081\u05d9\b\u0081\n\u0081\f\u0081\u05dc\t\u0081\u0001"+
		"\u0082\u0001\u0082\u0001\u0082\u0001\u0082\u0001\u0082\u0001\u0082\u0005"+
		"\u0082\u05e4\b\u0082\n\u0082\f\u0082\u05e7\t\u0082\u0001\u0083\u0001\u0083"+
		"\u0001\u0083\u0001\u0083\u0001\u0083\u0001\u0083\u0005\u0083\u05ef\b\u0083"+
		"\n\u0083\f\u0083\u05f2\t\u0083\u0001\u0084\u0001\u0084\u0001\u0084\u0001"+
		"\u0084\u0001\u0084\u0001\u0084\u0005\u0084\u05fa\b\u0084\n\u0084\f\u0084"+
		"\u05fd\t\u0084\u0001\u0085\u0001\u0085\u0001\u0085\u0001\u0085\u0001\u0085"+
		"\u0001\u0085\u0005\u0085\u0605\b\u0085\n\u0085\f\u0085\u0608\t\u0085\u0001"+
		"\u0086\u0001\u0086\u0001\u0086\u0001\u0086\u0001\u0086\u0001\u0086\u0005"+
		"\u0086\u0610\b\u0086\n\u0086\f\u0086\u0613\t\u0086\u0001\u0087\u0001\u0087"+
		"\u0001\u0087\u0001\u0087\u0001\u0087\u0001\u0087\u0005\u0087\u061b\b\u0087"+
		"\n\u0087\f\u0087\u061e\t\u0087\u0001\u0088\u0001\u0088\u0001\u0088\u0001"+
		"\u0088\u0001\u0088\u0001\u0088\u0001\u0088\u0003\u0088\u0627\b\u0088\u0001"+
		"\u0089\u0001\u0089\u0001\u0089\u0003\u0089\u062c\b\u0089\u0001\u008a\u0001"+
		"\u008a\u0001\u008a\u0003\u008a\u0631\b\u008a\u0001\u008b\u0001\u008b\u0001"+
		"\u008b\u0001\u008b\u0001\u008b\u0001\u008b\u0001\u008b\u0001\u008b\u0001"+
		"\u008b\u0003\u008b\u063c\b\u008b\u0001\u008b\u0001\u008b\u0001\u008b\u0001"+
		"\u008b\u0001\u008b\u0003\u008b\u0643\b\u008b\u0005\u008b\u0645\b\u008b"+
		"\n\u008b\f\u008b\u0648\t\u008b\u0001\u008c\u0001\u008c\u0001\u008c\u0003"+
		"\u008c\u064d\b\u008c\u0001\u008c\u0001\u008c\u0001\u008c\u0003\u008c\u0652"+
		"\b\u008c\u0005\u008c\u0654\b\u008c\n\u008c\f\u008c\u0657\t\u008c\u0001"+
		"\u008c\u0003\u008c\u065a\b\u008c\u0003\u008c\u065c\b\u008c\u0001\u008d"+
		"\u0003\u008d\u065f\b\u008d\u0001\u008d\u0001\u008d\u0003\u008d\u0663\b"+
		"\u008d\u0001\u008d\u0001\u008d\u0003\u008d\u0667\b\u008d\u0003\u008d\u0669"+
		"\b\u008d\u0001\u008d\u0003\u008d\u066c\b\u008d\u0001\u008e\u0001\u008e"+
		"\u0001\u008e\u0001\u008e\u0001\u008e\u0001\u008e\u0001\u008e\u0001\u008e"+
		"\u0001\u008e\u0001\u008e\u0003\u008e\u0678\b\u008e\u0001\u008e\u0001\u008e"+
		"\u0003\u008e\u067c\b\u008e\u0001\u008e\u0001\u008e\u0001\u008e\u0001\u008e"+
		"\u0003\u008e\u0682\b\u008e\u0001\u008e\u0003\u008e\u0685\b\u008e\u0001"+
		"\u008f\u0001\u008f\u0001\u008f\u0001\u0090\u0001\u0090\u0001\u0090\u0003"+
		"\u0090\u068d\b\u0090\u0001\u0090\u0001\u0090\u0001\u0091\u0001\u0091\u0003"+
		"\u0091\u0693\b\u0091\u0001\u0091\u0001\u0091\u0001\u0091\u0001\u0092\u0001"+
		"\u0092\u0001\u0093\u0001\u0093\u0005\u0093\u069c\b\u0093\n\u0093\f\u0093"+
		"\u069f\t\u0093\u0001\u0093\u0005\u0093\u06a2\b\u0093\n\u0093\f\u0093\u06a5"+
		"\t\u0093\u0001\u0093\u0003\u0093\u06a8\b\u0093\u0001\u0093\u0001\u0093"+
		"\u0005\u0093\u06ac\b\u0093\n\u0093\f\u0093\u06af\t\u0093\u0001\u0093\u0003"+
		"\u0093\u06b2\b\u0093\u0001\u0093\u0004\u0093\u06b5\b\u0093\u000b\u0093"+
		"\f\u0093\u06b6\u0001\u0093\u0005\u0093\u06ba\b\u0093\n\u0093\f\u0093\u06bd"+
		"\t\u0093\u0001\u0093\u0003\u0093\u06c0\b\u0093\u0001\u0093\u0004\u0093"+
		"\u06c3\b\u0093\u000b\u0093\f\u0093\u06c4\u0001\u0093\u0003\u0093\u06c8"+
		"\b\u0093\u0001\u0093\u0003\u0093\u06cb\b\u0093\u0001\u0094\u0004\u0094"+
		"\u06ce\b\u0094\u000b\u0094\f\u0094\u06cf\u0001\u0094\u0001\u0094\u0003"+
		"\u0094\u06d4\b\u0094\u0001\u0095\u0005\u0095\u06d7\b\u0095\n\u0095\f\u0095"+
		"\u06da\t\u0095\u0001\u0095\u0004\u0095\u06dd\b\u0095\u000b\u0095\f\u0095"+
		"\u06de\u0001\u0095\u0001\u0095\u0003\u0095\u06e3\b\u0095\u0001\u0096\u0001"+
		"\u0096\u0001\u0096\u0005\u0096\u06e8\b\u0096\n\u0096\f\u0096\u06eb\t\u0096"+
		"\u0001\u0096\u0003\u0096\u06ee\b\u0096\u0001\u0096\u0001\u0096\u0001\u0096"+
		"\u0004\u0096\u06f3\b\u0096\u000b\u0096\f\u0096\u06f4\u0001\u0096\u0003"+
		"\u0096\u06f8\b\u0096\u0001\u0096\u0003\u0096\u06fb\b\u0096\u0001\u0097"+
		"\u0001\u0097\u0001\u0097\u0001\u0098\u0001\u0098\u0003\u0098\u0702\b\u0098"+
		"\u0001\u0099\u0001\u0099\u0001\u0099\u0003\u0099\u0707\b\u0099\u0001\u009a"+
		"\u0001\u009a\u0003\u009a\u070b\b\u009a\u0001\u009a\u0003\u009a\u070e\b"+
		"\u009a\u0001\u009b\u0001\u009b\u0001\u009c\u0001\u009c\u0003\u009c\u0714"+
		"\b\u009c\u0001\u009d\u0001\u009d\u0001\u009d\u0003\u009d\u0719\b\u009d"+
		"\u0001\u009d\u0003\u009d\u071c\b\u009d\u0001\u009d\u0003\u009d\u071f\b"+
		"\u009d\u0001\u009d\u0003\u009d\u0722\b\u009d\u0001\u009d\u0001\u009d\u0001"+
		"\u009e\u0001\u009e\u0001\u009e\u0001\u009f\u0001\u009f\u0005\u009f\u072b"+
		"\b\u009f\n\u009f\f\u009f\u072e\t\u009f\u0001\u00a0\u0001\u00a0\u0003\u00a0"+
		"\u0732\b\u00a0\u0001\u00a1\u0001\u00a1\u0005\u00a1\u0736\b\u00a1\n\u00a1"+
		"\f\u00a1\u0739\t\u00a1\u0001\u00a1\u0001\u00a1\u0001\u00a2\u0001\u00a2"+
		"\u0001\u00a3\u0001\u00a3\u0004\u00a3\u0741\b\u00a3\u000b\u00a3\f\u00a3"+
		"\u0742\u0001\u00a4\u0001\u00a4\u0003\u00a4\u0747\b\u00a4\u0001\u00a4\u0001"+
		"\u00a4\u0001\u00a5\u0001\u00a5\u0001\u00a5\u0001\u00a5\u0003\u00a5\u074f"+
		"\b\u00a5\u0003\u00a5\u0751\b\u00a5\u0001\u00a5\u0001\u00a5\u0001\u00a6"+
		"\u0001\u00a6\u0001\u00a6\u0001\u00a6\u0001\u00a7\u0001\u00a7\u0003\u00a7"+
		"\u075b\b\u00a7\u0001\u00a7\u0001\u00a7\u0001\u00a8\u0001\u00a8\u0001\u00a8"+
		"\u0005\u00a8\u0762\b\u00a8\n\u00a8\f\u00a8\u0765\t\u00a8\u0001\u00a8\u0003"+
		"\u00a8\u0768\b\u00a8\u0001\u00a9\u0001\u00a9\u0001\u00a9\u0003\u00a9\u076d"+
		"\b\u00a9\u0001\u00aa\u0001\u00aa\u0001\u00aa\u0001\u00aa\u0001\u00ab\u0004"+
		"\u00ab\u0774\b\u00ab\u000b\u00ab\f\u00ab\u0775\u0001\u00ac\u0003\u00ac"+
		"\u0779\b\u00ac\u0001\u00ac\u0001\u00ac\u0001\u00ac\u0001\u00ac\u0001\u00ac"+
		"\u0001\u00ac\u0005\u00ac\u0781\b\u00ac\n\u00ac\f\u00ac\u0784\t\u00ac\u0001"+
		"\u00ad\u0001\u00ad\u0001\u00ad\u0001\u00ad\u0001\u00ad\u0001\u00ae\u0001"+
		"\u00ae\u0001\u00ae\u0001\u00ae\u0001\u00ae\u0001\u00af\u0001\u00af\u0001"+
		"\u00af\u0003\u00af\u0793\b\u00af\u0001\u00af\u0001\u00af\u0001\u00af\u0001"+
		"\u00b0\u0001\u00b0\u0001\u00b0\u0001\u00b0\u0001\u00b0\u0001\u00b1\u0001"+
		"\u00b1\u0003\u00b1\u079f\b\u00b1\u0001\u00b2\u0001\u00b2\u0001\u00b2\u0003"+
		"\u00b2\u07a4\b\u00b2\u0003\u00b2\u07a6\b\u00b2\u0001\u00b2\u0001\u00b2"+
		"\u0001\u00b2\u0001\u00b2\u0003\u00b2\u07ac\b\u00b2\u0003\u00b2\u07ae\b"+
		"\u00b2\u0005\u00b2\u07b0\b\u00b2\n\u00b2\f\u00b2\u07b3\t\u00b2\u0001\u00b2"+
		"\u0001\u00b2\u0003\u00b2\u07b7\b\u00b2\u0001\u00b2\u0003\u00b2\u07ba\b"+
		"\u00b2\u0001\u00b3\u0001\u00b3\u0001\u00b3\u0005\u00b3\u07bf\b\u00b3\n"+
		"\u00b3\f\u00b3\u07c2\t\u00b3\u0001\u00b3\u0001\u00b3\u0001\u00b3\u0001"+
		"\u00b3\u0005\u00b3\u07c8\b\u00b3\n\u00b3\f\u00b3\u07cb\t\u00b3\u0003\u00b3"+
		"\u07cd\b\u00b3\u0001\u00b3\u0001\u00b3\u0001\u00b3\u0005\u00b3\u07d2\b"+
		"\u00b3\n\u00b3\f\u00b3\u07d5\t\u00b3\u0003\u00b3\u07d7\b\u00b3\u0001\u00b4"+
		"\u0001\u00b4\u0001\u00b4\u0001\u00b5\u0001\u00b5\u0001\u00b5\u0001\u00b5"+
		"\u0003\u00b5\u07e0\b\u00b5\u0001\u00b6\u0001\u00b6\u0001\u00b6\u0001\u00b6"+
		"\u0001\u00b6\u0003\u00b6\u07e7\b\u00b6\u0001\u00b7\u0001\u00b7\u0001\u00b7"+
		"\u0005\u00b7\u07ec\b\u00b7\n\u00b7\f\u00b7\u07ef\t\u00b7\u0001\u00b7\u0003"+
		"\u00b7\u07f2\b\u00b7\u0001\u00b8\u0001\u00b8\u0001\u00b8\u0004\u00b8\u07f7"+
		"\b\u00b8\u000b\u00b8\f\u00b8\u07f8\u0001\u00b8\u0003\u00b8\u07fc\b\u00b8"+
		"\u0001\u00b9\u0001\u00b9\u0001\u00b9\u0001\u00b9\u0004\u00b9\u0802\b\u00b9"+
		"\u000b\u00b9\f\u00b9\u0803\u0001\u00b9\u0003\u00b9\u0807\b\u00b9\u0003"+
		"\u00b9\u0809\b\u00b9\u0001\u00ba\u0001\u00ba\u0001\u00ba\u0003\u00ba\u080e"+
		"\b\u00ba\u0001\u00bb\u0001\u00bb\u0001\u00bb\u0001\u00bb\u0001\u00bb\u0001"+
		"\u00bb\u0001\u00bb\u0003\u00bb\u0817\b\u00bb\u0001\u00bb\u0003\u00bb\u081a"+
		"\b\u00bb\u0001\u00bc\u0001\u00bc\u0001\u00bc\u0001\u00bc\u0001\u00bc\u0001"+
		"\u00bc\u0001\u00bc\u0003\u00bc\u0823\b\u00bc\u0001\u00bc\u0001\u00bc\u0001"+
		"\u00bc\u0003\u00bc\u0828\b\u00bc\u0001\u00bc\u0003\u00bc\u082b\b\u00bc"+
		"\u0001\u00bd\u0001\u00bd\u0001\u00bd\u0001\u00bd\u0001\u00bd\u0001\u00bd"+
		"\u0003\u00bd\u0833\b\u00bd\u0001\u00be\u0001\u00be\u0001\u00be\u0001\u00be"+
		"\u0001\u00be\u0001\u00be\u0001\u00be\u0003\u00be\u083c\b\u00be\u0001\u00bf"+
		"\u0001\u00bf\u0001\u00bf\u0001\u00bf\u0001\u00bf\u0001\u00bf\u0001\u00bf"+
		"\u0001\u00bf\u0001\u00bf\u0001\u00bf\u0001\u00bf\u0001\u00bf\u0001\u00bf"+
		"\u0003\u00bf\u084b\b\u00bf\u0001\u00bf\u0003\u00bf\u084e\b\u00bf\u0005"+
		"\u00bf\u0850\b\u00bf\n\u00bf\f\u00bf\u0853\t\u00bf\u0001\u00c0\u0001\u00c0"+
		"\u0001\u00c0\u0005\u00c0\u0858\b\u00c0\n\u00c0\f\u00c0\u085b\t\u00c0\u0001"+
		"\u00c0\u0003\u00c0\u085e\b\u00c0\u0001\u00c1\u0001\u00c1\u0001\u00c1\u0001"+
		"\u00c1\u0001\u00c1\u0001\u00c1\u0001\u00c1\u0003\u00c1\u0867\b\u00c1\u0001"+
		"\u00c1\u0003\u00c1\u086a\b\u00c1\u0001\u00c2\u0001\u00c2\u0001\u00c2\u0001"+
		"\u00c2\u0001\u00c2\u0001\u00c2\u0001\u00c2\u0003\u00c2\u0873\b\u00c2\u0001"+
		"\u00c2\u0001\u00c2\u0001\u00c2\u0003\u00c2\u0878\b\u00c2\u0001\u00c2\u0003"+
		"\u00c2\u087b\b\u00c2\u0001\u00c3\u0001\u00c3\u0001\u00c3\u0005\u00c3\u0880"+
		"\b\u00c3\n\u00c3\f\u00c3\u0883\t\u00c3\u0001\u00c3\u0001\u00c3\u0001\u00c3"+
		"\u0001\u00c3\u0001\u00c3\u0001\u00c3\u0003\u00c3\u088b\b\u00c3\u0001\u00c3"+
		"\u0001\u00c3\u0003\u00c3\u088f\b\u00c3\u0003\u00c3\u0891\b\u00c3\u0001"+
		"\u00c3\u0001\u00c3\u0001\u00c3\u0001\u00c3\u0001\u00c3\u0003\u00c3\u0898"+
		"\b\u00c3\u0001\u00c3\u0001\u00c3\u0003\u00c3\u089c\b\u00c3\u0001\u00c4"+
		"\u0001\u00c4\u0001\u00c4\u0003\u00c4\u08a1\b\u00c4\u0001\u00c5\u0001\u00c5"+
		"\u0001\u00c5\u0001\u00c6\u0001\u00c6\u0001\u00c6\u0001\u00c7\u0001\u00c7"+
		"\u0001\u00c7\u0001\u00c8\u0001\u00c8\u0001\u00c8\u0001\u00c9\u0001\u00c9"+
		"\u0001\u00c9\u0001\u00c9\u0000\n<\u0102\u0104\u0106\u0108\u010a\u010c"+
		"\u010e\u0116\u017e\u00ca\u0000\u0002\u0004\u0006\b\n\f\u000e\u0010\u0012"+
		"\u0014\u0016\u0018\u001a\u001c\u001e \"$&(*,.02468:<>@BDFHJLNPRTVXZ\\"+
		"^`bdfhjlnprtvxz|~\u0080\u0082\u0084\u0086\u0088\u008a\u008c\u008e\u0090"+
		"\u0092\u0094\u0096\u0098\u009a\u009c\u009e\u00a0\u00a2\u00a4\u00a6\u00a8"+
		"\u00aa\u00ac\u00ae\u00b0\u00b2\u00b4\u00b6\u00b8\u00ba\u00bc\u00be\u00c0"+
		"\u00c2\u00c4\u00c6\u00c8\u00ca\u00cc\u00ce\u00d0\u00d2\u00d4\u00d6\u00d8"+
		"\u00da\u00dc\u00de\u00e0\u00e2\u00e4\u00e6\u00e8\u00ea\u00ec\u00ee\u00f0"+
		"\u00f2\u00f4\u00f6\u00f8\u00fa\u00fc\u00fe\u0100\u0102\u0104\u0106\u0108"+
		"\u010a\u010c\u010e\u0110\u0112\u0114\u0116\u0118\u011a\u011c\u011e\u0120"+
		"\u0122\u0124\u0126\u0128\u012a\u012c\u012e\u0130\u0132\u0134\u0136\u0138"+
		"\u013a\u013c\u013e\u0140\u0142\u0144\u0146\u0148\u014a\u014c\u014e\u0150"+
		"\u0152\u0154\u0156\u0158\u015a\u015c\u015e\u0160\u0162\u0164\u0166\u0168"+
		"\u016a\u016c\u016e\u0170\u0172\u0174\u0176\u0178\u017a\u017c\u017e\u0180"+
		"\u0182\u0184\u0186\u0188\u018a\u018c\u018e\u0190\u0192\u0000\u0007\u0003"+
		"\u0000HRTTVV\u0002\u000011XX\u0002\u0000]]__\u0001\u000056\u0001\u0000"+
		"EF\u0004\u000078>>SSUU\u0002\u0000**[\\\u0961\u0000\u0195\u0001\u0000"+
		"\u0000\u0000\u0002\u0199\u0001\u0000\u0000\u0000\u0004\u019b\u0001\u0000"+
		"\u0000\u0000\u0006\u01a4\u0001\u0000\u0000\u0000\b\u01b3\u0001\u0000\u0000"+
		"\u0000\n\u01b6\u0001\u0000\u0000\u0000\f\u01bc\u0001\u0000\u0000\u0000"+
		"\u000e\u01c4\u0001\u0000\u0000\u0000\u0010\u01c6\u0001\u0000\u0000\u0000"+
		"\u0012\u01e2\u0001\u0000\u0000\u0000\u0014\u01ec\u0001\u0000\u0000\u0000"+
		"\u0016\u0216\u0001\u0000\u0000\u0000\u0018\u021a\u0001\u0000\u0000\u0000"+
		"\u001a\u021c\u0001\u0000\u0000\u0000\u001c\u021e\u0001\u0000\u0000\u0000"+
		"\u001e\u0222\u0001\u0000\u0000\u0000 \u022a\u0001\u0000\u0000\u0000\""+
		"\u0233\u0001\u0000\u0000\u0000$\u023c\u0001\u0000\u0000\u0000&\u023f\u0001"+
		"\u0000\u0000\u0000(\u0241\u0001\u0000\u0000\u0000*\u0249\u0001\u0000\u0000"+
		"\u0000,\u024b\u0001\u0000\u0000\u0000.\u0252\u0001\u0000\u0000\u00000"+
		"\u0268\u0001\u0000\u0000\u00002\u0273\u0001\u0000\u0000\u00004\u0275\u0001"+
		"\u0000\u0000\u00006\u027d\u0001\u0000\u0000\u00008\u0282\u0001\u0000\u0000"+
		"\u0000:\u028a\u0001\u0000\u0000\u0000<\u028f\u0001\u0000\u0000\u0000>"+
		"\u02a0\u0001\u0000\u0000\u0000@\u02a6\u0001\u0000\u0000\u0000B\u02ae\u0001"+
		"\u0000\u0000\u0000D\u02b0\u0001\u0000\u0000\u0000F\u02c3\u0001\u0000\u0000"+
		"\u0000H\u02ec\u0001\u0000\u0000\u0000J\u02ee\u0001\u0000\u0000\u0000L"+
		"\u0321\u0001\u0000\u0000\u0000N\u0324\u0001\u0000\u0000\u0000P\u032f\u0001"+
		"\u0000\u0000\u0000R\u035c\u0001\u0000\u0000\u0000T\u035e\u0001\u0000\u0000"+
		"\u0000V\u0361\u0001\u0000\u0000\u0000X\u0368\u0001\u0000\u0000\u0000Z"+
		"\u036f\u0001\u0000\u0000\u0000\\\u0377\u0001\u0000\u0000\u0000^\u0381"+
		"\u0001\u0000\u0000\u0000`\u0385\u0001\u0000\u0000\u0000b\u0388\u0001\u0000"+
		"\u0000\u0000d\u038b\u0001\u0000\u0000\u0000f\u038e\u0001\u0000\u0000\u0000"+
		"h\u0391\u0001\u0000\u0000\u0000j\u039b\u0001\u0000\u0000\u0000l\u03a5"+
		"\u0001\u0000\u0000\u0000n\u03a9\u0001\u0000\u0000\u0000p\u03b1\u0001\u0000"+
		"\u0000\u0000r\u03c0\u0001\u0000\u0000\u0000t\u03e2\u0001\u0000\u0000\u0000"+
		"v\u0408\u0001\u0000\u0000\u0000x\u040a\u0001\u0000\u0000\u0000z\u0415"+
		"\u0001\u0000\u0000\u0000|\u041f\u0001\u0000\u0000\u0000~\u0423\u0001\u0000"+
		"\u0000\u0000\u0080\u0435\u0001\u0000\u0000\u0000\u0082\u0437\u0001\u0000"+
		"\u0000\u0000\u0084\u043f\u0001\u0000\u0000\u0000\u0086\u0444\u0001\u0000"+
		"\u0000\u0000\u0088\u0448\u0001\u0000\u0000\u0000\u008a\u044a\u0001\u0000"+
		"\u0000\u0000\u008c\u044e\u0001\u0000\u0000\u0000\u008e\u045e\u0001\u0000"+
		"\u0000\u0000\u0090\u0467\u0001\u0000\u0000\u0000\u0092\u0470\u0001\u0000"+
		"\u0000\u0000\u0094\u0473\u0001\u0000\u0000\u0000\u0096\u0478\u0001\u0000"+
		"\u0000\u0000\u0098\u047d\u0001\u0000\u0000\u0000\u009a\u0482\u0001\u0000"+
		"\u0000\u0000\u009c\u0486\u0001\u0000\u0000\u0000\u009e\u0488\u0001\u0000"+
		"\u0000\u0000\u00a0\u048a\u0001\u0000\u0000\u0000\u00a2\u048c\u0001\u0000"+
		"\u0000\u0000\u00a4\u048e\u0001\u0000\u0000\u0000\u00a6\u0490\u0001\u0000"+
		"\u0000\u0000\u00a8\u0492\u0001\u0000\u0000\u0000\u00aa\u0499\u0001\u0000"+
		"\u0000\u0000\u00ac\u04a1\u0001\u0000\u0000\u0000\u00ae\u04af\u0001\u0000"+
		"\u0000\u0000\u00b0\u04b1\u0001\u0000\u0000\u0000\u00b2\u04b6\u0001\u0000"+
		"\u0000\u0000\u00b4\u04c3\u0001\u0000\u0000\u0000\u00b6\u04c9\u0001\u0000"+
		"\u0000\u0000\u00b8\u04df\u0001\u0000\u0000\u0000\u00ba\u04e1\u0001\u0000"+
		"\u0000\u0000\u00bc\u04eb\u0001\u0000\u0000\u0000\u00be\u04f0\u0001\u0000"+
		"\u0000\u0000\u00c0\u04f3\u0001\u0000\u0000\u0000\u00c2\u0504\u0001\u0000"+
		"\u0000\u0000\u00c4\u050c\u0001\u0000\u0000\u0000\u00c6\u0514\u0001\u0000"+
		"\u0000\u0000\u00c8\u0518\u0001\u0000\u0000\u0000\u00ca\u0520\u0001\u0000"+
		"\u0000\u0000\u00cc\u0524\u0001\u0000\u0000\u0000\u00ce\u053f\u0001\u0000"+
		"\u0000\u0000\u00d0\u0541\u0001\u0000\u0000\u0000\u00d2\u0544\u0001\u0000"+
		"\u0000\u0000\u00d4\u0558\u0001\u0000\u0000\u0000\u00d6\u055a\u0001\u0000"+
		"\u0000\u0000\u00d8\u0562\u0001\u0000\u0000\u0000\u00da\u0570\u0001\u0000"+
		"\u0000\u0000\u00dc\u0572\u0001\u0000\u0000\u0000\u00de\u0580\u0001\u0000"+
		"\u0000\u0000\u00e0\u0582\u0001\u0000\u0000\u0000\u00e2\u0588\u0001\u0000"+
		"\u0000\u0000\u00e4\u058a\u0001\u0000\u0000\u0000\u00e6\u0592\u0001\u0000"+
		"\u0000\u0000\u00e8\u059d\u0001\u0000\u0000\u0000\u00ea\u059f\u0001\u0000"+
		"\u0000\u0000\u00ec\u05b0\u0001\u0000\u0000\u0000\u00ee\u05b2\u0001\u0000"+
		"\u0000\u0000\u00f0\u05b5\u0001\u0000\u0000\u0000\u00f2\u05b8\u0001\u0000"+
		"\u0000\u0000\u00f4\u05bb\u0001\u0000\u0000\u0000\u00f6\u05be\u0001\u0000"+
		"\u0000\u0000\u00f8\u05c1\u0001\u0000\u0000\u0000\u00fa\u05c4\u0001\u0000"+
		"\u0000\u0000\u00fc\u05c8\u0001\u0000\u0000\u0000\u00fe\u05cb\u0001\u0000"+
		"\u0000\u0000\u0100\u05cf\u0001\u0000\u0000\u0000\u0102\u05d2\u0001\u0000"+
		"\u0000\u0000\u0104\u05dd\u0001\u0000\u0000\u0000\u0106\u05e8\u0001\u0000"+
		"\u0000\u0000\u0108\u05f3\u0001\u0000\u0000\u0000\u010a\u05fe\u0001\u0000"+
		"\u0000\u0000\u010c\u0609\u0001\u0000\u0000\u0000\u010e\u0614\u0001\u0000"+
		"\u0000\u0000\u0110\u0626\u0001\u0000\u0000\u0000\u0112\u0628\u0001\u0000"+
		"\u0000\u0000\u0114\u0630\u0001\u0000\u0000\u0000\u0116\u0632\u0001\u0000"+
		"\u0000\u0000\u0118\u065b\u0001\u0000\u0000\u0000\u011a\u066b\u0001\u0000"+
		"\u0000\u0000\u011c\u0684\u0001\u0000\u0000\u0000\u011e\u0686\u0001\u0000"+
		"\u0000\u0000\u0120\u0689\u0001\u0000\u0000\u0000\u0122\u0690\u0001\u0000"+
		"\u0000\u0000\u0124\u0697\u0001\u0000\u0000\u0000\u0126\u06ca\u0001\u0000"+
		"\u0000\u0000\u0128\u06cd\u0001\u0000\u0000\u0000\u012a\u06d8\u0001\u0000"+
		"\u0000\u0000\u012c\u06fa\u0001\u0000\u0000\u0000\u012e\u06fc\u0001\u0000"+
		"\u0000\u0000\u0130\u06ff\u0001\u0000\u0000\u0000\u0132\u0703\u0001\u0000"+
		"\u0000\u0000\u0134\u0708\u0001\u0000\u0000\u0000\u0136\u070f\u0001\u0000"+
		"\u0000\u0000\u0138\u0713\u0001\u0000\u0000\u0000\u013a\u0715\u0001\u0000"+
		"\u0000\u0000\u013c\u0725\u0001\u0000\u0000\u0000\u013e\u0728\u0001\u0000"+
		"\u0000\u0000\u0140\u0731\u0001\u0000\u0000\u0000\u0142\u0733\u0001\u0000"+
		"\u0000\u0000\u0144\u073c\u0001\u0000\u0000\u0000\u0146\u0740\u0001\u0000"+
		"\u0000\u0000\u0148\u0744\u0001\u0000\u0000\u0000\u014a\u074a\u0001\u0000"+
		"\u0000\u0000\u014c\u0754\u0001\u0000\u0000\u0000\u014e\u0758\u0001\u0000"+
		"\u0000\u0000\u0150\u075e\u0001\u0000\u0000\u0000\u0152\u076c\u0001\u0000"+
		"\u0000\u0000\u0154\u076e\u0001\u0000\u0000\u0000\u0156\u0773\u0001\u0000"+
		"\u0000\u0000\u0158\u0778\u0001\u0000\u0000\u0000\u015a\u0785\u0001\u0000"+
		"\u0000\u0000\u015c\u078a\u0001\u0000\u0000\u0000\u015e\u078f\u0001\u0000"+
		"\u0000\u0000\u0160\u0797\u0001\u0000\u0000\u0000\u0162\u079c\u0001\u0000"+
		"\u0000\u0000\u0164\u07b9\u0001\u0000\u0000\u0000\u0166\u07d6\u0001\u0000"+
		"\u0000\u0000\u0168\u07d8\u0001\u0000\u0000\u0000\u016a\u07df\u0001\u0000"+
		"\u0000\u0000\u016c\u07e6\u0001\u0000\u0000\u0000\u016e\u07e8\u0001\u0000"+
		"\u0000\u0000\u0170\u07f3\u0001\u0000\u0000\u0000\u0172\u07fd\u0001\u0000"+
		"\u0000\u0000\u0174\u080d\u0001\u0000\u0000\u0000\u0176\u0819\u0001\u0000"+
		"\u0000\u0000\u0178\u082a\u0001\u0000\u0000\u0000\u017a\u0832\u0001\u0000"+
		"\u0000\u0000\u017c\u0834\u0001\u0000\u0000\u0000\u017e\u083d\u0001\u0000"+
		"\u0000\u0000\u0180\u0854\u0001\u0000\u0000\u0000\u0182\u0869\u0001\u0000"+
		"\u0000\u0000\u0184\u087a\u0001\u0000\u0000\u0000\u0186\u089b\u0001\u0000"+
		"\u0000\u0000\u0188\u08a0\u0001\u0000\u0000\u0000\u018a\u08a2\u0001\u0000"+
		"\u0000\u0000\u018c\u08a5\u0001\u0000\u0000\u0000\u018e\u08a8\u0001\u0000"+
		"\u0000\u0000\u0190\u08ab\u0001\u0000\u0000\u0000\u0192\u08ae\u0001\u0000"+
		"\u0000\u0000\u0194\u0196\u0003\n\u0005\u0000\u0195\u0194\u0001\u0000\u0000"+
		"\u0000\u0195\u0196\u0001\u0000\u0000\u0000\u0196\u0197\u0001\u0000\u0000"+
		"\u0000\u0197\u0198\u0005\u0000\u0000\u0001\u0198\u0001\u0001\u0000\u0000"+
		"\u0000\u0199\u019a\u0003\u000e\u0007\u0000\u019a\u0003\u0001\u0000\u0000"+
		"\u0000\u019b\u019f\u0003\u00d2i\u0000\u019c\u019e\u0005a\u0000\u0000\u019d"+
		"\u019c\u0001\u0000\u0000\u0000\u019e\u01a1\u0001\u0000\u0000\u0000\u019f"+
		"\u019d\u0001\u0000\u0000\u0000\u019f\u01a0\u0001\u0000\u0000\u0000\u01a0"+
		"\u01a2\u0001\u0000\u0000\u0000\u01a1\u019f\u0001\u0000\u0000\u0000\u01a2"+
		"\u01a3\u0005\u0000\u0000\u0001\u01a3\u0005\u0001\u0000\u0000\u0000\u01a4"+
		"\u01a6\u0005+\u0000\u0000\u01a5\u01a7\u0003\u0186\u00c3\u0000\u01a6\u01a5"+
		"\u0001\u0000\u0000\u0000\u01a6\u01a7\u0001\u0000\u0000\u0000\u01a7\u01a8"+
		"\u0001\u0000\u0000\u0000\u01a8\u01a9\u0005.\u0000\u0000\u01a9\u01aa\u0005"+
		"W\u0000\u0000\u01aa\u01ae\u0003\u00d4j\u0000\u01ab\u01ad\u0005a\u0000"+
		"\u0000\u01ac\u01ab\u0001\u0000\u0000\u0000\u01ad\u01b0\u0001\u0000\u0000"+
		"\u0000\u01ae\u01ac\u0001\u0000\u0000\u0000\u01ae\u01af\u0001\u0000\u0000"+
		"\u0000\u01af\u01b1\u0001\u0000\u0000\u0000\u01b0\u01ae\u0001\u0000\u0000"+
		"\u0000\u01b1\u01b2\u0005\u0000\u0000\u0001\u01b2\u0007\u0001\u0000\u0000"+
		"\u0000\u01b3\u01b4\u0003\u00d8l\u0000\u01b4\t\u0001\u0000\u0000\u0000"+
		"\u01b5\u01b7\u0003\f\u0006\u0000\u01b6\u01b5\u0001\u0000\u0000\u0000\u01b7"+
		"\u01b8\u0001\u0000\u0000\u0000\u01b8\u01b6\u0001\u0000\u0000\u0000\u01b8"+
		"\u01b9\u0001\u0000\u0000\u0000\u01b9\u000b\u0001\u0000\u0000\u0000\u01ba"+
		"\u01bd\u0003\u0014\n\u0000\u01bb\u01bd\u0003\u0010\b\u0000\u01bc\u01ba"+
		"\u0001\u0000\u0000\u0000\u01bc\u01bb\u0001\u0000\u0000\u0000\u01bd\r\u0001"+
		"\u0000\u0000\u0000\u01be\u01bf\u0003\u0014\n\u0000\u01bf\u01c0\u0005a"+
		"\u0000\u0000\u01c0\u01c5\u0001\u0000\u0000\u0000\u01c1\u01c5\u0003\u0010"+
		"\b\u0000\u01c2\u01c5\u0005a\u0000\u0000\u01c3\u01c5\u0005\u0000\u0000"+
		"\u0001\u01c4\u01be\u0001\u0000\u0000\u0000\u01c4\u01c1\u0001\u0000\u0000"+
		"\u0000\u01c4\u01c2\u0001\u0000\u0000\u0000\u01c4\u01c3\u0001\u0000\u0000"+
		"\u0000\u01c5\u000f\u0001\u0000\u0000\u0000\u01c6\u01cb\u0003\u0012\t\u0000"+
		"\u01c7\u01c8\u00054\u0000\u0000\u01c8\u01ca\u0003\u0012\t\u0000\u01c9"+
		"\u01c7\u0001\u0000\u0000\u0000\u01ca\u01cd\u0001\u0000\u0000\u0000\u01cb"+
		"\u01c9\u0001\u0000\u0000\u0000\u01cb\u01cc\u0001\u0000\u0000\u0000\u01cc"+
		"\u01cf\u0001\u0000\u0000\u0000\u01cd\u01cb\u0001\u0000\u0000\u0000\u01ce"+
		"\u01d0\u00054\u0000\u0000\u01cf\u01ce\u0001\u0000\u0000\u0000\u01cf\u01d0"+
		"\u0001\u0000\u0000\u0000\u01d0\u01d1\u0001\u0000\u0000\u0000\u01d1\u01d2"+
		"\u0005a\u0000\u0000\u01d2\u0011\u0001\u0000\u0000\u0000\u01d3\u01e3\u0003"+
		"\u0016\u000b\u0000\u01d4\u01e3\u0003\u00c8d\u0000\u01d5\u01e3\u0003\u00d8"+
		"l\u0000\u01d6\u01e3\u0003\u001c\u000e\u0000\u01d7\u01e3\u0003*\u0015\u0000"+
		"\u01d8\u01e3\u0003\u001e\u000f\u0000\u01d9\u01e3\u0005\n\u0000\u0000\u01da"+
		"\u01e3\u0003$\u0012\u0000\u01db\u01e3\u0003&\u0013\u0000\u01dc\u01e3\u0003"+
		"(\u0014\u0000\u01dd\u01e3\u0005\f\u0000\u0000\u01de\u01e3\u0005\u0016"+
		"\u0000\u0000\u01df\u01e3\u0003 \u0010\u0000\u01e0\u01e3\u0003\"\u0011"+
		"\u0000\u01e1\u01e3\u0003,\u0016\u0000\u01e2\u01d3\u0001\u0000\u0000\u0000"+
		"\u01e2\u01d4\u0001\u0000\u0000\u0000\u01e2\u01d5\u0001\u0000\u0000\u0000"+
		"\u01e2\u01d6\u0001\u0000\u0000\u0000\u01e2\u01d7\u0001\u0000\u0000\u0000"+
		"\u01e2\u01d8\u0001\u0000\u0000\u0000\u01e2\u01d9\u0001\u0000\u0000\u0000"+
		"\u01e2\u01da\u0001\u0000\u0000\u0000\u01e2\u01db\u0001\u0000\u0000\u0000"+
		"\u01e2\u01dc\u0001\u0000\u0000\u0000\u01e2\u01dd\u0001\u0000\u0000\u0000"+
		"\u01e2\u01de\u0001\u0000\u0000\u0000\u01e2\u01df\u0001\u0000\u0000\u0000"+
		"\u01e2\u01e0\u0001\u0000\u0000\u0000\u01e2\u01e1\u0001\u0000\u0000\u0000"+
		"\u01e3\u0013\u0001\u0000\u0000\u0000\u01e4\u01ed\u0003F#\u0000\u01e5\u01ed"+
		"\u0003h4\u0000\u01e6\u01ed\u0003B!\u0000\u01e7\u01ed\u0003r9\u0000\u01e8"+
		"\u01ed\u0003p8\u0000\u01e9\u01ed\u0003v;\u0000\u01ea\u01ed\u0003n7\u0000"+
		"\u01eb\u01ed\u0003~?\u0000\u01ec\u01e4\u0001\u0000\u0000\u0000\u01ec\u01e5"+
		"\u0001\u0000\u0000\u0000\u01ec\u01e6\u0001\u0000\u0000\u0000\u01ec\u01e7"+
		"\u0001\u0000\u0000\u0000\u01ec\u01e8\u0001\u0000\u0000\u0000\u01ec\u01e9"+
		"\u0001\u0000\u0000\u0000\u01ec\u01ea\u0001\u0000\u0000\u0000\u01ec\u01eb"+
		"\u0001\u0000\u0000\u0000\u01ed\u0015\u0001\u0000\u0000\u0000\u01ee\u01ef"+
		"\u0005]\u0000\u0000\u01ef\u01f0\u00052\u0000\u0000\u01f0\u01f3\u0003\u00d4"+
		"j\u0000\u01f1\u01f2\u0005=\u0000\u0000\u01f2\u01f4\u0003\u0018\f\u0000"+
		"\u01f3\u01f1\u0001\u0000\u0000\u0000\u01f3\u01f4\u0001\u0000\u0000\u0000"+
		"\u01f4\u0217\u0001\u0000\u0000\u0000\u01f5\u01f6\u0005+\u0000\u0000\u01f6"+
		"\u01f7\u0003\u017a\u00bd\u0000\u01f7\u01f8\u0005.\u0000\u0000\u01f8\u01fb"+
		"\u0001\u0000\u0000\u0000\u01f9\u01fb\u0003\u017c\u00be\u0000\u01fa\u01f5"+
		"\u0001\u0000\u0000\u0000\u01fa\u01f9\u0001\u0000\u0000\u0000\u01fb\u01fc"+
		"\u0001\u0000\u0000\u0000\u01fc\u01fd\u00052\u0000\u0000\u01fd\u0200\u0003"+
		"\u00d4j\u0000\u01fe\u01ff\u0005=\u0000\u0000\u01ff\u0201\u0003\u0018\f"+
		"\u0000\u0200\u01fe\u0001\u0000\u0000\u0000\u0200\u0201\u0001\u0000\u0000"+
		"\u0000\u0201\u0217\u0001\u0000\u0000\u0000\u0202\u0203\u0003\u016e\u00b7"+
		"\u0000\u0203\u0204\u0005=\u0000\u0000\u0204\u0206\u0001\u0000\u0000\u0000"+
		"\u0205\u0202\u0001\u0000\u0000\u0000\u0206\u0207\u0001\u0000\u0000\u0000"+
		"\u0207\u0205\u0001\u0000\u0000\u0000\u0207\u0208\u0001\u0000\u0000\u0000"+
		"\u0208\u020b\u0001\u0000\u0000\u0000\u0209\u020c\u0003\u00d6k\u0000\u020a"+
		"\u020c\u0003\u00d8l\u0000\u020b\u0209\u0001\u0000\u0000\u0000\u020b\u020a"+
		"\u0001\u0000\u0000\u0000\u020c\u020e\u0001\u0000\u0000\u0000\u020d\u020f"+
		"\u0005`\u0000\u0000\u020e\u020d\u0001\u0000\u0000\u0000\u020e\u020f\u0001"+
		"\u0000\u0000\u0000\u020f\u0217\u0001\u0000\u0000\u0000\u0210\u0211\u0003"+
		"\u017a\u00bd\u0000\u0211\u0214\u0003\u001a\r\u0000\u0212\u0215\u0003\u00d6"+
		"k\u0000\u0213\u0215\u0003\u00d8l\u0000\u0214\u0212\u0001\u0000\u0000\u0000"+
		"\u0214\u0213\u0001\u0000\u0000\u0000\u0215\u0217\u0001\u0000\u0000\u0000"+
		"\u0216\u01ee\u0001\u0000\u0000\u0000\u0216\u01fa\u0001\u0000\u0000\u0000"+
		"\u0216\u0205\u0001\u0000\u0000\u0000\u0216\u0210\u0001\u0000\u0000\u0000"+
		"\u0217\u0017\u0001\u0000\u0000\u0000\u0218\u021b\u0003\u00d6k\u0000\u0219"+
		"\u021b\u0003\u00d8l\u0000\u021a\u0218\u0001\u0000\u0000\u0000\u021a\u0219"+
		"\u0001\u0000\u0000\u0000\u021b\u0019\u0001\u0000\u0000\u0000\u021c\u021d"+
		"\u0007\u0000\u0000\u0000\u021d\u001b\u0001\u0000\u0000\u0000\u021e\u0220"+
		"\u0005\u0014\u0000\u0000\u021f\u0221\u0003\u00d8l\u0000\u0220\u021f\u0001"+
		"\u0000\u0000\u0000\u0220\u0221\u0001\u0000\u0000\u0000\u0221\u001d\u0001"+
		"\u0000\u0000\u0000\u0222\u0228\u0005\u000f\u0000\u0000\u0223\u0226\u0003"+
		"\u00d4j\u0000\u0224\u0225\u0005\u001c\u0000\u0000\u0225\u0227\u0003\u00d4"+
		"j\u0000\u0226\u0224\u0001\u0000\u0000\u0000\u0226\u0227\u0001\u0000\u0000"+
		"\u0000\u0227\u0229\u0001\u0000\u0000\u0000\u0228\u0223\u0001\u0000\u0000"+
		"\u0000\u0228\u0229\u0001\u0000\u0000\u0000\u0229\u001f\u0001\u0000\u0000"+
		"\u0000\u022a\u022b\u0005!\u0000\u0000\u022b\u0230\u0005]\u0000\u0000\u022c"+
		"\u022d\u00053\u0000\u0000\u022d\u022f\u0005]\u0000\u0000\u022e\u022c\u0001"+
		"\u0000\u0000\u0000\u022f\u0232\u0001\u0000\u0000\u0000\u0230\u022e\u0001"+
		"\u0000\u0000\u0000\u0230\u0231\u0001\u0000\u0000\u0000\u0231!\u0001\u0000"+
		"\u0000\u0000\u0232\u0230\u0001\u0000\u0000\u0000\u0233\u0234\u0005\u001d"+
		"\u0000\u0000\u0234\u0239\u0005]\u0000\u0000\u0235\u0236\u00053\u0000\u0000"+
		"\u0236\u0238\u0005]\u0000\u0000\u0237\u0235\u0001\u0000\u0000\u0000\u0238"+
		"\u023b\u0001\u0000\u0000\u0000\u0239\u0237\u0001\u0000\u0000\u0000\u0239"+
		"\u023a\u0001\u0000\u0000\u0000\u023a#\u0001\u0000\u0000\u0000\u023b\u0239"+
		"\u0001\u0000\u0000\u0000\u023c\u023d\u0005 \u0000\u0000\u023d\u023e\u0003"+
		"\u0180\u00c0\u0000\u023e%\u0001\u0000\u0000\u0000\u023f\u0240\u0003\u00d6"+
		"k\u0000\u0240\'\u0001\u0000\u0000\u0000\u0241\u0242\u0005\u001f\u0000"+
		"\u0000\u0242\u0245\u0003\u00d4j\u0000\u0243\u0244\u00053\u0000\u0000\u0244"+
		"\u0246\u0003\u00d4j\u0000\u0245\u0243\u0001\u0000\u0000\u0000\u0245\u0246"+
		"\u0001\u0000\u0000\u0000\u0246)\u0001\u0000\u0000\u0000\u0247\u024a\u0003"+
		".\u0017\u0000\u0248\u024a\u00030\u0018\u0000\u0249\u0247\u0001\u0000\u0000"+
		"\u0000\u0249\u0248\u0001\u0000\u0000\u0000\u024a+\u0001\u0000\u0000\u0000"+
		"\u024b\u024e\u0003\u00d4j\u0000\u024c\u024d\u0005C\u0000\u0000\u024d\u024f"+
		"\u0003\u00d4j\u0000\u024e\u024c\u0001\u0000\u0000\u0000\u024f\u0250\u0001"+
		"\u0000\u0000\u0000\u0250\u024e\u0001\u0000\u0000\u0000\u0250\u0251\u0001"+
		"\u0000\u0000\u0000\u0251-\u0001\u0000\u0000\u0000\u0252\u0253\u0005\t"+
		"\u0000\u0000\u0253\u0254\u00038\u001c\u0000\u0254/\u0001\u0000\u0000\u0000"+
		"\u0255\u0259\u0005\u001c\u0000\u0000\u0256\u0258\u0007\u0001\u0000\u0000"+
		"\u0257\u0256\u0001\u0000\u0000\u0000\u0258\u025b\u0001\u0000\u0000\u0000"+
		"\u0259\u0257\u0001\u0000\u0000\u0000\u0259\u025a\u0001\u0000\u0000\u0000"+
		"\u025a\u025c\u0001\u0000\u0000\u0000\u025b\u0259\u0001\u0000\u0000\u0000"+
		"\u025c\u025d\u0003<\u001e\u0000\u025d\u025e\u0005\t\u0000\u0000\u025e"+
		"\u025f\u00032\u0019\u0000\u025f\u0269\u0001\u0000\u0000\u0000\u0260\u0262"+
		"\u0005\u001c\u0000\u0000\u0261\u0263\u0007\u0001\u0000\u0000\u0262\u0261"+
		"\u0001\u0000\u0000\u0000\u0263\u0264\u0001\u0000\u0000\u0000\u0264\u0262"+
		"\u0001\u0000\u0000\u0000\u0264\u0265\u0001\u0000\u0000\u0000\u0265\u0266"+
		"\u0001\u0000\u0000\u0000\u0266\u0267\u0005\t\u0000\u0000\u0267\u0269\u0003"+
		"2\u0019\u0000\u0268\u0255\u0001\u0000\u0000\u0000\u0268\u0260\u0001\u0000"+
		"\u0000\u0000\u02691\u0001\u0000\u0000\u0000\u026a\u026b\u0005+\u0000\u0000"+
		"\u026b\u026d\u00034\u001a\u0000\u026c\u026e\u00053\u0000\u0000\u026d\u026c"+
		"\u0001\u0000\u0000\u0000\u026d\u026e\u0001\u0000\u0000\u0000\u026e\u026f"+
		"\u0001\u0000\u0000\u0000\u026f\u0270\u0005.\u0000\u0000\u0270\u0274\u0001"+
		"\u0000\u0000\u0000\u0271\u0274\u00034\u001a\u0000\u0272\u0274\u00057\u0000"+
		"\u0000\u0273\u026a\u0001\u0000\u0000\u0000\u0273\u0271\u0001\u0000\u0000"+
		"\u0000\u0273\u0272\u0001\u0000\u0000\u0000\u02743\u0001\u0000\u0000\u0000"+
		"\u0275\u027a\u00036\u001b\u0000\u0276\u0277\u00053\u0000\u0000\u0277\u0279"+
		"\u00036\u001b\u0000\u0278\u0276\u0001\u0000\u0000\u0000\u0279\u027c\u0001"+
		"\u0000\u0000\u0000\u027a\u0278\u0001\u0000\u0000\u0000\u027a\u027b\u0001"+
		"\u0000\u0000\u0000\u027b5\u0001\u0000\u0000\u0000\u027c\u027a\u0001\u0000"+
		"\u0000\u0000\u027d\u0280\u0005]\u0000\u0000\u027e\u027f\u0005\u001a\u0000"+
		"\u0000\u027f\u0281\u0005]\u0000\u0000\u0280\u027e\u0001\u0000\u0000\u0000"+
		"\u0280\u0281\u0001\u0000\u0000\u0000\u02817\u0001\u0000\u0000\u0000\u0282"+
		"\u0287\u0003:\u001d\u0000\u0283\u0284\u00053\u0000\u0000\u0284\u0286\u0003"+
		":\u001d\u0000\u0285\u0283\u0001\u0000\u0000\u0000\u0286\u0289\u0001\u0000"+
		"\u0000\u0000\u0287\u0285\u0001\u0000\u0000\u0000\u0287\u0288\u0001\u0000"+
		"\u0000\u0000\u02889\u0001\u0000\u0000\u0000\u0289\u0287\u0001\u0000\u0000"+
		"\u0000\u028a\u028d\u0003<\u001e\u0000\u028b\u028c\u0005\u001a\u0000\u0000"+
		"\u028c\u028e\u0005]\u0000\u0000\u028d\u028b\u0001\u0000\u0000\u0000\u028d"+
		"\u028e\u0001\u0000\u0000\u0000\u028e;\u0001\u0000\u0000\u0000\u028f\u0290"+
		"\u0006\u001e\uffff\uffff\u0000\u0290\u0291\u0005]\u0000\u0000\u0291\u0297"+
		"\u0001\u0000\u0000\u0000\u0292\u0293\n\u0002\u0000\u0000\u0293\u0294\u0005"+
		"1\u0000\u0000\u0294\u0296\u0005]\u0000\u0000\u0295\u0292\u0001\u0000\u0000"+
		"\u0000\u0296\u0299\u0001\u0000\u0000\u0000\u0297\u0295\u0001\u0000\u0000"+
		"\u0000\u0297\u0298\u0001\u0000\u0000\u0000\u0298=\u0001\u0000\u0000\u0000"+
		"\u0299\u0297\u0001\u0000\u0000\u0000\u029a\u029b\u0005a\u0000\u0000\u029b"+
		"\u029c\u0005\u0001\u0000\u0000\u029c\u029d\u0003\n\u0005\u0000\u029d\u029e"+
		"\u0005\u0002\u0000\u0000\u029e\u02a1\u0001\u0000\u0000\u0000\u029f\u02a1"+
		"\u0003\u0010\b\u0000\u02a0\u029a\u0001\u0000\u0000\u0000\u02a0\u029f\u0001"+
		"\u0000\u0000\u0000\u02a1?\u0001\u0000\u0000\u0000\u02a2\u02a3\u0005U\u0000"+
		"\u0000\u02a3\u02a4\u0003\u00e2q\u0000\u02a4\u02a5\u0005a\u0000\u0000\u02a5"+
		"\u02a7\u0001\u0000\u0000\u0000\u02a6\u02a2\u0001\u0000\u0000\u0000\u02a7"+
		"\u02a8\u0001\u0000\u0000\u0000\u02a8\u02a6\u0001\u0000\u0000\u0000\u02a8"+
		"\u02a9\u0001\u0000\u0000\u0000\u02a9A\u0001\u0000\u0000\u0000\u02aa\u02ab"+
		"\u0003@ \u0000\u02ab\u02ac\u0003D\"\u0000\u02ac\u02af\u0001\u0000\u0000"+
		"\u0000\u02ad\u02af\u0003D\"\u0000\u02ae\u02aa\u0001\u0000\u0000\u0000"+
		"\u02ae\u02ad\u0001\u0000\u0000\u0000\u02afC\u0001\u0000\u0000\u0000\u02b0"+
		"\u02b1\u0005\u0011\u0000\u0000\u02b1\u02b3\u0005]\u0000\u0000\u02b2\u02b4"+
		"\u0003\u00cae\u0000\u02b3\u02b2\u0001\u0000\u0000\u0000\u02b3\u02b4\u0001"+
		"\u0000\u0000\u0000\u02b4\u02ba\u0001\u0000\u0000\u0000\u02b5\u02b7\u0005"+
		"+\u0000\u0000\u02b6\u02b8\u0003\u0162\u00b1\u0000\u02b7\u02b6\u0001\u0000"+
		"\u0000\u0000\u02b7\u02b8\u0001\u0000\u0000\u0000\u02b8\u02b9\u0001\u0000"+
		"\u0000\u0000\u02b9\u02bb\u0005.\u0000\u0000\u02ba\u02b5\u0001\u0000\u0000"+
		"\u0000\u02ba\u02bb\u0001\u0000\u0000\u0000\u02bb\u02bc\u0001\u0000\u0000"+
		"\u0000\u02bc\u02bd\u00052\u0000\u0000\u02bd\u02be\u0003>\u001f\u0000\u02be"+
		"E\u0001\u0000\u0000\u0000\u02bf\u02c0\u0003@ \u0000\u02c0\u02c1\u0003"+
		"H$\u0000\u02c1\u02c4\u0001\u0000\u0000\u0000\u02c2\u02c4\u0003H$\u0000"+
		"\u02c3\u02bf\u0001\u0000\u0000\u0000\u02c3\u02c2\u0001\u0000\u0000\u0000"+
		"\u02c4G\u0001\u0000\u0000\u0000\u02c5\u02c6\u0005\u001b\u0000\u0000\u02c6"+
		"\u02c8\u0005]\u0000\u0000\u02c7\u02c9\u0003\u00cae\u0000\u02c8\u02c7\u0001"+
		"\u0000\u0000\u0000\u02c8\u02c9\u0001\u0000\u0000\u0000\u02c9\u02ca\u0001"+
		"\u0000\u0000\u0000\u02ca\u02cc\u0005+\u0000\u0000\u02cb\u02cd\u0003J%"+
		"\u0000\u02cc\u02cb\u0001\u0000\u0000\u0000\u02cc\u02cd\u0001\u0000\u0000"+
		"\u0000\u02cd\u02ce\u0001\u0000\u0000\u0000\u02ce\u02d1\u0005.\u0000\u0000"+
		"\u02cf\u02d0\u0005W\u0000\u0000\u02d0\u02d2\u0003\u00d4j\u0000\u02d1\u02cf"+
		"\u0001\u0000\u0000\u0000\u02d1\u02d2\u0001\u0000\u0000\u0000\u02d2\u02d3"+
		"\u0001\u0000\u0000\u0000\u02d3\u02d5\u00052\u0000\u0000\u02d4\u02d6\u0003"+
		"\u0188\u00c4\u0000\u02d5\u02d4\u0001\u0000\u0000\u0000\u02d5\u02d6\u0001"+
		"\u0000\u0000\u0000\u02d6\u02d7\u0001\u0000\u0000\u0000\u02d7\u02ed\u0003"+
		">\u001f\u0000\u02d8\u02d9\u0005$\u0000\u0000\u02d9\u02da\u0005\u001b\u0000"+
		"\u0000\u02da\u02dc\u0005]\u0000\u0000\u02db\u02dd\u0003\u00cae\u0000\u02dc"+
		"\u02db\u0001\u0000\u0000\u0000\u02dc\u02dd\u0001\u0000\u0000\u0000\u02dd"+
		"\u02de\u0001\u0000\u0000\u0000\u02de\u02e0\u0005+\u0000\u0000\u02df\u02e1"+
		"\u0003J%\u0000\u02e0\u02df\u0001\u0000\u0000\u0000\u02e0\u02e1\u0001\u0000"+
		"\u0000\u0000\u02e1\u02e2\u0001\u0000\u0000\u0000\u02e2\u02e5\u0005.\u0000"+
		"\u0000\u02e3\u02e4\u0005W\u0000\u0000\u02e4\u02e6\u0003\u00d4j\u0000\u02e5"+
		"\u02e3\u0001\u0000\u0000\u0000\u02e5\u02e6\u0001\u0000\u0000\u0000\u02e6"+
		"\u02e7\u0001\u0000\u0000\u0000\u02e7\u02e9\u00052\u0000\u0000\u02e8\u02ea"+
		"\u0003\u0188\u00c4\u0000\u02e9\u02e8\u0001\u0000\u0000\u0000\u02e9\u02ea"+
		"\u0001\u0000\u0000\u0000\u02ea\u02eb\u0001\u0000\u0000\u0000\u02eb\u02ed"+
		"\u0003>\u001f\u0000\u02ec\u02c5\u0001\u0000\u0000\u0000\u02ec\u02d8\u0001"+
		"\u0000\u0000\u0000\u02edI\u0001\u0000\u0000\u0000\u02ee\u02ef\u0003L&"+
		"\u0000\u02efK\u0001\u0000\u0000\u0000\u02f0\u02f4\u0003N\'\u0000\u02f1"+
		"\u02f3\u0003V+\u0000\u02f2\u02f1\u0001\u0000\u0000\u0000\u02f3\u02f6\u0001"+
		"\u0000\u0000\u0000\u02f4\u02f2\u0001\u0000\u0000\u0000\u02f4\u02f5\u0001"+
		"\u0000\u0000\u0000\u02f5\u02fa\u0001\u0000\u0000\u0000\u02f6\u02f4\u0001"+
		"\u0000\u0000\u0000\u02f7\u02f9\u0003Z-\u0000\u02f8\u02f7\u0001\u0000\u0000"+
		"\u0000\u02f9\u02fc\u0001\u0000\u0000\u0000\u02fa\u02f8\u0001\u0000\u0000"+
		"\u0000\u02fa\u02fb\u0001\u0000\u0000\u0000\u02fb\u02fe\u0001\u0000\u0000"+
		"\u0000\u02fc\u02fa\u0001\u0000\u0000\u0000\u02fd\u02ff\u0003R)\u0000\u02fe"+
		"\u02fd\u0001\u0000\u0000\u0000\u02fe\u02ff\u0001\u0000\u0000\u0000\u02ff"+
		"\u0322\u0001\u0000\u0000\u0000\u0300\u0304\u0003P(\u0000\u0301\u0303\u0003"+
		"Z-\u0000\u0302\u0301\u0001\u0000\u0000\u0000\u0303\u0306\u0001\u0000\u0000"+
		"\u0000\u0304\u0302\u0001\u0000\u0000\u0000\u0304\u0305\u0001\u0000\u0000"+
		"\u0000\u0305\u0308\u0001\u0000\u0000\u0000\u0306\u0304\u0001\u0000\u0000"+
		"\u0000\u0307\u0309\u0003R)\u0000\u0308\u0307\u0001\u0000\u0000\u0000\u0308"+
		"\u0309\u0001\u0000\u0000\u0000\u0309\u0322\u0001\u0000\u0000\u0000\u030a"+
		"\u030c\u0003V+\u0000\u030b\u030a\u0001\u0000\u0000\u0000\u030c\u030d\u0001"+
		"\u0000\u0000\u0000\u030d\u030b\u0001\u0000\u0000\u0000\u030d\u030e\u0001"+
		"\u0000\u0000\u0000\u030e\u0312\u0001\u0000\u0000\u0000\u030f\u0311\u0003"+
		"Z-\u0000\u0310\u030f\u0001\u0000\u0000\u0000\u0311\u0314\u0001\u0000\u0000"+
		"\u0000\u0312\u0310\u0001\u0000\u0000\u0000\u0312\u0313\u0001\u0000\u0000"+
		"\u0000\u0313\u0316\u0001\u0000\u0000\u0000\u0314\u0312\u0001\u0000\u0000"+
		"\u0000\u0315\u0317\u0003R)\u0000\u0316\u0315\u0001\u0000\u0000\u0000\u0316"+
		"\u0317\u0001\u0000\u0000\u0000\u0317\u0322\u0001\u0000\u0000\u0000\u0318"+
		"\u031a\u0003Z-\u0000\u0319\u0318\u0001\u0000\u0000\u0000\u031a\u031b\u0001"+
		"\u0000\u0000\u0000\u031b\u0319\u0001\u0000\u0000\u0000\u031b\u031c\u0001"+
		"\u0000\u0000\u0000\u031c\u031e\u0001\u0000\u0000\u0000\u031d\u031f\u0003"+
		"R)\u0000\u031e\u031d\u0001\u0000\u0000\u0000\u031e\u031f\u0001\u0000\u0000"+
		"\u0000\u031f\u0322\u0001\u0000\u0000\u0000\u0320\u0322\u0003R)\u0000\u0321"+
		"\u02f0\u0001\u0000\u0000\u0000\u0321\u0300\u0001\u0000\u0000\u0000\u0321"+
		"\u030b\u0001\u0000\u0000\u0000\u0321\u0319\u0001\u0000\u0000\u0000\u0321"+
		"\u0320\u0001\u0000\u0000\u0000\u0322M\u0001\u0000\u0000\u0000\u0323\u0325"+
		"\u0003V+\u0000\u0324\u0323\u0001\u0000\u0000\u0000\u0325\u0326\u0001\u0000"+
		"\u0000\u0000\u0326\u0324\u0001\u0000\u0000\u0000\u0326\u0327\u0001\u0000"+
		"\u0000\u0000\u0327\u0328\u0001\u0000\u0000\u0000\u0328\u032a\u00058\u0000"+
		"\u0000\u0329\u032b\u00053\u0000\u0000\u032a\u0329\u0001\u0000\u0000\u0000"+
		"\u032a\u032b\u0001\u0000\u0000\u0000\u032bO\u0001\u0000\u0000\u0000\u032c"+
		"\u032e\u0003V+\u0000\u032d\u032c\u0001\u0000\u0000\u0000\u032e\u0331\u0001"+
		"\u0000\u0000\u0000\u032f\u032d\u0001\u0000\u0000\u0000\u032f\u0330\u0001"+
		"\u0000\u0000\u0000\u0330\u0333\u0001\u0000\u0000\u0000\u0331\u032f\u0001"+
		"\u0000\u0000\u0000\u0332\u0334\u0003Z-\u0000\u0333\u0332\u0001\u0000\u0000"+
		"\u0000\u0334\u0335\u0001\u0000\u0000\u0000\u0335\u0333\u0001\u0000\u0000"+
		"\u0000\u0335\u0336\u0001\u0000\u0000\u0000\u0336\u0337\u0001\u0000\u0000"+
		"\u0000\u0337\u0339\u00058\u0000\u0000\u0338\u033a\u00053\u0000\u0000\u0339"+
		"\u0338\u0001\u0000\u0000\u0000\u0339\u033a\u0001\u0000\u0000\u0000\u033a"+
		"Q\u0001\u0000\u0000\u0000\u033b\u033c\u00057\u0000\u0000\u033c\u0340\u0003"+
		"V+\u0000\u033d\u033f\u0003\\.\u0000\u033e\u033d\u0001\u0000\u0000\u0000"+
		"\u033f\u0342\u0001\u0000\u0000\u0000\u0340\u033e\u0001\u0000\u0000\u0000"+
		"\u0340\u0341\u0001\u0000\u0000\u0000\u0341\u0344\u0001\u0000\u0000\u0000"+
		"\u0342\u0340\u0001\u0000\u0000\u0000\u0343\u0345\u0003T*\u0000\u0344\u0343"+
		"\u0001\u0000\u0000\u0000\u0344\u0345\u0001\u0000\u0000\u0000\u0345\u035d"+
		"\u0001\u0000\u0000\u0000\u0346\u0347\u00057\u0000\u0000\u0347\u034b\u0003"+
		"X,\u0000\u0348\u034a\u0003\\.\u0000\u0349\u0348\u0001\u0000\u0000\u0000"+
		"\u034a\u034d\u0001\u0000\u0000\u0000\u034b\u0349\u0001\u0000\u0000\u0000"+
		"\u034b\u034c\u0001\u0000\u0000\u0000\u034c\u034f\u0001\u0000\u0000\u0000"+
		"\u034d\u034b\u0001\u0000\u0000\u0000\u034e\u0350\u0003T*\u0000\u034f\u034e"+
		"\u0001\u0000\u0000\u0000\u034f\u0350\u0001\u0000\u0000\u0000\u0350\u035d"+
		"\u0001\u0000\u0000\u0000\u0351\u0352\u00057\u0000\u0000\u0352\u0354\u0005"+
		"3\u0000\u0000\u0353\u0355\u0003\\.\u0000\u0354\u0353\u0001\u0000\u0000"+
		"\u0000\u0355\u0356\u0001\u0000\u0000\u0000\u0356\u0354\u0001\u0000\u0000"+
		"\u0000\u0356\u0357\u0001\u0000\u0000\u0000\u0357\u0359\u0001\u0000\u0000"+
		"\u0000\u0358\u035a\u0003T*\u0000\u0359\u0358\u0001\u0000\u0000\u0000\u0359"+
		"\u035a\u0001\u0000\u0000\u0000\u035a\u035d\u0001\u0000\u0000\u0000\u035b"+
		"\u035d\u0003T*\u0000\u035c\u033b\u0001\u0000\u0000\u0000\u035c\u0346\u0001"+
		"\u0000\u0000\u0000\u035c\u0351\u0001\u0000\u0000\u0000\u035c\u035b\u0001"+
		"\u0000\u0000\u0000\u035dS\u0001\u0000\u0000\u0000\u035e\u035f\u0005G\u0000"+
		"\u0000\u035f\u0360\u0003V+\u0000\u0360U\u0001\u0000\u0000\u0000\u0361"+
		"\u0363\u0003^/\u0000\u0362\u0364\u00053\u0000\u0000\u0363\u0362\u0001"+
		"\u0000\u0000\u0000\u0363\u0364\u0001\u0000\u0000\u0000\u0364\u0366\u0001"+
		"\u0000\u0000\u0000\u0365\u0367\u0005`\u0000\u0000\u0366\u0365\u0001\u0000"+
		"\u0000\u0000\u0366\u0367\u0001\u0000\u0000\u0000\u0367W\u0001\u0000\u0000"+
		"\u0000\u0368\u036a\u0003`0\u0000\u0369\u036b\u00053\u0000\u0000\u036a"+
		"\u0369\u0001\u0000\u0000\u0000\u036a\u036b\u0001\u0000\u0000\u0000\u036b"+
		"\u036d\u0001\u0000\u0000\u0000\u036c\u036e\u0005`\u0000\u0000\u036d\u036c"+
		"\u0001\u0000\u0000\u0000\u036d\u036e\u0001\u0000\u0000\u0000\u036eY\u0001"+
		"\u0000\u0000\u0000\u036f\u0370\u0003^/\u0000\u0370\u0372\u0003f3\u0000"+
		"\u0371\u0373\u00053\u0000\u0000\u0372\u0371\u0001\u0000\u0000\u0000\u0372"+
		"\u0373\u0001\u0000\u0000\u0000\u0373\u0375\u0001\u0000\u0000\u0000\u0374"+
		"\u0376\u0005`\u0000\u0000\u0375\u0374\u0001\u0000\u0000\u0000\u0375\u0376"+
		"\u0001\u0000\u0000\u0000\u0376[\u0001\u0000\u0000\u0000\u0377\u0379\u0003"+
		"^/\u0000\u0378\u037a\u0003f3\u0000\u0379\u0378\u0001\u0000\u0000\u0000"+
		"\u0379\u037a\u0001\u0000\u0000\u0000\u037a\u037c\u0001\u0000\u0000\u0000"+
		"\u037b\u037d\u00053\u0000\u0000\u037c\u037b\u0001\u0000\u0000\u0000\u037c"+
		"\u037d\u0001\u0000\u0000\u0000\u037d\u037f\u0001\u0000\u0000\u0000\u037e"+
		"\u0380\u0005`\u0000\u0000\u037f\u037e\u0001\u0000\u0000\u0000\u037f\u0380"+
		"\u0001\u0000\u0000\u0000\u0380]\u0001\u0000\u0000\u0000\u0381\u0383\u0005"+
		"]\u0000\u0000\u0382\u0384\u0003b1\u0000\u0383\u0382\u0001\u0000\u0000"+
		"\u0000\u0383\u0384\u0001\u0000\u0000\u0000\u0384_\u0001\u0000\u0000\u0000"+
		"\u0385\u0386\u0005]\u0000\u0000\u0386\u0387\u0003d2\u0000\u0387a\u0001"+
		"\u0000\u0000\u0000\u0388\u0389\u00052\u0000\u0000\u0389\u038a\u0003\u00d4"+
		"j\u0000\u038ac\u0001\u0000\u0000\u0000\u038b\u038c\u00052\u0000\u0000"+
		"\u038c\u038d\u0003\u00dam\u0000\u038de\u0001\u0000\u0000\u0000\u038e\u038f"+
		"\u0005=\u0000\u0000\u038f\u0390\u0003\u00d4j\u0000\u0390g\u0001\u0000"+
		"\u0000\u0000\u0391\u0392\u0005&\u0000\u0000\u0392\u0393\u0003\u00e2q\u0000"+
		"\u0393\u0394\u00052\u0000\u0000\u0394\u0399\u0003>\u001f\u0000\u0395\u039a"+
		"\u0003j5\u0000\u0396\u0398\u0003l6\u0000\u0397\u0396\u0001\u0000\u0000"+
		"\u0000\u0397\u0398\u0001\u0000\u0000\u0000\u0398\u039a\u0001\u0000\u0000"+
		"\u0000\u0399\u0395\u0001\u0000\u0000\u0000\u0399\u0397\u0001\u0000\u0000"+
		"\u0000\u039ai\u0001\u0000\u0000\u0000\u039b\u039c\u0005%\u0000\u0000\u039c"+
		"\u039d\u0003\u00e2q\u0000\u039d\u039e\u00052\u0000\u0000\u039e\u03a3\u0003"+
		">\u001f\u0000\u039f\u03a4\u0003j5\u0000\u03a0\u03a2\u0003l6\u0000\u03a1"+
		"\u03a0\u0001\u0000\u0000\u0000\u03a1\u03a2\u0001\u0000\u0000\u0000\u03a2"+
		"\u03a4\u0001\u0000\u0000\u0000\u03a3\u039f\u0001\u0000\u0000\u0000\u03a3"+
		"\u03a1\u0001\u0000\u0000\u0000\u03a4k\u0001\u0000\u0000\u0000\u03a5\u03a6"+
		"\u0005\b\u0000\u0000\u03a6\u03a7\u00052\u0000\u0000\u03a7\u03a8\u0003"+
		">\u001f\u0000\u03a8m\u0001\u0000\u0000\u0000\u03a9\u03aa\u0005\u001e\u0000"+
		"\u0000\u03aa\u03ab\u0003\u00e2q\u0000\u03ab\u03ac\u00052\u0000\u0000\u03ac"+
		"\u03ae\u0003>\u001f\u0000\u03ad\u03af\u0003l6\u0000\u03ae\u03ad\u0001"+
		"\u0000\u0000\u0000\u03ae\u03af\u0001\u0000\u0000\u0000\u03afo\u0001\u0000"+
		"\u0000\u0000\u03b0\u03b2\u0005$\u0000\u0000\u03b1\u03b0\u0001\u0000\u0000"+
		"\u0000\u03b1\u03b2\u0001\u0000\u0000\u0000\u03b2\u03b3\u0001\u0000\u0000"+
		"\u0000\u03b3\u03b4\u0005\u0017\u0000\u0000\u03b4\u03b5\u0003\u016e\u00b7"+
		"\u0000\u03b5\u03b6\u0005\u000e\u0000\u0000\u03b6\u03b7\u0003\u00d8l\u0000"+
		"\u03b7\u03b9\u00052\u0000\u0000\u03b8\u03ba\u0005`\u0000\u0000\u03b9\u03b8"+
		"\u0001\u0000\u0000\u0000\u03b9\u03ba\u0001\u0000\u0000\u0000\u03ba\u03bb"+
		"\u0001\u0000\u0000\u0000\u03bb\u03bd\u0003>\u001f\u0000\u03bc\u03be\u0003"+
		"l6\u0000\u03bd\u03bc\u0001\u0000\u0000\u0000\u03bd\u03be\u0001\u0000\u0000"+
		"\u0000\u03beq\u0001\u0000\u0000\u0000\u03bf\u03c1\u0005$\u0000\u0000\u03c0"+
		"\u03bf\u0001\u0000\u0000\u0000\u03c0\u03c1\u0001\u0000\u0000\u0000\u03c1"+
		"\u03c2\u0001\u0000\u0000\u0000\u03c2\u03de\u0005#\u0000\u0000\u03c3\u03c4"+
		"\u0005+\u0000\u0000\u03c4\u03c9\u0003t:\u0000\u03c5\u03c6\u00053\u0000"+
		"\u0000\u03c6\u03c8\u0003t:\u0000\u03c7\u03c5\u0001\u0000\u0000\u0000\u03c8"+
		"\u03cb\u0001\u0000\u0000\u0000\u03c9\u03c7\u0001\u0000\u0000\u0000\u03c9"+
		"\u03ca\u0001\u0000\u0000\u0000\u03ca\u03cd\u0001\u0000\u0000\u0000\u03cb"+
		"\u03c9\u0001\u0000\u0000\u0000\u03cc\u03ce\u00053\u0000\u0000\u03cd\u03cc"+
		"\u0001\u0000\u0000\u0000\u03cd\u03ce\u0001\u0000\u0000\u0000\u03ce\u03cf"+
		"\u0001\u0000\u0000\u0000\u03cf\u03d0\u0005.\u0000\u0000\u03d0\u03d1\u0005"+
		"2\u0000\u0000\u03d1\u03df\u0001\u0000\u0000\u0000\u03d2\u03d7\u0003t:"+
		"\u0000\u03d3\u03d4\u00053\u0000\u0000\u03d4\u03d6\u0003t:\u0000\u03d5"+
		"\u03d3\u0001\u0000\u0000\u0000\u03d6\u03d9\u0001\u0000\u0000\u0000\u03d7"+
		"\u03d5\u0001\u0000\u0000\u0000\u03d7\u03d8\u0001\u0000\u0000\u0000\u03d8"+
		"\u03da\u0001\u0000\u0000\u0000\u03d9\u03d7\u0001\u0000\u0000\u0000\u03da"+
		"\u03dc\u00052\u0000\u0000\u03db\u03dd\u0005`\u0000\u0000\u03dc\u03db\u0001"+
		"\u0000\u0000\u0000\u03dc\u03dd\u0001\u0000\u0000\u0000\u03dd\u03df\u0001"+
		"\u0000\u0000\u0000\u03de\u03c3\u0001\u0000\u0000\u0000\u03de\u03d2\u0001"+
		"\u0000\u0000\u0000\u03df\u03e0\u0001\u0000\u0000\u0000\u03e0\u03e1\u0003"+
		">\u001f\u0000\u03e1s\u0001\u0000\u0000\u0000\u03e2\u03e5\u0003\u00d4j"+
		"\u0000\u03e3\u03e4\u0005\u001a\u0000\u0000\u03e4\u03e6\u0003\u0174\u00ba"+
		"\u0000\u03e5\u03e3\u0001\u0000\u0000\u0000\u03e5\u03e6\u0001\u0000\u0000"+
		"\u0000\u03e6u\u0001\u0000\u0000\u0000\u03e7\u03e8\u0005\u0019\u0000\u0000"+
		"\u03e8\u03e9\u00052\u0000\u0000\u03e9\u03ea\u0003>\u001f\u0000\u03ea\u03eb"+
		"\u0003|>\u0000\u03eb\u0409\u0001\u0000\u0000\u0000\u03ec\u03ed\u0005\u0019"+
		"\u0000\u0000\u03ed\u03ee\u00052\u0000\u0000\u03ee\u03f0\u0003>\u001f\u0000"+
		"\u03ef\u03f1\u0003x<\u0000\u03f0\u03ef\u0001\u0000\u0000\u0000\u03f1\u03f2"+
		"\u0001\u0000\u0000\u0000\u03f2\u03f0\u0001\u0000\u0000\u0000\u03f2\u03f3"+
		"\u0001\u0000\u0000\u0000\u03f3\u03f5\u0001\u0000\u0000\u0000\u03f4\u03f6"+
		"\u0003l6\u0000\u03f5\u03f4\u0001\u0000\u0000\u0000\u03f5\u03f6\u0001\u0000"+
		"\u0000\u0000\u03f6\u03f8\u0001\u0000\u0000\u0000\u03f7\u03f9\u0003|>\u0000"+
		"\u03f8\u03f7\u0001\u0000\u0000\u0000\u03f8\u03f9\u0001\u0000\u0000\u0000"+
		"\u03f9\u0409\u0001\u0000\u0000\u0000\u03fa\u03fb\u0005\u0019\u0000\u0000"+
		"\u03fb\u03fc\u00052\u0000\u0000\u03fc\u03fe\u0003>\u001f\u0000\u03fd\u03ff"+
		"\u0003z=\u0000\u03fe\u03fd\u0001\u0000\u0000\u0000\u03ff\u0400\u0001\u0000"+
		"\u0000\u0000\u0400\u03fe\u0001\u0000\u0000\u0000\u0400\u0401\u0001\u0000"+
		"\u0000\u0000\u0401\u0403\u0001\u0000\u0000\u0000\u0402\u0404\u0003l6\u0000"+
		"\u0403\u0402\u0001\u0000\u0000\u0000\u0403\u0404\u0001\u0000\u0000\u0000"+
		"\u0404\u0406\u0001\u0000\u0000\u0000\u0405\u0407\u0003|>\u0000\u0406\u0405"+
		"\u0001\u0000\u0000\u0000\u0406\u0407\u0001\u0000\u0000\u0000\u0407\u0409"+
		"\u0001\u0000\u0000\u0000\u0408\u03e7\u0001\u0000\u0000\u0000\u0408\u03ec"+
		"\u0001\u0000\u0000\u0000\u0408\u03fa\u0001\u0000\u0000\u0000\u0409w\u0001"+
		"\u0000\u0000\u0000\u040a\u0410\u0005\r\u0000\u0000\u040b\u040e\u0003\u00d4"+
		"j\u0000\u040c\u040d\u0005\u001a\u0000\u0000\u040d\u040f\u0005]\u0000\u0000"+
		"\u040e\u040c\u0001\u0000\u0000\u0000\u040e\u040f\u0001\u0000\u0000\u0000"+
		"\u040f\u0411\u0001\u0000\u0000\u0000\u0410\u040b\u0001\u0000\u0000\u0000"+
		"\u0410\u0411\u0001\u0000\u0000\u0000\u0411\u0412\u0001\u0000\u0000\u0000"+
		"\u0412\u0413\u00052\u0000\u0000\u0413\u0414\u0003>\u001f\u0000\u0414y"+
		"\u0001\u0000\u0000\u0000\u0415\u0416\u0005\r\u0000\u0000\u0416\u0417\u0005"+
		"7\u0000\u0000\u0417\u041a\u0003\u00d4j\u0000\u0418\u0419\u0005\u001a\u0000"+
		"\u0000\u0419\u041b\u0005]\u0000\u0000\u041a\u0418\u0001\u0000\u0000\u0000"+
		"\u041a\u041b\u0001\u0000\u0000\u0000\u041b\u041c\u0001\u0000\u0000\u0000"+
		"\u041c\u041d\u00052\u0000\u0000\u041d\u041e\u0003>\u001f\u0000\u041e{"+
		"\u0001\u0000\u0000\u0000\u041f\u0420\u0005\u0012\u0000\u0000\u0420\u0421"+
		"\u00052\u0000\u0000\u0421\u0422\u0003>\u001f\u0000\u0422}\u0001\u0000"+
		"\u0000\u0000\u0423\u0424\u0003\u018c\u00c6\u0000\u0424\u0425\u0003\u0080"+
		"@\u0000\u0425\u0426\u00052\u0000\u0000\u0426\u0427\u0005a\u0000\u0000"+
		"\u0427\u0429\u0005\u0001\u0000\u0000\u0428\u042a\u0003\u0082A\u0000\u0429"+
		"\u0428\u0001\u0000\u0000\u0000\u042a\u042b\u0001\u0000\u0000\u0000\u042b"+
		"\u0429\u0001\u0000\u0000\u0000\u042b\u042c\u0001\u0000\u0000\u0000\u042c"+
		"\u042d\u0001\u0000\u0000\u0000\u042d\u042e\u0005\u0002\u0000\u0000\u042e"+
		"\u007f\u0001\u0000\u0000\u0000\u042f\u0430\u0003\u00deo\u0000\u0430\u0432"+
		"\u00053\u0000\u0000\u0431\u0433\u0003\u00dcn\u0000\u0432\u0431\u0001\u0000"+
		"\u0000\u0000\u0432\u0433\u0001\u0000\u0000\u0000\u0433\u0436\u0001\u0000"+
		"\u0000\u0000\u0434\u0436\u0003\u00e2q\u0000\u0435\u042f\u0001\u0000\u0000"+
		"\u0000\u0435\u0434\u0001\u0000\u0000\u0000\u0436\u0081\u0001\u0000\u0000"+
		"\u0000\u0437\u0438\u0003\u018e\u00c7\u0000\u0438\u043a\u0003\u0086C\u0000"+
		"\u0439\u043b\u0003\u0084B\u0000\u043a\u0439\u0001\u0000\u0000\u0000\u043a"+
		"\u043b\u0001\u0000\u0000\u0000\u043b\u043c\u0001\u0000\u0000\u0000\u043c"+
		"\u043d\u00052\u0000\u0000\u043d\u043e\u0003>\u001f\u0000\u043e\u0083\u0001"+
		"\u0000\u0000\u0000\u043f\u0440\u0005&\u0000\u0000\u0440\u0441\u0003\u00e2"+
		"q\u0000\u0441\u0085\u0001\u0000\u0000\u0000\u0442\u0445\u0003\u00b0X\u0000"+
		"\u0443\u0445\u0003\u0088D\u0000\u0444\u0442\u0001\u0000\u0000\u0000\u0444"+
		"\u0443\u0001\u0000\u0000\u0000\u0445\u0087\u0001\u0000\u0000\u0000\u0446"+
		"\u0449\u0003\u008aE\u0000\u0447\u0449\u0003\u008cF\u0000\u0448\u0446\u0001"+
		"\u0000\u0000\u0000\u0448\u0447\u0001\u0000\u0000\u0000\u0449\u0089\u0001"+
		"\u0000\u0000\u0000\u044a\u044b\u0003\u008cF\u0000\u044b\u044c\u0005\u001a"+
		"\u0000\u0000\u044c\u044d\u0003\u00a2Q\u0000\u044d\u008b\u0001\u0000\u0000"+
		"\u0000\u044e\u0453\u0003\u008eG\u0000\u044f\u0450\u00059\u0000\u0000\u0450"+
		"\u0452\u0003\u008eG\u0000\u0451\u044f\u0001\u0000\u0000\u0000\u0452\u0455"+
		"\u0001\u0000\u0000\u0000\u0453\u0451\u0001\u0000\u0000\u0000\u0453\u0454"+
		"\u0001\u0000\u0000\u0000\u0454\u008d\u0001\u0000\u0000\u0000\u0455\u0453"+
		"\u0001\u0000\u0000\u0000\u0456\u045f\u0003\u0090H\u0000\u0457\u045f\u0003"+
		"\u00a0P\u0000\u0458\u045f\u0003\u00a4R\u0000\u0459\u045f\u0003\u00a6S"+
		"\u0000\u045a\u045f\u0003\u00acV\u0000\u045b\u045f\u0003\u00aeW\u0000\u045c"+
		"\u045f\u0003\u00b8\\\u0000\u045d\u045f\u0003\u00c0`\u0000\u045e\u0456"+
		"\u0001\u0000\u0000\u0000\u045e\u0457\u0001\u0000\u0000\u0000\u045e\u0458"+
		"\u0001\u0000\u0000\u0000\u045e\u0459\u0001\u0000\u0000\u0000\u045e\u045a"+
		"\u0001\u0000\u0000\u0000\u045e\u045b\u0001\u0000\u0000\u0000\u045e\u045c"+
		"\u0001\u0000\u0000\u0000\u045e\u045d\u0001\u0000\u0000\u0000\u045f\u008f"+
		"\u0001\u0000\u0000\u0000\u0460\u0468\u0003\u0098L\u0000\u0461\u0468\u0003"+
		"\u0094J\u0000\u0462\u0468\u0003\u0096K\u0000\u0463\u0468\u0003\u0146\u00a3"+
		"\u0000\u0464\u0468\u0005\u000b\u0000\u0000\u0465\u0468\u0005\u0010\u0000"+
		"\u0000\u0466\u0468\u0005\u0006\u0000\u0000\u0467\u0460\u0001\u0000\u0000"+
		"\u0000\u0467\u0461\u0001\u0000\u0000\u0000\u0467\u0462\u0001\u0000\u0000"+
		"\u0000\u0467\u0463\u0001\u0000\u0000\u0000\u0467\u0464\u0001\u0000\u0000"+
		"\u0000\u0467\u0465\u0001\u0000\u0000\u0000\u0467\u0466\u0001\u0000\u0000"+
		"\u0000\u0468\u0091\u0001\u0000\u0000\u0000\u0469\u0471\u0003\u0098L\u0000"+
		"\u046a\u0471\u0003\u0094J\u0000\u046b\u0471\u0003\u0096K\u0000\u046c\u0471"+
		"\u0003\u0146\u00a3\u0000\u046d\u0471\u0005\u000b\u0000\u0000\u046e\u0471"+
		"\u0005\u0010\u0000\u0000\u046f\u0471\u0005\u0006\u0000\u0000\u0470\u0469"+
		"\u0001\u0000\u0000\u0000\u0470\u046a\u0001\u0000\u0000\u0000\u0470\u046b"+
		"\u0001\u0000\u0000\u0000\u0470\u046c\u0001\u0000\u0000\u0000\u0470\u046d"+
		"\u0001\u0000\u0000\u0000\u0470\u046e\u0001\u0000\u0000\u0000\u0470\u046f"+
		"\u0001\u0000\u0000\u0000\u0471\u0093\u0001\u0000\u0000\u0000\u0472\u0474"+
		"\u00056\u0000\u0000\u0473\u0472\u0001\u0000\u0000\u0000\u0473\u0474\u0001"+
		"\u0000\u0000\u0000\u0474\u0475\u0001\u0000\u0000\u0000\u0475\u0476\u0005"+
		"^\u0000\u0000\u0476\u0477\u0007\u0002\u0000\u0000\u0477\u0095\u0001\u0000"+
		"\u0000\u0000\u0478\u0479\u0003\u009aM\u0000\u0479\u047a\u0007\u0003\u0000"+
		"\u0000\u047a\u047b\u0003\u009eO\u0000\u047b\u0097\u0001\u0000\u0000\u0000"+
		"\u047c\u047e\u00056\u0000\u0000\u047d\u047c\u0001\u0000\u0000\u0000\u047d"+
		"\u047e\u0001\u0000\u0000\u0000\u047e\u047f\u0001\u0000\u0000\u0000\u047f"+
		"\u0480\u0005^\u0000\u0000\u0480\u0099\u0001\u0000\u0000\u0000\u0481\u0483"+
		"\u00056\u0000\u0000\u0482\u0481\u0001\u0000\u0000\u0000\u0482\u0483\u0001"+
		"\u0000\u0000\u0000\u0483\u0484\u0001\u0000\u0000\u0000\u0484\u0485\u0003"+
		"\u009cN\u0000\u0485\u009b\u0001\u0000\u0000\u0000\u0486\u0487\u0005^\u0000"+
		"\u0000\u0487\u009d\u0001\u0000\u0000\u0000\u0488\u0489\u0005^\u0000\u0000"+
		"\u0489\u009f\u0001\u0000\u0000\u0000\u048a\u048b\u0003\u00a2Q\u0000\u048b"+
		"\u00a1\u0001\u0000\u0000\u0000\u048c\u048d\u0003\u0192\u00c9\u0000\u048d"+
		"\u00a3\u0001\u0000\u0000\u0000\u048e\u048f\u0003\u0190\u00c8\u0000\u048f"+
		"\u00a5\u0001\u0000\u0000\u0000\u0490\u0491\u0003\u00a8T\u0000\u0491\u00a7"+
		"\u0001\u0000\u0000\u0000\u0492\u0495\u0005]\u0000\u0000\u0493\u0494\u0005"+
		"1\u0000\u0000\u0494\u0496\u0005]\u0000\u0000\u0495\u0493\u0001\u0000\u0000"+
		"\u0000\u0496\u0497\u0001\u0000\u0000\u0000\u0497\u0495\u0001\u0000\u0000"+
		"\u0000\u0497\u0498\u0001\u0000\u0000\u0000\u0498\u00a9\u0001\u0000\u0000"+
		"\u0000\u0499\u049e\u0005]\u0000\u0000\u049a\u049b\u00051\u0000\u0000\u049b"+
		"\u049d\u0005]\u0000\u0000\u049c\u049a\u0001\u0000\u0000\u0000\u049d\u04a0"+
		"\u0001\u0000\u0000\u0000\u049e\u049c\u0001\u0000\u0000\u0000\u049e\u049f"+
		"\u0001\u0000\u0000\u0000\u049f\u00ab\u0001\u0000\u0000\u0000\u04a0\u049e"+
		"\u0001\u0000\u0000\u0000\u04a1\u04a2\u0005+\u0000\u0000\u04a2\u04a3\u0003"+
		"\u0088D\u0000\u04a3\u04a4\u0005.\u0000\u0000\u04a4\u00ad\u0001\u0000\u0000"+
		"\u0000\u04a5\u04a7\u0005,\u0000\u0000\u04a6\u04a8\u0003\u00b2Y\u0000\u04a7"+
		"\u04a6\u0001\u0000\u0000\u0000\u04a7\u04a8\u0001\u0000\u0000\u0000\u04a8"+
		"\u04a9\u0001\u0000\u0000\u0000\u04a9\u04b0\u0005/\u0000\u0000\u04aa\u04ac"+
		"\u0005+\u0000\u0000\u04ab\u04ad\u0003\u00b0X\u0000\u04ac\u04ab\u0001\u0000"+
		"\u0000\u0000\u04ac\u04ad\u0001\u0000\u0000\u0000\u04ad\u04ae\u0001\u0000"+
		"\u0000\u0000\u04ae\u04b0\u0005.\u0000\u0000\u04af\u04a5\u0001\u0000\u0000"+
		"\u0000\u04af\u04aa\u0001\u0000\u0000\u0000\u04b0\u00af\u0001\u0000\u0000"+
		"\u0000\u04b1\u04b2\u0003\u00b4Z\u0000\u04b2\u04b4\u00053\u0000\u0000\u04b3"+
		"\u04b5\u0003\u00b2Y\u0000\u04b4\u04b3\u0001\u0000\u0000\u0000\u04b4\u04b5"+
		"\u0001\u0000\u0000\u0000\u04b5\u00b1\u0001\u0000\u0000\u0000\u04b6\u04bb"+
		"\u0003\u00b4Z\u0000\u04b7\u04b8\u00053\u0000\u0000\u04b8\u04ba\u0003\u00b4"+
		"Z\u0000\u04b9\u04b7\u0001\u0000\u0000\u0000\u04ba\u04bd\u0001\u0000\u0000"+
		"\u0000\u04bb\u04b9\u0001\u0000\u0000\u0000\u04bb\u04bc\u0001\u0000\u0000"+
		"\u0000\u04bc\u04bf\u0001\u0000\u0000\u0000\u04bd\u04bb\u0001\u0000\u0000"+
		"\u0000\u04be\u04c0\u00053\u0000\u0000\u04bf\u04be\u0001\u0000\u0000\u0000"+
		"\u04bf\u04c0\u0001\u0000\u0000\u0000\u04c0\u00b3\u0001\u0000\u0000\u0000"+
		"\u04c1\u04c4\u0003\u00b6[\u0000\u04c2\u04c4\u0003\u0088D\u0000\u04c3\u04c1"+
		"\u0001\u0000\u0000\u0000\u04c3\u04c2\u0001\u0000\u0000\u0000\u04c4\u00b5"+
		"\u0001\u0000\u0000\u0000\u04c5\u04c6\u00057\u0000\u0000\u04c6\u04ca\u0003"+
		"\u00a2Q\u0000\u04c7\u04c8\u00057\u0000\u0000\u04c8\u04ca\u0003\u00a4R"+
		"\u0000\u04c9\u04c5\u0001\u0000\u0000\u0000\u04c9\u04c7\u0001\u0000\u0000"+
		"\u0000\u04ca\u00b7\u0001\u0000\u0000\u0000\u04cb\u04cc\u0005-\u0000\u0000"+
		"\u04cc\u04e0\u00050\u0000\u0000\u04cd\u04ce\u0005-\u0000\u0000\u04ce\u04d0"+
		"\u0003\u00be_\u0000\u04cf\u04d1\u00053\u0000\u0000\u04d0\u04cf\u0001\u0000"+
		"\u0000\u0000\u04d0\u04d1\u0001\u0000\u0000\u0000\u04d1\u04d2\u0001\u0000"+
		"\u0000\u0000\u04d2\u04d3\u00050\u0000\u0000\u04d3\u04e0\u0001\u0000\u0000"+
		"\u0000\u04d4\u04d5\u0005-\u0000\u0000\u04d5\u04d8\u0003\u00ba]\u0000\u04d6"+
		"\u04d7\u00053\u0000\u0000\u04d7\u04d9\u0003\u00be_\u0000\u04d8\u04d6\u0001"+
		"\u0000\u0000\u0000\u04d8\u04d9\u0001\u0000\u0000\u0000\u04d9\u04db\u0001"+
		"\u0000\u0000\u0000\u04da\u04dc\u00053\u0000\u0000\u04db\u04da\u0001\u0000"+
		"\u0000\u0000\u04db\u04dc\u0001\u0000\u0000\u0000\u04dc\u04dd\u0001\u0000"+
		"\u0000\u0000\u04dd\u04de\u00050\u0000\u0000\u04de\u04e0\u0001\u0000\u0000"+
		"\u0000\u04df\u04cb\u0001\u0000\u0000\u0000\u04df\u04cd\u0001\u0000\u0000"+
		"\u0000\u04df\u04d4\u0001\u0000\u0000\u0000\u04e0\u00b9\u0001\u0000\u0000"+
		"\u0000\u04e1\u04e6\u0003\u00bc^\u0000\u04e2\u04e3\u00053\u0000\u0000\u04e3"+
		"\u04e5\u0003\u00bc^\u0000\u04e4\u04e2\u0001\u0000\u0000\u0000\u04e5\u04e8"+
		"\u0001\u0000\u0000\u0000\u04e6\u04e4\u0001\u0000\u0000\u0000\u04e6\u04e7"+
		"\u0001\u0000\u0000\u0000\u04e7\u00bb\u0001\u0000\u0000\u0000\u04e8\u04e6"+
		"\u0001\u0000\u0000\u0000\u04e9\u04ec\u0003\u0092I\u0000\u04ea\u04ec\u0003"+
		"\u00a8T\u0000\u04eb\u04e9\u0001\u0000\u0000\u0000\u04eb\u04ea\u0001\u0000"+
		"\u0000\u0000\u04ec\u04ed\u0001\u0000\u0000\u0000\u04ed\u04ee\u00052\u0000"+
		"\u0000\u04ee\u04ef\u0003\u0088D\u0000\u04ef\u00bd\u0001\u0000\u0000\u0000"+
		"\u04f0\u04f1\u0005G\u0000\u0000\u04f1\u04f2\u0003\u00a2Q\u0000\u04f2\u00bf"+
		"\u0001\u0000\u0000\u0000\u04f3\u04f4\u0003\u00aaU\u0000\u04f4\u0500\u0005"+
		"+\u0000\u0000\u04f5\u04f8\u0003\u00c2a\u0000\u04f6\u04f7\u00053\u0000"+
		"\u0000\u04f7\u04f9\u0003\u00c4b\u0000\u04f8\u04f6\u0001\u0000\u0000\u0000"+
		"\u04f8\u04f9\u0001\u0000\u0000\u0000\u04f9\u04fc\u0001\u0000\u0000\u0000"+
		"\u04fa\u04fc\u0003\u00c4b\u0000\u04fb\u04f5\u0001\u0000\u0000\u0000\u04fb"+
		"\u04fa\u0001\u0000\u0000\u0000\u04fc\u04fe\u0001\u0000\u0000\u0000\u04fd"+
		"\u04ff\u00053\u0000\u0000\u04fe\u04fd\u0001\u0000\u0000\u0000\u04fe\u04ff"+
		"\u0001\u0000\u0000\u0000\u04ff\u0501\u0001\u0000\u0000\u0000\u0500\u04fb"+
		"\u0001\u0000\u0000\u0000\u0500\u0501\u0001\u0000\u0000\u0000\u0501\u0502"+
		"\u0001\u0000\u0000\u0000\u0502\u0503\u0005.\u0000\u0000\u0503\u00c1\u0001"+
		"\u0000\u0000\u0000\u0504\u0509\u0003\u0088D\u0000\u0505\u0506\u00053\u0000"+
		"\u0000\u0506\u0508\u0003\u0088D\u0000\u0507\u0505\u0001\u0000\u0000\u0000"+
		"\u0508\u050b\u0001\u0000\u0000\u0000\u0509\u0507\u0001\u0000\u0000\u0000"+
		"\u0509\u050a\u0001\u0000\u0000\u0000\u050a\u00c3\u0001\u0000\u0000\u0000"+
		"\u050b\u0509\u0001\u0000\u0000\u0000\u050c\u0511\u0003\u00c6c\u0000\u050d"+
		"\u050e\u00053\u0000\u0000\u050e\u0510\u0003\u00c6c\u0000\u050f\u050d\u0001"+
		"\u0000\u0000\u0000\u0510\u0513\u0001\u0000\u0000\u0000\u0511\u050f\u0001"+
		"\u0000\u0000\u0000\u0511\u0512\u0001\u0000\u0000\u0000\u0512\u00c5\u0001"+
		"\u0000\u0000\u0000\u0513\u0511\u0001\u0000\u0000\u0000\u0514\u0515\u0005"+
		"]\u0000\u0000\u0515\u0516\u0005=\u0000\u0000\u0516\u0517\u0003\u0088D"+
		"\u0000\u0517\u00c7\u0001\u0000\u0000\u0000\u0518\u0519\u0003\u018a\u00c5"+
		"\u0000\u0519\u051b\u0005]\u0000\u0000\u051a\u051c\u0003\u00cae\u0000\u051b"+
		"\u051a\u0001\u0000\u0000\u0000\u051b\u051c\u0001\u0000\u0000\u0000\u051c"+
		"\u051d\u0001\u0000\u0000\u0000\u051d\u051e\u0005=\u0000\u0000\u051e\u051f"+
		"\u0003\u00d4j\u0000\u051f\u00c9\u0001\u0000\u0000\u0000\u0520\u0521\u0005"+
		",\u0000\u0000\u0521\u0522\u0003\u00ccf\u0000\u0522\u0523\u0005/\u0000"+
		"\u0000\u0523\u00cb\u0001\u0000\u0000\u0000\u0524\u0529\u0003\u00ceg\u0000"+
		"\u0525\u0526\u00053\u0000\u0000\u0526\u0528\u0003\u00ceg\u0000\u0527\u0525"+
		"\u0001\u0000\u0000\u0000\u0528\u052b\u0001\u0000\u0000\u0000\u0529\u0527"+
		"\u0001\u0000\u0000\u0000\u0529\u052a\u0001\u0000\u0000\u0000\u052a\u052d"+
		"\u0001\u0000\u0000\u0000\u052b\u0529\u0001\u0000\u0000\u0000\u052c\u052e"+
		"\u00053\u0000\u0000\u052d\u052c\u0001\u0000\u0000\u0000\u052d\u052e\u0001"+
		"\u0000\u0000\u0000\u052e\u00cd\u0001\u0000\u0000\u0000\u052f\u0531\u0005"+
		"]\u0000\u0000\u0530\u0532\u0003\u00d0h\u0000\u0531\u0530\u0001\u0000\u0000"+
		"\u0000\u0531\u0532\u0001\u0000\u0000\u0000\u0532\u0540\u0001\u0000\u0000"+
		"\u0000\u0533\u0534\u00057\u0000\u0000\u0534\u0537\u0005]\u0000\u0000\u0535"+
		"\u0536\u00052\u0000\u0000\u0536\u0538\u0003\u00d4j\u0000\u0537\u0535\u0001"+
		"\u0000\u0000\u0000\u0537\u0538\u0001\u0000\u0000\u0000\u0538\u0540\u0001"+
		"\u0000\u0000\u0000\u0539\u053a\u0005G\u0000\u0000\u053a\u053d\u0005]\u0000"+
		"\u0000\u053b\u053c\u00052\u0000\u0000\u053c\u053e\u0003\u00d4j\u0000\u053d"+
		"\u053b\u0001\u0000\u0000\u0000\u053d\u053e\u0001\u0000\u0000\u0000\u053e"+
		"\u0540\u0001\u0000\u0000\u0000\u053f\u052f\u0001\u0000\u0000\u0000\u053f"+
		"\u0533\u0001\u0000\u0000\u0000\u053f\u0539\u0001\u0000\u0000\u0000\u0540"+
		"\u00cf\u0001\u0000\u0000\u0000\u0541\u0542\u00052\u0000\u0000\u0542\u0543"+
		"\u0003\u00d4j\u0000\u0543\u00d1\u0001\u0000\u0000\u0000\u0544\u0549\u0003"+
		"\u00d4j\u0000\u0545\u0546\u00053\u0000\u0000\u0546\u0548\u0003\u00d4j"+
		"\u0000\u0547\u0545\u0001\u0000\u0000\u0000\u0548\u054b\u0001\u0000\u0000"+
		"\u0000\u0549\u0547\u0001\u0000\u0000\u0000\u0549\u054a\u0001\u0000\u0000"+
		"\u0000\u054a\u054d\u0001\u0000\u0000\u0000\u054b\u0549\u0001\u0000\u0000"+
		"\u0000\u054c\u054e\u00053\u0000\u0000\u054d\u054c\u0001\u0000\u0000\u0000"+
		"\u054d\u054e\u0001\u0000\u0000\u0000\u054e\u00d3\u0001\u0000\u0000\u0000"+
		"\u054f\u0555\u0003\u00e4r\u0000\u0550\u0551\u0005&\u0000\u0000\u0551\u0552"+
		"\u0003\u00e4r\u0000\u0552\u0553\u0005\b\u0000\u0000\u0553\u0554\u0003"+
		"\u00d4j\u0000\u0554\u0556\u0001\u0000\u0000\u0000\u0555\u0550\u0001\u0000"+
		"\u0000\u0000\u0555\u0556\u0001\u0000\u0000\u0000\u0556\u0559\u0001\u0000"+
		"\u0000\u0000\u0557\u0559\u0003\u0122\u0091\u0000\u0558\u054f\u0001\u0000"+
		"\u0000\u0000\u0558\u0557\u0001\u0000\u0000\u0000\u0559\u00d5\u0001\u0000"+
		"\u0000\u0000\u055a\u0560\u0005(\u0000\u0000\u055b\u055c\u0005\u001c\u0000"+
		"\u0000\u055c\u0561\u0003\u00d4j\u0000\u055d\u055f\u0003\u00d8l\u0000\u055e"+
		"\u055d\u0001\u0000\u0000\u0000\u055e\u055f\u0001\u0000\u0000\u0000\u055f"+
		"\u0561\u0001\u0000\u0000\u0000\u0560\u055b\u0001\u0000\u0000\u0000\u0560"+
		"\u055e\u0001\u0000\u0000\u0000\u0561\u00d7\u0001\u0000\u0000\u0000\u0562"+
		"\u0567\u0003\u00dam\u0000\u0563\u0564\u00053\u0000\u0000\u0564\u0566\u0003"+
		"\u00dam\u0000\u0565\u0563\u0001\u0000\u0000\u0000\u0566\u0569\u0001\u0000"+
		"\u0000\u0000\u0567\u0565\u0001\u0000\u0000\u0000\u0567\u0568\u0001\u0000"+
		"\u0000\u0000\u0568\u056b\u0001\u0000\u0000\u0000\u0569\u0567\u0001\u0000"+
		"\u0000\u0000\u056a\u056c\u00053\u0000\u0000\u056b\u056a\u0001\u0000\u0000"+
		"\u0000\u056b\u056c\u0001\u0000\u0000\u0000\u056c\u00d9\u0001\u0000\u0000"+
		"\u0000\u056d\u056e\u00057\u0000\u0000\u056e\u0571\u0003\u0102\u0081\u0000"+
		"\u056f\u0571\u0003\u00d4j\u0000\u0570\u056d\u0001\u0000\u0000\u0000\u0570"+
		"\u056f\u0001\u0000\u0000\u0000\u0571\u00db\u0001\u0000\u0000\u0000\u0572"+
		"\u0577\u0003\u00deo\u0000\u0573\u0574\u00053\u0000\u0000\u0574\u0576\u0003"+
		"\u00deo\u0000\u0575\u0573\u0001\u0000\u0000\u0000\u0576\u0579\u0001\u0000"+
		"\u0000\u0000\u0577\u0575\u0001\u0000\u0000\u0000\u0577\u0578\u0001\u0000"+
		"\u0000\u0000\u0578\u057b\u0001\u0000\u0000\u0000\u0579\u0577\u0001\u0000"+
		"\u0000\u0000\u057a\u057c\u00053\u0000\u0000\u057b\u057a\u0001\u0000\u0000"+
		"\u0000\u057b\u057c\u0001\u0000\u0000\u0000\u057c\u00dd\u0001\u0000\u0000"+
		"\u0000\u057d\u057e\u00057\u0000\u0000\u057e\u0581\u0003\u0102\u0081\u0000"+
		"\u057f\u0581\u0003\u00e2q\u0000\u0580\u057d\u0001\u0000\u0000\u0000\u0580"+
		"\u057f\u0001\u0000\u0000\u0000\u0581\u00df\u0001\u0000\u0000\u0000\u0582"+
		"\u0583\u0005]\u0000\u0000\u0583\u0584\u0005Y\u0000\u0000\u0584\u0585\u0003"+
		"\u00d4j\u0000\u0585\u00e1\u0001\u0000\u0000\u0000\u0586\u0589\u0003\u00e0"+
		"p\u0000\u0587\u0589\u0003\u00d4j\u0000\u0588\u0586\u0001\u0000\u0000\u0000"+
		"\u0588\u0587\u0001\u0000\u0000\u0000\u0589\u00e3\u0001\u0000\u0000\u0000"+
		"\u058a\u058f\u0003\u00e6s\u0000\u058b\u058c\u0005\'\u0000\u0000\u058c"+
		"\u058e\u0003\u00e6s\u0000\u058d\u058b\u0001\u0000\u0000\u0000\u058e\u0591"+
		"\u0001\u0000\u0000\u0000\u058f\u058d\u0001\u0000\u0000\u0000\u058f\u0590"+
		"\u0001\u0000\u0000\u0000\u0590\u00e5\u0001\u0000\u0000\u0000\u0591\u058f"+
		"\u0001\u0000\u0000\u0000\u0592\u0597\u0003\u00e8t\u0000\u0593\u0594\u0005"+
		"\u0015\u0000\u0000\u0594\u0596\u0003\u00e8t\u0000\u0595\u0593\u0001\u0000"+
		"\u0000\u0000\u0596\u0599\u0001\u0000\u0000\u0000\u0597\u0595\u0001\u0000"+
		"\u0000\u0000\u0597\u0598\u0001\u0000\u0000\u0000\u0598\u00e7\u0001\u0000"+
		"\u0000\u0000\u0599\u0597\u0001\u0000\u0000\u0000\u059a\u059b\u0005\"\u0000"+
		"\u0000\u059b\u059e\u0003\u00e8t\u0000\u059c\u059e\u0003\u00eau\u0000\u059d"+
		"\u059a\u0001\u0000\u0000\u0000\u059d\u059c\u0001\u0000\u0000\u0000\u059e"+
		"\u00e9\u0001\u0000\u0000\u0000\u059f\u05a3\u0003\u0102\u0081\u0000\u05a0"+
		"\u05a2\u0003\u00ecv\u0000\u05a1\u05a0\u0001\u0000\u0000\u0000\u05a2\u05a5"+
		"\u0001\u0000\u0000\u0000\u05a3\u05a1\u0001\u0000\u0000\u0000\u05a3\u05a4"+
		"\u0001\u0000\u0000\u0000\u05a4\u00eb\u0001\u0000\u0000\u0000\u05a5\u05a3"+
		"\u0001\u0000\u0000\u0000\u05a6\u05b1\u0003\u00eew\u0000\u05a7\u05b1\u0003"+
		"\u00f0x\u0000\u05a8\u05b1\u0003\u00f2y\u0000\u05a9\u05b1\u0003\u00f4z"+
		"\u0000\u05aa\u05b1\u0003\u00f6{\u0000\u05ab\u05b1\u0003\u00f8|\u0000\u05ac"+
		"\u05b1\u0003\u00fa}\u0000\u05ad\u05b1\u0003\u00fc~\u0000\u05ae\u05b1\u0003"+
		"\u00fe\u007f\u0000\u05af\u05b1\u0003\u0100\u0080\u0000\u05b0\u05a6\u0001"+
		"\u0000\u0000\u0000\u05b0\u05a7\u0001\u0000\u0000\u0000\u05b0\u05a8\u0001"+
		"\u0000\u0000\u0000\u05b0\u05a9\u0001\u0000\u0000\u0000\u05b0\u05aa\u0001"+
		"\u0000\u0000\u0000\u05b0\u05ab\u0001\u0000\u0000\u0000\u05b0\u05ac\u0001"+
		"\u0000\u0000\u0000\u05b0\u05ad\u0001\u0000\u0000\u0000\u05b0\u05ae\u0001"+
		"\u0000\u0000\u0000\u05b0\u05af\u0001\u0000\u0000\u0000\u05b1\u00ed\u0001"+
		"\u0000\u0000\u0000\u05b2\u05b3\u0005?\u0000\u0000\u05b3\u05b4\u0003\u0102"+
		"\u0081\u0000\u05b4\u00ef\u0001\u0000\u0000\u0000\u05b5\u05b6\u0005@\u0000"+
		"\u0000\u05b6\u05b7\u0003\u0102\u0081\u0000\u05b7\u00f1\u0001\u0000\u0000"+
		"\u0000\u05b8\u05b9\u0005A\u0000\u0000\u05b9\u05ba\u0003\u0102\u0081\u0000"+
		"\u05ba\u00f3\u0001\u0000\u0000\u0000\u05bb\u05bc\u0005;\u0000\u0000\u05bc"+
		"\u05bd\u0003\u0102\u0081\u0000\u05bd\u00f5\u0001\u0000\u0000\u0000\u05be"+
		"\u05bf\u0005B\u0000\u0000\u05bf\u05c0\u0003\u0102\u0081\u0000\u05c0\u00f7"+
		"\u0001\u0000\u0000\u0000\u05c1\u05c2\u0005<\u0000\u0000\u05c2\u05c3\u0003"+
		"\u0102\u0081\u0000\u05c3\u00f9\u0001\u0000\u0000\u0000\u05c4\u05c5\u0005"+
		"\"\u0000\u0000\u05c5\u05c6\u0005\u000e\u0000\u0000\u05c6\u05c7\u0003\u0102"+
		"\u0081\u0000\u05c7\u00fb\u0001\u0000\u0000\u0000\u05c8\u05c9\u0005\u000e"+
		"\u0000\u0000\u05c9\u05ca\u0003\u0102\u0081\u0000\u05ca\u00fd\u0001\u0000"+
		"\u0000\u0000\u05cb\u05cc\u0005\u0013\u0000\u0000\u05cc\u05cd\u0005\"\u0000"+
		"\u0000\u05cd\u05ce\u0003\u0102\u0081\u0000\u05ce\u00ff\u0001\u0000\u0000"+
		"\u0000\u05cf\u05d0\u0005\u0013\u0000\u0000\u05d0\u05d1\u0003\u0102\u0081"+
		"\u0000\u05d1\u0101\u0001\u0000\u0000\u0000\u05d2\u05d3\u0006\u0081\uffff"+
		"\uffff\u0000\u05d3\u05d4\u0003\u0104\u0082\u0000\u05d4\u05da\u0001\u0000"+
		"\u0000\u0000\u05d5\u05d6\n\u0002\u0000\u0000\u05d6\u05d7\u00059\u0000"+
		"\u0000\u05d7\u05d9\u0003\u0104\u0082\u0000\u05d8\u05d5\u0001\u0000\u0000"+
		"\u0000\u05d9\u05dc\u0001\u0000\u0000\u0000\u05da\u05d8\u0001\u0000\u0000"+
		"\u0000\u05da\u05db\u0001\u0000\u0000\u0000\u05db\u0103\u0001\u0000\u0000"+
		"\u0000\u05dc\u05da\u0001\u0000\u0000\u0000\u05dd\u05de\u0006\u0082\uffff"+
		"\uffff\u0000\u05de\u05df\u0003\u0106\u0083\u0000\u05df\u05e5\u0001\u0000"+
		"\u0000\u0000\u05e0\u05e1\n\u0002\u0000\u0000\u05e1\u05e2\u0005D\u0000"+
		"\u0000\u05e2\u05e4\u0003\u0106\u0083\u0000\u05e3\u05e0\u0001\u0000\u0000"+
		"\u0000\u05e4\u05e7\u0001\u0000\u0000\u0000\u05e5\u05e3\u0001\u0000\u0000"+
		"\u0000\u05e5\u05e6\u0001\u0000\u0000\u0000\u05e6\u0105\u0001\u0000\u0000"+
		"\u0000\u05e7\u05e5\u0001\u0000\u0000\u0000\u05e8\u05e9\u0006\u0083\uffff"+
		"\uffff\u0000\u05e9\u05ea\u0003\u0108\u0084\u0000\u05ea\u05f0\u0001\u0000"+
		"\u0000\u0000\u05eb\u05ec\n\u0002\u0000\u0000\u05ec\u05ed\u0005:\u0000"+
		"\u0000\u05ed\u05ef\u0003\u0108\u0084\u0000\u05ee\u05eb\u0001\u0000\u0000"+
		"\u0000\u05ef\u05f2\u0001\u0000\u0000\u0000\u05f0\u05ee\u0001\u0000\u0000"+
		"\u0000\u05f0\u05f1\u0001\u0000\u0000\u0000\u05f1\u0107\u0001\u0000\u0000"+
		"\u0000\u05f2\u05f0\u0001\u0000\u0000\u0000\u05f3\u05f4\u0006\u0084\uffff"+
		"\uffff\u0000\u05f4\u05f5\u0003\u010a\u0085\u0000\u05f5\u05fb\u0001\u0000"+
		"\u0000\u0000\u05f6\u05f7\n\u0002\u0000\u0000\u05f7\u05f8\u0007\u0004\u0000"+
		"\u0000\u05f8\u05fa\u0003\u010a\u0085\u0000\u05f9\u05f6\u0001\u0000\u0000"+
		"\u0000\u05fa\u05fd\u0001\u0000\u0000\u0000\u05fb\u05f9\u0001\u0000\u0000"+
		"\u0000\u05fb\u05fc\u0001\u0000\u0000\u0000\u05fc\u0109\u0001\u0000\u0000"+
		"\u0000\u05fd\u05fb\u0001\u0000\u0000\u0000\u05fe\u05ff\u0006\u0085\uffff"+
		"\uffff\u0000\u05ff\u0600\u0003\u010c\u0086\u0000\u0600\u0606\u0001\u0000"+
		"\u0000\u0000\u0601\u0602\n\u0002\u0000\u0000\u0602\u0603\u0007\u0003\u0000"+
		"\u0000\u0603\u0605\u0003\u010c\u0086\u0000\u0604\u0601\u0001\u0000\u0000"+
		"\u0000\u0605\u0608\u0001\u0000\u0000\u0000\u0606\u0604\u0001\u0000\u0000"+
		"\u0000\u0606\u0607\u0001\u0000\u0000\u0000\u0607\u010b\u0001\u0000\u0000"+
		"\u0000\u0608\u0606\u0001\u0000\u0000\u0000\u0609\u060a\u0006\u0086\uffff"+
		"\uffff\u0000\u060a\u060b\u0003\u010e\u0087\u0000\u060b\u0611\u0001\u0000"+
		"\u0000\u0000\u060c\u060d\n\u0002\u0000\u0000\u060d\u060e\u0007\u0005\u0000"+
		"\u0000\u060e\u0610\u0003\u010e\u0087\u0000\u060f\u060c\u0001\u0000\u0000"+
		"\u0000\u0610\u0613\u0001\u0000\u0000\u0000\u0611\u060f\u0001\u0000\u0000"+
		"\u0000\u0611\u0612\u0001\u0000\u0000\u0000\u0612\u010d\u0001\u0000\u0000"+
		"\u0000\u0613\u0611\u0001\u0000\u0000\u0000\u0614\u0615\u0006\u0087\uffff"+
		"\uffff\u0000\u0615\u0616\u0003\u0110\u0088\u0000\u0616\u061c\u0001\u0000"+
		"\u0000\u0000\u0617\u0618\n\u0002\u0000\u0000\u0618\u0619\u0007\u0006\u0000"+
		"\u0000\u0619\u061b\u0003\u0110\u0088\u0000\u061a\u0617\u0001\u0000\u0000"+
		"\u0000\u061b\u061e\u0001\u0000\u0000\u0000\u061c\u061a\u0001\u0000\u0000"+
		"\u0000\u061c\u061d\u0001\u0000\u0000\u0000\u061d\u010f\u0001\u0000\u0000"+
		"\u0000\u061e\u061c\u0001\u0000\u0000\u0000\u061f\u0620\u00055\u0000\u0000"+
		"\u0620\u0627\u0003\u0110\u0088\u0000\u0621\u0622\u00056\u0000\u0000\u0622"+
		"\u0627\u0003\u0110\u0088\u0000\u0623\u0624\u0005C\u0000\u0000\u0624\u0627"+
		"\u0003\u0110\u0088\u0000\u0625\u0627\u0003\u0112\u0089\u0000\u0626\u061f"+
		"\u0001\u0000\u0000\u0000\u0626\u0621\u0001\u0000\u0000\u0000\u0626\u0623"+
		"\u0001\u0000\u0000\u0000\u0626\u0625\u0001\u0000\u0000\u0000\u0627\u0111"+
		"\u0001\u0000\u0000\u0000\u0628\u062b\u0003\u0114\u008a\u0000\u0629\u062a"+
		"\u0005G\u0000\u0000\u062a\u062c\u0003\u0110\u0088\u0000\u062b\u0629\u0001"+
		"\u0000\u0000\u0000\u062b\u062c\u0001\u0000\u0000\u0000\u062c\u0113\u0001"+
		"\u0000\u0000\u0000\u062d\u062e\u0005\u0007\u0000\u0000\u062e\u0631\u0003"+
		"\u0116\u008b\u0000\u062f\u0631\u0003\u0116\u008b\u0000\u0630\u062d\u0001"+
		"\u0000\u0000\u0000\u0630\u062f\u0001\u0000\u0000\u0000\u0631\u0115\u0001"+
		"\u0000\u0000\u0000\u0632\u0633\u0006\u008b\uffff\uffff\u0000\u0633\u0634"+
		"\u0003\u011c\u008e\u0000\u0634\u0646\u0001\u0000\u0000\u0000\u0635\u0642"+
		"\n\u0002\u0000\u0000\u0636\u0637\u00051\u0000\u0000\u0637\u0643\u0005"+
		"]\u0000\u0000\u0638\u0643\u0003\u015e\u00af\u0000\u0639\u063b\u0005+\u0000"+
		"\u0000\u063a\u063c\u0003\u0162\u00b1\u0000\u063b\u063a\u0001\u0000\u0000"+
		"\u0000\u063b\u063c\u0001\u0000\u0000\u0000\u063c\u063d\u0001\u0000\u0000"+
		"\u0000\u063d\u0643\u0005.\u0000\u0000\u063e\u063f\u0005,\u0000\u0000\u063f"+
		"\u0640\u0003\u0118\u008c\u0000\u0640\u0641\u0005/\u0000\u0000\u0641\u0643"+
		"\u0001\u0000\u0000\u0000\u0642\u0636\u0001\u0000\u0000\u0000\u0642\u0638"+
		"\u0001\u0000\u0000\u0000\u0642\u0639\u0001\u0000\u0000\u0000\u0642\u063e"+
		"\u0001\u0000\u0000\u0000\u0643\u0645\u0001\u0000\u0000\u0000\u0644\u0635"+
		"\u0001\u0000\u0000\u0000\u0645\u0648\u0001\u0000\u0000\u0000\u0646\u0644"+
		"\u0001\u0000\u0000\u0000\u0646\u0647\u0001\u0000\u0000\u0000\u0647\u0117"+
		"\u0001\u0000\u0000\u0000\u0648\u0646\u0001\u0000\u0000\u0000\u0649\u065c"+
		"\u0003\u011a\u008d\u0000\u064a\u064d\u0003\u011a\u008d\u0000\u064b\u064d"+
		"\u0003\u0168\u00b4\u0000\u064c\u064a\u0001\u0000\u0000\u0000\u064c\u064b"+
		"\u0001\u0000\u0000\u0000\u064d\u0655\u0001\u0000\u0000\u0000\u064e\u0651"+
		"\u00053\u0000\u0000\u064f\u0652\u0003\u011a\u008d\u0000\u0650\u0652\u0003"+
		"\u0168\u00b4\u0000\u0651\u064f\u0001\u0000\u0000\u0000\u0651\u0650\u0001"+
		"\u0000\u0000\u0000\u0652\u0654\u0001\u0000\u0000\u0000\u0653\u064e\u0001"+
		"\u0000\u0000\u0000\u0654\u0657\u0001\u0000\u0000\u0000\u0655\u0653\u0001"+
		"\u0000\u0000\u0000\u0655\u0656\u0001\u0000\u0000\u0000\u0656\u0659\u0001"+
		"\u0000\u0000\u0000\u0657\u0655\u0001\u0000\u0000\u0000\u0658\u065a\u0005"+
		"3\u0000\u0000\u0659\u0658\u0001\u0000\u0000\u0000\u0659\u065a\u0001\u0000"+
		"\u0000\u0000\u065a\u065c\u0001\u0000\u0000\u0000\u065b\u0649\u0001\u0000"+
		"\u0000\u0000\u065b\u064c\u0001\u0000\u0000\u0000\u065c\u0119\u0001\u0000"+
		"\u0000\u0000\u065d\u065f\u0003\u00d4j\u0000\u065e\u065d\u0001\u0000\u0000"+
		"\u0000\u065e\u065f\u0001\u0000\u0000\u0000\u065f\u0660\u0001\u0000\u0000"+
		"\u0000\u0660\u0662\u00052\u0000\u0000\u0661\u0663\u0003\u00d4j\u0000\u0662"+
		"\u0661\u0001\u0000\u0000\u0000\u0662\u0663\u0001\u0000\u0000\u0000\u0663"+
		"\u0668\u0001\u0000\u0000\u0000\u0664\u0666\u00052\u0000\u0000\u0665\u0667"+
		"\u0003\u00d4j\u0000\u0666\u0665\u0001\u0000\u0000\u0000\u0666\u0667\u0001"+
		"\u0000\u0000\u0000\u0667\u0669\u0001\u0000\u0000\u0000\u0668\u0664\u0001"+
		"\u0000\u0000\u0000\u0668\u0669\u0001\u0000\u0000\u0000\u0669\u066c\u0001"+
		"\u0000\u0000\u0000\u066a\u066c\u0003\u00e2q\u0000\u066b\u065e\u0001\u0000"+
		"\u0000\u0000\u066b\u066a\u0001\u0000\u0000\u0000\u066c\u011b\u0001\u0000"+
		"\u0000\u0000\u066d\u0685\u0005]\u0000\u0000\u066e\u0685\u0005\u0010\u0000"+
		"\u0000\u066f\u0685\u0005\u0006\u0000\u0000\u0670\u0685\u0005\u000b\u0000"+
		"\u0000\u0671\u0685\u0003\u0146\u00a3\u0000\u0672\u0685\u0003\u011e\u008f"+
		"\u0000\u0673\u0685\u0005^\u0000\u0000\u0674\u0678\u0003\u014a\u00a5\u0000"+
		"\u0675\u0678\u0003\u0120\u0090\u0000\u0676\u0678\u0003\u015e\u00af\u0000"+
		"\u0677\u0674\u0001\u0000\u0000\u0000\u0677\u0675\u0001\u0000\u0000\u0000"+
		"\u0677\u0676\u0001\u0000\u0000\u0000\u0678\u0685\u0001\u0000\u0000\u0000"+
		"\u0679\u067c\u0003\u0148\u00a4\u0000\u067a\u067c\u0003\u015a\u00ad\u0000"+
		"\u067b\u0679\u0001\u0000\u0000\u0000\u067b\u067a\u0001\u0000\u0000\u0000"+
		"\u067c\u0685\u0001\u0000\u0000\u0000\u067d\u0682\u0003\u014e\u00a7\u0000"+
		"\u067e\u0682\u0003\u014c\u00a6\u0000\u067f\u0682\u0003\u0160\u00b0\u0000"+
		"\u0680\u0682\u0003\u015c\u00ae\u0000\u0681\u067d\u0001\u0000\u0000\u0000"+
		"\u0681\u067e\u0001\u0000\u0000\u0000\u0681\u067f\u0001\u0000\u0000\u0000"+
		"\u0681\u0680\u0001\u0000\u0000\u0000\u0682\u0685\u0001\u0000\u0000\u0000"+
		"\u0683\u0685\u0005X\u0000\u0000\u0684\u066d\u0001\u0000\u0000\u0000\u0684"+
		"\u066e\u0001\u0000\u0000\u0000\u0684\u066f\u0001\u0000\u0000\u0000\u0684"+
		"\u0670\u0001\u0000\u0000\u0000\u0684\u0671\u0001\u0000\u0000\u0000\u0684"+
		"\u0672\u0001\u0000\u0000\u0000\u0684\u0673\u0001\u0000\u0000\u0000\u0684"+
		"\u0677\u0001\u0000\u0000\u0000\u0684\u067b\u0001\u0000\u0000\u0000\u0684"+
		"\u0681\u0001\u0000\u0000\u0000\u0684\u0683\u0001\u0000\u0000\u0000\u0685"+
		"\u011d\u0001\u0000\u0000\u0000\u0686\u0687\u0005^\u0000\u0000\u0687\u0688"+
		"\u0007\u0002\u0000\u0000\u0688\u011f\u0001\u0000\u0000\u0000\u0689\u068c"+
		"\u0005+\u0000\u0000\u068a\u068d\u0003\u00d6k\u0000\u068b\u068d\u0003\u00e2"+
		"q\u0000\u068c\u068a\u0001\u0000\u0000\u0000\u068c\u068b\u0001\u0000\u0000"+
		"\u0000\u068d\u068e\u0001\u0000\u0000\u0000\u068e\u068f\u0005.\u0000\u0000"+
		"\u068f\u0121\u0001\u0000\u0000\u0000\u0690\u0692\u0005\u0018\u0000\u0000"+
		"\u0691\u0693\u0003\u0124\u0092\u0000\u0692\u0691\u0001\u0000\u0000\u0000"+
		"\u0692\u0693\u0001\u0000\u0000\u0000\u0693\u0694\u0001\u0000\u0000\u0000"+
		"\u0694\u0695\u00052\u0000\u0000\u0695\u0696\u0003\u00d4j\u0000\u0696\u0123"+
		"\u0001\u0000\u0000\u0000\u0697\u0698\u0003\u0126\u0093\u0000\u0698\u0125"+
		"\u0001\u0000\u0000\u0000\u0699\u069d\u0003\u0128\u0094\u0000\u069a\u069c"+
		"\u0003\u0130\u0098\u0000\u069b\u069a\u0001\u0000\u0000\u0000\u069c\u069f"+
		"\u0001\u0000\u0000\u0000\u069d\u069b\u0001\u0000\u0000\u0000\u069d\u069e"+
		"\u0001\u0000\u0000\u0000\u069e\u06a3\u0001\u0000\u0000\u0000\u069f\u069d"+
		"\u0001\u0000\u0000\u0000\u06a0\u06a2\u0003\u0132\u0099\u0000\u06a1\u06a0"+
		"\u0001\u0000\u0000\u0000\u06a2\u06a5\u0001\u0000\u0000\u0000\u06a3\u06a1"+
		"\u0001\u0000\u0000\u0000\u06a3\u06a4\u0001\u0000\u0000\u0000\u06a4\u06a7"+
		"\u0001\u0000\u0000\u0000\u06a5\u06a3\u0001\u0000\u0000\u0000\u06a6\u06a8"+
		"\u0003\u012c\u0096\u0000\u06a7\u06a6\u0001\u0000\u0000\u0000\u06a7\u06a8"+
		"\u0001\u0000\u0000\u0000\u06a8\u06cb\u0001\u0000\u0000\u0000\u06a9\u06ad"+
		"\u0003\u012a\u0095\u0000\u06aa\u06ac\u0003\u0132\u0099\u0000\u06ab\u06aa"+
		"\u0001\u0000\u0000\u0000\u06ac\u06af\u0001\u0000\u0000\u0000\u06ad\u06ab"+
		"\u0001\u0000\u0000\u0000\u06ad\u06ae\u0001\u0000\u0000\u0000\u06ae\u06b1"+
		"\u0001\u0000\u0000\u0000\u06af\u06ad\u0001\u0000\u0000\u0000\u06b0\u06b2"+
		"\u0003\u012c\u0096\u0000\u06b1\u06b0\u0001\u0000\u0000\u0000\u06b1\u06b2"+
		"\u0001\u0000\u0000\u0000\u06b2\u06cb\u0001\u0000\u0000\u0000\u06b3\u06b5"+
		"\u0003\u0130\u0098\u0000\u06b4\u06b3\u0001\u0000\u0000\u0000\u06b5\u06b6"+
		"\u0001\u0000\u0000\u0000\u06b6\u06b4\u0001\u0000\u0000\u0000\u06b6\u06b7"+
		"\u0001\u0000\u0000\u0000\u06b7\u06bb\u0001\u0000\u0000\u0000\u06b8\u06ba"+
		"\u0003\u0132\u0099\u0000\u06b9\u06b8\u0001\u0000\u0000\u0000\u06ba\u06bd"+
		"\u0001\u0000\u0000\u0000\u06bb\u06b9\u0001\u0000\u0000\u0000\u06bb\u06bc"+
		"\u0001\u0000\u0000\u0000\u06bc\u06bf\u0001\u0000\u0000\u0000\u06bd\u06bb"+
		"\u0001\u0000\u0000\u0000\u06be\u06c0\u0003\u012c\u0096\u0000\u06bf\u06be"+
		"\u0001\u0000\u0000\u0000\u06bf\u06c0\u0001\u0000\u0000\u0000\u06c0\u06cb"+
		"\u0001\u0000\u0000\u0000\u06c1\u06c3\u0003\u0132\u0099\u0000\u06c2\u06c1"+
		"\u0001\u0000\u0000\u0000\u06c3\u06c4\u0001\u0000\u0000\u0000\u06c4\u06c2"+
		"\u0001\u0000\u0000\u0000\u06c4\u06c5\u0001\u0000\u0000\u0000\u06c5\u06c7"+
		"\u0001\u0000\u0000\u0000\u06c6\u06c8\u0003\u012c\u0096\u0000\u06c7\u06c6"+
		"\u0001\u0000\u0000\u0000\u06c7\u06c8\u0001\u0000\u0000\u0000\u06c8\u06cb"+
		"\u0001\u0000\u0000\u0000\u06c9\u06cb\u0003\u012c\u0096\u0000\u06ca\u0699"+
		"\u0001\u0000\u0000\u0000\u06ca\u06a9\u0001\u0000\u0000\u0000\u06ca\u06b4"+
		"\u0001\u0000\u0000\u0000\u06ca\u06c2\u0001\u0000\u0000\u0000\u06ca\u06c9"+
		"\u0001\u0000\u0000\u0000\u06cb\u0127\u0001\u0000\u0000\u0000\u06cc\u06ce"+
		"\u0003\u0130\u0098\u0000\u06cd\u06cc\u0001\u0000\u0000\u0000\u06ce\u06cf"+
		"\u0001\u0000\u0000\u0000\u06cf\u06cd\u0001\u0000\u0000\u0000\u06cf\u06d0"+
		"\u0001\u0000\u0000\u0000\u06d0\u06d1\u0001\u0000\u0000\u0000\u06d1\u06d3"+
		"\u00058\u0000\u0000\u06d2\u06d4\u00053\u0000\u0000\u06d3\u06d2\u0001\u0000"+
		"\u0000\u0000\u06d3\u06d4\u0001\u0000\u0000\u0000\u06d4\u0129\u0001\u0000"+
		"\u0000\u0000\u06d5\u06d7\u0003\u0130\u0098\u0000\u06d6\u06d5\u0001\u0000"+
		"\u0000\u0000\u06d7\u06da\u0001\u0000\u0000\u0000\u06d8\u06d6\u0001\u0000"+
		"\u0000\u0000\u06d8\u06d9\u0001\u0000\u0000\u0000\u06d9\u06dc\u0001\u0000"+
		"\u0000\u0000\u06da\u06d8\u0001\u0000\u0000\u0000\u06db\u06dd\u0003\u0132"+
		"\u0099\u0000\u06dc\u06db\u0001\u0000\u0000\u0000\u06dd\u06de\u0001\u0000"+
		"\u0000\u0000\u06de\u06dc\u0001\u0000\u0000\u0000\u06de\u06df\u0001\u0000"+
		"\u0000\u0000\u06df\u06e0\u0001\u0000\u0000\u0000\u06e0\u06e2\u00058\u0000"+
		"\u0000\u06e1\u06e3\u00053\u0000\u0000\u06e2\u06e1\u0001\u0000\u0000\u0000"+
		"\u06e2\u06e3\u0001\u0000\u0000\u0000\u06e3\u012b\u0001\u0000\u0000\u0000"+
		"\u06e4\u06e5\u00057\u0000\u0000\u06e5\u06e9\u0003\u0130\u0098\u0000\u06e6"+
		"\u06e8\u0003\u0134\u009a\u0000\u06e7\u06e6\u0001\u0000\u0000\u0000\u06e8"+
		"\u06eb\u0001\u0000\u0000\u0000\u06e9\u06e7\u0001\u0000\u0000\u0000\u06e9"+
		"\u06ea\u0001\u0000\u0000\u0000\u06ea\u06ed\u0001\u0000\u0000\u0000\u06eb"+
		"\u06e9\u0001\u0000\u0000\u0000\u06ec\u06ee\u0003\u012e\u0097\u0000\u06ed"+
		"\u06ec\u0001\u0000\u0000\u0000\u06ed\u06ee\u0001\u0000\u0000\u0000\u06ee"+
		"\u06fb\u0001\u0000\u0000\u0000\u06ef\u06f0\u00057\u0000\u0000\u06f0\u06f2"+
		"\u00053\u0000\u0000\u06f1\u06f3\u0003\u0134\u009a\u0000\u06f2\u06f1\u0001"+
		"\u0000\u0000\u0000\u06f3\u06f4\u0001\u0000\u0000\u0000\u06f4\u06f2\u0001"+
		"\u0000\u0000\u0000\u06f4\u06f5\u0001\u0000\u0000\u0000\u06f5\u06f7\u0001"+
		"\u0000\u0000\u0000\u06f6\u06f8\u0003\u012e\u0097\u0000\u06f7\u06f6\u0001"+
		"\u0000\u0000\u0000\u06f7\u06f8\u0001\u0000\u0000\u0000\u06f8\u06fb\u0001"+
		"\u0000\u0000\u0000\u06f9\u06fb\u0003\u012e\u0097\u0000\u06fa\u06e4\u0001"+
		"\u0000\u0000\u0000\u06fa\u06ef\u0001\u0000\u0000\u0000\u06fa\u06f9\u0001"+
		"\u0000\u0000\u0000\u06fb\u012d\u0001\u0000\u0000\u0000\u06fc\u06fd\u0005"+
		"G\u0000\u0000\u06fd\u06fe\u0003\u0130\u0098\u0000\u06fe\u012f\u0001\u0000"+
		"\u0000\u0000\u06ff\u0701\u0003\u0136\u009b\u0000\u0700\u0702\u00053\u0000"+
		"\u0000\u0701\u0700\u0001\u0000\u0000\u0000\u0701\u0702\u0001\u0000\u0000"+
		"\u0000\u0702\u0131\u0001\u0000\u0000\u0000\u0703\u0704\u0003\u0136\u009b"+
		"\u0000\u0704\u0706\u0003f3\u0000\u0705\u0707\u00053\u0000\u0000\u0706"+
		"\u0705\u0001\u0000\u0000\u0000\u0706\u0707\u0001\u0000\u0000\u0000\u0707"+
		"\u0133\u0001\u0000\u0000\u0000\u0708\u070a\u0003\u0136\u009b\u0000\u0709"+
		"\u070b\u0003f3\u0000\u070a\u0709\u0001\u0000\u0000\u0000\u070a\u070b\u0001"+
		"\u0000\u0000\u0000\u070b\u070d\u0001\u0000\u0000\u0000\u070c\u070e\u0005"+
		"3\u0000\u0000\u070d\u070c\u0001\u0000\u0000\u0000\u070d\u070e\u0001\u0000"+
		"\u0000\u0000\u070e\u0135\u0001\u0000\u0000\u0000\u070f\u0710\u0005]\u0000"+
		"\u0000\u0710\u0137\u0001\u0000\u0000\u0000\u0711\u0714\u0003\u013a\u009d"+
		"\u0000\u0712\u0714\u0005\u0004\u0000\u0000\u0713\u0711\u0001\u0000\u0000"+
		"\u0000\u0713\u0712\u0001\u0000\u0000\u0000\u0714\u0139\u0001\u0000\u0000"+
		"\u0000\u0715\u0718\u0005-\u0000\u0000\u0716\u0719\u0003\u00d6k\u0000\u0717"+
		"\u0719\u0003\u00d8l\u0000\u0718\u0716\u0001\u0000\u0000\u0000\u0718\u0717"+
		"\u0001\u0000\u0000\u0000\u0719\u071b\u0001\u0000\u0000\u0000\u071a\u071c"+
		"\u0005=\u0000\u0000\u071b\u071a\u0001\u0000\u0000\u0000\u071b\u071c\u0001"+
		"\u0000\u0000\u0000\u071c\u071e\u0001\u0000\u0000\u0000\u071d\u071f\u0003"+
		"\u013c\u009e\u0000\u071e\u071d\u0001\u0000\u0000\u0000\u071e\u071f\u0001"+
		"\u0000\u0000\u0000\u071f\u0721\u0001\u0000\u0000\u0000\u0720\u0722\u0003"+
		"\u013e\u009f\u0000\u0721\u0720\u0001\u0000\u0000\u0000\u0721\u0722\u0001"+
		"\u0000\u0000\u0000\u0722\u0723\u0001\u0000\u0000\u0000\u0723\u0724\u0005"+
		"0\u0000\u0000\u0724\u013b\u0001\u0000\u0000\u0000\u0725\u0726\u0005Z\u0000"+
		"\u0000\u0726\u0727\u0005]\u0000\u0000\u0727\u013d\u0001\u0000\u0000\u0000"+
		"\u0728\u072c\u00052\u0000\u0000\u0729\u072b\u0003\u0140\u00a0\u0000\u072a"+
		"\u0729\u0001\u0000\u0000\u0000\u072b\u072e\u0001\u0000\u0000\u0000\u072c"+
		"\u072a\u0001\u0000\u0000\u0000\u072c\u072d\u0001\u0000\u0000\u0000\u072d"+
		"\u013f\u0001\u0000\u0000\u0000\u072e\u072c\u0001\u0000\u0000\u0000\u072f"+
		"\u0732\u0005\u0004\u0000\u0000\u0730\u0732\u0003\u013a\u009d\u0000\u0731"+
		"\u072f\u0001\u0000\u0000\u0000\u0731\u0730\u0001\u0000\u0000\u0000\u0732"+
		"\u0141\u0001\u0000\u0000\u0000\u0733\u0737\u0005\u0003\u0000\u0000\u0734"+
		"\u0736\u0003\u0138\u009c\u0000\u0735\u0734\u0001\u0000\u0000\u0000\u0736"+
		"\u0739\u0001\u0000\u0000\u0000\u0737\u0735\u0001\u0000\u0000\u0000\u0737"+
		"\u0738\u0001\u0000\u0000\u0000\u0738\u073a\u0001\u0000\u0000\u0000\u0739"+
		"\u0737\u0001\u0000\u0000\u0000\u073a\u073b\u0005\u0005\u0000\u0000\u073b"+
		"\u0143\u0001\u0000\u0000\u0000\u073c\u073d\u0005_\u0000\u0000\u073d\u0145"+
		"\u0001\u0000\u0000\u0000\u073e\u0741\u0003\u0142\u00a1\u0000\u073f\u0741"+
		"\u0003\u0144\u00a2\u0000\u0740\u073e\u0001\u0000\u0000\u0000\u0740\u073f"+
		"\u0001\u0000\u0000\u0000\u0741\u0742\u0001\u0000\u0000\u0000\u0742\u0740"+
		"\u0001\u0000\u0000\u0000\u0742\u0743\u0001\u0000\u0000\u0000\u0743\u0147"+
		"\u0001\u0000\u0000\u0000\u0744\u0746\u0005,\u0000\u0000\u0745\u0747\u0003"+
		"\u00dcn\u0000\u0746\u0745\u0001\u0000\u0000\u0000\u0746\u0747\u0001\u0000"+
		"\u0000\u0000\u0747\u0748\u0001\u0000\u0000\u0000\u0748\u0749\u0005/\u0000"+
		"\u0000\u0749\u0149\u0001\u0000\u0000\u0000\u074a\u0750\u0005+\u0000\u0000"+
		"\u074b\u074c\u0003\u00deo\u0000\u074c\u074e\u00053\u0000\u0000\u074d\u074f"+
		"\u0003\u00dcn\u0000\u074e\u074d\u0001\u0000\u0000\u0000\u074e\u074f\u0001"+
		"\u0000\u0000\u0000\u074f\u0751\u0001\u0000\u0000\u0000\u0750\u074b\u0001"+
		"\u0000\u0000\u0000\u0750\u0751\u0001\u0000\u0000\u0000\u0751\u0752\u0001"+
		"\u0000\u0000\u0000\u0752\u0753\u0005.\u0000\u0000\u0753\u014b\u0001\u0000"+
		"\u0000\u0000\u0754\u0755\u0005-\u0000\u0000\u0755\u0756\u0003\u00dcn\u0000"+
		"\u0756\u0757\u00050\u0000\u0000\u0757\u014d\u0001\u0000\u0000\u0000\u0758"+
		"\u075a\u0005-\u0000\u0000\u0759\u075b\u0003\u0150\u00a8\u0000\u075a\u0759"+
		"\u0001\u0000\u0000\u0000\u075a\u075b\u0001\u0000\u0000\u0000\u075b\u075c"+
		"\u0001\u0000\u0000\u0000\u075c\u075d\u00050\u0000\u0000\u075d\u014f\u0001"+
		"\u0000\u0000\u0000\u075e\u0763\u0003\u0152\u00a9\u0000\u075f\u0760\u0005"+
		"3\u0000\u0000\u0760\u0762\u0003\u0152\u00a9\u0000\u0761\u075f\u0001\u0000"+
		"\u0000\u0000\u0762\u0765\u0001\u0000\u0000\u0000\u0763\u0761\u0001\u0000"+
		"\u0000\u0000\u0763\u0764\u0001\u0000\u0000\u0000\u0764\u0767\u0001\u0000"+
		"\u0000\u0000\u0765\u0763\u0001\u0000\u0000\u0000\u0766\u0768\u00053\u0000"+
		"\u0000\u0767\u0766\u0001\u0000\u0000\u0000\u0767\u0768\u0001\u0000\u0000"+
		"\u0000\u0768\u0151\u0001\u0000\u0000\u0000\u0769\u076a\u0005G\u0000\u0000"+
		"\u076a\u076d\u0003\u0102\u0081\u0000\u076b\u076d\u0003\u0154\u00aa\u0000"+
		"\u076c\u0769\u0001\u0000\u0000\u0000\u076c\u076b\u0001\u0000\u0000\u0000"+
		"\u076d\u0153\u0001\u0000\u0000\u0000\u076e\u076f\u0003\u00d4j\u0000\u076f"+
		"\u0770\u00052\u0000\u0000\u0770\u0771\u0003\u00d4j\u0000\u0771\u0155\u0001"+
		"\u0000\u0000\u0000\u0772\u0774\u0003\u0158\u00ac\u0000\u0773\u0772\u0001"+
		"\u0000\u0000\u0000\u0774\u0775\u0001\u0000\u0000\u0000\u0775\u0773\u0001"+
		"\u0000\u0000\u0000\u0775\u0776\u0001\u0000\u0000\u0000\u0776\u0157\u0001"+
		"\u0000\u0000\u0000\u0777\u0779\u0005$\u0000\u0000\u0778\u0777\u0001\u0000"+
		"\u0000\u0000\u0778\u0779\u0001\u0000\u0000\u0000\u0779\u077a\u0001\u0000"+
		"\u0000\u0000\u077a\u077b\u0005\u0017\u0000\u0000\u077b\u077c\u0003\u016e"+
		"\u00b7\u0000\u077c\u077d\u0005\u000e\u0000\u0000\u077d\u0782\u0003\u00e4"+
		"r\u0000\u077e\u077f\u0005&\u0000\u0000\u077f\u0781\u0003\u00e4r\u0000"+
		"\u0780\u077e\u0001\u0000\u0000\u0000\u0781\u0784\u0001\u0000\u0000\u0000"+
		"\u0782\u0780\u0001\u0000\u0000\u0000\u0782\u0783\u0001\u0000\u0000\u0000"+
		"\u0783\u0159\u0001\u0000\u0000\u0000\u0784\u0782\u0001\u0000\u0000\u0000"+
		"\u0785\u0786\u0005,\u0000\u0000\u0786\u0787\u0003\u00e2q\u0000\u0787\u0788"+
		"\u0003\u0156\u00ab\u0000\u0788\u0789\u0005/\u0000\u0000\u0789\u015b\u0001"+
		"\u0000\u0000\u0000\u078a\u078b\u0005-\u0000\u0000\u078b\u078c\u0003\u00e2"+
		"q\u0000\u078c\u078d\u0003\u0156\u00ab\u0000\u078d\u078e\u00050\u0000\u0000"+
		"\u078e\u015d\u0001\u0000\u0000\u0000\u078f\u0792\u0005+\u0000\u0000\u0790"+
		"\u0793\u0003\u00e0p\u0000\u0791\u0793\u0003\u00d4j\u0000\u0792\u0790\u0001"+
		"\u0000\u0000\u0000\u0792\u0791\u0001\u0000\u0000\u0000\u0793\u0794\u0001"+
		"\u0000\u0000\u0000\u0794\u0795\u0003\u0156\u00ab\u0000\u0795\u0796\u0005"+
		".\u0000\u0000\u0796\u015f\u0001\u0000\u0000\u0000\u0797\u0798\u0005-\u0000"+
		"\u0000\u0798\u0799\u0003\u0154\u00aa\u0000\u0799\u079a\u0003\u0156\u00ab"+
		"\u0000\u079a\u079b\u00050\u0000\u0000\u079b\u0161\u0001\u0000\u0000\u0000"+
		"\u079c\u079e\u0003\u0164\u00b2\u0000\u079d\u079f\u00053\u0000\u0000\u079e"+
		"\u079d\u0001\u0000\u0000\u0000\u079e\u079f\u0001\u0000\u0000\u0000\u079f"+
		"\u0163\u0001\u0000\u0000\u0000\u07a0\u07a6\u0003\u0168\u00b4\u0000\u07a1"+
		"\u07a4\u0003\u00e0p\u0000\u07a2\u07a4\u0003\u00d4j\u0000\u07a3\u07a1\u0001"+
		"\u0000\u0000\u0000\u07a3\u07a2\u0001\u0000\u0000\u0000\u07a4\u07a6\u0001"+
		"\u0000\u0000\u0000\u07a5\u07a0\u0001\u0000\u0000\u0000\u07a5\u07a3\u0001"+
		"\u0000\u0000\u0000\u07a6\u07b1\u0001\u0000\u0000\u0000\u07a7\u07ad\u0005"+
		"3\u0000\u0000\u07a8\u07ae\u0003\u0168\u00b4\u0000\u07a9\u07ac\u0003\u00e0"+
		"p\u0000\u07aa\u07ac\u0003\u00d4j\u0000\u07ab\u07a9\u0001\u0000\u0000\u0000"+
		"\u07ab\u07aa\u0001\u0000\u0000\u0000\u07ac\u07ae\u0001\u0000\u0000\u0000"+
		"\u07ad\u07a8\u0001\u0000\u0000\u0000\u07ad\u07ab\u0001\u0000\u0000\u0000"+
		"\u07ae\u07b0\u0001\u0000\u0000\u0000\u07af\u07a7\u0001\u0000\u0000\u0000"+
		"\u07b0\u07b3\u0001\u0000\u0000\u0000\u07b1\u07af\u0001\u0000\u0000\u0000"+
		"\u07b1\u07b2\u0001\u0000\u0000\u0000\u07b2\u07b6\u0001\u0000\u0000\u0000"+
		"\u07b3\u07b1\u0001\u0000\u0000\u0000\u07b4\u07b5\u00053\u0000\u0000\u07b5"+
		"\u07b7\u0003\u0166\u00b3\u0000\u07b6\u07b4\u0001\u0000\u0000\u0000\u07b6"+
		"\u07b7\u0001\u0000\u0000\u0000\u07b7\u07ba\u0001\u0000\u0000\u0000\u07b8"+
		"\u07ba\u0003\u0166\u00b3\u0000\u07b9\u07a5\u0001\u0000\u0000\u0000\u07b9"+
		"\u07b8\u0001\u0000\u0000\u0000\u07ba\u0165\u0001\u0000\u0000\u0000\u07bb"+
		"\u07c0\u0003\u016a\u00b5\u0000\u07bc\u07bd\u00053\u0000\u0000\u07bd\u07bf"+
		"\u0003\u016a\u00b5\u0000\u07be\u07bc\u0001\u0000\u0000\u0000\u07bf\u07c2"+
		"\u0001\u0000\u0000\u0000\u07c0\u07be\u0001\u0000\u0000\u0000\u07c0\u07c1"+
		"\u0001\u0000\u0000\u0000\u07c1\u07cc\u0001\u0000\u0000\u0000\u07c2\u07c0"+
		"\u0001\u0000\u0000\u0000\u07c3\u07c4\u00053\u0000\u0000\u07c4\u07c9\u0003"+
		"\u016c\u00b6\u0000\u07c5\u07c6\u00053\u0000\u0000\u07c6\u07c8\u0003\u016c"+
		"\u00b6\u0000\u07c7\u07c5\u0001\u0000\u0000\u0000\u07c8\u07cb\u0001\u0000"+
		"\u0000\u0000\u07c9\u07c7\u0001\u0000\u0000\u0000\u07c9\u07ca\u0001\u0000"+
		"\u0000\u0000\u07ca\u07cd\u0001\u0000\u0000\u0000\u07cb\u07c9\u0001\u0000"+
		"\u0000\u0000\u07cc\u07c3\u0001\u0000\u0000\u0000\u07cc\u07cd\u0001\u0000"+
		"\u0000\u0000\u07cd\u07d7\u0001\u0000\u0000\u0000\u07ce\u07d3\u0003\u016c"+
		"\u00b6\u0000\u07cf\u07d0\u00053\u0000\u0000\u07d0\u07d2\u0003\u016c\u00b6"+
		"\u0000\u07d1\u07cf\u0001\u0000\u0000\u0000\u07d2\u07d5\u0001\u0000\u0000"+
		"\u0000\u07d3\u07d1\u0001\u0000\u0000\u0000\u07d3\u07d4\u0001\u0000\u0000"+
		"\u0000\u07d4\u07d7\u0001\u0000\u0000\u0000\u07d5\u07d3\u0001\u0000\u0000"+
		"\u0000\u07d6\u07bb\u0001\u0000\u0000\u0000\u07d6\u07ce\u0001\u0000\u0000"+
		"\u0000\u07d7\u0167\u0001\u0000\u0000\u0000\u07d8\u07d9\u00057\u0000\u0000"+
		"\u07d9\u07da\u0003\u00d4j\u0000\u07da\u0169\u0001\u0000\u0000\u0000\u07db"+
		"\u07dc\u0005]\u0000\u0000\u07dc\u07dd\u0005=\u0000\u0000\u07dd\u07e0\u0003"+
		"\u00d4j\u0000\u07de\u07e0\u0003\u0168\u00b4\u0000\u07df\u07db\u0001\u0000"+
		"\u0000\u0000\u07df\u07de\u0001\u0000\u0000\u0000\u07e0\u016b\u0001\u0000"+
		"\u0000\u0000\u07e1\u07e2\u0005]\u0000\u0000\u07e2\u07e3\u0005=\u0000\u0000"+
		"\u07e3\u07e7\u0003\u00d4j\u0000\u07e4\u07e5\u0005G\u0000\u0000\u07e5\u07e7"+
		"\u0003\u00d4j\u0000\u07e6\u07e1\u0001\u0000\u0000\u0000\u07e6\u07e4\u0001"+
		"\u0000\u0000\u0000\u07e7\u016d\u0001\u0000\u0000\u0000\u07e8\u07ed\u0003"+
		"\u0174\u00ba\u0000\u07e9\u07ea\u00053\u0000\u0000\u07ea\u07ec\u0003\u0174"+
		"\u00ba\u0000\u07eb\u07e9\u0001\u0000\u0000\u0000\u07ec\u07ef\u0001\u0000"+
		"\u0000\u0000\u07ed\u07eb\u0001\u0000\u0000\u0000\u07ed\u07ee\u0001\u0000"+
		"\u0000\u0000\u07ee\u07f1\u0001\u0000\u0000\u0000\u07ef\u07ed\u0001\u0000"+
		"\u0000\u0000\u07f0\u07f2\u00053\u0000\u0000\u07f1\u07f0\u0001\u0000\u0000"+
		"\u0000\u07f1\u07f2\u0001\u0000\u0000\u0000\u07f2\u016f\u0001\u0000\u0000"+
		"\u0000\u07f3\u07f6\u0003\u0174\u00ba\u0000\u07f4\u07f5\u00053\u0000\u0000"+
		"\u07f5\u07f7\u0003\u0174\u00ba\u0000\u07f6\u07f4\u0001\u0000\u0000\u0000"+
		"\u07f7\u07f8\u0001\u0000\u0000\u0000\u07f8\u07f6\u0001\u0000\u0000\u0000"+
		"\u07f8\u07f9\u0001\u0000\u0000\u0000\u07f9\u07fb\u0001\u0000\u0000\u0000"+
		"\u07fa\u07fc\u00053\u0000\u0000\u07fb\u07fa\u0001\u0000\u0000\u0000\u07fb"+
		"\u07fc\u0001\u0000\u0000\u0000\u07fc\u0171\u0001\u0000\u0000\u0000\u07fd"+
		"\u0808\u0003\u0174\u00ba\u0000\u07fe\u0809\u00053\u0000\u0000\u07ff\u0800"+
		"\u00053\u0000\u0000\u0800\u0802\u0003\u0174\u00ba\u0000\u0801\u07ff\u0001"+
		"\u0000\u0000\u0000\u0802\u0803\u0001\u0000\u0000\u0000\u0803\u0801\u0001"+
		"\u0000\u0000\u0000\u0803\u0804\u0001\u0000\u0000\u0000\u0804\u0806\u0001"+
		"\u0000\u0000\u0000\u0805\u0807\u00053\u0000\u0000\u0806\u0805\u0001\u0000"+
		"\u0000\u0000\u0806\u0807\u0001\u0000\u0000\u0000\u0807\u0809\u0001\u0000"+
		"\u0000\u0000\u0808\u07fe\u0001\u0000\u0000\u0000\u0808\u0801\u0001\u0000"+
		"\u0000\u0000\u0809\u0173\u0001\u0000\u0000\u0000\u080a\u080b\u00057\u0000"+
		"\u0000\u080b\u080e\u0003\u0174\u00ba\u0000\u080c\u080e\u0003\u0176\u00bb"+
		"\u0000\u080d\u080a\u0001\u0000\u0000\u0000\u080d\u080c\u0001\u0000\u0000"+
		"\u0000\u080e\u0175\u0001\u0000\u0000\u0000\u080f\u0816\u0003\u017e\u00bf"+
		"\u0000\u0810\u0811\u00051\u0000\u0000\u0811\u0817\u0005]\u0000\u0000\u0812"+
		"\u0813\u0005,\u0000\u0000\u0813\u0814\u0003\u0118\u008c\u0000\u0814\u0815"+
		"\u0005/\u0000\u0000\u0815\u0817\u0001\u0000\u0000\u0000\u0816\u0810\u0001"+
		"\u0000\u0000\u0000\u0816\u0812\u0001\u0000\u0000\u0000\u0817\u081a\u0001"+
		"\u0000\u0000\u0000\u0818\u081a\u0003\u0178\u00bc\u0000\u0819\u080f\u0001"+
		"\u0000\u0000\u0000\u0819\u0818\u0001\u0000\u0000\u0000\u081a\u0177\u0001"+
		"\u0000\u0000\u0000\u081b\u082b\u0005]\u0000\u0000\u081c\u081d\u0005+\u0000"+
		"\u0000\u081d\u081e\u0003\u0176\u00bb\u0000\u081e\u081f\u0005.\u0000\u0000"+
		"\u081f\u082b\u0001\u0000\u0000\u0000\u0820\u0822\u0005+\u0000\u0000\u0821"+
		"\u0823\u0003\u0172\u00b9\u0000\u0822\u0821\u0001\u0000\u0000\u0000\u0822"+
		"\u0823\u0001\u0000\u0000\u0000\u0823\u0824\u0001\u0000\u0000\u0000\u0824"+
		"\u082b\u0005.\u0000\u0000\u0825\u0827\u0005,\u0000\u0000\u0826\u0828\u0003"+
		"\u0170\u00b8\u0000\u0827\u0826\u0001\u0000\u0000\u0000\u0827\u0828\u0001"+
		"\u0000\u0000\u0000\u0828\u0829\u0001\u0000\u0000\u0000\u0829\u082b\u0005"+
		"/\u0000\u0000\u082a\u081b\u0001\u0000\u0000\u0000\u082a\u081c\u0001\u0000"+
		"\u0000\u0000\u082a\u0820\u0001\u0000\u0000\u0000\u082a\u0825\u0001\u0000"+
		"\u0000\u0000\u082b\u0179\u0001\u0000\u0000\u0000\u082c\u0833\u0003\u017c"+
		"\u00be\u0000\u082d\u0833\u0005]\u0000\u0000\u082e\u082f\u0005+\u0000\u0000"+
		"\u082f\u0830\u0003\u017a\u00bd\u0000\u0830\u0831\u0005.\u0000\u0000\u0831"+
		"\u0833\u0001\u0000\u0000\u0000\u0832\u082c\u0001\u0000\u0000\u0000\u0832"+
		"\u082d\u0001\u0000\u0000\u0000\u0832\u082e\u0001\u0000\u0000\u0000\u0833"+
		"\u017b\u0001\u0000\u0000\u0000\u0834\u083b\u0003\u017e\u00bf\u0000\u0835"+
		"\u0836\u00051\u0000\u0000\u0836\u083c\u0005]\u0000\u0000\u0837\u0838\u0005"+
		",\u0000\u0000\u0838\u0839\u0003\u0118\u008c\u0000\u0839\u083a\u0005/\u0000"+
		"\u0000\u083a\u083c\u0001\u0000\u0000\u0000\u083b\u0835\u0001\u0000\u0000"+
		"\u0000\u083b\u0837\u0001\u0000\u0000\u0000\u083c\u017d\u0001\u0000\u0000"+
		"\u0000\u083d\u083e\u0006\u00bf\uffff\uffff\u0000\u083e\u083f\u0003\u011c"+
		"\u008e\u0000\u083f\u0851\u0001\u0000\u0000\u0000\u0840\u084d\n\u0002\u0000"+
		"\u0000\u0841\u0842\u00051\u0000\u0000\u0842\u084e\u0005]\u0000\u0000\u0843"+
		"\u0844\u0005,\u0000\u0000\u0844\u0845\u0003\u0118\u008c\u0000\u0845\u0846"+
		"\u0005/\u0000\u0000\u0846\u084e\u0001\u0000\u0000\u0000\u0847\u084e\u0003"+
		"\u015e\u00af\u0000\u0848\u084a\u0005+\u0000\u0000\u0849\u084b\u0003\u0162"+
		"\u00b1\u0000\u084a\u0849\u0001\u0000\u0000\u0000\u084a\u084b\u0001\u0000"+
		"\u0000\u0000\u084b\u084c\u0001\u0000\u0000\u0000\u084c\u084e\u0005.\u0000"+
		"\u0000\u084d\u0841\u0001\u0000\u0000\u0000\u084d\u0843\u0001\u0000\u0000"+
		"\u0000\u084d\u0847\u0001\u0000\u0000\u0000\u084d\u0848\u0001\u0000\u0000"+
		"\u0000\u084e\u0850\u0001\u0000\u0000\u0000\u084f\u0840\u0001\u0000\u0000"+
		"\u0000\u0850\u0853\u0001\u0000\u0000\u0000\u0851\u084f\u0001\u0000\u0000"+
		"\u0000\u0851\u0852\u0001\u0000\u0000\u0000\u0852\u017f\u0001\u0000\u0000"+
		"\u0000\u0853\u0851\u0001\u0000\u0000\u0000\u0854\u0859\u0003\u0182\u00c1"+
		"\u0000\u0855\u0856\u00053\u0000\u0000\u0856\u0858\u0003\u0182\u00c1\u0000"+
		"\u0857\u0855\u0001\u0000\u0000\u0000\u0858\u085b\u0001\u0000\u0000\u0000"+
		"\u0859\u0857\u0001\u0000\u0000\u0000\u0859\u085a\u0001\u0000\u0000\u0000"+
		"\u085a\u085d\u0001\u0000\u0000\u0000\u085b\u0859\u0001\u0000\u0000\u0000"+
		"\u085c\u085e\u00053\u0000\u0000\u085d\u085c\u0001\u0000\u0000\u0000\u085d"+
		"\u085e\u0001\u0000\u0000\u0000\u085e\u0181\u0001\u0000\u0000\u0000\u085f"+
		"\u0866\u0003\u017e\u00bf\u0000\u0860\u0861\u00051\u0000\u0000\u0861\u0867"+
		"\u0005]\u0000\u0000\u0862\u0863\u0005,\u0000\u0000\u0863\u0864\u0003\u0118"+
		"\u008c\u0000\u0864\u0865\u0005/\u0000\u0000\u0865\u0867\u0001\u0000\u0000"+
		"\u0000\u0866\u0860\u0001\u0000\u0000\u0000\u0866\u0862\u0001\u0000\u0000"+
		"\u0000\u0867\u086a\u0001\u0000\u0000\u0000\u0868\u086a\u0003\u0184\u00c2"+
		"\u0000\u0869\u085f\u0001\u0000\u0000\u0000\u0869\u0868\u0001\u0000\u0000"+
		"\u0000\u086a\u0183\u0001\u0000\u0000\u0000\u086b\u087b\u0005]\u0000\u0000"+
		"\u086c\u086d\u0005+\u0000\u0000\u086d\u086e\u0003\u0182\u00c1\u0000\u086e"+
		"\u086f\u0005.\u0000\u0000\u086f\u087b\u0001\u0000\u0000\u0000\u0870\u0872"+
		"\u0005+\u0000\u0000\u0871\u0873\u0003\u0180\u00c0\u0000\u0872\u0871\u0001"+
		"\u0000\u0000\u0000\u0872\u0873\u0001\u0000\u0000\u0000\u0873\u0874\u0001"+
		"\u0000\u0000\u0000\u0874\u087b\u0005.\u0000\u0000\u0875\u0877\u0005,\u0000"+
		"\u0000\u0876\u0878\u0003\u0180\u00c0\u0000\u0877\u0876\u0001\u0000\u0000"+
		"\u0000\u0877\u0878\u0001\u0000\u0000\u0000\u0878\u0879\u0001\u0000\u0000"+
		"\u0000\u0879\u087b\u0005/\u0000\u0000\u087a\u086b\u0001\u0000\u0000\u0000"+
		"\u087a\u086c\u0001\u0000\u0000\u0000\u087a\u0870\u0001\u0000\u0000\u0000"+
		"\u087a\u0875\u0001\u0000\u0000\u0000\u087b\u0185\u0001\u0000\u0000\u0000"+
		"\u087c\u0881\u0003\u00d4j\u0000\u087d\u087e\u00053\u0000\u0000\u087e\u0880"+
		"\u0003\u00d4j\u0000\u087f\u087d\u0001\u0000\u0000\u0000\u0880\u0883\u0001"+
		"\u0000\u0000\u0000\u0881\u087f\u0001\u0000\u0000\u0000\u0881\u0882\u0001"+
		"\u0000\u0000\u0000\u0882\u0890\u0001\u0000\u0000\u0000\u0883\u0881\u0001"+
		"\u0000\u0000\u0000\u0884\u088e\u00053\u0000\u0000\u0885\u0886\u00057\u0000"+
		"\u0000\u0886\u088a\u0003\u00d4j\u0000\u0887\u0888\u00053\u0000\u0000\u0888"+
		"\u0889\u0005G\u0000\u0000\u0889\u088b\u0003\u00d4j\u0000\u088a\u0887\u0001"+
		"\u0000\u0000\u0000\u088a\u088b\u0001\u0000\u0000\u0000\u088b\u088f\u0001"+
		"\u0000\u0000\u0000\u088c\u088d\u0005G\u0000\u0000\u088d\u088f\u0003\u00d4"+
		"j\u0000\u088e\u0885\u0001\u0000\u0000\u0000\u088e\u088c\u0001\u0000\u0000"+
		"\u0000\u088f\u0891\u0001\u0000\u0000\u0000\u0890\u0884\u0001\u0000\u0000"+
		"\u0000\u0890\u0891\u0001\u0000\u0000\u0000\u0891\u089c\u0001\u0000\u0000"+
		"\u0000\u0892\u0893\u00057\u0000\u0000\u0893\u0897\u0003\u00d4j\u0000\u0894"+
		"\u0895\u00053\u0000\u0000\u0895\u0896\u0005G\u0000\u0000\u0896\u0898\u0003"+
		"\u00d4j\u0000\u0897\u0894\u0001\u0000\u0000\u0000\u0897\u0898\u0001\u0000"+
		"\u0000\u0000\u0898\u089c\u0001\u0000\u0000\u0000\u0899\u089a\u0005G\u0000"+
		"\u0000\u089a\u089c\u0003\u00d4j\u0000\u089b\u087c\u0001\u0000\u0000\u0000"+
		"\u089b\u0892\u0001\u0000\u0000\u0000\u089b\u0899\u0001\u0000\u0000\u0000"+
		"\u089c\u0187\u0001\u0000\u0000\u0000\u089d\u089e\u0005a\u0000\u0000\u089e"+
		"\u08a1\u0005`\u0000\u0000\u089f\u08a1\u0005`\u0000\u0000\u08a0\u089d\u0001"+
		"\u0000\u0000\u0000\u08a0\u089f\u0001\u0000\u0000\u0000\u08a1\u0189\u0001"+
		"\u0000\u0000\u0000\u08a2\u08a3\u0004\u00c5\n\u0000\u08a3\u08a4\u0005]"+
		"\u0000\u0000\u08a4\u018b\u0001\u0000\u0000\u0000\u08a5\u08a6\u0004\u00c6"+
		"\u000b\u0000\u08a6\u08a7\u0005]\u0000\u0000\u08a7\u018d\u0001\u0000\u0000"+
		"\u0000\u08a8\u08a9\u0004\u00c7\f\u0000\u08a9\u08aa\u0005]\u0000\u0000"+
		"\u08aa\u018f\u0001\u0000\u0000\u0000\u08ab\u08ac\u0004\u00c8\r\u0000\u08ac"+
		"\u08ad\u0005]\u0000\u0000\u08ad\u0191\u0001\u0000\u0000\u0000\u08ae\u08af"+
		"\u0004\u00c9\u000e\u0000\u08af\u08b0\u0005]\u0000\u0000\u08b0\u0193\u0001"+
		"\u0000\u0000\u0000\u0126\u0195\u019f\u01a6\u01ae\u01b8\u01bc\u01c4\u01cb"+
		"\u01cf\u01e2\u01ec\u01f3\u01fa\u0200\u0207\u020b\u020e\u0214\u0216\u021a"+
		"\u0220\u0226\u0228\u0230\u0239\u0245\u0249\u0250\u0259\u0264\u0268\u026d"+
		"\u0273\u027a\u0280\u0287\u028d\u0297\u02a0\u02a8\u02ae\u02b3\u02b7\u02ba"+
		"\u02c3\u02c8\u02cc\u02d1\u02d5\u02dc\u02e0\u02e5\u02e9\u02ec\u02f4\u02fa"+
		"\u02fe\u0304\u0308\u030d\u0312\u0316\u031b\u031e\u0321\u0326\u032a\u032f"+
		"\u0335\u0339\u0340\u0344\u034b\u034f\u0356\u0359\u035c\u0363\u0366\u036a"+
		"\u036d\u0372\u0375\u0379\u037c\u037f\u0383\u0397\u0399\u03a1\u03a3\u03ae"+
		"\u03b1\u03b9\u03bd\u03c0\u03c9\u03cd\u03d7\u03dc\u03de\u03e5\u03f2\u03f5"+
		"\u03f8\u0400\u0403\u0406\u0408\u040e\u0410\u041a\u042b\u0432\u0435\u043a"+
		"\u0444\u0448\u0453\u045e\u0467\u0470\u0473\u047d\u0482\u0497\u049e\u04a7"+
		"\u04ac\u04af\u04b4\u04bb\u04bf\u04c3\u04c9\u04d0\u04d8\u04db\u04df\u04e6"+
		"\u04eb\u04f8\u04fb\u04fe\u0500\u0509\u0511\u051b\u0529\u052d\u0531\u0537"+
		"\u053d\u053f\u0549\u054d\u0555\u0558\u055e\u0560\u0567\u056b\u0570\u0577"+
		"\u057b\u0580\u0588\u058f\u0597\u059d\u05a3\u05b0\u05da\u05e5\u05f0\u05fb"+
		"\u0606\u0611\u061c\u0626\u062b\u0630\u063b\u0642\u0646\u064c\u0651\u0655"+
		"\u0659\u065b\u065e\u0662\u0666\u0668\u066b\u0677\u067b\u0681\u0684\u068c"+
		"\u0692\u069d\u06a3\u06a7\u06ad\u06b1\u06b6\u06bb\u06bf\u06c4\u06c7\u06ca"+
		"\u06cf\u06d3\u06d8\u06de\u06e2\u06e9\u06ed\u06f4\u06f7\u06fa\u0701\u0706"+
		"\u070a\u070d\u0713\u0718\u071b\u071e\u0721\u072c\u0731\u0737\u0740\u0742"+
		"\u0746\u074e\u0750\u075a\u0763\u0767\u076c\u0775\u0778\u0782\u0792\u079e"+
		"\u07a3\u07a5\u07ab\u07ad\u07b1\u07b6\u07b9\u07c0\u07c9\u07cc\u07d3\u07d6"+
		"\u07df\u07e6\u07ed\u07f1\u07f8\u07fb\u0803\u0806\u0808\u080d\u0816\u0819"+
		"\u0822\u0827\u082a\u0832\u083b\u084a\u084d\u0851\u0859\u085d\u0866\u0869"+
		"\u0872\u0877\u087a\u0881\u088a\u088e\u0890\u0897\u089b\u08a0";
	public static final ATN _ATN =
		new ATNDeserializer().deserialize(_serializedATN.toCharArray());
	static {
		_decisionToDFA = new DFA[_ATN.getNumberOfDecisions()];
		for (int i = 0; i < _ATN.getNumberOfDecisions(); i++) {
			_decisionToDFA[i] = new DFA(_ATN.getDecisionState(i), i);
		}
	}
}