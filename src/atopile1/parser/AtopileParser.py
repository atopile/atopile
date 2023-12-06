# Generated from AtopileParser.g4 by ANTLR 4.13.0
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
        4,1,77,181,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,1,0,1,0,5,0,53,8,0,
        10,0,12,0,56,9,0,1,0,1,0,1,1,1,1,3,1,62,8,1,1,2,1,2,1,2,5,2,67,8,
        2,10,2,12,2,70,9,2,1,2,3,2,73,8,2,1,2,1,2,1,3,1,3,1,3,1,3,1,3,1,
        3,1,3,3,3,84,8,3,1,4,1,4,1,5,1,5,1,5,1,5,4,5,92,8,5,11,5,12,5,93,
        1,5,1,5,3,5,98,8,5,1,6,1,6,1,6,1,6,3,6,104,8,6,1,6,1,6,1,6,1,7,1,
        7,1,8,1,8,1,8,1,8,1,8,1,9,1,9,1,9,1,9,1,10,1,10,1,10,1,10,1,10,3,
        10,125,8,10,1,11,1,11,1,11,1,11,1,12,1,12,1,12,1,12,1,13,1,13,1,
        13,1,13,3,13,139,8,13,1,14,3,14,142,8,14,1,14,1,14,1,14,1,15,1,15,
        1,15,3,15,150,8,15,1,16,1,16,1,16,1,17,1,17,1,17,1,18,1,18,3,18,
        160,8,18,1,19,1,19,1,19,1,19,1,20,1,20,1,20,4,20,169,8,20,11,20,
        12,20,170,1,21,1,21,1,22,1,22,1,23,1,23,1,24,1,24,1,24,0,0,25,0,
        2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,
        48,0,2,1,0,6,8,1,0,17,18,180,0,54,1,0,0,0,2,61,1,0,0,0,4,63,1,0,
        0,0,6,83,1,0,0,0,8,85,1,0,0,0,10,97,1,0,0,0,12,99,1,0,0,0,14,108,
        1,0,0,0,16,110,1,0,0,0,18,115,1,0,0,0,20,124,1,0,0,0,22,126,1,0,
        0,0,24,130,1,0,0,0,26,138,1,0,0,0,28,141,1,0,0,0,30,146,1,0,0,0,
        32,151,1,0,0,0,34,154,1,0,0,0,36,159,1,0,0,0,38,161,1,0,0,0,40,165,
        1,0,0,0,42,172,1,0,0,0,44,174,1,0,0,0,46,176,1,0,0,0,48,178,1,0,
        0,0,50,53,5,19,0,0,51,53,3,2,1,0,52,50,1,0,0,0,52,51,1,0,0,0,53,
        56,1,0,0,0,54,52,1,0,0,0,54,55,1,0,0,0,55,57,1,0,0,0,56,54,1,0,0,
        0,57,58,5,0,0,1,58,1,1,0,0,0,59,62,3,4,2,0,60,62,3,8,4,0,61,59,1,
        0,0,0,61,60,1,0,0,0,62,3,1,0,0,0,63,68,3,6,3,0,64,65,5,36,0,0,65,
        67,3,6,3,0,66,64,1,0,0,0,67,70,1,0,0,0,68,66,1,0,0,0,68,69,1,0,0,
        0,69,72,1,0,0,0,70,68,1,0,0,0,71,73,5,36,0,0,72,71,1,0,0,0,72,73,
        1,0,0,0,73,74,1,0,0,0,74,75,5,19,0,0,75,5,1,0,0,0,76,84,3,16,8,0,
        77,84,3,18,9,0,78,84,3,24,12,0,79,84,3,22,11,0,80,84,3,30,15,0,81,
        84,3,28,14,0,82,84,3,32,16,0,83,76,1,0,0,0,83,77,1,0,0,0,83,78,1,
        0,0,0,83,79,1,0,0,0,83,80,1,0,0,0,83,81,1,0,0,0,83,82,1,0,0,0,84,
        7,1,0,0,0,85,86,3,12,6,0,86,9,1,0,0,0,87,98,3,4,2,0,88,89,5,19,0,
        0,89,91,5,1,0,0,90,92,3,2,1,0,91,90,1,0,0,0,92,93,1,0,0,0,93,91,
        1,0,0,0,93,94,1,0,0,0,94,95,1,0,0,0,95,96,5,2,0,0,96,98,1,0,0,0,
        97,87,1,0,0,0,97,88,1,0,0,0,98,11,1,0,0,0,99,100,3,14,7,0,100,103,
        3,44,22,0,101,102,5,14,0,0,102,104,3,36,18,0,103,101,1,0,0,0,103,
        104,1,0,0,0,104,105,1,0,0,0,105,106,5,35,0,0,106,107,3,10,5,0,107,
        13,1,0,0,0,108,109,7,0,0,0,109,15,1,0,0,0,110,111,5,15,0,0,111,112,
        3,36,18,0,112,113,5,14,0,0,113,114,3,46,23,0,114,17,1,0,0,0,115,
        116,3,36,18,0,116,117,5,38,0,0,117,118,3,20,10,0,118,19,1,0,0,0,
        119,125,3,46,23,0,120,125,5,4,0,0,121,125,3,36,18,0,122,125,3,34,
        17,0,123,125,3,48,24,0,124,119,1,0,0,0,124,120,1,0,0,0,124,121,1,
        0,0,0,124,122,1,0,0,0,124,123,1,0,0,0,125,21,1,0,0,0,126,127,3,36,
        18,0,127,128,5,62,0,0,128,129,3,36,18,0,129,23,1,0,0,0,130,131,3,
        26,13,0,131,132,5,51,0,0,132,133,3,26,13,0,133,25,1,0,0,0,134,139,
        3,36,18,0,135,139,3,38,19,0,136,139,3,28,14,0,137,139,3,30,15,0,
        138,134,1,0,0,0,138,135,1,0,0,0,138,136,1,0,0,0,138,137,1,0,0,0,
        139,27,1,0,0,0,140,142,5,16,0,0,141,140,1,0,0,0,141,142,1,0,0,0,
        142,143,1,0,0,0,143,144,5,10,0,0,144,145,3,44,22,0,145,29,1,0,0,
        0,146,149,5,9,0,0,147,150,3,44,22,0,148,150,3,42,21,0,149,147,1,
        0,0,0,149,148,1,0,0,0,150,31,1,0,0,0,151,152,5,11,0,0,152,153,3,
        36,18,0,153,33,1,0,0,0,154,155,5,13,0,0,155,156,3,36,18,0,156,35,
        1,0,0,0,157,160,3,40,20,0,158,160,3,44,22,0,159,157,1,0,0,0,159,
        158,1,0,0,0,160,37,1,0,0,0,161,162,3,36,18,0,162,163,5,29,0,0,163,
        164,3,42,21,0,164,39,1,0,0,0,165,168,3,44,22,0,166,167,5,29,0,0,
        167,169,3,44,22,0,168,166,1,0,0,0,169,170,1,0,0,0,170,168,1,0,0,
        0,170,171,1,0,0,0,171,41,1,0,0,0,172,173,5,4,0,0,173,43,1,0,0,0,
        174,175,5,20,0,0,175,45,1,0,0,0,176,177,5,3,0,0,177,47,1,0,0,0,178,
        179,7,1,0,0,179,49,1,0,0,0,15,52,54,61,68,72,83,93,97,103,124,138,
        141,149,159,170
    ]

