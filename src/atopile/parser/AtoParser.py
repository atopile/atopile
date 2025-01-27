# Generated from AtoParser.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

if "." in __name__:
    from .AtoParserBase import AtoParserBase
else:
    from AtoParserBase import AtoParserBase

def serializedATN():
    return [
        4,1,83,413,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,2,39,7,39,
        2,40,7,40,2,41,7,41,2,42,7,42,2,43,7,43,2,44,7,44,2,45,7,45,2,46,
        7,46,2,47,7,47,2,48,7,48,2,49,7,49,2,50,7,50,2,51,7,51,2,52,7,52,
        2,53,7,53,2,54,7,54,2,55,7,55,1,0,1,0,5,0,115,8,0,10,0,12,0,118,
        9,0,1,0,1,0,1,1,1,1,3,1,124,8,1,1,2,1,2,1,2,5,2,129,8,2,10,2,12,
        2,132,9,2,1,2,3,2,135,8,2,1,2,1,2,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,
        3,1,3,1,3,1,3,1,3,1,3,3,3,152,8,3,1,4,1,4,1,5,1,5,1,5,3,5,159,8,
        5,1,5,1,5,1,5,1,6,1,6,1,6,1,7,1,7,1,8,1,8,1,8,1,8,4,8,173,8,8,11,
        8,12,8,174,1,8,1,8,3,8,179,8,8,1,9,1,9,1,9,1,9,1,9,1,10,1,10,3,10,
        188,8,10,1,10,1,10,1,10,1,10,5,10,194,8,10,10,10,12,10,197,9,10,
        1,11,1,11,1,11,1,12,1,12,3,12,204,8,12,1,12,1,12,1,12,1,13,1,13,
        3,13,211,8,13,1,13,1,13,1,13,1,14,1,14,3,14,218,8,14,1,14,1,14,1,
        14,1,15,1,15,1,16,1,16,3,16,227,8,16,1,17,1,17,1,17,1,17,1,17,3,
        17,234,8,17,1,18,1,18,1,18,1,18,1,19,1,19,1,19,1,19,1,20,1,20,1,
        20,1,20,3,20,248,8,20,1,21,1,21,1,21,1,22,1,22,1,22,1,22,3,22,257,
        8,22,1,23,1,23,1,23,1,24,1,24,1,25,1,25,1,26,1,26,1,26,1,27,1,27,
        4,27,271,8,27,11,27,12,27,272,1,28,1,28,1,28,1,28,1,28,1,28,3,28,
        281,8,28,1,29,1,29,1,29,1,30,1,30,1,30,1,31,1,31,1,31,1,32,1,32,
        1,32,1,33,1,33,1,33,1,34,1,34,1,34,1,35,1,35,1,35,1,35,1,35,1,35,
        5,35,307,8,35,10,35,12,35,310,9,35,1,36,1,36,1,36,1,36,1,36,1,36,
        5,36,318,8,36,10,36,12,36,321,9,36,1,37,1,37,1,37,1,37,1,37,1,37,
        5,37,329,8,37,10,37,12,37,332,9,37,1,38,1,38,1,38,3,38,337,8,38,
        1,39,1,39,1,39,1,39,4,39,343,8,39,11,39,12,39,344,1,39,1,39,3,39,
        349,8,39,1,40,1,40,1,41,1,41,1,41,3,41,356,8,41,1,42,1,42,1,42,1,
        42,1,43,1,43,1,43,3,43,365,8,43,1,44,1,44,1,44,1,44,1,45,1,45,1,
        45,1,45,1,46,3,46,376,8,46,1,46,1,46,3,46,380,8,46,1,47,1,47,1,47,
        3,47,385,8,47,1,48,1,48,3,48,389,8,48,1,49,1,49,1,49,1,50,1,50,1,
        50,1,50,1,51,1,51,1,51,4,51,401,8,51,11,51,12,51,402,1,52,1,52,1,
        53,1,53,1,54,1,54,1,55,1,55,1,55,0,3,70,72,74,56,0,2,4,6,8,10,12,
        14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,54,56,
        58,60,62,64,66,68,70,72,74,76,78,80,82,84,86,88,90,92,94,96,98,100,
        102,104,106,108,110,0,7,1,0,6,8,1,0,72,73,1,0,67,68,2,0,46,46,48,
        48,1,0,51,52,2,0,36,36,53,53,1,0,16,17,413,0,116,1,0,0,0,2,123,1,
        0,0,0,4,125,1,0,0,0,6,151,1,0,0,0,8,153,1,0,0,0,10,155,1,0,0,0,12,
        163,1,0,0,0,14,166,1,0,0,0,16,178,1,0,0,0,18,180,1,0,0,0,20,187,
        1,0,0,0,22,198,1,0,0,0,24,201,1,0,0,0,26,208,1,0,0,0,28,215,1,0,
        0,0,30,222,1,0,0,0,32,226,1,0,0,0,34,233,1,0,0,0,36,235,1,0,0,0,
        38,239,1,0,0,0,40,247,1,0,0,0,42,249,1,0,0,0,44,252,1,0,0,0,46,258,
        1,0,0,0,48,261,1,0,0,0,50,263,1,0,0,0,52,265,1,0,0,0,54,268,1,0,
        0,0,56,280,1,0,0,0,58,282,1,0,0,0,60,285,1,0,0,0,62,288,1,0,0,0,
        64,291,1,0,0,0,66,294,1,0,0,0,68,297,1,0,0,0,70,300,1,0,0,0,72,311,
        1,0,0,0,74,322,1,0,0,0,76,333,1,0,0,0,78,348,1,0,0,0,80,350,1,0,
        0,0,82,355,1,0,0,0,84,357,1,0,0,0,86,364,1,0,0,0,88,366,1,0,0,0,
        90,370,1,0,0,0,92,375,1,0,0,0,94,381,1,0,0,0,96,388,1,0,0,0,98,390,
        1,0,0,0,100,393,1,0,0,0,102,397,1,0,0,0,104,404,1,0,0,0,106,406,
        1,0,0,0,108,408,1,0,0,0,110,410,1,0,0,0,112,115,5,79,0,0,113,115,
        3,2,1,0,114,112,1,0,0,0,114,113,1,0,0,0,115,118,1,0,0,0,116,114,
        1,0,0,0,116,117,1,0,0,0,117,119,1,0,0,0,118,116,1,0,0,0,119,120,
        5,0,0,1,120,1,1,0,0,0,121,124,3,4,2,0,122,124,3,8,4,0,123,121,1,
        0,0,0,123,122,1,0,0,0,124,3,1,0,0,0,125,130,3,6,3,0,126,127,5,41,
        0,0,127,129,3,6,3,0,128,126,1,0,0,0,129,132,1,0,0,0,130,128,1,0,
        0,0,130,131,1,0,0,0,131,134,1,0,0,0,132,130,1,0,0,0,133,135,5,41,
        0,0,134,133,1,0,0,0,134,135,1,0,0,0,135,136,1,0,0,0,136,137,5,79,
        0,0,137,5,1,0,0,0,138,152,3,20,10,0,139,152,3,18,9,0,140,152,3,24,
        12,0,141,152,3,26,13,0,142,152,3,28,14,0,143,152,3,38,19,0,144,152,
        3,36,18,0,145,152,3,44,22,0,146,152,3,42,21,0,147,152,3,52,26,0,
        148,152,3,22,11,0,149,152,3,48,24,0,150,152,3,50,25,0,151,138,1,
        0,0,0,151,139,1,0,0,0,151,140,1,0,0,0,151,141,1,0,0,0,151,142,1,
        0,0,0,151,143,1,0,0,0,151,144,1,0,0,0,151,145,1,0,0,0,151,146,1,
        0,0,0,151,147,1,0,0,0,151,148,1,0,0,0,151,149,1,0,0,0,151,150,1,
        0,0,0,152,7,1,0,0,0,153,154,3,10,5,0,154,9,1,0,0,0,155,156,3,14,
        7,0,156,158,3,106,53,0,157,159,3,12,6,0,158,157,1,0,0,0,158,159,
        1,0,0,0,159,160,1,0,0,0,160,161,5,40,0,0,161,162,3,16,8,0,162,11,
        1,0,0,0,163,164,5,12,0,0,164,165,3,96,48,0,165,13,1,0,0,0,166,167,
        7,0,0,0,167,15,1,0,0,0,168,179,3,4,2,0,169,170,5,79,0,0,170,172,
        5,1,0,0,171,173,3,2,1,0,172,171,1,0,0,0,173,174,1,0,0,0,174,172,
        1,0,0,0,174,175,1,0,0,0,175,176,1,0,0,0,176,177,5,2,0,0,177,179,
        1,0,0,0,178,168,1,0,0,0,178,169,1,0,0,0,179,17,1,0,0,0,180,181,5,
        13,0,0,181,182,3,96,48,0,182,183,5,12,0,0,183,184,3,108,54,0,184,
        19,1,0,0,0,185,186,5,12,0,0,186,188,3,108,54,0,187,185,1,0,0,0,187,
        188,1,0,0,0,188,189,1,0,0,0,189,190,5,13,0,0,190,195,3,96,48,0,191,
        192,5,39,0,0,192,194,3,96,48,0,193,191,1,0,0,0,194,197,1,0,0,0,195,
        193,1,0,0,0,195,196,1,0,0,0,196,21,1,0,0,0,197,195,1,0,0,0,198,199,
        3,96,48,0,199,200,3,98,49,0,200,23,1,0,0,0,201,203,3,96,48,0,202,
        204,3,98,49,0,203,202,1,0,0,0,203,204,1,0,0,0,204,205,1,0,0,0,205,
        206,5,43,0,0,206,207,3,34,17,0,207,25,1,0,0,0,208,210,3,96,48,0,
        209,211,3,98,49,0,210,209,1,0,0,0,210,211,1,0,0,0,211,212,1,0,0,
        0,212,213,3,30,15,0,213,214,3,32,16,0,214,27,1,0,0,0,215,217,3,96,
        48,0,216,218,3,98,49,0,217,216,1,0,0,0,217,218,1,0,0,0,218,219,1,
        0,0,0,219,220,7,1,0,0,220,221,3,32,16,0,221,29,1,0,0,0,222,223,7,
        2,0,0,223,31,1,0,0,0,224,227,3,86,43,0,225,227,3,70,35,0,226,224,
        1,0,0,0,226,225,1,0,0,0,227,33,1,0,0,0,228,234,3,108,54,0,229,234,
        3,46,23,0,230,234,3,86,43,0,231,234,3,70,35,0,232,234,3,110,55,0,
        233,228,1,0,0,0,233,229,1,0,0,0,233,230,1,0,0,0,233,231,1,0,0,0,
        233,232,1,0,0,0,234,35,1,0,0,0,235,236,3,96,48,0,236,237,5,66,0,
        0,237,238,3,96,48,0,238,37,1,0,0,0,239,240,3,40,20,0,240,241,5,55,
        0,0,241,242,3,40,20,0,242,39,1,0,0,0,243,248,3,96,48,0,244,248,3,
        100,50,0,245,248,3,42,21,0,246,248,3,44,22,0,247,243,1,0,0,0,247,
        244,1,0,0,0,247,245,1,0,0,0,247,246,1,0,0,0,248,41,1,0,0,0,249,250,
        5,10,0,0,250,251,3,106,53,0,251,43,1,0,0,0,252,256,5,9,0,0,253,257,
        3,106,53,0,254,257,3,104,52,0,255,257,3,108,54,0,256,253,1,0,0,0,
        256,254,1,0,0,0,256,255,1,0,0,0,257,45,1,0,0,0,258,259,5,11,0,0,
        259,260,3,96,48,0,260,47,1,0,0,0,261,262,3,108,54,0,262,49,1,0,0,
        0,263,264,5,20,0,0,264,51,1,0,0,0,265,266,5,14,0,0,266,267,3,54,
        27,0,267,53,1,0,0,0,268,270,3,70,35,0,269,271,3,56,28,0,270,269,
        1,0,0,0,271,272,1,0,0,0,272,270,1,0,0,0,272,273,1,0,0,0,273,55,1,
        0,0,0,274,281,3,58,29,0,275,281,3,60,30,0,276,281,3,62,31,0,277,
        281,3,64,32,0,278,281,3,66,33,0,279,281,3,68,34,0,280,274,1,0,0,
        0,280,275,1,0,0,0,280,276,1,0,0,0,280,277,1,0,0,0,280,278,1,0,0,
        0,280,279,1,0,0,0,281,57,1,0,0,0,282,283,5,58,0,0,283,284,3,70,35,
        0,284,59,1,0,0,0,285,286,5,59,0,0,286,287,3,70,35,0,287,61,1,0,0,
        0,288,289,5,62,0,0,289,290,3,70,35,0,290,63,1,0,0,0,291,292,5,61,
        0,0,292,293,3,70,35,0,293,65,1,0,0,0,294,295,5,18,0,0,295,296,3,
        70,35,0,296,67,1,0,0,0,297,298,5,19,0,0,298,299,3,70,35,0,299,69,
        1,0,0,0,300,301,6,35,-1,0,301,302,3,72,36,0,302,308,1,0,0,0,303,
        304,10,2,0,0,304,305,7,3,0,0,305,307,3,72,36,0,306,303,1,0,0,0,307,
        310,1,0,0,0,308,306,1,0,0,0,308,309,1,0,0,0,309,71,1,0,0,0,310,308,
        1,0,0,0,311,312,6,36,-1,0,312,313,3,74,37,0,313,319,1,0,0,0,314,
        315,10,2,0,0,315,316,7,4,0,0,316,318,3,74,37,0,317,314,1,0,0,0,318,
        321,1,0,0,0,319,317,1,0,0,0,319,320,1,0,0,0,320,73,1,0,0,0,321,319,
        1,0,0,0,322,323,6,37,-1,0,323,324,3,76,38,0,324,330,1,0,0,0,325,
        326,10,2,0,0,326,327,7,5,0,0,327,329,3,76,38,0,328,325,1,0,0,0,329,
        332,1,0,0,0,330,328,1,0,0,0,330,331,1,0,0,0,331,75,1,0,0,0,332,330,
        1,0,0,0,333,336,3,78,39,0,334,335,5,42,0,0,335,337,3,78,39,0,336,
        334,1,0,0,0,336,337,1,0,0,0,337,77,1,0,0,0,338,349,3,80,40,0,339,
        340,3,106,53,0,340,342,5,37,0,0,341,343,3,80,40,0,342,341,1,0,0,
        0,343,344,1,0,0,0,344,342,1,0,0,0,344,345,1,0,0,0,345,346,1,0,0,
        0,346,347,5,38,0,0,347,349,1,0,0,0,348,338,1,0,0,0,348,339,1,0,0,
        0,349,79,1,0,0,0,350,351,3,82,41,0,351,81,1,0,0,0,352,356,3,96,48,
        0,353,356,3,86,43,0,354,356,3,84,42,0,355,352,1,0,0,0,355,353,1,
        0,0,0,355,354,1,0,0,0,356,83,1,0,0,0,357,358,5,37,0,0,358,359,3,
        70,35,0,359,360,5,38,0,0,360,85,1,0,0,0,361,365,3,88,44,0,362,365,
        3,90,45,0,363,365,3,92,46,0,364,361,1,0,0,0,364,362,1,0,0,0,364,
        363,1,0,0,0,365,87,1,0,0,0,366,367,3,92,46,0,367,368,5,15,0,0,368,
        369,3,92,46,0,369,89,1,0,0,0,370,371,3,92,46,0,371,372,5,30,0,0,
        372,373,3,94,47,0,373,91,1,0,0,0,374,376,7,4,0,0,375,374,1,0,0,0,
        375,376,1,0,0,0,376,377,1,0,0,0,377,379,5,4,0,0,378,380,3,106,53,
        0,379,378,1,0,0,0,379,380,1,0,0,0,380,93,1,0,0,0,381,384,5,4,0,0,
        382,385,5,33,0,0,383,385,3,106,53,0,384,382,1,0,0,0,384,383,1,0,
        0,0,384,385,1,0,0,0,385,95,1,0,0,0,386,389,3,102,51,0,387,389,3,
        106,53,0,388,386,1,0,0,0,388,387,1,0,0,0,389,97,1,0,0,0,390,391,
        5,40,0,0,391,392,3,96,48,0,392,99,1,0,0,0,393,394,3,96,48,0,394,
        395,5,34,0,0,395,396,3,104,52,0,396,101,1,0,0,0,397,400,3,106,53,
        0,398,399,5,34,0,0,399,401,3,106,53,0,400,398,1,0,0,0,401,402,1,
        0,0,0,402,400,1,0,0,0,402,403,1,0,0,0,403,103,1,0,0,0,404,405,5,
        4,0,0,405,105,1,0,0,0,406,407,5,21,0,0,407,107,1,0,0,0,408,409,5,
        3,0,0,409,109,1,0,0,0,410,411,7,6,0,0,411,111,1,0,0,0,33,114,116,
        123,130,134,151,158,174,178,187,195,203,210,217,226,233,247,256,
        272,280,308,319,330,336,344,348,355,364,375,379,384,388,402
    ]

