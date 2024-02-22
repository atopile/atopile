# Generated from AtopileParser.g4 by ANTLR 4.13.1
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

if "." in __name__:
    from .AtopileParserBase import AtopileParserBase
else:
    from AtopileParserBase import AtopileParserBase

def serializedATN():
    return [
        4,1,79,253,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,2,35,7,35,1,0,1,0,5,0,75,8,0,10,0,12,0,78,9,0,1,0,
        1,0,1,1,1,1,3,1,84,8,1,1,2,1,2,1,2,5,2,89,8,2,10,2,12,2,92,9,2,1,
        2,3,2,95,8,2,1,2,1,2,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,3,3,
        109,8,3,1,4,1,4,1,5,1,5,1,5,1,5,3,5,117,8,5,1,5,1,5,1,5,1,6,1,6,
        1,7,1,7,1,7,1,7,4,7,128,8,7,11,7,12,7,129,1,7,1,7,3,7,134,8,7,1,
        8,1,8,1,8,1,8,1,8,1,9,1,9,1,9,1,9,1,9,1,9,5,9,147,8,9,10,9,12,9,
        150,9,9,1,10,1,10,3,10,154,8,10,1,10,1,10,1,10,1,11,1,11,1,11,1,
        11,3,11,163,8,11,1,12,1,12,1,12,1,13,1,13,3,13,170,8,13,1,14,1,14,
        1,14,1,14,1,15,1,15,3,15,178,8,15,1,16,1,16,1,16,3,16,183,8,16,1,
        17,1,17,1,17,1,17,1,18,1,18,3,18,191,8,18,1,19,1,19,1,19,3,19,196,
        8,19,1,20,1,20,1,20,1,20,1,21,1,21,1,21,1,21,1,22,1,22,1,22,1,22,
        3,22,210,8,22,1,23,1,23,1,23,1,24,1,24,1,24,3,24,218,8,24,1,25,1,
        25,1,25,1,26,1,26,1,27,1,27,1,28,1,28,3,28,229,8,28,1,29,1,29,1,
        29,1,30,1,30,1,30,1,30,1,31,1,31,1,31,4,31,241,8,31,11,31,12,31,
        242,1,32,1,32,1,33,1,33,1,34,1,34,1,35,1,35,1,35,0,0,36,0,2,4,6,
        8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,
        52,54,56,58,60,62,64,66,68,70,0,2,1,0,6,8,1,0,16,17,251,0,76,1,0,
        0,0,2,83,1,0,0,0,4,85,1,0,0,0,6,108,1,0,0,0,8,110,1,0,0,0,10,112,
        1,0,0,0,12,121,1,0,0,0,14,133,1,0,0,0,16,135,1,0,0,0,18,140,1,0,
        0,0,20,151,1,0,0,0,22,162,1,0,0,0,24,164,1,0,0,0,26,167,1,0,0,0,
        28,171,1,0,0,0,30,175,1,0,0,0,32,179,1,0,0,0,34,184,1,0,0,0,36,188,
        1,0,0,0,38,195,1,0,0,0,40,197,1,0,0,0,42,201,1,0,0,0,44,209,1,0,
        0,0,46,211,1,0,0,0,48,214,1,0,0,0,50,219,1,0,0,0,52,222,1,0,0,0,
        54,224,1,0,0,0,56,228,1,0,0,0,58,230,1,0,0,0,60,233,1,0,0,0,62,237,
        1,0,0,0,64,244,1,0,0,0,66,246,1,0,0,0,68,248,1,0,0,0,70,250,1,0,
        0,0,72,75,5,19,0,0,73,75,3,2,1,0,74,72,1,0,0,0,74,73,1,0,0,0,75,
        78,1,0,0,0,76,74,1,0,0,0,76,77,1,0,0,0,77,79,1,0,0,0,78,76,1,0,0,
        0,79,80,5,0,0,1,80,1,1,0,0,0,81,84,3,4,2,0,82,84,3,8,4,0,83,81,1,
        0,0,0,83,82,1,0,0,0,84,3,1,0,0,0,85,90,3,6,3,0,86,87,5,40,0,0,87,
        89,3,6,3,0,88,86,1,0,0,0,89,92,1,0,0,0,90,88,1,0,0,0,90,91,1,0,0,
        0,91,94,1,0,0,0,92,90,1,0,0,0,93,95,5,40,0,0,94,93,1,0,0,0,94,95,
        1,0,0,0,95,96,1,0,0,0,96,97,5,19,0,0,97,5,1,0,0,0,98,109,3,18,9,
        0,99,109,3,16,8,0,100,109,3,20,10,0,101,109,3,42,21,0,102,109,3,
        40,20,0,103,109,3,48,24,0,104,109,3,46,23,0,105,109,3,52,26,0,106,
        109,3,54,27,0,107,109,3,24,12,0,108,98,1,0,0,0,108,99,1,0,0,0,108,
        100,1,0,0,0,108,101,1,0,0,0,108,102,1,0,0,0,108,103,1,0,0,0,108,
        104,1,0,0,0,108,105,1,0,0,0,108,106,1,0,0,0,108,107,1,0,0,0,109,
        7,1,0,0,0,110,111,3,10,5,0,111,9,1,0,0,0,112,113,3,12,6,0,113,116,
        3,66,33,0,114,115,5,12,0,0,115,117,3,56,28,0,116,114,1,0,0,0,116,
        117,1,0,0,0,117,118,1,0,0,0,118,119,5,39,0,0,119,120,3,14,7,0,120,
        11,1,0,0,0,121,122,7,0,0,0,122,13,1,0,0,0,123,134,3,4,2,0,124,125,
        5,19,0,0,125,127,5,1,0,0,126,128,3,2,1,0,127,126,1,0,0,0,128,129,
        1,0,0,0,129,127,1,0,0,0,129,130,1,0,0,0,130,131,1,0,0,0,131,132,
        5,2,0,0,132,134,1,0,0,0,133,123,1,0,0,0,133,124,1,0,0,0,134,15,1,
        0,0,0,135,136,5,13,0,0,136,137,3,56,28,0,137,138,5,12,0,0,138,139,
        3,68,34,0,139,17,1,0,0,0,140,141,5,12,0,0,141,142,3,68,34,0,142,
        143,5,13,0,0,143,148,3,56,28,0,144,145,5,38,0,0,145,147,3,56,28,
        0,146,144,1,0,0,0,147,150,1,0,0,0,148,146,1,0,0,0,148,149,1,0,0,
        0,149,19,1,0,0,0,150,148,1,0,0,0,151,153,3,56,28,0,152,154,3,58,
        29,0,153,152,1,0,0,0,153,154,1,0,0,0,154,155,1,0,0,0,155,156,5,42,
        0,0,156,157,3,22,11,0,157,21,1,0,0,0,158,163,3,68,34,0,159,163,3,
        50,25,0,160,163,3,38,19,0,161,163,3,56,28,0,162,158,1,0,0,0,162,
        159,1,0,0,0,162,160,1,0,0,0,162,161,1,0,0,0,163,23,1,0,0,0,164,165,
        3,56,28,0,165,166,3,58,29,0,166,25,1,0,0,0,167,169,5,4,0,0,168,170,
        3,66,33,0,169,168,1,0,0,0,169,170,1,0,0,0,170,27,1,0,0,0,171,172,
        3,26,13,0,172,173,5,15,0,0,173,174,3,26,13,0,174,29,1,0,0,0,175,
        177,5,4,0,0,176,178,3,66,33,0,177,176,1,0,0,0,177,178,1,0,0,0,178,
        31,1,0,0,0,179,182,5,4,0,0,180,183,5,32,0,0,181,183,3,66,33,0,182,
        180,1,0,0,0,182,181,1,0,0,0,182,183,1,0,0,0,183,33,1,0,0,0,184,185,
        3,30,15,0,185,186,5,29,0,0,186,187,3,32,16,0,187,35,1,0,0,0,188,
        190,5,4,0,0,189,191,3,66,33,0,190,189,1,0,0,0,190,191,1,0,0,0,191,
        37,1,0,0,0,192,196,3,28,14,0,193,196,3,34,17,0,194,196,3,36,18,0,
        195,192,1,0,0,0,195,193,1,0,0,0,195,194,1,0,0,0,196,39,1,0,0,0,197,
        198,3,56,28,0,198,199,5,65,0,0,199,200,3,56,28,0,200,41,1,0,0,0,
        201,202,3,44,22,0,202,203,5,54,0,0,203,204,3,44,22,0,204,43,1,0,
        0,0,205,210,3,56,28,0,206,210,3,60,30,0,207,210,3,46,23,0,208,210,
        3,48,24,0,209,205,1,0,0,0,209,206,1,0,0,0,209,207,1,0,0,0,209,208,
        1,0,0,0,210,45,1,0,0,0,211,212,5,10,0,0,212,213,3,66,33,0,213,47,
        1,0,0,0,214,217,5,9,0,0,215,218,3,66,33,0,216,218,3,64,32,0,217,
        215,1,0,0,0,217,216,1,0,0,0,218,49,1,0,0,0,219,220,5,11,0,0,220,
        221,3,56,28,0,221,51,1,0,0,0,222,223,3,68,34,0,223,53,1,0,0,0,224,
        225,5,18,0,0,225,55,1,0,0,0,226,229,3,62,31,0,227,229,3,66,33,0,
        228,226,1,0,0,0,228,227,1,0,0,0,229,57,1,0,0,0,230,231,5,39,0,0,
        231,232,3,56,28,0,232,59,1,0,0,0,233,234,3,56,28,0,234,235,5,33,
        0,0,235,236,3,64,32,0,236,61,1,0,0,0,237,240,3,66,33,0,238,239,5,
        33,0,0,239,241,3,66,33,0,240,238,1,0,0,0,241,242,1,0,0,0,242,240,
        1,0,0,0,242,243,1,0,0,0,243,63,1,0,0,0,244,245,5,4,0,0,245,65,1,
        0,0,0,246,247,5,20,0,0,247,67,1,0,0,0,248,249,5,3,0,0,249,69,1,0,
        0,0,250,251,7,1,0,0,251,71,1,0,0,0,21,74,76,83,90,94,108,116,129,
        133,148,153,162,169,177,182,190,195,209,217,228,242
    ]

