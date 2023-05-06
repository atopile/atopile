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
        4,1,68,88,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,1,0,1,0,5,0,27,8,0,
        10,0,12,0,30,9,0,1,0,1,0,1,1,1,1,1,1,1,1,3,1,38,8,1,1,2,1,2,1,2,
        1,2,1,2,1,3,1,3,1,3,4,3,48,8,3,11,3,12,3,49,1,3,1,3,1,4,1,4,1,4,
        1,4,1,5,1,5,1,5,1,5,1,6,1,6,1,6,1,7,1,7,1,7,1,7,1,8,1,8,1,8,1,8,
        3,8,73,8,8,1,9,1,9,3,9,77,8,9,1,10,1,10,1,10,4,10,82,8,10,11,10,
        12,10,83,1,11,1,11,1,11,0,0,12,0,2,4,6,8,10,12,14,16,18,20,22,0,
        2,1,0,6,7,1,0,8,9,86,0,28,1,0,0,0,2,37,1,0,0,0,4,39,1,0,0,0,6,44,
        1,0,0,0,8,53,1,0,0,0,10,57,1,0,0,0,12,61,1,0,0,0,14,64,1,0,0,0,16,
        72,1,0,0,0,18,76,1,0,0,0,20,78,1,0,0,0,22,85,1,0,0,0,24,27,5,10,
        0,0,25,27,3,2,1,0,26,24,1,0,0,0,26,25,1,0,0,0,27,30,1,0,0,0,28,26,
        1,0,0,0,28,29,1,0,0,0,29,31,1,0,0,0,30,28,1,0,0,0,31,32,5,0,0,1,
        32,1,1,0,0,0,33,38,3,4,2,0,34,38,3,8,4,0,35,38,3,10,5,0,36,38,3,
        12,6,0,37,33,1,0,0,0,37,34,1,0,0,0,37,35,1,0,0,0,37,36,1,0,0,0,38,
        3,1,0,0,0,39,40,7,0,0,0,40,41,3,14,7,0,41,42,5,26,0,0,42,43,3,6,
        3,0,43,5,1,0,0,0,44,45,5,10,0,0,45,47,5,1,0,0,46,48,3,2,1,0,47,46,
        1,0,0,0,48,49,1,0,0,0,49,47,1,0,0,0,49,50,1,0,0,0,50,51,1,0,0,0,
        51,52,5,2,0,0,52,7,1,0,0,0,53,54,3,18,9,0,54,55,5,29,0,0,55,56,3,
        16,8,0,56,9,1,0,0,0,57,58,3,18,9,0,58,59,5,42,0,0,59,60,3,18,9,0,
        60,11,1,0,0,0,61,62,7,1,0,0,62,63,3,18,9,0,63,13,1,0,0,0,64,65,3,
        18,9,0,65,66,5,23,0,0,66,67,5,24,0,0,67,15,1,0,0,0,68,73,5,3,0,0,
        69,73,5,4,0,0,70,73,3,18,9,0,71,73,3,14,7,0,72,68,1,0,0,0,72,69,
        1,0,0,0,72,70,1,0,0,0,72,71,1,0,0,0,73,17,1,0,0,0,74,77,3,20,10,
        0,75,77,3,22,11,0,76,74,1,0,0,0,76,75,1,0,0,0,77,19,1,0,0,0,78,81,
        3,22,11,0,79,80,5,20,0,0,80,82,3,22,11,0,81,79,1,0,0,0,82,83,1,0,
        0,0,83,81,1,0,0,0,83,84,1,0,0,0,84,21,1,0,0,0,85,86,5,11,0,0,86,
        23,1,0,0,0,7,26,28,37,49,72,76,83
    ]

