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
        4,1,79,347,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,2,39,7,39,
        2,40,7,40,2,41,7,41,2,42,7,42,2,43,7,43,2,44,7,44,2,45,7,45,2,46,
        7,46,1,0,1,0,5,0,97,8,0,10,0,12,0,100,9,0,1,0,1,0,1,1,1,1,3,1,106,
        8,1,1,2,1,2,1,2,5,2,111,8,2,10,2,12,2,114,9,2,1,2,3,2,117,8,2,1,
        2,1,2,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,3,3,131,8,3,1,4,1,
        4,1,5,1,5,1,5,1,5,3,5,139,8,5,1,5,1,5,1,5,1,6,1,6,1,7,1,7,1,7,1,
        7,4,7,150,8,7,11,7,12,7,151,1,7,1,7,3,7,156,8,7,1,8,1,8,1,8,1,8,
        1,8,1,9,1,9,1,9,1,9,1,9,1,9,5,9,169,8,9,10,9,12,9,172,9,9,1,10,1,
        10,3,10,176,8,10,1,10,1,10,1,10,1,11,1,11,1,11,1,11,3,11,185,8,11,
        1,12,1,12,1,12,1,13,1,13,1,13,1,13,1,14,1,14,1,14,1,14,1,15,1,15,
        1,15,1,15,3,15,202,8,15,1,16,1,16,1,16,1,17,1,17,1,17,3,17,210,8,
        17,1,18,1,18,1,18,1,19,1,19,1,20,1,20,1,20,1,21,1,21,4,21,222,8,
        21,11,21,12,21,223,1,22,1,22,1,22,1,22,1,22,3,22,231,8,22,1,23,1,
        23,1,23,1,24,1,24,1,24,1,25,1,25,1,25,1,26,1,26,1,26,1,27,1,27,1,
        27,1,28,1,28,1,28,1,28,1,28,1,28,5,28,254,8,28,10,28,12,28,257,9,
        28,1,29,1,29,1,29,1,29,1,29,1,29,5,29,265,8,29,10,29,12,29,268,9,
        29,1,30,1,30,1,30,3,30,273,8,30,1,31,1,31,1,31,1,31,4,31,279,8,31,
        11,31,12,31,280,1,31,1,31,3,31,285,8,31,1,32,1,32,1,32,3,32,290,
        8,32,1,33,1,33,1,33,1,33,1,34,1,34,1,34,3,34,299,8,34,1,35,1,35,
        1,35,1,35,1,36,1,36,1,36,1,36,1,37,3,37,310,8,37,1,37,1,37,3,37,
        314,8,37,1,38,1,38,1,38,3,38,319,8,38,1,39,1,39,3,39,323,8,39,1,
        40,1,40,1,40,1,41,1,41,1,41,1,41,1,42,1,42,1,42,4,42,335,8,42,11,
        42,12,42,336,1,43,1,43,1,44,1,44,1,45,1,45,1,46,1,46,1,46,0,2,56,
        58,47,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,
        42,44,46,48,50,52,54,56,58,60,62,64,66,68,70,72,74,76,78,80,82,84,
        86,88,90,92,0,4,1,0,6,8,1,0,50,51,2,0,35,35,52,52,1,0,16,17,345,
        0,98,1,0,0,0,2,105,1,0,0,0,4,107,1,0,0,0,6,130,1,0,0,0,8,132,1,0,
        0,0,10,134,1,0,0,0,12,143,1,0,0,0,14,155,1,0,0,0,16,157,1,0,0,0,
        18,162,1,0,0,0,20,173,1,0,0,0,22,184,1,0,0,0,24,186,1,0,0,0,26,189,
        1,0,0,0,28,193,1,0,0,0,30,201,1,0,0,0,32,203,1,0,0,0,34,206,1,0,
        0,0,36,211,1,0,0,0,38,214,1,0,0,0,40,216,1,0,0,0,42,219,1,0,0,0,
        44,230,1,0,0,0,46,232,1,0,0,0,48,235,1,0,0,0,50,238,1,0,0,0,52,241,
        1,0,0,0,54,244,1,0,0,0,56,247,1,0,0,0,58,258,1,0,0,0,60,269,1,0,
        0,0,62,284,1,0,0,0,64,289,1,0,0,0,66,291,1,0,0,0,68,298,1,0,0,0,
        70,300,1,0,0,0,72,304,1,0,0,0,74,309,1,0,0,0,76,315,1,0,0,0,78,322,
        1,0,0,0,80,324,1,0,0,0,82,327,1,0,0,0,84,331,1,0,0,0,86,338,1,0,
        0,0,88,340,1,0,0,0,90,342,1,0,0,0,92,344,1,0,0,0,94,97,5,19,0,0,
        95,97,3,2,1,0,96,94,1,0,0,0,96,95,1,0,0,0,97,100,1,0,0,0,98,96,1,
        0,0,0,98,99,1,0,0,0,99,101,1,0,0,0,100,98,1,0,0,0,101,102,5,0,0,
        1,102,1,1,0,0,0,103,106,3,4,2,0,104,106,3,8,4,0,105,103,1,0,0,0,
        105,104,1,0,0,0,106,3,1,0,0,0,107,112,3,6,3,0,108,109,5,40,0,0,109,
        111,3,6,3,0,110,108,1,0,0,0,111,114,1,0,0,0,112,110,1,0,0,0,112,
        113,1,0,0,0,113,116,1,0,0,0,114,112,1,0,0,0,115,117,5,40,0,0,116,
        115,1,0,0,0,116,117,1,0,0,0,117,118,1,0,0,0,118,119,5,19,0,0,119,
        5,1,0,0,0,120,131,3,18,9,0,121,131,3,16,8,0,122,131,3,20,10,0,123,
        131,3,28,14,0,124,131,3,26,13,0,125,131,3,34,17,0,126,131,3,32,16,
        0,127,131,3,40,20,0,128,131,3,24,12,0,129,131,3,38,19,0,130,120,
        1,0,0,0,130,121,1,0,0,0,130,122,1,0,0,0,130,123,1,0,0,0,130,124,
        1,0,0,0,130,125,1,0,0,0,130,126,1,0,0,0,130,127,1,0,0,0,130,128,
        1,0,0,0,130,129,1,0,0,0,131,7,1,0,0,0,132,133,3,10,5,0,133,9,1,0,
        0,0,134,135,3,12,6,0,135,138,3,88,44,0,136,137,5,12,0,0,137,139,
        3,78,39,0,138,136,1,0,0,0,138,139,1,0,0,0,139,140,1,0,0,0,140,141,
        5,39,0,0,141,142,3,14,7,0,142,11,1,0,0,0,143,144,7,0,0,0,144,13,
        1,0,0,0,145,156,3,4,2,0,146,147,5,19,0,0,147,149,5,1,0,0,148,150,
        3,2,1,0,149,148,1,0,0,0,150,151,1,0,0,0,151,149,1,0,0,0,151,152,
        1,0,0,0,152,153,1,0,0,0,153,154,5,2,0,0,154,156,1,0,0,0,155,145,
        1,0,0,0,155,146,1,0,0,0,156,15,1,0,0,0,157,158,5,13,0,0,158,159,
        3,78,39,0,159,160,5,12,0,0,160,161,3,90,45,0,161,17,1,0,0,0,162,
        163,5,12,0,0,163,164,3,90,45,0,164,165,5,13,0,0,165,170,3,78,39,
        0,166,167,5,38,0,0,167,169,3,78,39,0,168,166,1,0,0,0,169,172,1,0,
        0,0,170,168,1,0,0,0,170,171,1,0,0,0,171,19,1,0,0,0,172,170,1,0,0,
        0,173,175,3,78,39,0,174,176,3,80,40,0,175,174,1,0,0,0,175,176,1,
        0,0,0,176,177,1,0,0,0,177,178,5,42,0,0,178,179,3,22,11,0,179,21,
        1,0,0,0,180,185,3,90,45,0,181,185,3,36,18,0,182,185,3,68,34,0,183,
        185,3,56,28,0,184,180,1,0,0,0,184,181,1,0,0,0,184,182,1,0,0,0,184,
        183,1,0,0,0,185,23,1,0,0,0,186,187,3,78,39,0,187,188,3,80,40,0,188,
        25,1,0,0,0,189,190,3,78,39,0,190,191,5,65,0,0,191,192,3,78,39,0,
        192,27,1,0,0,0,193,194,3,30,15,0,194,195,5,54,0,0,195,196,3,30,15,
        0,196,29,1,0,0,0,197,202,3,78,39,0,198,202,3,82,41,0,199,202,3,32,
        16,0,200,202,3,34,17,0,201,197,1,0,0,0,201,198,1,0,0,0,201,199,1,
        0,0,0,201,200,1,0,0,0,202,31,1,0,0,0,203,204,5,10,0,0,204,205,3,
        88,44,0,205,33,1,0,0,0,206,209,5,9,0,0,207,210,3,88,44,0,208,210,
        3,86,43,0,209,207,1,0,0,0,209,208,1,0,0,0,210,35,1,0,0,0,211,212,
        5,11,0,0,212,213,3,78,39,0,213,37,1,0,0,0,214,215,3,90,45,0,215,
        39,1,0,0,0,216,217,5,14,0,0,217,218,3,42,21,0,218,41,1,0,0,0,219,
        221,3,56,28,0,220,222,3,44,22,0,221,220,1,0,0,0,222,223,1,0,0,0,
        223,221,1,0,0,0,223,224,1,0,0,0,224,43,1,0,0,0,225,231,3,46,23,0,
        226,231,3,48,24,0,227,231,3,50,25,0,228,231,3,52,26,0,229,231,3,
        54,27,0,230,225,1,0,0,0,230,226,1,0,0,0,230,227,1,0,0,0,230,228,
        1,0,0,0,230,229,1,0,0,0,231,45,1,0,0,0,232,233,5,57,0,0,233,234,
        3,56,28,0,234,47,1,0,0,0,235,236,5,58,0,0,236,237,3,56,28,0,237,
        49,1,0,0,0,238,239,5,61,0,0,239,240,3,56,28,0,240,51,1,0,0,0,241,
        242,5,60,0,0,242,243,3,56,28,0,243,53,1,0,0,0,244,245,5,18,0,0,245,
        246,3,56,28,0,246,55,1,0,0,0,247,248,6,28,-1,0,248,249,3,58,29,0,
        249,255,1,0,0,0,250,251,10,2,0,0,251,252,7,1,0,0,252,254,3,58,29,
        0,253,250,1,0,0,0,254,257,1,0,0,0,255,253,1,0,0,0,255,256,1,0,0,
        0,256,57,1,0,0,0,257,255,1,0,0,0,258,259,6,29,-1,0,259,260,3,60,
        30,0,260,266,1,0,0,0,261,262,10,2,0,0,262,263,7,2,0,0,263,265,3,
        60,30,0,264,261,1,0,0,0,265,268,1,0,0,0,266,264,1,0,0,0,266,267,
        1,0,0,0,267,59,1,0,0,0,268,266,1,0,0,0,269,272,3,62,31,0,270,271,
        5,41,0,0,271,273,3,62,31,0,272,270,1,0,0,0,272,273,1,0,0,0,273,61,
        1,0,0,0,274,285,3,64,32,0,275,276,3,88,44,0,276,278,5,36,0,0,277,
        279,3,64,32,0,278,277,1,0,0,0,279,280,1,0,0,0,280,278,1,0,0,0,280,
        281,1,0,0,0,281,282,1,0,0,0,282,283,5,37,0,0,283,285,1,0,0,0,284,
        274,1,0,0,0,284,275,1,0,0,0,285,63,1,0,0,0,286,290,3,78,39,0,287,
        290,3,68,34,0,288,290,3,66,33,0,289,286,1,0,0,0,289,287,1,0,0,0,
        289,288,1,0,0,0,290,65,1,0,0,0,291,292,5,36,0,0,292,293,3,56,28,
        0,293,294,5,37,0,0,294,67,1,0,0,0,295,299,3,70,35,0,296,299,3,72,
        36,0,297,299,3,74,37,0,298,295,1,0,0,0,298,296,1,0,0,0,298,297,1,
        0,0,0,299,69,1,0,0,0,300,301,3,74,37,0,301,302,5,15,0,0,302,303,
        3,74,37,0,303,71,1,0,0,0,304,305,3,74,37,0,305,306,5,29,0,0,306,
        307,3,76,38,0,307,73,1,0,0,0,308,310,7,1,0,0,309,308,1,0,0,0,309,
        310,1,0,0,0,310,311,1,0,0,0,311,313,5,4,0,0,312,314,3,88,44,0,313,
        312,1,0,0,0,313,314,1,0,0,0,314,75,1,0,0,0,315,318,5,4,0,0,316,319,
        5,32,0,0,317,319,3,88,44,0,318,316,1,0,0,0,318,317,1,0,0,0,318,319,
        1,0,0,0,319,77,1,0,0,0,320,323,3,84,42,0,321,323,3,88,44,0,322,320,
        1,0,0,0,322,321,1,0,0,0,323,79,1,0,0,0,324,325,5,39,0,0,325,326,
        3,78,39,0,326,81,1,0,0,0,327,328,3,78,39,0,328,329,5,33,0,0,329,
        330,3,86,43,0,330,83,1,0,0,0,331,334,3,88,44,0,332,333,5,33,0,0,
        333,335,3,88,44,0,334,332,1,0,0,0,335,336,1,0,0,0,336,334,1,0,0,
        0,336,337,1,0,0,0,337,85,1,0,0,0,338,339,5,4,0,0,339,87,1,0,0,0,
        340,341,5,20,0,0,341,89,1,0,0,0,342,343,5,3,0,0,343,91,1,0,0,0,344,
        345,7,3,0,0,345,93,1,0,0,0,28,96,98,105,112,116,130,138,151,155,
        170,175,184,201,209,223,230,255,266,272,280,284,289,298,309,313,
        318,322,336
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
                     "'within'", "<INVALID>", "<INVALID>", "<INVALID>", 
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
                      "TRUE", "FALSE", "WITHIN", "NEWLINE", "NAME", "STRING_LITERAL", 
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
    RULE_retype_stmt = 13
    RULE_connect_stmt = 14
    RULE_connectable = 15
    RULE_signaldef_stmt = 16
    RULE_pindef_stmt = 17
    RULE_new_stmt = 18
    RULE_string_stmt = 19
    RULE_assert_stmt = 20
    RULE_comparison = 21
    RULE_compare_op_pair = 22
    RULE_lt_arithmetic_or = 23
    RULE_gt_arithmetic_or = 24
    RULE_lt_eq_arithmetic_or = 25
    RULE_gt_eq_arithmetic_or = 26
    RULE_in_arithmetic_or = 27
    RULE_arithmetic_expression = 28
    RULE_term = 29
    RULE_power = 30
    RULE_functional = 31
    RULE_atom = 32
    RULE_arithmetic_group = 33
    RULE_literal_physical = 34
    RULE_bound_quantity = 35
    RULE_bilateral_quantity = 36
    RULE_quantity = 37
    RULE_bilateral_tolerance = 38
    RULE_name_or_attr = 39
    RULE_type_info = 40
    RULE_numerical_pin_ref = 41
    RULE_attr = 42
    RULE_totally_an_integer = 43
    RULE_name = 44
    RULE_string = 45
    RULE_boolean_ = 46

    ruleNames =  [ "file_input", "stmt", "simple_stmts", "simple_stmt", 
                   "compound_stmt", "blockdef", "blocktype", "block", "dep_import_stmt", 
                   "import_stmt", "assign_stmt", "assignable", "declaration_stmt", 
                   "retype_stmt", "connect_stmt", "connectable", "signaldef_stmt", 
                   "pindef_stmt", "new_stmt", "string_stmt", "assert_stmt", 
                   "comparison", "compare_op_pair", "lt_arithmetic_or", 
                   "gt_arithmetic_or", "lt_eq_arithmetic_or", "gt_eq_arithmetic_or", 
                   "in_arithmetic_or", "arithmetic_expression", "term", 
                   "power", "functional", "atom", "arithmetic_group", "literal_physical", 
                   "bound_quantity", "bilateral_quantity", "quantity", "bilateral_tolerance", 
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
            self.state = 98
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 1603528) != 0):
                self.state = 96
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [19]:
                    self.state = 94
                    self.match(AtopileParser.NEWLINE)
                    pass
                elif token in [3, 6, 7, 8, 9, 10, 12, 13, 14, 20]:
                    self.state = 95
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 100
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 101
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
            self.state = 105
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 14, 20]:
                self.enterOuterAlt(localctx, 1)
                self.state = 103
                self.simple_stmts()
                pass
            elif token in [6, 7, 8]:
                self.enterOuterAlt(localctx, 2)
                self.state = 104
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
            self.state = 107
            self.simple_stmt()
            self.state = 112
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 108
                    self.match(AtopileParser.SEMI_COLON)
                    self.state = 109
                    self.simple_stmt() 
                self.state = 114
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 116
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==40:
                self.state = 115
                self.match(AtopileParser.SEMI_COLON)


            self.state = 118
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


        def assert_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Assert_stmtContext,0)


        def declaration_stmt(self):
            return self.getTypedRuleContext(AtopileParser.Declaration_stmtContext,0)


        def string_stmt(self):
            return self.getTypedRuleContext(AtopileParser.String_stmtContext,0)


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
            self.state = 130
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 120
                self.import_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 121
                self.dep_import_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 122
                self.assign_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 123
                self.connect_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 124
                self.retype_stmt()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 125
                self.pindef_stmt()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 126
                self.signaldef_stmt()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 127
                self.assert_stmt()
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 128
                self.declaration_stmt()
                pass

            elif la_ == 10:
                self.enterOuterAlt(localctx, 10)
                self.state = 129
                self.string_stmt()
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
            self.state = 132
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
            self.state = 134
            self.blocktype()
            self.state = 135
            self.name()
            self.state = 138
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 136
                self.match(AtopileParser.FROM)
                self.state = 137
                self.name_or_attr()


            self.state = 140
            self.match(AtopileParser.COLON)
            self.state = 141
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
            self.state = 143
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
            self.state = 155
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 14, 20]:
                self.enterOuterAlt(localctx, 1)
                self.state = 145
                self.simple_stmts()
                pass
            elif token in [19]:
                self.enterOuterAlt(localctx, 2)
                self.state = 146
                self.match(AtopileParser.NEWLINE)
                self.state = 147
                self.match(AtopileParser.INDENT)
                self.state = 149 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 148
                    self.stmt()
                    self.state = 151 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 1079240) != 0)):
                        break

                self.state = 153
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
            self.state = 157
            self.match(AtopileParser.IMPORT)
            self.state = 158
            self.name_or_attr()
            self.state = 159
            self.match(AtopileParser.FROM)
            self.state = 160
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
            self.state = 162
            self.match(AtopileParser.FROM)
            self.state = 163
            self.string()
            self.state = 164
            self.match(AtopileParser.IMPORT)
            self.state = 165
            self.name_or_attr()
            self.state = 170
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==38:
                self.state = 166
                self.match(AtopileParser.COMMA)
                self.state = 167
                self.name_or_attr()
                self.state = 172
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
            self.state = 173
            self.name_or_attr()
            self.state = 175
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==39:
                self.state = 174
                self.type_info()


            self.state = 177
            self.match(AtopileParser.ASSIGN)
            self.state = 178
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


        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtopileParser.Arithmetic_expressionContext,0)


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
            self.state = 184
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,11,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 180
                self.string()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 181
                self.new_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 182
                self.literal_physical()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 183
                self.arithmetic_expression(0)
                pass


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
            self.state = 186
            self.name_or_attr()
            self.state = 187
            self.type_info()
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
        self.enterRule(localctx, 26, self.RULE_retype_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 189
            self.name_or_attr()
            self.state = 190
            self.match(AtopileParser.ARROW)
            self.state = 191
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
        self.enterRule(localctx, 28, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 193
            self.connectable()
            self.state = 194
            self.match(AtopileParser.NOT_OP)
            self.state = 195
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
        self.enterRule(localctx, 30, self.RULE_connectable)
        try:
            self.state = 201
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 197
                self.name_or_attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 198
                self.numerical_pin_ref()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 199
                self.signaldef_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 200
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
        self.enterRule(localctx, 32, self.RULE_signaldef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 203
            self.match(AtopileParser.SIGNAL)
            self.state = 204
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
        self.enterRule(localctx, 34, self.RULE_pindef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 206
            self.match(AtopileParser.PIN)
            self.state = 209
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [20]:
                self.state = 207
                self.name()
                pass
            elif token in [4]:
                self.state = 208
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
        self.enterRule(localctx, 36, self.RULE_new_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 211
            self.match(AtopileParser.NEW)
            self.state = 212
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
        self.enterRule(localctx, 38, self.RULE_string_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 214
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
        self.enterRule(localctx, 40, self.RULE_assert_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 216
            self.match(AtopileParser.ASSERT)
            self.state = 217
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
        self.enterRule(localctx, 42, self.RULE_comparison)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 219
            self.arithmetic_expression(0)
            self.state = 221 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 220
                self.compare_op_pair()
                self.state = 223 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 3891110078048370688) != 0)):
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
        self.enterRule(localctx, 44, self.RULE_compare_op_pair)
        try:
            self.state = 230
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [57]:
                self.enterOuterAlt(localctx, 1)
                self.state = 225
                self.lt_arithmetic_or()
                pass
            elif token in [58]:
                self.enterOuterAlt(localctx, 2)
                self.state = 226
                self.gt_arithmetic_or()
                pass
            elif token in [61]:
                self.enterOuterAlt(localctx, 3)
                self.state = 227
                self.lt_eq_arithmetic_or()
                pass
            elif token in [60]:
                self.enterOuterAlt(localctx, 4)
                self.state = 228
                self.gt_eq_arithmetic_or()
                pass
            elif token in [18]:
                self.enterOuterAlt(localctx, 5)
                self.state = 229
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
        self.enterRule(localctx, 46, self.RULE_lt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 232
            self.match(AtopileParser.LESS_THAN)
            self.state = 233
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
        self.enterRule(localctx, 48, self.RULE_gt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 235
            self.match(AtopileParser.GREATER_THAN)
            self.state = 236
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
        self.enterRule(localctx, 50, self.RULE_lt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 238
            self.match(AtopileParser.LT_EQ)
            self.state = 239
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
        self.enterRule(localctx, 52, self.RULE_gt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 241
            self.match(AtopileParser.GT_EQ)
            self.state = 242
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
        self.enterRule(localctx, 54, self.RULE_in_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 244
            self.match(AtopileParser.WITHIN)
            self.state = 245
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

        def term(self):
            return self.getTypedRuleContext(AtopileParser.TermContext,0)


        def arithmetic_expression(self):
            return self.getTypedRuleContext(AtopileParser.Arithmetic_expressionContext,0)


        def ADD(self):
            return self.getToken(AtopileParser.ADD, 0)

        def MINUS(self):
            return self.getToken(AtopileParser.MINUS, 0)

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
        _startState = 56
        self.enterRecursionRule(localctx, 56, self.RULE_arithmetic_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 248
            self.term(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 255
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,16,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtopileParser.Arithmetic_expressionContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmetic_expression)
                    self.state = 250
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 251
                    _la = self._input.LA(1)
                    if not(_la==50 or _la==51):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 252
                    self.term(0) 
                self.state = 257
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,16,self._ctx)

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
        _startState = 58
        self.enterRecursionRule(localctx, 58, self.RULE_term, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 259
            self.power()
            self._ctx.stop = self._input.LT(-1)
            self.state = 266
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,17,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtopileParser.TermContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_term)
                    self.state = 261
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 262
                    _la = self._input.LA(1)
                    if not(_la==35 or _la==52):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 263
                    self.power() 
                self.state = 268
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,17,self._ctx)

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
        self.enterRule(localctx, 60, self.RULE_power)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 269
            self.functional()
            self.state = 272
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,18,self._ctx)
            if la_ == 1:
                self.state = 270
                self.match(AtopileParser.POWER)
                self.state = 271
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

        def atom(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtopileParser.AtomContext)
            else:
                return self.getTypedRuleContext(AtopileParser.AtomContext,i)


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
        self.enterRule(localctx, 62, self.RULE_functional)
        self._la = 0 # Token type
        try:
            self.state = 284
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,20,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 274
                self.atom()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 275
                self.name()
                self.state = 276
                self.match(AtopileParser.OPEN_PAREN)
                self.state = 278 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 277
                    self.atom()
                    self.state = 280 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 3377768441053200) != 0)):
                        break

                self.state = 282
                self.match(AtopileParser.CLOSE_PAREN)
                pass


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
        self.enterRule(localctx, 64, self.RULE_atom)
        try:
            self.state = 289
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [20]:
                self.enterOuterAlt(localctx, 1)
                self.state = 286
                self.name_or_attr()
                pass
            elif token in [4, 50, 51]:
                self.enterOuterAlt(localctx, 2)
                self.state = 287
                self.literal_physical()
                pass
            elif token in [36]:
                self.enterOuterAlt(localctx, 3)
                self.state = 288
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
        self.enterRule(localctx, 66, self.RULE_arithmetic_group)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 291
            self.match(AtopileParser.OPEN_PAREN)
            self.state = 292
            self.arithmetic_expression(0)
            self.state = 293
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
        self.enterRule(localctx, 68, self.RULE_literal_physical)
        try:
            self.state = 298
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,22,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 295
                self.bound_quantity()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 296
                self.bilateral_quantity()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 297
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
        self.enterRule(localctx, 70, self.RULE_bound_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 300
            self.quantity()
            self.state = 301
            self.match(AtopileParser.TO)
            self.state = 302
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
        self.enterRule(localctx, 72, self.RULE_bilateral_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 304
            self.quantity()
            self.state = 305
            self.match(AtopileParser.PLUS_OR_MINUS)
            self.state = 306
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
        self.enterRule(localctx, 74, self.RULE_quantity)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 309
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==50 or _la==51:
                self.state = 308
                _la = self._input.LA(1)
                if not(_la==50 or _la==51):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()


            self.state = 311
            self.match(AtopileParser.NUMBER)
            self.state = 313
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,24,self._ctx)
            if la_ == 1:
                self.state = 312
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
        self.enterRule(localctx, 76, self.RULE_bilateral_tolerance)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 315
            self.match(AtopileParser.NUMBER)
            self.state = 318
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,25,self._ctx)
            if la_ == 1:
                self.state = 316
                self.match(AtopileParser.PERCENT)

            elif la_ == 2:
                self.state = 317
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
        self.enterRule(localctx, 78, self.RULE_name_or_attr)
        try:
            self.state = 322
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,26,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 320
                self.attr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 321
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
        self.enterRule(localctx, 80, self.RULE_type_info)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 324
            self.match(AtopileParser.COLON)
            self.state = 325
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
        self.enterRule(localctx, 82, self.RULE_numerical_pin_ref)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 327
            self.name_or_attr()
            self.state = 328
            self.match(AtopileParser.DOT)
            self.state = 329
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
        self.enterRule(localctx, 84, self.RULE_attr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 331
            self.name()
            self.state = 334 
            self._errHandler.sync(self)
            _alt = 1
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    self.state = 332
                    self.match(AtopileParser.DOT)
                    self.state = 333
                    self.name()

                else:
                    raise NoViableAltException(self)
                self.state = 336 
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,27,self._ctx)

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
        self.enterRule(localctx, 86, self.RULE_totally_an_integer)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 338
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
        self.enterRule(localctx, 88, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 340
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
        self.enterRule(localctx, 90, self.RULE_string)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 342
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
        self.enterRule(localctx, 92, self.RULE_boolean_)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 344
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
        self._predicates[28] = self.arithmetic_expression_sempred
        self._predicates[29] = self.term_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def arithmetic_expression_sempred(self, localctx:Arithmetic_expressionContext, predIndex:int):
            if predIndex == 0:
                return self.precpred(self._ctx, 2)
         

    def term_sempred(self, localctx:TermContext, predIndex:int):
            if predIndex == 1:
                return self.precpred(self._ctx, 2)
         




