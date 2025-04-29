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
        4,1,84,458,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,2,39,7,39,
        2,40,7,40,2,41,7,41,2,42,7,42,2,43,7,43,2,44,7,44,2,45,7,45,2,46,
        7,46,2,47,7,47,2,48,7,48,2,49,7,49,2,50,7,50,2,51,7,51,2,52,7,52,
        2,53,7,53,2,54,7,54,2,55,7,55,2,56,7,56,2,57,7,57,2,58,7,58,2,59,
        7,59,2,60,7,60,2,61,7,61,2,62,7,62,2,63,7,63,2,64,7,64,1,0,1,0,5,
        0,133,8,0,10,0,12,0,136,9,0,1,0,1,0,1,1,1,1,3,1,142,8,1,1,2,1,2,
        1,2,5,2,147,8,2,10,2,12,2,150,9,2,1,2,3,2,153,8,2,1,2,1,2,1,3,1,
        3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,3,3,171,8,3,1,
        4,1,4,1,5,1,5,1,5,3,5,178,8,5,1,5,1,5,1,5,1,6,1,6,1,6,1,7,1,7,1,
        8,1,8,1,8,1,8,4,8,192,8,8,11,8,12,8,193,1,8,1,8,3,8,198,8,8,1,9,
        1,9,1,9,1,9,1,9,1,10,1,10,3,10,207,8,10,1,10,1,10,1,10,1,10,5,10,
        213,8,10,10,10,12,10,216,9,10,1,11,1,11,1,11,1,12,1,12,3,12,223,
        8,12,1,13,1,13,1,13,1,13,1,14,1,14,1,14,1,14,1,15,1,15,1,15,1,15,
        1,16,1,16,1,17,1,17,3,17,241,8,17,1,18,1,18,1,18,1,18,1,18,3,18,
        248,8,18,1,19,1,19,1,19,1,19,1,20,1,20,1,20,4,20,257,8,20,11,20,
        12,20,258,1,21,1,21,1,21,1,21,1,22,1,22,1,23,1,23,1,23,3,23,270,
        8,23,1,24,1,24,1,24,1,25,1,25,1,26,1,26,1,27,1,27,1,27,1,27,3,27,
        283,8,27,1,28,1,28,1,28,1,29,1,29,1,30,1,30,1,31,1,31,1,31,1,32,
        1,32,4,32,297,8,32,11,32,12,32,298,1,33,1,33,1,33,1,33,1,33,1,33,
        3,33,307,8,33,1,34,1,34,1,34,1,35,1,35,1,35,1,36,1,36,1,36,1,37,
        1,37,1,37,1,38,1,38,1,38,1,39,1,39,1,39,1,40,1,40,1,40,1,40,1,40,
        1,40,5,40,333,8,40,10,40,12,40,336,9,40,1,41,1,41,1,41,1,41,1,41,
        1,41,5,41,344,8,41,10,41,12,41,347,9,41,1,42,1,42,1,42,1,42,1,42,
        1,42,5,42,355,8,42,10,42,12,42,358,9,42,1,43,1,43,1,43,3,43,363,
        8,43,1,44,1,44,1,44,1,44,4,44,369,8,44,11,44,12,44,370,1,44,1,44,
        3,44,375,8,44,1,45,1,45,1,46,1,46,1,46,3,46,382,8,46,1,47,1,47,1,
        47,1,47,1,48,1,48,1,48,3,48,391,8,48,1,49,1,49,1,49,1,49,1,50,1,
        50,1,50,1,50,1,51,3,51,402,8,51,1,51,1,51,3,51,406,8,51,1,52,1,52,
        1,52,3,52,411,8,52,1,53,1,53,1,54,1,54,1,54,1,54,1,55,1,55,1,55,
        1,56,1,56,3,56,424,8,56,1,57,1,57,1,57,5,57,429,8,57,10,57,12,57,
        432,9,57,1,57,3,57,435,8,57,1,58,1,58,1,58,5,58,440,8,58,10,58,12,
        58,443,9,58,1,59,1,59,1,60,1,60,1,60,1,61,1,61,1,62,1,62,1,63,1,
        63,1,64,1,64,1,64,0,3,80,82,84,65,0,2,4,6,8,10,12,14,16,18,20,22,
        24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,54,56,58,60,62,64,66,
        68,70,72,74,76,78,80,82,84,86,88,90,92,94,96,98,100,102,104,106,
        108,110,112,114,116,118,120,122,124,126,128,0,7,1,0,6,8,1,0,73,74,
        1,0,68,69,2,0,48,48,50,50,1,0,53,54,2,0,38,38,55,55,1,0,16,17,450,
        0,134,1,0,0,0,2,141,1,0,0,0,4,143,1,0,0,0,6,170,1,0,0,0,8,172,1,
        0,0,0,10,174,1,0,0,0,12,182,1,0,0,0,14,185,1,0,0,0,16,197,1,0,0,
        0,18,199,1,0,0,0,20,206,1,0,0,0,22,217,1,0,0,0,24,222,1,0,0,0,26,
        224,1,0,0,0,28,228,1,0,0,0,30,232,1,0,0,0,32,236,1,0,0,0,34,240,
        1,0,0,0,36,247,1,0,0,0,38,249,1,0,0,0,40,253,1,0,0,0,42,260,1,0,
        0,0,44,264,1,0,0,0,46,269,1,0,0,0,48,271,1,0,0,0,50,274,1,0,0,0,
        52,276,1,0,0,0,54,278,1,0,0,0,56,284,1,0,0,0,58,287,1,0,0,0,60,289,
        1,0,0,0,62,291,1,0,0,0,64,294,1,0,0,0,66,306,1,0,0,0,68,308,1,0,
        0,0,70,311,1,0,0,0,72,314,1,0,0,0,74,317,1,0,0,0,76,320,1,0,0,0,
        78,323,1,0,0,0,80,326,1,0,0,0,82,337,1,0,0,0,84,348,1,0,0,0,86,359,
        1,0,0,0,88,374,1,0,0,0,90,376,1,0,0,0,92,381,1,0,0,0,94,383,1,0,
        0,0,96,390,1,0,0,0,98,392,1,0,0,0,100,396,1,0,0,0,102,401,1,0,0,
        0,104,407,1,0,0,0,106,412,1,0,0,0,108,414,1,0,0,0,110,418,1,0,0,
        0,112,421,1,0,0,0,114,425,1,0,0,0,116,436,1,0,0,0,118,444,1,0,0,
        0,120,446,1,0,0,0,122,449,1,0,0,0,124,451,1,0,0,0,126,453,1,0,0,
        0,128,455,1,0,0,0,130,133,5,80,0,0,131,133,3,2,1,0,132,130,1,0,0,
        0,132,131,1,0,0,0,133,136,1,0,0,0,134,132,1,0,0,0,134,135,1,0,0,
        0,135,137,1,0,0,0,136,134,1,0,0,0,137,138,5,0,0,1,138,1,1,0,0,0,
        139,142,3,4,2,0,140,142,3,8,4,0,141,139,1,0,0,0,141,140,1,0,0,0,
        142,3,1,0,0,0,143,148,3,6,3,0,144,145,5,43,0,0,145,147,3,6,3,0,146,
        144,1,0,0,0,147,150,1,0,0,0,148,146,1,0,0,0,148,149,1,0,0,0,149,
        152,1,0,0,0,150,148,1,0,0,0,151,153,5,43,0,0,152,151,1,0,0,0,152,
        153,1,0,0,0,153,154,1,0,0,0,154,155,5,80,0,0,155,5,1,0,0,0,156,171,
        3,20,10,0,157,171,3,18,9,0,158,171,3,26,13,0,159,171,3,28,14,0,160,
        171,3,30,15,0,161,171,3,42,21,0,162,171,3,40,20,0,163,171,3,38,19,
        0,164,171,3,52,26,0,165,171,3,48,24,0,166,171,3,62,31,0,167,171,
        3,22,11,0,168,171,3,58,29,0,169,171,3,60,30,0,170,156,1,0,0,0,170,
        157,1,0,0,0,170,158,1,0,0,0,170,159,1,0,0,0,170,160,1,0,0,0,170,
        161,1,0,0,0,170,162,1,0,0,0,170,163,1,0,0,0,170,164,1,0,0,0,170,
        165,1,0,0,0,170,166,1,0,0,0,170,167,1,0,0,0,170,168,1,0,0,0,170,
        169,1,0,0,0,171,7,1,0,0,0,172,173,3,10,5,0,173,9,1,0,0,0,174,175,
        3,14,7,0,175,177,3,124,62,0,176,178,3,12,6,0,177,176,1,0,0,0,177,
        178,1,0,0,0,178,179,1,0,0,0,179,180,5,42,0,0,180,181,3,16,8,0,181,
        11,1,0,0,0,182,183,5,12,0,0,183,184,3,116,58,0,184,13,1,0,0,0,185,
        186,7,0,0,0,186,15,1,0,0,0,187,198,3,4,2,0,188,189,5,80,0,0,189,
        191,5,1,0,0,190,192,3,2,1,0,191,190,1,0,0,0,192,193,1,0,0,0,193,
        191,1,0,0,0,193,194,1,0,0,0,194,195,1,0,0,0,195,196,5,2,0,0,196,
        198,1,0,0,0,197,187,1,0,0,0,197,188,1,0,0,0,198,17,1,0,0,0,199,200,
        5,13,0,0,200,201,3,116,58,0,201,202,5,12,0,0,202,203,3,126,63,0,
        203,19,1,0,0,0,204,205,5,12,0,0,205,207,3,126,63,0,206,204,1,0,0,
        0,206,207,1,0,0,0,207,208,1,0,0,0,208,209,5,13,0,0,209,214,3,116,
        58,0,210,211,5,41,0,0,211,213,3,116,58,0,212,210,1,0,0,0,213,216,
        1,0,0,0,214,212,1,0,0,0,214,215,1,0,0,0,215,21,1,0,0,0,216,214,1,
        0,0,0,217,218,3,114,57,0,218,219,3,120,60,0,219,23,1,0,0,0,220,223,
        3,114,57,0,221,223,3,22,11,0,222,220,1,0,0,0,222,221,1,0,0,0,223,
        25,1,0,0,0,224,225,3,24,12,0,225,226,5,45,0,0,226,227,3,36,18,0,
        227,27,1,0,0,0,228,229,3,24,12,0,229,230,3,32,16,0,230,231,3,34,
        17,0,231,29,1,0,0,0,232,233,3,24,12,0,233,234,7,1,0,0,234,235,3,
        34,17,0,235,31,1,0,0,0,236,237,7,2,0,0,237,33,1,0,0,0,238,241,3,
        96,48,0,239,241,3,80,40,0,240,238,1,0,0,0,240,239,1,0,0,0,241,35,
        1,0,0,0,242,248,3,126,63,0,243,248,3,56,28,0,244,248,3,96,48,0,245,
        248,3,80,40,0,246,248,3,128,64,0,247,242,1,0,0,0,247,243,1,0,0,0,
        247,244,1,0,0,0,247,245,1,0,0,0,247,246,1,0,0,0,248,37,1,0,0,0,249,
        250,3,114,57,0,250,251,5,67,0,0,251,252,3,116,58,0,252,39,1,0,0,
        0,253,256,3,46,23,0,254,255,5,21,0,0,255,257,3,44,22,0,256,254,1,
        0,0,0,257,258,1,0,0,0,258,256,1,0,0,0,258,259,1,0,0,0,259,41,1,0,
        0,0,260,261,3,46,23,0,261,262,5,22,0,0,262,263,3,46,23,0,263,43,
        1,0,0,0,264,265,3,114,57,0,265,45,1,0,0,0,266,270,3,114,57,0,267,
        270,3,48,24,0,268,270,3,50,25,0,269,266,1,0,0,0,269,267,1,0,0,0,
        269,268,1,0,0,0,270,47,1,0,0,0,271,272,5,10,0,0,272,273,3,124,62,
        0,273,49,1,0,0,0,274,275,3,54,27,0,275,51,1,0,0,0,276,277,3,54,27,
        0,277,53,1,0,0,0,278,282,5,9,0,0,279,283,3,124,62,0,280,283,3,122,
        61,0,281,283,3,126,63,0,282,279,1,0,0,0,282,280,1,0,0,0,282,281,
        1,0,0,0,283,55,1,0,0,0,284,285,5,11,0,0,285,286,3,116,58,0,286,57,
        1,0,0,0,287,288,3,126,63,0,288,59,1,0,0,0,289,290,5,20,0,0,290,61,
        1,0,0,0,291,292,5,14,0,0,292,293,3,64,32,0,293,63,1,0,0,0,294,296,
        3,80,40,0,295,297,3,66,33,0,296,295,1,0,0,0,297,298,1,0,0,0,298,
        296,1,0,0,0,298,299,1,0,0,0,299,65,1,0,0,0,300,307,3,68,34,0,301,
        307,3,70,35,0,302,307,3,72,36,0,303,307,3,74,37,0,304,307,3,76,38,
        0,305,307,3,78,39,0,306,300,1,0,0,0,306,301,1,0,0,0,306,302,1,0,
        0,0,306,303,1,0,0,0,306,304,1,0,0,0,306,305,1,0,0,0,307,67,1,0,0,
        0,308,309,5,59,0,0,309,310,3,80,40,0,310,69,1,0,0,0,311,312,5,60,
        0,0,312,313,3,80,40,0,313,71,1,0,0,0,314,315,5,63,0,0,315,316,3,
        80,40,0,316,73,1,0,0,0,317,318,5,62,0,0,318,319,3,80,40,0,319,75,
        1,0,0,0,320,321,5,18,0,0,321,322,3,80,40,0,322,77,1,0,0,0,323,324,
        5,19,0,0,324,325,3,80,40,0,325,79,1,0,0,0,326,327,6,40,-1,0,327,
        328,3,82,41,0,328,334,1,0,0,0,329,330,10,2,0,0,330,331,7,3,0,0,331,
        333,3,82,41,0,332,329,1,0,0,0,333,336,1,0,0,0,334,332,1,0,0,0,334,
        335,1,0,0,0,335,81,1,0,0,0,336,334,1,0,0,0,337,338,6,41,-1,0,338,
        339,3,84,42,0,339,345,1,0,0,0,340,341,10,2,0,0,341,342,7,4,0,0,342,
        344,3,84,42,0,343,340,1,0,0,0,344,347,1,0,0,0,345,343,1,0,0,0,345,
        346,1,0,0,0,346,83,1,0,0,0,347,345,1,0,0,0,348,349,6,42,-1,0,349,
        350,3,86,43,0,350,356,1,0,0,0,351,352,10,2,0,0,352,353,7,5,0,0,353,
        355,3,86,43,0,354,351,1,0,0,0,355,358,1,0,0,0,356,354,1,0,0,0,356,
        357,1,0,0,0,357,85,1,0,0,0,358,356,1,0,0,0,359,362,3,88,44,0,360,
        361,5,44,0,0,361,363,3,88,44,0,362,360,1,0,0,0,362,363,1,0,0,0,363,
        87,1,0,0,0,364,375,3,90,45,0,365,366,3,124,62,0,366,368,5,39,0,0,
        367,369,3,90,45,0,368,367,1,0,0,0,369,370,1,0,0,0,370,368,1,0,0,
        0,370,371,1,0,0,0,371,372,1,0,0,0,372,373,5,40,0,0,373,375,1,0,0,
        0,374,364,1,0,0,0,374,365,1,0,0,0,375,89,1,0,0,0,376,377,3,92,46,
        0,377,91,1,0,0,0,378,382,3,114,57,0,379,382,3,96,48,0,380,382,3,
        94,47,0,381,378,1,0,0,0,381,379,1,0,0,0,381,380,1,0,0,0,382,93,1,
        0,0,0,383,384,5,39,0,0,384,385,3,80,40,0,385,386,5,40,0,0,386,95,
        1,0,0,0,387,391,3,98,49,0,388,391,3,100,50,0,389,391,3,102,51,0,
        390,387,1,0,0,0,390,388,1,0,0,0,390,389,1,0,0,0,391,97,1,0,0,0,392,
        393,3,102,51,0,393,394,5,15,0,0,394,395,3,102,51,0,395,99,1,0,0,
        0,396,397,3,102,51,0,397,398,5,32,0,0,398,399,3,104,52,0,399,101,
        1,0,0,0,400,402,7,4,0,0,401,400,1,0,0,0,401,402,1,0,0,0,402,403,
        1,0,0,0,403,405,5,4,0,0,404,406,3,124,62,0,405,404,1,0,0,0,405,406,
        1,0,0,0,406,103,1,0,0,0,407,410,5,4,0,0,408,411,5,35,0,0,409,411,
        3,124,62,0,410,408,1,0,0,0,410,409,1,0,0,0,410,411,1,0,0,0,411,105,
        1,0,0,0,412,413,5,4,0,0,413,107,1,0,0,0,414,415,5,46,0,0,415,416,
        3,106,53,0,416,417,5,47,0,0,417,109,1,0,0,0,418,419,5,36,0,0,419,
        420,5,4,0,0,420,111,1,0,0,0,421,423,3,124,62,0,422,424,3,108,54,
        0,423,422,1,0,0,0,423,424,1,0,0,0,424,113,1,0,0,0,425,430,3,112,
        56,0,426,427,5,36,0,0,427,429,3,112,56,0,428,426,1,0,0,0,429,432,
        1,0,0,0,430,428,1,0,0,0,430,431,1,0,0,0,431,434,1,0,0,0,432,430,
        1,0,0,0,433,435,3,110,55,0,434,433,1,0,0,0,434,435,1,0,0,0,435,115,
        1,0,0,0,436,441,3,124,62,0,437,438,5,36,0,0,438,440,3,124,62,0,439,
        437,1,0,0,0,440,443,1,0,0,0,441,439,1,0,0,0,441,442,1,0,0,0,442,
        117,1,0,0,0,443,441,1,0,0,0,444,445,3,124,62,0,445,119,1,0,0,0,446,
        447,5,42,0,0,447,448,3,118,59,0,448,121,1,0,0,0,449,450,5,4,0,0,
        450,123,1,0,0,0,451,452,5,23,0,0,452,125,1,0,0,0,453,454,5,3,0,0,
        454,127,1,0,0,0,455,456,7,6,0,0,456,129,1,0,0,0,34,132,134,141,148,
        152,170,177,193,197,206,214,222,240,247,258,269,282,298,306,334,
        345,356,362,370,374,381,390,401,405,410,423,430,434,441
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
                     "'within'", "'is'", "'pass'", "'~>'", "'~'", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "'+/-'", "'\\u00B1'", "'%'", "'.'", "'...'", 
                     "'*'", "'('", "')'", "','", "':'", "';'", "'**'", "'='", 
                     "'['", "']'", "'|'", "'^'", "'&'", "'<<'", "'>>'", 
                     "'+'", "'-'", "'/'", "'//'", "'{'", "'}'", "'<'", "'>'", 
                     "'=='", "'>='", "'<='", "'<>'", "'!='", "'@'", "'->'", 
                     "'+='", "'-='", "'*='", "'@='", "'/='", "'&='", "'|='", 
                     "'^='", "'<<='", "'>>='", "'**='", "'//='" ]

    symbolicNames = [ "<INVALID>", "INDENT", "DEDENT", "STRING", "NUMBER", 
                      "INTEGER", "COMPONENT", "MODULE", "INTERFACE", "PIN", 
                      "SIGNAL", "NEW", "FROM", "IMPORT", "ASSERT", "TO", 
                      "TRUE", "FALSE", "WITHIN", "IS", "PASS", "DIRECTED_CONNECT", 
                      "CONNECT", "NAME", "STRING_LITERAL", "BYTES_LITERAL", 
                      "DECIMAL_INTEGER", "OCT_INTEGER", "HEX_INTEGER", "BIN_INTEGER", 
                      "FLOAT_NUMBER", "IMAG_NUMBER", "PLUS_OR_MINUS", "PLUS_SLASH_MINUS", 
                      "PLUS_MINUS_SIGN", "PERCENT", "DOT", "ELLIPSIS", "STAR", 
                      "OPEN_PAREN", "CLOSE_PAREN", "COMMA", "COLON", "SEMI_COLON", 
                      "POWER", "ASSIGN", "OPEN_BRACK", "CLOSE_BRACK", "OR_OP", 
                      "XOR", "AND_OP", "LEFT_SHIFT", "RIGHT_SHIFT", "ADD", 
                      "MINUS", "DIV", "IDIV", "OPEN_BRACE", "CLOSE_BRACE", 
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
    RULE_field_reference_or_declaration = 12
    RULE_assign_stmt = 13
    RULE_cum_assign_stmt = 14
    RULE_set_assign_stmt = 15
    RULE_cum_operator = 16
    RULE_cum_assignable = 17
    RULE_assignable = 18
    RULE_retype_stmt = 19
    RULE_directed_connect_stmt = 20
    RULE_connect_stmt = 21
    RULE_bridgeable = 22
    RULE_connectable = 23
    RULE_signaldef_stmt = 24
    RULE_pindef_stmt = 25
    RULE_pin_declaration = 26
    RULE_pin_stmt = 27
    RULE_new_stmt = 28
    RULE_string_stmt = 29
    RULE_pass_stmt = 30
    RULE_assert_stmt = 31
    RULE_comparison = 32
    RULE_compare_op_pair = 33
    RULE_lt_arithmetic_or = 34
    RULE_gt_arithmetic_or = 35
    RULE_lt_eq_arithmetic_or = 36
    RULE_gt_eq_arithmetic_or = 37
    RULE_in_arithmetic_or = 38
    RULE_is_arithmetic_or = 39
    RULE_arithmetic_expression = 40
    RULE_sum = 41
    RULE_term = 42
    RULE_power = 43
    RULE_functional = 44
    RULE_bound = 45
    RULE_atom = 46
    RULE_arithmetic_group = 47
    RULE_literal_physical = 48
    RULE_bound_quantity = 49
    RULE_bilateral_quantity = 50
    RULE_quantity = 51
    RULE_bilateral_tolerance = 52
    RULE_key = 53
    RULE_array_index = 54
    RULE_pin_reference_end = 55
    RULE_field_reference_part = 56
    RULE_field_reference = 57
    RULE_type_reference = 58
    RULE_unit = 59
    RULE_type_info = 60
    RULE_totally_an_integer = 61
    RULE_name = 62
    RULE_string = 63
    RULE_boolean_ = 64

    ruleNames =  [ "file_input", "stmt", "simple_stmts", "simple_stmt", 
                   "compound_stmt", "blockdef", "blockdef_super", "blocktype", 
                   "block", "dep_import_stmt", "import_stmt", "declaration_stmt", 
                   "field_reference_or_declaration", "assign_stmt", "cum_assign_stmt", 
                   "set_assign_stmt", "cum_operator", "cum_assignable", 
                   "assignable", "retype_stmt", "directed_connect_stmt", 
                   "connect_stmt", "bridgeable", "connectable", "signaldef_stmt", 
                   "pindef_stmt", "pin_declaration", "pin_stmt", "new_stmt", 
                   "string_stmt", "pass_stmt", "assert_stmt", "comparison", 
                   "compare_op_pair", "lt_arithmetic_or", "gt_arithmetic_or", 
                   "lt_eq_arithmetic_or", "gt_eq_arithmetic_or", "in_arithmetic_or", 
                   "is_arithmetic_or", "arithmetic_expression", "sum", "term", 
                   "power", "functional", "bound", "atom", "arithmetic_group", 
                   "literal_physical", "bound_quantity", "bilateral_quantity", 
                   "quantity", "bilateral_tolerance", "key", "array_index", 
                   "pin_reference_end", "field_reference_part", "field_reference", 
                   "type_reference", "unit", "type_info", "totally_an_integer", 
                   "name", "string", "boolean_" ]

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
    DIRECTED_CONNECT=21
    CONNECT=22
    NAME=23
    STRING_LITERAL=24
    BYTES_LITERAL=25
    DECIMAL_INTEGER=26
    OCT_INTEGER=27
    HEX_INTEGER=28
    BIN_INTEGER=29
    FLOAT_NUMBER=30
    IMAG_NUMBER=31
    PLUS_OR_MINUS=32
    PLUS_SLASH_MINUS=33
    PLUS_MINUS_SIGN=34
    PERCENT=35
    DOT=36
    ELLIPSIS=37
    STAR=38
    OPEN_PAREN=39
    CLOSE_PAREN=40
    COMMA=41
    COLON=42
    SEMI_COLON=43
    POWER=44
    ASSIGN=45
    OPEN_BRACK=46
    CLOSE_BRACK=47
    OR_OP=48
    XOR=49
    AND_OP=50
    LEFT_SHIFT=51
    RIGHT_SHIFT=52
    ADD=53
    MINUS=54
    DIV=55
    IDIV=56
    OPEN_BRACE=57
    CLOSE_BRACE=58
    LESS_THAN=59
    GREATER_THAN=60
    EQUALS=61
    GT_EQ=62
    LT_EQ=63
    NOT_EQ_1=64
    NOT_EQ_2=65
    AT=66
    ARROW=67
    ADD_ASSIGN=68
    SUB_ASSIGN=69
    MULT_ASSIGN=70
    AT_ASSIGN=71
    DIV_ASSIGN=72
    AND_ASSIGN=73
    OR_ASSIGN=74
    XOR_ASSIGN=75
    LEFT_SHIFT_ASSIGN=76
    RIGHT_SHIFT_ASSIGN=77
    POWER_ASSIGN=78
    IDIV_ASSIGN=79
    NEWLINE=80
    COMMENT=81
    WS=82
    EXPLICIT_LINE_JOINING=83
    ERRORTOKEN=84

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
            self.state = 134
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 9467848) != 0) or _la==80:
                self.state = 132
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [80]:
                    self.state = 130
                    self.match(AtoParser.NEWLINE)
                    pass
                elif token in [3, 6, 7, 8, 9, 10, 12, 13, 14, 20, 23]:
                    self.state = 131
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 136
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 137
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
            self.state = 141
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 14, 20, 23]:
                self.enterOuterAlt(localctx, 1)
                self.state = 139
                self.simple_stmts()
                pass
            elif token in [6, 7, 8]:
                self.enterOuterAlt(localctx, 2)
                self.state = 140
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
            self.state = 143
            self.simple_stmt()
            self.state = 148
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 144
                    self.match(AtoParser.SEMI_COLON)
                    self.state = 145
                    self.simple_stmt() 
                self.state = 150
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 152
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==43:
                self.state = 151
                self.match(AtoParser.SEMI_COLON)


            self.state = 154
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


        def directed_connect_stmt(self):
            return self.getTypedRuleContext(AtoParser.Directed_connect_stmtContext,0)


        def retype_stmt(self):
            return self.getTypedRuleContext(AtoParser.Retype_stmtContext,0)


        def pin_declaration(self):
            return self.getTypedRuleContext(AtoParser.Pin_declarationContext,0)


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
            self.state = 170
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 156
                self.import_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 157
                self.dep_import_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 158
                self.assign_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 159
                self.cum_assign_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 160
                self.set_assign_stmt()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 161
                self.connect_stmt()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 162
                self.directed_connect_stmt()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 163
                self.retype_stmt()
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 164
                self.pin_declaration()
                pass

            elif la_ == 10:
                self.enterOuterAlt(localctx, 10)
                self.state = 165
                self.signaldef_stmt()
                pass

            elif la_ == 11:
                self.enterOuterAlt(localctx, 11)
                self.state = 166
                self.assert_stmt()
                pass

            elif la_ == 12:
                self.enterOuterAlt(localctx, 12)
                self.state = 167
                self.declaration_stmt()
                pass

            elif la_ == 13:
                self.enterOuterAlt(localctx, 13)
                self.state = 168
                self.string_stmt()
                pass

            elif la_ == 14:
                self.enterOuterAlt(localctx, 14)
                self.state = 169
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
            self.state = 172
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
            self.state = 174
            self.blocktype()
            self.state = 175
            self.name()
            self.state = 177
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 176
                self.blockdef_super()


            self.state = 179
            self.match(AtoParser.COLON)
            self.state = 180
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

        def type_reference(self):
            return self.getTypedRuleContext(AtoParser.Type_referenceContext,0)


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
            self.state = 182
            self.match(AtoParser.FROM)
            self.state = 183
            self.type_reference()
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
            self.state = 185
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
            self.state = 197
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 14, 20, 23]:
                self.enterOuterAlt(localctx, 1)
                self.state = 187
                self.simple_stmts()
                pass
            elif token in [80]:
                self.enterOuterAlt(localctx, 2)
                self.state = 188
                self.match(AtoParser.NEWLINE)
                self.state = 189
                self.match(AtoParser.INDENT)
                self.state = 191 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 190
                    self.stmt()
                    self.state = 193 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 9467848) != 0)):
                        break

                self.state = 195
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

        def type_reference(self):
            return self.getTypedRuleContext(AtoParser.Type_referenceContext,0)


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
            self.state = 199
            self.match(AtoParser.IMPORT)
            self.state = 200
            self.type_reference()
            self.state = 201
            self.match(AtoParser.FROM)
            self.state = 202
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

        def type_reference(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtoParser.Type_referenceContext)
            else:
                return self.getTypedRuleContext(AtoParser.Type_referenceContext,i)


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
            self.state = 206
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 204
                self.match(AtoParser.FROM)
                self.state = 205
                self.string()


            self.state = 208
            self.match(AtoParser.IMPORT)
            self.state = 209
            self.type_reference()
            self.state = 214
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==41:
                self.state = 210
                self.match(AtoParser.COMMA)
                self.state = 211
                self.type_reference()
                self.state = 216
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

        def field_reference(self):
            return self.getTypedRuleContext(AtoParser.Field_referenceContext,0)


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
            self.state = 217
            self.field_reference()
            self.state = 218
            self.type_info()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Field_reference_or_declarationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def field_reference(self):
            return self.getTypedRuleContext(AtoParser.Field_referenceContext,0)


        def declaration_stmt(self):
            return self.getTypedRuleContext(AtoParser.Declaration_stmtContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_field_reference_or_declaration

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitField_reference_or_declaration" ):
                return visitor.visitField_reference_or_declaration(self)
            else:
                return visitor.visitChildren(self)




    def field_reference_or_declaration(self):

        localctx = AtoParser.Field_reference_or_declarationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_field_reference_or_declaration)
        try:
            self.state = 222
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,11,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 220
                self.field_reference()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 221
                self.declaration_stmt()
                pass


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

        def field_reference_or_declaration(self):
            return self.getTypedRuleContext(AtoParser.Field_reference_or_declarationContext,0)


        def ASSIGN(self):
            return self.getToken(AtoParser.ASSIGN, 0)

        def assignable(self):
            return self.getTypedRuleContext(AtoParser.AssignableContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_assign_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssign_stmt" ):
                return visitor.visitAssign_stmt(self)
            else:
                return visitor.visitChildren(self)




    def assign_stmt(self):

        localctx = AtoParser.Assign_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_assign_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 224
            self.field_reference_or_declaration()
            self.state = 225
            self.match(AtoParser.ASSIGN)
            self.state = 226
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

        def field_reference_or_declaration(self):
            return self.getTypedRuleContext(AtoParser.Field_reference_or_declarationContext,0)


        def cum_operator(self):
            return self.getTypedRuleContext(AtoParser.Cum_operatorContext,0)


        def cum_assignable(self):
            return self.getTypedRuleContext(AtoParser.Cum_assignableContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_cum_assign_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCum_assign_stmt" ):
                return visitor.visitCum_assign_stmt(self)
            else:
                return visitor.visitChildren(self)




    def cum_assign_stmt(self):

        localctx = AtoParser.Cum_assign_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_cum_assign_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 228
            self.field_reference_or_declaration()
            self.state = 229
            self.cum_operator()
            self.state = 230
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

        def field_reference_or_declaration(self):
            return self.getTypedRuleContext(AtoParser.Field_reference_or_declarationContext,0)


        def cum_assignable(self):
            return self.getTypedRuleContext(AtoParser.Cum_assignableContext,0)


        def OR_ASSIGN(self):
            return self.getToken(AtoParser.OR_ASSIGN, 0)

        def AND_ASSIGN(self):
            return self.getToken(AtoParser.AND_ASSIGN, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_set_assign_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSet_assign_stmt" ):
                return visitor.visitSet_assign_stmt(self)
            else:
                return visitor.visitChildren(self)




    def set_assign_stmt(self):

        localctx = AtoParser.Set_assign_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_set_assign_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 232
            self.field_reference_or_declaration()
            self.state = 233
            _la = self._input.LA(1)
            if not(_la==73 or _la==74):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 234
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
        self.enterRule(localctx, 32, self.RULE_cum_operator)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 236
            _la = self._input.LA(1)
            if not(_la==68 or _la==69):
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
        self.enterRule(localctx, 34, self.RULE_cum_assignable)
        try:
            self.state = 240
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 238
                self.literal_physical()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 239
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
        self.enterRule(localctx, 36, self.RULE_assignable)
        try:
            self.state = 247
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 242
                self.string()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 243
                self.new_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 244
                self.literal_physical()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 245
                self.arithmetic_expression(0)
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 246
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

        def field_reference(self):
            return self.getTypedRuleContext(AtoParser.Field_referenceContext,0)


        def ARROW(self):
            return self.getToken(AtoParser.ARROW, 0)

        def type_reference(self):
            return self.getTypedRuleContext(AtoParser.Type_referenceContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_retype_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRetype_stmt" ):
                return visitor.visitRetype_stmt(self)
            else:
                return visitor.visitChildren(self)




    def retype_stmt(self):

        localctx = AtoParser.Retype_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_retype_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 249
            self.field_reference()
            self.state = 250
            self.match(AtoParser.ARROW)
            self.state = 251
            self.type_reference()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Directed_connect_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def connectable(self):
            return self.getTypedRuleContext(AtoParser.ConnectableContext,0)


        def DIRECTED_CONNECT(self, i:int=None):
            if i is None:
                return self.getTokens(AtoParser.DIRECTED_CONNECT)
            else:
                return self.getToken(AtoParser.DIRECTED_CONNECT, i)

        def bridgeable(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtoParser.BridgeableContext)
            else:
                return self.getTypedRuleContext(AtoParser.BridgeableContext,i)


        def getRuleIndex(self):
            return AtoParser.RULE_directed_connect_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDirected_connect_stmt" ):
                return visitor.visitDirected_connect_stmt(self)
            else:
                return visitor.visitChildren(self)




    def directed_connect_stmt(self):

        localctx = AtoParser.Directed_connect_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_directed_connect_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 253
            self.connectable()
            self.state = 256 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 254
                self.match(AtoParser.DIRECTED_CONNECT)
                self.state = 255
                self.bridgeable()
                self.state = 258 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==21):
                    break

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


        def CONNECT(self):
            return self.getToken(AtoParser.CONNECT, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_connect_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConnect_stmt" ):
                return visitor.visitConnect_stmt(self)
            else:
                return visitor.visitChildren(self)




    def connect_stmt(self):

        localctx = AtoParser.Connect_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 260
            self.connectable()
            self.state = 261
            self.match(AtoParser.CONNECT)
            self.state = 262
            self.connectable()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BridgeableContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def field_reference(self):
            return self.getTypedRuleContext(AtoParser.Field_referenceContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_bridgeable

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBridgeable" ):
                return visitor.visitBridgeable(self)
            else:
                return visitor.visitChildren(self)




    def bridgeable(self):

        localctx = AtoParser.BridgeableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_bridgeable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 264
            self.field_reference()
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

        def field_reference(self):
            return self.getTypedRuleContext(AtoParser.Field_referenceContext,0)


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
        self.enterRule(localctx, 46, self.RULE_connectable)
        try:
            self.state = 269
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [23]:
                self.enterOuterAlt(localctx, 1)
                self.state = 266
                self.field_reference()
                pass
            elif token in [10]:
                self.enterOuterAlt(localctx, 2)
                self.state = 267
                self.signaldef_stmt()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 3)
                self.state = 268
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
        self.enterRule(localctx, 48, self.RULE_signaldef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 271
            self.match(AtoParser.SIGNAL)
            self.state = 272
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

        def pin_stmt(self):
            return self.getTypedRuleContext(AtoParser.Pin_stmtContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_pindef_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPindef_stmt" ):
                return visitor.visitPindef_stmt(self)
            else:
                return visitor.visitChildren(self)




    def pindef_stmt(self):

        localctx = AtoParser.Pindef_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_pindef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 274
            self.pin_stmt()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Pin_declarationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def pin_stmt(self):
            return self.getTypedRuleContext(AtoParser.Pin_stmtContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_pin_declaration

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPin_declaration" ):
                return visitor.visitPin_declaration(self)
            else:
                return visitor.visitChildren(self)




    def pin_declaration(self):

        localctx = AtoParser.Pin_declarationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_pin_declaration)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 276
            self.pin_stmt()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Pin_stmtContext(ParserRuleContext):
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
            return AtoParser.RULE_pin_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPin_stmt" ):
                return visitor.visitPin_stmt(self)
            else:
                return visitor.visitChildren(self)




    def pin_stmt(self):

        localctx = AtoParser.Pin_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_pin_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 278
            self.match(AtoParser.PIN)
            self.state = 282
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [23]:
                self.state = 279
                self.name()
                pass
            elif token in [4]:
                self.state = 280
                self.totally_an_integer()
                pass
            elif token in [3]:
                self.state = 281
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

        def type_reference(self):
            return self.getTypedRuleContext(AtoParser.Type_referenceContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_new_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNew_stmt" ):
                return visitor.visitNew_stmt(self)
            else:
                return visitor.visitChildren(self)




    def new_stmt(self):

        localctx = AtoParser.New_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_new_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 284
            self.match(AtoParser.NEW)
            self.state = 285
            self.type_reference()
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
        self.enterRule(localctx, 58, self.RULE_string_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 287
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
        self.enterRule(localctx, 60, self.RULE_pass_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 289
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
        self.enterRule(localctx, 62, self.RULE_assert_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 291
            self.match(AtoParser.ASSERT)
            self.state = 292
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
        self.enterRule(localctx, 64, self.RULE_comparison)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 294
            self.arithmetic_expression(0)
            self.state = 296 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 295
                self.compare_op_pair()
                self.state = 298 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & -2882303761516331008) != 0)):
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
        self.enterRule(localctx, 66, self.RULE_compare_op_pair)
        try:
            self.state = 306
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [59]:
                self.enterOuterAlt(localctx, 1)
                self.state = 300
                self.lt_arithmetic_or()
                pass
            elif token in [60]:
                self.enterOuterAlt(localctx, 2)
                self.state = 301
                self.gt_arithmetic_or()
                pass
            elif token in [63]:
                self.enterOuterAlt(localctx, 3)
                self.state = 302
                self.lt_eq_arithmetic_or()
                pass
            elif token in [62]:
                self.enterOuterAlt(localctx, 4)
                self.state = 303
                self.gt_eq_arithmetic_or()
                pass
            elif token in [18]:
                self.enterOuterAlt(localctx, 5)
                self.state = 304
                self.in_arithmetic_or()
                pass
            elif token in [19]:
                self.enterOuterAlt(localctx, 6)
                self.state = 305
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
        self.enterRule(localctx, 68, self.RULE_lt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 308
            self.match(AtoParser.LESS_THAN)
            self.state = 309
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
        self.enterRule(localctx, 70, self.RULE_gt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 311
            self.match(AtoParser.GREATER_THAN)
            self.state = 312
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
        self.enterRule(localctx, 72, self.RULE_lt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 314
            self.match(AtoParser.LT_EQ)
            self.state = 315
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
        self.enterRule(localctx, 74, self.RULE_gt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 317
            self.match(AtoParser.GT_EQ)
            self.state = 318
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
        self.enterRule(localctx, 76, self.RULE_in_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 320
            self.match(AtoParser.WITHIN)
            self.state = 321
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
        self.enterRule(localctx, 78, self.RULE_is_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 323
            self.match(AtoParser.IS)
            self.state = 324
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
        _startState = 80
        self.enterRecursionRule(localctx, 80, self.RULE_arithmetic_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 327
            self.sum_(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 334
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,19,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.Arithmetic_expressionContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmetic_expression)
                    self.state = 329
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 330
                    _la = self._input.LA(1)
                    if not(_la==48 or _la==50):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 331
                    self.sum_(0) 
                self.state = 336
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,19,self._ctx)

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
        _startState = 82
        self.enterRecursionRule(localctx, 82, self.RULE_sum, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 338
            self.term(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 345
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,20,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.SumContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_sum)
                    self.state = 340
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 341
                    _la = self._input.LA(1)
                    if not(_la==53 or _la==54):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 342
                    self.term(0) 
                self.state = 347
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,20,self._ctx)

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
        _startState = 84
        self.enterRecursionRule(localctx, 84, self.RULE_term, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 349
            self.power()
            self._ctx.stop = self._input.LT(-1)
            self.state = 356
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,21,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.TermContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_term)
                    self.state = 351
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 352
                    _la = self._input.LA(1)
                    if not(_la==38 or _la==55):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 353
                    self.power() 
                self.state = 358
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,21,self._ctx)

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
        self.enterRule(localctx, 86, self.RULE_power)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 359
            self.functional()
            self.state = 362
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,22,self._ctx)
            if la_ == 1:
                self.state = 360
                self.match(AtoParser.POWER)
                self.state = 361
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
        self.enterRule(localctx, 88, self.RULE_functional)
        self._la = 0 # Token type
        try:
            self.state = 374
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,24,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 364
                self.bound()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 365
                self.name()
                self.state = 366
                self.match(AtoParser.OPEN_PAREN)
                self.state = 368 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 367
                    self.bound()
                    self.state = 370 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 27022147528425488) != 0)):
                        break

                self.state = 372
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
        self.enterRule(localctx, 90, self.RULE_bound)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 376
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

        def field_reference(self):
            return self.getTypedRuleContext(AtoParser.Field_referenceContext,0)


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
        self.enterRule(localctx, 92, self.RULE_atom)
        try:
            self.state = 381
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [23]:
                self.enterOuterAlt(localctx, 1)
                self.state = 378
                self.field_reference()
                pass
            elif token in [4, 53, 54]:
                self.enterOuterAlt(localctx, 2)
                self.state = 379
                self.literal_physical()
                pass
            elif token in [39]:
                self.enterOuterAlt(localctx, 3)
                self.state = 380
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
        self.enterRule(localctx, 94, self.RULE_arithmetic_group)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 383
            self.match(AtoParser.OPEN_PAREN)
            self.state = 384
            self.arithmetic_expression(0)
            self.state = 385
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
        self.enterRule(localctx, 96, self.RULE_literal_physical)
        try:
            self.state = 390
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,26,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 387
                self.bound_quantity()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 388
                self.bilateral_quantity()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 389
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
        self.enterRule(localctx, 98, self.RULE_bound_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 392
            self.quantity()
            self.state = 393
            self.match(AtoParser.TO)
            self.state = 394
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
        self.enterRule(localctx, 100, self.RULE_bilateral_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 396
            self.quantity()
            self.state = 397
            self.match(AtoParser.PLUS_OR_MINUS)
            self.state = 398
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
        self.enterRule(localctx, 102, self.RULE_quantity)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 401
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==53 or _la==54:
                self.state = 400
                _la = self._input.LA(1)
                if not(_la==53 or _la==54):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()


            self.state = 403
            self.match(AtoParser.NUMBER)
            self.state = 405
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,28,self._ctx)
            if la_ == 1:
                self.state = 404
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
        self.enterRule(localctx, 104, self.RULE_bilateral_tolerance)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 407
            self.match(AtoParser.NUMBER)
            self.state = 410
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,29,self._ctx)
            if la_ == 1:
                self.state = 408
                self.match(AtoParser.PERCENT)

            elif la_ == 2:
                self.state = 409
                self.name()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class KeyContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self):
            return self.getToken(AtoParser.NUMBER, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_key

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitKey" ):
                return visitor.visitKey(self)
            else:
                return visitor.visitChildren(self)




    def key(self):

        localctx = AtoParser.KeyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 106, self.RULE_key)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 412
            self.match(AtoParser.NUMBER)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Array_indexContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def OPEN_BRACK(self):
            return self.getToken(AtoParser.OPEN_BRACK, 0)

        def key(self):
            return self.getTypedRuleContext(AtoParser.KeyContext,0)


        def CLOSE_BRACK(self):
            return self.getToken(AtoParser.CLOSE_BRACK, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_array_index

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArray_index" ):
                return visitor.visitArray_index(self)
            else:
                return visitor.visitChildren(self)




    def array_index(self):

        localctx = AtoParser.Array_indexContext(self, self._ctx, self.state)
        self.enterRule(localctx, 108, self.RULE_array_index)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 414
            self.match(AtoParser.OPEN_BRACK)
            self.state = 415
            self.key()
            self.state = 416
            self.match(AtoParser.CLOSE_BRACK)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Pin_reference_endContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def DOT(self):
            return self.getToken(AtoParser.DOT, 0)

        def NUMBER(self):
            return self.getToken(AtoParser.NUMBER, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_pin_reference_end

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPin_reference_end" ):
                return visitor.visitPin_reference_end(self)
            else:
                return visitor.visitChildren(self)




    def pin_reference_end(self):

        localctx = AtoParser.Pin_reference_endContext(self, self._ctx, self.state)
        self.enterRule(localctx, 110, self.RULE_pin_reference_end)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 418
            self.match(AtoParser.DOT)
            self.state = 419
            self.match(AtoParser.NUMBER)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Field_reference_partContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def array_index(self):
            return self.getTypedRuleContext(AtoParser.Array_indexContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_field_reference_part

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitField_reference_part" ):
                return visitor.visitField_reference_part(self)
            else:
                return visitor.visitChildren(self)




    def field_reference_part(self):

        localctx = AtoParser.Field_reference_partContext(self, self._ctx, self.state)
        self.enterRule(localctx, 112, self.RULE_field_reference_part)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 421
            self.name()
            self.state = 423
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,30,self._ctx)
            if la_ == 1:
                self.state = 422
                self.array_index()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Field_referenceContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def field_reference_part(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtoParser.Field_reference_partContext)
            else:
                return self.getTypedRuleContext(AtoParser.Field_reference_partContext,i)


        def DOT(self, i:int=None):
            if i is None:
                return self.getTokens(AtoParser.DOT)
            else:
                return self.getToken(AtoParser.DOT, i)

        def pin_reference_end(self):
            return self.getTypedRuleContext(AtoParser.Pin_reference_endContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_field_reference

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitField_reference" ):
                return visitor.visitField_reference(self)
            else:
                return visitor.visitChildren(self)




    def field_reference(self):

        localctx = AtoParser.Field_referenceContext(self, self._ctx, self.state)
        self.enterRule(localctx, 114, self.RULE_field_reference)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 425
            self.field_reference_part()
            self.state = 430
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,31,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 426
                    self.match(AtoParser.DOT)
                    self.state = 427
                    self.field_reference_part() 
                self.state = 432
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,31,self._ctx)

            self.state = 434
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,32,self._ctx)
            if la_ == 1:
                self.state = 433
                self.pin_reference_end()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Type_referenceContext(ParserRuleContext):
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
            return AtoParser.RULE_type_reference

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitType_reference" ):
                return visitor.visitType_reference(self)
            else:
                return visitor.visitChildren(self)




    def type_reference(self):

        localctx = AtoParser.Type_referenceContext(self, self._ctx, self.state)
        self.enterRule(localctx, 116, self.RULE_type_reference)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 436
            self.name()
            self.state = 441
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==36:
                self.state = 437
                self.match(AtoParser.DOT)
                self.state = 438
                self.name()
                self.state = 443
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class UnitContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_unit

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUnit" ):
                return visitor.visitUnit(self)
            else:
                return visitor.visitChildren(self)




    def unit(self):

        localctx = AtoParser.UnitContext(self, self._ctx, self.state)
        self.enterRule(localctx, 118, self.RULE_unit)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 444
            self.name()
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

        def unit(self):
            return self.getTypedRuleContext(AtoParser.UnitContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_type_info

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitType_info" ):
                return visitor.visitType_info(self)
            else:
                return visitor.visitChildren(self)




    def type_info(self):

        localctx = AtoParser.Type_infoContext(self, self._ctx, self.state)
        self.enterRule(localctx, 120, self.RULE_type_info)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 446
            self.match(AtoParser.COLON)
            self.state = 447
            self.unit()
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
        self.enterRule(localctx, 122, self.RULE_totally_an_integer)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 449
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
        self.enterRule(localctx, 124, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 451
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
        self.enterRule(localctx, 126, self.RULE_string)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 453
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
        self.enterRule(localctx, 128, self.RULE_boolean_)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 455
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
        self._predicates[40] = self.arithmetic_expression_sempred
        self._predicates[41] = self.sum_sempred
        self._predicates[42] = self.term_sempred
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
         




