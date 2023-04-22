// Generated from /Users/mattwildoer/Projects/atopile/src/atopile/parser/ato.g4 by ANTLR 4.9.2

from antlr4.Token import CommonToken
import re
import importlib

# Allow languages to extend the lexer and parser, by loading the parser dynamically
module_path = __name__[:-5]
language_name = __name__.split('.')[-1]
language_name = language_name[:-5]  # Remove Lexer from name
LanguageParser = getattr(importlib.import_module('{}Parser'.format(module_path)), '{}Parser'.format(language_name))

import org.antlr.v4.runtime.Lexer;
import org.antlr.v4.runtime.CharStream;
import org.antlr.v4.runtime.Token;
import org.antlr.v4.runtime.TokenStream;
import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.atn.*;
import org.antlr.v4.runtime.dfa.DFA;
import org.antlr.v4.runtime.misc.*;

@SuppressWarnings({"all", "warnings", "unchecked", "unused", "cast"})
public class atoLexer extends Lexer {
	static { RuntimeMetaData.checkVersion("4.9.2", RuntimeMetaData.VERSION); }

	protected static final DFA[] _decisionToDFA;
	protected static final PredictionContextCache _sharedContextCache =
		new PredictionContextCache();
	public static final int
		T__0=1, T__1=2, T__2=3, T__3=4, T__4=5, T__5=6, T__6=7, T__7=8, T__8=9, 
		T__9=10, T__10=11, T__11=12, T__12=13, T__13=14, T__14=15, STRING=16, 
		NUMBER=17, INTEGER=18, DEF=19, FROM=20, IMPORT=21, AS=22, GLOBAL=23, NEWLINE=24, 
		NAME=25, STRING_LITERAL=26, BYTES_LITERAL=27, DECIMAL_INTEGER=28, OCT_INTEGER=29, 
		HEX_INTEGER=30, BIN_INTEGER=31, FLOAT_NUMBER=32, IMAG_NUMBER=33, DOT=34, 
		ELLIPSIS=35, STAR=36, OPEN_PAREN=37, CLOSE_PAREN=38, COMMA=39, COLON=40, 
		SEMI_COLON=41, POWER=42, ASSIGN=43, OPEN_BRACK=44, CLOSE_BRACK=45, OR_OP=46, 
		XOR=47, AND_OP=48, LEFT_SHIFT=49, RIGHT_SHIFT=50, ADD=51, MINUS=52, DIV=53, 
		MOD=54, IDIV=55, CONNECT_OP=56, OPEN_BRACE=57, CLOSE_BRACE=58, LESS_THAN=59, 
		GREATER_THAN=60, EQUALS=61, GT_EQ=62, LT_EQ=63, NOT_EQ_1=64, NOT_EQ_2=65, 
		AT=66, ARROW=67, ADD_ASSIGN=68, SUB_ASSIGN=69, MULT_ASSIGN=70, AT_ASSIGN=71, 
		DIV_ASSIGN=72, MOD_ASSIGN=73, AND_ASSIGN=74, OR_ASSIGN=75, XOR_ASSIGN=76, 
		LEFT_SHIFT_ASSIGN=77, RIGHT_SHIFT_ASSIGN=78, POWER_ASSIGN=79, IDIV_ASSIGN=80, 
		SKIP_=81, UNKNOWN_CHAR=82;
	public static String[] channelNames = {
		"DEFAULT_TOKEN_CHANNEL", "HIDDEN"
	};

	public static String[] modeNames = {
		"DEFAULT_MODE"
	};

	private static String[] makeRuleNames() {
		return new String[] {
			"T__0", "T__1", "T__2", "T__3", "T__4", "T__5", "T__6", "T__7", "T__8", 
			"T__9", "T__10", "T__11", "T__12", "T__13", "T__14", "STRING", "NUMBER", 
			"INTEGER", "DEF", "FROM", "IMPORT", "AS", "GLOBAL", "NEWLINE", "NAME", 
			"STRING_LITERAL", "BYTES_LITERAL", "DECIMAL_INTEGER", "OCT_INTEGER", 
			"HEX_INTEGER", "BIN_INTEGER", "FLOAT_NUMBER", "IMAG_NUMBER", "DOT", "ELLIPSIS", 
			"STAR", "OPEN_PAREN", "CLOSE_PAREN", "COMMA", "COLON", "SEMI_COLON", 
			"POWER", "ASSIGN", "OPEN_BRACK", "CLOSE_BRACK", "OR_OP", "XOR", "AND_OP", 
			"LEFT_SHIFT", "RIGHT_SHIFT", "ADD", "MINUS", "DIV", "MOD", "IDIV", "CONNECT_OP", 
			"OPEN_BRACE", "CLOSE_BRACE", "LESS_THAN", "GREATER_THAN", "EQUALS", "GT_EQ", 
			"LT_EQ", "NOT_EQ_1", "NOT_EQ_2", "AT", "ARROW", "ADD_ASSIGN", "SUB_ASSIGN", 
			"MULT_ASSIGN", "AT_ASSIGN", "DIV_ASSIGN", "MOD_ASSIGN", "AND_ASSIGN", 
			"OR_ASSIGN", "XOR_ASSIGN", "LEFT_SHIFT_ASSIGN", "RIGHT_SHIFT_ASSIGN", 
			"POWER_ASSIGN", "IDIV_ASSIGN", "SKIP_", "UNKNOWN_CHAR", "SHORT_STRING", 
			"LONG_STRING", "LONG_STRING_ITEM", "LONG_STRING_CHAR", "STRING_ESCAPE_SEQ", 
			"NON_ZERO_DIGIT", "DIGIT", "OCT_DIGIT", "HEX_DIGIT", "BIN_DIGIT", "POINT_FLOAT", 
			"EXPONENT_FLOAT", "INT_PART", "FRACTION", "EXPONENT", "SHORT_BYTES", 
			"LONG_BYTES", "LONG_BYTES_ITEM", "SHORT_BYTES_CHAR_NO_SINGLE_QUOTE", 
			"SHORT_BYTES_CHAR_NO_DOUBLE_QUOTE", "LONG_BYTES_CHAR", "BYTES_ESCAPE_SEQ", 
			"SPACES", "COMMENT", "LINE_JOINING", "ID_START", "ID_CONTINUE"
		};
	}
	public static final String[] ruleNames = makeRuleNames();