class AtopileParser ( AtopileParserBase ):

    grammarFileName = "AtopileParser.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "'component'", "'module'", 
                     "'interface'", "'pin'", "'signal'", "'with'", "'optional'", 
                     "'new'", "'from'", "'import'", "'private'", "'True'", 
                     "'False'", "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "'.'", "'...'", "'*'", "'('", 
                     "')'", "','", "':'", "';'", "'**'", "'='", "'['", "']'", 
                     "'|'", "'^'", "'&'", "'<<'", "'>>'", "'+'", "'-'", 
                     "'/'", "'%'", "'//'", "'~'", "'{'", "'}'", "'<'", "'>'", 
                     "'=='", "'>='", "'<='", "'<>'", "'!='", "'@'", "'->'", 
                     "'+='", "'-='", "'*='", "'@='", "'/='", "'%='", "'&='", 
                     "'|='", "'^='", "'<<='", "'>>='", "'**='", "'//='" ]

    symbolicNames = [ "<INVALID>", "INDENT", "DEDENT", "STRING", "NUMBER", 
                      "INTEGER", "COMPONENT", "MODULE", "INTERFACE", "PIN", 
                      "SIGNAL", "WITH", "OPTIONAL", "NEW", "FROM", "IMPORT", 
                      "PRIVATE", "TRUE", "FALSE", "NEWLINE", "NAME", "STRING_LITERAL", 
                      "BYTES_LITERAL", "DECIMAL_INTEGER", "OCT_INTEGER", 
                      "HEX_INTEGER", "BIN_INTEGER", "FLOAT_NUMBER", "IMAG_NUMBER", 
                      "DOT", "ELLIPSIS", "STAR", "OPEN_PAREN", "CLOSE_PAREN", 
                      "COMMA", "COLON", "SEMI_COLON", "POWER", "ASSIGN", 
                      "OPEN_BRACK", "CLOSE_BRACK", "OR_OP", "XOR", "AND_OP", 
                      "LEFT_SHIFT", "RIGHT_SHIFT", "ADD", "MINUS", "DIV", 
                      "MOD", "IDIV", "NOT_OP", "OPEN_BRACE", "CLOSE_BRACE", 
                      "LESS_THAN", "GREATER_THAN", "EQUALS", "GT_EQ", "LT_EQ", 
                      "NOT_EQ_1", "NOT_EQ_2", "AT", "ARROW", "ADD_ASSIGN", 
                      "SUB_ASSIGN", "MULT_ASSIGN", "AT_ASSIGN", "DIV_ASSIGN", 
                      "MOD_ASSIGN", "AND_ASSIGN", "OR_ASSIGN", "XOR_ASSIGN", 
                      "LEFT_SHIFT_ASSIGN", "RIGHT_SHIFT_ASSIGN", "POWER_ASSIGN", 
                      "IDIV_ASSIGN", "SKIP_", "UNKNOWN_CHAR" ]

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
    RULE_retype_stmt = 11
    RULE_connect_stmt = 12
    RULE_connectable = 13
    RULE_signaldef_stmt = 14
    RULE_pindef_stmt = 15
    RULE_with_stmt = 16
    RULE_new_stmt = 17
    RULE_name_or_attr = 18
    RULE_numerical_pin_ref = 19
    RULE_attr = 20
    RULE_totally_an_integer = 21
    RULE_name = 22
    RULE_string = 23
    RULE_boolean_ = 24

    ruleNames =  [ "file_input", "stmt", "simple_stmts", "simple_stmt", 
                   "compound_stmt", "block", "blockdef", "blocktype", "import_stmt", 
                   "assign_stmt", "assignable", "retype_stmt", "connect_stmt", 
                   "connectable", "signaldef_stmt", "pindef_stmt", "with_stmt", 
                   "new_stmt", "name_or_attr", "numerical_pin_ref", "attr", 
                   "totally_an_integer", "name", "string", "boolean_" ]

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
    WITH=11
    OPTIONAL=12
    NEW=13
    FROM=14
    IMPORT=15
    PRIVATE=16
    TRUE=17
    FALSE=18
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
    DOT=29
    ELLIPSIS=30
    STAR=31
    OPEN_PAREN=32
    CLOSE_PAREN=33
    COMMA=34
    COLON=35
    SEMI_COLON=36
    POWER=37
    ASSIGN=38
    OPEN_BRACK=39
    CLOSE_BRACK=40
    OR_OP=41
    XOR=42
    AND_OP=43
    LEFT_SHIFT=44
    RIGHT_SHIFT=45
    ADD=46
    MINUS=47
    DIV=48
    MOD=49
    IDIV=50
    NOT_OP=51
    OPEN_BRACE=52
    CLOSE_BRACE=53
    LESS_THAN=54
    GREATER_THAN=55
    EQUALS=56
    GT_EQ=57
    LT_EQ=58
    NOT_EQ_1=59
    NOT_EQ_2=60
    AT=61
    ARROW=62
    ADD_ASSIGN=63
    SUB_ASSIGN=64
    MULT_ASSIGN=65
    AT_ASSIGN=66
    DIV_ASSIGN=67
    MOD_ASSIGN=68
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
        self.checkVersion("4.13.0")
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterFile_input" ):
                listener.enterFile_input(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitFile_input" ):
                listener.exitFile_input(self)

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
            self.state = 54
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 1675200) != 0):
                self.state = 52
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [19]:
                    self.state = 50
                    self.match(AtopileParser.NEWLINE)
                    pass
                elif token in [6, 7, 8, 9, 10, 11, 15, 16, 20]:
                    self.state = 51
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 56
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 57
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterStmt" ):
                listener.enterStmt(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitStmt" ):
                listener.exitStmt(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStmt" ):
                return visitor.visitStmt(self)
            else:
                return visitor.visitChildren(self)




    def stmt(self):

        localctx = AtopileParser.StmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_stmt)
        try:
            self.state = 61
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [9, 10, 11, 15, 16, 20]:
                self.enterOuterAlt(localctx, 1)
                self.state = 59
                self.simple_stmts()
                pass
            elif token in [6, 7, 8]:
                self.enterOuterAlt(localctx, 2)
                self.state = 60
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSimple_stmts" ):
                listener.enterSimple_stmts(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSimple_stmts" ):
                listener.exitSimple_stmts(self)

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
            self.state = 63
            self.simple_stmt()
            self.state = 68
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 64
                    self.match(AtopileParser.SEMI_COLON)
                    self.state = 65
                    self.simple_stmt() 
                self.state = 70
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 72
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==36:
                self.state = 71
                self.match(AtopileParser.SEMI_COLON)


            self.state = 74
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


        def with_stmt(self):
            return self.getTypedRuleContext(AtopileParser.With_stmtContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_simple_stmt

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSimple_stmt" ):
                listener.enterSimple_stmt(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSimple_stmt" ):
                listener.exitSimple_stmt(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSimple_stmt" ):
                return visitor.visitSimple_stmt(self)
            else:
                return visitor.visitChildren(self)




    def simple_stmt(self):

        localctx = AtopileParser.Simple_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_simple_stmt)
        try:
            self.state = 83
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 76
                self.import_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 77
                self.assign_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 78
                self.connect_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 79
                self.retype_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 80
                self.pindef_stmt()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 81
                self.signaldef_stmt()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 82
                self.with_stmt()
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCompound_stmt" ):
                listener.enterCompound_stmt(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCompound_stmt" ):
                listener.exitCompound_stmt(self)

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
            self.state = 85
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBlock" ):
                listener.enterBlock(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBlock" ):
                listener.exitBlock(self)

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
            self.state = 97
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [9, 10, 11, 15, 16, 20]:
                self.enterOuterAlt(localctx, 1)
                self.state = 87
                self.simple_stmts()
                pass
            elif token in [19]:
                self.enterOuterAlt(localctx, 2)
                self.state = 88
                self.match(AtopileParser.NEWLINE)
                self.state = 89
                self.match(AtopileParser.INDENT)
                self.state = 91 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 90
                    self.stmt()
                    self.state = 93 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 1150912) != 0)):
                        break

                self.state = 95
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBlockdef" ):
                listener.enterBlockdef(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBlockdef" ):
                listener.exitBlockdef(self)

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
            self.state = 99
            self.blocktype()
            self.state = 100
            self.name()
            self.state = 103
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==14:
                self.state = 101
                self.match(AtopileParser.FROM)
                self.state = 102
                self.name_or_attr()


            self.state = 105
            self.match(AtopileParser.COLON)
            self.state = 106
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBlocktype" ):
                listener.enterBlocktype(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBlocktype" ):
                listener.exitBlocktype(self)

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
            self.state = 108
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterImport_stmt" ):
                listener.enterImport_stmt(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitImport_stmt" ):
                listener.exitImport_stmt(self)

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
            self.state = 110
            self.match(AtopileParser.IMPORT)
            self.state = 111
            self.name_or_attr()
            self.state = 112
            self.match(AtopileParser.FROM)
            self.state = 113
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterAssign_stmt" ):
                listener.enterAssign_stmt(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitAssign_stmt" ):
                listener.exitAssign_stmt(self)

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
            self.state = 115
            self.name_or_attr()
            self.state = 116
            self.match(AtopileParser.ASSIGN)
            self.state = 117
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


        def NUMBER(self):
            return self.getToken(AtopileParser.NUMBER, 0)

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def new_stmt(self):
            return self.getTypedRuleContext(AtopileParser.New_stmtContext,0)


        def boolean_(self):
            return self.getTypedRuleContext(AtopileParser.Boolean_Context,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_assignable

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterAssignable" ):
                listener.enterAssignable(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitAssignable" ):
                listener.exitAssignable(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssignable" ):
                return visitor.visitAssignable(self)
            else:
                return visitor.visitChildren(self)




    def assignable(self):

        localctx = AtopileParser.AssignableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_assignable)
        try:
            self.state = 124
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3]:
                self.enterOuterAlt(localctx, 1)
                self.state = 119
                self.string()
                pass
            elif token in [4]:
                self.enterOuterAlt(localctx, 2)
                self.state = 120
                self.match(AtopileParser.NUMBER)
                pass
            elif token in [20]:
                self.enterOuterAlt(localctx, 3)
                self.state = 121
                self.name_or_attr()
                pass
            elif token in [13]:
                self.enterOuterAlt(localctx, 4)
                self.state = 122
                self.new_stmt()
                pass
            elif token in [17, 18]:
                self.enterOuterAlt(localctx, 5)
                self.state = 123
                self.boolean_()
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterRetype_stmt" ):
                listener.enterRetype_stmt(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitRetype_stmt" ):
                listener.exitRetype_stmt(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRetype_stmt" ):
                return visitor.visitRetype_stmt(self)
            else:
                return visitor.visitChildren(self)




    def retype_stmt(self):

        localctx = AtopileParser.Retype_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_retype_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 126
            self.name_or_attr()
            self.state = 127
            self.match(AtopileParser.ARROW)
            self.state = 128
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterConnect_stmt" ):
                listener.enterConnect_stmt(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitConnect_stmt" ):
                listener.exitConnect_stmt(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConnect_stmt" ):
                return visitor.visitConnect_stmt(self)
            else:
                return visitor.visitChildren(self)




    def connect_stmt(self):

        localctx = AtopileParser.Connect_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 130
            self.connectable()
            self.state = 131
            self.match(AtopileParser.NOT_OP)
            self.state = 132
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterConnectable" ):
                listener.enterConnectable(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitConnectable" ):
                listener.exitConnectable(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConnectable" ):
                return visitor.visitConnectable(self)
            else:
                return visitor.visitChildren(self)




    def connectable(self):

        localctx = AtopileParser.ConnectableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_connectable)
        try:
            self.state = 138
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,10,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 134
                self.name_or_attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 135
                self.numerical_pin_ref()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 136
                self.signaldef_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 137
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


        def PRIVATE(self):
            return self.getToken(AtopileParser.PRIVATE, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_signaldef_stmt

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSignaldef_stmt" ):
                listener.enterSignaldef_stmt(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSignaldef_stmt" ):
                listener.exitSignaldef_stmt(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSignaldef_stmt" ):
                return visitor.visitSignaldef_stmt(self)
            else:
                return visitor.visitChildren(self)




    def signaldef_stmt(self):

        localctx = AtopileParser.Signaldef_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_signaldef_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 141
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==16:
                self.state = 140
                self.match(AtopileParser.PRIVATE)


            self.state = 143
            self.match(AtopileParser.SIGNAL)
            self.state = 144
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPindef_stmt" ):
                listener.enterPindef_stmt(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPindef_stmt" ):
                listener.exitPindef_stmt(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPindef_stmt" ):
                return visitor.visitPindef_stmt(self)
            else:
                return visitor.visitChildren(self)




    def pindef_stmt(self):

        localctx = AtopileParser.Pindef_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_pindef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 146
            self.match(AtopileParser.PIN)
            self.state = 149
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [20]:
                self.state = 147
                self.name()
                pass
            elif token in [4]:
                self.state = 148
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


    class With_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def WITH(self):
            return self.getToken(AtopileParser.WITH, 0)

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_with_stmt

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterWith_stmt" ):
                listener.enterWith_stmt(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitWith_stmt" ):
                listener.exitWith_stmt(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitWith_stmt" ):
                return visitor.visitWith_stmt(self)
            else:
                return visitor.visitChildren(self)




    def with_stmt(self):

        localctx = AtopileParser.With_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_with_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 151
            self.match(AtopileParser.WITH)
            self.state = 152
            self.name_or_attr()
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterNew_stmt" ):
                listener.enterNew_stmt(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitNew_stmt" ):
                listener.exitNew_stmt(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNew_stmt" ):
                return visitor.visitNew_stmt(self)
            else:
                return visitor.visitChildren(self)




    def new_stmt(self):

        localctx = AtopileParser.New_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_new_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 154
            self.match(AtopileParser.NEW)
            self.state = 155
            self.name_or_attr()
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterName_or_attr" ):
                listener.enterName_or_attr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitName_or_attr" ):
                listener.exitName_or_attr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitName_or_attr" ):
                return visitor.visitName_or_attr(self)
            else:
                return visitor.visitChildren(self)




    def name_or_attr(self):

        localctx = AtopileParser.Name_or_attrContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_name_or_attr)
        try:
            self.state = 159
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 157
                self.attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 158
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterNumerical_pin_ref" ):
                listener.enterNumerical_pin_ref(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitNumerical_pin_ref" ):
                listener.exitNumerical_pin_ref(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNumerical_pin_ref" ):
                return visitor.visitNumerical_pin_ref(self)
            else:
                return visitor.visitChildren(self)




    def numerical_pin_ref(self):

        localctx = AtopileParser.Numerical_pin_refContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_numerical_pin_ref)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 161
            self.name_or_attr()
            self.state = 162
            self.match(AtopileParser.DOT)
            self.state = 163
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterAttr" ):
                listener.enterAttr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitAttr" ):
                listener.exitAttr(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAttr" ):
                return visitor.visitAttr(self)
            else:
                return visitor.visitChildren(self)




    def attr(self):

        localctx = AtopileParser.AttrContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_attr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 165
            self.name()
            self.state = 168 
            self._errHandler.sync(self)
            _alt = 1
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    self.state = 166
                    self.match(AtopileParser.DOT)
                    self.state = 167
                    self.name()

                else:
                    raise NoViableAltException(self)
                self.state = 170 
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,14,self._ctx)

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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTotally_an_integer" ):
                listener.enterTotally_an_integer(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTotally_an_integer" ):
                listener.exitTotally_an_integer(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTotally_an_integer" ):
                return visitor.visitTotally_an_integer(self)
            else:
                return visitor.visitChildren(self)




    def totally_an_integer(self):

        localctx = AtopileParser.Totally_an_integerContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_totally_an_integer)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 172
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterName" ):
                listener.enterName(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitName" ):
                listener.exitName(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitName" ):
                return visitor.visitName(self)
            else:
                return visitor.visitChildren(self)




    def name(self):

        localctx = AtopileParser.NameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 174
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterString" ):
                listener.enterString(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitString" ):
                listener.exitString(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitString" ):
                return visitor.visitString(self)
            else:
                return visitor.visitChildren(self)




    def string(self):

        localctx = AtopileParser.StringContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_string)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 176
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

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBoolean_" ):
                listener.enterBoolean_(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBoolean_" ):
                listener.exitBoolean_(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBoolean_" ):
                return visitor.visitBoolean_(self)
            else:
                return visitor.visitChildren(self)




    def boolean_(self):

        localctx = AtopileParser.Boolean_Context(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_boolean_)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 178
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





