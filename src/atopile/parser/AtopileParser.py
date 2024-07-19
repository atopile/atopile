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
        4,1,80,391,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,2,39,7,39,
        2,40,7,40,2,41,7,41,2,42,7,42,2,43,7,43,2,44,7,44,2,45,7,45,2,46,
        7,46,2,47,7,47,2,48,7,48,2,49,7,49,2,50,7,50,2,51,7,51,2,52,7,52,
        1,0,1,0,5,0,109,8,0,10,0,12,0,112,9,0,1,0,1,0,1,1,1,1,3,1,118,8,
        1,1,2,1,2,1,2,5,2,123,8,2,10,2,12,2,126,9,2,1,2,3,2,129,8,2,1,2,
        1,2,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,3,3,145,8,3,
        1,4,1,4,1,5,1,5,1,5,1,5,3,5,153,8,5,1,5,1,5,1,5,1,6,1,6,1,7,1,7,
        1,7,1,7,4,7,164,8,7,11,7,12,7,165,1,7,1,7,3,7,170,8,7,1,8,1,8,1,
        8,1,8,1,8,1,9,1,9,1,9,1,9,1,9,1,9,5,9,183,8,9,10,9,12,9,186,9,9,
        1,10,1,10,1,10,1,11,1,11,3,11,193,8,11,1,11,1,11,1,11,1,12,1,12,
        3,12,200,8,12,1,12,1,12,1,12,1,13,1,13,1,14,1,14,3,14,209,8,14,1,
        15,1,15,1,15,1,15,1,15,3,15,216,8,15,1,16,1,16,1,16,1,16,1,17,1,
        17,1,17,1,17,1,18,1,18,1,18,1,18,3,18,230,8,18,1,19,1,19,1,19,1,
        20,1,20,1,20,1,20,3,20,239,8,20,1,21,1,21,1,21,1,22,1,22,1,23,1,
        23,1,24,1,24,1,24,1,25,1,25,4,25,253,8,25,11,25,12,25,254,1,26,1,
        26,1,26,1,26,1,26,3,26,262,8,26,1,27,1,27,1,27,1,28,1,28,1,28,1,
        29,1,29,1,29,1,30,1,30,1,30,1,31,1,31,1,31,1,32,1,32,1,32,1,32,1,
        32,1,32,5,32,285,8,32,10,32,12,32,288,9,32,1,33,1,33,1,33,1,33,1,
        33,1,33,5,33,296,8,33,10,33,12,33,299,9,33,1,34,1,34,1,34,1,34,1,
        34,1,34,5,34,307,8,34,10,34,12,34,310,9,34,1,35,1,35,1,35,3,35,315,
        8,35,1,36,1,36,1,36,1,36,4,36,321,8,36,11,36,12,36,322,1,36,1,36,
        3,36,327,8,36,1,37,1,37,1,38,1,38,1,38,3,38,334,8,38,1,39,1,39,1,
        39,1,39,1,40,1,40,1,40,3,40,343,8,40,1,41,1,41,1,41,1,41,1,42,1,
        42,1,42,1,42,1,43,3,43,354,8,43,1,43,1,43,3,43,358,8,43,1,44,1,44,
        1,44,3,44,363,8,44,1,45,1,45,3,45,367,8,45,1,46,1,46,1,46,1,47,1,
        47,1,47,1,47,1,48,1,48,1,48,4,48,379,8,48,11,48,12,48,380,1,49,1,
        49,1,50,1,50,1,51,1,51,1,52,1,52,1,52,0,3,64,66,68,53,0,2,4,6,8,
        10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,
        54,56,58,60,62,64,66,68,70,72,74,76,78,80,82,84,86,88,90,92,94,96,
        98,100,102,104,0,6,1,0,6,8,1,0,67,68,2,0,46,46,48,48,1,0,51,52,2,
        0,36,36,53,53,1,0,16,17,390,0,110,1,0,0,0,2,117,1,0,0,0,4,119,1,
        0,0,0,6,144,1,0,0,0,8,146,1,0,0,0,10,148,1,0,0,0,12,157,1,0,0,0,
        14,169,1,0,0,0,16,171,1,0,0,0,18,176,1,0,0,0,20,187,1,0,0,0,22,190,
        1,0,0,0,24,197,1,0,0,0,26,204,1,0,0,0,28,208,1,0,0,0,30,215,1,0,
        0,0,32,217,1,0,0,0,34,221,1,0,0,0,36,229,1,0,0,0,38,231,1,0,0,0,
        40,234,1,0,0,0,42,240,1,0,0,0,44,243,1,0,0,0,46,245,1,0,0,0,48,247,
        1,0,0,0,50,250,1,0,0,0,52,261,1,0,0,0,54,263,1,0,0,0,56,266,1,0,
        0,0,58,269,1,0,0,0,60,272,1,0,0,0,62,275,1,0,0,0,64,278,1,0,0,0,
        66,289,1,0,0,0,68,300,1,0,0,0,70,311,1,0,0,0,72,326,1,0,0,0,74,328,
        1,0,0,0,76,333,1,0,0,0,78,335,1,0,0,0,80,342,1,0,0,0,82,344,1,0,
        0,0,84,348,1,0,0,0,86,353,1,0,0,0,88,359,1,0,0,0,90,366,1,0,0,0,
        92,368,1,0,0,0,94,371,1,0,0,0,96,375,1,0,0,0,98,382,1,0,0,0,100,
        384,1,0,0,0,102,386,1,0,0,0,104,388,1,0,0,0,106,109,5,20,0,0,107,
        109,3,2,1,0,108,106,1,0,0,0,108,107,1,0,0,0,109,112,1,0,0,0,110,
        108,1,0,0,0,110,111,1,0,0,0,111,113,1,0,0,0,112,110,1,0,0,0,113,
        114,5,0,0,1,114,1,1,0,0,0,115,118,3,4,2,0,116,118,3,8,4,0,117,115,
        1,0,0,0,117,116,1,0,0,0,118,3,1,0,0,0,119,124,3,6,3,0,120,121,5,
        41,0,0,121,123,3,6,3,0,122,120,1,0,0,0,123,126,1,0,0,0,124,122,1,
        0,0,0,124,125,1,0,0,0,125,128,1,0,0,0,126,124,1,0,0,0,127,129,5,
        41,0,0,128,127,1,0,0,0,128,129,1,0,0,0,129,130,1,0,0,0,130,131,5,
        20,0,0,131,5,1,0,0,0,132,145,3,18,9,0,133,145,3,16,8,0,134,145,3,
        22,11,0,135,145,3,24,12,0,136,145,3,34,17,0,137,145,3,32,16,0,138,
        145,3,40,20,0,139,145,3,38,19,0,140,145,3,48,24,0,141,145,3,20,10,
        0,142,145,3,44,22,0,143,145,3,46,23,0,144,132,1,0,0,0,144,133,1,
        0,0,0,144,134,1,0,0,0,144,135,1,0,0,0,144,136,1,0,0,0,144,137,1,
        0,0,0,144,138,1,0,0,0,144,139,1,0,0,0,144,140,1,0,0,0,144,141,1,
        0,0,0,144,142,1,0,0,0,144,143,1,0,0,0,145,7,1,0,0,0,146,147,3,10,
        5,0,147,9,1,0,0,0,148,149,3,12,6,0,149,152,3,100,50,0,150,151,5,
        12,0,0,151,153,3,90,45,0,152,150,1,0,0,0,152,153,1,0,0,0,153,154,
        1,0,0,0,154,155,5,40,0,0,155,156,3,14,7,0,156,11,1,0,0,0,157,158,
        7,0,0,0,158,13,1,0,0,0,159,170,3,4,2,0,160,161,5,20,0,0,161,163,
        5,1,0,0,162,164,3,2,1,0,163,162,1,0,0,0,164,165,1,0,0,0,165,163,
        1,0,0,0,165,166,1,0,0,0,166,167,1,0,0,0,167,168,5,2,0,0,168,170,
        1,0,0,0,169,159,1,0,0,0,169,160,1,0,0,0,170,15,1,0,0,0,171,172,5,
        13,0,0,172,173,3,90,45,0,173,174,5,12,0,0,174,175,3,102,51,0,175,
        17,1,0,0,0,176,177,5,12,0,0,177,178,3,102,51,0,178,179,5,13,0,0,
        179,184,3,90,45,0,180,181,5,39,0,0,181,183,3,90,45,0,182,180,1,0,
        0,0,183,186,1,0,0,0,184,182,1,0,0,0,184,185,1,0,0,0,185,19,1,0,0,
        0,186,184,1,0,0,0,187,188,3,90,45,0,188,189,3,92,46,0,189,21,1,0,
        0,0,190,192,3,90,45,0,191,193,3,92,46,0,192,191,1,0,0,0,192,193,
        1,0,0,0,193,194,1,0,0,0,194,195,5,43,0,0,195,196,3,30,15,0,196,23,
        1,0,0,0,197,199,3,90,45,0,198,200,3,92,46,0,199,198,1,0,0,0,199,
        200,1,0,0,0,200,201,1,0,0,0,201,202,3,26,13,0,202,203,3,28,14,0,
        203,25,1,0,0,0,204,205,7,1,0,0,205,27,1,0,0,0,206,209,3,80,40,0,
        207,209,3,64,32,0,208,206,1,0,0,0,208,207,1,0,0,0,209,29,1,0,0,0,
        210,216,3,102,51,0,211,216,3,42,21,0,212,216,3,80,40,0,213,216,3,
        64,32,0,214,216,3,104,52,0,215,210,1,0,0,0,215,211,1,0,0,0,215,212,
        1,0,0,0,215,213,1,0,0,0,215,214,1,0,0,0,216,31,1,0,0,0,217,218,3,
        90,45,0,218,219,5,66,0,0,219,220,3,90,45,0,220,33,1,0,0,0,221,222,
        3,36,18,0,222,223,5,55,0,0,223,224,3,36,18,0,224,35,1,0,0,0,225,
        230,3,90,45,0,226,230,3,94,47,0,227,230,3,38,19,0,228,230,3,40,20,
        0,229,225,1,0,0,0,229,226,1,0,0,0,229,227,1,0,0,0,229,228,1,0,0,
        0,230,37,1,0,0,0,231,232,5,10,0,0,232,233,3,100,50,0,233,39,1,0,
        0,0,234,238,5,9,0,0,235,239,3,100,50,0,236,239,3,98,49,0,237,239,
        3,102,51,0,238,235,1,0,0,0,238,236,1,0,0,0,238,237,1,0,0,0,239,41,
        1,0,0,0,240,241,5,11,0,0,241,242,3,90,45,0,242,43,1,0,0,0,243,244,
        3,102,51,0,244,45,1,0,0,0,245,246,5,19,0,0,246,47,1,0,0,0,247,248,
        5,14,0,0,248,249,3,50,25,0,249,49,1,0,0,0,250,252,3,64,32,0,251,
        253,3,52,26,0,252,251,1,0,0,0,253,254,1,0,0,0,254,252,1,0,0,0,254,
        255,1,0,0,0,255,51,1,0,0,0,256,262,3,54,27,0,257,262,3,56,28,0,258,
        262,3,58,29,0,259,262,3,60,30,0,260,262,3,62,31,0,261,256,1,0,0,
        0,261,257,1,0,0,0,261,258,1,0,0,0,261,259,1,0,0,0,261,260,1,0,0,
        0,262,53,1,0,0,0,263,264,5,58,0,0,264,265,3,64,32,0,265,55,1,0,0,
        0,266,267,5,59,0,0,267,268,3,64,32,0,268,57,1,0,0,0,269,270,5,62,
        0,0,270,271,3,64,32,0,271,59,1,0,0,0,272,273,5,61,0,0,273,274,3,
        64,32,0,274,61,1,0,0,0,275,276,5,18,0,0,276,277,3,64,32,0,277,63,
        1,0,0,0,278,279,6,32,-1,0,279,280,3,66,33,0,280,286,1,0,0,0,281,
        282,10,2,0,0,282,283,7,2,0,0,283,285,3,66,33,0,284,281,1,0,0,0,285,
        288,1,0,0,0,286,284,1,0,0,0,286,287,1,0,0,0,287,65,1,0,0,0,288,286,
        1,0,0,0,289,290,6,33,-1,0,290,291,3,68,34,0,291,297,1,0,0,0,292,
        293,10,2,0,0,293,294,7,3,0,0,294,296,3,68,34,0,295,292,1,0,0,0,296,
        299,1,0,0,0,297,295,1,0,0,0,297,298,1,0,0,0,298,67,1,0,0,0,299,297,
        1,0,0,0,300,301,6,34,-1,0,301,302,3,70,35,0,302,308,1,0,0,0,303,
        304,10,2,0,0,304,305,7,4,0,0,305,307,3,70,35,0,306,303,1,0,0,0,307,
        310,1,0,0,0,308,306,1,0,0,0,308,309,1,0,0,0,309,69,1,0,0,0,310,308,
        1,0,0,0,311,314,3,72,36,0,312,313,5,42,0,0,313,315,3,72,36,0,314,
        312,1,0,0,0,314,315,1,0,0,0,315,71,1,0,0,0,316,327,3,74,37,0,317,
        318,3,100,50,0,318,320,5,37,0,0,319,321,3,74,37,0,320,319,1,0,0,
        0,321,322,1,0,0,0,322,320,1,0,0,0,322,323,1,0,0,0,323,324,1,0,0,
        0,324,325,5,38,0,0,325,327,1,0,0,0,326,316,1,0,0,0,326,317,1,0,0,
        0,327,73,1,0,0,0,328,329,3,76,38,0,329,75,1,0,0,0,330,334,3,90,45,
        0,331,334,3,80,40,0,332,334,3,78,39,0,333,330,1,0,0,0,333,331,1,
        0,0,0,333,332,1,0,0,0,334,77,1,0,0,0,335,336,5,37,0,0,336,337,3,
        64,32,0,337,338,5,38,0,0,338,79,1,0,0,0,339,343,3,82,41,0,340,343,
        3,84,42,0,341,343,3,86,43,0,342,339,1,0,0,0,342,340,1,0,0,0,342,
        341,1,0,0,0,343,81,1,0,0,0,344,345,3,86,43,0,345,346,5,15,0,0,346,
        347,3,86,43,0,347,83,1,0,0,0,348,349,3,86,43,0,349,350,5,30,0,0,
        350,351,3,88,44,0,351,85,1,0,0,0,352,354,7,3,0,0,353,352,1,0,0,0,
        353,354,1,0,0,0,354,355,1,0,0,0,355,357,5,4,0,0,356,358,3,100,50,
        0,357,356,1,0,0,0,357,358,1,0,0,0,358,87,1,0,0,0,359,362,5,4,0,0,
        360,363,5,33,0,0,361,363,3,100,50,0,362,360,1,0,0,0,362,361,1,0,
        0,0,362,363,1,0,0,0,363,89,1,0,0,0,364,367,3,96,48,0,365,367,3,100,
        50,0,366,364,1,0,0,0,366,365,1,0,0,0,367,91,1,0,0,0,368,369,5,40,
        0,0,369,370,3,90,45,0,370,93,1,0,0,0,371,372,3,90,45,0,372,373,5,
        34,0,0,373,374,3,98,49,0,374,95,1,0,0,0,375,378,3,100,50,0,376,377,
        5,34,0,0,377,379,3,100,50,0,378,376,1,0,0,0,379,380,1,0,0,0,380,
        378,1,0,0,0,380,381,1,0,0,0,381,97,1,0,0,0,382,383,5,4,0,0,383,99,
        1,0,0,0,384,385,5,21,0,0,385,101,1,0,0,0,386,387,5,3,0,0,387,103,
        1,0,0,0,388,389,7,5,0,0,389,105,1,0,0,0,31,108,110,117,124,128,144,
        152,165,169,184,192,199,208,215,229,238,254,261,286,297,308,314,
        322,326,333,342,353,357,362,366,380
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
                     "'within'", "'pass'", "<INVALID>", "<INVALID>", "<INVALID>", 
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
                      "TRUE", "FALSE", "WITHIN", "PASS", "NEWLINE", "NAME", 
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
    RULE_declaration_stmt = 10
    RULE_assign_stmt = 11
    RULE_cum_assign_stmt = 12
    RULE_cum_operator = 13
    RULE_cum_assignable = 14
    RULE_assignable = 15
    RULE_retype_stmt = 16
    RULE_connect_stmt = 17
    RULE_connectable = 18
    RULE_signaldef_stmt = 19
    RULE_pindef_stmt = 20
    RULE_new_stmt = 21
    RULE_string_stmt = 22
    RULE_pass_stmt = 23
    RULE_assert_stmt = 24
    RULE_comparison = 25
    RULE_compare_op_pair = 26
    RULE_lt_arithmetic_or = 27
    RULE_gt_arithmetic_or = 28
    RULE_lt_eq_arithmetic_or = 29
    RULE_gt_eq_arithmetic_or = 30
    RULE_in_arithmetic_or = 31
    RULE_arithmetic_expression = 32
    RULE_sum = 33
    RULE_term = 34
    RULE_power = 35
    RULE_functional = 36
    RULE_bound = 37
    RULE_atom = 38
    RULE_arithmetic_group = 39
    RULE_literal_physical = 40
    RULE_bound_quantity = 41
    RULE_bilateral_quantity = 42
    RULE_quantity = 43
    RULE_bilateral_tolerance = 44
    RULE_name_or_attr = 45
    RULE_type_info = 46
    RULE_numerical_pin_ref = 47
    RULE_attr = 48
    RULE_totally_an_integer = 49
    RULE_name = 50
    RULE_string = 51
    RULE_boolean_ = 52

    ruleNames =  [ "file_input", "stmt", "simple_stmts", "simple_stmt", 
                   "compound_stmt", "blockdef", "blocktype", "block", "dep_import_stmt", 
                   "import_stmt", "declaration_stmt", "assign_stmt", "cum_assign_stmt", 
                   "cum_operator", "cum_assignable", "assignable", "retype_stmt", 
                   "connect_stmt", "connectable", "signaldef_stmt", "pindef_stmt", 
                   "new_stmt", "string_stmt", "pass_stmt", "assert_stmt", 
                   "comparison", "compare_op_pair", "lt_arithmetic_or", 
                   "gt_arithmetic_or", "lt_eq_arithmetic_or", "gt_eq_arithmetic_or", 
                   "in_arithmetic_or", "arithmetic_expression", "sum", "term", 
                   "power", "functional", "bound", "atom", "arithmetic_group", 
                   "literal_physical", "bound_quantity", "bilateral_quantity", 
                   "quantity", "bilateral_tolerance", "name_or_attr", "type_info", 
                   "numerical_pin_ref", "attr", "totally_an_integer", "name", 
                   "string", "boolean_" ]

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
    WITHIN=18
    PASS=19
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
    PLUS_OR_MINUS=30
    PLUS_SLASH_MINUS=31
    PLUS_MINUS_SIGN=32
    PERCENT=33
    DOT=34
    ELLIPSIS=35
    STAR=36
    OPEN_PAREN=37
    CLOSE_PAREN=38
    COMMA=39
    COLON=40
    SEMI_COLON=41
    POWER=42
    ASSIGN=43
    OPEN_BRACK=44
    CLOSE_BRACK=45
    OR_OP=46
    XOR=47
    AND_OP=48
    LEFT_SHIFT=49
    RIGHT_SHIFT=50
    ADD=51
    MINUS=52
    DIV=53
    IDIV=54
    NOT_OP=55
    OPEN_BRACE=56
    CLOSE_BRACE=57
    LESS_THAN=58
    GREATER_THAN=59
    EQUALS=60
    GT_EQ=61
    LT_EQ=62
    NOT_EQ_1=63
    NOT_EQ_2=64
    AT=65
    ARROW=66
    ADD_ASSIGN=67
    SUB_ASSIGN=68
    MULT_ASSIGN=69
    AT_ASSIGN=70
    DIV_ASSIGN=71
    AND_ASSIGN=72
    OR_ASSIGN=73
    XOR_ASSIGN=74
    LEFT_SHIFT_ASSIGN=75
    RIGHT_SHIFT_ASSIGN=76
    POWER_ASSIGN=77
    IDIV_ASSIGN=78
    SKIP_=79
    UNKNOWN_CHAR=80

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
            self.state = 110
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 3700680) != 0):
                self.state = 108
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [20]:
                    self.state = 106
                    self.match(AtopileParser.NEWLINE)
                    pass
                elif token in [3, 6, 7, 8, 9, 10, 12, 13, 14, 19, 21]:
                    self.state = 107
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 112
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 113
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
            self.state = 117
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 14, 19, 21]:
                self.enterOuterAlt(localctx, 1)
                self.state = 115
                self.simple_stmts()
                pass
            elif token in [6, 7, 8]:
                self.enterOuterAlt(localctx, 2)
                self.state = 116
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
            self.state = 119
            self.simple_stmt()
            self.state = 124
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 120
                    self.match(AtopileParser.SEMI_COLON)
                    self.state = 121
                    self.simple_stmt() 
                self.state = 126
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 128
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==41:
                self.state = 127
                self.match(AtopileParser.SEMI_COLON)


            self.state = 130
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


        def cum_assign_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Cum_assign_stmtContext,0)


        def connect_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Connect_stmtContext,0)


        def retype_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Retype_stmtContext,0)


        def pindef_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Pindef_stmtContext,0)


        def signaldef_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Signaldef_stmtContext,0)


        def assert_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Assert_stmtContext,0)


        def declaration_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Declaration_stmtContext,0)


        def string_stmt(self):
            return self.getTypedRuleContext(AtopileParser.String_stmtContext,0)


        def pass_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Pass_stmtContext,0)


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
            self.state = 144
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 132
                self.import_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 133
                self.dep_import_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 134
                self.assign_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 135
                self.cum_assign_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 136
                self.connect_stmt()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 137
                self.retype_stmt()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 138
                self.pindef_stmt()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 139
                self.signaldef_stmt()
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 140
                self.assert_stmt()
                pass

            elif la_ == 10:
                self.enterOuterAlt(localctx, 10)
                self.state = 141
                self.declaration_stmt()
                pass

            elif la_ == 11:
                self.enterOuterAlt(localctx, 11)
                self.state = 142
                self.string_stmt()
                pass

            elif la_ == 12:
                self.enterOuterAlt(localctx, 12)
                self.state = 143
                self.pass_stmt()
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
            self.state = 146
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
            self.state = 148
            self.blocktype()
            self.state = 149
            self.name()
            self.state = 152
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 150
                self.match(AtopileParser.FROM)
                self.state = 151
                self.name_or_attr()


            self.state = 154
            self.match(AtopileParser.COLON)
            self.state = 155
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
            self.state = 157
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
            self.state = 169
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 14, 19, 21]:
                self.enterOuterAlt(localctx, 1)
                self.state = 159
                self.simple_stmts()
                pass
            elif token in [20]:
                self.enterOuterAlt(localctx, 2)
                self.state = 160
                self.match(AtopileParser.NEWLINE)
                self.state = 161
                self.match(AtopileParser.INDENT)
                self.state = 163 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 162
                    self.stmt()
                    self.state = 165 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 2652104) != 0)):
                        break

                self.state = 167
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
            self.state = 171
            self.match(AtopileParser.IMPORT)
            self.state = 172
            self.name_or_attr()
            self.state = 173
            self.match(AtopileParser.FROM)
            self.state = 174
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
            self.state = 176
            self.match(AtopileParser.FROM)
            self.state = 177
            self.string()
            self.state = 178
            self.match(AtopileParser.IMPORT)
            self.state = 179
            self.name_or_attr()
            self.state = 184
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==39:
                self.state = 180
                self.match(AtopileParser.COMMA)
                self.state = 181
                self.name_or_attr()
                self.state = 186
                self._errHandler.sync(self)
                _la = self._input.LA(1)

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
        self.enterRule(localctx, 20, self.RULE_declaration_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 187
            self.name_or_attr()
            self.state = 188
            self.type_info()
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
        self.enterRule(localctx, 22, self.RULE_assign_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 190
            self.name_or_attr()
            self.state = 192
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==40:
                self.state = 191
                self.type_info()


            self.state = 194
            self.match(AtopileParser.ASSIGN)
            self.state = 195
            self.assignable()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Cum_assign_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def cum_operator(self):
            return self.getTypedRuleContext(AtopileParser.Cum_operatorContext,0)


        def cum_assignable(self):
            return self.getTypedRuleContext(AtopileParser.Cum_assignableContext,0)


        def type_info(self):
            return self.getTypedRuleContext(AtopileParser.Type_infoContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_cum_assign_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCum_assign_stmt" ):
                return visitor.visitCum_assign_stmt(self)
            else:
                return visitor.visitChildren(self)




    def cum_assign_stmt(self):

        localctx = AtopileParser.Cum_assign_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_cum_assign_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 197
            self.name_or_attr()
            self.state = 199
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==40:
                self.state = 198
                self.type_info()


            self.state = 201
            self.cum_operator()
            self.state = 202
            self.cum_assignable()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Cum_operatorContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ADD_ASSIGN(self):
            return self.getToken(AtopileParser.ADD_ASSIGN, 0)

        def SUB_ASSIGN(self):
            return self.getToken(AtopileParser.SUB_ASSIGN, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_cum_operator

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCum_operator" ):
                return visitor.visitCum_operator(self)
            else:
                return visitor.visitChildren(self)




    def cum_operator(self):

        localctx = AtopileParser.Cum_operatorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_cum_operator)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 204
            _la = self._input.LA(1)
            if not(_la==67 or _la==68):
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


    class Cum_assignableContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def literal_physical(self):
            return self.getTypedRuleContext(AtopileParser.Literal_physicalContext,0)


        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtopileParser.Arithmetic_expressionContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_cum_assignable

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCum_assignable" ):
                return visitor.visitCum_assignable(self)
            else:
                return visitor.visitChildren(self)




    def cum_assignable(self):

        localctx = AtopileParser.Cum_assignableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_cum_assignable)
        try:
            self.state = 208
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 206
                self.literal_physical()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 207
                self.arithmetic_expression(0)
                pass


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


        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtopileParser.Arithmetic_expressionContext,0)


        def boolean_(self):
            return self.getTypedRuleContext(AtopileParser.Boolean_Context,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_assignable

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssignable" ):
                return visitor.visitAssignable(self)
            else:
                return visitor.visitChildren(self)




    def assignable(self):

        localctx = AtopileParser.AssignableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_assignable)
        try:
            self.state = 215
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 210
                self.string()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 211
                self.new_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 212
                self.literal_physical()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 213
                self.arithmetic_expression(0)
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 214
                self.boolean_()
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
        self.enterRule(localctx, 32, self.RULE_retype_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 217
            self.name_or_attr()
            self.state = 218
            self.match(AtopileParser.ARROW)
            self.state = 219
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
        self.enterRule(localctx, 34, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 221
            self.connectable()
            self.state = 222
            self.match(AtopileParser.NOT_OP)
            self.state = 223
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
        self.enterRule(localctx, 36, self.RULE_connectable)
        try:
            self.state = 229
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 225
                self.name_or_attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 226
                self.numerical_pin_ref()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 227
                self.signaldef_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 228
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
        self.enterRule(localctx, 38, self.RULE_signaldef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 231
            self.match(AtopileParser.SIGNAL)
            self.state = 232
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


        def string(self):
            return self.getTypedRuleContext(AtopileParser.StringContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_pindef_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPindef_stmt" ):
                return visitor.visitPindef_stmt(self)
            else:
                return visitor.visitChildren(self)




    def pindef_stmt(self):

        localctx = AtopileParser.Pindef_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_pindef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 234
            self.match(AtopileParser.PIN)
            self.state = 238
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [21]:
                self.state = 235
                self.name()
                pass
            elif token in [4]:
                self.state = 236
                self.totally_an_integer()
                pass
            elif token in [3]:
                self.state = 237
                self.string()
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
        self.enterRule(localctx, 42, self.RULE_new_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 240
            self.match(AtopileParser.NEW)
            self.state = 241
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
        self.enterRule(localctx, 44, self.RULE_string_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 243
            self.string()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Pass_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def PASS(self):
            return self.getToken(AtopileParser.PASS, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_pass_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPass_stmt" ):
                return visitor.visitPass_stmt(self)
            else:
                return visitor.visitChildren(self)




    def pass_stmt(self):

        localctx = AtopileParser.Pass_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_pass_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 245
            self.match(AtopileParser.PASS)
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

        def ASSERT(self):
            return self.getToken(AtopileParser.ASSERT, 0)

        def comparison(self):
            return self.getTypedRuleContext(AtopileParser.ComparisonContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_assert_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssert_stmt" ):
                return visitor.visitAssert_stmt(self)
            else:
                return visitor.visitChildren(self)




    def assert_stmt(self):

        localctx = AtopileParser.Assert_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_assert_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 247
            self.match(AtopileParser.ASSERT)
            self.state = 248
            self.comparison()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ComparisonContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtopileParser.Arithmetic_expressionContext,0)


        def compare_op_pair(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.Compare_op_pairContext)
            else:
                return self.getTypedRuleContext(AtopileParser.Compare_op_pairContext,i)


        def getRuleIndex(self):
            return AtopileParser.RULE_comparison

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitComparison" ):
                return visitor.visitComparison(self)
            else:
                return visitor.visitChildren(self)




    def comparison(self):

        localctx = AtopileParser.ComparisonContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_comparison)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 250
            self.arithmetic_expression(0)
            self.state = 252 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 251
                self.compare_op_pair()
                self.state = 254 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 7782220156096479232) != 0)):
                    break

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Compare_op_pairContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def lt_arithmetic_or(self):
            return self.getTypedRuleContext(AtopileParser.Lt_arithmetic_orContext,0)


        def gt_arithmetic_or(self):
            return self.getTypedRuleContext(AtopileParser.Gt_arithmetic_orContext,0)


        def lt_eq_arithmetic_or(self):
            return self.getTypedRuleContext(AtopileParser.Lt_eq_arithmetic_orContext,0)


        def gt_eq_arithmetic_or(self):
            return self.getTypedRuleContext(AtopileParser.Gt_eq_arithmetic_orContext,0)


        def in_arithmetic_or(self):
            return self.getTypedRuleContext(AtopileParser.In_arithmetic_orContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_compare_op_pair

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCompare_op_pair" ):
                return visitor.visitCompare_op_pair(self)
            else:
                return visitor.visitChildren(self)




    def compare_op_pair(self):

        localctx = AtopileParser.Compare_op_pairContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_compare_op_pair)
        try:
            self.state = 261
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [58]:
                self.enterOuterAlt(localctx, 1)
                self.state = 256
                self.lt_arithmetic_or()
                pass
            elif token in [59]:
                self.enterOuterAlt(localctx, 2)
                self.state = 257
                self.gt_arithmetic_or()
                pass
            elif token in [62]:
                self.enterOuterAlt(localctx, 3)
                self.state = 258
                self.lt_eq_arithmetic_or()
                pass
            elif token in [61]:
                self.enterOuterAlt(localctx, 4)
                self.state = 259
                self.gt_eq_arithmetic_or()
                pass
            elif token in [18]:
                self.enterOuterAlt(localctx, 5)
                self.state = 260
                self.in_arithmetic_or()
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


    class Lt_arithmetic_orContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LESS_THAN(self):
            return self.getToken(AtopileParser.LESS_THAN, 0)

        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtopileParser.Arithmetic_expressionContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_lt_arithmetic_or

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLt_arithmetic_or" ):
                return visitor.visitLt_arithmetic_or(self)
            else:
                return visitor.visitChildren(self)




    def lt_arithmetic_or(self):

        localctx = AtopileParser.Lt_arithmetic_orContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_lt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 263
            self.match(AtopileParser.LESS_THAN)
            self.state = 264
            self.arithmetic_expression(0)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Gt_arithmetic_orContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def GREATER_THAN(self):
            return self.getToken(AtopileParser.GREATER_THAN, 0)

        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtopileParser.Arithmetic_expressionContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_gt_arithmetic_or

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGt_arithmetic_or" ):
                return visitor.visitGt_arithmetic_or(self)
            else:
                return visitor.visitChildren(self)




    def gt_arithmetic_or(self):

        localctx = AtopileParser.Gt_arithmetic_orContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_gt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 266
            self.match(AtopileParser.GREATER_THAN)
            self.state = 267
            self.arithmetic_expression(0)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Lt_eq_arithmetic_orContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LT_EQ(self):
            return self.getToken(AtopileParser.LT_EQ, 0)

        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtopileParser.Arithmetic_expressionContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_lt_eq_arithmetic_or

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLt_eq_arithmetic_or" ):
                return visitor.visitLt_eq_arithmetic_or(self)
            else:
                return visitor.visitChildren(self)




    def lt_eq_arithmetic_or(self):

        localctx = AtopileParser.Lt_eq_arithmetic_orContext(self, self._ctx, self.state)
        self.enterRule(localctx, 58, self.RULE_lt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 269
            self.match(AtopileParser.LT_EQ)
            self.state = 270
            self.arithmetic_expression(0)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Gt_eq_arithmetic_orContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def GT_EQ(self):
            return self.getToken(AtopileParser.GT_EQ, 0)

        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtopileParser.Arithmetic_expressionContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_gt_eq_arithmetic_or

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGt_eq_arithmetic_or" ):
                return visitor.visitGt_eq_arithmetic_or(self)
            else:
                return visitor.visitChildren(self)




    def gt_eq_arithmetic_or(self):

        localctx = AtopileParser.Gt_eq_arithmetic_orContext(self, self._ctx, self.state)
        self.enterRule(localctx, 60, self.RULE_gt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 272
            self.match(AtopileParser.GT_EQ)
            self.state = 273
            self.arithmetic_expression(0)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class In_arithmetic_orContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def WITHIN(self):
            return self.getToken(AtopileParser.WITHIN, 0)

        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtopileParser.Arithmetic_expressionContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_in_arithmetic_or

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIn_arithmetic_or" ):
                return visitor.visitIn_arithmetic_or(self)
            else:
                return visitor.visitChildren(self)




    def in_arithmetic_or(self):

        localctx = AtopileParser.In_arithmetic_orContext(self, self._ctx, self.state)
        self.enterRule(localctx, 62, self.RULE_in_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 275
            self.match(AtopileParser.WITHIN)
            self.state = 276
            self.arithmetic_expression(0)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Arithmetic_expressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def sum_(self):
            return self.getTypedRuleContext(AtopileParser.SumContext,0)


        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtopileParser.Arithmetic_expressionContext,0)


        def OR_OP(self):
            return self.getToken(AtopileParser.OR_OP, 0)

        def AND_OP(self):
            return self.getToken(AtopileParser.AND_OP, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_arithmetic_expression

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArithmetic_expression" ):
                return visitor.visitArithmetic_expression(self)
            else:
                return visitor.visitChildren(self)



    def arithmetic_expression(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = AtopileParser.Arithmetic_expressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 64
        self.enterRecursionRule(localctx, 64, self.RULE_arithmetic_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 279
            self.sum_(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 286
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,18,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtopileParser.Arithmetic_expressionContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmetic_expression)
                    self.state = 281
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 282
                    _la = self._input.LA(1)
                    if not(_la==46 or _la==48):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 283
                    self.sum_(0) 
                self.state = 288
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,18,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class SumContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def term(self):
            return self.getTypedRuleContext(AtopileParser.TermContext,0)


        def sum_(self):
            return self.getTypedRuleContext(AtopileParser.SumContext,0)


        def ADD(self):
            return self.getToken(AtopileParser.ADD, 0)

        def MINUS(self):
            return self.getToken(AtopileParser.MINUS, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_sum

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSum" ):
                return visitor.visitSum(self)
            else:
                return visitor.visitChildren(self)



    def sum_(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = AtopileParser.SumContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 66
        self.enterRecursionRule(localctx, 66, self.RULE_sum, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 290
            self.term(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 297
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,19,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtopileParser.SumContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_sum)
                    self.state = 292
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 293
                    _la = self._input.LA(1)
                    if not(_la==51 or _la==52):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 294
                    self.term(0) 
                self.state = 299
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,19,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class TermContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def power(self):
            return self.getTypedRuleContext(AtopileParser.PowerContext,0)


        def term(self):
            return self.getTypedRuleContext(AtopileParser.TermContext,0)


        def STAR(self):
            return self.getToken(AtopileParser.STAR, 0)

        def DIV(self):
            return self.getToken(AtopileParser.DIV, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_term

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTerm" ):
                return visitor.visitTerm(self)
            else:
                return visitor.visitChildren(self)



    def term(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = AtopileParser.TermContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 68
        self.enterRecursionRule(localctx, 68, self.RULE_term, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 301
            self.power()
            self._ctx.stop = self._input.LT(-1)
            self.state = 308
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,20,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtopileParser.TermContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_term)
                    self.state = 303
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 304
                    _la = self._input.LA(1)
                    if not(_la==36 or _la==53):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 305
                    self.power() 
                self.state = 310
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,20,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class PowerContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def functional(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.FunctionalContext)
            else:
                return self.getTypedRuleContext(AtopileParser.FunctionalContext,i)


        def POWER(self):
            return self.getToken(AtopileParser.POWER, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_power

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPower" ):
                return visitor.visitPower(self)
            else:
                return visitor.visitChildren(self)




    def power(self):

        localctx = AtopileParser.PowerContext(self, self._ctx, self.state)
        self.enterRule(localctx, 70, self.RULE_power)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 311
            self.functional()
            self.state = 314
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,21,self._ctx)
            if la_ == 1:
                self.state = 312
                self.match(AtopileParser.POWER)
                self.state = 313
                self.functional()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FunctionalContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def bound(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.BoundContext)
            else:
                return self.getTypedRuleContext(AtopileParser.BoundContext,i)


        def name(self):
            return self.getTypedRuleContext(AtopileParser.NameContext,0)


        def OPEN_PAREN(self):
            return self.getToken(AtopileParser.OPEN_PAREN, 0)

        def CLOSE_PAREN(self):
            return self.getToken(AtopileParser.CLOSE_PAREN, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_functional

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFunctional" ):
                return visitor.visitFunctional(self)
            else:
                return visitor.visitChildren(self)




    def functional(self):

        localctx = AtopileParser.FunctionalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 72, self.RULE_functional)
        self._la = 0 # Token type
        try:
            self.state = 326
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,23,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 316
                self.bound()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 317
                self.name()
                self.state = 318
                self.match(AtopileParser.OPEN_PAREN)
                self.state = 320 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 319
                    self.bound()
                    self.state = 322 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 6755536882106384) != 0)):
                        break

                self.state = 324
                self.match(AtopileParser.CLOSE_PAREN)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BoundContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def atom(self):
            return self.getTypedRuleContext(AtopileParser.AtomContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_bound

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBound" ):
                return visitor.visitBound(self)
            else:
                return visitor.visitChildren(self)




    def bound(self):

        localctx = AtopileParser.BoundContext(self, self._ctx, self.state)
        self.enterRule(localctx, 74, self.RULE_bound)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 328
            self.atom()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AtomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name_or_attr(self):
            return self.getTypedRuleContext(AtopileParser.Name_or_attrContext,0)


        def literal_physical(self):
            return self.getTypedRuleContext(AtopileParser.Literal_physicalContext,0)


        def arithmetic_group(self):
            return self.getTypedRuleContext(AtopileParser.Arithmetic_groupContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_atom

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAtom" ):
                return visitor.visitAtom(self)
            else:
                return visitor.visitChildren(self)




    def atom(self):

        localctx = AtopileParser.AtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 76, self.RULE_atom)
        try:
            self.state = 333
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [21]:
                self.enterOuterAlt(localctx, 1)
                self.state = 330
                self.name_or_attr()
                pass
            elif token in [4, 51, 52]:
                self.enterOuterAlt(localctx, 2)
                self.state = 331
                self.literal_physical()
                pass
            elif token in [37]:
                self.enterOuterAlt(localctx, 3)
                self.state = 332
                self.arithmetic_group()
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


    class Arithmetic_groupContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def OPEN_PAREN(self):
            return self.getToken(AtopileParser.OPEN_PAREN, 0)

        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtopileParser.Arithmetic_expressionContext,0)


        def CLOSE_PAREN(self):
            return self.getToken(AtopileParser.CLOSE_PAREN, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_arithmetic_group

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArithmetic_group" ):
                return visitor.visitArithmetic_group(self)
            else:
                return visitor.visitChildren(self)




    def arithmetic_group(self):

        localctx = AtopileParser.Arithmetic_groupContext(self, self._ctx, self.state)
        self.enterRule(localctx, 78, self.RULE_arithmetic_group)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 335
            self.match(AtopileParser.OPEN_PAREN)
            self.state = 336
            self.arithmetic_expression(0)
            self.state = 337
            self.match(AtopileParser.CLOSE_PAREN)
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


        def quantity(self):
            return self.getTypedRuleContext(AtopileParser.QuantityContext,0)


        def getRuleIndex(self):
            return AtopileParser.RULE_literal_physical

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLiteral_physical" ):
                return visitor.visitLiteral_physical(self)
            else:
                return visitor.visitChildren(self)




    def literal_physical(self):

        localctx = AtopileParser.Literal_physicalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 80, self.RULE_literal_physical)
        try:
            self.state = 342
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,25,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 339
                self.bound_quantity()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 340
                self.bilateral_quantity()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 341
                self.quantity()
                pass


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

        def quantity(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.QuantityContext)
            else:
                return self.getTypedRuleContext(AtopileParser.QuantityContext,i)


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
        self.enterRule(localctx, 82, self.RULE_bound_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 344
            self.quantity()
            self.state = 345
            self.match(AtopileParser.TO)
            self.state = 346
            self.quantity()
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

        def quantity(self):
            return self.getTypedRuleContext(AtopileParser.QuantityContext,0)


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
        self.enterRule(localctx, 84, self.RULE_bilateral_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 348
            self.quantity()
            self.state = 349
            self.match(AtopileParser.PLUS_OR_MINUS)
            self.state = 350
            self.bilateral_tolerance()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class QuantityContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self):
            return self.getToken(AtopileParser.NUMBER, 0)

        def name(self):
            return self.getTypedRuleContext(AtopileParser.NameContext,0)


        def ADD(self):
            return self.getToken(AtopileParser.ADD, 0)

        def MINUS(self):
            return self.getToken(AtopileParser.MINUS, 0)

        def getRuleIndex(self):
            return AtopileParser.RULE_quantity

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitQuantity" ):
                return visitor.visitQuantity(self)
            else:
                return visitor.visitChildren(self)




    def quantity(self):

        localctx = AtopileParser.QuantityContext(self, self._ctx, self.state)
        self.enterRule(localctx, 86, self.RULE_quantity)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 353
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==51 or _la==52:
                self.state = 352
                _la = self._input.LA(1)
                if not(_la==51 or _la==52):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()


            self.state = 355
            self.match(AtopileParser.NUMBER)
            self.state = 357
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,27,self._ctx)
            if la_ == 1:
                self.state = 356
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
        self.enterRule(localctx, 88, self.RULE_bilateral_tolerance)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 359
            self.match(AtopileParser.NUMBER)
            self.state = 362
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,28,self._ctx)
            if la_ == 1:
                self.state = 360
                self.match(AtopileParser.PERCENT)

            elif la_ == 2:
                self.state = 361
                self.name()


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
        self.enterRule(localctx, 90, self.RULE_name_or_attr)
        try:
            self.state = 366
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,29,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 364
                self.attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 365
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
        self.enterRule(localctx, 92, self.RULE_type_info)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 368
            self.match(AtopileParser.COLON)
            self.state = 369
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
        self.enterRule(localctx, 94, self.RULE_numerical_pin_ref)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 371
            self.name_or_attr()
            self.state = 372
            self.match(AtopileParser.DOT)
            self.state = 373
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
        self.enterRule(localctx, 96, self.RULE_attr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 375
            self.name()
            self.state = 378 
            self._errHandler.sync(self)
            _alt = 1
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    self.state = 376
                    self.match(AtopileParser.DOT)
                    self.state = 377
                    self.name()

                else:
                    raise NoViableAltException(self)
                self.state = 380 
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,30,self._ctx)

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
        self.enterRule(localctx, 98, self.RULE_totally_an_integer)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 382
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
        self.enterRule(localctx, 100, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 384
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
        self.enterRule(localctx, 102, self.RULE_string)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 386
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
        self.enterRule(localctx, 104, self.RULE_boolean_)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 388
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



    def sempred(self, localctx:RuleContext, ruleIndex:int, predIndex:int):
        if self._predicates == None:
            self._predicates = dict()
        self._predicates[32] = self.arithmetic_expression_sempred
        self._predicates[33] = self.sum_sempred
        self._predicates[34] = self.term_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def arithmetic_expression_sempred(self, localctx:Arithmetic_expressionContext, predIndex:int):
            if predIndex == 0:
                return self.precpred(self._ctx, 2)
         

    def sum_sempred(self, localctx:SumContext, predIndex:int):
            if predIndex == 1:
                return self.precpred(self._ctx, 2)
         

    def term_sempred(self, localctx:TermContext, predIndex:int):
            if predIndex == 2:
                return self.precpred(self._ctx, 2)
         