class AtopileParser ( AtopileParserBase ):

    grammarFileName = "AtopileParser.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "'component'", "'module'", 
                     "'interface'", "'pin'", "'signal'", "'new'", "'from'", 
                     "'import'", "'assert'", "'to'", "'True'", "'False'", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "'+/-'", "'\\u00B1'", "'%'", "'.'", "'...'", "'*'", 
                     "'('", "')'", "','", "':'", "';'", "'**'", "'='", "'['", 
                     "']'", "'|'", "'^'", "'&'", "'<<'", "'>>'", "'+'", 
                     "'-'", "'/'", "'//'", "'~'", "'{'", "'}'", "'<'", "'>'", 
                     "'=='", "'>='", "'<='", "'<>'", "'!='", "'@'", "'->'", 
                     "'+='", "'-='", "'*='", "'@='", "'/='", "'&='", "'|='", 
                     "'^='", "'<<='", "'>>='", "'**='", "'//='" ]

    symbolicNames = [ "<INVALID>", "INDENT", "DEDENT", "STRING", "NUMBER", 
                      "INTEGER", "COMPONENT", "MODULE", "INTERFACE", "PIN", 
                      "SIGNAL", "NEW", "FROM", "IMPORT", "ASSERT", "TO", 
                      "TRUE", "FALSE", "ASSERTION_STRING", "NEWLINE", "NAME", 
                      "STRING_LITERAL", "BYTES_LITERAL", "DECIMAL_INTEGER", 
                      "OCT_INTEGER", "HEX_INTEGER", "BIN_INTEGER", "FLOAT_NUMBER", 
                      "IMAG_NUMBER", "PLUS_OR_MINUS", "PLUS_SLASH_MINUS", 
                      "PLUS_MINUS_SIGN", "PERCENT", "DOT", "ELLIPSIS", "STAR", 
                      "OPEN_PAREN", "CLOSE_PAREN", "COMMA", "COLON", "SEMI_COLON", 
                      "POWER", "ASSIGN", "OPEN_BRACK", "CLOSE_BRACK", "OR_OP", 
                      "XOR", "AND_OP", "LEFT_SHIFT", "RIGHT_SHIFT", "ADD", 
                      "MINUS", "DIV", "IDIV", "NOT_OP", "OPEN_BRACE", "CLOSE_BRACE", 
                      "LESS_THAN", "GREATER_THAN", "EQUALS", "GT_EQ", "LT_EQ", 
                      "NOT_EQ_1", "NOT_EQ_2", "AT", "ARROW", "ADD_ASSIGN", 
                      "SUB_ASSIGN", "MULT_ASSIGN", "AT_ASSIGN", "DIV_ASSIGN", 
                      "AND_ASSIGN", "OR_ASSIGN", "XOR_ASSIGN", "LEFT_SHIFT_ASSIGN", 
                      "RIGHT_SHIFT_ASSIGN", "POWER_ASSIGN", "IDIV_ASSIGN", 
                      "SKIP_", "UNKNOWN_CHAR" ]

    RULE_file_input = 0
    RULE_stmt = 1
    RULE_simple_stmts = 2
    RULE_simple_stmt = 3
    RULE_compound_stmt = 4
    RULE_blockdef = 5
    RULE_blocktype = 6
    RULE_block = 7
    RULE_dep_import_stmt = 8
    RULE_import_stmt = 9
    RULE_assign_stmt = 10
    RULE_assignable = 11
    RULE_declaration_stmt = 12
    RULE_quantity_end = 13
    RULE_bound_quantity = 14
    RULE_bilateral_nominal = 15
    RULE_bilateral_tolerance = 16
    RULE_bilateral_quantity = 17
    RULE_implicit_quantity = 18
    RULE_literal_physical = 19
    RULE_retype_stmt = 20
    RULE_connect_stmt = 21
    RULE_connectable = 22
    RULE_signaldef_stmt = 23
    RULE_pindef_stmt = 24
    RULE_new_stmt = 25
    RULE_string_stmt = 26
    RULE_assert_stmt = 27
    RULE_name_or_attr = 28
    RULE_type_info = 29
    RULE_numerical_pin_ref = 30
    RULE_attr = 31
    RULE_totally_an_integer = 32
    RULE_name = 33
    RULE_string = 34
    RULE_boolean_ = 35

    ruleNames =  [ "file_input", "stmt", "simple_stmts", "simple_stmt", 
                   "compound_stmt", "blockdef", "blocktype", "block", "dep_import_stmt", 
                   "import_stmt", "assign_stmt", "assignable", "declaration_stmt", 
                   "quantity_end", "bound_quantity", "bilateral_nominal", 
                   "bilateral_tolerance", "bilateral_quantity", "implicit_quantity", 
                   "literal_physical", "retype_stmt", "connect_stmt", "connectable", 
                   "signaldef_stmt", "pindef_stmt", "new_stmt", "string_stmt", 
                   "assert_stmt", "name_or_attr", "type_info", "numerical_pin_ref", 
                   "attr", "totally_an_integer", "name", "string", "boolean_" ]

    EOF = Token.EOF
    INDENT=1
    DEDENT=2
    STRING=3
    NUMBER=4
    INTEGER=5
    COMPONENT=6
    MODULE=7
    INTERFACE=8
    PIN=9
    SIGNAL=10
    NEW=11
    FROM=12
    IMPORT=13
    ASSERT=14
    TO=15
    TRUE=16
    FALSE=17
    ASSERTION_STRING=18
    NEWLINE=19
    NAME=20
    STRING_LITERAL=21
    BYTES_LITERAL=22
    DECIMAL_INTEGER=23
    OCT_INTEGER=24
    HEX_INTEGER=25
    BIN_INTEGER=26
    FLOAT_NUMBER=27
    IMAG_NUMBER=28
    PLUS_OR_MINUS=29
    PLUS_SLASH_MINUS=30
    PLUS_MINUS_SIGN=31
    PERCENT=32
    DOT=33
    ELLIPSIS=34
    STAR=35
    OPEN_PAREN=36
    CLOSE_PAREN=37
    COMMA=38
    COLON=39
    SEMI_COLON=40
    POWER=41
    ASSIGN=42
    OPEN_BRACK=43
    CLOSE_BRACK=44
    OR_OP=45
    XOR=46
    AND_OP=47
    LEFT_SHIFT=48
    RIGHT_SHIFT=49
    ADD=50
    MINUS=51
    DIV=52
    IDIV=53
    NOT_OP=54
    OPEN_BRACE=55
    CLOSE_BRACE=56
    LESS_THAN=57
    GREATER_THAN=58
    EQUALS=59
    GT_EQ=60
    LT_EQ=61
    NOT_EQ_1=62
    NOT_EQ_2=63
    AT=64
    ARROW=65
    ADD_ASSIGN=66
    SUB_ASSIGN=67
    MULT_ASSIGN=68
    AT_ASSIGN=69
    DIV_ASSIGN=70
    AND_ASSIGN=71
    OR_ASSIGN=72
    XOR_ASSIGN=73
    LEFT_SHIFT_ASSIGN=74
    RIGHT_SHIFT_ASSIGN=75
    POWER_ASSIGN=76
    IDIV_ASSIGN=77
    SKIP_=78
    UNKNOWN_CHAR=79

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.1")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class File_inputContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EOF(self):
            return self.getToken(AtopileParser.EOF, 0)

        def NEWLINE(self, i:int=None):
            if i is None:
                return self.getTokens(AtopileParser.NEWLINE)
            else:
                return self.getToken(AtopileParser.NEWLINE, i)

        def stmt(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.StmtContext)
            else:
                return self.getTypedRuleContext(AtopileParser.StmtContext,i)


        def getRuleIndex(self):
            return AtopileParser.RULE_file_input

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFile_input" ):
                return visitor.visitFile_input(self)
            else:
                return visitor.visitChildren(self)




    def file_input(self):

        localctx = AtopileParser.File_inputContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_file_input)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 76
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 1849288) != 0):
                self.state = 74
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [19]:
                    self.state = 72
                    self.match(AtopileParser.NEWLINE)
                    pass
                elif token in [3, 6, 7, 8, 9, 10, 12, 13, 18, 20]:
                    self.state = 73
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 78
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 79
            self.match(AtopileParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def simple_stmts(self):
            return self.getTypedRuleContext(AtopileParser.Simple_stmtsContext,0)


        def compound_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Compound_stmtContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStmt" ):
                return visitor.visitStmt(self)
            else:
                return visitor.visitChildren(self)




    def stmt(self):

        localctx = AtopileParser.StmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_stmt)
        try:
            self.state = 83
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 18, 20]:
                self.enterOuterAlt(localctx, 1)
                self.state = 81
                self.simple_stmts()
                pass
            elif token in [6, 7, 8]:
                self.enterOuterAlt(localctx, 2)
                self.state = 82
                self.compound_stmt()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Simple_stmtsContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def simple_stmt(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.Simple_stmtContext)
            else:
                return self.getTypedRuleContext(AtopileParser.Simple_stmtContext,i)


        def NEWLINE(self):
            return self.getToken(AtopileParser.NEWLINE, 0)

        def SEMI_COLON(self, i:int=None):
            if i is None:
                return self.getTokens(AtopileParser.SEMI_COLON)
            else:
                return self.getToken(AtopileParser.SEMI_COLON, i)

        def getRuleIndex(self):
            return AtopileParser.RULE_simple_stmts

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSimple_stmts" ):
                return visitor.visitSimple_stmts(self)
            else:
                return visitor.visitChildren(self)




    def simple_stmts(self):

        localctx = AtopileParser.Simple_stmtsContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_simple_stmts)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 85
            self.simple_stmt()
            self.state = 90
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 86
                    self.match(AtopileParser.SEMI_COLON)
                    self.state = 87
                    self.simple_stmt() 
                self.state = 92
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 94
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==40:
                self.state = 93
                self.match(AtopileParser.SEMI_COLON)


            self.state = 96
            self.match(AtopileParser.NEWLINE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Simple_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def import_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Import_stmtContext,0)


        def dep_import_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Dep_import_stmtContext,0)


        def assign_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Assign_stmtContext,0)


        def connect_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Connect_stmtContext,0)


        def retype_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Retype_stmtContext,0)


        def pindef_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Pindef_stmtContext,0)


        def signaldef_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Signaldef_stmtContext,0)


        def string_stmt(self):
            return self.getTypedRuleContext(AtopileParser.String_stmtContext,0)


        def assert_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Assert_stmtContext,0)


        def declaration_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Declaration_stmtContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_simple_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSimple_stmt" ):
                return visitor.visitSimple_stmt(self)
            else:
                return visitor.visitChildren(self)




    def simple_stmt(self):

        localctx = AtopileParser.Simple_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_simple_stmt)
        try:
            self.state = 108
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 98
                self.import_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 99
                self.dep_import_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 100
                self.assign_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 101
                self.connect_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 102
                self.retype_stmt()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 103
                self.pindef_stmt()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 104
                self.signaldef_stmt()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 105
                self.string_stmt()
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 106
                self.assert_stmt()
                pass

            elif la_ == 10:
                self.enterOuterAlt(localctx, 10)
                self.state = 107
                self.declaration_stmt()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Compound_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def blockdef(self):
            return self.getTypedRuleContext(AtopileParser.BlockdefContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_compound_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCompound_stmt" ):
                return visitor.visitCompound_stmt(self)
            else:
                return visitor.visitChildren(self)




    def compound_stmt(self):

        localctx = AtopileParser.Compound_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_compound_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 110
            self.blockdef()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BlockdefContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def blocktype(self):
            return self.getTypedRuleContext(AtopileParser.BlocktypeContext,0)


        def name(self):
            return self.getTypedRuleContext(AtopileParser.NameContext,0)


        def COLON(self):
            return self.getToken(AtopileParser.COLON, 0)

        def block(self):
            return self.getTypedRuleContext(AtopileParser.BlockContext,0)


        def FROM(self):
            return self.getToken(AtopileParser.FROM, 0)

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_blockdef

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBlockdef" ):
                return visitor.visitBlockdef(self)
            else:
                return visitor.visitChildren(self)




    def blockdef(self):

        localctx = AtopileParser.BlockdefContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_blockdef)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 112
            self.blocktype()
            self.state = 113
            self.name()
            self.state = 116
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 114
                self.match(AtopileParser.FROM)
                self.state = 115
                self.name_or_attr()


            self.state = 118
            self.match(AtopileParser.COLON)
            self.state = 119
            self.block()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BlocktypeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def COMPONENT(self):
            return self.getToken(AtopileParser.COMPONENT, 0)

        def MODULE(self):
            return self.getToken(AtopileParser.MODULE, 0)

        def INTERFACE(self):
            return self.getToken(AtopileParser.INTERFACE, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_blocktype

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBlocktype" ):
                return visitor.visitBlocktype(self)
            else:
                return visitor.visitChildren(self)




    def blocktype(self):

        localctx = AtopileParser.BlocktypeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_blocktype)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 121
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 448) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BlockContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def simple_stmts(self):
            return self.getTypedRuleContext(AtopileParser.Simple_stmtsContext,0)


        def NEWLINE(self):
            return self.getToken(AtopileParser.NEWLINE, 0)

        def INDENT(self):
            return self.getToken(AtopileParser.INDENT, 0)

        def DEDENT(self):
            return self.getToken(AtopileParser.DEDENT, 0)

        def stmt(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.StmtContext)
            else:
                return self.getTypedRuleContext(AtopileParser.StmtContext,i)


        def getRuleIndex(self):
            return AtopileParser.RULE_block

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBlock" ):
                return visitor.visitBlock(self)
            else:
                return visitor.visitChildren(self)




    def block(self):

        localctx = AtopileParser.BlockContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_block)
        self._la = 0 # Token type
        try:
            self.state = 133
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 18, 20]:
                self.enterOuterAlt(localctx, 1)
                self.state = 123
                self.simple_stmts()
                pass
            elif token in [19]:
                self.enterOuterAlt(localctx, 2)
                self.state = 124
                self.match(AtopileParser.NEWLINE)
                self.state = 125
                self.match(AtopileParser.INDENT)
                self.state = 127 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 126
                    self.stmt()
                    self.state = 129 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 1325000) != 0)):
                        break

                self.state = 131
                self.match(AtopileParser.DEDENT)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Dep_import_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IMPORT(self):
            return self.getToken(AtopileParser.IMPORT, 0)

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def FROM(self):
            return self.getToken(AtopileParser.FROM, 0)

        def string(self):
            return self.getTypedRuleContext(AtopileParser.StringContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_dep_import_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDep_import_stmt" ):
                return visitor.visitDep_import_stmt(self)
            else:
                return visitor.visitChildren(self)




    def dep_import_stmt(self):

        localctx = AtopileParser.Dep_import_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_dep_import_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 135
            self.match(AtopileParser.IMPORT)
            self.state = 136
            self.name_or_attr()
            self.state = 137
            self.match(AtopileParser.FROM)
            self.state = 138
            self.string()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Import_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def FROM(self):
            return self.getToken(AtopileParser.FROM, 0)

        def string(self):
            return self.getTypedRuleContext(AtopileParser.StringContext,0)


        def IMPORT(self):
            return self.getToken(AtopileParser.IMPORT, 0)

        def name_or_attr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.Name_or_attrContext)
            else:
                return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(AtopileParser.COMMA)
            else:
                return self.getToken(AtopileParser.COMMA, i)

        def getRuleIndex(self):
            return AtopileParser.RULE_import_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitImport_stmt" ):
                return visitor.visitImport_stmt(self)
            else:
                return visitor.visitChildren(self)




    def import_stmt(self):

        localctx = AtopileParser.Import_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_import_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 140
            self.match(AtopileParser.FROM)
            self.state = 141
            self.string()
            self.state = 142
            self.match(AtopileParser.IMPORT)
            self.state = 143
            self.name_or_attr()
            self.state = 148
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==38:
                self.state = 144
                self.match(AtopileParser.COMMA)
                self.state = 145
                self.name_or_attr()
                self.state = 150
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Assign_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def ASSIGN(self):
            return self.getToken(AtopileParser.ASSIGN, 0)

        def assignable(self):
            return self.getTypedRuleContext(AtopileParser.AssignableContext,0)


        def type_info(self):
            return self.getTypedRuleContext(AtopileParser.Type_infoContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_assign_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssign_stmt" ):
                return visitor.visitAssign_stmt(self)
            else:
                return visitor.visitChildren(self)




    def assign_stmt(self):

        localctx = AtopileParser.Assign_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_assign_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 151
            self.name_or_attr()
            self.state = 153
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==39:
                self.state = 152
                self.type_info()


            self.state = 155
            self.match(AtopileParser.ASSIGN)
            self.state = 156
            self.assignable()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AssignableContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def string(self):
            return self.getTypedRuleContext(AtopileParser.StringContext,0)


        def new_stmt(self):
            return self.getTypedRuleContext(AtopileParser.New_stmtContext,0)


        def literal_physical(self):
            return self.getTypedRuleContext(AtopileParser.Literal_physicalContext,0)


        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_assignable

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssignable" ):
                return visitor.visitAssignable(self)
            else:
                return visitor.visitChildren(self)




    def assignable(self):

        localctx = AtopileParser.AssignableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_assignable)
        try:
            self.state = 162
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3]:
                self.enterOuterAlt(localctx, 1)
                self.state = 158
                self.string()
                pass
            elif token in [11]:
                self.enterOuterAlt(localctx, 2)
                self.state = 159
                self.new_stmt()
                pass
            elif token in [4]:
                self.enterOuterAlt(localctx, 3)
                self.state = 160
                self.literal_physical()
                pass
            elif token in [20]:
                self.enterOuterAlt(localctx, 4)
                self.state = 161
                self.name_or_attr()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Declaration_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def type_info(self):
            return self.getTypedRuleContext(AtopileParser.Type_infoContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_declaration_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDeclaration_stmt" ):
                return visitor.visitDeclaration_stmt(self)
            else:
                return visitor.visitChildren(self)




    def declaration_stmt(self):

        localctx = AtopileParser.Declaration_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_declaration_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 164
            self.name_or_attr()
            self.state = 165
            self.type_info()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Quantity_endContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self):
            return self.getToken(AtopileParser.NUMBER, 0)

        def name(self):
            return self.getTypedRuleContext(AtopileParser.NameContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_quantity_end

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitQuantity_end" ):
                return visitor.visitQuantity_end(self)
            else:
                return visitor.visitChildren(self)




    def quantity_end(self):

        localctx = AtopileParser.Quantity_endContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_quantity_end)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 167
            self.match(AtopileParser.NUMBER)
            self.state = 169
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==20:
                self.state = 168
                self.name()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Bound_quantityContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def quantity_end(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.Quantity_endContext)
            else:
                return self.getTypedRuleContext(AtopileParser.Quantity_endContext,i)


        def TO(self):
            return self.getToken(AtopileParser.TO, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_bound_quantity

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBound_quantity" ):
                return visitor.visitBound_quantity(self)
            else:
                return visitor.visitChildren(self)




    def bound_quantity(self):

        localctx = AtopileParser.Bound_quantityContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_bound_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 171
            self.quantity_end()
            self.state = 172
            self.match(AtopileParser.TO)
            self.state = 173
            self.quantity_end()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Bilateral_nominalContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self):
            return self.getToken(AtopileParser.NUMBER, 0)

        def name(self):
            return self.getTypedRuleContext(AtopileParser.NameContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_bilateral_nominal

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBilateral_nominal" ):
                return visitor.visitBilateral_nominal(self)
            else:
                return visitor.visitChildren(self)




    def bilateral_nominal(self):

        localctx = AtopileParser.Bilateral_nominalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_bilateral_nominal)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 175
            self.match(AtopileParser.NUMBER)
            self.state = 177
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==20:
                self.state = 176
                self.name()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Bilateral_toleranceContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self):
            return self.getToken(AtopileParser.NUMBER, 0)

        def PERCENT(self):
            return self.getToken(AtopileParser.PERCENT, 0)

        def name(self):
            return self.getTypedRuleContext(AtopileParser.NameContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_bilateral_tolerance

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBilateral_tolerance" ):
                return visitor.visitBilateral_tolerance(self)
            else:
                return visitor.visitChildren(self)




    def bilateral_tolerance(self):

        localctx = AtopileParser.Bilateral_toleranceContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_bilateral_tolerance)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 179
            self.match(AtopileParser.NUMBER)
            self.state = 182
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [32]:
                self.state = 180
                self.match(AtopileParser.PERCENT)
                pass
            elif token in [20]:
                self.state = 181
                self.name()
                pass
            elif token in [19, 40]:
                pass
            else:
                pass
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Bilateral_quantityContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def bilateral_nominal(self):
            return self.getTypedRuleContext(AtopileParser.Bilateral_nominalContext,0)


        def PLUS_OR_MINUS(self):
            return self.getToken(AtopileParser.PLUS_OR_MINUS, 0)

        def bilateral_tolerance(self):
            return self.getTypedRuleContext(AtopileParser.Bilateral_toleranceContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_bilateral_quantity

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBilateral_quantity" ):
                return visitor.visitBilateral_quantity(self)
            else:
                return visitor.visitChildren(self)




    def bilateral_quantity(self):

        localctx = AtopileParser.Bilateral_quantityContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_bilateral_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 184
            self.bilateral_nominal()
            self.state = 185
            self.match(AtopileParser.PLUS_OR_MINUS)
            self.state = 186
            self.bilateral_tolerance()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Implicit_quantityContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self):
            return self.getToken(AtopileParser.NUMBER, 0)

        def name(self):
            return self.getTypedRuleContext(AtopileParser.NameContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_implicit_quantity

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitImplicit_quantity" ):
                return visitor.visitImplicit_quantity(self)
            else:
                return visitor.visitChildren(self)




    def implicit_quantity(self):

        localctx = AtopileParser.Implicit_quantityContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_implicit_quantity)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 188
            self.match(AtopileParser.NUMBER)
            self.state = 190
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==20:
                self.state = 189
                self.name()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Literal_physicalContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def bound_quantity(self):
            return self.getTypedRuleContext(AtopileParser.Bound_quantityContext,0)


        def bilateral_quantity(self):
            return self.getTypedRuleContext(AtopileParser.Bilateral_quantityContext,0)


        def implicit_quantity(self):
            return self.getTypedRuleContext(AtopileParser.Implicit_quantityContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_literal_physical

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLiteral_physical" ):
                return visitor.visitLiteral_physical(self)
            else:
                return visitor.visitChildren(self)




    def literal_physical(self):

        localctx = AtopileParser.Literal_physicalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_literal_physical)
        try:
            self.state = 195
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,16,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 192
                self.bound_quantity()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 193
                self.bilateral_quantity()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 194
                self.implicit_quantity()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Retype_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name_or_attr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.Name_or_attrContext)
            else:
                return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,i)


        def ARROW(self):
            return self.getToken(AtopileParser.ARROW, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_retype_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRetype_stmt" ):
                return visitor.visitRetype_stmt(self)
            else:
                return visitor.visitChildren(self)




    def retype_stmt(self):

        localctx = AtopileParser.Retype_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_retype_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 197
            self.name_or_attr()
            self.state = 198
            self.match(AtopileParser.ARROW)
            self.state = 199
            self.name_or_attr()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Connect_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def connectable(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.ConnectableContext)
            else:
                return self.getTypedRuleContext(AtopileParser.ConnectableContext,i)


        def NOT_OP(self):
            return self.getToken(AtopileParser.NOT_OP, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_connect_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConnect_stmt" ):
                return visitor.visitConnect_stmt(self)
            else:
                return visitor.visitChildren(self)




    def connect_stmt(self):

        localctx = AtopileParser.Connect_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 201
            self.connectable()
            self.state = 202
            self.match(AtopileParser.NOT_OP)
            self.state = 203
            self.connectable()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ConnectableContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def numerical_pin_ref(self):
            return self.getTypedRuleContext(AtopileParser.Numerical_pin_refContext,0)


        def signaldef_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Signaldef_stmtContext,0)


        def pindef_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Pindef_stmtContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_connectable

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConnectable" ):
                return visitor.visitConnectable(self)
            else:
                return visitor.visitChildren(self)




    def connectable(self):

        localctx = AtopileParser.ConnectableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_connectable)
        try:
            self.state = 209
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,17,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 205
                self.name_or_attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 206
                self.numerical_pin_ref()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 207
                self.signaldef_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 208
                self.pindef_stmt()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Signaldef_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def SIGNAL(self):
            return self.getToken(AtopileParser.SIGNAL, 0)

        def name(self):
            return self.getTypedRuleContext(AtopileParser.NameContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_signaldef_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSignaldef_stmt" ):
                return visitor.visitSignaldef_stmt(self)
            else:
                return visitor.visitChildren(self)




    def signaldef_stmt(self):

        localctx = AtopileParser.Signaldef_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_signaldef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 211
            self.match(AtopileParser.SIGNAL)
            self.state = 212
            self.name()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Pindef_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def PIN(self):
            return self.getToken(AtopileParser.PIN, 0)

        def name(self):
            return self.getTypedRuleContext(AtopileParser.NameContext,0)


        def totally_an_integer(self):
            return self.getTypedRuleContext(AtopileParser.Totally_an_integerContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_pindef_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPindef_stmt" ):
                return visitor.visitPindef_stmt(self)
            else:
                return visitor.visitChildren(self)




    def pindef_stmt(self):

        localctx = AtopileParser.Pindef_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_pindef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 214
            self.match(AtopileParser.PIN)
            self.state = 217
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [20]:
                self.state = 215
                self.name()
                pass
            elif token in [4]:
                self.state = 216
                self.totally_an_integer()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class New_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NEW(self):
            return self.getToken(AtopileParser.NEW, 0)

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_new_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNew_stmt" ):
                return visitor.visitNew_stmt(self)
            else:
                return visitor.visitChildren(self)




    def new_stmt(self):

        localctx = AtopileParser.New_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_new_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 219
            self.match(AtopileParser.NEW)
            self.state = 220
            self.name_or_attr()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class String_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def string(self):
            return self.getTypedRuleContext(AtopileParser.StringContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_string_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitString_stmt" ):
                return visitor.visitString_stmt(self)
            else:
                return visitor.visitChildren(self)




    def string_stmt(self):

        localctx = AtopileParser.String_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_string_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 222
            self.string()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Assert_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ASSERTION_STRING(self):
            return self.getToken(AtopileParser.ASSERTION_STRING, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_assert_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssert_stmt" ):
                return visitor.visitAssert_stmt(self)
            else:
                return visitor.visitChildren(self)




    def assert_stmt(self):

        localctx = AtopileParser.Assert_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_assert_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 224
            self.match(AtopileParser.ASSERTION_STRING)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Name_or_attrContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def attr(self):
            return self.getTypedRuleContext(AtopileParser.AttrContext,0)


        def name(self):
            return self.getTypedRuleContext(AtopileParser.NameContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_name_or_attr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitName_or_attr" ):
                return visitor.visitName_or_attr(self)
            else:
                return visitor.visitChildren(self)




    def name_or_attr(self):

        localctx = AtopileParser.Name_or_attrContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_name_or_attr)
        try:
            self.state = 228
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,19,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 226
                self.attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 227
                self.name()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Type_infoContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def COLON(self):
            return self.getToken(AtopileParser.COLON, 0)

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_type_info

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitType_info" ):
                return visitor.visitType_info(self)
            else:
                return visitor.visitChildren(self)




    def type_info(self):

        localctx = AtopileParser.Type_infoContext(self, self._ctx, self.state)
        self.enterRule(localctx, 58, self.RULE_type_info)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 230
            self.match(AtopileParser.COLON)
            self.state = 231
            self.name_or_attr()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Numerical_pin_refContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def DOT(self):
            return self.getToken(AtopileParser.DOT, 0)

        def totally_an_integer(self):
            return self.getTypedRuleContext(AtopileParser.Totally_an_integerContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_numerical_pin_ref

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNumerical_pin_ref" ):
                return visitor.visitNumerical_pin_ref(self)
            else:
                return visitor.visitChildren(self)




    def numerical_pin_ref(self):

        localctx = AtopileParser.Numerical_pin_refContext(self, self._ctx, self.state)
        self.enterRule(localctx, 60, self.RULE_numerical_pin_ref)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 233
            self.name_or_attr()
            self.state = 234
            self.match(AtopileParser.DOT)
            self.state = 235
            self.totally_an_integer()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AttrContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.NameContext)
            else:
                return self.getTypedRuleContext(AtopileParser.NameContext,i)


        def DOT(self, i:int=None):
            if i is None:
                return self.getTokens(AtopileParser.DOT)
            else:
                return self.getToken(AtopileParser.DOT, i)

        def getRuleIndex(self):
            return AtopileParser.RULE_attr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAttr" ):
                return visitor.visitAttr(self)
            else:
                return visitor.visitChildren(self)




    def attr(self):

        localctx = AtopileParser.AttrContext(self, self._ctx, self.state)
        self.enterRule(localctx, 62, self.RULE_attr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 237
            self.name()
            self.state = 240 
            self._errHandler.sync(self)
            _alt = 1
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    self.state = 238
                    self.match(AtopileParser.DOT)
                    self.state = 239
                    self.name()

                else:
                    raise NoViableAltException(self)
                self.state = 242 
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,20,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Totally_an_integerContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self):
            return self.getToken(AtopileParser.NUMBER, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_totally_an_integer

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTotally_an_integer" ):
                return visitor.visitTotally_an_integer(self)
            else:
                return visitor.visitChildren(self)




    def totally_an_integer(self):

        localctx = AtopileParser.Totally_an_integerContext(self, self._ctx, self.state)
        self.enterRule(localctx, 64, self.RULE_totally_an_integer)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 244
            self.match(AtopileParser.NUMBER)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NameContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NAME(self):
            return self.getToken(AtopileParser.NAME, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_name

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitName" ):
                return visitor.visitName(self)
            else:
                return visitor.visitChildren(self)




    def name(self):

        localctx = AtopileParser.NameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 66, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 246
            self.match(AtopileParser.NAME)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StringContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def STRING(self):
            return self.getToken(AtopileParser.STRING, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_string

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitString" ):
                return visitor.visitString(self)
            else:
                return visitor.visitChildren(self)




    def string(self):

        localctx = AtopileParser.StringContext(self, self._ctx, self.state)
        self.enterRule(localctx, 68, self.RULE_string)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 248
            self.match(AtopileParser.STRING)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Boolean_Context(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def TRUE(self):
            return self.getToken(AtopileParser.TRUE, 0)

        def FALSE(self):
            return self.getToken(AtopileParser.FALSE, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_boolean_

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBoolean_" ):
                return visitor.visitBoolean_(self)
            else:
                return visitor.visitChildren(self)




    def boolean_(self):

        localctx = AtopileParser.Boolean_Context(self, self._ctx, self.state)
        self.enterRule(localctx, 70, self.RULE_boolean_)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 250
            _la = self._input.LA(1)
            if not(_la==16 or _la==17):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





