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
        4,1,76,168,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,1,0,1,0,5,0,47,8,0,10,0,12,0,50,9,0,1,0,1,0,1,1,1,
        1,3,1,56,8,1,1,2,1,2,1,2,5,2,61,8,2,10,2,12,2,64,9,2,1,2,3,2,67,
        8,2,1,2,1,2,1,3,1,3,1,3,1,3,1,3,1,3,3,3,77,8,3,1,4,1,4,3,4,81,8,
        4,1,5,1,5,1,5,1,5,4,5,87,8,5,11,5,12,5,88,1,5,1,5,3,5,93,8,5,1,6,
        3,6,96,8,6,1,6,1,6,1,6,1,6,1,6,1,7,3,7,104,8,7,1,7,1,7,1,7,1,7,1,
        7,1,8,1,8,1,8,1,8,1,8,1,9,1,9,1,9,1,9,1,10,1,10,1,10,1,10,1,10,3,
        10,125,8,10,1,11,1,11,1,11,1,11,1,12,1,12,1,12,3,12,134,8,12,1,13,
        3,13,137,8,13,1,13,1,13,1,13,1,14,1,14,1,14,1,15,1,15,1,15,1,16,
        1,16,1,16,1,17,1,17,3,17,153,8,17,1,18,1,18,1,18,4,18,158,8,18,11,
        18,12,18,159,1,19,1,19,1,20,1,20,1,21,1,21,1,21,0,0,22,0,2,4,6,8,
        10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,0,1,1,0,16,17,
        169,0,48,1,0,0,0,2,55,1,0,0,0,4,57,1,0,0,0,6,76,1,0,0,0,8,80,1,0,
        0,0,10,92,1,0,0,0,12,95,1,0,0,0,14,103,1,0,0,0,16,110,1,0,0,0,18,
        115,1,0,0,0,20,124,1,0,0,0,22,126,1,0,0,0,24,133,1,0,0,0,26,136,
        1,0,0,0,28,141,1,0,0,0,30,144,1,0,0,0,32,147,1,0,0,0,34,152,1,0,
        0,0,36,154,1,0,0,0,38,161,1,0,0,0,40,163,1,0,0,0,42,165,1,0,0,0,
        44,47,5,18,0,0,45,47,3,2,1,0,46,44,1,0,0,0,46,45,1,0,0,0,47,50,1,
        0,0,0,48,46,1,0,0,0,48,49,1,0,0,0,49,51,1,0,0,0,50,48,1,0,0,0,51,
        52,5,0,0,1,52,1,1,0,0,0,53,56,3,4,2,0,54,56,3,8,4,0,55,53,1,0,0,
        0,55,54,1,0,0,0,56,3,1,0,0,0,57,62,3,6,3,0,58,59,5,35,0,0,59,61,
        3,6,3,0,60,58,1,0,0,0,61,64,1,0,0,0,62,60,1,0,0,0,62,63,1,0,0,0,
        63,66,1,0,0,0,64,62,1,0,0,0,65,67,5,35,0,0,66,65,1,0,0,0,66,67,1,
        0,0,0,67,68,1,0,0,0,68,69,5,18,0,0,69,5,1,0,0,0,70,77,3,16,8,0,71,
        77,3,18,9,0,72,77,3,22,11,0,73,77,3,28,14,0,74,77,3,26,13,0,75,77,
        3,30,15,0,76,70,1,0,0,0,76,71,1,0,0,0,76,72,1,0,0,0,76,73,1,0,0,
        0,76,74,1,0,0,0,76,75,1,0,0,0,77,7,1,0,0,0,78,81,3,12,6,0,79,81,
        3,14,7,0,80,78,1,0,0,0,80,79,1,0,0,0,81,9,1,0,0,0,82,93,3,4,2,0,
        83,84,5,18,0,0,84,86,5,1,0,0,85,87,3,2,1,0,86,85,1,0,0,0,87,88,1,
        0,0,0,88,86,1,0,0,0,88,89,1,0,0,0,89,90,1,0,0,0,90,91,5,2,0,0,91,
        93,1,0,0,0,92,82,1,0,0,0,92,83,1,0,0,0,93,11,1,0,0,0,94,96,5,11,
        0,0,95,94,1,0,0,0,95,96,1,0,0,0,96,97,1,0,0,0,97,98,5,6,0,0,98,99,
        3,38,19,0,99,100,5,34,0,0,100,101,3,10,5,0,101,13,1,0,0,0,102,104,
        5,11,0,0,103,102,1,0,0,0,103,104,1,0,0,0,104,105,1,0,0,0,105,106,
        5,7,0,0,106,107,3,38,19,0,107,108,5,34,0,0,108,109,3,10,5,0,109,
        15,1,0,0,0,110,111,5,14,0,0,111,112,3,34,17,0,112,113,5,13,0,0,113,
        114,3,40,20,0,114,17,1,0,0,0,115,116,3,34,17,0,116,117,5,37,0,0,
        117,118,3,20,10,0,118,19,1,0,0,0,119,125,3,40,20,0,120,125,5,4,0,
        0,121,125,3,34,17,0,122,125,3,32,16,0,123,125,3,42,21,0,124,119,
        1,0,0,0,124,120,1,0,0,0,124,121,1,0,0,0,124,122,1,0,0,0,124,123,
        1,0,0,0,125,21,1,0,0,0,126,127,3,24,12,0,127,128,5,50,0,0,128,129,
        3,24,12,0,129,23,1,0,0,0,130,134,3,34,17,0,131,134,3,26,13,0,132,
        134,3,28,14,0,133,130,1,0,0,0,133,131,1,0,0,0,133,132,1,0,0,0,134,
        25,1,0,0,0,135,137,5,15,0,0,136,135,1,0,0,0,136,137,1,0,0,0,137,
        138,1,0,0,0,138,139,5,9,0,0,139,140,3,38,19,0,140,27,1,0,0,0,141,
        142,5,8,0,0,142,143,3,38,19,0,143,29,1,0,0,0,144,145,5,10,0,0,145,
        146,3,34,17,0,146,31,1,0,0,0,147,148,5,12,0,0,148,149,3,34,17,0,
        149,33,1,0,0,0,150,153,3,36,18,0,151,153,3,38,19,0,152,150,1,0,0,
        0,152,151,1,0,0,0,153,35,1,0,0,0,154,157,3,38,19,0,155,156,5,28,
        0,0,156,158,3,38,19,0,157,155,1,0,0,0,158,159,1,0,0,0,159,157,1,
        0,0,0,159,160,1,0,0,0,160,37,1,0,0,0,161,162,5,19,0,0,162,39,1,0,
        0,0,163,164,5,3,0,0,164,41,1,0,0,0,165,166,7,0,0,0,166,43,1,0,0,
        0,16,46,48,55,62,66,76,80,88,92,95,103,124,133,136,152,159
    ]

