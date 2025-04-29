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
        4,1,87,475,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,2,39,7,39,
        2,40,7,40,2,41,7,41,2,42,7,42,2,43,7,43,2,44,7,44,2,45,7,45,2,46,
        7,46,2,47,7,47,2,48,7,48,2,49,7,49,2,50,7,50,2,51,7,51,2,52,7,52,
        2,53,7,53,2,54,7,54,2,55,7,55,2,56,7,56,2,57,7,57,2,58,7,58,2,59,
        7,59,2,60,7,60,2,61,7,61,2,62,7,62,2,63,7,63,2,64,7,64,2,65,7,65,
        2,66,7,66,1,0,1,0,5,0,137,8,0,10,0,12,0,140,9,0,1,0,1,0,1,1,1,1,
        1,2,1,2,1,2,3,2,149,8,2,1,3,1,3,1,3,5,3,154,8,3,10,3,12,3,157,9,
        3,1,3,3,3,160,8,3,1,3,1,3,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,
        4,1,4,1,4,1,4,1,4,3,4,178,8,4,1,5,1,5,3,5,182,8,5,1,6,1,6,1,6,3,
        6,187,8,6,1,6,1,6,1,6,1,7,1,7,1,7,1,8,1,8,1,9,1,9,1,9,1,9,4,9,201,
        8,9,11,9,12,9,202,1,9,1,9,3,9,207,8,9,1,10,1,10,1,10,1,10,1,10,1,
        11,1,11,3,11,216,8,11,1,11,1,11,1,11,1,11,5,11,222,8,11,10,11,12,
        11,225,9,11,1,12,1,12,1,12,1,13,1,13,3,13,232,8,13,1,14,1,14,1,14,
        1,14,1,15,1,15,1,15,1,15,1,16,1,16,1,16,1,16,1,17,1,17,1,18,1,18,
        3,18,250,8,18,1,19,1,19,1,19,1,19,1,19,3,19,257,8,19,1,20,1,20,1,
        20,1,20,1,21,1,21,1,21,1,21,1,22,1,22,1,22,3,22,270,8,22,1,23,1,
        23,1,23,1,24,1,24,1,25,1,25,1,26,1,26,1,26,1,26,3,26,283,8,26,1,
        27,1,27,1,27,1,27,1,27,1,27,3,27,291,8,27,1,28,1,28,1,29,1,29,1,
        30,1,30,1,31,1,31,1,31,1,31,1,31,1,31,1,31,1,32,1,32,1,32,1,33,1,
        33,1,33,1,34,1,34,4,34,314,8,34,11,34,12,34,315,1,35,1,35,1,35,1,
        35,1,35,1,35,3,35,324,8,35,1,36,1,36,1,36,1,37,1,37,1,37,1,38,1,
        38,1,38,1,39,1,39,1,39,1,40,1,40,1,40,1,41,1,41,1,41,1,42,1,42,1,
        42,1,42,1,42,1,42,5,42,350,8,42,10,42,12,42,353,9,42,1,43,1,43,1,
        43,1,43,1,43,1,43,5,43,361,8,43,10,43,12,43,364,9,43,1,44,1,44,1,
        44,1,44,1,44,1,44,5,44,372,8,44,10,44,12,44,375,9,44,1,45,1,45,1,
        45,3,45,380,8,45,1,46,1,46,1,46,1,46,4,46,386,8,46,11,46,12,46,387,
        1,46,1,46,3,46,392,8,46,1,47,1,47,1,48,1,48,1,48,3,48,399,8,48,1,
        49,1,49,1,49,1,49,1,50,1,50,1,50,3,50,408,8,50,1,51,1,51,1,51,1,
        51,1,52,1,52,1,52,1,52,1,53,3,53,419,8,53,1,53,1,53,3,53,423,8,53,
        1,54,1,54,1,54,3,54,428,8,54,1,55,1,55,1,56,1,56,1,56,1,56,1,57,
        1,57,1,57,1,58,1,58,3,58,441,8,58,1,59,1,59,1,59,5,59,446,8,59,10,
        59,12,59,449,9,59,1,59,3,59,452,8,59,1,60,1,60,1,60,5,60,457,8,60,
        10,60,12,60,460,9,60,1,61,1,61,1,62,1,62,1,62,1,63,1,63,1,64,1,64,
        1,65,1,65,1,66,1,66,1,66,0,3,84,86,88,67,0,2,4,6,8,10,12,14,16,18,
        20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,54,56,58,60,62,
        64,66,68,70,72,74,76,78,80,82,84,86,88,90,92,94,96,98,100,102,104,
        106,108,110,112,114,116,118,120,122,124,126,128,130,132,0,7,1,0,
        6,8,1,0,75,76,1,0,70,71,2,0,49,49,51,51,1,0,54,55,2,0,39,39,56,56,
        1,0,18,19,467,0,138,1,0,0,0,2,143,1,0,0,0,4,148,1,0,0,0,6,150,1,
        0,0,0,8,177,1,0,0,0,10,181,1,0,0,0,12,183,1,0,0,0,14,191,1,0,0,0,
        16,194,1,0,0,0,18,206,1,0,0,0,20,208,1,0,0,0,22,215,1,0,0,0,24,226,
        1,0,0,0,26,231,1,0,0,0,28,233,1,0,0,0,30,237,1,0,0,0,32,241,1,0,
        0,0,34,245,1,0,0,0,36,249,1,0,0,0,38,256,1,0,0,0,40,258,1,0,0,0,
        42,262,1,0,0,0,44,269,1,0,0,0,46,271,1,0,0,0,48,274,1,0,0,0,50,276,
        1,0,0,0,52,278,1,0,0,0,54,284,1,0,0,0,56,292,1,0,0,0,58,294,1,0,
        0,0,60,296,1,0,0,0,62,298,1,0,0,0,64,305,1,0,0,0,66,308,1,0,0,0,
        68,311,1,0,0,0,70,323,1,0,0,0,72,325,1,0,0,0,74,328,1,0,0,0,76,331,
        1,0,0,0,78,334,1,0,0,0,80,337,1,0,0,0,82,340,1,0,0,0,84,343,1,0,
        0,0,86,354,1,0,0,0,88,365,1,0,0,0,90,376,1,0,0,0,92,391,1,0,0,0,
        94,393,1,0,0,0,96,398,1,0,0,0,98,400,1,0,0,0,100,407,1,0,0,0,102,
        409,1,0,0,0,104,413,1,0,0,0,106,418,1,0,0,0,108,424,1,0,0,0,110,
        429,1,0,0,0,112,431,1,0,0,0,114,435,1,0,0,0,116,438,1,0,0,0,118,
        442,1,0,0,0,120,453,1,0,0,0,122,461,1,0,0,0,124,463,1,0,0,0,126,
        466,1,0,0,0,128,468,1,0,0,0,130,470,1,0,0,0,132,472,1,0,0,0,134,
        137,5,82,0,0,135,137,3,4,2,0,136,134,1,0,0,0,136,135,1,0,0,0,137,
        140,1,0,0,0,138,136,1,0,0,0,138,139,1,0,0,0,139,141,1,0,0,0,140,
        138,1,0,0,0,141,142,5,0,0,1,142,1,1,0,0,0,143,144,5,83,0,0,144,3,
        1,0,0,0,145,149,3,6,3,0,146,149,3,10,5,0,147,149,3,2,1,0,148,145,
        1,0,0,0,148,146,1,0,0,0,148,147,1,0,0,0,149,5,1,0,0,0,150,155,3,
        8,4,0,151,152,5,44,0,0,152,154,3,8,4,0,153,151,1,0,0,0,154,157,1,
        0,0,0,155,153,1,0,0,0,155,156,1,0,0,0,156,159,1,0,0,0,157,155,1,
        0,0,0,158,160,5,44,0,0,159,158,1,0,0,0,159,160,1,0,0,0,160,161,1,
        0,0,0,161,162,5,82,0,0,162,7,1,0,0,0,163,178,3,22,11,0,164,178,3,
        20,10,0,165,178,3,28,14,0,166,178,3,30,15,0,167,178,3,32,16,0,168,
        178,3,42,21,0,169,178,3,40,20,0,170,178,3,50,25,0,171,178,3,46,23,
        0,172,178,3,64,32,0,173,178,3,24,12,0,174,178,3,58,29,0,175,178,
        3,60,30,0,176,178,3,66,33,0,177,163,1,0,0,0,177,164,1,0,0,0,177,
        165,1,0,0,0,177,166,1,0,0,0,177,167,1,0,0,0,177,168,1,0,0,0,177,
        169,1,0,0,0,177,170,1,0,0,0,177,171,1,0,0,0,177,172,1,0,0,0,177,
        173,1,0,0,0,177,174,1,0,0,0,177,175,1,0,0,0,177,176,1,0,0,0,178,
        9,1,0,0,0,179,182,3,12,6,0,180,182,3,62,31,0,181,179,1,0,0,0,181,
        180,1,0,0,0,182,11,1,0,0,0,183,184,3,16,8,0,184,186,3,128,64,0,185,
        187,3,14,7,0,186,185,1,0,0,0,186,187,1,0,0,0,187,188,1,0,0,0,188,
        189,5,43,0,0,189,190,3,18,9,0,190,13,1,0,0,0,191,192,5,12,0,0,192,
        193,3,120,60,0,193,15,1,0,0,0,194,195,7,0,0,0,195,17,1,0,0,0,196,
        207,3,6,3,0,197,198,5,82,0,0,198,200,5,1,0,0,199,201,3,4,2,0,200,
        199,1,0,0,0,201,202,1,0,0,0,202,200,1,0,0,0,202,203,1,0,0,0,203,
        204,1,0,0,0,204,205,5,2,0,0,205,207,1,0,0,0,206,196,1,0,0,0,206,
        197,1,0,0,0,207,19,1,0,0,0,208,209,5,13,0,0,209,210,3,120,60,0,210,
        211,5,12,0,0,211,212,3,130,65,0,212,21,1,0,0,0,213,214,5,12,0,0,
        214,216,3,130,65,0,215,213,1,0,0,0,215,216,1,0,0,0,216,217,1,0,0,
        0,217,218,5,13,0,0,218,223,3,120,60,0,219,220,5,42,0,0,220,222,3,
        120,60,0,221,219,1,0,0,0,222,225,1,0,0,0,223,221,1,0,0,0,223,224,
        1,0,0,0,224,23,1,0,0,0,225,223,1,0,0,0,226,227,3,118,59,0,227,228,
        3,124,62,0,228,25,1,0,0,0,229,232,3,118,59,0,230,232,3,24,12,0,231,
        229,1,0,0,0,231,230,1,0,0,0,232,27,1,0,0,0,233,234,3,26,13,0,234,
        235,5,46,0,0,235,236,3,38,19,0,236,29,1,0,0,0,237,238,3,26,13,0,
        238,239,3,34,17,0,239,240,3,36,18,0,240,31,1,0,0,0,241,242,3,26,
        13,0,242,243,7,1,0,0,243,244,3,36,18,0,244,33,1,0,0,0,245,246,7,
        2,0,0,246,35,1,0,0,0,247,250,3,100,50,0,248,250,3,84,42,0,249,247,
        1,0,0,0,249,248,1,0,0,0,250,37,1,0,0,0,251,257,3,130,65,0,252,257,
        3,54,27,0,253,257,3,100,50,0,254,257,3,84,42,0,255,257,3,132,66,
        0,256,251,1,0,0,0,256,252,1,0,0,0,256,253,1,0,0,0,256,254,1,0,0,
        0,256,255,1,0,0,0,257,39,1,0,0,0,258,259,3,118,59,0,259,260,5,69,
        0,0,260,261,3,120,60,0,261,41,1,0,0,0,262,263,3,44,22,0,263,264,
        5,58,0,0,264,265,3,44,22,0,265,43,1,0,0,0,266,270,3,118,59,0,267,
        270,3,46,23,0,268,270,3,48,24,0,269,266,1,0,0,0,269,267,1,0,0,0,
        269,268,1,0,0,0,270,45,1,0,0,0,271,272,5,10,0,0,272,273,3,128,64,
        0,273,47,1,0,0,0,274,275,3,52,26,0,275,49,1,0,0,0,276,277,3,52,26,
        0,277,51,1,0,0,0,278,282,5,9,0,0,279,283,3,128,64,0,280,283,3,126,
        63,0,281,283,3,130,65,0,282,279,1,0,0,0,282,280,1,0,0,0,282,281,
        1,0,0,0,283,53,1,0,0,0,284,285,5,11,0,0,285,290,3,120,60,0,286,287,
        5,47,0,0,287,288,3,56,28,0,288,289,5,48,0,0,289,291,1,0,0,0,290,
        286,1,0,0,0,290,291,1,0,0,0,291,55,1,0,0,0,292,293,5,4,0,0,293,57,
        1,0,0,0,294,295,3,130,65,0,295,59,1,0,0,0,296,297,5,22,0,0,297,61,
        1,0,0,0,298,299,5,14,0,0,299,300,3,128,64,0,300,301,5,15,0,0,301,
        302,3,118,59,0,302,303,5,43,0,0,303,304,3,18,9,0,304,63,1,0,0,0,
        305,306,5,16,0,0,306,307,3,68,34,0,307,65,1,0,0,0,308,309,5,23,0,
        0,309,310,3,128,64,0,310,67,1,0,0,0,311,313,3,84,42,0,312,314,3,
        70,35,0,313,312,1,0,0,0,314,315,1,0,0,0,315,313,1,0,0,0,315,316,
        1,0,0,0,316,69,1,0,0,0,317,324,3,72,36,0,318,324,3,74,37,0,319,324,
        3,76,38,0,320,324,3,78,39,0,321,324,3,80,40,0,322,324,3,82,41,0,
        323,317,1,0,0,0,323,318,1,0,0,0,323,319,1,0,0,0,323,320,1,0,0,0,
        323,321,1,0,0,0,323,322,1,0,0,0,324,71,1,0,0,0,325,326,5,61,0,0,
        326,327,3,84,42,0,327,73,1,0,0,0,328,329,5,62,0,0,329,330,3,84,42,
        0,330,75,1,0,0,0,331,332,5,65,0,0,332,333,3,84,42,0,333,77,1,0,0,
        0,334,335,5,64,0,0,335,336,3,84,42,0,336,79,1,0,0,0,337,338,5,20,
        0,0,338,339,3,84,42,0,339,81,1,0,0,0,340,341,5,21,0,0,341,342,3,
        84,42,0,342,83,1,0,0,0,343,344,6,42,-1,0,344,345,3,86,43,0,345,351,
        1,0,0,0,346,347,10,2,0,0,347,348,7,3,0,0,348,350,3,86,43,0,349,346,
        1,0,0,0,350,353,1,0,0,0,351,349,1,0,0,0,351,352,1,0,0,0,352,85,1,
        0,0,0,353,351,1,0,0,0,354,355,6,43,-1,0,355,356,3,88,44,0,356,362,
        1,0,0,0,357,358,10,2,0,0,358,359,7,4,0,0,359,361,3,88,44,0,360,357,
        1,0,0,0,361,364,1,0,0,0,362,360,1,0,0,0,362,363,1,0,0,0,363,87,1,
        0,0,0,364,362,1,0,0,0,365,366,6,44,-1,0,366,367,3,90,45,0,367,373,
        1,0,0,0,368,369,10,2,0,0,369,370,7,5,0,0,370,372,3,90,45,0,371,368,
        1,0,0,0,372,375,1,0,0,0,373,371,1,0,0,0,373,374,1,0,0,0,374,89,1,
        0,0,0,375,373,1,0,0,0,376,379,3,92,46,0,377,378,5,45,0,0,378,380,
        3,92,46,0,379,377,1,0,0,0,379,380,1,0,0,0,380,91,1,0,0,0,381,392,
        3,94,47,0,382,383,3,128,64,0,383,385,5,40,0,0,384,386,3,94,47,0,
        385,384,1,0,0,0,386,387,1,0,0,0,387,385,1,0,0,0,387,388,1,0,0,0,
        388,389,1,0,0,0,389,390,5,41,0,0,390,392,1,0,0,0,391,381,1,0,0,0,
        391,382,1,0,0,0,392,93,1,0,0,0,393,394,3,96,48,0,394,95,1,0,0,0,
        395,399,3,118,59,0,396,399,3,100,50,0,397,399,3,98,49,0,398,395,
        1,0,0,0,398,396,1,0,0,0,398,397,1,0,0,0,399,97,1,0,0,0,400,401,5,
        40,0,0,401,402,3,84,42,0,402,403,5,41,0,0,403,99,1,0,0,0,404,408,
        3,102,51,0,405,408,3,104,52,0,406,408,3,106,53,0,407,404,1,0,0,0,
        407,405,1,0,0,0,407,406,1,0,0,0,408,101,1,0,0,0,409,410,3,106,53,
        0,410,411,5,17,0,0,411,412,3,106,53,0,412,103,1,0,0,0,413,414,3,
        106,53,0,414,415,5,33,0,0,415,416,3,108,54,0,416,105,1,0,0,0,417,
        419,7,4,0,0,418,417,1,0,0,0,418,419,1,0,0,0,419,420,1,0,0,0,420,
        422,5,4,0,0,421,423,3,128,64,0,422,421,1,0,0,0,422,423,1,0,0,0,423,
        107,1,0,0,0,424,427,5,4,0,0,425,428,5,36,0,0,426,428,3,128,64,0,
        427,425,1,0,0,0,427,426,1,0,0,0,427,428,1,0,0,0,428,109,1,0,0,0,
        429,430,5,4,0,0,430,111,1,0,0,0,431,432,5,47,0,0,432,433,3,110,55,
        0,433,434,5,48,0,0,434,113,1,0,0,0,435,436,5,37,0,0,436,437,5,4,
        0,0,437,115,1,0,0,0,438,440,3,128,64,0,439,441,3,112,56,0,440,439,
        1,0,0,0,440,441,1,0,0,0,441,117,1,0,0,0,442,447,3,116,58,0,443,444,
        5,37,0,0,444,446,3,116,58,0,445,443,1,0,0,0,446,449,1,0,0,0,447,
        445,1,0,0,0,447,448,1,0,0,0,448,451,1,0,0,0,449,447,1,0,0,0,450,
        452,3,114,57,0,451,450,1,0,0,0,451,452,1,0,0,0,452,119,1,0,0,0,453,
        458,3,128,64,0,454,455,5,37,0,0,455,457,3,128,64,0,456,454,1,0,0,
        0,457,460,1,0,0,0,458,456,1,0,0,0,458,459,1,0,0,0,459,121,1,0,0,
        0,460,458,1,0,0,0,461,462,3,128,64,0,462,123,1,0,0,0,463,464,5,43,
        0,0,464,465,3,122,61,0,465,125,1,0,0,0,466,467,5,4,0,0,467,127,1,
        0,0,0,468,469,5,24,0,0,469,129,1,0,0,0,470,471,5,3,0,0,471,131,1,
        0,0,0,472,473,7,6,0,0,473,133,1,0,0,0,35,136,138,148,155,159,177,
        181,186,202,206,215,223,231,249,256,269,282,290,315,323,351,362,
        373,379,387,391,398,407,418,422,427,440,447,451,458
    ]

