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
        4,1,88,561,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,2,39,7,39,
        2,40,7,40,2,41,7,41,2,42,7,42,2,43,7,43,2,44,7,44,2,45,7,45,2,46,
        7,46,2,47,7,47,2,48,7,48,2,49,7,49,2,50,7,50,2,51,7,51,2,52,7,52,
        2,53,7,53,2,54,7,54,2,55,7,55,2,56,7,56,2,57,7,57,2,58,7,58,2,59,
        7,59,2,60,7,60,2,61,7,61,2,62,7,62,2,63,7,63,2,64,7,64,2,65,7,65,
        2,66,7,66,2,67,7,67,2,68,7,68,2,69,7,69,2,70,7,70,2,71,7,71,2,72,
        7,72,2,73,7,73,2,74,7,74,2,75,7,75,2,76,7,76,1,0,1,0,5,0,157,8,0,
        10,0,12,0,160,9,0,1,0,1,0,1,1,1,1,1,2,1,2,1,2,3,2,169,8,2,1,3,1,
        3,1,3,5,3,174,8,3,10,3,12,3,177,9,3,1,3,3,3,180,8,3,1,3,1,3,1,4,
        1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,3,4,199,
        8,4,1,5,1,5,3,5,203,8,5,1,6,1,6,1,6,3,6,208,8,6,1,6,1,6,1,6,1,7,
        1,7,1,7,1,8,1,8,1,9,1,9,1,9,1,9,4,9,222,8,9,11,9,12,9,223,1,9,1,
        9,3,9,228,8,9,1,10,1,10,1,10,1,10,1,10,1,11,1,11,3,11,237,8,11,1,
        11,1,11,1,11,1,11,5,11,243,8,11,10,11,12,11,246,9,11,1,12,1,12,1,
        12,1,13,1,13,3,13,253,8,13,1,14,1,14,1,14,1,14,1,15,1,15,1,15,1,
        15,1,16,1,16,1,16,1,16,1,17,1,17,1,18,1,18,3,18,271,8,18,1,19,1,
        19,1,19,1,19,1,19,3,19,278,8,19,1,20,1,20,1,20,1,20,1,21,1,21,1,
        21,4,21,287,8,21,11,21,12,21,288,1,22,1,22,1,22,1,22,1,23,1,23,1,
        24,1,24,1,24,3,24,300,8,24,1,25,1,25,1,25,1,26,1,26,1,27,1,27,1,
        28,1,28,1,28,1,28,3,28,313,8,28,1,29,1,29,1,29,1,29,1,29,1,29,3,
        29,321,8,29,1,30,1,30,1,31,1,31,1,32,1,32,1,33,1,33,1,33,1,33,1,
        33,3,33,334,8,33,1,33,1,33,1,33,1,34,1,34,1,34,1,35,1,35,1,35,1,
        35,3,35,346,8,35,1,35,1,35,3,35,350,8,35,1,35,3,35,353,8,35,1,36,
        1,36,1,37,1,37,1,37,5,37,360,8,37,10,37,12,37,363,9,37,1,38,1,38,
        1,38,1,38,1,39,1,39,4,39,371,8,39,11,39,12,39,372,1,40,1,40,1,40,
        1,40,1,40,1,40,3,40,381,8,40,1,41,1,41,1,41,1,42,1,42,1,42,1,43,
        1,43,1,43,1,44,1,44,1,44,1,45,1,45,1,45,1,46,1,46,1,46,1,47,1,47,
        1,47,1,47,1,47,1,47,5,47,407,8,47,10,47,12,47,410,9,47,1,48,1,48,
        1,48,1,48,1,48,1,48,5,48,418,8,48,10,48,12,48,421,9,48,1,49,1,49,
        1,49,1,49,1,49,1,49,5,49,429,8,49,10,49,12,49,432,9,49,1,50,1,50,
        1,50,3,50,437,8,50,1,51,1,51,1,51,1,51,4,51,443,8,51,11,51,12,51,
        444,1,51,1,51,3,51,449,8,51,1,52,1,52,1,53,1,53,3,53,455,8,53,1,
        53,1,53,3,53,459,8,53,1,53,1,53,3,53,463,8,53,3,53,465,8,53,3,53,
        467,8,53,1,53,1,53,1,54,1,54,1,54,3,54,474,8,54,1,55,1,55,1,55,1,
        55,1,56,1,56,1,56,3,56,483,8,56,1,57,1,57,1,57,1,57,1,58,1,58,1,
        58,1,58,1,59,1,59,3,59,495,8,59,1,60,1,60,1,60,3,60,500,8,60,1,61,
        1,61,1,62,1,62,1,62,1,62,1,63,1,63,1,63,1,64,1,64,3,64,513,8,64,
        1,65,1,65,1,65,5,65,518,8,65,10,65,12,65,521,9,65,1,65,3,65,524,
        8,65,1,66,1,66,1,66,5,66,529,8,66,10,66,12,66,532,9,66,1,67,1,67,
        1,68,1,68,1,68,1,69,1,69,1,70,1,70,1,70,3,70,544,8,70,1,71,1,71,
        1,72,1,72,1,73,1,73,1,74,1,74,1,75,3,75,555,8,75,1,75,1,75,1,76,
        1,76,1,76,0,3,94,96,98,77,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,
        30,32,34,36,38,40,42,44,46,48,50,52,54,56,58,60,62,64,66,68,70,72,
        74,76,78,80,82,84,86,88,90,92,94,96,98,100,102,104,106,108,110,112,
        114,116,118,120,122,124,126,128,130,132,134,136,138,140,142,144,
        146,148,150,152,0,7,1,0,6,8,1,0,76,77,1,0,71,72,2,0,51,51,53,53,
        1,0,56,57,2,0,41,41,58,58,1,0,18,19,557,0,158,1,0,0,0,2,163,1,0,
        0,0,4,168,1,0,0,0,6,170,1,0,0,0,8,198,1,0,0,0,10,202,1,0,0,0,12,
        204,1,0,0,0,14,212,1,0,0,0,16,215,1,0,0,0,18,227,1,0,0,0,20,229,
        1,0,0,0,22,236,1,0,0,0,24,247,1,0,0,0,26,252,1,0,0,0,28,254,1,0,
        0,0,30,258,1,0,0,0,32,262,1,0,0,0,34,266,1,0,0,0,36,270,1,0,0,0,
        38,277,1,0,0,0,40,279,1,0,0,0,42,283,1,0,0,0,44,290,1,0,0,0,46,294,
        1,0,0,0,48,299,1,0,0,0,50,301,1,0,0,0,52,304,1,0,0,0,54,306,1,0,
        0,0,56,308,1,0,0,0,58,314,1,0,0,0,60,322,1,0,0,0,62,324,1,0,0,0,
        64,326,1,0,0,0,66,328,1,0,0,0,68,338,1,0,0,0,70,341,1,0,0,0,72,354,
        1,0,0,0,74,356,1,0,0,0,76,364,1,0,0,0,78,368,1,0,0,0,80,380,1,0,
        0,0,82,382,1,0,0,0,84,385,1,0,0,0,86,388,1,0,0,0,88,391,1,0,0,0,
        90,394,1,0,0,0,92,397,1,0,0,0,94,400,1,0,0,0,96,411,1,0,0,0,98,422,
        1,0,0,0,100,433,1,0,0,0,102,448,1,0,0,0,104,450,1,0,0,0,106,452,
        1,0,0,0,108,473,1,0,0,0,110,475,1,0,0,0,112,482,1,0,0,0,114,484,
        1,0,0,0,116,488,1,0,0,0,118,492,1,0,0,0,120,496,1,0,0,0,122,501,
        1,0,0,0,124,503,1,0,0,0,126,507,1,0,0,0,128,510,1,0,0,0,130,514,
        1,0,0,0,132,525,1,0,0,0,134,533,1,0,0,0,136,535,1,0,0,0,138,538,
        1,0,0,0,140,543,1,0,0,0,142,545,1,0,0,0,144,547,1,0,0,0,146,549,
        1,0,0,0,148,551,1,0,0,0,150,554,1,0,0,0,152,558,1,0,0,0,154,157,
        5,83,0,0,155,157,3,4,2,0,156,154,1,0,0,0,156,155,1,0,0,0,157,160,
        1,0,0,0,158,156,1,0,0,0,158,159,1,0,0,0,159,161,1,0,0,0,160,158,
        1,0,0,0,161,162,5,0,0,1,162,1,1,0,0,0,163,164,5,84,0,0,164,3,1,0,
        0,0,165,169,3,6,3,0,166,169,3,10,5,0,167,169,3,2,1,0,168,165,1,0,
        0,0,168,166,1,0,0,0,168,167,1,0,0,0,169,5,1,0,0,0,170,175,3,8,4,
        0,171,172,5,46,0,0,172,174,3,8,4,0,173,171,1,0,0,0,174,177,1,0,0,
        0,175,173,1,0,0,0,175,176,1,0,0,0,176,179,1,0,0,0,177,175,1,0,0,
        0,178,180,5,46,0,0,179,178,1,0,0,0,179,180,1,0,0,0,180,181,1,0,0,
        0,181,182,5,83,0,0,182,7,1,0,0,0,183,199,3,22,11,0,184,199,3,20,
        10,0,185,199,3,28,14,0,186,199,3,30,15,0,187,199,3,32,16,0,188,199,
        3,44,22,0,189,199,3,42,21,0,190,199,3,40,20,0,191,199,3,54,27,0,
        192,199,3,50,25,0,193,199,3,68,34,0,194,199,3,24,12,0,195,199,3,
        62,31,0,196,199,3,64,32,0,197,199,3,70,35,0,198,183,1,0,0,0,198,
        184,1,0,0,0,198,185,1,0,0,0,198,186,1,0,0,0,198,187,1,0,0,0,198,
        188,1,0,0,0,198,189,1,0,0,0,198,190,1,0,0,0,198,191,1,0,0,0,198,
        192,1,0,0,0,198,193,1,0,0,0,198,194,1,0,0,0,198,195,1,0,0,0,198,
        196,1,0,0,0,198,197,1,0,0,0,199,9,1,0,0,0,200,203,3,12,6,0,201,203,
        3,66,33,0,202,200,1,0,0,0,202,201,1,0,0,0,203,11,1,0,0,0,204,205,
        3,16,8,0,205,207,3,138,69,0,206,208,3,14,7,0,207,206,1,0,0,0,207,
        208,1,0,0,0,208,209,1,0,0,0,209,210,5,45,0,0,210,211,3,18,9,0,211,
        13,1,0,0,0,212,213,5,12,0,0,213,214,3,132,66,0,214,15,1,0,0,0,215,
        216,7,0,0,0,216,17,1,0,0,0,217,228,3,6,3,0,218,219,5,83,0,0,219,
        221,5,1,0,0,220,222,3,4,2,0,221,220,1,0,0,0,222,223,1,0,0,0,223,
        221,1,0,0,0,223,224,1,0,0,0,224,225,1,0,0,0,225,226,5,2,0,0,226,
        228,1,0,0,0,227,217,1,0,0,0,227,218,1,0,0,0,228,19,1,0,0,0,229,230,
        5,13,0,0,230,231,3,132,66,0,231,232,5,12,0,0,232,233,3,142,71,0,
        233,21,1,0,0,0,234,235,5,12,0,0,235,237,3,142,71,0,236,234,1,0,0,
        0,236,237,1,0,0,0,237,238,1,0,0,0,238,239,5,13,0,0,239,244,3,132,
        66,0,240,241,5,44,0,0,241,243,3,132,66,0,242,240,1,0,0,0,243,246,
        1,0,0,0,244,242,1,0,0,0,244,245,1,0,0,0,245,23,1,0,0,0,246,244,1,
        0,0,0,247,248,3,130,65,0,248,249,3,136,68,0,249,25,1,0,0,0,250,253,
        3,130,65,0,251,253,3,24,12,0,252,250,1,0,0,0,252,251,1,0,0,0,253,
        27,1,0,0,0,254,255,3,26,13,0,255,256,5,48,0,0,256,257,3,38,19,0,
        257,29,1,0,0,0,258,259,3,26,13,0,259,260,3,34,17,0,260,261,3,36,
        18,0,261,31,1,0,0,0,262,263,3,26,13,0,263,264,7,1,0,0,264,265,3,
        36,18,0,265,33,1,0,0,0,266,267,7,2,0,0,267,35,1,0,0,0,268,271,3,
        112,56,0,269,271,3,94,47,0,270,268,1,0,0,0,270,269,1,0,0,0,271,37,
        1,0,0,0,272,278,3,142,71,0,273,278,3,58,29,0,274,278,3,112,56,0,
        275,278,3,94,47,0,276,278,3,144,72,0,277,272,1,0,0,0,277,273,1,0,
        0,0,277,274,1,0,0,0,277,275,1,0,0,0,277,276,1,0,0,0,278,39,1,0,0,
        0,279,280,3,130,65,0,280,281,5,70,0,0,281,282,3,132,66,0,282,41,
        1,0,0,0,283,286,3,48,24,0,284,285,5,24,0,0,285,287,3,46,23,0,286,
        284,1,0,0,0,287,288,1,0,0,0,288,286,1,0,0,0,288,289,1,0,0,0,289,
        43,1,0,0,0,290,291,3,48,24,0,291,292,5,25,0,0,292,293,3,48,24,0,
        293,45,1,0,0,0,294,295,3,130,65,0,295,47,1,0,0,0,296,300,3,130,65,
        0,297,300,3,50,25,0,298,300,3,52,26,0,299,296,1,0,0,0,299,297,1,
        0,0,0,299,298,1,0,0,0,300,49,1,0,0,0,301,302,5,10,0,0,302,303,3,
        138,69,0,303,51,1,0,0,0,304,305,3,56,28,0,305,53,1,0,0,0,306,307,
        3,56,28,0,307,55,1,0,0,0,308,312,5,9,0,0,309,313,3,138,69,0,310,
        313,3,146,73,0,311,313,3,142,71,0,312,309,1,0,0,0,312,310,1,0,0,
        0,312,311,1,0,0,0,313,57,1,0,0,0,314,315,5,11,0,0,315,320,3,132,
        66,0,316,317,5,49,0,0,317,318,3,60,30,0,318,319,5,50,0,0,319,321,
        1,0,0,0,320,316,1,0,0,0,320,321,1,0,0,0,321,59,1,0,0,0,322,323,3,
        146,73,0,323,61,1,0,0,0,324,325,3,142,71,0,325,63,1,0,0,0,326,327,
        5,22,0,0,327,65,1,0,0,0,328,329,5,14,0,0,329,330,3,138,69,0,330,
        331,5,15,0,0,331,333,3,130,65,0,332,334,3,106,53,0,333,332,1,0,0,
        0,333,334,1,0,0,0,334,335,1,0,0,0,335,336,5,45,0,0,336,337,3,18,
        9,0,337,67,1,0,0,0,338,339,5,16,0,0,339,340,3,78,39,0,340,69,1,0,
        0,0,341,342,5,23,0,0,342,345,3,132,66,0,343,344,5,45,0,0,344,346,
        3,72,36,0,345,343,1,0,0,0,345,346,1,0,0,0,346,352,1,0,0,0,347,349,
        5,62,0,0,348,350,3,74,37,0,349,348,1,0,0,0,349,350,1,0,0,0,350,351,
        1,0,0,0,351,353,5,63,0,0,352,347,1,0,0,0,352,353,1,0,0,0,353,71,
        1,0,0,0,354,355,3,138,69,0,355,73,1,0,0,0,356,361,3,76,38,0,357,
        358,5,44,0,0,358,360,3,76,38,0,359,357,1,0,0,0,360,363,1,0,0,0,361,
        359,1,0,0,0,361,362,1,0,0,0,362,75,1,0,0,0,363,361,1,0,0,0,364,365,
        3,138,69,0,365,366,5,48,0,0,366,367,3,140,70,0,367,77,1,0,0,0,368,
        370,3,94,47,0,369,371,3,80,40,0,370,369,1,0,0,0,371,372,1,0,0,0,
        372,370,1,0,0,0,372,373,1,0,0,0,373,79,1,0,0,0,374,381,3,82,41,0,
        375,381,3,84,42,0,376,381,3,86,43,0,377,381,3,88,44,0,378,381,3,
        90,45,0,379,381,3,92,46,0,380,374,1,0,0,0,380,375,1,0,0,0,380,376,
        1,0,0,0,380,377,1,0,0,0,380,378,1,0,0,0,380,379,1,0,0,0,381,81,1,
        0,0,0,382,383,5,62,0,0,383,384,3,94,47,0,384,83,1,0,0,0,385,386,
        5,63,0,0,386,387,3,94,47,0,387,85,1,0,0,0,388,389,5,66,0,0,389,390,
        3,94,47,0,390,87,1,0,0,0,391,392,5,65,0,0,392,393,3,94,47,0,393,
        89,1,0,0,0,394,395,5,20,0,0,395,396,3,94,47,0,396,91,1,0,0,0,397,
        398,5,21,0,0,398,399,3,94,47,0,399,93,1,0,0,0,400,401,6,47,-1,0,
        401,402,3,96,48,0,402,408,1,0,0,0,403,404,10,2,0,0,404,405,7,3,0,
        0,405,407,3,96,48,0,406,403,1,0,0,0,407,410,1,0,0,0,408,406,1,0,
        0,0,408,409,1,0,0,0,409,95,1,0,0,0,410,408,1,0,0,0,411,412,6,48,
        -1,0,412,413,3,98,49,0,413,419,1,0,0,0,414,415,10,2,0,0,415,416,
        7,4,0,0,416,418,3,98,49,0,417,414,1,0,0,0,418,421,1,0,0,0,419,417,
        1,0,0,0,419,420,1,0,0,0,420,97,1,0,0,0,421,419,1,0,0,0,422,423,6,
        49,-1,0,423,424,3,100,50,0,424,430,1,0,0,0,425,426,10,2,0,0,426,
        427,7,5,0,0,427,429,3,100,50,0,428,425,1,0,0,0,429,432,1,0,0,0,430,
        428,1,0,0,0,430,431,1,0,0,0,431,99,1,0,0,0,432,430,1,0,0,0,433,436,
        3,102,51,0,434,435,5,47,0,0,435,437,3,102,51,0,436,434,1,0,0,0,436,
        437,1,0,0,0,437,101,1,0,0,0,438,449,3,104,52,0,439,440,3,138,69,
        0,440,442,5,42,0,0,441,443,3,104,52,0,442,441,1,0,0,0,443,444,1,
        0,0,0,444,442,1,0,0,0,444,445,1,0,0,0,445,446,1,0,0,0,446,447,5,
        43,0,0,447,449,1,0,0,0,448,438,1,0,0,0,448,439,1,0,0,0,449,103,1,
        0,0,0,450,451,3,108,54,0,451,105,1,0,0,0,452,466,5,49,0,0,453,455,
        3,148,74,0,454,453,1,0,0,0,454,455,1,0,0,0,455,456,1,0,0,0,456,458,
        5,45,0,0,457,459,3,148,74,0,458,457,1,0,0,0,458,459,1,0,0,0,459,
        464,1,0,0,0,460,462,5,45,0,0,461,463,3,148,74,0,462,461,1,0,0,0,
        462,463,1,0,0,0,463,465,1,0,0,0,464,460,1,0,0,0,464,465,1,0,0,0,
        465,467,1,0,0,0,466,454,1,0,0,0,466,467,1,0,0,0,467,468,1,0,0,0,
        468,469,5,50,0,0,469,107,1,0,0,0,470,474,3,130,65,0,471,474,3,112,
        56,0,472,474,3,110,55,0,473,470,1,0,0,0,473,471,1,0,0,0,473,472,
        1,0,0,0,474,109,1,0,0,0,475,476,5,42,0,0,476,477,3,94,47,0,477,478,
        5,43,0,0,478,111,1,0,0,0,479,483,3,114,57,0,480,483,3,116,58,0,481,
        483,3,118,59,0,482,479,1,0,0,0,482,480,1,0,0,0,482,481,1,0,0,0,483,
        113,1,0,0,0,484,485,3,118,59,0,485,486,5,17,0,0,486,487,3,118,59,
        0,487,115,1,0,0,0,488,489,3,118,59,0,489,490,5,35,0,0,490,491,3,
        120,60,0,491,117,1,0,0,0,492,494,3,150,75,0,493,495,3,138,69,0,494,
        493,1,0,0,0,494,495,1,0,0,0,495,119,1,0,0,0,496,499,3,152,76,0,497,
        500,5,38,0,0,498,500,3,138,69,0,499,497,1,0,0,0,499,498,1,0,0,0,
        499,500,1,0,0,0,500,121,1,0,0,0,501,502,3,148,74,0,502,123,1,0,0,
        0,503,504,5,49,0,0,504,505,3,122,61,0,505,506,5,50,0,0,506,125,1,
        0,0,0,507,508,5,39,0,0,508,509,3,146,73,0,509,127,1,0,0,0,510,512,
        3,138,69,0,511,513,3,124,62,0,512,511,1,0,0,0,512,513,1,0,0,0,513,
        129,1,0,0,0,514,519,3,128,64,0,515,516,5,39,0,0,516,518,3,128,64,
        0,517,515,1,0,0,0,518,521,1,0,0,0,519,517,1,0,0,0,519,520,1,0,0,
        0,520,523,1,0,0,0,521,519,1,0,0,0,522,524,3,126,63,0,523,522,1,0,
        0,0,523,524,1,0,0,0,524,131,1,0,0,0,525,530,3,138,69,0,526,527,5,
        39,0,0,527,529,3,138,69,0,528,526,1,0,0,0,529,532,1,0,0,0,530,528,
        1,0,0,0,530,531,1,0,0,0,531,133,1,0,0,0,532,530,1,0,0,0,533,534,
        3,138,69,0,534,135,1,0,0,0,535,536,5,45,0,0,536,537,3,134,67,0,537,
        137,1,0,0,0,538,539,5,26,0,0,539,139,1,0,0,0,540,544,3,142,71,0,
        541,544,3,144,72,0,542,544,3,150,75,0,543,540,1,0,0,0,543,541,1,
        0,0,0,543,542,1,0,0,0,544,141,1,0,0,0,545,546,5,3,0,0,546,143,1,
        0,0,0,547,548,7,6,0,0,548,145,1,0,0,0,549,550,3,152,76,0,550,147,
        1,0,0,0,551,552,3,150,75,0,552,149,1,0,0,0,553,555,7,4,0,0,554,553,
        1,0,0,0,554,555,1,0,0,0,555,556,1,0,0,0,556,557,3,152,76,0,557,151,
        1,0,0,0,558,559,5,4,0,0,559,153,1,0,0,0,47,156,158,168,175,179,198,
        202,207,223,227,236,244,252,270,277,288,299,312,320,333,345,349,
        352,361,372,380,408,419,430,436,444,448,454,458,462,464,466,473,
        482,494,499,512,519,523,530,543,554
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
                     "'~>'", "'~'", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "'+/-'", "'\\u00B1'", 
                     "'%'", "'.'", "'...'", "'*'", "'('", "')'", "','", 
                     "':'", "';'", "'**'", "'='", "'['", "']'", "'|'", "'^'", 
                     "'&'", "'<<'", "'>>'", "'+'", "'-'", "'/'", "'//'", 
                     "'{'", "'}'", "'<'", "'>'", "'=='", "'>='", "'<='", 
                     "'<>'", "'!='", "'@'", "'->'", "'+='", "'-='", "'*='", 
                     "'@='", "'/='", "'&='", "'|='", "'^='", "'<<='", "'>>='", 
                     "'**='", "'//='" ]

    symbolicNames = [ "<INVALID>", "INDENT", "DEDENT", "STRING", "NUMBER", 
                      "INTEGER", "COMPONENT", "MODULE", "INTERFACE", "PIN", 
                      "SIGNAL", "NEW", "FROM", "IMPORT", "FOR", "IN", "ASSERT", 
                      "TO", "TRUE", "FALSE", "WITHIN", "IS", "PASS", "TRAIT", 
                      "SPERM", "WIRE", "NAME", "STRING_LITERAL", "BYTES_LITERAL", 
                      "DECIMAL_INTEGER", "OCT_INTEGER", "HEX_INTEGER", "BIN_INTEGER", 
                      "FLOAT_NUMBER", "IMAG_NUMBER", "PLUS_OR_MINUS", "PLUS_SLASH_MINUS", 
                      "PLUS_MINUS_SIGN", "PERCENT", "DOT", "ELLIPSIS", "STAR", 
                      "OPEN_PAREN", "CLOSE_PAREN", "COMMA", "COLON", "SEMI_COLON", 
                      "POWER", "ASSIGN", "OPEN_BRACK", "CLOSE_BRACK", "OR_OP", 
                      "XOR", "AND_OP", "LEFT_SHIFT", "RIGHT_SHIFT", "PLUS", 
                      "MINUS", "DIV", "IDIV", "OPEN_BRACE", "CLOSE_BRACE", 
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
    RULE_directed_connect_stmt = 21
    RULE_connect_stmt = 22
    RULE_bridgeable = 23
    RULE_connectable = 24
    RULE_signaldef_stmt = 25
    RULE_pindef_stmt = 26
    RULE_pin_declaration = 27
    RULE_pin_stmt = 28
    RULE_new_stmt = 29
    RULE_new_count = 30
    RULE_string_stmt = 31
    RULE_pass_stmt = 32
    RULE_for_stmt = 33
    RULE_assert_stmt = 34
    RULE_trait_stmt = 35
    RULE_constructor = 36
    RULE_trait_parameter_list = 37
    RULE_trait_parameter = 38
    RULE_comparison = 39
    RULE_compare_op_pair = 40
    RULE_lt_arithmetic_or = 41
    RULE_gt_arithmetic_or = 42
    RULE_lt_eq_arithmetic_or = 43
    RULE_gt_eq_arithmetic_or = 44
    RULE_in_arithmetic_or = 45
    RULE_is_arithmetic_or = 46
    RULE_arithmetic_expression = 47
    RULE_sum = 48
    RULE_term = 49
    RULE_power = 50
    RULE_functional = 51
    RULE_bound = 52
    RULE_slice = 53
    RULE_atom = 54
    RULE_arithmetic_group = 55
    RULE_literal_physical = 56
    RULE_bound_quantity = 57
    RULE_bilateral_quantity = 58
    RULE_quantity = 59
    RULE_bilateral_tolerance = 60
    RULE_key = 61
    RULE_array_index = 62
    RULE_pin_reference_end = 63
    RULE_field_reference_part = 64
    RULE_field_reference = 65
    RULE_type_reference = 66
    RULE_unit = 67
    RULE_type_info = 68
    RULE_name = 69
    RULE_literal = 70
    RULE_string = 71
    RULE_boolean_ = 72
    RULE_number_hint_natural = 73
    RULE_number_hint_integer = 74
    RULE_number = 75
    RULE_number_signless = 76

    ruleNames =  [ "file_input", "pragma_stmt", "stmt", "simple_stmts", 
                   "simple_stmt", "compound_stmt", "blockdef", "blockdef_super", 
                   "blocktype", "block", "dep_import_stmt", "import_stmt", 
                   "declaration_stmt", "field_reference_or_declaration", 
                   "assign_stmt", "cum_assign_stmt", "set_assign_stmt", 
                   "cum_operator", "cum_assignable", "assignable", "retype_stmt", 
                   "directed_connect_stmt", "connect_stmt", "bridgeable", 
                   "connectable", "signaldef_stmt", "pindef_stmt", "pin_declaration", 
                   "pin_stmt", "new_stmt", "new_count", "string_stmt", "pass_stmt", 
                   "for_stmt", "assert_stmt", "trait_stmt", "constructor", 
                   "trait_parameter_list", "trait_parameter", "comparison", 
                   "compare_op_pair", "lt_arithmetic_or", "gt_arithmetic_or", 
                   "lt_eq_arithmetic_or", "gt_eq_arithmetic_or", "in_arithmetic_or", 
                   "is_arithmetic_or", "arithmetic_expression", "sum", "term", 
                   "power", "functional", "bound", "slice", "atom", "arithmetic_group", 
                   "literal_physical", "bound_quantity", "bilateral_quantity", 
                   "quantity", "bilateral_tolerance", "key", "array_index", 
                   "pin_reference_end", "field_reference_part", "field_reference", 
                   "type_reference", "unit", "type_info", "name", "literal", 
                   "string", "boolean_", "number_hint_natural", "number_hint_integer", 
                   "number", "number_signless" ]

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
    SPERM=24
    WIRE=25
    NAME=26
    STRING_LITERAL=27
    BYTES_LITERAL=28
    DECIMAL_INTEGER=29
    OCT_INTEGER=30
    HEX_INTEGER=31
    BIN_INTEGER=32
    FLOAT_NUMBER=33
    IMAG_NUMBER=34
    PLUS_OR_MINUS=35
    PLUS_SLASH_MINUS=36
    PLUS_MINUS_SIGN=37
    PERCENT=38
    DOT=39
    ELLIPSIS=40
    STAR=41
    OPEN_PAREN=42
    CLOSE_PAREN=43
    COMMA=44
    COLON=45
    SEMI_COLON=46
    POWER=47
    ASSIGN=48
    OPEN_BRACK=49
    CLOSE_BRACK=50
    OR_OP=51
    XOR=52
    AND_OP=53
    LEFT_SHIFT=54
    RIGHT_SHIFT=55
    PLUS=56
    MINUS=57
    DIV=58
    IDIV=59
    OPEN_BRACE=60
    CLOSE_BRACE=61
    LESS_THAN=62
    GREATER_THAN=63
    EQUALS=64
    GT_EQ=65
    LT_EQ=66
    NOT_EQ_1=67
    NOT_EQ_2=68
    AT=69
    ARROW=70
    ADD_ASSIGN=71
    SUB_ASSIGN=72
    MULT_ASSIGN=73
    AT_ASSIGN=74
    DIV_ASSIGN=75
    AND_ASSIGN=76
    OR_ASSIGN=77
    XOR_ASSIGN=78
    LEFT_SHIFT_ASSIGN=79
    RIGHT_SHIFT_ASSIGN=80
    POWER_ASSIGN=81
    IDIV_ASSIGN=82
    NEWLINE=83
    PRAGMA=84
    COMMENT=85
    WS=86
    EXPLICIT_LINE_JOINING=87
    ERRORTOKEN=88

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
            self.state = 158
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 79787976) != 0) or _la==83 or _la==84:
                self.state = 156
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [83]:
                    self.state = 154
                    self.match(AtoParser.NEWLINE)
                    pass
                elif token in [3, 6, 7, 8, 9, 10, 12, 13, 14, 16, 22, 23, 26, 84]:
                    self.state = 155
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 160
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 161
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
            self.state = 163
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
            self.state = 168
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 16, 22, 23, 26]:
                self.enterOuterAlt(localctx, 1)
                self.state = 165
                self.simple_stmts()
                pass
            elif token in [6, 7, 8, 14]:
                self.enterOuterAlt(localctx, 2)
                self.state = 166
                self.compound_stmt()
                pass
            elif token in [84]:
                self.enterOuterAlt(localctx, 3)
                self.state = 167
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
            self.state = 170
            self.simple_stmt()
            self.state = 175
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 171
                    self.match(AtoParser.SEMI_COLON)
                    self.state = 172
                    self.simple_stmt() 
                self.state = 177
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 179
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==46:
                self.state = 178
                self.match(AtoParser.SEMI_COLON)


            self.state = 181
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
            self.state = 198
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 183
                self.import_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 184
                self.dep_import_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 185
                self.assign_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 186
                self.cum_assign_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 187
                self.set_assign_stmt()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 188
                self.connect_stmt()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 189
                self.directed_connect_stmt()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 190
                self.retype_stmt()
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 191
                self.pin_declaration()
                pass

            elif la_ == 10:
                self.enterOuterAlt(localctx, 10)
                self.state = 192
                self.signaldef_stmt()
                pass

            elif la_ == 11:
                self.enterOuterAlt(localctx, 11)
                self.state = 193
                self.assert_stmt()
                pass

            elif la_ == 12:
                self.enterOuterAlt(localctx, 12)
                self.state = 194
                self.declaration_stmt()
                pass

            elif la_ == 13:
                self.enterOuterAlt(localctx, 13)
                self.state = 195
                self.string_stmt()
                pass

            elif la_ == 14:
                self.enterOuterAlt(localctx, 14)
                self.state = 196
                self.pass_stmt()
                pass

            elif la_ == 15:
                self.enterOuterAlt(localctx, 15)
                self.state = 197
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
            self.state = 202
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [6, 7, 8]:
                self.enterOuterAlt(localctx, 1)
                self.state = 200
                self.blockdef()
                pass
            elif token in [14]:
                self.enterOuterAlt(localctx, 2)
                self.state = 201
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
            self.state = 204
            self.blocktype()
            self.state = 205
            self.name()
            self.state = 207
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 206
                self.blockdef_super()


            self.state = 209
            self.match(AtoParser.COLON)
            self.state = 210
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
            self.state = 212
            self.match(AtoParser.FROM)
            self.state = 213
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
            self.state = 215
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
            self.state = 227
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 16, 22, 23, 26]:
                self.enterOuterAlt(localctx, 1)
                self.state = 217
                self.simple_stmts()
                pass
            elif token in [83]:
                self.enterOuterAlt(localctx, 2)
                self.state = 218
                self.match(AtoParser.NEWLINE)
                self.state = 219
                self.match(AtoParser.INDENT)
                self.state = 221 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 220
                    self.stmt()
                    self.state = 223 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 79787976) != 0) or _la==84):
                        break

                self.state = 225
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
            self.state = 229
            self.match(AtoParser.IMPORT)
            self.state = 230
            self.type_reference()
            self.state = 231
            self.match(AtoParser.FROM)
            self.state = 232
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
            self.state = 236
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 234
                self.match(AtoParser.FROM)
                self.state = 235
                self.string()


            self.state = 238
            self.match(AtoParser.IMPORT)
            self.state = 239
            self.type_reference()
            self.state = 244
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==44:
                self.state = 240
                self.match(AtoParser.COMMA)
                self.state = 241
                self.type_reference()
                self.state = 246
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
            self.state = 247
            self.field_reference()
            self.state = 248
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
            self.state = 252
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 250
                self.field_reference()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 251
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
            self.state = 254
            self.field_reference_or_declaration()
            self.state = 255
            self.match(AtoParser.ASSIGN)
            self.state = 256
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
            self.state = 258
            self.field_reference_or_declaration()
            self.state = 259
            self.cum_operator()
            self.state = 260
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
            self.state = 262
            self.field_reference_or_declaration()
            self.state = 263
            _la = self._input.LA(1)
            if not(_la==76 or _la==77):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 264
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
            self.state = 266
            _la = self._input.LA(1)
            if not(_la==71 or _la==72):
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
            self.state = 270
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 268
                self.literal_physical()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 269
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
            self.state = 277
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 272
                self.string()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 273
                self.new_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 274
                self.literal_physical()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 275
                self.arithmetic_expression(0)
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 276
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
            self.state = 279
            self.field_reference()
            self.state = 280
            self.match(AtoParser.ARROW)
            self.state = 281
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


        def SPERM(self, i:int=None):
            if i is None:
                return self.getTokens(AtoParser.SPERM)
            else:
                return self.getToken(AtoParser.SPERM, i)

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
        self.enterRule(localctx, 42, self.RULE_directed_connect_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 283
            self.connectable()
            self.state = 286 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 284
                self.match(AtoParser.SPERM)
                self.state = 285
                self.bridgeable()
                self.state = 288 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==24):
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


        def WIRE(self):
            return self.getToken(AtoParser.WIRE, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_connect_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConnect_stmt" ):
                return visitor.visitConnect_stmt(self)
            else:
                return visitor.visitChildren(self)




    def connect_stmt(self):

        localctx = AtoParser.Connect_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 290
            self.connectable()
            self.state = 291
            self.match(AtoParser.WIRE)
            self.state = 292
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
        self.enterRule(localctx, 46, self.RULE_bridgeable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 294
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
        self.enterRule(localctx, 48, self.RULE_connectable)
        try:
            self.state = 299
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [26]:
                self.enterOuterAlt(localctx, 1)
                self.state = 296
                self.field_reference()
                pass
            elif token in [10]:
                self.enterOuterAlt(localctx, 2)
                self.state = 297
                self.signaldef_stmt()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 3)
                self.state = 298
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
        self.enterRule(localctx, 50, self.RULE_signaldef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 301
            self.match(AtoParser.SIGNAL)
            self.state = 302
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
        self.enterRule(localctx, 52, self.RULE_pindef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 304
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
        self.enterRule(localctx, 54, self.RULE_pin_declaration)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 306
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


        def number_hint_natural(self):
            return self.getTypedRuleContext(AtoParser.Number_hint_naturalContext,0)


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
        self.enterRule(localctx, 56, self.RULE_pin_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 308
            self.match(AtoParser.PIN)
            self.state = 312
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [26]:
                self.state = 309
                self.name()
                pass
            elif token in [4]:
                self.state = 310
                self.number_hint_natural()
                pass
            elif token in [3]:
                self.state = 311
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
        self.enterRule(localctx, 58, self.RULE_new_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 314
            self.match(AtoParser.NEW)
            self.state = 315
            self.type_reference()
            self.state = 320
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==49:
                self.state = 316
                self.match(AtoParser.OPEN_BRACK)
                self.state = 317
                self.new_count()
                self.state = 318
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

        def number_hint_natural(self):
            return self.getTypedRuleContext(AtoParser.Number_hint_naturalContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_new_count

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNew_count" ):
                return visitor.visitNew_count(self)
            else:
                return visitor.visitChildren(self)




    def new_count(self):

        localctx = AtoParser.New_countContext(self, self._ctx, self.state)
        self.enterRule(localctx, 60, self.RULE_new_count)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 322
            self.number_hint_natural()
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
        self.enterRule(localctx, 62, self.RULE_string_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 324
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
        self.enterRule(localctx, 64, self.RULE_pass_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 326
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


        def slice_(self):
            return self.getTypedRuleContext(AtoParser.SliceContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_for_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFor_stmt" ):
                return visitor.visitFor_stmt(self)
            else:
                return visitor.visitChildren(self)




    def for_stmt(self):

        localctx = AtoParser.For_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 66, self.RULE_for_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 328
            self.match(AtoParser.FOR)
            self.state = 329
            self.name()
            self.state = 330
            self.match(AtoParser.IN)
            self.state = 331
            self.field_reference()
            self.state = 333
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==49:
                self.state = 332
                self.slice_()


            self.state = 335
            self.match(AtoParser.COLON)
            self.state = 336
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
        self.enterRule(localctx, 68, self.RULE_assert_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 338
            self.match(AtoParser.ASSERT)
            self.state = 339
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

        def type_reference(self):
            return self.getTypedRuleContext(AtoParser.Type_referenceContext,0)


        def COLON(self):
            return self.getToken(AtoParser.COLON, 0)

        def constructor(self):
            return self.getTypedRuleContext(AtoParser.ConstructorContext,0)


        def LESS_THAN(self):
            return self.getToken(AtoParser.LESS_THAN, 0)

        def GREATER_THAN(self):
            return self.getToken(AtoParser.GREATER_THAN, 0)

        def trait_parameter_list(self):
            return self.getTypedRuleContext(AtoParser.Trait_parameter_listContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_trait_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTrait_stmt" ):
                return visitor.visitTrait_stmt(self)
            else:
                return visitor.visitChildren(self)




    def trait_stmt(self):

        localctx = AtoParser.Trait_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 70, self.RULE_trait_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 341
            self.match(AtoParser.TRAIT)
            self.state = 342
            self.type_reference()
            self.state = 345
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==45:
                self.state = 343
                self.match(AtoParser.COLON)
                self.state = 344
                self.constructor()


            self.state = 352
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==62:
                self.state = 347
                self.match(AtoParser.LESS_THAN)
                self.state = 349
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==26:
                    self.state = 348
                    self.trait_parameter_list()


                self.state = 351
                self.match(AtoParser.GREATER_THAN)


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ConstructorContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_constructor

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConstructor" ):
                return visitor.visitConstructor(self)
            else:
                return visitor.visitChildren(self)




    def constructor(self):

        localctx = AtoParser.ConstructorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 72, self.RULE_constructor)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 354
            self.name()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Trait_parameter_listContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def trait_parameter(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtoParser.Trait_parameterContext)
            else:
                return self.getTypedRuleContext(AtoParser.Trait_parameterContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(AtoParser.COMMA)
            else:
                return self.getToken(AtoParser.COMMA, i)

        def getRuleIndex(self):
            return AtoParser.RULE_trait_parameter_list

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTrait_parameter_list" ):
                return visitor.visitTrait_parameter_list(self)
            else:
                return visitor.visitChildren(self)




    def trait_parameter_list(self):

        localctx = AtoParser.Trait_parameter_listContext(self, self._ctx, self.state)
        self.enterRule(localctx, 74, self.RULE_trait_parameter_list)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 356
            self.trait_parameter()
            self.state = 361
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==44:
                self.state = 357
                self.match(AtoParser.COMMA)
                self.state = 358
                self.trait_parameter()
                self.state = 363
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Trait_parameterContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def ASSIGN(self):
            return self.getToken(AtoParser.ASSIGN, 0)

        def literal(self):
            return self.getTypedRuleContext(AtoParser.LiteralContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_trait_parameter

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTrait_parameter" ):
                return visitor.visitTrait_parameter(self)
            else:
                return visitor.visitChildren(self)




    def trait_parameter(self):

        localctx = AtoParser.Trait_parameterContext(self, self._ctx, self.state)
        self.enterRule(localctx, 76, self.RULE_trait_parameter)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 364
            self.name()
            self.state = 365
            self.match(AtoParser.ASSIGN)
            self.state = 366
            self.literal()
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
        self.enterRule(localctx, 78, self.RULE_comparison)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 368
            self.arithmetic_expression(0)
            self.state = 370 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 369
                self.compare_op_pair()
                self.state = 372 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (((((_la - 20)) & ~0x3f) == 0 and ((1 << (_la - 20)) & 118747255799811) != 0)):
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
        self.enterRule(localctx, 80, self.RULE_compare_op_pair)
        try:
            self.state = 380
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [62]:
                self.enterOuterAlt(localctx, 1)
                self.state = 374
                self.lt_arithmetic_or()
                pass
            elif token in [63]:
                self.enterOuterAlt(localctx, 2)
                self.state = 375
                self.gt_arithmetic_or()
                pass
            elif token in [66]:
                self.enterOuterAlt(localctx, 3)
                self.state = 376
                self.lt_eq_arithmetic_or()
                pass
            elif token in [65]:
                self.enterOuterAlt(localctx, 4)
                self.state = 377
                self.gt_eq_arithmetic_or()
                pass
            elif token in [20]:
                self.enterOuterAlt(localctx, 5)
                self.state = 378
                self.in_arithmetic_or()
                pass
            elif token in [21]:
                self.enterOuterAlt(localctx, 6)
                self.state = 379
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
        self.enterRule(localctx, 82, self.RULE_lt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 382
            self.match(AtoParser.LESS_THAN)
            self.state = 383
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
        self.enterRule(localctx, 84, self.RULE_gt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 385
            self.match(AtoParser.GREATER_THAN)
            self.state = 386
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
        self.enterRule(localctx, 86, self.RULE_lt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 388
            self.match(AtoParser.LT_EQ)
            self.state = 389
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
        self.enterRule(localctx, 88, self.RULE_gt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 391
            self.match(AtoParser.GT_EQ)
            self.state = 392
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
        self.enterRule(localctx, 90, self.RULE_in_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 394
            self.match(AtoParser.WITHIN)
            self.state = 395
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
        self.enterRule(localctx, 92, self.RULE_is_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 397
            self.match(AtoParser.IS)
            self.state = 398
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
        _startState = 94
        self.enterRecursionRule(localctx, 94, self.RULE_arithmetic_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 401
            self.sum_(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 408
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,26,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.Arithmetic_expressionContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmetic_expression)
                    self.state = 403
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 404
                    _la = self._input.LA(1)
                    if not(_la==51 or _la==53):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 405
                    self.sum_(0) 
                self.state = 410
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,26,self._ctx)

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


        def PLUS(self):
            return self.getToken(AtoParser.PLUS, 0)

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
        _startState = 96
        self.enterRecursionRule(localctx, 96, self.RULE_sum, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 412
            self.term(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 419
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,27,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.SumContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_sum)
                    self.state = 414
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 415
                    _la = self._input.LA(1)
                    if not(_la==56 or _la==57):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 416
                    self.term(0) 
                self.state = 421
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,27,self._ctx)

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
        _startState = 98
        self.enterRecursionRule(localctx, 98, self.RULE_term, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 423
            self.power()
            self._ctx.stop = self._input.LT(-1)
            self.state = 430
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,28,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.TermContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_term)
                    self.state = 425
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 426
                    _la = self._input.LA(1)
                    if not(_la==41 or _la==58):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 427
                    self.power() 
                self.state = 432
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,28,self._ctx)

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
        self.enterRule(localctx, 100, self.RULE_power)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 433
            self.functional()
            self.state = 436
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,29,self._ctx)
            if la_ == 1:
                self.state = 434
                self.match(AtoParser.POWER)
                self.state = 435
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
        self.enterRule(localctx, 102, self.RULE_functional)
        self._la = 0 # Token type
        try:
            self.state = 448
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,31,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 438
                self.bound()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 439
                self.name()
                self.state = 440
                self.match(AtoParser.OPEN_PAREN)
                self.state = 442 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 441
                    self.bound()
                    self.state = 444 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 216177180227403792) != 0)):
                        break

                self.state = 446
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
        self.enterRule(localctx, 104, self.RULE_bound)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 450
            self.atom()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SliceContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def OPEN_BRACK(self):
            return self.getToken(AtoParser.OPEN_BRACK, 0)

        def CLOSE_BRACK(self):
            return self.getToken(AtoParser.CLOSE_BRACK, 0)

        def COLON(self, i:int=None):
            if i is None:
                return self.getTokens(AtoParser.COLON)
            else:
                return self.getToken(AtoParser.COLON, i)

        def number_hint_integer(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtoParser.Number_hint_integerContext)
            else:
                return self.getTypedRuleContext(AtoParser.Number_hint_integerContext,i)


        def getRuleIndex(self):
            return AtoParser.RULE_slice

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSlice" ):
                return visitor.visitSlice(self)
            else:
                return visitor.visitChildren(self)




    def slice_(self):

        localctx = AtoParser.SliceContext(self, self._ctx, self.state)
        self.enterRule(localctx, 106, self.RULE_slice)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 452
            self.match(AtoParser.OPEN_BRACK)
            self.state = 466
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 216207966485872656) != 0):
                self.state = 454
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 216172782113783824) != 0):
                    self.state = 453
                    self.number_hint_integer()


                self.state = 456
                self.match(AtoParser.COLON)
                self.state = 458
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 216172782113783824) != 0):
                    self.state = 457
                    self.number_hint_integer()


                self.state = 464
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==45:
                    self.state = 460
                    self.match(AtoParser.COLON)
                    self.state = 462
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if (((_la) & ~0x3f) == 0 and ((1 << _la) & 216172782113783824) != 0):
                        self.state = 461
                        self.number_hint_integer()






            self.state = 468
            self.match(AtoParser.CLOSE_BRACK)
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
        self.enterRule(localctx, 108, self.RULE_atom)
        try:
            self.state = 473
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [26]:
                self.enterOuterAlt(localctx, 1)
                self.state = 470
                self.field_reference()
                pass
            elif token in [4, 56, 57]:
                self.enterOuterAlt(localctx, 2)
                self.state = 471
                self.literal_physical()
                pass
            elif token in [42]:
                self.enterOuterAlt(localctx, 3)
                self.state = 472
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
        self.enterRule(localctx, 110, self.RULE_arithmetic_group)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 475
            self.match(AtoParser.OPEN_PAREN)
            self.state = 476
            self.arithmetic_expression(0)
            self.state = 477
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
        self.enterRule(localctx, 112, self.RULE_literal_physical)
        try:
            self.state = 482
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,38,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 479
                self.bound_quantity()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 480
                self.bilateral_quantity()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 481
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
        self.enterRule(localctx, 114, self.RULE_bound_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 484
            self.quantity()
            self.state = 485
            self.match(AtoParser.TO)
            self.state = 486
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
        self.enterRule(localctx, 116, self.RULE_bilateral_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 488
            self.quantity()
            self.state = 489
            self.match(AtoParser.PLUS_OR_MINUS)
            self.state = 490
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

        def number(self):
            return self.getTypedRuleContext(AtoParser.NumberContext,0)


        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_quantity

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitQuantity" ):
                return visitor.visitQuantity(self)
            else:
                return visitor.visitChildren(self)




    def quantity(self):

        localctx = AtoParser.QuantityContext(self, self._ctx, self.state)
        self.enterRule(localctx, 118, self.RULE_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 492
            self.number()
            self.state = 494
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,39,self._ctx)
            if la_ == 1:
                self.state = 493
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

        def number_signless(self):
            return self.getTypedRuleContext(AtoParser.Number_signlessContext,0)


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
        self.enterRule(localctx, 120, self.RULE_bilateral_tolerance)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 496
            self.number_signless()
            self.state = 499
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,40,self._ctx)
            if la_ == 1:
                self.state = 497
                self.match(AtoParser.PERCENT)

            elif la_ == 2:
                self.state = 498
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

        def number_hint_integer(self):
            return self.getTypedRuleContext(AtoParser.Number_hint_integerContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_key

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitKey" ):
                return visitor.visitKey(self)
            else:
                return visitor.visitChildren(self)




    def key(self):

        localctx = AtoParser.KeyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 122, self.RULE_key)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 501
            self.number_hint_integer()
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
        self.enterRule(localctx, 124, self.RULE_array_index)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 503
            self.match(AtoParser.OPEN_BRACK)
            self.state = 504
            self.key()
            self.state = 505
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

        def number_hint_natural(self):
            return self.getTypedRuleContext(AtoParser.Number_hint_naturalContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_pin_reference_end

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPin_reference_end" ):
                return visitor.visitPin_reference_end(self)
            else:
                return visitor.visitChildren(self)




    def pin_reference_end(self):

        localctx = AtoParser.Pin_reference_endContext(self, self._ctx, self.state)
        self.enterRule(localctx, 126, self.RULE_pin_reference_end)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 507
            self.match(AtoParser.DOT)
            self.state = 508
            self.number_hint_natural()
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
        self.enterRule(localctx, 128, self.RULE_field_reference_part)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 510
            self.name()
            self.state = 512
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,41,self._ctx)
            if la_ == 1:
                self.state = 511
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
        self.enterRule(localctx, 130, self.RULE_field_reference)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 514
            self.field_reference_part()
            self.state = 519
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,42,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 515
                    self.match(AtoParser.DOT)
                    self.state = 516
                    self.field_reference_part() 
                self.state = 521
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,42,self._ctx)

            self.state = 523
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,43,self._ctx)
            if la_ == 1:
                self.state = 522
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
        self.enterRule(localctx, 132, self.RULE_type_reference)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 525
            self.name()
            self.state = 530
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==39:
                self.state = 526
                self.match(AtoParser.DOT)
                self.state = 527
                self.name()
                self.state = 532
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
        self.enterRule(localctx, 134, self.RULE_unit)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 533
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
        self.enterRule(localctx, 136, self.RULE_type_info)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 535
            self.match(AtoParser.COLON)
            self.state = 536
            self.unit()
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
        self.enterRule(localctx, 138, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 538
            self.match(AtoParser.NAME)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LiteralContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def string(self):
            return self.getTypedRuleContext(AtoParser.StringContext,0)


        def boolean_(self):
            return self.getTypedRuleContext(AtoParser.Boolean_Context,0)


        def number(self):
            return self.getTypedRuleContext(AtoParser.NumberContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_literal

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLiteral" ):
                return visitor.visitLiteral(self)
            else:
                return visitor.visitChildren(self)




    def literal(self):

        localctx = AtoParser.LiteralContext(self, self._ctx, self.state)
        self.enterRule(localctx, 140, self.RULE_literal)
        try:
            self.state = 543
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3]:
                self.enterOuterAlt(localctx, 1)
                self.state = 540
                self.string()
                pass
            elif token in [18, 19]:
                self.enterOuterAlt(localctx, 2)
                self.state = 541
                self.boolean_()
                pass
            elif token in [4, 56, 57]:
                self.enterOuterAlt(localctx, 3)
                self.state = 542
                self.number()
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
        self.enterRule(localctx, 142, self.RULE_string)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 545
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
        self.enterRule(localctx, 144, self.RULE_boolean_)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 547
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


    class Number_hint_naturalContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def number_signless(self):
            return self.getTypedRuleContext(AtoParser.Number_signlessContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_number_hint_natural

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNumber_hint_natural" ):
                return visitor.visitNumber_hint_natural(self)
            else:
                return visitor.visitChildren(self)




    def number_hint_natural(self):

        localctx = AtoParser.Number_hint_naturalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 146, self.RULE_number_hint_natural)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 549
            self.number_signless()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Number_hint_integerContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def number(self):
            return self.getTypedRuleContext(AtoParser.NumberContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_number_hint_integer

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNumber_hint_integer" ):
                return visitor.visitNumber_hint_integer(self)
            else:
                return visitor.visitChildren(self)




    def number_hint_integer(self):

        localctx = AtoParser.Number_hint_integerContext(self, self._ctx, self.state)
        self.enterRule(localctx, 148, self.RULE_number_hint_integer)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 551
            self.number()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NumberContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def number_signless(self):
            return self.getTypedRuleContext(AtoParser.Number_signlessContext,0)


        def PLUS(self):
            return self.getToken(AtoParser.PLUS, 0)

        def MINUS(self):
            return self.getToken(AtoParser.MINUS, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_number

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNumber" ):
                return visitor.visitNumber(self)
            else:
                return visitor.visitChildren(self)




    def number(self):

        localctx = AtoParser.NumberContext(self, self._ctx, self.state)
        self.enterRule(localctx, 150, self.RULE_number)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 554
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==56 or _la==57:
                self.state = 553
                _la = self._input.LA(1)
                if not(_la==56 or _la==57):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()


            self.state = 556
            self.number_signless()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Number_signlessContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self):
            return self.getToken(AtoParser.NUMBER, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_number_signless

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNumber_signless" ):
                return visitor.visitNumber_signless(self)
            else:
                return visitor.visitChildren(self)




    def number_signless(self):

        localctx = AtoParser.Number_signlessContext(self, self._ctx, self.state)
        self.enterRule(localctx, 152, self.RULE_number_signless)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 558
            self.match(AtoParser.NUMBER)
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
        self._predicates[47] = self.arithmetic_expression_sempred
        self._predicates[48] = self.sum_sempred
        self._predicates[49] = self.term_sempred
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
         




