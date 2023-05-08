# Generated from AtopileParser.g4 by ANTLR 4.12.0
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

if __name__ is not None and "." in __name__:
    from .AtopileParserBase import AtopileParserBase
else:
    from AtopileParserBase import AtopileParserBase

def serializedATN():
    return [
        4,1,71,137,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,1,0,1,0,5,0,37,8,0,10,0,12,0,40,9,
        0,1,0,1,0,1,1,1,1,3,1,46,8,1,1,2,1,2,1,2,5,2,51,8,2,10,2,12,2,54,
        9,2,1,2,3,2,57,8,2,1,2,1,2,1,3,1,3,1,3,1,3,1,3,3,3,66,8,3,1,4,1,
        4,3,4,70,8,4,1,5,1,5,1,5,1,5,4,5,76,8,5,11,5,12,5,77,1,5,1,5,3,5,
        82,8,5,1,6,3,6,85,8,6,1,6,1,6,1,6,1,6,1,6,1,7,3,7,93,8,7,1,7,1,7,
        1,7,1,7,1,7,1,8,1,8,1,8,1,8,1,8,1,8,3,8,106,8,8,1,9,1,9,1,9,1,9,
        1,10,1,10,1,10,1,11,1,11,1,11,1,12,1,12,1,12,1,13,1,13,1,13,1,14,
        1,14,3,14,126,8,14,1,15,1,15,1,15,4,15,131,8,15,11,15,12,15,132,
        1,16,1,16,1,16,0,0,17,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,
        32,0,0,138,0,38,1,0,0,0,2,45,1,0,0,0,4,47,1,0,0,0,6,65,1,0,0,0,8,
        69,1,0,0,0,10,81,1,0,0,0,12,84,1,0,0,0,14,92,1,0,0,0,16,99,1,0,0,
        0,18,107,1,0,0,0,20,111,1,0,0,0,22,114,1,0,0,0,24,117,1,0,0,0,26,
        120,1,0,0,0,28,125,1,0,0,0,30,127,1,0,0,0,32,134,1,0,0,0,34,37,5,
        13,0,0,35,37,3,2,1,0,36,34,1,0,0,0,36,35,1,0,0,0,37,40,1,0,0,0,38,
        36,1,0,0,0,38,39,1,0,0,0,39,41,1,0,0,0,40,38,1,0,0,0,41,42,5,0,0,
        1,42,1,1,0,0,0,43,46,3,4,2,0,44,46,3,8,4,0,45,43,1,0,0,0,45,44,1,
        0,0,0,46,3,1,0,0,0,47,52,3,6,3,0,48,49,5,30,0,0,49,51,3,6,3,0,50,
        48,1,0,0,0,51,54,1,0,0,0,52,50,1,0,0,0,52,53,1,0,0,0,53,56,1,0,0,
        0,54,52,1,0,0,0,55,57,5,30,0,0,56,55,1,0,0,0,56,57,1,0,0,0,57,58,
        1,0,0,0,58,59,5,13,0,0,59,5,1,0,0,0,60,66,3,16,8,0,61,66,3,18,9,
        0,62,66,3,20,10,0,63,66,3,22,11,0,64,66,3,24,12,0,65,60,1,0,0,0,
        65,61,1,0,0,0,65,62,1,0,0,0,65,63,1,0,0,0,65,64,1,0,0,0,66,7,1,0,
        0,0,67,70,3,12,6,0,68,70,3,14,7,0,69,67,1,0,0,0,69,68,1,0,0,0,70,
        9,1,0,0,0,71,82,3,4,2,0,72,73,5,13,0,0,73,75,5,1,0,0,74,76,3,2,1,
        0,75,74,1,0,0,0,76,77,1,0,0,0,77,75,1,0,0,0,77,78,1,0,0,0,78,79,
        1,0,0,0,79,80,5,2,0,0,80,82,1,0,0,0,81,71,1,0,0,0,81,72,1,0,0,0,
        82,11,1,0,0,0,83,85,5,11,0,0,84,83,1,0,0,0,84,85,1,0,0,0,85,86,1,
        0,0,0,86,87,5,6,0,0,87,88,3,32,16,0,88,89,5,29,0,0,89,90,3,10,5,
        0,90,13,1,0,0,0,91,93,5,11,0,0,92,91,1,0,0,0,92,93,1,0,0,0,93,94,
        1,0,0,0,94,95,5,7,0,0,95,96,3,32,16,0,96,97,5,29,0,0,97,98,3,10,
        5,0,98,15,1,0,0,0,99,100,3,28,14,0,100,105,5,32,0,0,101,106,5,3,
        0,0,102,106,5,4,0,0,103,106,3,28,14,0,104,106,3,26,13,0,105,101,
        1,0,0,0,105,102,1,0,0,0,105,103,1,0,0,0,105,104,1,0,0,0,106,17,1,
        0,0,0,107,108,3,28,14,0,108,109,5,45,0,0,109,110,3,28,14,0,110,19,
        1,0,0,0,111,112,5,8,0,0,112,113,3,32,16,0,113,21,1,0,0,0,114,115,
        5,9,0,0,115,116,3,32,16,0,116,23,1,0,0,0,117,118,5,10,0,0,118,119,
        3,28,14,0,119,25,1,0,0,0,120,121,5,12,0,0,121,122,3,28,14,0,122,
        27,1,0,0,0,123,126,3,30,15,0,124,126,3,32,16,0,125,123,1,0,0,0,125,
        124,1,0,0,0,126,29,1,0,0,0,127,130,3,32,16,0,128,129,5,23,0,0,129,
        131,3,32,16,0,130,128,1,0,0,0,131,132,1,0,0,0,132,130,1,0,0,0,132,
        133,1,0,0,0,133,31,1,0,0,0,134,135,5,14,0,0,135,33,1,0,0,0,14,36,
        38,45,52,56,65,69,77,81,84,92,105,125,132
    ]