class AtopileParser ( AtopileParserBase ):

    grammarFileName = "AtopileParser.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "'component'", "'module'", 
                     "'pin'", "'signal'", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "'.'", "'...'", 
                     "'*'", "'('", "')'", "','", "':'", "';'", "'**'", "'='", 
                     "'['", "']'", "'|'", "'^'", "'&'", "'<<'", "'>>'", 
                     "'+'", "'-'", "'/'", "'%'", "'//'", "'~'", "'{'", "'}'", 
                     "'<'", "'>'", "'=='", "'>='", "'<='", "'<>'", "'!='", 
                     "'@'", "'->'", "'+='", "'-='", "'*='", "'@='", "'/='", 
                     "'%='", "'&='", "'|='", "'^='", "'<<='", "'>>='", "'**='", 
                     "'//='" ]

    symbolicNames = [ "<INVALID>", "INDENT", "DEDENT", "STRING", "NUMBER", 
                      "INTEGER", "COMPONENT", "MODULE", "PIN", "SIGNAL", 
                      "NEWLINE", "NAME", "STRING_LITERAL", "BYTES_LITERAL", 
                      "DECIMAL_INTEGER", "OCT_INTEGER", "HEX_INTEGER", "BIN_INTEGER", 
                      "FLOAT_NUMBER", "IMAG_NUMBER", "DOT", "ELLIPSIS", 
                      "STAR", "OPEN_PAREN", "CLOSE_PAREN", "COMMA", "COLON", 
                      "SEMI_COLON", "POWER", "ASSIGN", "OPEN_BRACK", "CLOSE_BRACK", 
                      "OR_OP", "XOR", "AND_OP", "LEFT_SHIFT", "RIGHT_SHIFT", 
                      "ADD", "MINUS", "DIV", "MOD", "IDIV", "NOT_OP", "OPEN_BRACE", 
                      "CLOSE_BRACE", "LESS_THAN", "GREATER_THAN", "EQUALS", 
                      "GT_EQ", "LT_EQ", "NOT_EQ_1", "NOT_EQ_2", "AT", "ARROW", 
                      "ADD_ASSIGN", "SUB_ASSIGN", "MULT_ASSIGN", "AT_ASSIGN", 
                      "DIV_ASSIGN", "MOD_ASSIGN", "AND_ASSIGN", "OR_ASSIGN", 
                      "XOR_ASSIGN", "LEFT_SHIFT_ASSIGN", "RIGHT_SHIFT_ASSIGN", 
                      "POWER_ASSIGN", "IDIV_ASSIGN", "SKIP_", "UNKNOWN_CHAR" ]

    RULE_file_input = 0
    RULE_stmt = 1
    RULE_block_def = 2
    RULE_block = 3
    RULE_assign_stmt = 4
    RULE_connect_stmt = 5
    RULE_def_stmt = 6
    RULE_paramatised_stmt = 7
    RULE_assign_value = 8
    RULE_name_or_attr = 9
    RULE_attr = 10
    RULE_name = 11

    ruleNames =  [ "file_input", "stmt", "block_def", "block", "assign_stmt", 
                   "connect_stmt", "def_stmt", "paramatised_stmt", "assign_value", 
                   "name_or_attr", "attr", "name" ]

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
    NEWLINE=10
    NAME=11
    STRING_LITERAL=12
    BYTES_LITERAL=13
    DECIMAL_INTEGER=14
    OCT_INTEGER=15
    HEX_INTEGER=16
    BIN_INTEGER=17
    FLOAT_NUMBER=18
    IMAG_NUMBER=19
    DOT=20
    ELLIPSIS=21
    STAR=22
    OPEN_PAREN=23
    CLOSE_PAREN=24
    COMMA=25
    COLON=26
    SEMI_COLON=27
    POWER=28
    ASSIGN=29
    OPEN_BRACK=30
    CLOSE_BRACK=31
    OR_OP=32
    XOR=33
    AND_OP=34
    LEFT_SHIFT=35
    RIGHT_SHIFT=36
    ADD=37
    MINUS=38
    DIV=39
    MOD=40
    IDIV=41
    NOT_OP=42
    OPEN_BRACE=43
    CLOSE_BRACE=44
    LESS_THAN=45
    GREATER_THAN=46
    EQUALS=47
    GT_EQ=48
    LT_EQ=49
    NOT_EQ_1=50
    NOT_EQ_2=51
    AT=52
    ARROW=53
    ADD_ASSIGN=54
    SUB_ASSIGN=55
    MULT_ASSIGN=56
    AT_ASSIGN=57
    DIV_ASSIGN=58
    MOD_ASSIGN=59
    AND_ASSIGN=60
    OR_ASSIGN=61
    XOR_ASSIGN=62
    LEFT_SHIFT_ASSIGN=63
    RIGHT_SHIFT_ASSIGN=64
    POWER_ASSIGN=65
    IDIV_ASSIGN=66
    SKIP_=67
    UNKNOWN_CHAR=68

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
            self.state = 28
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 4032) != 0):
                self.state = 26
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [10]:
                    self.state = 24
                    self.match(AtopileParser.NEWLINE)
                    pass
                elif token in [6, 7, 8, 9, 11]:
                    self.state = 25
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 30
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 31
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

        def block_def(self):
            return self.getTypedRuleContext(AtopileParser.Block_defContext,0)


        def assign_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Assign_stmtContext,0)


        def connect_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Connect_stmtContext,0)


        def def_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Def_stmtContext,0)


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
            self.state = 37
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,2,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 33
                self.block_def()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 34
                self.assign_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 35
                self.connect_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 36
                self.def_stmt()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Block_defContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def paramatised_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Paramatised_stmtContext,0)


        def COLON(self):
            return self.getToken(AtopileParser.COLON, 0)

        def block(self):
            return self.getTypedRuleContext(AtopileParser.BlockContext,0)


        def COMPONENT(self):
            return self.getToken(AtopileParser.COMPONENT, 0)

        def MODULE(self):
            return self.getToken(AtopileParser.MODULE, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_block_def

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBlock_def" ):
                listener.enterBlock_def(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBlock_def" ):
                listener.exitBlock_def(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBlock_def" ):
                return visitor.visitBlock_def(self)
            else:
                return visitor.visitChildren(self)




    def block_def(self):

        localctx = AtopileParser.Block_defContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_block_def)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 39
            _la = self._input.LA(1)
            if not(_la==6 or _la==7):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 40
            self.paramatised_stmt()
            self.state = 41
            self.match(AtopileParser.COLON)
            self.state = 42
            self.block()
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
        self.enterRule(localctx, 6, self.RULE_block)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 44
            self.match(AtopileParser.NEWLINE)
            self.state = 45
            self.match(AtopileParser.INDENT)
            self.state = 47 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 46
                self.stmt()
                self.state = 49 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 3008) != 0)):
                    break

            self.state = 51
            self.match(AtopileParser.DEDENT)
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

        def assign_value(self):
            return self.getTypedRuleContext(AtopileParser.Assign_valueContext,0)


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
        self.enterRule(localctx, 8, self.RULE_assign_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 53
            self.name_or_attr()
            self.state = 54
            self.match(AtopileParser.ASSIGN)
            self.state = 55
            self.assign_value()
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
        self.enterRule(localctx, 10, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 57
            self.name_or_attr()
            self.state = 58
            self.match(AtopileParser.NOT_OP)
            self.state = 59
            self.name_or_attr()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Def_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def PIN(self):
            return self.getToken(AtopileParser.PIN, 0)

        def SIGNAL(self):
            return self.getToken(AtopileParser.SIGNAL, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_def_stmt

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDef_stmt" ):
                listener.enterDef_stmt(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDef_stmt" ):
                listener.exitDef_stmt(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDef_stmt" ):
                return visitor.visitDef_stmt(self)
            else:
                return visitor.visitChildren(self)




    def def_stmt(self):

        localctx = AtopileParser.Def_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_def_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 61
            _la = self._input.LA(1)
            if not(_la==8 or _la==9):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 62
            self.name_or_attr()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Paramatised_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def OPEN_PAREN(self):
            return self.getToken(AtopileParser.OPEN_PAREN, 0)

        def CLOSE_PAREN(self):
            return self.getToken(AtopileParser.CLOSE_PAREN, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_paramatised_stmt

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterParamatised_stmt" ):
                listener.enterParamatised_stmt(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitParamatised_stmt" ):
                listener.exitParamatised_stmt(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParamatised_stmt" ):
                return visitor.visitParamatised_stmt(self)
            else:
                return visitor.visitChildren(self)




    def paramatised_stmt(self):

        localctx = AtopileParser.Paramatised_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_paramatised_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 64
            self.name_or_attr()
            self.state = 65
            self.match(AtopileParser.OPEN_PAREN)
            self.state = 66
            self.match(AtopileParser.CLOSE_PAREN)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Assign_valueContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def STRING(self):
            return self.getToken(AtopileParser.STRING, 0)

        def NUMBER(self):
            return self.getToken(AtopileParser.NUMBER, 0)

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def paramatised_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Paramatised_stmtContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_assign_value

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterAssign_value" ):
                listener.enterAssign_value(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitAssign_value" ):
                listener.exitAssign_value(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssign_value" ):
                return visitor.visitAssign_value(self)
            else:
                return visitor.visitChildren(self)




    def assign_value(self):

        localctx = AtopileParser.Assign_valueContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_assign_value)
        try:
            self.state = 72
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,4,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 68
                self.match(AtopileParser.STRING)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 69
                self.match(AtopileParser.NUMBER)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 70
                self.name_or_attr()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 71
                self.paramatised_stmt()
                pass


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
        self.enterRule(localctx, 18, self.RULE_name_or_attr)
        try:
            self.state = 76
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 74
                self.attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 75
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
        self.enterRule(localctx, 20, self.RULE_attr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 78
            self.name()
            self.state = 81 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 79
                self.match(AtopileParser.DOT)
                self.state = 80
                self.name()
                self.state = 83 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==20):
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
        self.enterRule(localctx, 22, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 85
            self.match(AtopileParser.NAME)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





