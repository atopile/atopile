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
        4,1,77,223,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,1,0,
        1,0,5,0,69,8,0,10,0,12,0,72,9,0,1,0,1,0,1,1,1,1,3,1,78,8,1,1,2,1,
        2,1,2,5,2,83,8,2,10,2,12,2,86,9,2,1,2,3,2,89,8,2,1,2,1,2,1,3,1,3,
        1,3,1,3,1,3,1,3,1,3,1,3,3,3,101,8,3,1,4,1,4,1,5,1,5,1,5,1,5,4,5,
        109,8,5,11,5,12,5,110,1,5,1,5,3,5,115,8,5,1,6,1,6,1,6,1,6,3,6,121,
        8,6,1,6,1,6,1,6,1,7,1,7,1,8,1,8,1,8,1,8,1,8,1,9,1,9,1,9,1,9,1,10,
        1,10,1,10,3,10,140,8,10,1,11,1,11,3,11,144,8,11,1,12,1,12,1,12,1,
        12,1,13,1,13,1,13,1,14,1,14,1,14,3,14,156,8,14,1,15,1,15,1,15,1,
        15,1,16,1,16,3,16,164,8,16,1,17,1,17,1,17,3,17,169,8,17,1,18,1,18,
        1,18,1,18,1,19,1,19,1,19,1,19,1,20,1,20,1,20,1,20,3,20,183,8,20,
        1,21,1,21,1,21,1,22,1,22,1,22,3,22,191,8,22,1,23,1,23,1,23,1,24,
        1,24,1,25,1,25,1,26,1,26,3,26,202,8,26,1,27,1,27,1,27,1,27,1,28,
        1,28,1,28,4,28,211,8,28,11,28,12,28,212,1,29,1,29,1,30,1,30,1,31,
        1,31,1,32,1,32,1,32,0,0,33,0,2,4,6,8,10,12,14,16,18,20,22,24,26,
        28,30,32,34,36,38,40,42,44,46,48,50,52,54,56,58,60,62,64,0,2,1,0,
        6,8,1,0,17,18,218,0,70,1,0,0,0,2,77,1,0,0,0,4,79,1,0,0,0,6,100,1,
        0,0,0,8,102,1,0,0,0,10,114,1,0,0,0,12,116,1,0,0,0,14,125,1,0,0,0,
        16,127,1,0,0,0,18,132,1,0,0,0,20,139,1,0,0,0,22,141,1,0,0,0,24,145,
        1,0,0,0,26,149,1,0,0,0,28,152,1,0,0,0,30,157,1,0,0,0,32,161,1,0,
        0,0,34,168,1,0,0,0,36,170,1,0,0,0,38,174,1,0,0,0,40,182,1,0,0,0,
        42,184,1,0,0,0,44,187,1,0,0,0,46,192,1,0,0,0,48,195,1,0,0,0,50,197,
        1,0,0,0,52,201,1,0,0,0,54,203,1,0,0,0,56,207,1,0,0,0,58,214,1,0,
        0,0,60,216,1,0,0,0,62,218,1,0,0,0,64,220,1,0,0,0,66,69,5,20,0,0,
        67,69,3,2,1,0,68,66,1,0,0,0,68,67,1,0,0,0,69,72,1,0,0,0,70,68,1,
        0,0,0,70,71,1,0,0,0,71,73,1,0,0,0,72,70,1,0,0,0,73,74,5,0,0,1,74,
        1,1,0,0,0,75,78,3,4,2,0,76,78,3,8,4,0,77,75,1,0,0,0,77,76,1,0,0,
        0,78,3,1,0,0,0,79,84,3,6,3,0,80,81,5,38,0,0,81,83,3,6,3,0,82,80,
        1,0,0,0,83,86,1,0,0,0,84,82,1,0,0,0,84,85,1,0,0,0,85,88,1,0,0,0,
        86,84,1,0,0,0,87,89,5,38,0,0,88,87,1,0,0,0,88,89,1,0,0,0,89,90,1,
        0,0,0,90,91,5,20,0,0,91,5,1,0,0,0,92,101,3,16,8,0,93,101,3,18,9,
        0,94,101,3,38,19,0,95,101,3,36,18,0,96,101,3,44,22,0,97,101,3,42,
        21,0,98,101,3,48,24,0,99,101,3,50,25,0,100,92,1,0,0,0,100,93,1,0,
        0,0,100,94,1,0,0,0,100,95,1,0,0,0,100,96,1,0,0,0,100,97,1,0,0,0,
        100,98,1,0,0,0,100,99,1,0,0,0,101,7,1,0,0,0,102,103,3,12,6,0,103,
        9,1,0,0,0,104,115,3,4,2,0,105,106,5,20,0,0,106,108,5,1,0,0,107,109,
        3,2,1,0,108,107,1,0,0,0,109,110,1,0,0,0,110,108,1,0,0,0,110,111,
        1,0,0,0,111,112,1,0,0,0,112,113,5,2,0,0,113,115,1,0,0,0,114,104,
        1,0,0,0,114,105,1,0,0,0,115,11,1,0,0,0,116,117,3,14,7,0,117,120,
        3,60,30,0,118,119,5,12,0,0,119,121,3,52,26,0,120,118,1,0,0,0,120,
        121,1,0,0,0,121,122,1,0,0,0,122,123,5,37,0,0,123,124,3,10,5,0,124,
        13,1,0,0,0,125,126,7,0,0,0,126,15,1,0,0,0,127,128,5,13,0,0,128,129,
        3,52,26,0,129,130,5,12,0,0,130,131,3,62,31,0,131,17,1,0,0,0,132,
        133,3,52,26,0,133,134,5,40,0,0,134,135,3,20,10,0,135,19,1,0,0,0,
        136,140,3,62,31,0,137,140,3,46,23,0,138,140,3,34,17,0,139,136,1,
        0,0,0,139,137,1,0,0,0,139,138,1,0,0,0,140,21,1,0,0,0,141,143,5,4,
        0,0,142,144,3,60,30,0,143,142,1,0,0,0,143,144,1,0,0,0,144,23,1,0,
        0,0,145,146,3,22,11,0,146,147,5,14,0,0,147,148,3,22,11,0,148,25,
        1,0,0,0,149,150,5,4,0,0,150,151,3,60,30,0,151,27,1,0,0,0,152,155,
        5,4,0,0,153,156,3,60,30,0,154,156,5,30,0,0,155,153,1,0,0,0,155,154,
        1,0,0,0,155,156,1,0,0,0,156,29,1,0,0,0,157,158,3,26,13,0,158,159,
        5,15,0,0,159,160,3,28,14,0,160,31,1,0,0,0,161,163,5,4,0,0,162,164,
        3,60,30,0,163,162,1,0,0,0,163,164,1,0,0,0,164,33,1,0,0,0,165,169,
        3,24,12,0,166,169,3,30,15,0,167,169,3,32,16,0,168,165,1,0,0,0,168,
        166,1,0,0,0,168,167,1,0,0,0,169,35,1,0,0,0,170,171,3,52,26,0,171,
        172,5,63,0,0,172,173,3,52,26,0,173,37,1,0,0,0,174,175,3,40,20,0,
        175,176,5,52,0,0,176,177,3,40,20,0,177,39,1,0,0,0,178,183,3,52,26,
        0,179,183,3,54,27,0,180,183,3,42,21,0,181,183,3,44,22,0,182,178,
        1,0,0,0,182,179,1,0,0,0,182,180,1,0,0,0,182,181,1,0,0,0,183,41,1,
        0,0,0,184,185,5,10,0,0,185,186,3,60,30,0,186,43,1,0,0,0,187,190,
        5,9,0,0,188,191,3,60,30,0,189,191,3,58,29,0,190,188,1,0,0,0,190,
        189,1,0,0,0,191,45,1,0,0,0,192,193,5,11,0,0,193,194,3,52,26,0,194,
        47,1,0,0,0,195,196,3,62,31,0,196,49,1,0,0,0,197,198,5,19,0,0,198,
        51,1,0,0,0,199,202,3,56,28,0,200,202,3,60,30,0,201,199,1,0,0,0,201,
        200,1,0,0,0,202,53,1,0,0,0,203,204,3,52,26,0,204,205,5,31,0,0,205,
        206,3,58,29,0,206,55,1,0,0,0,207,210,3,60,30,0,208,209,5,31,0,0,
        209,211,3,60,30,0,210,208,1,0,0,0,211,212,1,0,0,0,212,210,1,0,0,
        0,212,213,1,0,0,0,213,57,1,0,0,0,214,215,5,4,0,0,215,59,1,0,0,0,
        216,217,5,21,0,0,217,61,1,0,0,0,218,219,5,3,0,0,219,63,1,0,0,0,220,
        221,7,1,0,0,221,65,1,0,0,0,18,68,70,77,84,88,100,110,114,120,139,
        143,155,163,168,182,190,201,212
    ]