class AtopileParser ( AtopileParserBase ):

    grammarFileName = "AtopileParser.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "'component'", "'module'", 
                     "'pin'", "'signal'", "'with'", "'optional'", "'new'", 
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
                      "WITH", "OPTIONAL", "NEW", "NEWLINE", "NAME", "STRING_LITERAL", 
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
    RULE_assign_stmt = 8
    RULE_connect_stmt = 9
    RULE_pindef_stmt = 10
    RULE_signaldef_stmt = 11
    RULE_with_stmt = 12
    RULE_new_element = 13
    RULE_name_or_attr = 14
    RULE_attr = 15
    RULE_name = 16

    ruleNames =  [ "file_input", "stmt", "simple_stmts", "simple_stmt", 
                   "compound_stmt", "block", "componentdef", "moduledef", 
                   "assign_stmt", "connect_stmt", "pindef_stmt", "signaldef_stmt", 
                   "with_stmt", "new_element", "name_or_attr", "attr", "name" ]

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
    NEWLINE=13
    NAME=14
    STRING_LITERAL=15
    BYTES_LITERAL=16
    DECIMAL_INTEGER=17
    OCT_INTEGER=18
    HEX_INTEGER=19
    BIN_INTEGER=20
    FLOAT_NUMBER=21
    IMAG_NUMBER=22
    DOT=23
    ELLIPSIS=24
    STAR=25
    OPEN_PAREN=26
    CLOSE_PAREN=27
    COMMA=28
    COLON=29
    SEMI_COLON=30
    POWER=31
    ASSIGN=32
    OPEN_BRACK=33
    CLOSE_BRACK=34
    OR_OP=35
    XOR=36
    AND_OP=37
    LEFT_SHIFT=38
    RIGHT_SHIFT=39
    ADD=40
    MINUS=41
    DIV=42
    MOD=43
    IDIV=44
    NOT_OP=45
    OPEN_BRACE=46
    CLOSE_BRACE=47
    LESS_THAN=48
    GREATER_THAN=49
    EQUALS=50
    GT_EQ=51
    LT_EQ=52
    NOT_EQ_1=53
    NOT_EQ_2=54
    AT=55
    ARROW=56
    ADD_ASSIGN=57
    SUB_ASSIGN=58
    MULT_ASSIGN=59
    AT_ASSIGN=60
    DIV_ASSIGN=61
    MOD_ASSIGN=62
    AND_ASSIGN=63
    OR_ASSIGN=64
    XOR_ASSIGN=65
    LEFT_SHIFT_ASSIGN=66
    RIGHT_SHIFT_ASSIGN=67
    POWER_ASSIGN=68
    IDIV_ASSIGN=69
    SKIP_=70
    UNKNOWN_CHAR=71

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.12.0")
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
            self.state = 38
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 28608) != 0):
                self.state = 36
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [13]:
                    self.state = 34
                    self.match(AtopileParser.NEWLINE)
                    pass
                elif token in [6, 7, 8, 9, 10, 11, 14]:
                    self.state = 35
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 40
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 41
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
            self.state = 45
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [8, 9, 10, 14]:
                self.enterOuterAlt(localctx, 1)
                self.state = 43
                self.simple_stmts()
                pass
            elif token in [6, 7, 11]:
                self.enterOuterAlt(localctx, 2)
                self.state = 44
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
            self.state = 47
            self.simple_stmt()
            self.state = 52
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 48
                    self.match(AtopileParser.SEMI_COLON)
                    self.state = 49
                    self.simple_stmt() 
                self.state = 54
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 56
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==30:
                self.state = 55
                self.match(AtopileParser.SEMI_COLON)


            self.state = 58
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
            self.state = 65
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 60
                self.assign_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 61
                self.connect_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 62
                self.pindef_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 63
                self.signaldef_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 64
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
            self.state = 69
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,6,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 67
                self.componentdef()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 68
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
            self.state = 81
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [8, 9, 10, 14]:
                self.enterOuterAlt(localctx, 1)
                self.state = 71
                self.simple_stmts()
                pass
            elif token in [13]:
                self.enterOuterAlt(localctx, 2)
                self.state = 72
                self.match(AtopileParser.NEWLINE)
                self.state = 73
                self.match(AtopileParser.INDENT)
                self.state = 75 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 74
                    self.stmt()
                    self.state = 77 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 20416) != 0)):
                        break

                self.state = 79
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
            self.state = 84
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==11:
                self.state = 83
                self.match(AtopileParser.OPTIONAL)


            self.state = 86
            self.match(AtopileParser.COMPONENT)
            self.state = 87
            self.name()
            self.state = 88
            self.match(AtopileParser.COLON)
            self.state = 89
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
            self.state = 92
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==11:
                self.state = 91
                self.match(AtopileParser.OPTIONAL)


            self.state = 94
            self.match(AtopileParser.MODULE)
            self.state = 95
            self.name()
            self.state = 96
            self.match(AtopileParser.COLON)
            self.state = 97
            self.block()
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

        def name_or_attr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.Name_or_attrContext)
            else:
                return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,i)


        def ASSIGN(self):
            return self.getToken(AtopileParser.ASSIGN, 0)

        def STRING(self):
            return self.getToken(AtopileParser.STRING, 0)

        def NUMBER(self):
            return self.getToken(AtopileParser.NUMBER, 0)

        def new_element(self):
            return self.getTypedRuleContext(AtopileParser.New_elementContext,0)


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
        self.enterRule(localctx, 16, self.RULE_assign_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 99
            self.name_or_attr()
            self.state = 100
            self.match(AtopileParser.ASSIGN)
            self.state = 105
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3]:
                self.state = 101
                self.match(AtopileParser.STRING)
                pass
            elif token in [4]:
                self.state = 102
                self.match(AtopileParser.NUMBER)
                pass
            elif token in [14]:
                self.state = 103
                self.name_or_attr()
                pass
            elif token in [12]:
                self.state = 104
                self.new_element()
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

        def name_or_attr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.Name_or_attrContext)
            else:
                return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,i)


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
        self.enterRule(localctx, 18, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 107
            self.name_or_attr()
            self.state = 108
            self.match(AtopileParser.NOT_OP)
            self.state = 109
            self.name_or_attr()
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
        self.enterRule(localctx, 20, self.RULE_pindef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 111
            self.match(AtopileParser.PIN)
            self.state = 112
            self.name()
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
        self.enterRule(localctx, 22, self.RULE_signaldef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 114
            self.match(AtopileParser.SIGNAL)
            self.state = 115
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
        self.enterRule(localctx, 24, self.RULE_with_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 117
            self.match(AtopileParser.WITH)
            self.state = 118
            self.name_or_attr()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class New_elementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NEW(self):
            return self.getToken(AtopileParser.NEW, 0)

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_new_element

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterNew_element" ):
                listener.enterNew_element(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitNew_element" ):
                listener.exitNew_element(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNew_element" ):
                return visitor.visitNew_element(self)
            else:
                return visitor.visitChildren(self)




    def new_element(self):

        localctx = AtopileParser.New_elementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_new_element)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 120
            self.match(AtopileParser.NEW)
            self.state = 121
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
        self.enterRule(localctx, 28, self.RULE_name_or_attr)
        try:
            self.state = 125
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 123
                self.attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 124
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
        self.enterRule(localctx, 30, self.RULE_attr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 127
            self.name()
            self.state = 130 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 128
                self.match(AtopileParser.DOT)
                self.state = 129
                self.name()
                self.state = 132 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==23):
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
        self.enterRule(localctx, 32, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 134
            self.match(AtopileParser.NAME)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