class AtoParser ( AtoParserBase ):

    grammarFileName = "AtoParser.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "'component'", "'module'", 
                     "'interface'", "'pin'", "'signal'", "'new'", "'from'", 
                     "'import'", "'for'", "'in'", "'assert'", "'to'", "'True'", 
                     "'False'", "'within'", "'is'", "'pass'", "'trait'", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "'+/-'", "'\\u00B1'", "'%'", 
                     "'.'", "'...'", "'*'", "'('", "')'", "','", "':'", 
                     "';'", "'**'", "'='", "'['", "']'", "'|'", "'^'", "'&'", 
                     "'<<'", "'>>'", "'+'", "'-'", "'/'", "'//'", "'~'", 
                     "'{'", "'}'", "'<'", "'>'", "'=='", "'>='", "'<='", 
                     "'<>'", "'!='", "'@'", "'->'", "'+='", "'-='", "'*='", 
                     "'@='", "'/='", "'&='", "'|='", "'^='", "'<<='", "'>>='", 
                     "'**='", "'//='" ]

    symbolicNames = [ "<INVALID>", "INDENT", "DEDENT", "STRING", "NUMBER", 
                      "INTEGER", "COMPONENT", "MODULE", "INTERFACE", "PIN", 
                      "SIGNAL", "NEW", "FROM", "IMPORT", "FOR", "IN", "ASSERT", 
                      "TO", "TRUE", "FALSE", "WITHIN", "IS", "PASS", "TRAIT", 
                      "NAME", "STRING_LITERAL", "BYTES_LITERAL", "DECIMAL_INTEGER", 
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
                      "NEWLINE", "PRAGMA", "COMMENT", "WS", "EXPLICIT_LINE_JOINING", 
                      "ERRORTOKEN" ]

    RULE_file_input = 0
    RULE_pragma_stmt = 1
    RULE_stmt = 2
    RULE_simple_stmts = 3
    RULE_simple_stmt = 4
    RULE_compound_stmt = 5
    RULE_blockdef = 6
    RULE_blockdef_super = 7
    RULE_blocktype = 8
    RULE_block = 9
    RULE_dep_import_stmt = 10
    RULE_import_stmt = 11
    RULE_declaration_stmt = 12
    RULE_field_reference_or_declaration = 13
    RULE_assign_stmt = 14
    RULE_cum_assign_stmt = 15
    RULE_set_assign_stmt = 16
    RULE_cum_operator = 17
    RULE_cum_assignable = 18
    RULE_assignable = 19
    RULE_retype_stmt = 20
    RULE_connect_stmt = 21
    RULE_connectable = 22
    RULE_signaldef_stmt = 23
    RULE_pindef_stmt = 24
    RULE_pin_declaration = 25
    RULE_pin_stmt = 26
    RULE_new_stmt = 27
    RULE_new_count = 28
    RULE_string_stmt = 29
    RULE_pass_stmt = 30
    RULE_for_stmt = 31
    RULE_assert_stmt = 32
    RULE_trait_stmt = 33
    RULE_comparison = 34
    RULE_compare_op_pair = 35
    RULE_lt_arithmetic_or = 36
    RULE_gt_arithmetic_or = 37
    RULE_lt_eq_arithmetic_or = 38
    RULE_gt_eq_arithmetic_or = 39
    RULE_in_arithmetic_or = 40
    RULE_is_arithmetic_or = 41
    RULE_arithmetic_expression = 42
    RULE_sum = 43
    RULE_term = 44
    RULE_power = 45
    RULE_functional = 46
    RULE_bound = 47
    RULE_atom = 48
    RULE_arithmetic_group = 49
    RULE_literal_physical = 50
    RULE_bound_quantity = 51
    RULE_bilateral_quantity = 52
    RULE_quantity = 53
    RULE_bilateral_tolerance = 54
    RULE_key = 55
    RULE_array_index = 56
    RULE_pin_reference_end = 57
    RULE_field_reference_part = 58
    RULE_field_reference = 59
    RULE_type_reference = 60
    RULE_unit = 61
    RULE_type_info = 62
    RULE_totally_an_integer = 63
    RULE_name = 64
    RULE_string = 65
    RULE_boolean_ = 66

    ruleNames =  [ "file_input", "pragma_stmt", "stmt", "simple_stmts", 
                   "simple_stmt", "compound_stmt", "blockdef", "blockdef_super", 
                   "blocktype", "block", "dep_import_stmt", "import_stmt", 
                   "declaration_stmt", "field_reference_or_declaration", 
                   "assign_stmt", "cum_assign_stmt", "set_assign_stmt", 
                   "cum_operator", "cum_assignable", "assignable", "retype_stmt", 
                   "connect_stmt", "connectable", "signaldef_stmt", "pindef_stmt", 
                   "pin_declaration", "pin_stmt", "new_stmt", "new_count", 
                   "string_stmt", "pass_stmt", "for_stmt", "assert_stmt", 
                   "trait_stmt", "comparison", "compare_op_pair", "lt_arithmetic_or", 
                   "gt_arithmetic_or", "lt_eq_arithmetic_or", "gt_eq_arithmetic_or", 
                   "in_arithmetic_or", "is_arithmetic_or", "arithmetic_expression", 
                   "sum", "term", "power", "functional", "bound", "atom", 
                   "arithmetic_group", "literal_physical", "bound_quantity", 
                   "bilateral_quantity", "quantity", "bilateral_tolerance", 
                   "key", "array_index", "pin_reference_end", "field_reference_part", 
                   "field_reference", "type_reference", "unit", "type_info", 
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
    FOR=14
    IN=15
    ASSERT=16
    TO=17
    TRUE=18
    FALSE=19
    WITHIN=20
    IS=21
    PASS=22
    TRAIT=23
    NAME=24
    STRING_LITERAL=25
    BYTES_LITERAL=26
    DECIMAL_INTEGER=27
    OCT_INTEGER=28
    HEX_INTEGER=29
    BIN_INTEGER=30
    FLOAT_NUMBER=31
    IMAG_NUMBER=32
    PLUS_OR_MINUS=33
    PLUS_SLASH_MINUS=34
    PLUS_MINUS_SIGN=35
    PERCENT=36
    DOT=37
    ELLIPSIS=38
    STAR=39
    OPEN_PAREN=40
    CLOSE_PAREN=41
    COMMA=42
    COLON=43
    SEMI_COLON=44
    POWER=45
    ASSIGN=46
    OPEN_BRACK=47
    CLOSE_BRACK=48
    OR_OP=49
    XOR=50
    AND_OP=51
    LEFT_SHIFT=52
    RIGHT_SHIFT=53
    ADD=54
    MINUS=55
    DIV=56
    IDIV=57
    NOT_OP=58
    OPEN_BRACE=59
    CLOSE_BRACE=60
    LESS_THAN=61
    GREATER_THAN=62
    EQUALS=63
    GT_EQ=64
    LT_EQ=65
    NOT_EQ_1=66
    NOT_EQ_2=67
    AT=68
    ARROW=69
    ADD_ASSIGN=70
    SUB_ASSIGN=71
    MULT_ASSIGN=72
    AT_ASSIGN=73
    DIV_ASSIGN=74
    AND_ASSIGN=75
    OR_ASSIGN=76
    XOR_ASSIGN=77
    LEFT_SHIFT_ASSIGN=78
    RIGHT_SHIFT_ASSIGN=79
    POWER_ASSIGN=80
    IDIV_ASSIGN=81
    NEWLINE=82
    PRAGMA=83
    COMMENT=84
    WS=85
    EXPLICIT_LINE_JOINING=86
    ERRORTOKEN=87

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
            self.state = 138
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 29456328) != 0) or _la==82 or _la==83:
                self.state = 136
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [82]:
                    self.state = 134
                    self.match(AtoParser.NEWLINE)
                    pass
                elif token in [3, 6, 7, 8, 9, 10, 12, 13, 14, 16, 22, 23, 24, 83]:
                    self.state = 135
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 140
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 141
            self.match(AtoParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Pragma_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def PRAGMA(self):
            return self.getToken(AtoParser.PRAGMA, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_pragma_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPragma_stmt" ):
                return visitor.visitPragma_stmt(self)
            else:
                return visitor.visitChildren(self)




    def pragma_stmt(self):

        localctx = AtoParser.Pragma_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_pragma_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 143
            self.match(AtoParser.PRAGMA)
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


        def pragma_stmt(self):
            return self.getTypedRuleContext(AtoParser.Pragma_stmtContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStmt" ):
                return visitor.visitStmt(self)
            else:
                return visitor.visitChildren(self)




    def stmt(self):

        localctx = AtoParser.StmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_stmt)
        try:
            self.state = 148
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 16, 22, 23, 24]:
                self.enterOuterAlt(localctx, 1)
                self.state = 145
                self.simple_stmts()
                pass
            elif token in [6, 7, 8, 14]:
                self.enterOuterAlt(localctx, 2)
                self.state = 146
                self.compound_stmt()
                pass
            elif token in [83]:
                self.enterOuterAlt(localctx, 3)
                self.state = 147
                self.pragma_stmt()
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
        self.enterRule(localctx, 6, self.RULE_simple_stmts)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 150
            self.simple_stmt()
            self.state = 155
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 151
                    self.match(AtoParser.SEMI_COLON)
                    self.state = 152
                    self.simple_stmt() 
                self.state = 157
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 159
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==44:
                self.state = 158
                self.match(AtoParser.SEMI_COLON)


            self.state = 161
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


        def trait_stmt(self):
            return self.getTypedRuleContext(AtoParser.Trait_stmtContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_simple_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSimple_stmt" ):
                return visitor.visitSimple_stmt(self)
            else:
                return visitor.visitChildren(self)




    def simple_stmt(self):

        localctx = AtoParser.Simple_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_simple_stmt)
        try:
            self.state = 177
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 163
                self.import_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 164
                self.dep_import_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 165
                self.assign_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 166
                self.cum_assign_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 167
                self.set_assign_stmt()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 168
                self.connect_stmt()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 169
                self.retype_stmt()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 170
                self.pin_declaration()
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 171
                self.signaldef_stmt()
                pass

            elif la_ == 10:
                self.enterOuterAlt(localctx, 10)
                self.state = 172
                self.assert_stmt()
                pass

            elif la_ == 11:
                self.enterOuterAlt(localctx, 11)
                self.state = 173
                self.declaration_stmt()
                pass

            elif la_ == 12:
                self.enterOuterAlt(localctx, 12)
                self.state = 174
                self.string_stmt()
                pass

            elif la_ == 13:
                self.enterOuterAlt(localctx, 13)
                self.state = 175
                self.pass_stmt()
                pass

            elif la_ == 14:
                self.enterOuterAlt(localctx, 14)
                self.state = 176
                self.trait_stmt()
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


        def for_stmt(self):
            return self.getTypedRuleContext(AtoParser.For_stmtContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_compound_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCompound_stmt" ):
                return visitor.visitCompound_stmt(self)
            else:
                return visitor.visitChildren(self)




    def compound_stmt(self):

        localctx = AtoParser.Compound_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_compound_stmt)
        try:
            self.state = 181
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [6, 7, 8]:
                self.enterOuterAlt(localctx, 1)
                self.state = 179
                self.blockdef()
                pass
            elif token in [14]:
                self.enterOuterAlt(localctx, 2)
                self.state = 180
                self.for_stmt()
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
        self.enterRule(localctx, 12, self.RULE_blockdef)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 183
            self.blocktype()
            self.state = 184
            self.name()
            self.state = 186
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 185
                self.blockdef_super()


            self.state = 188
            self.match(AtoParser.COLON)
            self.state = 189
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
        self.enterRule(localctx, 14, self.RULE_blockdef_super)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 191
            self.match(AtoParser.FROM)
            self.state = 192
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
        self.enterRule(localctx, 16, self.RULE_blocktype)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 194
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
        self.enterRule(localctx, 18, self.RULE_block)
        self._la = 0 # Token type
        try:
            self.state = 206
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 16, 22, 23, 24]:
                self.enterOuterAlt(localctx, 1)
                self.state = 196
                self.simple_stmts()
                pass
            elif token in [82]:
                self.enterOuterAlt(localctx, 2)
                self.state = 197
                self.match(AtoParser.NEWLINE)
                self.state = 198
                self.match(AtoParser.INDENT)
                self.state = 200 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 199
                    self.stmt()
                    self.state = 202 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 29456328) != 0) or _la==83):
                        break

                self.state = 204
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
        self.enterRule(localctx, 20, self.RULE_dep_import_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 208
            self.match(AtoParser.IMPORT)
            self.state = 209
            self.type_reference()
            self.state = 210
            self.match(AtoParser.FROM)
            self.state = 211
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
        self.enterRule(localctx, 22, self.RULE_import_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 215
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 213
                self.match(AtoParser.FROM)
                self.state = 214
                self.string()


            self.state = 217
            self.match(AtoParser.IMPORT)
            self.state = 218
            self.type_reference()
            self.state = 223
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==42:
                self.state = 219
                self.match(AtoParser.COMMA)
                self.state = 220
                self.type_reference()
                self.state = 225
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
        self.enterRule(localctx, 24, self.RULE_declaration_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 226
            self.field_reference()
            self.state = 227
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
        self.enterRule(localctx, 26, self.RULE_field_reference_or_declaration)
        try:
            self.state = 231
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 229
                self.field_reference()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 230
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
        self.enterRule(localctx, 28, self.RULE_assign_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 233
            self.field_reference_or_declaration()
            self.state = 234
            self.match(AtoParser.ASSIGN)
            self.state = 235
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
        self.enterRule(localctx, 30, self.RULE_cum_assign_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 237
            self.field_reference_or_declaration()
            self.state = 238
            self.cum_operator()
            self.state = 239
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
        self.enterRule(localctx, 32, self.RULE_set_assign_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 241
            self.field_reference_or_declaration()
            self.state = 242
            _la = self._input.LA(1)
            if not(_la==75 or _la==76):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 243
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
        self.enterRule(localctx, 34, self.RULE_cum_operator)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 245
            _la = self._input.LA(1)
            if not(_la==70 or _la==71):
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
        self.enterRule(localctx, 36, self.RULE_cum_assignable)
        try:
            self.state = 249
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 247
                self.literal_physical()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 248
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
        self.enterRule(localctx, 38, self.RULE_assignable)
        try:
            self.state = 256
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 251
                self.string()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 252
                self.new_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 253
                self.literal_physical()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 254
                self.arithmetic_expression(0)
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 255
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
        self.enterRule(localctx, 40, self.RULE_retype_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 258
            self.field_reference()
            self.state = 259
            self.match(AtoParser.ARROW)
            self.state = 260
            self.type_reference()
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
        self.enterRule(localctx, 42, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 262
            self.connectable()
            self.state = 263
            self.match(AtoParser.NOT_OP)
            self.state = 264
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
        self.enterRule(localctx, 44, self.RULE_connectable)
        try:
            self.state = 269
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [24]:
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
        self.enterRule(localctx, 46, self.RULE_signaldef_stmt)
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
        self.enterRule(localctx, 48, self.RULE_pindef_stmt)
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
        self.enterRule(localctx, 50, self.RULE_pin_declaration)
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
        self.enterRule(localctx, 52, self.RULE_pin_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 278
            self.match(AtoParser.PIN)
            self.state = 282
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [24]:
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


        def OPEN_BRACK(self):
            return self.getToken(AtoParser.OPEN_BRACK, 0)

        def new_count(self):
            return self.getTypedRuleContext(AtoParser.New_countContext,0)


        def CLOSE_BRACK(self):
            return self.getToken(AtoParser.CLOSE_BRACK, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_new_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNew_stmt" ):
                return visitor.visitNew_stmt(self)
            else:
                return visitor.visitChildren(self)




    def new_stmt(self):

        localctx = AtoParser.New_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_new_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 284
            self.match(AtoParser.NEW)
            self.state = 285
            self.type_reference()
            self.state = 290
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==47:
                self.state = 286
                self.match(AtoParser.OPEN_BRACK)
                self.state = 287
                self.new_count()
                self.state = 288
                self.match(AtoParser.CLOSE_BRACK)


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class New_countContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self):
            return self.getToken(AtoParser.NUMBER, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_new_count

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNew_count" ):
                return visitor.visitNew_count(self)
            else:
                return visitor.visitChildren(self)




    def new_count(self):

        localctx = AtoParser.New_countContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_new_count)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 292
            self.match(AtoParser.NUMBER)
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
            self.state = 294
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
            self.state = 296
            self.match(AtoParser.PASS)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class For_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def FOR(self):
            return self.getToken(AtoParser.FOR, 0)

        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def IN(self):
            return self.getToken(AtoParser.IN, 0)

        def field_reference(self):
            return self.getTypedRuleContext(AtoParser.Field_referenceContext,0)


        def COLON(self):
            return self.getToken(AtoParser.COLON, 0)

        def block(self):
            return self.getTypedRuleContext(AtoParser.BlockContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_for_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFor_stmt" ):
                return visitor.visitFor_stmt(self)
            else:
                return visitor.visitChildren(self)




    def for_stmt(self):

        localctx = AtoParser.For_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 62, self.RULE_for_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 298
            self.match(AtoParser.FOR)
            self.state = 299
            self.name()
            self.state = 300
            self.match(AtoParser.IN)
            self.state = 301
            self.field_reference()
            self.state = 302
            self.match(AtoParser.COLON)
            self.state = 303
            self.block()
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
        self.enterRule(localctx, 64, self.RULE_assert_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 305
            self.match(AtoParser.ASSERT)
            self.state = 306
            self.comparison()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Trait_stmtContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def TRAIT(self):
            return self.getToken(AtoParser.TRAIT, 0)

        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_trait_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTrait_stmt" ):
                return visitor.visitTrait_stmt(self)
            else:
                return visitor.visitChildren(self)




    def trait_stmt(self):

        localctx = AtoParser.Trait_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 66, self.RULE_trait_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 308
            self.match(AtoParser.TRAIT)
            self.state = 309
            self.name()
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
        self.enterRule(localctx, 68, self.RULE_comparison)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 311
            self.arithmetic_expression(0)
            self.state = 313 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 312
                self.compare_op_pair()
                self.state = 315 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (((((_la - 20)) & ~0x3f) == 0 and ((1 << (_la - 20)) & 59373627899907) != 0)):
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
        self.enterRule(localctx, 70, self.RULE_compare_op_pair)
        try:
            self.state = 323
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [61]:
                self.enterOuterAlt(localctx, 1)
                self.state = 317
                self.lt_arithmetic_or()
                pass
            elif token in [62]:
                self.enterOuterAlt(localctx, 2)
                self.state = 318
                self.gt_arithmetic_or()
                pass
            elif token in [65]:
                self.enterOuterAlt(localctx, 3)
                self.state = 319
                self.lt_eq_arithmetic_or()
                pass
            elif token in [64]:
                self.enterOuterAlt(localctx, 4)
                self.state = 320
                self.gt_eq_arithmetic_or()
                pass
            elif token in [20]:
                self.enterOuterAlt(localctx, 5)
                self.state = 321
                self.in_arithmetic_or()
                pass
            elif token in [21]:
                self.enterOuterAlt(localctx, 6)
                self.state = 322
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
        self.enterRule(localctx, 72, self.RULE_lt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 325
            self.match(AtoParser.LESS_THAN)
            self.state = 326
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
        self.enterRule(localctx, 74, self.RULE_gt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 328
            self.match(AtoParser.GREATER_THAN)
            self.state = 329
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
        self.enterRule(localctx, 76, self.RULE_lt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 331
            self.match(AtoParser.LT_EQ)
            self.state = 332
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
        self.enterRule(localctx, 78, self.RULE_gt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 334
            self.match(AtoParser.GT_EQ)
            self.state = 335
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
        self.enterRule(localctx, 80, self.RULE_in_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 337
            self.match(AtoParser.WITHIN)
            self.state = 338
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
        self.enterRule(localctx, 82, self.RULE_is_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 340
            self.match(AtoParser.IS)
            self.state = 341
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
        _startState = 84
        self.enterRecursionRule(localctx, 84, self.RULE_arithmetic_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 344
            self.sum_(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 351
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,20,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.Arithmetic_expressionContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmetic_expression)
                    self.state = 346
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 347
                    _la = self._input.LA(1)
                    if not(_la==49 or _la==51):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 348
                    self.sum_(0) 
                self.state = 353
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
        _startState = 86
        self.enterRecursionRule(localctx, 86, self.RULE_sum, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 355
            self.term(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 362
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,21,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.SumContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_sum)
                    self.state = 357
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 358
                    _la = self._input.LA(1)
                    if not(_la==54 or _la==55):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 359
                    self.term(0) 
                self.state = 364
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
        _startState = 88
        self.enterRecursionRule(localctx, 88, self.RULE_term, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 366
            self.power()
            self._ctx.stop = self._input.LT(-1)
            self.state = 373
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,22,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.TermContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_term)
                    self.state = 368
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 369
                    _la = self._input.LA(1)
                    if not(_la==39 or _la==56):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 370
                    self.power() 
                self.state = 375
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
        self.enterRule(localctx, 90, self.RULE_power)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 376
            self.functional()
            self.state = 379
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,23,self._ctx)
            if la_ == 1:
                self.state = 377
                self.match(AtoParser.POWER)
                self.state = 378
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
        self.enterRule(localctx, 92, self.RULE_functional)
        self._la = 0 # Token type
        try:
            self.state = 391
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,25,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 381
                self.bound()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 382
                self.name()
                self.state = 383
                self.match(AtoParser.OPEN_PAREN)
                self.state = 385 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 384
                    self.bound()
                    self.state = 387 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 54044295056850960) != 0)):
                        break

                self.state = 389
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
        self.enterRule(localctx, 94, self.RULE_bound)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 393
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
        self.enterRule(localctx, 96, self.RULE_atom)
        try:
            self.state = 398
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [24]:
                self.enterOuterAlt(localctx, 1)
                self.state = 395
                self.field_reference()
                pass
            elif token in [4, 54, 55]:
                self.enterOuterAlt(localctx, 2)
                self.state = 396
                self.literal_physical()
                pass
            elif token in [40]:
                self.enterOuterAlt(localctx, 3)
                self.state = 397
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
        self.enterRule(localctx, 98, self.RULE_arithmetic_group)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 400
            self.match(AtoParser.OPEN_PAREN)
            self.state = 401
            self.arithmetic_expression(0)
            self.state = 402
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
        self.enterRule(localctx, 100, self.RULE_literal_physical)
        try:
            self.state = 407
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,27,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 404
                self.bound_quantity()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 405
                self.bilateral_quantity()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 406
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
        self.enterRule(localctx, 102, self.RULE_bound_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 409
            self.quantity()
            self.state = 410
            self.match(AtoParser.TO)
            self.state = 411
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
        self.enterRule(localctx, 104, self.RULE_bilateral_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 413
            self.quantity()
            self.state = 414
            self.match(AtoParser.PLUS_OR_MINUS)
            self.state = 415
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
        self.enterRule(localctx, 106, self.RULE_quantity)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 418
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==54 or _la==55:
                self.state = 417
                _la = self._input.LA(1)
                if not(_la==54 or _la==55):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()


            self.state = 420
            self.match(AtoParser.NUMBER)
            self.state = 422
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,29,self._ctx)
            if la_ == 1:
                self.state = 421
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
        self.enterRule(localctx, 108, self.RULE_bilateral_tolerance)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 424
            self.match(AtoParser.NUMBER)
            self.state = 427
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,30,self._ctx)
            if la_ == 1:
                self.state = 425
                self.match(AtoParser.PERCENT)

            elif la_ == 2:
                self.state = 426
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
        self.enterRule(localctx, 110, self.RULE_key)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 429
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
        self.enterRule(localctx, 112, self.RULE_array_index)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 431
            self.match(AtoParser.OPEN_BRACK)
            self.state = 432
            self.key()
            self.state = 433
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
        self.enterRule(localctx, 114, self.RULE_pin_reference_end)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 435
            self.match(AtoParser.DOT)
            self.state = 436
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
        self.enterRule(localctx, 116, self.RULE_field_reference_part)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 438
            self.name()
            self.state = 440
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,31,self._ctx)
            if la_ == 1:
                self.state = 439
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
        self.enterRule(localctx, 118, self.RULE_field_reference)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 442
            self.field_reference_part()
            self.state = 447
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,32,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 443
                    self.match(AtoParser.DOT)
                    self.state = 444
                    self.field_reference_part() 
                self.state = 449
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,32,self._ctx)

            self.state = 451
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,33,self._ctx)
            if la_ == 1:
                self.state = 450
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
        self.enterRule(localctx, 120, self.RULE_type_reference)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 453
            self.name()
            self.state = 458
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==37:
                self.state = 454
                self.match(AtoParser.DOT)
                self.state = 455
                self.name()
                self.state = 460
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
        self.enterRule(localctx, 122, self.RULE_unit)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 461
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
        self.enterRule(localctx, 124, self.RULE_type_info)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 463
            self.match(AtoParser.COLON)
            self.state = 464
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
        self.enterRule(localctx, 126, self.RULE_totally_an_integer)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 466
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
        self.enterRule(localctx, 128, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 468
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
        self.enterRule(localctx, 130, self.RULE_string)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 470
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
        self.enterRule(localctx, 132, self.RULE_boolean_)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 472
            _la = self._input.LA(1)
            if not(_la==18 or _la==19):
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
        self._predicates[42] = self.arithmetic_expression_sempred
        self._predicates[43] = self.sum_sempred
        self._predicates[44] = self.term_sempred
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
         