class AtoParser ( AtoParserBase ):

    grammarFileName = "AtoParser.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "'component'", "'module'", 
                     "'interface'", "'pin'", "'signal'", "'new'", "'from'", 
                     "'import'", "'assert'", "'to'", "'True'", "'False'", 
                     "'within'", "'is'", "'pass'", "<INVALID>", "<INVALID>", 
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
                      "TRUE", "FALSE", "WITHIN", "IS", "PASS", "NAME", "STRING_LITERAL", 
                      "BYTES_LITERAL", "DECIMAL_INTEGER", "OCT_INTEGER", 
                      "HEX_INTEGER", "BIN_INTEGER", "FLOAT_NUMBER", "IMAG_NUMBER", 
                      "PLUS_OR_MINUS", "PLUS_SLASH_MINUS", "PLUS_MINUS_SIGN", 
                      "PERCENT", "DOT", "ELLIPSIS", "STAR", "OPEN_PAREN", 
                      "CLOSE_PAREN", "COMMA", "COLON", "SEMI_COLON", "POWER", 
                      "ASSIGN", "OPEN_BRACK", "CLOSE_BRACK", "OR_OP", "XOR", 
                      "AND_OP", "LEFT_SHIFT", "RIGHT_SHIFT", "ADD", "MINUS", 
                      "DIV", "IDIV", "NOT_OP", "OPEN_BRACE", "CLOSE_BRACE", 
                      "LESS_THAN", "GREATER_THAN", "EQUALS", "GT_EQ", "LT_EQ", 
                      "NOT_EQ_1", "NOT_EQ_2", "AT", "ARROW", "ADD_ASSIGN", 
                      "SUB_ASSIGN", "MULT_ASSIGN", "AT_ASSIGN", "DIV_ASSIGN", 
                      "AND_ASSIGN", "OR_ASSIGN", "XOR_ASSIGN", "LEFT_SHIFT_ASSIGN", 
                      "RIGHT_SHIFT_ASSIGN", "POWER_ASSIGN", "IDIV_ASSIGN", 
                      "NEWLINE", "COMMENT", "WS", "EXPLICIT_LINE_JOINING", 
                      "ERRORTOKEN" ]

    RULE_file_input = 0
    RULE_stmt = 1
    RULE_simple_stmts = 2
    RULE_simple_stmt = 3
    RULE_compound_stmt = 4
    RULE_blockdef = 5
    RULE_blockdef_super = 6
    RULE_blocktype = 7
    RULE_block = 8
    RULE_dep_import_stmt = 9
    RULE_import_stmt = 10
    RULE_declaration_stmt = 11
    RULE_assign_stmt = 12
    RULE_cum_assign_stmt = 13
    RULE_set_assign_stmt = 14
    RULE_cum_operator = 15
    RULE_cum_assignable = 16
    RULE_assignable = 17
    RULE_retype_stmt = 18
    RULE_connect_stmt = 19
    RULE_connectable = 20
    RULE_signaldef_stmt = 21
    RULE_pindef_stmt = 22
    RULE_new_stmt = 23
    RULE_string_stmt = 24
    RULE_pass_stmt = 25
    RULE_assert_stmt = 26
    RULE_comparison = 27
    RULE_compare_op_pair = 28
    RULE_lt_arithmetic_or = 29
    RULE_gt_arithmetic_or = 30
    RULE_lt_eq_arithmetic_or = 31
    RULE_gt_eq_arithmetic_or = 32
    RULE_in_arithmetic_or = 33
    RULE_is_arithmetic_or = 34
    RULE_arithmetic_expression = 35
    RULE_sum = 36
    RULE_term = 37
    RULE_power = 38
    RULE_functional = 39
    RULE_bound = 40
    RULE_atom = 41
    RULE_arithmetic_group = 42
    RULE_literal_physical = 43
    RULE_bound_quantity = 44
    RULE_bilateral_quantity = 45
    RULE_quantity = 46
    RULE_bilateral_tolerance = 47
    RULE_name_or_attr = 48
    RULE_type_info = 49
    RULE_numerical_pin_ref = 50
    RULE_attr = 51
    RULE_totally_an_integer = 52
    RULE_name = 53
    RULE_string = 54
    RULE_boolean_ = 55

    ruleNames =  [ "file_input", "stmt", "simple_stmts", "simple_stmt", 
                   "compound_stmt", "blockdef", "blockdef_super", "blocktype", 
                   "block", "dep_import_stmt", "import_stmt", "declaration_stmt", 
                   "assign_stmt", "cum_assign_stmt", "set_assign_stmt", 
                   "cum_operator", "cum_assignable", "assignable", "retype_stmt", 
                   "connect_stmt", "connectable", "signaldef_stmt", "pindef_stmt", 
                   "new_stmt", "string_stmt", "pass_stmt", "assert_stmt", 
                   "comparison", "compare_op_pair", "lt_arithmetic_or", 
                   "gt_arithmetic_or", "lt_eq_arithmetic_or", "gt_eq_arithmetic_or", 
                   "in_arithmetic_or", "is_arithmetic_or", "arithmetic_expression", 
                   "sum", "term", "power", "functional", "bound", "atom", 
                   "arithmetic_group", "literal_physical", "bound_quantity", 
                   "bilateral_quantity", "quantity", "bilateral_tolerance", 
                   "name_or_attr", "type_info", "numerical_pin_ref", "attr", 
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
    NEW=11
    FROM=12
    IMPORT=13
    ASSERT=14
    TO=15
    TRUE=16
    FALSE=17
    WITHIN=18
    IS=19
    PASS=20
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
    NEWLINE=79
    COMMENT=80
    WS=81
    EXPLICIT_LINE_JOINING=82
    ERRORTOKEN=83

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class File_inputContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EOF(self):
            return self.getToken(AtoParser.EOF, 0)

        def NEWLINE(self, i:int=None):
            if i is None:
                return self.getTokens(AtoParser.NEWLINE)
            else:
                return self.getToken(AtoParser.NEWLINE, i)

        def stmt(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtoParser.StmtContext)
            else:
                return self.getTypedRuleContext(AtoParser.StmtContext,i)


        def getRuleIndex(self):
            return AtoParser.RULE_file_input

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFile_input" ):
                return visitor.visitFile_input(self)
            else:
                return visitor.visitChildren(self)




    def file_input(self):

        localctx = AtoParser.File_inputContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_file_input)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 116
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 3176392) != 0) or _la==79:
                self.state = 114
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [79]:
                    self.state = 112
                    self.match(AtoParser.NEWLINE)
                    pass
                elif token in [3, 6, 7, 8, 9, 10, 12, 13, 14, 20, 21]:
                    self.state = 113
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 118
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 119
            self.match(AtoParser.EOF)
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
            return self.getTypedRuleContext(AtoParser.Simple_stmtsContext,0)


        def compound_stmt(self):
            return self.getTypedRuleContext(AtoParser.Compound_stmtContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStmt" ):
                return visitor.visitStmt(self)
            else:
                return visitor.visitChildren(self)




    def stmt(self):

        localctx = AtoParser.StmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_stmt)
        try:
            self.state = 123
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 14, 20, 21]:
                self.enterOuterAlt(localctx, 1)
                self.state = 121
                self.simple_stmts()
                pass
            elif token in [6, 7, 8]:
                self.enterOuterAlt(localctx, 2)
                self.state = 122
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
                return self.getTypedRuleContexts(AtoParser.Simple_stmtContext)
            else:
                return self.getTypedRuleContext(AtoParser.Simple_stmtContext,i)


        def NEWLINE(self):
            return self.getToken(AtoParser.NEWLINE, 0)

        def SEMI_COLON(self, i:int=None):
            if i is None:
                return self.getTokens(AtoParser.SEMI_COLON)
            else:
                return self.getToken(AtoParser.SEMI_COLON, i)

        def getRuleIndex(self):
            return AtoParser.RULE_simple_stmts

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSimple_stmts" ):
                return visitor.visitSimple_stmts(self)
            else:
                return visitor.visitChildren(self)




    def simple_stmts(self):

        localctx = AtoParser.Simple_stmtsContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_simple_stmts)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 125
            self.simple_stmt()
            self.state = 130
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 126
                    self.match(AtoParser.SEMI_COLON)
                    self.state = 127
                    self.simple_stmt() 
                self.state = 132
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 134
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==41:
                self.state = 133
                self.match(AtoParser.SEMI_COLON)


            self.state = 136
            self.match(AtoParser.NEWLINE)
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
            return self.getTypedRuleContext(AtoParser.Import_stmtContext,0)


        def dep_import_stmt(self):
            return self.getTypedRuleContext(AtoParser.Dep_import_stmtContext,0)


        def assign_stmt(self):
            return self.getTypedRuleContext(AtoParser.Assign_stmtContext,0)


        def cum_assign_stmt(self):
            return self.getTypedRuleContext(AtoParser.Cum_assign_stmtContext,0)


        def set_assign_stmt(self):
            return self.getTypedRuleContext(AtoParser.Set_assign_stmtContext,0)


        def connect_stmt(self):
            return self.getTypedRuleContext(AtoParser.Connect_stmtContext,0)


        def retype_stmt(self):
            return self.getTypedRuleContext(AtoParser.Retype_stmtContext,0)


        def pindef_stmt(self):
            return self.getTypedRuleContext(AtoParser.Pindef_stmtContext,0)


        def signaldef_stmt(self):
            return self.getTypedRuleContext(AtoParser.Signaldef_stmtContext,0)


        def assert_stmt(self):
            return self.getTypedRuleContext(AtoParser.Assert_stmtContext,0)


        def declaration_stmt(self):
            return self.getTypedRuleContext(AtoParser.Declaration_stmtContext,0)


        def string_stmt(self):
            return self.getTypedRuleContext(AtoParser.String_stmtContext,0)


        def pass_stmt(self):
            return self.getTypedRuleContext(AtoParser.Pass_stmtContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_simple_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSimple_stmt" ):
                return visitor.visitSimple_stmt(self)
            else:
                return visitor.visitChildren(self)




    def simple_stmt(self):

        localctx = AtoParser.Simple_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_simple_stmt)
        try:
            self.state = 151
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 138
                self.import_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 139
                self.dep_import_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 140
                self.assign_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 141
                self.cum_assign_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 142
                self.set_assign_stmt()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 143
                self.connect_stmt()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 144
                self.retype_stmt()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 145
                self.pindef_stmt()
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 146
                self.signaldef_stmt()
                pass

            elif la_ == 10:
                self.enterOuterAlt(localctx, 10)
                self.state = 147
                self.assert_stmt()
                pass

            elif la_ == 11:
                self.enterOuterAlt(localctx, 11)
                self.state = 148
                self.declaration_stmt()
                pass

            elif la_ == 12:
                self.enterOuterAlt(localctx, 12)
                self.state = 149
                self.string_stmt()
                pass

            elif la_ == 13:
                self.enterOuterAlt(localctx, 13)
                self.state = 150
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
            return self.getTypedRuleContext(AtoParser.BlockdefContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_compound_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCompound_stmt" ):
                return visitor.visitCompound_stmt(self)
            else:
                return visitor.visitChildren(self)




    def compound_stmt(self):

        localctx = AtoParser.Compound_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_compound_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 153
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
            return self.getTypedRuleContext(AtoParser.BlocktypeContext,0)


        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def COLON(self):
            return self.getToken(AtoParser.COLON, 0)

        def block(self):
            return self.getTypedRuleContext(AtoParser.BlockContext,0)


        def blockdef_super(self):
            return self.getTypedRuleContext(AtoParser.Blockdef_superContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_blockdef

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBlockdef" ):
                return visitor.visitBlockdef(self)
            else:
                return visitor.visitChildren(self)




    def blockdef(self):

        localctx = AtoParser.BlockdefContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_blockdef)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 155
            self.blocktype()
            self.state = 156
            self.name()
            self.state = 158
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 157
                self.blockdef_super()


            self.state = 160
            self.match(AtoParser.COLON)
            self.state = 161
            self.block()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Blockdef_superContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def FROM(self):
            return self.getToken(AtoParser.FROM, 0)

        def name_or_attr(self):
            return self.getTypedRuleContext(AtoParser.Name_or_attrContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_blockdef_super

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBlockdef_super" ):
                return visitor.visitBlockdef_super(self)
            else:
                return visitor.visitChildren(self)




    def blockdef_super(self):

        localctx = AtoParser.Blockdef_superContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_blockdef_super)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 163
            self.match(AtoParser.FROM)
            self.state = 164
            self.name_or_attr()
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
            return self.getToken(AtoParser.COMPONENT, 0)

        def MODULE(self):
            return self.getToken(AtoParser.MODULE, 0)

        def INTERFACE(self):
            return self.getToken(AtoParser.INTERFACE, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_blocktype

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBlocktype" ):
                return visitor.visitBlocktype(self)
            else:
                return visitor.visitChildren(self)




    def blocktype(self):

        localctx = AtoParser.BlocktypeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_blocktype)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 166
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
            return self.getTypedRuleContext(AtoParser.Simple_stmtsContext,0)


        def NEWLINE(self):
            return self.getToken(AtoParser.NEWLINE, 0)

        def INDENT(self):
            return self.getToken(AtoParser.INDENT, 0)

        def DEDENT(self):
            return self.getToken(AtoParser.DEDENT, 0)

        def stmt(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtoParser.StmtContext)
            else:
                return self.getTypedRuleContext(AtoParser.StmtContext,i)


        def getRuleIndex(self):
            return AtoParser.RULE_block

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBlock" ):
                return visitor.visitBlock(self)
            else:
                return visitor.visitChildren(self)




    def block(self):

        localctx = AtoParser.BlockContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_block)
        self._la = 0 # Token type
        try:
            self.state = 178
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 14, 20, 21]:
                self.enterOuterAlt(localctx, 1)
                self.state = 168
                self.simple_stmts()
                pass
            elif token in [79]:
                self.enterOuterAlt(localctx, 2)
                self.state = 169
                self.match(AtoParser.NEWLINE)
                self.state = 170
                self.match(AtoParser.INDENT)
                self.state = 172 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 171
                    self.stmt()
                    self.state = 174 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 3176392) != 0)):
                        break

                self.state = 176
                self.match(AtoParser.DEDENT)
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
            return self.getToken(AtoParser.IMPORT, 0)

        def name_or_attr(self):
            return self.getTypedRuleContext(AtoParser.Name_or_attrContext,0)


        def FROM(self):
            return self.getToken(AtoParser.FROM, 0)

        def string(self):
            return self.getTypedRuleContext(AtoParser.StringContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_dep_import_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDep_import_stmt" ):
                return visitor.visitDep_import_stmt(self)
            else:
                return visitor.visitChildren(self)




    def dep_import_stmt(self):

        localctx = AtoParser.Dep_import_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_dep_import_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 180
            self.match(AtoParser.IMPORT)
            self.state = 181
            self.name_or_attr()
            self.state = 182
            self.match(AtoParser.FROM)
            self.state = 183
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

        def IMPORT(self):
            return self.getToken(AtoParser.IMPORT, 0)

        def name_or_attr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtoParser.Name_or_attrContext)
            else:
                return self.getTypedRuleContext(AtoParser.Name_or_attrContext,i)


        def FROM(self):
            return self.getToken(AtoParser.FROM, 0)

        def string(self):
            return self.getTypedRuleContext(AtoParser.StringContext,0)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(AtoParser.COMMA)
            else:
                return self.getToken(AtoParser.COMMA, i)

        def getRuleIndex(self):
            return AtoParser.RULE_import_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitImport_stmt" ):
                return visitor.visitImport_stmt(self)
            else:
                return visitor.visitChildren(self)




    def import_stmt(self):

        localctx = AtoParser.Import_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_import_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 187
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 185
                self.match(AtoParser.FROM)
                self.state = 186
                self.string()


            self.state = 189
            self.match(AtoParser.IMPORT)
            self.state = 190
            self.name_or_attr()
            self.state = 195
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==39:
                self.state = 191
                self.match(AtoParser.COMMA)
                self.state = 192
                self.name_or_attr()
                self.state = 197
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
            return self.getTypedRuleContext(AtoParser.Name_or_attrContext,0)


        def type_info(self):
            return self.getTypedRuleContext(AtoParser.Type_infoContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_declaration_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDeclaration_stmt" ):
                return visitor.visitDeclaration_stmt(self)
            else:
                return visitor.visitChildren(self)




    def declaration_stmt(self):

        localctx = AtoParser.Declaration_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_declaration_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 198
            self.name_or_attr()
            self.state = 199
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
            return self.getTypedRuleContext(AtoParser.Name_or_attrContext,0)


        def ASSIGN(self):
            return self.getToken(AtoParser.ASSIGN, 0)

        def assignable(self):
            return self.getTypedRuleContext(AtoParser.AssignableContext,0)


        def type_info(self):
            return self.getTypedRuleContext(AtoParser.Type_infoContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_assign_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssign_stmt" ):
                return visitor.visitAssign_stmt(self)
            else:
                return visitor.visitChildren(self)




    def assign_stmt(self):

        localctx = AtoParser.Assign_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_assign_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 201
            self.name_or_attr()
            self.state = 203
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==40:
                self.state = 202
                self.type_info()


            self.state = 205
            self.match(AtoParser.ASSIGN)
            self.state = 206
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
            return self.getTypedRuleContext(AtoParser.Name_or_attrContext,0)


        def cum_operator(self):
            return self.getTypedRuleContext(AtoParser.Cum_operatorContext,0)


        def cum_assignable(self):
            return self.getTypedRuleContext(AtoParser.Cum_assignableContext,0)


        def type_info(self):
            return self.getTypedRuleContext(AtoParser.Type_infoContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_cum_assign_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCum_assign_stmt" ):
                return visitor.visitCum_assign_stmt(self)
            else:
                return visitor.visitChildren(self)




    def cum_assign_stmt(self):

        localctx = AtoParser.Cum_assign_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_cum_assign_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 208
            self.name_or_attr()
            self.state = 210
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==40:
                self.state = 209
                self.type_info()


            self.state = 212
            self.cum_operator()
            self.state = 213
            self.cum_assignable()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Set_assign_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name_or_attr(self):
            return self.getTypedRuleContext(AtoParser.Name_or_attrContext,0)


        def cum_assignable(self):
            return self.getTypedRuleContext(AtoParser.Cum_assignableContext,0)


        def OR_ASSIGN(self):
            return self.getToken(AtoParser.OR_ASSIGN, 0)

        def AND_ASSIGN(self):
            return self.getToken(AtoParser.AND_ASSIGN, 0)

        def type_info(self):
            return self.getTypedRuleContext(AtoParser.Type_infoContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_set_assign_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSet_assign_stmt" ):
                return visitor.visitSet_assign_stmt(self)
            else:
                return visitor.visitChildren(self)




    def set_assign_stmt(self):

        localctx = AtoParser.Set_assign_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_set_assign_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 215
            self.name_or_attr()
            self.state = 217
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==40:
                self.state = 216
                self.type_info()


            self.state = 219
            _la = self._input.LA(1)
            if not(_la==72 or _la==73):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 220
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
            return self.getToken(AtoParser.ADD_ASSIGN, 0)

        def SUB_ASSIGN(self):
            return self.getToken(AtoParser.SUB_ASSIGN, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_cum_operator

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCum_operator" ):
                return visitor.visitCum_operator(self)
            else:
                return visitor.visitChildren(self)




    def cum_operator(self):

        localctx = AtoParser.Cum_operatorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_cum_operator)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 222
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
            return self.getTypedRuleContext(AtoParser.Literal_physicalContext,0)


        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtoParser.Arithmetic_expressionContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_cum_assignable

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCum_assignable" ):
                return visitor.visitCum_assignable(self)
            else:
                return visitor.visitChildren(self)




    def cum_assignable(self):

        localctx = AtoParser.Cum_assignableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_cum_assignable)
        try:
            self.state = 226
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 224
                self.literal_physical()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 225
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
            return self.getTypedRuleContext(AtoParser.StringContext,0)


        def new_stmt(self):
            return self.getTypedRuleContext(AtoParser.New_stmtContext,0)


        def literal_physical(self):
            return self.getTypedRuleContext(AtoParser.Literal_physicalContext,0)


        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtoParser.Arithmetic_expressionContext,0)


        def boolean_(self):
            return self.getTypedRuleContext(AtoParser.Boolean_Context,0)


        def getRuleIndex(self):
            return AtoParser.RULE_assignable

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssignable" ):
                return visitor.visitAssignable(self)
            else:
                return visitor.visitChildren(self)




    def assignable(self):

        localctx = AtoParser.AssignableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_assignable)
        try:
            self.state = 233
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,15,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 228
                self.string()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 229
                self.new_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 230
                self.literal_physical()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 231
                self.arithmetic_expression(0)
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 232
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
                return self.getTypedRuleContexts(AtoParser.Name_or_attrContext)
            else:
                return self.getTypedRuleContext(AtoParser.Name_or_attrContext,i)


        def ARROW(self):
            return self.getToken(AtoParser.ARROW, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_retype_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRetype_stmt" ):
                return visitor.visitRetype_stmt(self)
            else:
                return visitor.visitChildren(self)




    def retype_stmt(self):

        localctx = AtoParser.Retype_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_retype_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 235
            self.name_or_attr()
            self.state = 236
            self.match(AtoParser.ARROW)
            self.state = 237
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
                return self.getTypedRuleContexts(AtoParser.ConnectableContext)
            else:
                return self.getTypedRuleContext(AtoParser.ConnectableContext,i)


        def NOT_OP(self):
            return self.getToken(AtoParser.NOT_OP, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_connect_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConnect_stmt" ):
                return visitor.visitConnect_stmt(self)
            else:
                return visitor.visitChildren(self)




    def connect_stmt(self):

        localctx = AtoParser.Connect_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 239
            self.connectable()
            self.state = 240
            self.match(AtoParser.NOT_OP)
            self.state = 241
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
            return self.getTypedRuleContext(AtoParser.Name_or_attrContext,0)


        def numerical_pin_ref(self):
            return self.getTypedRuleContext(AtoParser.Numerical_pin_refContext,0)


        def signaldef_stmt(self):
            return self.getTypedRuleContext(AtoParser.Signaldef_stmtContext,0)


        def pindef_stmt(self):
            return self.getTypedRuleContext(AtoParser.Pindef_stmtContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_connectable

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConnectable" ):
                return visitor.visitConnectable(self)
            else:
                return visitor.visitChildren(self)




    def connectable(self):

        localctx = AtoParser.ConnectableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_connectable)
        try:
            self.state = 247
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,16,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 243
                self.name_or_attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 244
                self.numerical_pin_ref()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 245
                self.signaldef_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 246
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
            return self.getToken(AtoParser.SIGNAL, 0)

        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_signaldef_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSignaldef_stmt" ):
                return visitor.visitSignaldef_stmt(self)
            else:
                return visitor.visitChildren(self)




    def signaldef_stmt(self):

        localctx = AtoParser.Signaldef_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_signaldef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 249
            self.match(AtoParser.SIGNAL)
            self.state = 250
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
            return self.getToken(AtoParser.PIN, 0)

        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def totally_an_integer(self):
            return self.getTypedRuleContext(AtoParser.Totally_an_integerContext,0)


        def string(self):
            return self.getTypedRuleContext(AtoParser.StringContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_pindef_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPindef_stmt" ):
                return visitor.visitPindef_stmt(self)
            else:
                return visitor.visitChildren(self)




    def pindef_stmt(self):

        localctx = AtoParser.Pindef_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_pindef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 252
            self.match(AtoParser.PIN)
            self.state = 256
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [21]:
                self.state = 253
                self.name()
                pass
            elif token in [4]:
                self.state = 254
                self.totally_an_integer()
                pass
            elif token in [3]:
                self.state = 255
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
            return self.getToken(AtoParser.NEW, 0)

        def name_or_attr(self):
            return self.getTypedRuleContext(AtoParser.Name_or_attrContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_new_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNew_stmt" ):
                return visitor.visitNew_stmt(self)
            else:
                return visitor.visitChildren(self)




    def new_stmt(self):

        localctx = AtoParser.New_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_new_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 258
            self.match(AtoParser.NEW)
            self.state = 259
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
            return self.getTypedRuleContext(AtoParser.StringContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_string_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitString_stmt" ):
                return visitor.visitString_stmt(self)
            else:
                return visitor.visitChildren(self)




    def string_stmt(self):

        localctx = AtoParser.String_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_string_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 261
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
            return self.getToken(AtoParser.PASS, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_pass_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPass_stmt" ):
                return visitor.visitPass_stmt(self)
            else:
                return visitor.visitChildren(self)




    def pass_stmt(self):

        localctx = AtoParser.Pass_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_pass_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 263
            self.match(AtoParser.PASS)
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
            return self.getToken(AtoParser.ASSERT, 0)

        def comparison(self):
            return self.getTypedRuleContext(AtoParser.ComparisonContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_assert_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssert_stmt" ):
                return visitor.visitAssert_stmt(self)
            else:
                return visitor.visitChildren(self)




    def assert_stmt(self):

        localctx = AtoParser.Assert_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_assert_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 265
            self.match(AtoParser.ASSERT)
            self.state = 266
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
            return self.getTypedRuleContext(AtoParser.Arithmetic_expressionContext,0)


        def compare_op_pair(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtoParser.Compare_op_pairContext)
            else:
                return self.getTypedRuleContext(AtoParser.Compare_op_pairContext,i)


        def getRuleIndex(self):
            return AtoParser.RULE_comparison

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitComparison" ):
                return visitor.visitComparison(self)
            else:
                return visitor.visitChildren(self)




    def comparison(self):

        localctx = AtoParser.ComparisonContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_comparison)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 268
            self.arithmetic_expression(0)
            self.state = 270 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 269
                self.compare_op_pair()
                self.state = 272 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 7782220156097003520) != 0)):
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
            return self.getTypedRuleContext(AtoParser.Lt_arithmetic_orContext,0)


        def gt_arithmetic_or(self):
            return self.getTypedRuleContext(AtoParser.Gt_arithmetic_orContext,0)


        def lt_eq_arithmetic_or(self):
            return self.getTypedRuleContext(AtoParser.Lt_eq_arithmetic_orContext,0)


        def gt_eq_arithmetic_or(self):
            return self.getTypedRuleContext(AtoParser.Gt_eq_arithmetic_orContext,0)


        def in_arithmetic_or(self):
            return self.getTypedRuleContext(AtoParser.In_arithmetic_orContext,0)


        def is_arithmetic_or(self):
            return self.getTypedRuleContext(AtoParser.Is_arithmetic_orContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_compare_op_pair

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCompare_op_pair" ):
                return visitor.visitCompare_op_pair(self)
            else:
                return visitor.visitChildren(self)




    def compare_op_pair(self):

        localctx = AtoParser.Compare_op_pairContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_compare_op_pair)
        try:
            self.state = 280
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [58]:
                self.enterOuterAlt(localctx, 1)
                self.state = 274
                self.lt_arithmetic_or()
                pass
            elif token in [59]:
                self.enterOuterAlt(localctx, 2)
                self.state = 275
                self.gt_arithmetic_or()
                pass
            elif token in [62]:
                self.enterOuterAlt(localctx, 3)
                self.state = 276
                self.lt_eq_arithmetic_or()
                pass
            elif token in [61]:
                self.enterOuterAlt(localctx, 4)
                self.state = 277
                self.gt_eq_arithmetic_or()
                pass
            elif token in [18]:
                self.enterOuterAlt(localctx, 5)
                self.state = 278
                self.in_arithmetic_or()
                pass
            elif token in [19]:
                self.enterOuterAlt(localctx, 6)
                self.state = 279
                self.is_arithmetic_or()
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
            return self.getToken(AtoParser.LESS_THAN, 0)

        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtoParser.Arithmetic_expressionContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_lt_arithmetic_or

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLt_arithmetic_or" ):
                return visitor.visitLt_arithmetic_or(self)
            else:
                return visitor.visitChildren(self)




    def lt_arithmetic_or(self):

        localctx = AtoParser.Lt_arithmetic_orContext(self, self._ctx, self.state)
        self.enterRule(localctx, 58, self.RULE_lt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 282
            self.match(AtoParser.LESS_THAN)
            self.state = 283
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
            return self.getToken(AtoParser.GREATER_THAN, 0)

        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtoParser.Arithmetic_expressionContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_gt_arithmetic_or

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGt_arithmetic_or" ):
                return visitor.visitGt_arithmetic_or(self)
            else:
                return visitor.visitChildren(self)




    def gt_arithmetic_or(self):

        localctx = AtoParser.Gt_arithmetic_orContext(self, self._ctx, self.state)
        self.enterRule(localctx, 60, self.RULE_gt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 285
            self.match(AtoParser.GREATER_THAN)
            self.state = 286
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
            return self.getToken(AtoParser.LT_EQ, 0)

        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtoParser.Arithmetic_expressionContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_lt_eq_arithmetic_or

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLt_eq_arithmetic_or" ):
                return visitor.visitLt_eq_arithmetic_or(self)
            else:
                return visitor.visitChildren(self)




    def lt_eq_arithmetic_or(self):

        localctx = AtoParser.Lt_eq_arithmetic_orContext(self, self._ctx, self.state)
        self.enterRule(localctx, 62, self.RULE_lt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 288
            self.match(AtoParser.LT_EQ)
            self.state = 289
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
            return self.getToken(AtoParser.GT_EQ, 0)

        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtoParser.Arithmetic_expressionContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_gt_eq_arithmetic_or

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGt_eq_arithmetic_or" ):
                return visitor.visitGt_eq_arithmetic_or(self)
            else:
                return visitor.visitChildren(self)




    def gt_eq_arithmetic_or(self):

        localctx = AtoParser.Gt_eq_arithmetic_orContext(self, self._ctx, self.state)
        self.enterRule(localctx, 64, self.RULE_gt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 291
            self.match(AtoParser.GT_EQ)
            self.state = 292
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
            return self.getToken(AtoParser.WITHIN, 0)

        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtoParser.Arithmetic_expressionContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_in_arithmetic_or

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIn_arithmetic_or" ):
                return visitor.visitIn_arithmetic_or(self)
            else:
                return visitor.visitChildren(self)




    def in_arithmetic_or(self):

        localctx = AtoParser.In_arithmetic_orContext(self, self._ctx, self.state)
        self.enterRule(localctx, 66, self.RULE_in_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 294
            self.match(AtoParser.WITHIN)
            self.state = 295
            self.arithmetic_expression(0)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Is_arithmetic_orContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IS(self):
            return self.getToken(AtoParser.IS, 0)

        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtoParser.Arithmetic_expressionContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_is_arithmetic_or

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIs_arithmetic_or" ):
                return visitor.visitIs_arithmetic_or(self)
            else:
                return visitor.visitChildren(self)




    def is_arithmetic_or(self):

        localctx = AtoParser.Is_arithmetic_orContext(self, self._ctx, self.state)
        self.enterRule(localctx, 68, self.RULE_is_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 297
            self.match(AtoParser.IS)
            self.state = 298
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
            return self.getTypedRuleContext(AtoParser.SumContext,0)


        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtoParser.Arithmetic_expressionContext,0)


        def OR_OP(self):
            return self.getToken(AtoParser.OR_OP, 0)

        def AND_OP(self):
            return self.getToken(AtoParser.AND_OP, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_arithmetic_expression

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArithmetic_expression" ):
                return visitor.visitArithmetic_expression(self)
            else:
                return visitor.visitChildren(self)



    def arithmetic_expression(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = AtoParser.Arithmetic_expressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 70
        self.enterRecursionRule(localctx, 70, self.RULE_arithmetic_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 301
            self.sum_(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 308
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,20,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.Arithmetic_expressionContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmetic_expression)
                    self.state = 303
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 304
                    _la = self._input.LA(1)
                    if not(_la==46 or _la==48):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 305
                    self.sum_(0) 
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


    class SumContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def term(self):
            return self.getTypedRuleContext(AtoParser.TermContext,0)


        def sum_(self):
            return self.getTypedRuleContext(AtoParser.SumContext,0)


        def ADD(self):
            return self.getToken(AtoParser.ADD, 0)

        def MINUS(self):
            return self.getToken(AtoParser.MINUS, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_sum

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSum" ):
                return visitor.visitSum(self)
            else:
                return visitor.visitChildren(self)



    def sum_(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = AtoParser.SumContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 72
        self.enterRecursionRule(localctx, 72, self.RULE_sum, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 312
            self.term(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 319
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,21,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.SumContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_sum)
                    self.state = 314
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 315
                    _la = self._input.LA(1)
                    if not(_la==51 or _la==52):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 316
                    self.term(0) 
                self.state = 321
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,21,self._ctx)

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
            return self.getTypedRuleContext(AtoParser.PowerContext,0)


        def term(self):
            return self.getTypedRuleContext(AtoParser.TermContext,0)


        def STAR(self):
            return self.getToken(AtoParser.STAR, 0)

        def DIV(self):
            return self.getToken(AtoParser.DIV, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_term

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTerm" ):
                return visitor.visitTerm(self)
            else:
                return visitor.visitChildren(self)



    def term(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = AtoParser.TermContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 74
        self.enterRecursionRule(localctx, 74, self.RULE_term, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 323
            self.power()
            self._ctx.stop = self._input.LT(-1)
            self.state = 330
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,22,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.TermContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_term)
                    self.state = 325
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 326
                    _la = self._input.LA(1)
                    if not(_la==36 or _la==53):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 327
                    self.power() 
                self.state = 332
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,22,self._ctx)

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
                return self.getTypedRuleContexts(AtoParser.FunctionalContext)
            else:
                return self.getTypedRuleContext(AtoParser.FunctionalContext,i)


        def POWER(self):
            return self.getToken(AtoParser.POWER, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_power

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPower" ):
                return visitor.visitPower(self)
            else:
                return visitor.visitChildren(self)




    def power(self):

        localctx = AtoParser.PowerContext(self, self._ctx, self.state)
        self.enterRule(localctx, 76, self.RULE_power)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 333
            self.functional()
            self.state = 336
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,23,self._ctx)
            if la_ == 1:
                self.state = 334
                self.match(AtoParser.POWER)
                self.state = 335
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
                return self.getTypedRuleContexts(AtoParser.BoundContext)
            else:
                return self.getTypedRuleContext(AtoParser.BoundContext,i)


        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def OPEN_PAREN(self):
            return self.getToken(AtoParser.OPEN_PAREN, 0)

        def CLOSE_PAREN(self):
            return self.getToken(AtoParser.CLOSE_PAREN, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_functional

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFunctional" ):
                return visitor.visitFunctional(self)
            else:
                return visitor.visitChildren(self)




    def functional(self):

        localctx = AtoParser.FunctionalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 78, self.RULE_functional)
        self._la = 0 # Token type
        try:
            self.state = 348
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,25,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 338
                self.bound()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 339
                self.name()
                self.state = 340
                self.match(AtoParser.OPEN_PAREN)
                self.state = 342 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 341
                    self.bound()
                    self.state = 344 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 6755536882106384) != 0)):
                        break

                self.state = 346
                self.match(AtoParser.CLOSE_PAREN)
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
            return self.getTypedRuleContext(AtoParser.AtomContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_bound

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBound" ):
                return visitor.visitBound(self)
            else:
                return visitor.visitChildren(self)




    def bound(self):

        localctx = AtoParser.BoundContext(self, self._ctx, self.state)
        self.enterRule(localctx, 80, self.RULE_bound)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 350
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
            return self.getTypedRuleContext(AtoParser.Name_or_attrContext,0)


        def literal_physical(self):
            return self.getTypedRuleContext(AtoParser.Literal_physicalContext,0)


        def arithmetic_group(self):
            return self.getTypedRuleContext(AtoParser.Arithmetic_groupContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_atom

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAtom" ):
                return visitor.visitAtom(self)
            else:
                return visitor.visitChildren(self)




    def atom(self):

        localctx = AtoParser.AtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 82, self.RULE_atom)
        try:
            self.state = 355
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [21]:
                self.enterOuterAlt(localctx, 1)
                self.state = 352
                self.name_or_attr()
                pass
            elif token in [4, 51, 52]:
                self.enterOuterAlt(localctx, 2)
                self.state = 353
                self.literal_physical()
                pass
            elif token in [37]:
                self.enterOuterAlt(localctx, 3)
                self.state = 354
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
            return self.getToken(AtoParser.OPEN_PAREN, 0)

        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtoParser.Arithmetic_expressionContext,0)


        def CLOSE_PAREN(self):
            return self.getToken(AtoParser.CLOSE_PAREN, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_arithmetic_group

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArithmetic_group" ):
                return visitor.visitArithmetic_group(self)
            else:
                return visitor.visitChildren(self)




    def arithmetic_group(self):

        localctx = AtoParser.Arithmetic_groupContext(self, self._ctx, self.state)
        self.enterRule(localctx, 84, self.RULE_arithmetic_group)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 357
            self.match(AtoParser.OPEN_PAREN)
            self.state = 358
            self.arithmetic_expression(0)
            self.state = 359
            self.match(AtoParser.CLOSE_PAREN)
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
            return self.getTypedRuleContext(AtoParser.Bound_quantityContext,0)


        def bilateral_quantity(self):
            return self.getTypedRuleContext(AtoParser.Bilateral_quantityContext,0)


        def quantity(self):
            return self.getTypedRuleContext(AtoParser.QuantityContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_literal_physical

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLiteral_physical" ):
                return visitor.visitLiteral_physical(self)
            else:
                return visitor.visitChildren(self)




    def literal_physical(self):

        localctx = AtoParser.Literal_physicalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 86, self.RULE_literal_physical)
        try:
            self.state = 364
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,27,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 361
                self.bound_quantity()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 362
                self.bilateral_quantity()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 363
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
                return self.getTypedRuleContexts(AtoParser.QuantityContext)
            else:
                return self.getTypedRuleContext(AtoParser.QuantityContext,i)


        def TO(self):
            return self.getToken(AtoParser.TO, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_bound_quantity

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBound_quantity" ):
                return visitor.visitBound_quantity(self)
            else:
                return visitor.visitChildren(self)




    def bound_quantity(self):

        localctx = AtoParser.Bound_quantityContext(self, self._ctx, self.state)
        self.enterRule(localctx, 88, self.RULE_bound_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 366
            self.quantity()
            self.state = 367
            self.match(AtoParser.TO)
            self.state = 368
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
            return self.getTypedRuleContext(AtoParser.QuantityContext,0)


        def PLUS_OR_MINUS(self):
            return self.getToken(AtoParser.PLUS_OR_MINUS, 0)

        def bilateral_tolerance(self):
            return self.getTypedRuleContext(AtoParser.Bilateral_toleranceContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_bilateral_quantity

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBilateral_quantity" ):
                return visitor.visitBilateral_quantity(self)
            else:
                return visitor.visitChildren(self)




    def bilateral_quantity(self):

        localctx = AtoParser.Bilateral_quantityContext(self, self._ctx, self.state)
        self.enterRule(localctx, 90, self.RULE_bilateral_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 370
            self.quantity()
            self.state = 371
            self.match(AtoParser.PLUS_OR_MINUS)
            self.state = 372
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
            return self.getToken(AtoParser.NUMBER, 0)

        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def ADD(self):
            return self.getToken(AtoParser.ADD, 0)

        def MINUS(self):
            return self.getToken(AtoParser.MINUS, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_quantity

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitQuantity" ):
                return visitor.visitQuantity(self)
            else:
                return visitor.visitChildren(self)




    def quantity(self):

        localctx = AtoParser.QuantityContext(self, self._ctx, self.state)
        self.enterRule(localctx, 92, self.RULE_quantity)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 375
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==51 or _la==52:
                self.state = 374
                _la = self._input.LA(1)
                if not(_la==51 or _la==52):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()


            self.state = 377
            self.match(AtoParser.NUMBER)
            self.state = 379
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,29,self._ctx)
            if la_ == 1:
                self.state = 378
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
            return self.getToken(AtoParser.NUMBER, 0)

        def PERCENT(self):
            return self.getToken(AtoParser.PERCENT, 0)

        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_bilateral_tolerance

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBilateral_tolerance" ):
                return visitor.visitBilateral_tolerance(self)
            else:
                return visitor.visitChildren(self)




    def bilateral_tolerance(self):

        localctx = AtoParser.Bilateral_toleranceContext(self, self._ctx, self.state)
        self.enterRule(localctx, 94, self.RULE_bilateral_tolerance)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 381
            self.match(AtoParser.NUMBER)
            self.state = 384
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,30,self._ctx)
            if la_ == 1:
                self.state = 382
                self.match(AtoParser.PERCENT)

            elif la_ == 2:
                self.state = 383
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
            return self.getTypedRuleContext(AtoParser.AttrContext,0)


        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_name_or_attr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitName_or_attr" ):
                return visitor.visitName_or_attr(self)
            else:
                return visitor.visitChildren(self)




    def name_or_attr(self):

        localctx = AtoParser.Name_or_attrContext(self, self._ctx, self.state)
        self.enterRule(localctx, 96, self.RULE_name_or_attr)
        try:
            self.state = 388
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,31,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 386
                self.attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 387
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
            return self.getToken(AtoParser.COLON, 0)

        def name_or_attr(self):
            return self.getTypedRuleContext(AtoParser.Name_or_attrContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_type_info

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitType_info" ):
                return visitor.visitType_info(self)
            else:
                return visitor.visitChildren(self)




    def type_info(self):

        localctx = AtoParser.Type_infoContext(self, self._ctx, self.state)
        self.enterRule(localctx, 98, self.RULE_type_info)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 390
            self.match(AtoParser.COLON)
            self.state = 391
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
            return self.getTypedRuleContext(AtoParser.Name_or_attrContext,0)


        def DOT(self):
            return self.getToken(AtoParser.DOT, 0)

        def totally_an_integer(self):
            return self.getTypedRuleContext(AtoParser.Totally_an_integerContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_numerical_pin_ref

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNumerical_pin_ref" ):
                return visitor.visitNumerical_pin_ref(self)
            else:
                return visitor.visitChildren(self)




    def numerical_pin_ref(self):

        localctx = AtoParser.Numerical_pin_refContext(self, self._ctx, self.state)
        self.enterRule(localctx, 100, self.RULE_numerical_pin_ref)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 393
            self.name_or_attr()
            self.state = 394
            self.match(AtoParser.DOT)
            self.state = 395
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
                return self.getTypedRuleContexts(AtoParser.NameContext)
            else:
                return self.getTypedRuleContext(AtoParser.NameContext,i)


        def DOT(self, i:int=None):
            if i is None:
                return self.getTokens(AtoParser.DOT)
            else:
                return self.getToken(AtoParser.DOT, i)

        def getRuleIndex(self):
            return AtoParser.RULE_attr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAttr" ):
                return visitor.visitAttr(self)
            else:
                return visitor.visitChildren(self)




    def attr(self):

        localctx = AtoParser.AttrContext(self, self._ctx, self.state)
        self.enterRule(localctx, 102, self.RULE_attr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 397
            self.name()
            self.state = 400 
            self._errHandler.sync(self)
            _alt = 1
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    self.state = 398
                    self.match(AtoParser.DOT)
                    self.state = 399
                    self.name()

                else:
                    raise NoViableAltException(self)
                self.state = 402 
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,32,self._ctx)

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
            return self.getToken(AtoParser.NUMBER, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_totally_an_integer

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTotally_an_integer" ):
                return visitor.visitTotally_an_integer(self)
            else:
                return visitor.visitChildren(self)




    def totally_an_integer(self):

        localctx = AtoParser.Totally_an_integerContext(self, self._ctx, self.state)
        self.enterRule(localctx, 104, self.RULE_totally_an_integer)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 404
            self.match(AtoParser.NUMBER)
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
            return self.getToken(AtoParser.NAME, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_name

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitName" ):
                return visitor.visitName(self)
            else:
                return visitor.visitChildren(self)




    def name(self):

        localctx = AtoParser.NameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 106, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 406
            self.match(AtoParser.NAME)
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
            return self.getToken(AtoParser.STRING, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_string

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitString" ):
                return visitor.visitString(self)
            else:
                return visitor.visitChildren(self)




    def string(self):

        localctx = AtoParser.StringContext(self, self._ctx, self.state)
        self.enterRule(localctx, 108, self.RULE_string)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 408
            self.match(AtoParser.STRING)
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
            return self.getToken(AtoParser.TRUE, 0)

        def FALSE(self):
            return self.getToken(AtoParser.FALSE, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_boolean_

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBoolean_" ):
                return visitor.visitBoolean_(self)
            else:
                return visitor.visitChildren(self)




    def boolean_(self):

        localctx = AtoParser.Boolean_Context(self, self._ctx, self.state)
        self.enterRule(localctx, 110, self.RULE_boolean_)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 410
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
        self._predicates[35] = self.arithmetic_expression_sempred
        self._predicates[36] = self.sum_sempred
        self._predicates[37] = self.term_sempred
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
         