class AtopileParser ( AtopileParserBase ):

    grammarFileName = "AtopileParser.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "'component'", "'module'", 
                     "'pin'", "'signal'", "'with'", "'optional'", "'new'", 
                     "'from'", "'import'", "'private'", "'True'", "'False'", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "'.'", "'...'", "'*'", "'('", 
                     "')'", "','", "':'", "';'", "'**'", "'='", "'['", "']'", 
                     "'|'", "'^'", "'&'", "'<<'", "'>>'", "'+'", "'-'", 
                     "'/'", "'%'", "'//'", "'~'", "'{'", "'}'", "'<'", "'>'", 
                     "'=='", "'>='", "'<='", "'<>'", "'!='", "'@'", "'->'", 
                     "'+='", "'-='", "'*='", "'@='", "'/='", "'%='", "'&='", 
                     "'|='", "'^='", "'<<='", "'>>='", "'**='", "'//='" ]

    symbolicNames = [ "<INVALID>", "INDENT", "DEDENT", "STRING", "NUMBER", 
                      "INTEGER", "COMPONENT", "MODULE", "PIN", "SIGNAL", 
                      "WITH", "OPTIONAL", "NEW", "FROM", "IMPORT", "PRIVATE", 
                      "TRUE", "FALSE", "NEWLINE", "NAME", "STRING_LITERAL", 
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
    RULE_componentdef = 6
    RULE_moduledef = 7
    RULE_import_stmt = 8
    RULE_assign_stmt = 9
    RULE_assignable = 10
    RULE_connect_stmt = 11
    RULE_connectable = 12
    RULE_signaldef_stmt = 13
    RULE_pindef_stmt = 14
    RULE_with_stmt = 15
    RULE_new_stmt = 16
    RULE_name_or_attr = 17
    RULE_attr = 18
    RULE_name = 19
    RULE_string = 20
    RULE_boolean_ = 21

    ruleNames =  [ "file_input", "stmt", "simple_stmts", "simple_stmt", 
                   "compound_stmt", "block", "componentdef", "moduledef", 
                   "import_stmt", "assign_stmt", "assignable", "connect_stmt", 
                   "connectable", "signaldef_stmt", "pindef_stmt", "with_stmt", 
                   "new_stmt", "name_or_attr", "attr", "name", "string", 
                   "boolean_" ]

    EOF = Token.EOF
    INDENT=1
    DEDENT=2
    STRING=3
    NUMBER=4
    INTEGER=5
    COMPONENT=6
    MODULE=7
    PIN=8
    SIGNAL=9
    WITH=10
    OPTIONAL=11
    NEW=12
    FROM=13
    IMPORT=14
    PRIVATE=15
    TRUE=16
    FALSE=17
    NEWLINE=18
    NAME=19
    STRING_LITERAL=20
    BYTES_LITERAL=21
    DECIMAL_INTEGER=22
    OCT_INTEGER=23
    HEX_INTEGER=24
    BIN_INTEGER=25
    FLOAT_NUMBER=26
    IMAG_NUMBER=27
    DOT=28
    ELLIPSIS=29
    STAR=30
    OPEN_PAREN=31
    CLOSE_PAREN=32
    COMMA=33
    COLON=34
    SEMI_COLON=35
    POWER=36
    ASSIGN=37
    OPEN_BRACK=38
    CLOSE_BRACK=39
    OR_OP=40
    XOR=41
    AND_OP=42
    LEFT_SHIFT=43
    RIGHT_SHIFT=44
    ADD=45
    MINUS=46
    DIV=47
    MOD=48
    IDIV=49
    NOT_OP=50
    OPEN_BRACE=51
    CLOSE_BRACE=52
    LESS_THAN=53
    GREATER_THAN=54
    EQUALS=55
    GT_EQ=56
    LT_EQ=57
    NOT_EQ_1=58
    NOT_EQ_2=59
    AT=60
    ARROW=61
    ADD_ASSIGN=62
    SUB_ASSIGN=63
    MULT_ASSIGN=64
    AT_ASSIGN=65
    DIV_ASSIGN=66
    MOD_ASSIGN=67
    AND_ASSIGN=68
    OR_ASSIGN=69
    XOR_ASSIGN=70
    LEFT_SHIFT_ASSIGN=71
    RIGHT_SHIFT_ASSIGN=72
    POWER_ASSIGN=73
    IDIV_ASSIGN=74
    SKIP_=75
    UNKNOWN_CHAR=76

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
            self.state = 48
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 839616) != 0):
                self.state = 46
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [18]:
                    self.state = 44
                    self.match(AtopileParser.NEWLINE)
                    pass
                elif token in [6, 7, 8, 9, 10, 11, 14, 15, 19]:
                    self.state = 45
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 50
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 51
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
            self.state = 55
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [8, 9, 10, 14, 15, 19]:
                self.enterOuterAlt(localctx, 1)
                self.state = 53
                self.simple_stmts()
                pass
            elif token in [6, 7, 11]:
                self.enterOuterAlt(localctx, 2)
                self.state = 54
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
            self.state = 57
            self.simple_stmt()
            self.state = 62
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 58
                    self.match(AtopileParser.SEMI_COLON)
                    self.state = 59
                    self.simple_stmt() 
                self.state = 64
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 66
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==35:
                self.state = 65
                self.match(AtopileParser.SEMI_COLON)


            self.state = 68
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
            self.state = 76
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 70
                self.import_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 71
                self.assign_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 72
                self.connect_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 73
                self.pindef_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 74
                self.signaldef_stmt()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 75
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

        def componentdef(self):
            return self.getTypedRuleContext(AtopileParser.ComponentdefContext,0)


        def moduledef(self):
            return self.getTypedRuleContext(AtopileParser.ModuledefContext,0)


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
            self.state = 80
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,6,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 78
                self.componentdef()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 79
                self.moduledef()
                pass


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
            self.state = 92
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [8, 9, 10, 14, 15, 19]:
                self.enterOuterAlt(localctx, 1)
                self.state = 82
                self.simple_stmts()
                pass
            elif token in [18]:
                self.enterOuterAlt(localctx, 2)
                self.state = 83
                self.match(AtopileParser.NEWLINE)
                self.state = 84
                self.match(AtopileParser.INDENT)
                self.state = 86 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 85
                    self.stmt()
                    self.state = 88 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 577472) != 0)):
                        break

                self.state = 90
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


    class ComponentdefContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def COMPONENT(self):
            return self.getToken(AtopileParser.COMPONENT, 0)

        def name(self):
            return self.getTypedRuleContext(AtopileParser.NameContext,0)


        def COLON(self):
            return self.getToken(AtopileParser.COLON, 0)

        def block(self):
            return self.getTypedRuleContext(AtopileParser.BlockContext,0)


        def OPTIONAL(self):
            return self.getToken(AtopileParser.OPTIONAL, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_componentdef

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterComponentdef" ):
                listener.enterComponentdef(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitComponentdef" ):
                listener.exitComponentdef(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitComponentdef" ):
                return visitor.visitComponentdef(self)
            else:
                return visitor.visitChildren(self)




    def componentdef(self):

        localctx = AtopileParser.ComponentdefContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_componentdef)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 95
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==11:
                self.state = 94
                self.match(AtopileParser.OPTIONAL)


            self.state = 97
            self.match(AtopileParser.COMPONENT)
            self.state = 98
            self.name()
            self.state = 99
            self.match(AtopileParser.COLON)
            self.state = 100
            self.block()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ModuledefContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def MODULE(self):
            return self.getToken(AtopileParser.MODULE, 0)

        def name(self):
            return self.getTypedRuleContext(AtopileParser.NameContext,0)


        def COLON(self):
            return self.getToken(AtopileParser.COLON, 0)

        def block(self):
            return self.getTypedRuleContext(AtopileParser.BlockContext,0)


        def OPTIONAL(self):
            return self.getToken(AtopileParser.OPTIONAL, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_moduledef

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterModuledef" ):
                listener.enterModuledef(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitModuledef" ):
                listener.exitModuledef(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitModuledef" ):
                return visitor.visitModuledef(self)
            else:
                return visitor.visitChildren(self)




    def moduledef(self):

        localctx = AtopileParser.ModuledefContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_moduledef)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 103
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==11:
                self.state = 102
                self.match(AtopileParser.OPTIONAL)


            self.state = 105
            self.match(AtopileParser.MODULE)
            self.state = 106
            self.name()
            self.state = 107
            self.match(AtopileParser.COLON)
            self.state = 108
            self.block()
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
            elif token in [19]:
                self.enterOuterAlt(localctx, 3)
                self.state = 121
                self.name_or_attr()
                pass
            elif token in [12]:
                self.enterOuterAlt(localctx, 4)
                self.state = 122
                self.new_stmt()
                pass
            elif token in [16, 17]:
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
        self.enterRule(localctx, 22, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 126
            self.connectable()
            self.state = 127
            self.match(AtopileParser.NOT_OP)
            self.state = 128
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
        self.enterRule(localctx, 24, self.RULE_connectable)
        try:
            self.state = 133
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [19]:
                self.enterOuterAlt(localctx, 1)
                self.state = 130
                self.name_or_attr()
                pass
            elif token in [9, 15]:
                self.enterOuterAlt(localctx, 2)
                self.state = 131
                self.signaldef_stmt()
                pass
            elif token in [8]:
                self.enterOuterAlt(localctx, 3)
                self.state = 132
                self.pindef_stmt()
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
        self.enterRule(localctx, 26, self.RULE_signaldef_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 136
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==15:
                self.state = 135
                self.match(AtopileParser.PRIVATE)


            self.state = 138
            self.match(AtopileParser.SIGNAL)
            self.state = 139
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
        self.enterRule(localctx, 28, self.RULE_pindef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 141
            self.match(AtopileParser.PIN)
            self.state = 142
            self.name()
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
        self.enterRule(localctx, 30, self.RULE_with_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 144
            self.match(AtopileParser.WITH)
            self.state = 145
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
        self.enterRule(localctx, 32, self.RULE_new_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 147
            self.match(AtopileParser.NEW)
            self.state = 148
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
        self.enterRule(localctx, 34, self.RULE_name_or_attr)
        try:
            self.state = 152
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 150
                self.attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 151
                self.name()
                pass


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
        self.enterRule(localctx, 36, self.RULE_attr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 154
            self.name()
            self.state = 157 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 155
                self.match(AtopileParser.DOT)
                self.state = 156
                self.name()
                self.state = 159 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==28):
                    break

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
        self.enterRule(localctx, 38, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 161
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
        self.enterRule(localctx, 40, self.RULE_string)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 163
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
        self.enterRule(localctx, 42, self.RULE_boolean_)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 165
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