class AtopileParser ( AtopileParserBase ):

    grammarFileName = "AtopileParser.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "'component'", "'module'", 
                     "'interface'", "'pin'", "'signal'", "'new'", "'from'", 
                     "'import'", "'to'", "'+/-'", "'eqn'", "'True'", "'False'", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "'%'", "'.'", 
                     "'...'", "'*'", "'('", "')'", "','", "':'", "';'", 
                     "'**'", "'='", "'['", "']'", "'|'", "'^'", "'&'", "'<<'", 
                     "'>>'", "'+'", "'-'", "'/'", "'//'", "'~'", "'{'", 
                     "'}'", "'<'", "'>'", "'=='", "'>='", "'<='", "'<>'", 
                     "'!='", "'@'", "'->'", "'+='", "'-='", "'*='", "'@='", 
                     "'/='", "'&='", "'|='", "'^='", "'<<='", "'>>='", "'**='", 
                     "'//='" ]

    symbolicNames = [ "<INVALID>", "INDENT", "DEDENT", "STRING", "NUMBER", 
                      "INTEGER", "COMPONENT", "MODULE", "INTERFACE", "PIN", 
                      "SIGNAL", "NEW", "FROM", "IMPORT", "TO", "PLUS_OR_MINUS", 
                      "EQN", "TRUE", "FALSE", "EQUATION_STRING", "NEWLINE", 
                      "NAME", "STRING_LITERAL", "BYTES_LITERAL", "DECIMAL_INTEGER", 
                      "OCT_INTEGER", "HEX_INTEGER", "BIN_INTEGER", "FLOAT_NUMBER", 
                      "IMAG_NUMBER", "PERCENT", "DOT", "ELLIPSIS", "STAR", 
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
    RULE_block = 5
    RULE_blockdef = 6
    RULE_blocktype = 7
    RULE_import_stmt = 8
    RULE_assign_stmt = 9
    RULE_assignable = 10
    RULE_quantity_end = 11
    RULE_bound_quantity = 12
    RULE_bilateral_nominal = 13
    RULE_bilateral_tolerance = 14
    RULE_bilateral_quantity = 15
    RULE_implicit_quantity = 16
    RULE_physical = 17
    RULE_retype_stmt = 18
    RULE_connect_stmt = 19
    RULE_connectable = 20
    RULE_signaldef_stmt = 21
    RULE_pindef_stmt = 22
    RULE_new_stmt = 23
    RULE_string_stmt = 24
    RULE_eqn_stmt = 25
    RULE_name_or_attr = 26
    RULE_numerical_pin_ref = 27
    RULE_attr = 28
    RULE_totally_an_integer = 29
    RULE_name = 30
    RULE_string = 31
    RULE_boolean_ = 32

    ruleNames =  [ "file_input", "stmt", "simple_stmts", "simple_stmt", 
                   "compound_stmt", "block", "blockdef", "blocktype", "import_stmt", 
                   "assign_stmt", "assignable", "quantity_end", "bound_quantity", 
                   "bilateral_nominal", "bilateral_tolerance", "bilateral_quantity", 
                   "implicit_quantity", "physical", "retype_stmt", "connect_stmt", 
                   "connectable", "signaldef_stmt", "pindef_stmt", "new_stmt", 
                   "string_stmt", "eqn_stmt", "name_or_attr", "numerical_pin_ref", 
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
    TO=14
    PLUS_OR_MINUS=15
    EQN=16
    TRUE=17
    FALSE=18
    EQUATION_STRING=19
    NEWLINE=20
    NAME=21
    STRING_LITERAL=22
    BYTES_LITERAL=23
    DECIMAL_INTEGER=24
    OCT_INTEGER=25
    HEX_INTEGER=26
    BIN_INTEGER=27
    FLOAT_NUMBER=28
    IMAG_NUMBER=29
    PERCENT=30
    DOT=31
    ELLIPSIS=32
    STAR=33
    OPEN_PAREN=34
    CLOSE_PAREN=35
    COMMA=36
    COLON=37
    SEMI_COLON=38
    POWER=39
    ASSIGN=40
    OPEN_BRACK=41
    CLOSE_BRACK=42
    OR_OP=43
    XOR=44
    AND_OP=45
    LEFT_SHIFT=46
    RIGHT_SHIFT=47
    ADD=48
    MINUS=49
    DIV=50
    IDIV=51
    NOT_OP=52
    OPEN_BRACE=53
    CLOSE_BRACE=54
    LESS_THAN=55
    GREATER_THAN=56
    EQUALS=57
    GT_EQ=58
    LT_EQ=59
    NOT_EQ_1=60
    NOT_EQ_2=61
    AT=62
    ARROW=63
    ADD_ASSIGN=64
    SUB_ASSIGN=65
    MULT_ASSIGN=66
    AT_ASSIGN=67
    DIV_ASSIGN=68
    AND_ASSIGN=69
    OR_ASSIGN=70
    XOR_ASSIGN=71
    LEFT_SHIFT_ASSIGN=72
    RIGHT_SHIFT_ASSIGN=73
    POWER_ASSIGN=74
    IDIV_ASSIGN=75
    SKIP_=76
    UNKNOWN_CHAR=77

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
            self.state = 70
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 3680200) != 0):
                self.state = 68
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [20]:
                    self.state = 66
                    self.match(AtopileParser.NEWLINE)
                    pass
                elif token in [3, 6, 7, 8, 9, 10, 13, 19, 21]:
                    self.state = 67
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 72
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 73
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
            self.state = 77
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 13, 19, 21]:
                self.enterOuterAlt(localctx, 1)
                self.state = 75
                self.simple_stmts()
                pass
            elif token in [6, 7, 8]:
                self.enterOuterAlt(localctx, 2)
                self.state = 76
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
            self.state = 79
            self.simple_stmt()
            self.state = 84
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 80
                    self.match(AtopileParser.SEMI_COLON)
                    self.state = 81
                    self.simple_stmt() 
                self.state = 86
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 88
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==38:
                self.state = 87
                self.match(AtopileParser.SEMI_COLON)


            self.state = 90
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


        def eqn_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Eqn_stmtContext,0)


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
            self.state = 100
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 92
                self.import_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 93
                self.assign_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 94
                self.connect_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 95
                self.retype_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 96
                self.pindef_stmt()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 97
                self.signaldef_stmt()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 98
                self.string_stmt()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 99
                self.eqn_stmt()
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
            self.state = 102
            self.blockdef()
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
        self.enterRule(localctx, 10, self.RULE_block)
        self._la = 0 # Token type
        try:
            self.state = 114
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 13, 19, 21]:
                self.enterOuterAlt(localctx, 1)
                self.state = 104
                self.simple_stmts()
                pass
            elif token in [20]:
                self.enterOuterAlt(localctx, 2)
                self.state = 105
                self.match(AtopileParser.NEWLINE)
                self.state = 106
                self.match(AtopileParser.INDENT)
                self.state = 108 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 107
                    self.stmt()
                    self.state = 110 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 2631624) != 0)):
                        break

                self.state = 112
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
        self.enterRule(localctx, 12, self.RULE_blockdef)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 116
            self.blocktype()
            self.state = 117
            self.name()
            self.state = 120
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 118
                self.match(AtopileParser.FROM)
                self.state = 119
                self.name_or_attr()


            self.state = 122
            self.match(AtopileParser.COLON)
            self.state = 123
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
        self.enterRule(localctx, 14, self.RULE_blocktype)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 125
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


    class Import_stmtContext(ParserRuleContext):
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
            return AtopileParser.RULE_import_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitImport_stmt" ):
                return visitor.visitImport_stmt(self)
            else:
                return visitor.visitChildren(self)




    def import_stmt(self):

        localctx = AtopileParser.Import_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_import_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 127
            self.match(AtopileParser.IMPORT)
            self.state = 128
            self.name_or_attr()
            self.state = 129
            self.match(AtopileParser.FROM)
            self.state = 130
            self.string()
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


        def getRuleIndex(self):
            return AtopileParser.RULE_assign_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssign_stmt" ):
                return visitor.visitAssign_stmt(self)
            else:
                return visitor.visitChildren(self)




    def assign_stmt(self):

        localctx = AtopileParser.Assign_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_assign_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 132
            self.name_or_attr()
            self.state = 133
            self.match(AtopileParser.ASSIGN)
            self.state = 134
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


        def physical(self):
            return self.getTypedRuleContext(AtopileParser.PhysicalContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_assignable

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssignable" ):
                return visitor.visitAssignable(self)
            else:
                return visitor.visitChildren(self)




    def assignable(self):

        localctx = AtopileParser.AssignableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_assignable)
        try:
            self.state = 139
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3]:
                self.enterOuterAlt(localctx, 1)
                self.state = 136
                self.string()
                pass
            elif token in [11]:
                self.enterOuterAlt(localctx, 2)
                self.state = 137
                self.new_stmt()
                pass
            elif token in [4]:
                self.enterOuterAlt(localctx, 3)
                self.state = 138
                self.physical()
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
        self.enterRule(localctx, 22, self.RULE_quantity_end)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 141
            self.match(AtopileParser.NUMBER)
            self.state = 143
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==21:
                self.state = 142
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
        self.enterRule(localctx, 24, self.RULE_bound_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 145
            self.quantity_end()
            self.state = 146
            self.match(AtopileParser.TO)
            self.state = 147
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
        self.enterRule(localctx, 26, self.RULE_bilateral_nominal)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 149
            self.match(AtopileParser.NUMBER)
            self.state = 150
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

        def name(self):
            return self.getTypedRuleContext(AtopileParser.NameContext,0)


        def PERCENT(self):
            return self.getToken(AtopileParser.PERCENT, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_bilateral_tolerance

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBilateral_tolerance" ):
                return visitor.visitBilateral_tolerance(self)
            else:
                return visitor.visitChildren(self)




    def bilateral_tolerance(self):

        localctx = AtopileParser.Bilateral_toleranceContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_bilateral_tolerance)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 152
            self.match(AtopileParser.NUMBER)
            self.state = 155
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [21]:
                self.state = 153
                self.name()
                pass
            elif token in [30]:
                self.state = 154
                self.match(AtopileParser.PERCENT)
                pass
            elif token in [20, 38]:
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
        self.enterRule(localctx, 30, self.RULE_bilateral_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 157
            self.bilateral_nominal()
            self.state = 158
            self.match(AtopileParser.PLUS_OR_MINUS)
            self.state = 159
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
        self.enterRule(localctx, 32, self.RULE_implicit_quantity)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 161
            self.match(AtopileParser.NUMBER)
            self.state = 163
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==21:
                self.state = 162
                self.name()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PhysicalContext(ParserRuleContext):
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
            return AtopileParser.RULE_physical

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPhysical" ):
                return visitor.visitPhysical(self)
            else:
                return visitor.visitChildren(self)




    def physical(self):

        localctx = AtopileParser.PhysicalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_physical)
        try:
            self.state = 168
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 165
                self.bound_quantity()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 166
                self.bilateral_quantity()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 167
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
        self.enterRule(localctx, 36, self.RULE_retype_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 170
            self.name_or_attr()
            self.state = 171
            self.match(AtopileParser.ARROW)
            self.state = 172
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
        self.enterRule(localctx, 38, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 174
            self.connectable()
            self.state = 175
            self.match(AtopileParser.NOT_OP)
            self.state = 176
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
        self.enterRule(localctx, 40, self.RULE_connectable)
        try:
            self.state = 182
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 178
                self.name_or_attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 179
                self.numerical_pin_ref()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 180
                self.signaldef_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 181
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
        self.enterRule(localctx, 42, self.RULE_signaldef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 184
            self.match(AtopileParser.SIGNAL)
            self.state = 185
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
        self.enterRule(localctx, 44, self.RULE_pindef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 187
            self.match(AtopileParser.PIN)
            self.state = 190
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [21]:
                self.state = 188
                self.name()
                pass
            elif token in [4]:
                self.state = 189
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
        self.enterRule(localctx, 46, self.RULE_new_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 192
            self.match(AtopileParser.NEW)
            self.state = 193
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
        self.enterRule(localctx, 48, self.RULE_string_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 195
            self.string()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Eqn_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EQUATION_STRING(self):
            return self.getToken(AtopileParser.EQUATION_STRING, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_eqn_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEqn_stmt" ):
                return visitor.visitEqn_stmt(self)
            else:
                return visitor.visitChildren(self)




    def eqn_stmt(self):

        localctx = AtopileParser.Eqn_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_eqn_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 197
            self.match(AtopileParser.EQUATION_STRING)
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
        self.enterRule(localctx, 52, self.RULE_name_or_attr)
        try:
            self.state = 201
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,16,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 199
                self.attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 200
                self.name()
                pass


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
        self.enterRule(localctx, 54, self.RULE_numerical_pin_ref)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 203
            self.name_or_attr()
            self.state = 204
            self.match(AtopileParser.DOT)
            self.state = 205
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
        self.enterRule(localctx, 56, self.RULE_attr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 207
            self.name()
            self.state = 210 
            self._errHandler.sync(self)
            _alt = 1
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    self.state = 208
                    self.match(AtopileParser.DOT)
                    self.state = 209
                    self.name()

                else:
                    raise NoViableAltException(self)
                self.state = 212 
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,17,self._ctx)

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
        self.enterRule(localctx, 58, self.RULE_totally_an_integer)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 214
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
        self.enterRule(localctx, 60, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 216
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
        self.enterRule(localctx, 62, self.RULE_string)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 218
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
        self.enterRule(localctx, 64, self.RULE_boolean_)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 220
            _la = self._input.LA(1)
            if not(_la==17 or _la==18):
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





