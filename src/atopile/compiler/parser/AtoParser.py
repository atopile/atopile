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
        4,1,92,555,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
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
        7,72,2,73,7,73,2,74,7,74,2,75,7,75,1,0,1,0,5,0,155,8,0,10,0,12,0,
        158,9,0,1,0,1,0,1,1,1,1,1,2,1,2,1,2,3,2,167,8,2,1,3,1,3,1,3,5,3,
        172,8,3,10,3,12,3,175,9,3,1,3,3,3,178,8,3,1,3,1,3,1,4,1,4,1,4,1,
        4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,3,4,194,8,4,1,5,1,5,3,5,198,8,
        5,1,6,1,6,1,6,3,6,203,8,6,1,6,1,6,1,6,1,7,1,7,1,7,1,8,1,8,1,9,1,
        9,1,9,1,9,4,9,217,8,9,11,9,12,9,218,1,9,1,9,3,9,223,8,9,1,10,1,10,
        3,10,227,8,10,1,10,1,10,1,10,1,11,1,11,1,11,1,12,1,12,3,12,237,8,
        12,1,13,1,13,1,13,1,13,1,14,1,14,1,14,1,14,1,14,3,14,248,8,14,1,
        15,1,15,1,15,1,15,1,16,1,16,1,16,1,16,3,16,258,8,16,1,17,1,17,1,
        17,1,17,1,18,1,18,1,19,1,19,1,20,1,20,1,20,3,20,271,8,20,1,21,1,
        21,1,21,1,22,1,22,1,23,1,23,1,24,1,24,1,24,1,24,3,24,284,8,24,1,
        25,1,25,1,25,1,25,1,25,1,25,3,25,292,8,25,1,25,3,25,295,8,25,1,26,
        1,26,1,27,1,27,1,28,1,28,1,29,1,29,1,29,1,29,5,29,307,8,29,10,29,
        12,29,310,9,29,1,29,3,29,313,8,29,3,29,315,8,29,1,29,1,29,1,30,1,
        30,3,30,321,8,30,1,30,3,30,324,8,30,1,31,1,31,1,31,1,31,1,31,1,31,
        1,31,1,32,1,32,1,32,1,33,1,33,3,33,338,8,33,1,33,1,33,1,33,3,33,
        343,8,33,1,33,3,33,346,8,33,1,34,1,34,1,35,1,35,1,35,1,35,5,35,354,
        8,35,10,35,12,35,357,9,35,1,35,3,35,360,8,35,3,35,362,8,35,1,35,
        1,35,1,36,1,36,1,36,1,36,1,37,1,37,4,37,372,8,37,11,37,12,37,373,
        1,38,1,38,1,38,1,38,1,38,1,38,3,38,382,8,38,1,39,1,39,1,39,1,40,
        1,40,1,40,1,41,1,41,1,41,1,42,1,42,1,42,1,43,1,43,1,43,1,44,1,44,
        1,44,1,45,1,45,1,45,1,45,1,45,1,45,5,45,408,8,45,10,45,12,45,411,
        9,45,1,46,1,46,1,46,1,46,1,46,1,46,5,46,419,8,46,10,46,12,46,422,
        9,46,1,47,1,47,1,47,1,47,1,47,1,47,5,47,430,8,47,10,47,12,47,433,
        9,47,1,48,1,48,1,48,3,48,438,8,48,1,49,1,49,3,49,442,8,49,1,49,1,
        49,3,49,446,8,49,1,49,1,49,3,49,450,8,49,3,49,452,8,49,3,49,454,
        8,49,1,49,1,49,1,49,1,49,3,49,460,8,49,1,49,3,49,463,8,49,1,50,1,
        50,1,51,1,51,1,52,1,52,1,53,1,53,1,53,3,53,474,8,53,1,54,1,54,1,
        54,1,54,1,55,1,55,1,55,3,55,483,8,55,1,56,1,56,1,56,1,56,1,57,1,
        57,1,57,1,57,1,58,1,58,3,58,495,8,58,1,59,1,59,1,59,3,59,500,8,59,
        1,60,1,60,1,61,1,61,1,61,1,61,1,62,1,62,1,62,1,63,1,63,3,63,513,
        8,63,1,64,1,64,1,64,5,64,518,8,64,10,64,12,64,521,9,64,1,64,3,64,
        524,8,64,1,65,1,65,1,66,1,66,1,67,1,67,1,67,1,68,1,68,1,69,1,69,
        1,69,3,69,538,8,69,1,70,1,70,1,71,1,71,1,72,1,72,1,73,1,73,1,74,
        3,74,549,8,74,1,74,1,74,1,75,1,75,1,75,0,3,90,92,94,76,0,2,4,6,8,
        10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,
        54,56,58,60,62,64,66,68,70,72,74,76,78,80,82,84,86,88,90,92,94,96,
        98,100,102,104,106,108,110,112,114,116,118,120,122,124,126,128,130,
        132,134,136,138,140,142,144,146,148,150,0,6,1,0,6,8,1,0,24,25,2,
        0,67,67,69,69,1,0,72,73,2,0,56,56,74,74,1,0,18,19,553,0,156,1,0,
        0,0,2,161,1,0,0,0,4,166,1,0,0,0,6,168,1,0,0,0,8,193,1,0,0,0,10,197,
        1,0,0,0,12,199,1,0,0,0,14,207,1,0,0,0,16,210,1,0,0,0,18,222,1,0,
        0,0,20,226,1,0,0,0,22,231,1,0,0,0,24,236,1,0,0,0,26,238,1,0,0,0,
        28,247,1,0,0,0,30,249,1,0,0,0,32,253,1,0,0,0,34,259,1,0,0,0,36,263,
        1,0,0,0,38,265,1,0,0,0,40,270,1,0,0,0,42,272,1,0,0,0,44,275,1,0,
        0,0,46,277,1,0,0,0,48,279,1,0,0,0,50,285,1,0,0,0,52,296,1,0,0,0,
        54,298,1,0,0,0,56,300,1,0,0,0,58,302,1,0,0,0,60,323,1,0,0,0,62,325,
        1,0,0,0,64,332,1,0,0,0,66,335,1,0,0,0,68,347,1,0,0,0,70,349,1,0,
        0,0,72,365,1,0,0,0,74,369,1,0,0,0,76,381,1,0,0,0,78,383,1,0,0,0,
        80,386,1,0,0,0,82,389,1,0,0,0,84,392,1,0,0,0,86,395,1,0,0,0,88,398,
        1,0,0,0,90,401,1,0,0,0,92,412,1,0,0,0,94,423,1,0,0,0,96,434,1,0,
        0,0,98,462,1,0,0,0,100,464,1,0,0,0,102,466,1,0,0,0,104,468,1,0,0,
        0,106,473,1,0,0,0,108,475,1,0,0,0,110,482,1,0,0,0,112,484,1,0,0,
        0,114,488,1,0,0,0,116,492,1,0,0,0,118,496,1,0,0,0,120,501,1,0,0,
        0,122,503,1,0,0,0,124,507,1,0,0,0,126,510,1,0,0,0,128,514,1,0,0,
        0,130,525,1,0,0,0,132,527,1,0,0,0,134,529,1,0,0,0,136,532,1,0,0,
        0,138,537,1,0,0,0,140,539,1,0,0,0,142,541,1,0,0,0,144,543,1,0,0,
        0,146,545,1,0,0,0,148,548,1,0,0,0,150,552,1,0,0,0,152,155,5,87,0,
        0,153,155,3,4,2,0,154,152,1,0,0,0,154,153,1,0,0,0,155,158,1,0,0,
        0,156,154,1,0,0,0,156,157,1,0,0,0,157,159,1,0,0,0,158,156,1,0,0,
        0,159,160,5,0,0,1,160,1,1,0,0,0,161,162,5,88,0,0,162,3,1,0,0,0,163,
        167,3,6,3,0,164,167,3,10,5,0,165,167,3,2,1,0,166,163,1,0,0,0,166,
        164,1,0,0,0,166,165,1,0,0,0,167,5,1,0,0,0,168,173,3,8,4,0,169,170,
        5,62,0,0,170,172,3,8,4,0,171,169,1,0,0,0,172,175,1,0,0,0,173,171,
        1,0,0,0,173,174,1,0,0,0,174,177,1,0,0,0,175,173,1,0,0,0,176,178,
        5,62,0,0,177,176,1,0,0,0,177,178,1,0,0,0,178,179,1,0,0,0,179,180,
        5,87,0,0,180,7,1,0,0,0,181,194,3,20,10,0,182,194,3,26,13,0,183,194,
        3,34,17,0,184,194,3,32,16,0,185,194,3,30,15,0,186,194,3,46,23,0,
        187,194,3,42,21,0,188,194,3,64,32,0,189,194,3,22,11,0,190,194,3,
        54,27,0,191,194,3,56,28,0,192,194,3,66,33,0,193,181,1,0,0,0,193,
        182,1,0,0,0,193,183,1,0,0,0,193,184,1,0,0,0,193,185,1,0,0,0,193,
        186,1,0,0,0,193,187,1,0,0,0,193,188,1,0,0,0,193,189,1,0,0,0,193,
        190,1,0,0,0,193,191,1,0,0,0,193,192,1,0,0,0,194,9,1,0,0,0,195,198,
        3,12,6,0,196,198,3,62,31,0,197,195,1,0,0,0,197,196,1,0,0,0,198,11,
        1,0,0,0,199,200,3,16,8,0,200,202,3,130,65,0,201,203,3,14,7,0,202,
        201,1,0,0,0,202,203,1,0,0,0,203,204,1,0,0,0,204,205,5,61,0,0,205,
        206,3,18,9,0,206,13,1,0,0,0,207,208,5,12,0,0,208,209,3,130,65,0,
        209,15,1,0,0,0,210,211,7,0,0,0,211,17,1,0,0,0,212,223,3,6,3,0,213,
        214,5,87,0,0,214,216,5,1,0,0,215,217,3,4,2,0,216,215,1,0,0,0,217,
        218,1,0,0,0,218,216,1,0,0,0,218,219,1,0,0,0,219,220,1,0,0,0,220,
        221,5,2,0,0,221,223,1,0,0,0,222,212,1,0,0,0,222,213,1,0,0,0,223,
        19,1,0,0,0,224,225,5,12,0,0,225,227,3,140,70,0,226,224,1,0,0,0,226,
        227,1,0,0,0,227,228,1,0,0,0,228,229,5,13,0,0,229,230,3,130,65,0,
        230,21,1,0,0,0,231,232,3,128,64,0,232,233,3,134,67,0,233,23,1,0,
        0,0,234,237,3,128,64,0,235,237,3,22,11,0,236,234,1,0,0,0,236,235,
        1,0,0,0,237,25,1,0,0,0,238,239,3,24,12,0,239,240,5,64,0,0,240,241,
        3,28,14,0,241,27,1,0,0,0,242,248,3,140,70,0,243,248,3,50,25,0,244,
        248,3,110,55,0,245,248,3,90,45,0,246,248,3,142,71,0,247,242,1,0,
        0,0,247,243,1,0,0,0,247,244,1,0,0,0,247,245,1,0,0,0,247,246,1,0,
        0,0,248,29,1,0,0,0,249,250,3,128,64,0,250,251,5,86,0,0,251,252,3,
        130,65,0,252,31,1,0,0,0,253,254,3,36,18,0,254,257,7,1,0,0,255,258,
        3,36,18,0,256,258,3,32,16,0,257,255,1,0,0,0,257,256,1,0,0,0,258,
        33,1,0,0,0,259,260,3,38,19,0,260,261,5,26,0,0,261,262,3,38,19,0,
        262,35,1,0,0,0,263,264,3,40,20,0,264,37,1,0,0,0,265,266,3,40,20,
        0,266,39,1,0,0,0,267,271,3,128,64,0,268,271,3,42,21,0,269,271,3,
        44,22,0,270,267,1,0,0,0,270,268,1,0,0,0,270,269,1,0,0,0,271,41,1,
        0,0,0,272,273,5,10,0,0,273,274,3,136,68,0,274,43,1,0,0,0,275,276,
        3,48,24,0,276,45,1,0,0,0,277,278,3,48,24,0,278,47,1,0,0,0,279,283,
        5,9,0,0,280,284,3,136,68,0,281,284,3,144,72,0,282,284,3,140,70,0,
        283,280,1,0,0,0,283,281,1,0,0,0,283,282,1,0,0,0,284,49,1,0,0,0,285,
        286,5,11,0,0,286,291,3,130,65,0,287,288,5,65,0,0,288,289,3,52,26,
        0,289,290,5,66,0,0,290,292,1,0,0,0,291,287,1,0,0,0,291,292,1,0,0,
        0,292,294,1,0,0,0,293,295,3,70,35,0,294,293,1,0,0,0,294,295,1,0,
        0,0,295,51,1,0,0,0,296,297,3,144,72,0,297,53,1,0,0,0,298,299,3,140,
        70,0,299,55,1,0,0,0,300,301,5,22,0,0,301,57,1,0,0,0,302,314,5,65,
        0,0,303,308,3,128,64,0,304,305,5,59,0,0,305,307,3,128,64,0,306,304,
        1,0,0,0,307,310,1,0,0,0,308,306,1,0,0,0,308,309,1,0,0,0,309,312,
        1,0,0,0,310,308,1,0,0,0,311,313,5,59,0,0,312,311,1,0,0,0,312,313,
        1,0,0,0,313,315,1,0,0,0,314,303,1,0,0,0,314,315,1,0,0,0,315,316,
        1,0,0,0,316,317,5,66,0,0,317,59,1,0,0,0,318,320,3,128,64,0,319,321,
        3,98,49,0,320,319,1,0,0,0,320,321,1,0,0,0,321,324,1,0,0,0,322,324,
        3,58,29,0,323,318,1,0,0,0,323,322,1,0,0,0,324,61,1,0,0,0,325,326,
        5,14,0,0,326,327,3,136,68,0,327,328,5,15,0,0,328,329,3,60,30,0,329,
        330,5,61,0,0,330,331,3,18,9,0,331,63,1,0,0,0,332,333,5,16,0,0,333,
        334,3,74,37,0,334,65,1,0,0,0,335,337,5,23,0,0,336,338,3,128,64,0,
        337,336,1,0,0,0,337,338,1,0,0,0,338,339,1,0,0,0,339,342,3,130,65,
        0,340,341,5,60,0,0,341,343,3,68,34,0,342,340,1,0,0,0,342,343,1,0,
        0,0,343,345,1,0,0,0,344,346,3,70,35,0,345,344,1,0,0,0,345,346,1,
        0,0,0,346,67,1,0,0,0,347,348,3,136,68,0,348,69,1,0,0,0,349,361,5,
        78,0,0,350,355,3,72,36,0,351,352,5,59,0,0,352,354,3,72,36,0,353,
        351,1,0,0,0,354,357,1,0,0,0,355,353,1,0,0,0,355,356,1,0,0,0,356,
        359,1,0,0,0,357,355,1,0,0,0,358,360,5,59,0,0,359,358,1,0,0,0,359,
        360,1,0,0,0,360,362,1,0,0,0,361,350,1,0,0,0,361,362,1,0,0,0,362,
        363,1,0,0,0,363,364,5,79,0,0,364,71,1,0,0,0,365,366,3,136,68,0,366,
        367,5,64,0,0,367,368,3,138,69,0,368,73,1,0,0,0,369,371,3,90,45,0,
        370,372,3,76,38,0,371,370,1,0,0,0,372,373,1,0,0,0,373,371,1,0,0,
        0,373,374,1,0,0,0,374,75,1,0,0,0,375,382,3,78,39,0,376,382,3,80,
        40,0,377,382,3,82,41,0,378,382,3,84,42,0,379,382,3,86,43,0,380,382,
        3,88,44,0,381,375,1,0,0,0,381,376,1,0,0,0,381,377,1,0,0,0,381,378,
        1,0,0,0,381,379,1,0,0,0,381,380,1,0,0,0,382,77,1,0,0,0,383,384,5,
        78,0,0,384,385,3,90,45,0,385,79,1,0,0,0,386,387,5,79,0,0,387,388,
        3,90,45,0,388,81,1,0,0,0,389,390,5,82,0,0,390,391,3,90,45,0,391,
        83,1,0,0,0,392,393,5,81,0,0,393,394,3,90,45,0,394,85,1,0,0,0,395,
        396,5,20,0,0,396,397,3,90,45,0,397,87,1,0,0,0,398,399,5,21,0,0,399,
        400,3,90,45,0,400,89,1,0,0,0,401,402,6,45,-1,0,402,403,3,92,46,0,
        403,409,1,0,0,0,404,405,10,2,0,0,405,406,7,2,0,0,406,408,3,92,46,
        0,407,404,1,0,0,0,408,411,1,0,0,0,409,407,1,0,0,0,409,410,1,0,0,
        0,410,91,1,0,0,0,411,409,1,0,0,0,412,413,6,46,-1,0,413,414,3,94,
        47,0,414,420,1,0,0,0,415,416,10,2,0,0,416,417,7,3,0,0,417,419,3,
        94,47,0,418,415,1,0,0,0,419,422,1,0,0,0,420,418,1,0,0,0,420,421,
        1,0,0,0,421,93,1,0,0,0,422,420,1,0,0,0,423,424,6,47,-1,0,424,425,
        3,96,48,0,425,431,1,0,0,0,426,427,10,2,0,0,427,428,7,4,0,0,428,430,
        3,96,48,0,429,426,1,0,0,0,430,433,1,0,0,0,431,429,1,0,0,0,431,432,
        1,0,0,0,432,95,1,0,0,0,433,431,1,0,0,0,434,437,3,106,53,0,435,436,
        5,63,0,0,436,438,3,106,53,0,437,435,1,0,0,0,437,438,1,0,0,0,438,
        97,1,0,0,0,439,453,5,65,0,0,440,442,3,100,50,0,441,440,1,0,0,0,441,
        442,1,0,0,0,442,443,1,0,0,0,443,445,5,61,0,0,444,446,3,102,51,0,
        445,444,1,0,0,0,445,446,1,0,0,0,446,451,1,0,0,0,447,449,5,61,0,0,
        448,450,3,104,52,0,449,448,1,0,0,0,449,450,1,0,0,0,450,452,1,0,0,
        0,451,447,1,0,0,0,451,452,1,0,0,0,452,454,1,0,0,0,453,441,1,0,0,
        0,453,454,1,0,0,0,454,455,1,0,0,0,455,463,5,66,0,0,456,457,5,65,
        0,0,457,459,5,60,0,0,458,460,3,104,52,0,459,458,1,0,0,0,459,460,
        1,0,0,0,460,461,1,0,0,0,461,463,5,66,0,0,462,439,1,0,0,0,462,456,
        1,0,0,0,463,99,1,0,0,0,464,465,3,146,73,0,465,101,1,0,0,0,466,467,
        3,146,73,0,467,103,1,0,0,0,468,469,3,146,73,0,469,105,1,0,0,0,470,
        474,3,128,64,0,471,474,3,110,55,0,472,474,3,108,54,0,473,470,1,0,
        0,0,473,471,1,0,0,0,473,472,1,0,0,0,474,107,1,0,0,0,475,476,5,57,
        0,0,476,477,3,90,45,0,477,478,5,58,0,0,478,109,1,0,0,0,479,483,3,
        112,56,0,480,483,3,114,57,0,481,483,3,116,58,0,482,479,1,0,0,0,482,
        480,1,0,0,0,482,481,1,0,0,0,483,111,1,0,0,0,484,485,3,116,58,0,485,
        486,5,17,0,0,486,487,3,116,58,0,487,113,1,0,0,0,488,489,3,116,58,
        0,489,490,5,50,0,0,490,491,3,118,59,0,491,115,1,0,0,0,492,494,3,
        148,74,0,493,495,3,136,68,0,494,493,1,0,0,0,494,495,1,0,0,0,495,
        117,1,0,0,0,496,499,3,150,75,0,497,500,5,53,0,0,498,500,3,136,68,
        0,499,497,1,0,0,0,499,498,1,0,0,0,499,500,1,0,0,0,500,119,1,0,0,
        0,501,502,3,146,73,0,502,121,1,0,0,0,503,504,5,65,0,0,504,505,3,
        120,60,0,505,506,5,66,0,0,506,123,1,0,0,0,507,508,5,54,0,0,508,509,
        3,144,72,0,509,125,1,0,0,0,510,512,3,136,68,0,511,513,3,122,61,0,
        512,511,1,0,0,0,512,513,1,0,0,0,513,127,1,0,0,0,514,519,3,126,63,
        0,515,516,5,54,0,0,516,518,3,126,63,0,517,515,1,0,0,0,518,521,1,
        0,0,0,519,517,1,0,0,0,519,520,1,0,0,0,520,523,1,0,0,0,521,519,1,
        0,0,0,522,524,3,124,62,0,523,522,1,0,0,0,523,524,1,0,0,0,524,129,
        1,0,0,0,525,526,3,136,68,0,526,131,1,0,0,0,527,528,3,136,68,0,528,
        133,1,0,0,0,529,530,5,61,0,0,530,531,3,132,66,0,531,135,1,0,0,0,
        532,533,5,41,0,0,533,137,1,0,0,0,534,538,3,140,70,0,535,538,3,142,
        71,0,536,538,3,148,74,0,537,534,1,0,0,0,537,535,1,0,0,0,537,536,
        1,0,0,0,538,139,1,0,0,0,539,540,5,3,0,0,540,141,1,0,0,0,541,542,
        7,5,0,0,542,143,1,0,0,0,543,544,3,150,75,0,544,145,1,0,0,0,545,546,
        3,148,74,0,546,147,1,0,0,0,547,549,7,3,0,0,548,547,1,0,0,0,548,549,
        1,0,0,0,549,550,1,0,0,0,550,551,3,150,75,0,551,149,1,0,0,0,552,553,
        5,4,0,0,553,151,1,0,0,0,51,154,156,166,173,177,193,197,202,218,222,
        226,236,247,257,270,283,291,294,308,312,314,320,323,337,342,345,
        355,359,361,373,381,409,420,431,437,441,445,449,451,453,459,462,
        473,482,494,499,512,519,523,537,548
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
                     "'~>'", "'<~'", "'~'", "'int'", "'float'", "'string'", 
                     "'str'", "'bytes'", "'if'", "'parameter'", "'param'", 
                     "'test'", "'require'", "'requires'", "'check'", "'report'", 
                     "'ensure'", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "'+/-'", "'\\u00B1'", 
                     "'%'", "'.'", "'...'", "'*'", "'('", "')'", "','", 
                     "'::'", "':'", "';'", "'**'", "'='", "'['", "']'", 
                     "'|'", "'^'", "'&'", "'<<'", "'>>'", "'+'", "'-'", 
                     "'/'", "'//'", "'{'", "'}'", "'<'", "'>'", "'=='", 
                     "'>='", "'<='", "'<>'", "'!='", "'@'", "'->'" ]

    symbolicNames = [ "<INVALID>", "INDENT", "DEDENT", "STRING", "NUMBER", 
                      "INTEGER", "COMPONENT", "MODULE", "INTERFACE", "PIN", 
                      "SIGNAL", "NEW", "FROM", "IMPORT", "FOR", "IN", "ASSERT", 
                      "TO", "TRUE", "FALSE", "WITHIN", "IS", "PASS", "TRAIT", 
                      "SPERM", "LSPERM", "WIRE", "INT", "FLOAT", "STRING_", 
                      "STR", "BYTES", "IF", "PARAMETER", "PARAM", "TEST", 
                      "REQUIRE", "REQUIRES", "CHECK", "REPORT", "ENSURE", 
                      "NAME", "STRING_LITERAL", "BYTES_LITERAL", "DECIMAL_INTEGER", 
                      "OCT_INTEGER", "HEX_INTEGER", "BIN_INTEGER", "FLOAT_NUMBER", 
                      "IMAG_NUMBER", "PLUS_OR_MINUS", "PLUS_SLASH_MINUS", 
                      "PLUS_MINUS_SIGN", "PERCENT", "DOT", "ELLIPSIS", "STAR", 
                      "OPEN_PAREN", "CLOSE_PAREN", "COMMA", "DOUBLE_COLON", 
                      "COLON", "SEMI_COLON", "POWER", "ASSIGN", "OPEN_BRACK", 
                      "CLOSE_BRACK", "OR_OP", "XOR", "AND_OP", "LEFT_SHIFT", 
                      "RIGHT_SHIFT", "PLUS", "MINUS", "DIV", "IDIV", "OPEN_BRACE", 
                      "CLOSE_BRACE", "LESS_THAN", "GREATER_THAN", "EQUALS", 
                      "GT_EQ", "LT_EQ", "NOT_EQ_1", "NOT_EQ_2", "AT", "ARROW", 
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
    RULE_import_stmt = 10
    RULE_declaration_stmt = 11
    RULE_field_reference_or_declaration = 12
    RULE_assign_stmt = 13
    RULE_assignable = 14
    RULE_retype_stmt = 15
    RULE_directed_connect_stmt = 16
    RULE_connect_stmt = 17
    RULE_bridgeable = 18
    RULE_mif = 19
    RULE_connectable = 20
    RULE_signaldef_stmt = 21
    RULE_pindef_stmt = 22
    RULE_pin_declaration = 23
    RULE_pin_stmt = 24
    RULE_new_stmt = 25
    RULE_new_count = 26
    RULE_string_stmt = 27
    RULE_pass_stmt = 28
    RULE_list_literal_of_field_references = 29
    RULE_iterable_references = 30
    RULE_for_stmt = 31
    RULE_assert_stmt = 32
    RULE_trait_stmt = 33
    RULE_constructor = 34
    RULE_template = 35
    RULE_template_arg = 36
    RULE_comparison = 37
    RULE_compare_op_pair = 38
    RULE_lt_arithmetic_or = 39
    RULE_gt_arithmetic_or = 40
    RULE_lt_eq_arithmetic_or = 41
    RULE_gt_eq_arithmetic_or = 42
    RULE_in_arithmetic_or = 43
    RULE_is_arithmetic_or = 44
    RULE_arithmetic_expression = 45
    RULE_sum = 46
    RULE_term = 47
    RULE_power = 48
    RULE_slice = 49
    RULE_slice_start = 50
    RULE_slice_stop = 51
    RULE_slice_step = 52
    RULE_atom = 53
    RULE_arithmetic_group = 54
    RULE_literal_physical = 55
    RULE_bound_quantity = 56
    RULE_bilateral_quantity = 57
    RULE_quantity = 58
    RULE_bilateral_tolerance = 59
    RULE_key = 60
    RULE_array_index = 61
    RULE_pin_reference_end = 62
    RULE_field_reference_part = 63
    RULE_field_reference = 64
    RULE_type_reference = 65
    RULE_unit = 66
    RULE_type_info = 67
    RULE_name = 68
    RULE_literal = 69
    RULE_string = 70
    RULE_boolean_ = 71
    RULE_number_hint_natural = 72
    RULE_number_hint_integer = 73
    RULE_number = 74
    RULE_number_signless = 75

    ruleNames =  [ "file_input", "pragma_stmt", "stmt", "simple_stmts", 
                   "simple_stmt", "compound_stmt", "blockdef", "blockdef_super", 
                   "blocktype", "block", "import_stmt", "declaration_stmt", 
                   "field_reference_or_declaration", "assign_stmt", "assignable", 
                   "retype_stmt", "directed_connect_stmt", "connect_stmt", 
                   "bridgeable", "mif", "connectable", "signaldef_stmt", 
                   "pindef_stmt", "pin_declaration", "pin_stmt", "new_stmt", 
                   "new_count", "string_stmt", "pass_stmt", "list_literal_of_field_references", 
                   "iterable_references", "for_stmt", "assert_stmt", "trait_stmt", 
                   "constructor", "template", "template_arg", "comparison", 
                   "compare_op_pair", "lt_arithmetic_or", "gt_arithmetic_or", 
                   "lt_eq_arithmetic_or", "gt_eq_arithmetic_or", "in_arithmetic_or", 
                   "is_arithmetic_or", "arithmetic_expression", "sum", "term", 
                   "power", "slice", "slice_start", "slice_stop", "slice_step", 
                   "atom", "arithmetic_group", "literal_physical", "bound_quantity", 
                   "bilateral_quantity", "quantity", "bilateral_tolerance", 
                   "key", "array_index", "pin_reference_end", "field_reference_part", 
                   "field_reference", "type_reference", "unit", "type_info", 
                   "name", "literal", "string", "boolean_", "number_hint_natural", 
                   "number_hint_integer", "number", "number_signless" ]

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
    LSPERM=25
    WIRE=26
    INT=27
    FLOAT=28
    STRING_=29
    STR=30
    BYTES=31
    IF=32
    PARAMETER=33
    PARAM=34
    TEST=35
    REQUIRE=36
    REQUIRES=37
    CHECK=38
    REPORT=39
    ENSURE=40
    NAME=41
    STRING_LITERAL=42
    BYTES_LITERAL=43
    DECIMAL_INTEGER=44
    OCT_INTEGER=45
    HEX_INTEGER=46
    BIN_INTEGER=47
    FLOAT_NUMBER=48
    IMAG_NUMBER=49
    PLUS_OR_MINUS=50
    PLUS_SLASH_MINUS=51
    PLUS_MINUS_SIGN=52
    PERCENT=53
    DOT=54
    ELLIPSIS=55
    STAR=56
    OPEN_PAREN=57
    CLOSE_PAREN=58
    COMMA=59
    DOUBLE_COLON=60
    COLON=61
    SEMI_COLON=62
    POWER=63
    ASSIGN=64
    OPEN_BRACK=65
    CLOSE_BRACK=66
    OR_OP=67
    XOR=68
    AND_OP=69
    LEFT_SHIFT=70
    RIGHT_SHIFT=71
    PLUS=72
    MINUS=73
    DIV=74
    IDIV=75
    OPEN_BRACE=76
    CLOSE_BRACE=77
    LESS_THAN=78
    GREATER_THAN=79
    EQUALS=80
    GT_EQ=81
    LT_EQ=82
    NOT_EQ_1=83
    NOT_EQ_2=84
    AT=85
    ARROW=86
    NEWLINE=87
    PRAGMA=88
    COMMENT=89
    WS=90
    EXPLICIT_LINE_JOINING=91
    ERRORTOKEN=92

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
            self.state = 156
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 2199035934664) != 0) or _la==87 or _la==88:
                self.state = 154
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [87]:
                    self.state = 152
                    self.match(AtoParser.NEWLINE)
                    pass
                elif token in [3, 6, 7, 8, 9, 10, 12, 13, 14, 16, 22, 23, 41, 88]:
                    self.state = 153
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 158
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 159
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
            self.state = 161
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
            self.state = 166
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 16, 22, 23, 41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 163
                self.simple_stmts()
                pass
            elif token in [6, 7, 8, 14]:
                self.enterOuterAlt(localctx, 2)
                self.state = 164
                self.compound_stmt()
                pass
            elif token in [88]:
                self.enterOuterAlt(localctx, 3)
                self.state = 165
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
            self.state = 168
            self.simple_stmt()
            self.state = 173
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 169
                    self.match(AtoParser.SEMI_COLON)
                    self.state = 170
                    self.simple_stmt() 
                self.state = 175
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 177
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==62:
                self.state = 176
                self.match(AtoParser.SEMI_COLON)


            self.state = 179
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


        def assign_stmt(self):
            return self.getTypedRuleContext(AtoParser.Assign_stmtContext,0)


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
            self.state = 193
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 181
                self.import_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 182
                self.assign_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 183
                self.connect_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 184
                self.directed_connect_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 185
                self.retype_stmt()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 186
                self.pin_declaration()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 187
                self.signaldef_stmt()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 188
                self.assert_stmt()
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 189
                self.declaration_stmt()
                pass

            elif la_ == 10:
                self.enterOuterAlt(localctx, 10)
                self.state = 190
                self.string_stmt()
                pass

            elif la_ == 11:
                self.enterOuterAlt(localctx, 11)
                self.state = 191
                self.pass_stmt()
                pass

            elif la_ == 12:
                self.enterOuterAlt(localctx, 12)
                self.state = 192
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
            self.state = 197
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [6, 7, 8]:
                self.enterOuterAlt(localctx, 1)
                self.state = 195
                self.blockdef()
                pass
            elif token in [14]:
                self.enterOuterAlt(localctx, 2)
                self.state = 196
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


        def type_reference(self):
            return self.getTypedRuleContext(AtoParser.Type_referenceContext,0)


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
            self.state = 199
            self.blocktype()
            self.state = 200
            self.type_reference()
            self.state = 202
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 201
                self.blockdef_super()


            self.state = 204
            self.match(AtoParser.COLON)
            self.state = 205
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
            self.state = 207
            self.match(AtoParser.FROM)
            self.state = 208
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
            self.state = 210
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
            self.state = 222
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 16, 22, 23, 41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 212
                self.simple_stmts()
                pass
            elif token in [87]:
                self.enterOuterAlt(localctx, 2)
                self.state = 213
                self.match(AtoParser.NEWLINE)
                self.state = 214
                self.match(AtoParser.INDENT)
                self.state = 216 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 215
                    self.stmt()
                    self.state = 218 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 2199035934664) != 0) or _la==88):
                        break

                self.state = 220
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


    class Import_stmtContext(ParserRuleContext):
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
            self.state = 226
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 224
                self.match(AtoParser.FROM)
                self.state = 225
                self.string()


            self.state = 228
            self.match(AtoParser.IMPORT)
            self.state = 229
            self.type_reference()
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
            self.state = 231
            self.field_reference()
            self.state = 232
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
            self.state = 236
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,11,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 234
                self.field_reference()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 235
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
            self.state = 238
            self.field_reference_or_declaration()
            self.state = 239
            self.match(AtoParser.ASSIGN)
            self.state = 240
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
        self.enterRule(localctx, 28, self.RULE_assignable)
        try:
            self.state = 247
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
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
        self.enterRule(localctx, 30, self.RULE_retype_stmt)
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

        def bridgeable(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtoParser.BridgeableContext)
            else:
                return self.getTypedRuleContext(AtoParser.BridgeableContext,i)


        def SPERM(self):
            return self.getToken(AtoParser.SPERM, 0)

        def LSPERM(self):
            return self.getToken(AtoParser.LSPERM, 0)

        def directed_connect_stmt(self):
            return self.getTypedRuleContext(AtoParser.Directed_connect_stmtContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_directed_connect_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDirected_connect_stmt" ):
                return visitor.visitDirected_connect_stmt(self)
            else:
                return visitor.visitChildren(self)




    def directed_connect_stmt(self):

        localctx = AtoParser.Directed_connect_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_directed_connect_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 253
            self.bridgeable()
            self.state = 254
            _la = self._input.LA(1)
            if not(_la==24 or _la==25):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 257
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
            if la_ == 1:
                self.state = 255
                self.bridgeable()
                pass

            elif la_ == 2:
                self.state = 256
                self.directed_connect_stmt()
                pass


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

        def mif(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtoParser.MifContext)
            else:
                return self.getTypedRuleContext(AtoParser.MifContext,i)


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
        self.enterRule(localctx, 34, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 259
            self.mif()
            self.state = 260
            self.match(AtoParser.WIRE)
            self.state = 261
            self.mif()
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

        def connectable(self):
            return self.getTypedRuleContext(AtoParser.ConnectableContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_bridgeable

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBridgeable" ):
                return visitor.visitBridgeable(self)
            else:
                return visitor.visitChildren(self)




    def bridgeable(self):

        localctx = AtoParser.BridgeableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_bridgeable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 263
            self.connectable()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MifContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def connectable(self):
            return self.getTypedRuleContext(AtoParser.ConnectableContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_mif

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMif" ):
                return visitor.visitMif(self)
            else:
                return visitor.visitChildren(self)




    def mif(self):

        localctx = AtoParser.MifContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_mif)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 265
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
        self.enterRule(localctx, 40, self.RULE_connectable)
        try:
            self.state = 270
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 267
                self.field_reference()
                pass
            elif token in [10]:
                self.enterOuterAlt(localctx, 2)
                self.state = 268
                self.signaldef_stmt()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 3)
                self.state = 269
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
        self.enterRule(localctx, 42, self.RULE_signaldef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 272
            self.match(AtoParser.SIGNAL)
            self.state = 273
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
        self.enterRule(localctx, 44, self.RULE_pindef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 275
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
        self.enterRule(localctx, 46, self.RULE_pin_declaration)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 277
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
        self.enterRule(localctx, 48, self.RULE_pin_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 279
            self.match(AtoParser.PIN)
            self.state = 283
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41]:
                self.state = 280
                self.name()
                pass
            elif token in [4]:
                self.state = 281
                self.number_hint_natural()
                pass
            elif token in [3]:
                self.state = 282
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

        def template(self):
            return self.getTypedRuleContext(AtoParser.TemplateContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_new_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNew_stmt" ):
                return visitor.visitNew_stmt(self)
            else:
                return visitor.visitChildren(self)




    def new_stmt(self):

        localctx = AtoParser.New_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_new_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 285
            self.match(AtoParser.NEW)
            self.state = 286
            self.type_reference()
            self.state = 291
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==65:
                self.state = 287
                self.match(AtoParser.OPEN_BRACK)
                self.state = 288
                self.new_count()
                self.state = 289
                self.match(AtoParser.CLOSE_BRACK)


            self.state = 294
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==78:
                self.state = 293
                self.template()


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
        self.enterRule(localctx, 52, self.RULE_new_count)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 296
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
        self.enterRule(localctx, 54, self.RULE_string_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 298
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
        self.enterRule(localctx, 56, self.RULE_pass_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 300
            self.match(AtoParser.PASS)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class List_literal_of_field_referencesContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def OPEN_BRACK(self):
            return self.getToken(AtoParser.OPEN_BRACK, 0)

        def CLOSE_BRACK(self):
            return self.getToken(AtoParser.CLOSE_BRACK, 0)

        def field_reference(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtoParser.Field_referenceContext)
            else:
                return self.getTypedRuleContext(AtoParser.Field_referenceContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(AtoParser.COMMA)
            else:
                return self.getToken(AtoParser.COMMA, i)

        def getRuleIndex(self):
            return AtoParser.RULE_list_literal_of_field_references

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitList_literal_of_field_references" ):
                return visitor.visitList_literal_of_field_references(self)
            else:
                return visitor.visitChildren(self)




    def list_literal_of_field_references(self):

        localctx = AtoParser.List_literal_of_field_referencesContext(self, self._ctx, self.state)
        self.enterRule(localctx, 58, self.RULE_list_literal_of_field_references)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 302
            self.match(AtoParser.OPEN_BRACK)
            self.state = 314
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==41:
                self.state = 303
                self.field_reference()
                self.state = 308
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,18,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 304
                        self.match(AtoParser.COMMA)
                        self.state = 305
                        self.field_reference() 
                    self.state = 310
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,18,self._ctx)

                self.state = 312
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==59:
                    self.state = 311
                    self.match(AtoParser.COMMA)




            self.state = 316
            self.match(AtoParser.CLOSE_BRACK)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Iterable_referencesContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def field_reference(self):
            return self.getTypedRuleContext(AtoParser.Field_referenceContext,0)


        def slice_(self):
            return self.getTypedRuleContext(AtoParser.SliceContext,0)


        def list_literal_of_field_references(self):
            return self.getTypedRuleContext(AtoParser.List_literal_of_field_referencesContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_iterable_references

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIterable_references" ):
                return visitor.visitIterable_references(self)
            else:
                return visitor.visitChildren(self)




    def iterable_references(self):

        localctx = AtoParser.Iterable_referencesContext(self, self._ctx, self.state)
        self.enterRule(localctx, 60, self.RULE_iterable_references)
        self._la = 0 # Token type
        try:
            self.state = 323
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 318
                self.field_reference()
                self.state = 320
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==65:
                    self.state = 319
                    self.slice_()


                pass
            elif token in [65]:
                self.enterOuterAlt(localctx, 2)
                self.state = 322
                self.list_literal_of_field_references()
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

        def iterable_references(self):
            return self.getTypedRuleContext(AtoParser.Iterable_referencesContext,0)


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
            self.state = 325
            self.match(AtoParser.FOR)
            self.state = 326
            self.name()
            self.state = 327
            self.match(AtoParser.IN)
            self.state = 328
            self.iterable_references()
            self.state = 329
            self.match(AtoParser.COLON)
            self.state = 330
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
            self.state = 332
            self.match(AtoParser.ASSERT)
            self.state = 333
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


        def field_reference(self):
            return self.getTypedRuleContext(AtoParser.Field_referenceContext,0)


        def DOUBLE_COLON(self):
            return self.getToken(AtoParser.DOUBLE_COLON, 0)

        def constructor(self):
            return self.getTypedRuleContext(AtoParser.ConstructorContext,0)


        def template(self):
            return self.getTypedRuleContext(AtoParser.TemplateContext,0)


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
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 335
            self.match(AtoParser.TRAIT)
            self.state = 337
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,23,self._ctx)
            if la_ == 1:
                self.state = 336
                self.field_reference()


            self.state = 339
            self.type_reference()
            self.state = 342
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==60:
                self.state = 340
                self.match(AtoParser.DOUBLE_COLON)
                self.state = 341
                self.constructor()


            self.state = 345
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==78:
                self.state = 344
                self.template()


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
        self.enterRule(localctx, 68, self.RULE_constructor)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 347
            self.name()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TemplateContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LESS_THAN(self):
            return self.getToken(AtoParser.LESS_THAN, 0)

        def GREATER_THAN(self):
            return self.getToken(AtoParser.GREATER_THAN, 0)

        def template_arg(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtoParser.Template_argContext)
            else:
                return self.getTypedRuleContext(AtoParser.Template_argContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(AtoParser.COMMA)
            else:
                return self.getToken(AtoParser.COMMA, i)

        def getRuleIndex(self):
            return AtoParser.RULE_template

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTemplate" ):
                return visitor.visitTemplate(self)
            else:
                return visitor.visitChildren(self)




    def template(self):

        localctx = AtoParser.TemplateContext(self, self._ctx, self.state)
        self.enterRule(localctx, 70, self.RULE_template)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 349
            self.match(AtoParser.LESS_THAN)
            self.state = 361
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==41:
                self.state = 350
                self.template_arg()
                self.state = 355
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,26,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 351
                        self.match(AtoParser.COMMA)
                        self.state = 352
                        self.template_arg() 
                    self.state = 357
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,26,self._ctx)

                self.state = 359
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==59:
                    self.state = 358
                    self.match(AtoParser.COMMA)




            self.state = 363
            self.match(AtoParser.GREATER_THAN)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Template_argContext(ParserRuleContext):
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
            return AtoParser.RULE_template_arg

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTemplate_arg" ):
                return visitor.visitTemplate_arg(self)
            else:
                return visitor.visitChildren(self)




    def template_arg(self):

        localctx = AtoParser.Template_argContext(self, self._ctx, self.state)
        self.enterRule(localctx, 72, self.RULE_template_arg)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 365
            self.name()
            self.state = 366
            self.match(AtoParser.ASSIGN)
            self.state = 367
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
        self.enterRule(localctx, 74, self.RULE_comparison)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 369
            self.arithmetic_expression(0)
            self.state = 371 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 370
                self.compare_op_pair()
                self.state = 373 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (((((_la - 20)) & ~0x3f) == 0 and ((1 << (_la - 20)) & 7782220156096217091) != 0)):
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
        self.enterRule(localctx, 76, self.RULE_compare_op_pair)
        try:
            self.state = 381
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [78]:
                self.enterOuterAlt(localctx, 1)
                self.state = 375
                self.lt_arithmetic_or()
                pass
            elif token in [79]:
                self.enterOuterAlt(localctx, 2)
                self.state = 376
                self.gt_arithmetic_or()
                pass
            elif token in [82]:
                self.enterOuterAlt(localctx, 3)
                self.state = 377
                self.lt_eq_arithmetic_or()
                pass
            elif token in [81]:
                self.enterOuterAlt(localctx, 4)
                self.state = 378
                self.gt_eq_arithmetic_or()
                pass
            elif token in [20]:
                self.enterOuterAlt(localctx, 5)
                self.state = 379
                self.in_arithmetic_or()
                pass
            elif token in [21]:
                self.enterOuterAlt(localctx, 6)
                self.state = 380
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
        self.enterRule(localctx, 78, self.RULE_lt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 383
            self.match(AtoParser.LESS_THAN)
            self.state = 384
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
        self.enterRule(localctx, 80, self.RULE_gt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 386
            self.match(AtoParser.GREATER_THAN)
            self.state = 387
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
        self.enterRule(localctx, 82, self.RULE_lt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 389
            self.match(AtoParser.LT_EQ)
            self.state = 390
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
        self.enterRule(localctx, 84, self.RULE_gt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 392
            self.match(AtoParser.GT_EQ)
            self.state = 393
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
        self.enterRule(localctx, 86, self.RULE_in_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 395
            self.match(AtoParser.WITHIN)
            self.state = 396
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
        self.enterRule(localctx, 88, self.RULE_is_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 398
            self.match(AtoParser.IS)
            self.state = 399
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
        _startState = 90
        self.enterRecursionRule(localctx, 90, self.RULE_arithmetic_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 402
            self.sum_(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 409
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,31,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.Arithmetic_expressionContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmetic_expression)
                    self.state = 404
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 405
                    _la = self._input.LA(1)
                    if not(_la==67 or _la==69):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 406
                    self.sum_(0) 
                self.state = 411
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,31,self._ctx)

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
        _startState = 92
        self.enterRecursionRule(localctx, 92, self.RULE_sum, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 413
            self.term(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 420
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,32,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.SumContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_sum)
                    self.state = 415
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 416
                    _la = self._input.LA(1)
                    if not(_la==72 or _la==73):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 417
                    self.term(0) 
                self.state = 422
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,32,self._ctx)

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
        _startState = 94
        self.enterRecursionRule(localctx, 94, self.RULE_term, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 424
            self.power()
            self._ctx.stop = self._input.LT(-1)
            self.state = 431
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,33,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.TermContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_term)
                    self.state = 426
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 427
                    _la = self._input.LA(1)
                    if not(_la==56 or _la==74):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 428
                    self.power() 
                self.state = 433
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,33,self._ctx)

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

        def atom(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtoParser.AtomContext)
            else:
                return self.getTypedRuleContext(AtoParser.AtomContext,i)


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
        self.enterRule(localctx, 96, self.RULE_power)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 434
            self.atom()
            self.state = 437
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,34,self._ctx)
            if la_ == 1:
                self.state = 435
                self.match(AtoParser.POWER)
                self.state = 436
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

        def slice_start(self):
            return self.getTypedRuleContext(AtoParser.Slice_startContext,0)


        def slice_stop(self):
            return self.getTypedRuleContext(AtoParser.Slice_stopContext,0)


        def slice_step(self):
            return self.getTypedRuleContext(AtoParser.Slice_stepContext,0)


        def DOUBLE_COLON(self):
            return self.getToken(AtoParser.DOUBLE_COLON, 0)

        def getRuleIndex(self):
            return AtoParser.RULE_slice

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSlice" ):
                return visitor.visitSlice(self)
            else:
                return visitor.visitChildren(self)




    def slice_(self):

        localctx = AtoParser.SliceContext(self, self._ctx, self.state)
        self.enterRule(localctx, 98, self.RULE_slice)
        self._la = 0 # Token type
        try:
            self.state = 462
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,41,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 439
                self.match(AtoParser.OPEN_BRACK)
                self.state = 453
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4 or _la==61 or _la==72 or _la==73:
                    self.state = 441
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if _la==4 or _la==72 or _la==73:
                        self.state = 440
                        self.slice_start()


                    self.state = 443
                    self.match(AtoParser.COLON)
                    self.state = 445
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if _la==4 or _la==72 or _la==73:
                        self.state = 444
                        self.slice_stop()


                    self.state = 451
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if _la==61:
                        self.state = 447
                        self.match(AtoParser.COLON)
                        self.state = 449
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if _la==4 or _la==72 or _la==73:
                            self.state = 448
                            self.slice_step()






                self.state = 455
                self.match(AtoParser.CLOSE_BRACK)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 456
                self.match(AtoParser.OPEN_BRACK)

                self.state = 457
                self.match(AtoParser.DOUBLE_COLON)
                self.state = 459
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4 or _la==72 or _la==73:
                    self.state = 458
                    self.slice_step()


                self.state = 461
                self.match(AtoParser.CLOSE_BRACK)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Slice_startContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def number_hint_integer(self):
            return self.getTypedRuleContext(AtoParser.Number_hint_integerContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_slice_start

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSlice_start" ):
                return visitor.visitSlice_start(self)
            else:
                return visitor.visitChildren(self)




    def slice_start(self):

        localctx = AtoParser.Slice_startContext(self, self._ctx, self.state)
        self.enterRule(localctx, 100, self.RULE_slice_start)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 464
            self.number_hint_integer()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Slice_stopContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def number_hint_integer(self):
            return self.getTypedRuleContext(AtoParser.Number_hint_integerContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_slice_stop

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSlice_stop" ):
                return visitor.visitSlice_stop(self)
            else:
                return visitor.visitChildren(self)




    def slice_stop(self):

        localctx = AtoParser.Slice_stopContext(self, self._ctx, self.state)
        self.enterRule(localctx, 102, self.RULE_slice_stop)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 466
            self.number_hint_integer()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Slice_stepContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def number_hint_integer(self):
            return self.getTypedRuleContext(AtoParser.Number_hint_integerContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_slice_step

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSlice_step" ):
                return visitor.visitSlice_step(self)
            else:
                return visitor.visitChildren(self)




    def slice_step(self):

        localctx = AtoParser.Slice_stepContext(self, self._ctx, self.state)
        self.enterRule(localctx, 104, self.RULE_slice_step)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 468
            self.number_hint_integer()
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
        self.enterRule(localctx, 106, self.RULE_atom)
        try:
            self.state = 473
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 470
                self.field_reference()
                pass
            elif token in [4, 72, 73]:
                self.enterOuterAlt(localctx, 2)
                self.state = 471
                self.literal_physical()
                pass
            elif token in [57]:
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
        self.enterRule(localctx, 108, self.RULE_arithmetic_group)
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
        self.enterRule(localctx, 110, self.RULE_literal_physical)
        try:
            self.state = 482
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,43,self._ctx)
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
        self.enterRule(localctx, 112, self.RULE_bound_quantity)
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
        self.enterRule(localctx, 114, self.RULE_bilateral_quantity)
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
        self.enterRule(localctx, 116, self.RULE_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 492
            self.number()
            self.state = 494
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,44,self._ctx)
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
        self.enterRule(localctx, 118, self.RULE_bilateral_tolerance)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 496
            self.number_signless()
            self.state = 499
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,45,self._ctx)
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
        self.enterRule(localctx, 120, self.RULE_key)
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
        self.enterRule(localctx, 122, self.RULE_array_index)
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
        self.enterRule(localctx, 124, self.RULE_pin_reference_end)
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
        self.enterRule(localctx, 126, self.RULE_field_reference_part)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 510
            self.name()
            self.state = 512
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,46,self._ctx)
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
        self.enterRule(localctx, 128, self.RULE_field_reference)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 514
            self.field_reference_part()
            self.state = 519
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,47,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 515
                    self.match(AtoParser.DOT)
                    self.state = 516
                    self.field_reference_part() 
                self.state = 521
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,47,self._ctx)

            self.state = 523
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,48,self._ctx)
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

        def name(self):
            return self.getTypedRuleContext(AtoParser.NameContext,0)


        def getRuleIndex(self):
            return AtoParser.RULE_type_reference

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitType_reference" ):
                return visitor.visitType_reference(self)
            else:
                return visitor.visitChildren(self)




    def type_reference(self):

        localctx = AtoParser.Type_referenceContext(self, self._ctx, self.state)
        self.enterRule(localctx, 130, self.RULE_type_reference)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 525
            self.name()
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
        self.enterRule(localctx, 132, self.RULE_unit)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 527
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
        self.enterRule(localctx, 134, self.RULE_type_info)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 529
            self.match(AtoParser.COLON)
            self.state = 530
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
        self.enterRule(localctx, 136, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 532
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
        self.enterRule(localctx, 138, self.RULE_literal)
        try:
            self.state = 537
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3]:
                self.enterOuterAlt(localctx, 1)
                self.state = 534
                self.string()
                pass
            elif token in [18, 19]:
                self.enterOuterAlt(localctx, 2)
                self.state = 535
                self.boolean_()
                pass
            elif token in [4, 72, 73]:
                self.enterOuterAlt(localctx, 3)
                self.state = 536
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
        self.enterRule(localctx, 140, self.RULE_string)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 539
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
        self.enterRule(localctx, 142, self.RULE_boolean_)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 541
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
        self.enterRule(localctx, 144, self.RULE_number_hint_natural)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 543
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
        self.enterRule(localctx, 146, self.RULE_number_hint_integer)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 545
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
        self.enterRule(localctx, 148, self.RULE_number)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 548
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==72 or _la==73:
                self.state = 547
                _la = self._input.LA(1)
                if not(_la==72 or _la==73):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()


            self.state = 550
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
        self.enterRule(localctx, 150, self.RULE_number_signless)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 552
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
        self._predicates[45] = self.arithmetic_expression_sempred
        self._predicates[46] = self.sum_sempred
        self._predicates[47] = self.term_sempred
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
         