	private static String[] makeLiteralNames() {
		return new String[] {
			null, "'nonlocal'", "'assert'", "'if'", "'else'", "'lambda'", "'or'", 
			"'and'", "'not'", "'in'", "'is'", "'None'", "'True'", "'False'", "'class'", 
			"'yield'", null, null, null, "'def'", "'from'", "'import'", "'as'", "'global'", 
			null, null, null, null, null, null, null, null, null, null, "'.'", "'...'", 
			"'*'", "'('", "')'", "','", "':'", "';'", "'**'", "'='", "'['", "']'", 
			"'|'", "'^'", "'&'", "'<<'", "'>>'", "'+'", "'-'", "'/'", "'%'", "'//'", 
			"'~'", "'{'", "'}'", "'<'", "'>'", "'=='", "'>='", "'<='", "'<>'", "'!='", 
			"'@'", "'->'", "'+='", "'-='", "'*='", "'@='", "'/='", "'%='", "'&='", 
			"'|='", "'^='", "'<<='", "'>>='", "'**='", "'//='"
		};
	}
	private static final String[] _LITERAL_NAMES = makeLiteralNames();
	private static String[] makeSymbolicNames() {
		return new String[] {
			null, null, null, null, null, null, null, null, null, null, null, null, 
			null, null, null, null, "STRING", "NUMBER", "INTEGER", "DEF", "FROM", 
			"IMPORT", "AS", "GLOBAL", "NEWLINE", "NAME", "STRING_LITERAL", "BYTES_LITERAL", 
			"DECIMAL_INTEGER", "OCT_INTEGER", "HEX_INTEGER", "BIN_INTEGER", "FLOAT_NUMBER", 
			"IMAG_NUMBER", "DOT", "ELLIPSIS", "STAR", "OPEN_PAREN", "CLOSE_PAREN", 
			"COMMA", "COLON", "SEMI_COLON", "POWER", "ASSIGN", "OPEN_BRACK", "CLOSE_BRACK", 
			"OR_OP", "XOR", "AND_OP", "LEFT_SHIFT", "RIGHT_SHIFT", "ADD", "MINUS", 
			"DIV", "MOD", "IDIV", "CONNECT_OP", "OPEN_BRACE", "CLOSE_BRACE", "LESS_THAN", 
			"GREATER_THAN", "EQUALS", "GT_EQ", "LT_EQ", "NOT_EQ_1", "NOT_EQ_2", "AT", 
			"ARROW", "ADD_ASSIGN", "SUB_ASSIGN", "MULT_ASSIGN", "AT_ASSIGN", "DIV_ASSIGN", 
			"MOD_ASSIGN", "AND_ASSIGN", "OR_ASSIGN", "XOR_ASSIGN", "LEFT_SHIFT_ASSIGN", 
			"RIGHT_SHIFT_ASSIGN", "POWER_ASSIGN", "IDIV_ASSIGN", "SKIP_", "UNKNOWN_CHAR"
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


	@property
	def tokens(self):
	    try:
	        return self._tokens
	    except AttributeError:
	        self._tokens = []
	        return self._tokens

	@property
	def indents(self):
	    try:
	        return self._indents
	    except AttributeError:
	        self._indents = []
	        return self._indents

	@property
	def opened(self):
	    try:
	        return self._opened
	    except AttributeError:
	        self._opened = 0
	        return self._opened

	@opened.setter
	def opened(self, value):
	    self._opened = value

	@property
	def lastToken(self):
	    try:
	        return self._lastToken
	    except AttributeError:
	        self._lastToken = None
	        return self._lastToken

	@lastToken.setter
	def lastToken(self, value):
	    self._lastToken = value

	def reset(self):
	    super().reset()
	    self.tokens = []
	    self.indents = []
	    self.opened = 0
	    self.lastToken = None

	def emitToken(self, t):
	    super().emitToken(t)
	    self.tokens.append(t)

	def nextToken(self):
	    if self._input.LA(1) == Token.EOF and self.indents:
	        for i in range(len(self.tokens)-1,-1,-1):
	            if self.tokens[i].type == Token.EOF:
	                self.tokens.pop(i)

	        self.emitToken(self.commonToken(LanguageParser.NEWLINE, '\n'))
	        while self.indents:
	            self.emitToken(self.createDedent())
	            self.indents.pop()

	        self.emitToken(self.commonToken(LanguageParser.EOF, "<EOF>"))
	    next = super().nextToken()
	    if next.channel == Token.DEFAULT_CHANNEL:
	        self.lastToken = next
	    return next if not self.tokens else self.tokens.pop(0)

	def createDedent(self):
	    dedent = self.commonToken(LanguageParser.DEDENT, "")
	    dedent.line = self.lastToken.line
	    return dedent

	def commonToken(self, type, text, indent=0):
	    stop = self.getCharIndex()-1-indent
	    start = (stop - len(text) + 1) if text else stop
	    return CommonToken(self._tokenFactorySourcePair, type, super().DEFAULT_TOKEN_CHANNEL, start, stop)

	@staticmethod
	def getIndentationCount(spaces):
	    count = 0
	    for ch in spaces:
	        if ch == '\t':
	            count += 8 - (count % 8)
	        else:
	            count += 1
	    return count

	def atStartOfInput(self):
	    return Lexer.column.fget(self) == 0 and Lexer.line.fget(self) == 1


	public atoLexer(CharStream input) {
		super(input);
		_interp = new LexerATNSimulator(this,_ATN,_decisionToDFA,_sharedContextCache);
	}

	@Override
	public String getGrammarFileName() { return "ato.g4"; }

	@Override
	public String[] getRuleNames() { return ruleNames; }

	@Override
	public String getSerializedATN() { return _serializedATN; }

	@Override
	public String[] getChannelNames() { return channelNames; }

	@Override
	public String[] getModeNames() { return modeNames; }

	@Override
	public ATN getATN() { return _ATN; }

	@Override
	public void action(RuleContext _localctx, int ruleIndex, int actionIndex) {
		switch (ruleIndex) {
		case 23:
			NEWLINE_action((RuleContext)_localctx, actionIndex);
			break;
		case 36:
			OPEN_PAREN_action((RuleContext)_localctx, actionIndex);
			break;
		case 37:
			CLOSE_PAREN_action((RuleContext)_localctx, actionIndex);
			break;
		case 43:
			OPEN_BRACK_action((RuleContext)_localctx, actionIndex);
			break;
		case 44:
			CLOSE_BRACK_action((RuleContext)_localctx, actionIndex);
			break;
		case 56:
			OPEN_BRACE_action((RuleContext)_localctx, actionIndex);
			break;
		case 57:
			CLOSE_BRACE_action((RuleContext)_localctx, actionIndex);
			break;
		}
	}
	private void NEWLINE_action(RuleContext _localctx, int actionIndex) {
		switch (actionIndex) {
		case 0:

			tempt = Lexer.text.fget(self)
			newLine = re.sub("[^\r\n\f]+", "", tempt)
			spaces = re.sub("[\r\n\f]+", "", tempt)
			la_char = ""
			try:
			    la = self._input.LA(1)
			    la_char = chr(la)       # Python does not compare char to ints directly
			except ValueError:          # End of file
			    pass

			# Strip newlines inside open clauses except if we are near EOF. We keep NEWLINEs near EOF to
			# satisfy the final newline needed by the single_put rule used by the REPL.
			try:
			    nextnext_la = self._input.LA(2)
			    nextnext_la_char = chr(nextnext_la)
			except ValueError:
			    nextnext_eof = True
			else:
			    nextnext_eof = False

			if self.opened > 0 or nextnext_eof is False and (la_char == '\r' or la_char == '\n' or la_char == '\f' or la_char == '#'):
			    self.skip()
			else:
			    indent = self.getIndentationCount(spaces)
			    previous = self.indents[-1] if self.indents else 0
			    self.emitToken(self.commonToken(self.NEWLINE, newLine, indent=indent))      # NEWLINE is actually the '\n' char
			    if indent == previous:
			        self.skip()
			    elif indent > previous:
			        self.indents.append(indent)
			        self.emitToken(self.commonToken(LanguageParser.INDENT, spaces))
			    else:
			        while self.indents and self.indents[-1] > indent:
			            self.emitToken(self.createDedent())
			            self.indents.pop()
			    
			break;
		}
	}
	private void OPEN_PAREN_action(RuleContext _localctx, int actionIndex) {
		switch (actionIndex) {
		case 1:
			self.opened += 1
			break;
		}
	}
	private void CLOSE_PAREN_action(RuleContext _localctx, int actionIndex) {
		switch (actionIndex) {
		case 2:
			self.opened -= 1
			break;
		}
	}
	private void OPEN_BRACK_action(RuleContext _localctx, int actionIndex) {
		switch (actionIndex) {
		case 3:
			self.opened += 1
			break;
		}
	}
	private void CLOSE_BRACK_action(RuleContext _localctx, int actionIndex) {
		switch (actionIndex) {
		case 4:
			self.opened -= 1
			break;
		}
	}
	private void OPEN_BRACE_action(RuleContext _localctx, int actionIndex) {
		switch (actionIndex) {
		case 5:
			self.opened += 1
			break;
		}
	}
	private void CLOSE_BRACE_action(RuleContext _localctx, int actionIndex) {
		switch (actionIndex) {
		case 6:
			self.opened -= 1
			break;
		}
	}
	@Override
	public boolean sempred(RuleContext _localctx, int ruleIndex, int predIndex) {
		switch (ruleIndex) {
		case 23:
			return NEWLINE_sempred((RuleContext)_localctx, predIndex);
		}
		return true;
	}
	private boolean NEWLINE_sempred(RuleContext _localctx, int predIndex) {
		switch (predIndex) {
		case 0:
			return self.atStartOfInput();
		}
		return true;
	}

	public static final String _serializedATN =
		"\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\2T\u02fd\b\1\4\2\t"+
		"\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7\4\b\t\b\4\t\t\t\4\n\t\n\4\13"+
		"\t\13\4\f\t\f\4\r\t\r\4\16\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22"+
		"\4\23\t\23\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30\4\31\t\31"+
		"\4\32\t\32\4\33\t\33\4\34\t\34\4\35\t\35\4\36\t\36\4\37\t\37\4 \t \4!"+
		"\t!\4\"\t\"\4#\t#\4$\t$\4%\t%\4&\t&\4\'\t\'\4(\t(\4)\t)\4*\t*\4+\t+\4"+
		",\t,\4-\t-\4.\t.\4/\t/\4\60\t\60\4\61\t\61\4\62\t\62\4\63\t\63\4\64\t"+
		"\64\4\65\t\65\4\66\t\66\4\67\t\67\48\t8\49\t9\4:\t:\4;\t;\4<\t<\4=\t="+
		"\4>\t>\4?\t?\4@\t@\4A\tA\4B\tB\4C\tC\4D\tD\4E\tE\4F\tF\4G\tG\4H\tH\4I"+
		"\tI\4J\tJ\4K\tK\4L\tL\4M\tM\4N\tN\4O\tO\4P\tP\4Q\tQ\4R\tR\4S\tS\4T\tT"+
		"\4U\tU\4V\tV\4W\tW\4X\tX\4Y\tY\4Z\tZ\4[\t[\4\\\t\\\4]\t]\4^\t^\4_\t_\4"+
		"`\t`\4a\ta\4b\tb\4c\tc\4d\td\4e\te\4f\tf\4g\tg\4h\th\4i\ti\4j\tj\4k\t"+
		"k\4l\tl\4m\tm\4n\tn\3\2\3\2\3\2\3\2\3\2\3\2\3\2\3\2\3\2\3\3\3\3\3\3\3"+
		"\3\3\3\3\3\3\3\3\4\3\4\3\4\3\5\3\5\3\5\3\5\3\5\3\6\3\6\3\6\3\6\3\6\3\6"+
		"\3\6\3\7\3\7\3\7\3\b\3\b\3\b\3\b\3\t\3\t\3\t\3\t\3\n\3\n\3\n\3\13\3\13"+
		"\3\13\3\f\3\f\3\f\3\f\3\f\3\r\3\r\3\r\3\r\3\r\3\16\3\16\3\16\3\16\3\16"+
		"\3\16\3\17\3\17\3\17\3\17\3\17\3\17\3\20\3\20\3\20\3\20\3\20\3\20\3\21"+
		"\3\21\5\21\u012c\n\21\3\22\3\22\3\22\5\22\u0131\n\22\3\23\3\23\3\23\3"+
		"\23\5\23\u0137\n\23\3\24\3\24\3\24\3\24\3\25\3\25\3\25\3\25\3\25\3\26"+
		"\3\26\3\26\3\26\3\26\3\26\3\26\3\27\3\27\3\27\3\30\3\30\3\30\3\30\3\30"+
		"\3\30\3\30\3\31\3\31\3\31\5\31\u0156\n\31\3\31\3\31\5\31\u015a\n\31\3"+
		"\31\5\31\u015d\n\31\5\31\u015f\n\31\3\31\3\31\3\32\3\32\7\32\u0165\n\32"+
		"\f\32\16\32\u0168\13\32\3\33\3\33\3\33\3\33\3\33\5\33\u016f\n\33\3\33"+
		"\3\33\5\33\u0173\n\33\3\34\3\34\3\34\3\34\3\34\5\34\u017a\n\34\3\34\3"+
		"\34\5\34\u017e\n\34\3\35\3\35\7\35\u0182\n\35\f\35\16\35\u0185\13\35\3"+
		"\35\6\35\u0188\n\35\r\35\16\35\u0189\5\35\u018c\n\35\3\36\3\36\3\36\6"+
		"\36\u0191\n\36\r\36\16\36\u0192\3\37\3\37\3\37\6\37\u0198\n\37\r\37\16"+
		"\37\u0199\3 \3 \3 \6 \u019f\n \r \16 \u01a0\3!\3!\5!\u01a5\n!\3\"\3\""+
		"\5\"\u01a9\n\"\3\"\3\"\3#\3#\3$\3$\3$\3$\3%\3%\3&\3&\3&\3\'\3\'\3\'\3"+
		"(\3(\3)\3)\3*\3*\3+\3+\3+\3,\3,\3-\3-\3-\3.\3.\3.\3/\3/\3\60\3\60\3\61"+
		"\3\61\3\62\3\62\3\62\3\63\3\63\3\63\3\64\3\64\3\65\3\65\3\66\3\66\3\67"+
		"\3\67\38\38\38\39\39\3:\3:\3:\3;\3;\3;\3<\3<\3=\3=\3>\3>\3>\3?\3?\3?\3"+
		"@\3@\3@\3A\3A\3A\3B\3B\3B\3C\3C\3D\3D\3D\3E\3E\3E\3F\3F\3F\3G\3G\3G\3"+
		"H\3H\3H\3I\3I\3I\3J\3J\3J\3K\3K\3K\3L\3L\3L\3M\3M\3M\3N\3N\3N\3N\3O\3"+
		"O\3O\3O\3P\3P\3P\3P\3Q\3Q\3Q\3Q\3R\3R\3R\5R\u0231\nR\3R\3R\3S\3S\3T\3"+
		"T\3T\7T\u023a\nT\fT\16T\u023d\13T\3T\3T\3T\3T\7T\u0243\nT\fT\16T\u0246"+
		"\13T\3T\5T\u0249\nT\3U\3U\3U\3U\3U\7U\u0250\nU\fU\16U\u0253\13U\3U\3U"+
		"\3U\3U\3U\3U\3U\3U\7U\u025d\nU\fU\16U\u0260\13U\3U\3U\3U\5U\u0265\nU\3"+
		"V\3V\5V\u0269\nV\3W\3W\3X\3X\3X\3X\5X\u0271\nX\3Y\3Y\3Z\3Z\3[\3[\3\\\3"+
		"\\\3]\3]\3^\5^\u027e\n^\3^\3^\3^\3^\5^\u0284\n^\3_\3_\5_\u0288\n_\3_\3"+
		"_\3`\6`\u028d\n`\r`\16`\u028e\3a\3a\6a\u0293\na\ra\16a\u0294\3b\3b\5b"+
		"\u0299\nb\3b\6b\u029c\nb\rb\16b\u029d\3c\3c\3c\7c\u02a3\nc\fc\16c\u02a6"+
		"\13c\3c\3c\3c\3c\7c\u02ac\nc\fc\16c\u02af\13c\3c\5c\u02b2\nc\3d\3d\3d"+
		"\3d\3d\7d\u02b9\nd\fd\16d\u02bc\13d\3d\3d\3d\3d\3d\3d\3d\3d\7d\u02c6\n"+
		"d\fd\16d\u02c9\13d\3d\3d\3d\5d\u02ce\nd\3e\3e\5e\u02d2\ne\3f\5f\u02d5"+
		"\nf\3g\5g\u02d8\ng\3h\5h\u02db\nh\3i\3i\3i\3j\6j\u02e1\nj\rj\16j\u02e2"+
		"\3k\3k\7k\u02e7\nk\fk\16k\u02ea\13k\3l\3l\5l\u02ee\nl\3l\5l\u02f1\nl\3"+
		"l\3l\5l\u02f5\nl\3m\5m\u02f8\nm\3n\3n\5n\u02fc\nn\6\u0251\u025e\u02ba"+
		"\u02c7\2o\3\3\5\4\7\5\t\6\13\7\r\b\17\t\21\n\23\13\25\f\27\r\31\16\33"+
		"\17\35\20\37\21!\22#\23%\24\'\25)\26+\27-\30/\31\61\32\63\33\65\34\67"+
		"\359\36;\37= ?!A\"C#E$G%I&K\'M(O)Q*S+U,W-Y.[/]\60_\61a\62c\63e\64g\65"+
		"i\66k\67m8o9q:s;u<w=y>{?}@\177A\u0081B\u0083C\u0085D\u0087E\u0089F\u008b"+
		"G\u008dH\u008fI\u0091J\u0093K\u0095L\u0097M\u0099N\u009bO\u009dP\u009f"+
		"Q\u00a1R\u00a3S\u00a5T\u00a7\2\u00a9\2\u00ab\2\u00ad\2\u00af\2\u00b1\2"+
		"\u00b3\2\u00b5\2\u00b7\2\u00b9\2\u00bb\2\u00bd\2\u00bf\2\u00c1\2\u00c3"+
		"\2\u00c5\2\u00c7\2\u00c9\2\u00cb\2\u00cd\2\u00cf\2\u00d1\2\u00d3\2\u00d5"+
		"\2\u00d7\2\u00d9\2\u00db\2\3\2\33\b\2HHTTWWhhttww\4\2HHhh\4\2TTtt\4\2"+
		"DDdd\4\2QQqq\4\2ZZzz\4\2LLll\6\2\f\f\16\17))^^\6\2\f\f\16\17$$^^\3\2^"+
		"^\3\2\63;\3\2\62;\3\2\629\5\2\62;CHch\3\2\62\63\4\2GGgg\4\2--//\7\2\2"+
		"\13\r\16\20(*]_\u0081\7\2\2\13\r\16\20#%]_\u0081\4\2\2]_\u0081\3\2\2\u0081"+
		"\4\2\13\13\"\"\4\2\f\f\16\17\u0129\2C\\aac|\u00ac\u00ac\u00b7\u00b7\u00bc"+
		"\u00bc\u00c2\u00d8\u00da\u00f8\u00fa\u0243\u0252\u02c3\u02c8\u02d3\u02e2"+
		"\u02e6\u02f0\u02f0\u037c\u037c\u0388\u0388\u038a\u038c\u038e\u038e\u0390"+
		"\u03a3\u03a5\u03d0\u03d2\u03f7\u03f9\u0483\u048c\u04d0\u04d2\u04fb\u0502"+
		"\u0511\u0533\u0558\u055b\u055b\u0563\u0589\u05d2\u05ec\u05f2\u05f4\u0623"+
		"\u063c\u0642\u064c\u0670\u0671\u0673\u06d5\u06d7\u06d7\u06e7\u06e8\u06f0"+
		"\u06f1\u06fc\u06fe\u0701\u0701\u0712\u0712\u0714\u0731\u074f\u076f\u0782"+
		"\u07a7\u07b3\u07b3\u0906\u093b\u093f\u093f\u0952\u0952\u095a\u0963\u097f"+
		"\u097f\u0987\u098e\u0991\u0992\u0995\u09aa\u09ac\u09b2\u09b4\u09b4\u09b8"+
		"\u09bb\u09bf\u09bf\u09d0\u09d0\u09de\u09df\u09e1\u09e3\u09f2\u09f3\u0a07"+
		"\u0a0c\u0a11\u0a12\u0a15\u0a2a\u0a2c\u0a32\u0a34\u0a35\u0a37\u0a38\u0a3a"+
		"\u0a3b\u0a5b\u0a5e\u0a60\u0a60\u0a74\u0a76\u0a87\u0a8f\u0a91\u0a93\u0a95"+
		"\u0aaa\u0aac\u0ab2\u0ab4\u0ab5\u0ab7\u0abb\u0abf\u0abf\u0ad2\u0ad2\u0ae2"+
		"\u0ae3\u0b07\u0b0e\u0b11\u0b12\u0b15\u0b2a\u0b2c\u0b32\u0b34\u0b35\u0b37"+
		"\u0b3b\u0b3f\u0b3f\u0b5e\u0b5f\u0b61\u0b63\u0b73\u0b73\u0b85\u0b85\u0b87"+
		"\u0b8c\u0b90\u0b92\u0b94\u0b97\u0b9b\u0b9c\u0b9e\u0b9e\u0ba0\u0ba1\u0ba5"+
		"\u0ba6\u0baa\u0bac\u0bb0\u0bbb\u0c07\u0c0e\u0c10\u0c12\u0c14\u0c2a\u0c2c"+
		"\u0c35\u0c37\u0c3b\u0c62\u0c63\u0c87\u0c8e\u0c90\u0c92\u0c94\u0caa\u0cac"+
		"\u0cb5\u0cb7\u0cbb\u0cbf\u0cbf\u0ce0\u0ce0\u0ce2\u0ce3\u0d07\u0d0e\u0d10"+
		"\u0d12\u0d14\u0d2a\u0d2c\u0d3b\u0d62\u0d63\u0d87\u0d98\u0d9c\u0db3\u0db5"+
		"\u0dbd\u0dbf\u0dbf\u0dc2\u0dc8\u0e03\u0e32\u0e34\u0e35\u0e42\u0e48\u0e83"+
		"\u0e84\u0e86\u0e86\u0e89\u0e8a\u0e8c\u0e8c\u0e8f\u0e8f\u0e96\u0e99\u0e9b"+
		"\u0ea1\u0ea3\u0ea5\u0ea7\u0ea7\u0ea9\u0ea9\u0eac\u0ead\u0eaf\u0eb2\u0eb4"+
		"\u0eb5\u0ebf\u0ebf\u0ec2\u0ec6\u0ec8\u0ec8\u0ede\u0edf\u0f02\u0f02\u0f42"+
		"\u0f49\u0f4b\u0f6c\u0f8a\u0f8d\u1002\u1023\u1025\u1029\u102b\u102c\u1052"+
		"\u1057\u10a2\u10c7\u10d2\u10fc\u10fe\u10fe\u1102\u115b\u1161\u11a4\u11aa"+
		"\u11fb\u1202\u124a\u124c\u124f\u1252\u1258\u125a\u125a\u125c\u125f\u1262"+
		"\u128a\u128c\u128f\u1292\u12b2\u12b4\u12b7\u12ba\u12c0\u12c2\u12c2\u12c4"+
		"\u12c7\u12ca\u12d8\u12da\u1312\u1314\u1317\u131a\u135c\u1382\u1391\u13a2"+
		"\u13f6\u1403\u166e\u1671\u1678\u1683\u169c\u16a2\u16ec\u16f0\u16f2\u1702"+
		"\u170e\u1710\u1713\u1722\u1733\u1742\u1753\u1762\u176e\u1770\u1772\u1782"+
		"\u17b5\u17d9\u17d9\u17de\u17de\u1822\u1879\u1882\u18aa\u1902\u191e\u1952"+
		"\u196f\u1972\u1976\u1982\u19ab\u19c3\u19c9\u1a02\u1a18\u1d02\u1dc1\u1e02"+
		"\u1e9d\u1ea2\u1efb\u1f02\u1f17\u1f1a\u1f1f\u1f22\u1f47\u1f4a\u1f4f\u1f52"+
		"\u1f59\u1f5b\u1f5b\u1f5d\u1f5d\u1f5f\u1f5f\u1f61\u1f7f\u1f82\u1fb6\u1fb8"+
		"\u1fbe\u1fc0\u1fc0\u1fc4\u1fc6\u1fc8\u1fce\u1fd2\u1fd5\u1fd8\u1fdd\u1fe2"+
		"\u1fee\u1ff4\u1ff6\u1ff8\u1ffe\u2073\u2073\u2081\u2081\u2092\u2096\u2104"+
		"\u2104\u2109\u2109\u210c\u2115\u2117\u2117\u211a\u211f\u2126\u2126\u2128"+
		"\u2128\u212a\u212a\u212c\u2133\u2135\u213b\u213e\u2141\u2147\u214b\u2162"+
		"\u2185\u2c02\u2c30\u2c32\u2c60\u2c82\u2ce6\u2d02\u2d27\u2d32\u2d67\u2d71"+
		"\u2d71\u2d82\u2d98\u2da2\u2da8\u2daa\u2db0\u2db2\u2db8\u2dba\u2dc0\u2dc2"+
		"\u2dc8\u2dca\u2dd0\u2dd2\u2dd8\u2dda\u2de0\u3007\u3009\u3023\u302b\u3033"+
		"\u3037\u303a\u303e\u3043\u3098\u309d\u30a1\u30a3\u30fc\u30fe\u3101\u3107"+
		"\u312e\u3133\u3190\u31a2\u31b9\u31f2\u3201\u3402\u4db7\u4e02\u9fbd\ua002"+
		"\ua48e\ua802\ua803\ua805\ua807\ua809\ua80c\ua80e\ua824\uac02\ud7a5\uf902"+
		"\ufa2f\ufa32\ufa6c\ufa72\ufadb\ufb02\ufb08\ufb15\ufb19\ufb1f\ufb1f\ufb21"+
		"\ufb2a\ufb2c\ufb38\ufb3a\ufb3e\ufb40\ufb40\ufb42\ufb43\ufb45\ufb46\ufb48"+
		"\ufbb3\ufbd5\ufd3f\ufd52\ufd91\ufd94\ufdc9\ufdf2\ufdfd\ufe72\ufe76\ufe78"+
		"\ufefe\uff23\uff3c\uff43\uff5c\uff68\uffc0\uffc4\uffc9\uffcc\uffd1\uffd4"+
		"\uffd9\uffdc\uffde\u0096\2\62;\u0302\u0371\u0485\u0488\u0593\u05bb\u05bd"+
		"\u05bf\u05c1\u05c1\u05c3\u05c4\u05c6\u05c7\u05c9\u05c9\u0612\u0617\u064d"+
		"\u0660\u0662\u066b\u0672\u0672\u06d8\u06de\u06e1\u06e6\u06e9\u06ea\u06ec"+
		"\u06ef\u06f2\u06fb\u0713\u0713\u0732\u074c\u07a8\u07b2\u0903\u0905\u093e"+
		"\u093e\u0940\u094f\u0953\u0956\u0964\u0965\u0968\u0971\u0983\u0985\u09be"+
		"\u09be\u09c0\u09c6\u09c9\u09ca\u09cd\u09cf\u09d9\u09d9\u09e4\u09e5\u09e8"+
		"\u09f1\u0a03\u0a05\u0a3e\u0a3e\u0a40\u0a44\u0a49\u0a4a\u0a4d\u0a4f\u0a68"+
		"\u0a73\u0a83\u0a85\u0abe\u0abe\u0ac0\u0ac7\u0ac9\u0acb\u0acd\u0acf\u0ae4"+
		"\u0ae5\u0ae8\u0af1\u0b03\u0b05\u0b3e\u0b3e\u0b40\u0b45\u0b49\u0b4a\u0b4d"+
		"\u0b4f\u0b58\u0b59\u0b68\u0b71\u0b84\u0b84\u0bc0\u0bc4\u0bc8\u0bca\u0bcc"+
		"\u0bcf\u0bd9\u0bd9\u0be8\u0bf1\u0c03\u0c05\u0c40\u0c46\u0c48\u0c4a\u0c4c"+
		"\u0c4f\u0c57\u0c58\u0c68\u0c71\u0c84\u0c85\u0cbe\u0cbe\u0cc0\u0cc6\u0cc8"+
		"\u0cca\u0ccc\u0ccf\u0cd7\u0cd8\u0ce8\u0cf1\u0d04\u0d05\u0d40\u0d45\u0d48"+
		"\u0d4a\u0d4c\u0d4f\u0d59\u0d59\u0d68\u0d71\u0d84\u0d85\u0dcc\u0dcc\u0dd1"+
		"\u0dd6\u0dd8\u0dd8\u0dda\u0de1\u0df4\u0df5\u0e33\u0e33\u0e36\u0e3c\u0e49"+
		"\u0e50\u0e52\u0e5b\u0eb3\u0eb3\u0eb6\u0ebb\u0ebd\u0ebe\u0eca\u0ecf\u0ed2"+
		"\u0edb\u0f1a\u0f1b\u0f22\u0f2b\u0f37\u0f37\u0f39\u0f39\u0f3b\u0f3b\u0f40"+
		"\u0f41\u0f73\u0f86\u0f88\u0f89\u0f92\u0f99\u0f9b\u0fbe\u0fc8\u0fc8\u102e"+
		"\u1034\u1038\u103b\u1042\u104b\u1058\u105b\u1361\u1361\u136b\u1373\u1714"+
		"\u1716\u1734\u1736\u1754\u1755\u1774\u1775\u17b8\u17d5\u17df\u17df\u17e2"+
		"\u17eb\u180d\u180f\u1812\u181b\u18ab\u18ab\u1922\u192d\u1932\u193d\u1948"+
		"\u1951\u19b2\u19c2\u19ca\u19cb\u19d2\u19db\u1a19\u1a1d\u1dc2\u1dc5\u2041"+
		"\u2042\u2056\u2056\u20d2\u20de\u20e3\u20e3\u20e7\u20ed\u302c\u3031\u309b"+
		"\u309c\ua804\ua804\ua808\ua808\ua80d\ua80d\ua825\ua829\ufb20\ufb20\ufe02"+
		"\ufe11\ufe22\ufe25\ufe35\ufe36\ufe4f\ufe51\uff12\uff1b\uff41\uff41\2\u031d"+
		"\2\3\3\2\2\2\2\5\3\2\2\2\2\7\3\2\2\2\2\t\3\2\2\2\2\13\3\2\2\2\2\r\3\2"+
		"\2\2\2\17\3\2\2\2\2\21\3\2\2\2\2\23\3\2\2\2\2\25\3\2\2\2\2\27\3\2\2\2"+
		"\2\31\3\2\2\2\2\33\3\2\2\2\2\35\3\2\2\2\2\37\3\2\2\2\2!\3\2\2\2\2#\3\2"+
		"\2\2\2%\3\2\2\2\2\'\3\2\2\2\2)\3\2\2\2\2+\3\2\2\2\2-\3\2\2\2\2/\3\2\2"+
		"\2\2\61\3\2\2\2\2\63\3\2\2\2\2\65\3\2\2\2\2\67\3\2\2\2\29\3\2\2\2\2;\3"+
		"\2\2\2\2=\3\2\2\2\2?\3\2\2\2\2A\3\2\2\2\2C\3\2\2\2\2E\3\2\2\2\2G\3\2\2"+
		"\2\2I\3\2\2\2\2K\3\2\2\2\2M\3\2\2\2\2O\3\2\2\2\2Q\3\2\2\2\2S\3\2\2\2\2"+
		"U\3\2\2\2\2W\3\2\2\2\2Y\3\2\2\2\2[\3\2\2\2\2]\3\2\2\2\2_\3\2\2\2\2a\3"+
		"\2\2\2\2c\3\2\2\2\2e\3\2\2\2\2g\3\2\2\2\2i\3\2\2\2\2k\3\2\2\2\2m\3\2\2"+
		"\2\2o\3\2\2\2\2q\3\2\2\2\2s\3\2\2\2\2u\3\2\2\2\2w\3\2\2\2\2y\3\2\2\2\2"+
		"{\3\2\2\2\2}\3\2\2\2\2\177\3\2\2\2\2\u0081\3\2\2\2\2\u0083\3\2\2\2\2\u0085"+
		"\3\2\2\2\2\u0087\3\2\2\2\2\u0089\3\2\2\2\2\u008b\3\2\2\2\2\u008d\3\2\2"+
		"\2\2\u008f\3\2\2\2\2\u0091\3\2\2\2\2\u0093\3\2\2\2\2\u0095\3\2\2\2\2\u0097"+
		"\3\2\2\2\2\u0099\3\2\2\2\2\u009b\3\2\2\2\2\u009d\3\2\2\2\2\u009f\3\2\2"+
		"\2\2\u00a1\3\2\2\2\2\u00a3\3\2\2\2\2\u00a5\3\2\2\2\3\u00dd\3\2\2\2\5\u00e6"+
		"\3\2\2\2\7\u00ed\3\2\2\2\t\u00f0\3\2\2\2\13\u00f5\3\2\2\2\r\u00fc\3\2"+
		"\2\2\17\u00ff\3\2\2\2\21\u0103\3\2\2\2\23\u0107\3\2\2\2\25\u010a\3\2\2"+
		"\2\27\u010d\3\2\2\2\31\u0112\3\2\2\2\33\u0117\3\2\2\2\35\u011d\3\2\2\2"+
		"\37\u0123\3\2\2\2!\u012b\3\2\2\2#\u0130\3\2\2\2%\u0136\3\2\2\2\'\u0138"+
		"\3\2\2\2)\u013c\3\2\2\2+\u0141\3\2\2\2-\u0148\3\2\2\2/\u014b\3\2\2\2\61"+
		"\u015e\3\2\2\2\63\u0162\3\2\2\2\65\u016e\3\2\2\2\67\u0179\3\2\2\29\u018b"+
		"\3\2\2\2;\u018d\3\2\2\2=\u0194\3\2\2\2?\u019b\3\2\2\2A\u01a4\3\2\2\2C"+
		"\u01a8\3\2\2\2E\u01ac\3\2\2\2G\u01ae\3\2\2\2I\u01b2\3\2\2\2K\u01b4\3\2"+
		"\2\2M\u01b7\3\2\2\2O\u01ba\3\2\2\2Q\u01bc\3\2\2\2S\u01be\3\2\2\2U\u01c0"+
		"\3\2\2\2W\u01c3\3\2\2\2Y\u01c5\3\2\2\2[\u01c8\3\2\2\2]\u01cb\3\2\2\2_"+
		"\u01cd\3\2\2\2a\u01cf\3\2\2\2c\u01d1\3\2\2\2e\u01d4\3\2\2\2g\u01d7\3\2"+
		"\2\2i\u01d9\3\2\2\2k\u01db\3\2\2\2m\u01dd\3\2\2\2o\u01df\3\2\2\2q\u01e2"+
		"\3\2\2\2s\u01e4\3\2\2\2u\u01e7\3\2\2\2w\u01ea\3\2\2\2y\u01ec\3\2\2\2{"+
		"\u01ee\3\2\2\2}\u01f1\3\2\2\2\177\u01f4\3\2\2\2\u0081\u01f7\3\2\2\2\u0083"+
		"\u01fa\3\2\2\2\u0085\u01fd\3\2\2\2\u0087\u01ff\3\2\2\2\u0089\u0202\3\2"+
		"\2\2\u008b\u0205\3\2\2\2\u008d\u0208\3\2\2\2\u008f\u020b\3\2\2\2\u0091"+
		"\u020e\3\2\2\2\u0093\u0211\3\2\2\2\u0095\u0214\3\2\2\2\u0097\u0217\3\2"+
		"\2\2\u0099\u021a\3\2\2\2\u009b\u021d\3\2\2\2\u009d\u0221\3\2\2\2\u009f"+
		"\u0225\3\2\2\2\u00a1\u0229\3\2\2\2\u00a3\u0230\3\2\2\2\u00a5\u0234\3\2"+
		"\2\2\u00a7\u0248\3\2\2\2\u00a9\u0264\3\2\2\2\u00ab\u0268\3\2\2\2\u00ad"+
		"\u026a\3\2\2\2\u00af\u0270\3\2\2\2\u00b1\u0272\3\2\2\2\u00b3\u0274\3\2"+
		"\2\2\u00b5\u0276\3\2\2\2\u00b7\u0278\3\2\2\2\u00b9\u027a\3\2\2\2\u00bb"+
		"\u0283\3\2\2\2\u00bd\u0287\3\2\2\2\u00bf\u028c\3\2\2\2\u00c1\u0290\3\2"+
		"\2\2\u00c3\u0296\3\2\2\2\u00c5\u02b1\3\2\2\2\u00c7\u02cd\3\2\2\2\u00c9"+
		"\u02d1\3\2\2\2\u00cb\u02d4\3\2\2\2\u00cd\u02d7\3\2\2\2\u00cf\u02da\3\2"+
		"\2\2\u00d1\u02dc\3\2\2\2\u00d3\u02e0\3\2\2\2\u00d5\u02e4\3\2\2\2\u00d7"+
		"\u02eb\3\2\2\2\u00d9\u02f7\3\2\2\2\u00db\u02fb\3\2\2\2\u00dd\u00de\7p"+
		"\2\2\u00de\u00df\7q\2\2\u00df\u00e0\7p\2\2\u00e0\u00e1\7n\2\2\u00e1\u00e2"+
		"\7q\2\2\u00e2\u00e3\7e\2\2\u00e3\u00e4\7c\2\2\u00e4\u00e5\7n\2\2\u00e5"+
		"\4\3\2\2\2\u00e6\u00e7\7c\2\2\u00e7\u00e8\7u\2\2\u00e8\u00e9\7u\2\2\u00e9"+
		"\u00ea\7g\2\2\u00ea\u00eb\7t\2\2\u00eb\u00ec\7v\2\2\u00ec\6\3\2\2\2\u00ed"+
		"\u00ee\7k\2\2\u00ee\u00ef\7h\2\2\u00ef\b\3\2\2\2\u00f0\u00f1\7g\2\2\u00f1"+
		"\u00f2\7n\2\2\u00f2\u00f3\7u\2\2\u00f3\u00f4\7g\2\2\u00f4\n\3\2\2\2\u00f5"+
		"\u00f6\7n\2\2\u00f6\u00f7\7c\2\2\u00f7\u00f8\7o\2\2\u00f8\u00f9\7d\2\2"+
		"\u00f9\u00fa\7f\2\2\u00fa\u00fb\7c\2\2\u00fb\f\3\2\2\2\u00fc\u00fd\7q"+
		"\2\2\u00fd\u00fe\7t\2\2\u00fe\16\3\2\2\2\u00ff\u0100\7c\2\2\u0100\u0101"+
		"\7p\2\2\u0101\u0102\7f\2\2\u0102\20\3\2\2\2\u0103\u0104\7p\2\2\u0104\u0105"+
		"\7q\2\2\u0105\u0106\7v\2\2\u0106\22\3\2\2\2\u0107\u0108\7k\2\2\u0108\u0109"+
		"\7p\2\2\u0109\24\3\2\2\2\u010a\u010b\7k\2\2\u010b\u010c\7u\2\2\u010c\26"+
		"\3\2\2\2\u010d\u010e\7P\2\2\u010e\u010f\7q\2\2\u010f\u0110\7p\2\2\u0110"+
		"\u0111\7g\2\2\u0111\30\3\2\2\2\u0112\u0113\7V\2\2\u0113\u0114\7t\2\2\u0114"+
		"\u0115\7w\2\2\u0115\u0116\7g\2\2\u0116\32\3\2\2\2\u0117\u0118\7H\2\2\u0118"+
		"\u0119\7c\2\2\u0119\u011a\7n\2\2\u011a\u011b\7u\2\2\u011b\u011c\7g\2\2"+
		"\u011c\34\3\2\2\2\u011d\u011e\7e\2\2\u011e\u011f\7n\2\2\u011f\u0120\7"+
		"c\2\2\u0120\u0121\7u\2\2\u0121\u0122\7u\2\2\u0122\36\3\2\2\2\u0123\u0124"+
		"\7{\2\2\u0124\u0125\7k\2\2\u0125\u0126\7g\2\2\u0126\u0127\7n\2\2\u0127"+
		"\u0128\7f\2\2\u0128 \3\2\2\2\u0129\u012c\5\65\33\2\u012a\u012c\5\67\34"+
		"\2\u012b\u0129\3\2\2\2\u012b\u012a\3\2\2\2\u012c\"\3\2\2\2\u012d\u0131"+
		"\5%\23\2\u012e\u0131\5A!\2\u012f\u0131\5C\"\2\u0130\u012d\3\2\2\2\u0130"+
		"\u012e\3\2\2\2\u0130\u012f\3\2\2\2\u0131$\3\2\2\2\u0132\u0137\59\35\2"+
		"\u0133\u0137\5;\36\2\u0134\u0137\5=\37\2\u0135\u0137\5? \2\u0136\u0132"+
		"\3\2\2\2\u0136\u0133\3\2\2\2\u0136\u0134\3\2\2\2\u0136\u0135\3\2\2\2\u0137"+
		"&\3\2\2\2\u0138\u0139\7f\2\2\u0139\u013a\7g\2\2\u013a\u013b\7h\2\2\u013b"+
		"(\3\2\2\2\u013c\u013d\7h\2\2\u013d\u013e\7t\2\2\u013e\u013f\7q\2\2\u013f"+
		"\u0140\7o\2\2\u0140*\3\2\2\2\u0141\u0142\7k\2\2\u0142\u0143\7o\2\2\u0143"+
		"\u0144\7r\2\2\u0144\u0145\7q\2\2\u0145\u0146\7t\2\2\u0146\u0147\7v\2\2"+
		"\u0147,\3\2\2\2\u0148\u0149\7c\2\2\u0149\u014a\7u\2\2\u014a.\3\2\2\2\u014b"+
		"\u014c\7i\2\2\u014c\u014d\7n\2\2\u014d\u014e\7q\2\2\u014e\u014f\7d\2\2"+
		"\u014f\u0150\7c\2\2\u0150\u0151\7n\2\2\u0151\60\3\2\2\2\u0152\u0153\6"+
		"\31\2\2\u0153\u015f\5\u00d3j\2\u0154\u0156\7\17\2\2\u0155\u0154\3\2\2"+
		"\2\u0155\u0156\3\2\2\2\u0156\u0157\3\2\2\2\u0157\u015a\7\f\2\2\u0158\u015a"+
		"\4\16\17\2\u0159\u0155\3\2\2\2\u0159\u0158\3\2\2\2\u015a\u015c\3\2\2\2"+
		"\u015b\u015d\5\u00d3j\2\u015c\u015b\3\2\2\2\u015c\u015d\3\2\2\2\u015d"+
		"\u015f\3\2\2\2\u015e\u0152\3\2\2\2\u015e\u0159\3\2\2\2\u015f\u0160\3\2"+
		"\2\2\u0160\u0161\b\31\2\2\u0161\62\3\2\2\2\u0162\u0166\5\u00d9m\2\u0163"+
		"\u0165\5\u00dbn\2\u0164\u0163\3\2\2\2\u0165\u0168\3\2\2\2\u0166\u0164"+
		"\3\2\2\2\u0166\u0167\3\2\2\2\u0167\64\3\2\2\2\u0168\u0166\3\2\2\2\u0169"+
		"\u016f\t\2\2\2\u016a\u016b\t\3\2\2\u016b\u016f\t\4\2\2\u016c\u016d\t\4"+
		"\2\2\u016d\u016f\t\3\2\2\u016e\u0169\3\2\2\2\u016e\u016a\3\2\2\2\u016e"+
		"\u016c\3\2\2\2\u016e\u016f\3\2\2\2\u016f\u0172\3\2\2\2\u0170\u0173\5\u00a7"+
		"T\2\u0171\u0173\5\u00a9U\2\u0172\u0170\3\2\2\2\u0172\u0171\3\2\2\2\u0173"+
		"\66\3\2\2\2\u0174\u017a\t\5\2\2\u0175\u0176\t\5\2\2\u0176\u017a\t\4\2"+
		"\2\u0177\u0178\t\4\2\2\u0178\u017a\t\5\2\2\u0179\u0174\3\2\2\2\u0179\u0175"+
		"\3\2\2\2\u0179\u0177\3\2\2\2\u017a\u017d\3\2\2\2\u017b\u017e\5\u00c5c"+
		"\2\u017c\u017e\5\u00c7d\2\u017d\u017b\3\2\2\2\u017d\u017c\3\2\2\2\u017e"+
		"8\3\2\2\2\u017f\u0183\5\u00b1Y\2\u0180\u0182\5\u00b3Z\2\u0181\u0180\3"+
		"\2\2\2\u0182\u0185\3\2\2\2\u0183\u0181\3\2\2\2\u0183\u0184\3\2\2\2\u0184"+
		"\u018c\3\2\2\2\u0185\u0183\3\2\2\2\u0186\u0188\7\62\2\2\u0187\u0186\3"+
		"\2\2\2\u0188\u0189\3\2\2\2\u0189\u0187\3\2\2\2\u0189\u018a\3\2\2\2\u018a"+
		"\u018c\3\2\2\2\u018b\u017f\3\2\2\2\u018b\u0187\3\2\2\2\u018c:\3\2\2\2"+
		"\u018d\u018e\7\62\2\2\u018e\u0190\t\6\2\2\u018f\u0191\5\u00b5[\2\u0190"+
		"\u018f\3\2\2\2\u0191\u0192\3\2\2\2\u0192\u0190\3\2\2\2\u0192\u0193\3\2"+
		"\2\2\u0193<\3\2\2\2\u0194\u0195\7\62\2\2\u0195\u0197\t\7\2\2\u0196\u0198"+
		"\5\u00b7\\\2\u0197\u0196\3\2\2\2\u0198\u0199\3\2\2\2\u0199\u0197\3\2\2"+
		"\2\u0199\u019a\3\2\2\2\u019a>\3\2\2\2\u019b\u019c\7\62\2\2\u019c\u019e"+
		"\t\5\2\2\u019d\u019f\5\u00b9]\2\u019e\u019d\3\2\2\2\u019f\u01a0\3\2\2"+
		"\2\u01a0\u019e\3\2\2\2\u01a0\u01a1\3\2\2\2\u01a1@\3\2\2\2\u01a2\u01a5"+
		"\5\u00bb^\2\u01a3\u01a5\5\u00bd_\2\u01a4\u01a2\3\2\2\2\u01a4\u01a3\3\2"+
		"\2\2\u01a5B\3\2\2\2\u01a6\u01a9\5A!\2\u01a7\u01a9\5\u00bf`\2\u01a8\u01a6"+
		"\3\2\2\2\u01a8\u01a7\3\2\2\2\u01a9\u01aa\3\2\2\2\u01aa\u01ab\t\b\2\2\u01ab"+
		"D\3\2\2\2\u01ac\u01ad\7\60\2\2\u01adF\3\2\2\2\u01ae\u01af\7\60\2\2\u01af"+
		"\u01b0\7\60\2\2\u01b0\u01b1\7\60\2\2\u01b1H\3\2\2\2\u01b2\u01b3\7,\2\2"+
		"\u01b3J\3\2\2\2\u01b4\u01b5\7*\2\2\u01b5\u01b6\b&\3\2\u01b6L\3\2\2\2\u01b7"+
		"\u01b8\7+\2\2\u01b8\u01b9\b\'\4\2\u01b9N\3\2\2\2\u01ba\u01bb\7.\2\2\u01bb"+
		"P\3\2\2\2\u01bc\u01bd\7<\2\2\u01bdR\3\2\2\2\u01be\u01bf\7=\2\2\u01bfT"+
		"\3\2\2\2\u01c0\u01c1\7,\2\2\u01c1\u01c2\7,\2\2\u01c2V\3\2\2\2\u01c3\u01c4"+
		"\7?\2\2\u01c4X\3\2\2\2\u01c5\u01c6\7]\2\2\u01c6\u01c7\b-\5\2\u01c7Z\3"+
		"\2\2\2\u01c8\u01c9\7_\2\2\u01c9\u01ca\b.\6\2\u01ca\\\3\2\2\2\u01cb\u01cc"+
		"\7~\2\2\u01cc^\3\2\2\2\u01cd\u01ce\7`\2\2\u01ce`\3\2\2\2\u01cf\u01d0\7"+
		"(\2\2\u01d0b\3\2\2\2\u01d1\u01d2\7>\2\2\u01d2\u01d3\7>\2\2\u01d3d\3\2"+
		"\2\2\u01d4\u01d5\7@\2\2\u01d5\u01d6\7@\2\2\u01d6f\3\2\2\2\u01d7\u01d8"+
		"\7-\2\2\u01d8h\3\2\2\2\u01d9\u01da\7/\2\2\u01daj\3\2\2\2\u01db\u01dc\7"+
		"\61\2\2\u01dcl\3\2\2\2\u01dd\u01de\7\'\2\2\u01den\3\2\2\2\u01df\u01e0"+
		"\7\61\2\2\u01e0\u01e1\7\61\2\2\u01e1p\3\2\2\2\u01e2\u01e3\7\u0080\2\2"+
		"\u01e3r\3\2\2\2\u01e4\u01e5\7}\2\2\u01e5\u01e6\b:\7\2\u01e6t\3\2\2\2\u01e7"+
		"\u01e8\7\177\2\2\u01e8\u01e9\b;\b\2\u01e9v\3\2\2\2\u01ea\u01eb\7>\2\2"+
		"\u01ebx\3\2\2\2\u01ec\u01ed\7@\2\2\u01edz\3\2\2\2\u01ee\u01ef\7?\2\2\u01ef"+
		"\u01f0\7?\2\2\u01f0|\3\2\2\2\u01f1\u01f2\7@\2\2\u01f2\u01f3\7?\2\2\u01f3"+
		"~\3\2\2\2\u01f4\u01f5\7>\2\2\u01f5\u01f6\7?\2\2\u01f6\u0080\3\2\2\2\u01f7"+
		"\u01f8\7>\2\2\u01f8\u01f9\7@\2\2\u01f9\u0082\3\2\2\2\u01fa\u01fb\7#\2"+
		"\2\u01fb\u01fc\7?\2\2\u01fc\u0084\3\2\2\2\u01fd\u01fe\7B\2\2\u01fe\u0086"+
		"\3\2\2\2\u01ff\u0200\7/\2\2\u0200\u0201\7@\2\2\u0201\u0088\3\2\2\2\u0202"+
		"\u0203\7-\2\2\u0203\u0204\7?\2\2\u0204\u008a\3\2\2\2\u0205\u0206\7/\2"+
		"\2\u0206\u0207\7?\2\2\u0207\u008c\3\2\2\2\u0208\u0209\7,\2\2\u0209\u020a"+
		"\7?\2\2\u020a\u008e\3\2\2\2\u020b\u020c\7B\2\2\u020c\u020d\7?\2\2\u020d"+
		"\u0090\3\2\2\2\u020e\u020f\7\61\2\2\u020f\u0210\7?\2\2\u0210\u0092\3\2"+
		"\2\2\u0211\u0212\7\'\2\2\u0212\u0213\7?\2\2\u0213\u0094\3\2\2\2\u0214"+
		"\u0215\7(\2\2\u0215\u0216\7?\2\2\u0216\u0096\3\2\2\2\u0217\u0218\7~\2"+
		"\2\u0218\u0219\7?\2\2\u0219\u0098\3\2\2\2\u021a\u021b\7`\2\2\u021b\u021c"+
		"\7?\2\2\u021c\u009a\3\2\2\2\u021d\u021e\7>\2\2\u021e\u021f\7>\2\2\u021f"+
		"\u0220\7?\2\2\u0220\u009c\3\2\2\2\u0221\u0222\7@\2\2\u0222\u0223\7@\2"+
		"\2\u0223\u0224\7?\2\2\u0224\u009e\3\2\2\2\u0225\u0226\7,\2\2\u0226\u0227"+
		"\7,\2\2\u0227\u0228\7?\2\2\u0228\u00a0\3\2\2\2\u0229\u022a\7\61\2\2\u022a"+
		"\u022b\7\61\2\2\u022b\u022c\7?\2\2\u022c\u00a2\3\2\2\2\u022d\u0231\5\u00d3"+
		"j\2\u022e\u0231\5\u00d5k\2\u022f\u0231\5\u00d7l\2\u0230\u022d\3\2\2\2"+
		"\u0230\u022e\3\2\2\2\u0230\u022f\3\2\2\2\u0231\u0232\3\2\2\2\u0232\u0233"+
		"\bR\t\2\u0233\u00a4\3\2\2\2\u0234\u0235\13\2\2\2\u0235\u00a6\3\2\2\2\u0236"+
		"\u023b\7)\2\2\u0237\u023a\5\u00afX\2\u0238\u023a\n\t\2\2\u0239\u0237\3"+
		"\2\2\2\u0239\u0238\3\2\2\2\u023a\u023d\3\2\2\2\u023b\u0239\3\2\2\2\u023b"+
		"\u023c\3\2\2\2\u023c\u023e\3\2\2\2\u023d\u023b\3\2\2\2\u023e\u0249\7)"+
		"\2\2\u023f\u0244\7$\2\2\u0240\u0243\5\u00afX\2\u0241\u0243\n\n\2\2\u0242"+
		"\u0240\3\2\2\2\u0242\u0241\3\2\2\2\u0243\u0246\3\2\2\2\u0244\u0242\3\2"+
		"\2\2\u0244\u0245\3\2\2\2\u0245\u0247\3\2\2\2\u0246\u0244\3\2\2\2\u0247"+
		"\u0249\7$\2\2\u0248\u0236\3\2\2\2\u0248\u023f\3\2\2\2\u0249\u00a8\3\2"+
		"\2\2\u024a\u024b\7)\2\2\u024b\u024c\7)\2\2\u024c\u024d\7)\2\2\u024d\u0251"+
		"\3\2\2\2\u024e\u0250\5\u00abV\2\u024f\u024e\3\2\2\2\u0250\u0253\3\2\2"+
		"\2\u0251\u0252\3\2\2\2\u0251\u024f\3\2\2\2\u0252\u0254\3\2\2\2\u0253\u0251"+
		"\3\2\2\2\u0254\u0255\7)\2\2\u0255\u0256\7)\2\2\u0256\u0265\7)\2\2\u0257"+
		"\u0258\7$\2\2\u0258\u0259\7$\2\2\u0259\u025a\7$\2\2\u025a\u025e\3\2\2"+
		"\2\u025b\u025d\5\u00abV\2\u025c\u025b\3\2\2\2\u025d\u0260\3\2\2\2\u025e"+
		"\u025f\3\2\2\2\u025e\u025c\3\2\2\2\u025f\u0261\3\2\2\2\u0260\u025e\3\2"+
		"\2\2\u0261\u0262\7$\2\2\u0262\u0263\7$\2\2\u0263\u0265\7$\2\2\u0264\u024a"+
		"\3\2\2\2\u0264\u0257\3\2\2\2\u0265\u00aa\3\2\2\2\u0266\u0269\5\u00adW"+
		"\2\u0267\u0269\5\u00afX\2\u0268\u0266\3\2\2\2\u0268\u0267\3\2\2\2\u0269"+
		"\u00ac\3\2\2\2\u026a\u026b\n\13\2\2\u026b\u00ae\3\2\2\2\u026c\u026d\7"+
		"^\2\2\u026d\u0271\13\2\2\2\u026e\u026f\7^\2\2\u026f\u0271\5\61\31\2\u0270"+
		"\u026c\3\2\2\2\u0270\u026e\3\2\2\2\u0271\u00b0\3\2\2\2\u0272\u0273\t\f"+
		"\2\2\u0273\u00b2\3\2\2\2\u0274\u0275\t\r\2\2\u0275\u00b4\3\2\2\2\u0276"+
		"\u0277\t\16\2\2\u0277\u00b6\3\2\2\2\u0278\u0279\t\17\2\2\u0279\u00b8\3"+
		"\2\2\2\u027a\u027b\t\20\2\2\u027b\u00ba\3\2\2\2\u027c\u027e\5\u00bf`\2"+
		"\u027d\u027c\3\2\2\2\u027d\u027e\3\2\2\2\u027e\u027f\3\2\2\2\u027f\u0284"+
		"\5\u00c1a\2\u0280\u0281\5\u00bf`\2\u0281\u0282\7\60\2\2\u0282\u0284\3"+
		"\2\2\2\u0283\u027d\3\2\2\2\u0283\u0280\3\2\2\2\u0284\u00bc\3\2\2\2\u0285"+
		"\u0288\5\u00bf`\2\u0286\u0288\5\u00bb^\2\u0287\u0285\3\2\2\2\u0287\u0286"+
		"\3\2\2\2\u0288\u0289\3\2\2\2\u0289\u028a\5\u00c3b\2\u028a\u00be\3\2\2"+
		"\2\u028b\u028d\5\u00b3Z\2\u028c\u028b\3\2\2\2\u028d\u028e\3\2\2\2\u028e"+
		"\u028c\3\2\2\2\u028e\u028f\3\2\2\2\u028f\u00c0\3\2\2\2\u0290\u0292\7\60"+
		"\2\2\u0291\u0293\5\u00b3Z\2\u0292\u0291\3\2\2\2\u0293\u0294\3\2\2\2\u0294"+
		"\u0292\3\2\2\2\u0294\u0295\3\2\2\2\u0295\u00c2\3\2\2\2\u0296\u0298\t\21"+
		"\2\2\u0297\u0299\t\22\2\2\u0298\u0297\3\2\2\2\u0298\u0299\3\2\2\2\u0299"+
		"\u029b\3\2\2\2\u029a\u029c\5\u00b3Z\2\u029b\u029a\3\2\2\2\u029c\u029d"+
		"\3\2\2\2\u029d\u029b\3\2\2\2\u029d\u029e\3\2\2\2\u029e\u00c4\3\2\2\2\u029f"+
		"\u02a4\7)\2\2\u02a0\u02a3\5\u00cbf\2\u02a1\u02a3\5\u00d1i\2\u02a2\u02a0"+
		"\3\2\2\2\u02a2\u02a1\3\2\2\2\u02a3\u02a6\3\2\2\2\u02a4\u02a2\3\2\2\2\u02a4"+
		"\u02a5\3\2\2\2\u02a5\u02a7\3\2\2\2\u02a6\u02a4\3\2\2\2\u02a7\u02b2\7)"+
		"\2\2\u02a8\u02ad\7$\2\2\u02a9\u02ac\5\u00cdg\2\u02aa\u02ac\5\u00d1i\2"+
		"\u02ab\u02a9\3\2\2\2\u02ab\u02aa\3\2\2\2\u02ac\u02af\3\2\2\2\u02ad\u02ab"+
		"\3\2\2\2\u02ad\u02ae\3\2\2\2\u02ae\u02b0\3\2\2\2\u02af\u02ad\3\2\2\2\u02b0"+
		"\u02b2\7$\2\2\u02b1\u029f\3\2\2\2\u02b1\u02a8\3\2\2\2\u02b2\u00c6\3\2"+
		"\2\2\u02b3\u02b4\7)\2\2\u02b4\u02b5\7)\2\2\u02b5\u02b6\7)\2\2\u02b6\u02ba"+
		"\3\2\2\2\u02b7\u02b9\5\u00c9e\2\u02b8\u02b7\3\2\2\2\u02b9\u02bc\3\2\2"+
		"\2\u02ba\u02bb\3\2\2\2\u02ba\u02b8\3\2\2\2\u02bb\u02bd\3\2\2\2\u02bc\u02ba"+
		"\3\2\2\2\u02bd\u02be\7)\2\2\u02be\u02bf\7)\2\2\u02bf\u02ce\7)\2\2\u02c0"+
		"\u02c1\7$\2\2\u02c1\u02c2\7$\2\2\u02c2\u02c3\7$\2\2\u02c3\u02c7\3\2\2"+
		"\2\u02c4\u02c6\5\u00c9e\2\u02c5\u02c4\3\2\2\2\u02c6\u02c9\3\2\2\2\u02c7"+
		"\u02c8\3\2\2\2\u02c7\u02c5\3\2\2\2\u02c8\u02ca\3\2\2\2\u02c9\u02c7\3\2"+
		"\2\2\u02ca\u02cb\7$\2\2\u02cb\u02cc\7$\2\2\u02cc\u02ce\7$\2\2\u02cd\u02b3"+
		"\3\2\2\2\u02cd\u02c0\3\2\2\2\u02ce\u00c8\3\2\2\2\u02cf\u02d2\5\u00cfh"+
		"\2\u02d0\u02d2\5\u00d1i\2\u02d1\u02cf\3\2\2\2\u02d1\u02d0\3\2\2\2\u02d2"+
		"\u00ca\3\2\2\2\u02d3\u02d5\t\23\2\2\u02d4\u02d3\3\2\2\2\u02d5\u00cc\3"+
		"\2\2\2\u02d6\u02d8\t\24\2\2\u02d7\u02d6\3\2\2\2\u02d8\u00ce\3\2\2\2\u02d9"+
		"\u02db\t\25\2\2\u02da\u02d9\3\2\2\2\u02db\u00d0\3\2\2\2\u02dc\u02dd\7"+
		"^\2\2\u02dd\u02de\t\26\2\2\u02de\u00d2\3\2\2\2\u02df\u02e1\t\27\2\2\u02e0"+
		"\u02df\3\2\2\2\u02e1\u02e2\3\2\2\2\u02e2\u02e0\3\2\2\2\u02e2\u02e3\3\2"+
		"\2\2\u02e3\u00d4\3\2\2\2\u02e4\u02e8\7%\2\2\u02e5\u02e7\n\30\2\2\u02e6"+
		"\u02e5\3\2\2\2\u02e7\u02ea\3\2\2\2\u02e8\u02e6\3\2\2\2\u02e8\u02e9\3\2"+
		"\2\2\u02e9\u00d6\3\2\2\2\u02ea\u02e8\3\2\2\2\u02eb\u02ed\7^\2\2\u02ec"+
		"\u02ee\5\u00d3j\2\u02ed\u02ec\3\2\2\2\u02ed\u02ee\3\2\2\2\u02ee\u02f4"+
		"\3\2\2\2\u02ef\u02f1\7\17\2\2\u02f0\u02ef\3\2\2\2\u02f0\u02f1\3\2\2\2"+
		"\u02f1\u02f2\3\2\2\2\u02f2\u02f5\7\f\2\2\u02f3\u02f5\4\16\17\2\u02f4\u02f0"+
		"\3\2\2\2\u02f4\u02f3\3\2\2\2\u02f5\u00d8\3\2\2\2\u02f6\u02f8\t\31\2\2"+
		"\u02f7\u02f6\3\2\2\2\u02f8\u00da\3\2\2\2\u02f9\u02fc\5\u00d9m\2\u02fa"+
		"\u02fc\t\32\2\2\u02fb\u02f9\3\2\2\2\u02fb\u02fa\3\2\2\2\u02fc\u00dc\3"+
		"\2\2\2<\2\u012b\u0130\u0136\u0155\u0159\u015c\u015e\u0166\u016e\u0172"+
		"\u0179\u017d\u0183\u0189\u018b\u0192\u0199\u01a0\u01a4\u01a8\u0230\u0239"+
		"\u023b\u0242\u0244\u0248\u0251\u025e\u0264\u0268\u0270\u027d\u0283\u0287"+
		"\u028e\u0294\u0298\u029d\u02a2\u02a4\u02ab\u02ad\u02b1\u02ba\u02c7\u02cd"+
		"\u02d1\u02d4\u02d7\u02da\u02e2\u02e8\u02ed\u02f0\u02f4\u02f7\u02fb\n\3"+
		"\31\2\3&\3\3\'\4\3-\5\3.\6\3:\7\3;\b\b\2\2";
	public static final ATN _ATN =
		new ATNDeserializer().deserialize(_serializedATN.toCharArray());
	static {
		_decisionToDFA = new DFA[_ATN.getNumberOfDecisions()];
		for (int i = 0; i < _ATN.getNumberOfDecisions(); i++) {
			_decisionToDFA[i] = new DFA(_ATN.getDecisionState(i), i);
		}
	}
}