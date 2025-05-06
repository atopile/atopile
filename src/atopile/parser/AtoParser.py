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
        4,1,104,615,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,
        7,6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,
        13,2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,
        20,7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,
        26,2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,
        33,7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,2,39,7,
        39,2,40,7,40,2,41,7,41,2,42,7,42,2,43,7,43,2,44,7,44,2,45,7,45,2,
        46,7,46,2,47,7,47,2,48,7,48,2,49,7,49,2,50,7,50,2,51,7,51,2,52,7,
        52,2,53,7,53,2,54,7,54,2,55,7,55,2,56,7,56,2,57,7,57,2,58,7,58,2,
        59,7,59,2,60,7,60,2,61,7,61,2,62,7,62,2,63,7,63,2,64,7,64,2,65,7,
        65,2,66,7,66,2,67,7,67,2,68,7,68,2,69,7,69,2,70,7,70,2,71,7,71,2,
        72,7,72,2,73,7,73,2,74,7,74,2,75,7,75,2,76,7,76,2,77,7,77,2,78,7,
        78,2,79,7,79,2,80,7,80,2,81,7,81,2,82,7,82,1,0,1,0,5,0,169,8,0,10,
        0,12,0,172,9,0,1,0,1,0,1,1,1,1,1,2,1,2,1,2,3,2,181,8,2,1,3,1,3,1,
        3,5,3,186,8,3,10,3,12,3,189,9,3,1,3,3,3,192,8,3,1,3,1,3,1,4,1,4,
        1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,3,4,211,8,4,
        1,5,1,5,3,5,215,8,5,1,6,1,6,1,6,3,6,220,8,6,1,6,1,6,1,6,1,7,1,7,
        1,7,1,8,1,8,1,9,1,9,1,9,1,9,4,9,234,8,9,11,9,12,9,235,1,9,1,9,3,
        9,240,8,9,1,10,1,10,1,10,1,10,1,10,1,11,1,11,3,11,249,8,11,1,11,
        1,11,1,11,1,11,5,11,255,8,11,10,11,12,11,258,9,11,1,12,1,12,1,12,
        1,13,1,13,3,13,265,8,13,1,14,1,14,1,14,1,14,1,15,1,15,1,15,1,15,
        1,16,1,16,1,16,1,16,1,17,1,17,1,18,1,18,3,18,283,8,18,1,19,1,19,
        1,19,1,19,1,19,3,19,290,8,19,1,20,1,20,1,20,1,20,1,21,1,21,1,21,
        4,21,299,8,21,11,21,12,21,300,1,22,1,22,1,22,1,22,1,23,1,23,1,24,
        1,24,1,25,1,25,1,25,3,25,314,8,25,1,26,1,26,1,26,1,27,1,27,1,28,
        1,28,1,29,1,29,1,29,1,29,3,29,327,8,29,1,30,1,30,1,30,1,30,1,30,
        1,30,3,30,335,8,30,1,30,3,30,338,8,30,1,31,1,31,1,32,1,32,1,33,1,
        33,1,34,1,34,1,34,1,34,5,34,350,8,34,10,34,12,34,353,9,34,1,34,3,
        34,356,8,34,3,34,358,8,34,1,34,1,34,1,35,1,35,3,35,364,8,35,1,35,
        3,35,367,8,35,1,36,1,36,1,36,1,36,1,36,1,36,1,36,1,37,1,37,1,37,
        1,38,1,38,1,38,1,38,3,38,383,8,38,1,38,3,38,386,8,38,1,39,1,39,1,
        40,1,40,1,40,1,40,5,40,394,8,40,10,40,12,40,397,9,40,1,40,3,40,400,
        8,40,3,40,402,8,40,1,40,1,40,1,41,1,41,1,41,1,41,1,42,1,42,4,42,
        412,8,42,11,42,12,42,413,1,43,1,43,1,43,1,43,1,43,1,43,3,43,422,
        8,43,1,44,1,44,1,44,1,45,1,45,1,45,1,46,1,46,1,46,1,47,1,47,1,47,
        1,48,1,48,1,48,1,49,1,49,1,49,1,50,1,50,1,50,1,50,1,50,1,50,5,50,
        448,8,50,10,50,12,50,451,9,50,1,51,1,51,1,51,1,51,1,51,1,51,5,51,
        459,8,51,10,51,12,51,462,9,51,1,52,1,52,1,52,1,52,1,52,1,52,5,52,
        470,8,52,10,52,12,52,473,9,52,1,53,1,53,1,53,3,53,478,8,53,1,54,
        1,54,1,54,1,54,4,54,484,8,54,11,54,12,54,485,1,54,1,54,3,54,490,
        8,54,1,55,1,55,1,56,1,56,3,56,496,8,56,1,56,1,56,3,56,500,8,56,1,
        56,1,56,3,56,504,8,56,3,56,506,8,56,3,56,508,8,56,1,56,1,56,1,56,
        1,56,3,56,514,8,56,1,56,3,56,517,8,56,1,57,1,57,1,58,1,58,1,59,1,
        59,1,60,1,60,1,60,3,60,528,8,60,1,61,1,61,1,61,1,61,1,62,1,62,1,
        62,3,62,537,8,62,1,63,1,63,1,63,1,63,1,64,1,64,1,64,1,64,1,65,1,
        65,3,65,549,8,65,1,66,1,66,1,66,3,66,554,8,66,1,67,1,67,1,68,1,68,
        1,68,1,68,1,69,1,69,1,69,1,70,1,70,3,70,567,8,70,1,71,1,71,1,71,
        5,71,572,8,71,10,71,12,71,575,9,71,1,71,3,71,578,8,71,1,72,1,72,
        1,72,5,72,583,8,72,10,72,12,72,586,9,72,1,73,1,73,1,74,1,74,1,74,
        1,75,1,75,1,76,1,76,1,76,3,76,598,8,76,1,77,1,77,1,78,1,78,1,79,
        1,79,1,80,1,80,1,81,3,81,609,8,81,1,81,1,81,1,82,1,82,1,82,0,3,100,
        102,104,83,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,
        40,42,44,46,48,50,52,54,56,58,60,62,64,66,68,70,72,74,76,78,80,82,
        84,86,88,90,92,94,96,98,100,102,104,106,108,110,112,114,116,118,
        120,122,124,126,128,130,132,134,136,138,140,142,144,146,148,150,
        152,154,156,158,160,162,164,0,8,1,0,6,8,1,0,92,93,1,0,87,88,1,0,
        24,25,2,0,67,67,69,69,1,0,72,73,2,0,56,56,74,74,1,0,18,19,613,0,
        170,1,0,0,0,2,175,1,0,0,0,4,180,1,0,0,0,6,182,1,0,0,0,8,210,1,0,
        0,0,10,214,1,0,0,0,12,216,1,0,0,0,14,224,1,0,0,0,16,227,1,0,0,0,
        18,239,1,0,0,0,20,241,1,0,0,0,22,248,1,0,0,0,24,259,1,0,0,0,26,264,
        1,0,0,0,28,266,1,0,0,0,30,270,1,0,0,0,32,274,1,0,0,0,34,278,1,0,
        0,0,36,282,1,0,0,0,38,289,1,0,0,0,40,291,1,0,0,0,42,295,1,0,0,0,
        44,302,1,0,0,0,46,306,1,0,0,0,48,308,1,0,0,0,50,313,1,0,0,0,52,315,
        1,0,0,0,54,318,1,0,0,0,56,320,1,0,0,0,58,322,1,0,0,0,60,328,1,0,
        0,0,62,339,1,0,0,0,64,341,1,0,0,0,66,343,1,0,0,0,68,345,1,0,0,0,
        70,366,1,0,0,0,72,368,1,0,0,0,74,375,1,0,0,0,76,378,1,0,0,0,78,387,
        1,0,0,0,80,389,1,0,0,0,82,405,1,0,0,0,84,409,1,0,0,0,86,421,1,0,
        0,0,88,423,1,0,0,0,90,426,1,0,0,0,92,429,1,0,0,0,94,432,1,0,0,0,
        96,435,1,0,0,0,98,438,1,0,0,0,100,441,1,0,0,0,102,452,1,0,0,0,104,
        463,1,0,0,0,106,474,1,0,0,0,108,489,1,0,0,0,110,491,1,0,0,0,112,
        516,1,0,0,0,114,518,1,0,0,0,116,520,1,0,0,0,118,522,1,0,0,0,120,
        527,1,0,0,0,122,529,1,0,0,0,124,536,1,0,0,0,126,538,1,0,0,0,128,
        542,1,0,0,0,130,546,1,0,0,0,132,550,1,0,0,0,134,555,1,0,0,0,136,
        557,1,0,0,0,138,561,1,0,0,0,140,564,1,0,0,0,142,568,1,0,0,0,144,
        579,1,0,0,0,146,587,1,0,0,0,148,589,1,0,0,0,150,592,1,0,0,0,152,
        597,1,0,0,0,154,599,1,0,0,0,156,601,1,0,0,0,158,603,1,0,0,0,160,
        605,1,0,0,0,162,608,1,0,0,0,164,612,1,0,0,0,166,169,5,99,0,0,167,
        169,3,4,2,0,168,166,1,0,0,0,168,167,1,0,0,0,169,172,1,0,0,0,170,
        168,1,0,0,0,170,171,1,0,0,0,171,173,1,0,0,0,172,170,1,0,0,0,173,
        174,5,0,0,1,174,1,1,0,0,0,175,176,5,100,0,0,176,3,1,0,0,0,177,181,
        3,6,3,0,178,181,3,10,5,0,179,181,3,2,1,0,180,177,1,0,0,0,180,178,
        1,0,0,0,180,179,1,0,0,0,181,5,1,0,0,0,182,187,3,8,4,0,183,184,5,
        62,0,0,184,186,3,8,4,0,185,183,1,0,0,0,186,189,1,0,0,0,187,185,1,
        0,0,0,187,188,1,0,0,0,188,191,1,0,0,0,189,187,1,0,0,0,190,192,5,
        62,0,0,191,190,1,0,0,0,191,192,1,0,0,0,192,193,1,0,0,0,193,194,5,
        99,0,0,194,7,1,0,0,0,195,211,3,22,11,0,196,211,3,20,10,0,197,211,
        3,28,14,0,198,211,3,30,15,0,199,211,3,32,16,0,200,211,3,44,22,0,
        201,211,3,42,21,0,202,211,3,40,20,0,203,211,3,56,28,0,204,211,3,
        52,26,0,205,211,3,74,37,0,206,211,3,24,12,0,207,211,3,64,32,0,208,
        211,3,66,33,0,209,211,3,76,38,0,210,195,1,0,0,0,210,196,1,0,0,0,
        210,197,1,0,0,0,210,198,1,0,0,0,210,199,1,0,0,0,210,200,1,0,0,0,
        210,201,1,0,0,0,210,202,1,0,0,0,210,203,1,0,0,0,210,204,1,0,0,0,
        210,205,1,0,0,0,210,206,1,0,0,0,210,207,1,0,0,0,210,208,1,0,0,0,
        210,209,1,0,0,0,211,9,1,0,0,0,212,215,3,12,6,0,213,215,3,72,36,0,
        214,212,1,0,0,0,214,213,1,0,0,0,215,11,1,0,0,0,216,217,3,16,8,0,
        217,219,3,150,75,0,218,220,3,14,7,0,219,218,1,0,0,0,219,220,1,0,
        0,0,220,221,1,0,0,0,221,222,5,61,0,0,222,223,3,18,9,0,223,13,1,0,
        0,0,224,225,5,12,0,0,225,226,3,144,72,0,226,15,1,0,0,0,227,228,7,
        0,0,0,228,17,1,0,0,0,229,240,3,6,3,0,230,231,5,99,0,0,231,233,5,
        1,0,0,232,234,3,4,2,0,233,232,1,0,0,0,234,235,1,0,0,0,235,233,1,
        0,0,0,235,236,1,0,0,0,236,237,1,0,0,0,237,238,5,2,0,0,238,240,1,
        0,0,0,239,229,1,0,0,0,239,230,1,0,0,0,240,19,1,0,0,0,241,242,5,13,
        0,0,242,243,3,144,72,0,243,244,5,12,0,0,244,245,3,154,77,0,245,21,
        1,0,0,0,246,247,5,12,0,0,247,249,3,154,77,0,248,246,1,0,0,0,248,
        249,1,0,0,0,249,250,1,0,0,0,250,251,5,13,0,0,251,256,3,144,72,0,
        252,253,5,59,0,0,253,255,3,144,72,0,254,252,1,0,0,0,255,258,1,0,
        0,0,256,254,1,0,0,0,256,257,1,0,0,0,257,23,1,0,0,0,258,256,1,0,0,
        0,259,260,3,142,71,0,260,261,3,148,74,0,261,25,1,0,0,0,262,265,3,
        142,71,0,263,265,3,24,12,0,264,262,1,0,0,0,264,263,1,0,0,0,265,27,
        1,0,0,0,266,267,3,26,13,0,267,268,5,64,0,0,268,269,3,38,19,0,269,
        29,1,0,0,0,270,271,3,26,13,0,271,272,3,34,17,0,272,273,3,36,18,0,
        273,31,1,0,0,0,274,275,3,26,13,0,275,276,7,1,0,0,276,277,3,36,18,
        0,277,33,1,0,0,0,278,279,7,2,0,0,279,35,1,0,0,0,280,283,3,124,62,
        0,281,283,3,100,50,0,282,280,1,0,0,0,282,281,1,0,0,0,283,37,1,0,
        0,0,284,290,3,154,77,0,285,290,3,60,30,0,286,290,3,124,62,0,287,
        290,3,100,50,0,288,290,3,156,78,0,289,284,1,0,0,0,289,285,1,0,0,
        0,289,286,1,0,0,0,289,287,1,0,0,0,289,288,1,0,0,0,290,39,1,0,0,0,
        291,292,3,142,71,0,292,293,5,86,0,0,293,294,3,144,72,0,294,41,1,
        0,0,0,295,298,3,46,23,0,296,297,7,3,0,0,297,299,3,46,23,0,298,296,
        1,0,0,0,299,300,1,0,0,0,300,298,1,0,0,0,300,301,1,0,0,0,301,43,1,
        0,0,0,302,303,3,48,24,0,303,304,5,26,0,0,304,305,3,48,24,0,305,45,
        1,0,0,0,306,307,3,50,25,0,307,47,1,0,0,0,308,309,3,50,25,0,309,49,
        1,0,0,0,310,314,3,142,71,0,311,314,3,52,26,0,312,314,3,54,27,0,313,
        310,1,0,0,0,313,311,1,0,0,0,313,312,1,0,0,0,314,51,1,0,0,0,315,316,
        5,10,0,0,316,317,3,150,75,0,317,53,1,0,0,0,318,319,3,58,29,0,319,
        55,1,0,0,0,320,321,3,58,29,0,321,57,1,0,0,0,322,326,5,9,0,0,323,
        327,3,150,75,0,324,327,3,158,79,0,325,327,3,154,77,0,326,323,1,0,
        0,0,326,324,1,0,0,0,326,325,1,0,0,0,327,59,1,0,0,0,328,329,5,11,
        0,0,329,334,3,144,72,0,330,331,5,65,0,0,331,332,3,62,31,0,332,333,
        5,66,0,0,333,335,1,0,0,0,334,330,1,0,0,0,334,335,1,0,0,0,335,337,
        1,0,0,0,336,338,3,80,40,0,337,336,1,0,0,0,337,338,1,0,0,0,338,61,
        1,0,0,0,339,340,3,158,79,0,340,63,1,0,0,0,341,342,3,154,77,0,342,
        65,1,0,0,0,343,344,5,22,0,0,344,67,1,0,0,0,345,357,5,65,0,0,346,
        351,3,142,71,0,347,348,5,59,0,0,348,350,3,142,71,0,349,347,1,0,0,
        0,350,353,1,0,0,0,351,349,1,0,0,0,351,352,1,0,0,0,352,355,1,0,0,
        0,353,351,1,0,0,0,354,356,5,59,0,0,355,354,1,0,0,0,355,356,1,0,0,
        0,356,358,1,0,0,0,357,346,1,0,0,0,357,358,1,0,0,0,358,359,1,0,0,
        0,359,360,5,66,0,0,360,69,1,0,0,0,361,363,3,142,71,0,362,364,3,112,
        56,0,363,362,1,0,0,0,363,364,1,0,0,0,364,367,1,0,0,0,365,367,3,68,
        34,0,366,361,1,0,0,0,366,365,1,0,0,0,367,71,1,0,0,0,368,369,5,14,
        0,0,369,370,3,150,75,0,370,371,5,15,0,0,371,372,3,70,35,0,372,373,
        5,61,0,0,373,374,3,18,9,0,374,73,1,0,0,0,375,376,5,16,0,0,376,377,
        3,84,42,0,377,75,1,0,0,0,378,379,5,23,0,0,379,382,3,144,72,0,380,
        381,5,60,0,0,381,383,3,78,39,0,382,380,1,0,0,0,382,383,1,0,0,0,383,
        385,1,0,0,0,384,386,3,80,40,0,385,384,1,0,0,0,385,386,1,0,0,0,386,
        77,1,0,0,0,387,388,3,150,75,0,388,79,1,0,0,0,389,401,5,78,0,0,390,
        395,3,82,41,0,391,392,5,59,0,0,392,394,3,82,41,0,393,391,1,0,0,0,
        394,397,1,0,0,0,395,393,1,0,0,0,395,396,1,0,0,0,396,399,1,0,0,0,
        397,395,1,0,0,0,398,400,5,59,0,0,399,398,1,0,0,0,399,400,1,0,0,0,
        400,402,1,0,0,0,401,390,1,0,0,0,401,402,1,0,0,0,402,403,1,0,0,0,
        403,404,5,79,0,0,404,81,1,0,0,0,405,406,3,150,75,0,406,407,5,64,
        0,0,407,408,3,152,76,0,408,83,1,0,0,0,409,411,3,100,50,0,410,412,
        3,86,43,0,411,410,1,0,0,0,412,413,1,0,0,0,413,411,1,0,0,0,413,414,
        1,0,0,0,414,85,1,0,0,0,415,422,3,88,44,0,416,422,3,90,45,0,417,422,
        3,92,46,0,418,422,3,94,47,0,419,422,3,96,48,0,420,422,3,98,49,0,
        421,415,1,0,0,0,421,416,1,0,0,0,421,417,1,0,0,0,421,418,1,0,0,0,
        421,419,1,0,0,0,421,420,1,0,0,0,422,87,1,0,0,0,423,424,5,78,0,0,
        424,425,3,100,50,0,425,89,1,0,0,0,426,427,5,79,0,0,427,428,3,100,
        50,0,428,91,1,0,0,0,429,430,5,82,0,0,430,431,3,100,50,0,431,93,1,
        0,0,0,432,433,5,81,0,0,433,434,3,100,50,0,434,95,1,0,0,0,435,436,
        5,20,0,0,436,437,3,100,50,0,437,97,1,0,0,0,438,439,5,21,0,0,439,
        440,3,100,50,0,440,99,1,0,0,0,441,442,6,50,-1,0,442,443,3,102,51,
        0,443,449,1,0,0,0,444,445,10,2,0,0,445,446,7,4,0,0,446,448,3,102,
        51,0,447,444,1,0,0,0,448,451,1,0,0,0,449,447,1,0,0,0,449,450,1,0,
        0,0,450,101,1,0,0,0,451,449,1,0,0,0,452,453,6,51,-1,0,453,454,3,
        104,52,0,454,460,1,0,0,0,455,456,10,2,0,0,456,457,7,5,0,0,457,459,
        3,104,52,0,458,455,1,0,0,0,459,462,1,0,0,0,460,458,1,0,0,0,460,461,
        1,0,0,0,461,103,1,0,0,0,462,460,1,0,0,0,463,464,6,52,-1,0,464,465,
        3,106,53,0,465,471,1,0,0,0,466,467,10,2,0,0,467,468,7,6,0,0,468,
        470,3,106,53,0,469,466,1,0,0,0,470,473,1,0,0,0,471,469,1,0,0,0,471,
        472,1,0,0,0,472,105,1,0,0,0,473,471,1,0,0,0,474,477,3,108,54,0,475,
        476,5,63,0,0,476,478,3,108,54,0,477,475,1,0,0,0,477,478,1,0,0,0,
        478,107,1,0,0,0,479,490,3,110,55,0,480,481,3,150,75,0,481,483,5,
        57,0,0,482,484,3,110,55,0,483,482,1,0,0,0,484,485,1,0,0,0,485,483,
        1,0,0,0,485,486,1,0,0,0,486,487,1,0,0,0,487,488,5,58,0,0,488,490,
        1,0,0,0,489,479,1,0,0,0,489,480,1,0,0,0,490,109,1,0,0,0,491,492,
        3,120,60,0,492,111,1,0,0,0,493,507,5,65,0,0,494,496,3,114,57,0,495,
        494,1,0,0,0,495,496,1,0,0,0,496,497,1,0,0,0,497,499,5,61,0,0,498,
        500,3,116,58,0,499,498,1,0,0,0,499,500,1,0,0,0,500,505,1,0,0,0,501,
        503,5,61,0,0,502,504,3,118,59,0,503,502,1,0,0,0,503,504,1,0,0,0,
        504,506,1,0,0,0,505,501,1,0,0,0,505,506,1,0,0,0,506,508,1,0,0,0,
        507,495,1,0,0,0,507,508,1,0,0,0,508,509,1,0,0,0,509,517,5,66,0,0,
        510,511,5,65,0,0,511,513,5,60,0,0,512,514,3,118,59,0,513,512,1,0,
        0,0,513,514,1,0,0,0,514,515,1,0,0,0,515,517,5,66,0,0,516,493,1,0,
        0,0,516,510,1,0,0,0,517,113,1,0,0,0,518,519,3,160,80,0,519,115,1,
        0,0,0,520,521,3,160,80,0,521,117,1,0,0,0,522,523,3,160,80,0,523,
        119,1,0,0,0,524,528,3,142,71,0,525,528,3,124,62,0,526,528,3,122,
        61,0,527,524,1,0,0,0,527,525,1,0,0,0,527,526,1,0,0,0,528,121,1,0,
        0,0,529,530,5,57,0,0,530,531,3,100,50,0,531,532,5,58,0,0,532,123,
        1,0,0,0,533,537,3,126,63,0,534,537,3,128,64,0,535,537,3,130,65,0,
        536,533,1,0,0,0,536,534,1,0,0,0,536,535,1,0,0,0,537,125,1,0,0,0,
        538,539,3,130,65,0,539,540,5,17,0,0,540,541,3,130,65,0,541,127,1,
        0,0,0,542,543,3,130,65,0,543,544,5,50,0,0,544,545,3,132,66,0,545,
        129,1,0,0,0,546,548,3,162,81,0,547,549,3,150,75,0,548,547,1,0,0,
        0,548,549,1,0,0,0,549,131,1,0,0,0,550,553,3,164,82,0,551,554,5,53,
        0,0,552,554,3,150,75,0,553,551,1,0,0,0,553,552,1,0,0,0,553,554,1,
        0,0,0,554,133,1,0,0,0,555,556,3,160,80,0,556,135,1,0,0,0,557,558,
        5,65,0,0,558,559,3,134,67,0,559,560,5,66,0,0,560,137,1,0,0,0,561,
        562,5,54,0,0,562,563,3,158,79,0,563,139,1,0,0,0,564,566,3,150,75,
        0,565,567,3,136,68,0,566,565,1,0,0,0,566,567,1,0,0,0,567,141,1,0,
        0,0,568,573,3,140,70,0,569,570,5,54,0,0,570,572,3,140,70,0,571,569,
        1,0,0,0,572,575,1,0,0,0,573,571,1,0,0,0,573,574,1,0,0,0,574,577,
        1,0,0,0,575,573,1,0,0,0,576,578,3,138,69,0,577,576,1,0,0,0,577,578,
        1,0,0,0,578,143,1,0,0,0,579,584,3,150,75,0,580,581,5,54,0,0,581,
        583,3,150,75,0,582,580,1,0,0,0,583,586,1,0,0,0,584,582,1,0,0,0,584,
        585,1,0,0,0,585,145,1,0,0,0,586,584,1,0,0,0,587,588,3,150,75,0,588,
        147,1,0,0,0,589,590,5,61,0,0,590,591,3,146,73,0,591,149,1,0,0,0,
        592,593,5,41,0,0,593,151,1,0,0,0,594,598,3,154,77,0,595,598,3,156,
        78,0,596,598,3,162,81,0,597,594,1,0,0,0,597,595,1,0,0,0,597,596,
        1,0,0,0,598,153,1,0,0,0,599,600,5,3,0,0,600,155,1,0,0,0,601,602,
        7,7,0,0,602,157,1,0,0,0,603,604,3,164,82,0,604,159,1,0,0,0,605,606,
        3,162,81,0,606,161,1,0,0,0,607,609,7,5,0,0,608,607,1,0,0,0,608,609,
        1,0,0,0,609,610,1,0,0,0,610,611,3,164,82,0,611,163,1,0,0,0,612,613,
        5,4,0,0,613,165,1,0,0,0,55,168,170,180,187,191,210,214,219,235,239,
        248,256,264,282,289,300,313,326,334,337,351,355,357,363,366,382,
        385,395,399,401,413,421,449,460,471,477,485,489,495,499,503,505,
        507,513,516,527,536,548,553,566,573,577,584,597,608
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
                     "'>='", "'<='", "'<>'", "'!='", "'@'", "'->'", "'+='", 
                     "'-='", "'*='", "'@='", "'/='", "'&='", "'|='", "'^='", 
                     "'<<='", "'>>='", "'**='", "'//='" ]

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
                      "ADD_ASSIGN", "SUB_ASSIGN", "MULT_ASSIGN", "AT_ASSIGN", 
                      "DIV_ASSIGN", "AND_ASSIGN", "OR_ASSIGN", "XOR_ASSIGN", 
                      "LEFT_SHIFT_ASSIGN", "RIGHT_SHIFT_ASSIGN", "POWER_ASSIGN", 
                      "IDIV_ASSIGN", "NEWLINE", "PRAGMA", "COMMENT", "WS", 
                      "EXPLICIT_LINE_JOINING", "ERRORTOKEN" ]

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
    RULE_mif = 24
    RULE_connectable = 25
    RULE_signaldef_stmt = 26
    RULE_pindef_stmt = 27
    RULE_pin_declaration = 28
    RULE_pin_stmt = 29
    RULE_new_stmt = 30
    RULE_new_count = 31
    RULE_string_stmt = 32
    RULE_pass_stmt = 33
    RULE_list_literal_of_field_references = 34
    RULE_iterable_references = 35
    RULE_for_stmt = 36
    RULE_assert_stmt = 37
    RULE_trait_stmt = 38
    RULE_constructor = 39
    RULE_template = 40
    RULE_template_arg = 41
    RULE_comparison = 42
    RULE_compare_op_pair = 43
    RULE_lt_arithmetic_or = 44
    RULE_gt_arithmetic_or = 45
    RULE_lt_eq_arithmetic_or = 46
    RULE_gt_eq_arithmetic_or = 47
    RULE_in_arithmetic_or = 48
    RULE_is_arithmetic_or = 49
    RULE_arithmetic_expression = 50
    RULE_sum = 51
    RULE_term = 52
    RULE_power = 53
    RULE_functional = 54
    RULE_bound = 55
    RULE_slice = 56
    RULE_slice_start = 57
    RULE_slice_stop = 58
    RULE_slice_step = 59
    RULE_atom = 60
    RULE_arithmetic_group = 61
    RULE_literal_physical = 62
    RULE_bound_quantity = 63
    RULE_bilateral_quantity = 64
    RULE_quantity = 65
    RULE_bilateral_tolerance = 66
    RULE_key = 67
    RULE_array_index = 68
    RULE_pin_reference_end = 69
    RULE_field_reference_part = 70
    RULE_field_reference = 71
    RULE_type_reference = 72
    RULE_unit = 73
    RULE_type_info = 74
    RULE_name = 75
    RULE_literal = 76
    RULE_string = 77
    RULE_boolean_ = 78
    RULE_number_hint_natural = 79
    RULE_number_hint_integer = 80
    RULE_number = 81
    RULE_number_signless = 82

    ruleNames =  [ "file_input", "pragma_stmt", "stmt", "simple_stmts", 
                   "simple_stmt", "compound_stmt", "blockdef", "blockdef_super", 
                   "blocktype", "block", "dep_import_stmt", "import_stmt", 
                   "declaration_stmt", "field_reference_or_declaration", 
                   "assign_stmt", "cum_assign_stmt", "set_assign_stmt", 
                   "cum_operator", "cum_assignable", "assignable", "retype_stmt", 
                   "directed_connect_stmt", "connect_stmt", "bridgeable", 
                   "mif", "connectable", "signaldef_stmt", "pindef_stmt", 
                   "pin_declaration", "pin_stmt", "new_stmt", "new_count", 
                   "string_stmt", "pass_stmt", "list_literal_of_field_references", 
                   "iterable_references", "for_stmt", "assert_stmt", "trait_stmt", 
                   "constructor", "template", "template_arg", "comparison", 
                   "compare_op_pair", "lt_arithmetic_or", "gt_arithmetic_or", 
                   "lt_eq_arithmetic_or", "gt_eq_arithmetic_or", "in_arithmetic_or", 
                   "is_arithmetic_or", "arithmetic_expression", "sum", "term", 
                   "power", "functional", "bound", "slice", "slice_start", 
                   "slice_stop", "slice_step", "atom", "arithmetic_group", 
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
    ADD_ASSIGN=87
    SUB_ASSIGN=88
    MULT_ASSIGN=89
    AT_ASSIGN=90
    DIV_ASSIGN=91
    AND_ASSIGN=92
    OR_ASSIGN=93
    XOR_ASSIGN=94
    LEFT_SHIFT_ASSIGN=95
    RIGHT_SHIFT_ASSIGN=96
    POWER_ASSIGN=97
    IDIV_ASSIGN=98
    NEWLINE=99
    PRAGMA=100
    COMMENT=101
    WS=102
    EXPLICIT_LINE_JOINING=103
    ERRORTOKEN=104

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
            self.state = 170
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 2199035934664) != 0) or _la==99 or _la==100:
                self.state = 168
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [99]:
                    self.state = 166
                    self.match(AtoParser.NEWLINE)
                    pass
                elif token in [3, 6, 7, 8, 9, 10, 12, 13, 14, 16, 22, 23, 41, 100]:
                    self.state = 167
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 172
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 173
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
            self.state = 175
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
            self.state = 180
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 16, 22, 23, 41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 177
                self.simple_stmts()
                pass
            elif token in [6, 7, 8, 14]:
                self.enterOuterAlt(localctx, 2)
                self.state = 178
                self.compound_stmt()
                pass
            elif token in [100]:
                self.enterOuterAlt(localctx, 3)
                self.state = 179
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
            self.state = 182
            self.simple_stmt()
            self.state = 187
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 183
                    self.match(AtoParser.SEMI_COLON)
                    self.state = 184
                    self.simple_stmt() 
                self.state = 189
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 191
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==62:
                self.state = 190
                self.match(AtoParser.SEMI_COLON)


            self.state = 193
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
            self.state = 210
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 195
                self.import_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 196
                self.dep_import_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 197
                self.assign_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 198
                self.cum_assign_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 199
                self.set_assign_stmt()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 200
                self.connect_stmt()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 201
                self.directed_connect_stmt()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 202
                self.retype_stmt()
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 203
                self.pin_declaration()
                pass

            elif la_ == 10:
                self.enterOuterAlt(localctx, 10)
                self.state = 204
                self.signaldef_stmt()
                pass

            elif la_ == 11:
                self.enterOuterAlt(localctx, 11)
                self.state = 205
                self.assert_stmt()
                pass

            elif la_ == 12:
                self.enterOuterAlt(localctx, 12)
                self.state = 206
                self.declaration_stmt()
                pass

            elif la_ == 13:
                self.enterOuterAlt(localctx, 13)
                self.state = 207
                self.string_stmt()
                pass

            elif la_ == 14:
                self.enterOuterAlt(localctx, 14)
                self.state = 208
                self.pass_stmt()
                pass

            elif la_ == 15:
                self.enterOuterAlt(localctx, 15)
                self.state = 209
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
            self.state = 214
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [6, 7, 8]:
                self.enterOuterAlt(localctx, 1)
                self.state = 212
                self.blockdef()
                pass
            elif token in [14]:
                self.enterOuterAlt(localctx, 2)
                self.state = 213
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
            self.state = 216
            self.blocktype()
            self.state = 217
            self.name()
            self.state = 219
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 218
                self.blockdef_super()


            self.state = 221
            self.match(AtoParser.COLON)
            self.state = 222
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
            self.state = 224
            self.match(AtoParser.FROM)
            self.state = 225
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
            self.state = 227
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
            self.state = 239
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 16, 22, 23, 41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 229
                self.simple_stmts()
                pass
            elif token in [99]:
                self.enterOuterAlt(localctx, 2)
                self.state = 230
                self.match(AtoParser.NEWLINE)
                self.state = 231
                self.match(AtoParser.INDENT)
                self.state = 233 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 232
                    self.stmt()
                    self.state = 235 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 2199035934664) != 0) or _la==100):
                        break

                self.state = 237
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
            self.state = 241
            self.match(AtoParser.IMPORT)
            self.state = 242
            self.type_reference()
            self.state = 243
            self.match(AtoParser.FROM)
            self.state = 244
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
            self.state = 248
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 246
                self.match(AtoParser.FROM)
                self.state = 247
                self.string()


            self.state = 250
            self.match(AtoParser.IMPORT)
            self.state = 251
            self.type_reference()
            self.state = 256
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==59:
                self.state = 252
                self.match(AtoParser.COMMA)
                self.state = 253
                self.type_reference()
                self.state = 258
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
            self.state = 259
            self.field_reference()
            self.state = 260
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
            self.state = 264
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 262
                self.field_reference()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 263
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
            self.state = 266
            self.field_reference_or_declaration()
            self.state = 267
            self.match(AtoParser.ASSIGN)
            self.state = 268
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
            self.state = 270
            self.field_reference_or_declaration()
            self.state = 271
            self.cum_operator()
            self.state = 272
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
            self.state = 274
            self.field_reference_or_declaration()
            self.state = 275
            _la = self._input.LA(1)
            if not(_la==92 or _la==93):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 276
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
            self.state = 278
            _la = self._input.LA(1)
            if not(_la==87 or _la==88):
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
            self.state = 282
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 280
                self.literal_physical()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 281
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
            self.state = 289
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 284
                self.string()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 285
                self.new_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 286
                self.literal_physical()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 287
                self.arithmetic_expression(0)
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 288
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
            self.state = 291
            self.field_reference()
            self.state = 292
            self.match(AtoParser.ARROW)
            self.state = 293
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


        def SPERM(self, i:int=None):
            if i is None:
                return self.getTokens(AtoParser.SPERM)
            else:
                return self.getToken(AtoParser.SPERM, i)

        def LSPERM(self, i:int=None):
            if i is None:
                return self.getTokens(AtoParser.LSPERM)
            else:
                return self.getToken(AtoParser.LSPERM, i)

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
            self.state = 295
            self.bridgeable()
            self.state = 298 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 296
                _la = self._input.LA(1)
                if not(_la==24 or _la==25):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 297
                self.bridgeable()
                self.state = 300 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==24 or _la==25):
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
        self.enterRule(localctx, 44, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 302
            self.mif()
            self.state = 303
            self.match(AtoParser.WIRE)
            self.state = 304
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
        self.enterRule(localctx, 46, self.RULE_bridgeable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 306
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
        self.enterRule(localctx, 48, self.RULE_mif)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 308
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
        self.enterRule(localctx, 50, self.RULE_connectable)
        try:
            self.state = 313
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 310
                self.field_reference()
                pass
            elif token in [10]:
                self.enterOuterAlt(localctx, 2)
                self.state = 311
                self.signaldef_stmt()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 3)
                self.state = 312
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
        self.enterRule(localctx, 52, self.RULE_signaldef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 315
            self.match(AtoParser.SIGNAL)
            self.state = 316
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
        self.enterRule(localctx, 54, self.RULE_pindef_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 318
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
        self.enterRule(localctx, 56, self.RULE_pin_declaration)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 320
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
        self.enterRule(localctx, 58, self.RULE_pin_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 322
            self.match(AtoParser.PIN)
            self.state = 326
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41]:
                self.state = 323
                self.name()
                pass
            elif token in [4]:
                self.state = 324
                self.number_hint_natural()
                pass
            elif token in [3]:
                self.state = 325
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
        self.enterRule(localctx, 60, self.RULE_new_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 328
            self.match(AtoParser.NEW)
            self.state = 329
            self.type_reference()
            self.state = 334
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==65:
                self.state = 330
                self.match(AtoParser.OPEN_BRACK)
                self.state = 331
                self.new_count()
                self.state = 332
                self.match(AtoParser.CLOSE_BRACK)


            self.state = 337
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==78:
                self.state = 336
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
        self.enterRule(localctx, 62, self.RULE_new_count)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 339
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
        self.enterRule(localctx, 64, self.RULE_string_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 341
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
        self.enterRule(localctx, 66, self.RULE_pass_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 343
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
        self.enterRule(localctx, 68, self.RULE_list_literal_of_field_references)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 345
            self.match(AtoParser.OPEN_BRACK)
            self.state = 357
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==41:
                self.state = 346
                self.field_reference()
                self.state = 351
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,20,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 347
                        self.match(AtoParser.COMMA)
                        self.state = 348
                        self.field_reference() 
                    self.state = 353
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,20,self._ctx)

                self.state = 355
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==59:
                    self.state = 354
                    self.match(AtoParser.COMMA)




            self.state = 359
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
        self.enterRule(localctx, 70, self.RULE_iterable_references)
        self._la = 0 # Token type
        try:
            self.state = 366
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 361
                self.field_reference()
                self.state = 363
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==65:
                    self.state = 362
                    self.slice_()


                pass
            elif token in [65]:
                self.enterOuterAlt(localctx, 2)
                self.state = 365
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
        self.enterRule(localctx, 72, self.RULE_for_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 368
            self.match(AtoParser.FOR)
            self.state = 369
            self.name()
            self.state = 370
            self.match(AtoParser.IN)
            self.state = 371
            self.iterable_references()
            self.state = 372
            self.match(AtoParser.COLON)
            self.state = 373
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
        self.enterRule(localctx, 74, self.RULE_assert_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 375
            self.match(AtoParser.ASSERT)
            self.state = 376
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
        self.enterRule(localctx, 76, self.RULE_trait_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 378
            self.match(AtoParser.TRAIT)
            self.state = 379
            self.type_reference()
            self.state = 382
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==60:
                self.state = 380
                self.match(AtoParser.DOUBLE_COLON)
                self.state = 381
                self.constructor()


            self.state = 385
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==78:
                self.state = 384
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
        self.enterRule(localctx, 78, self.RULE_constructor)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 387
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
        self.enterRule(localctx, 80, self.RULE_template)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 389
            self.match(AtoParser.LESS_THAN)
            self.state = 401
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==41:
                self.state = 390
                self.template_arg()
                self.state = 395
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,27,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 391
                        self.match(AtoParser.COMMA)
                        self.state = 392
                        self.template_arg() 
                    self.state = 397
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,27,self._ctx)

                self.state = 399
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==59:
                    self.state = 398
                    self.match(AtoParser.COMMA)




            self.state = 403
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
        self.enterRule(localctx, 82, self.RULE_template_arg)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 405
            self.name()
            self.state = 406
            self.match(AtoParser.ASSIGN)
            self.state = 407
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
        self.enterRule(localctx, 84, self.RULE_comparison)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 409
            self.arithmetic_expression(0)
            self.state = 411 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 410
                self.compare_op_pair()
                self.state = 413 
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
        self.enterRule(localctx, 86, self.RULE_compare_op_pair)
        try:
            self.state = 421
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [78]:
                self.enterOuterAlt(localctx, 1)
                self.state = 415
                self.lt_arithmetic_or()
                pass
            elif token in [79]:
                self.enterOuterAlt(localctx, 2)
                self.state = 416
                self.gt_arithmetic_or()
                pass
            elif token in [82]:
                self.enterOuterAlt(localctx, 3)
                self.state = 417
                self.lt_eq_arithmetic_or()
                pass
            elif token in [81]:
                self.enterOuterAlt(localctx, 4)
                self.state = 418
                self.gt_eq_arithmetic_or()
                pass
            elif token in [20]:
                self.enterOuterAlt(localctx, 5)
                self.state = 419
                self.in_arithmetic_or()
                pass
            elif token in [21]:
                self.enterOuterAlt(localctx, 6)
                self.state = 420
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
        self.enterRule(localctx, 88, self.RULE_lt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 423
            self.match(AtoParser.LESS_THAN)
            self.state = 424
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
        self.enterRule(localctx, 90, self.RULE_gt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 426
            self.match(AtoParser.GREATER_THAN)
            self.state = 427
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
        self.enterRule(localctx, 92, self.RULE_lt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 429
            self.match(AtoParser.LT_EQ)
            self.state = 430
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
        self.enterRule(localctx, 94, self.RULE_gt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 432
            self.match(AtoParser.GT_EQ)
            self.state = 433
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
        self.enterRule(localctx, 96, self.RULE_in_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 435
            self.match(AtoParser.WITHIN)
            self.state = 436
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
        self.enterRule(localctx, 98, self.RULE_is_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 438
            self.match(AtoParser.IS)
            self.state = 439
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
        _startState = 100
        self.enterRecursionRule(localctx, 100, self.RULE_arithmetic_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 442
            self.sum_(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 449
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,32,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.Arithmetic_expressionContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmetic_expression)
                    self.state = 444
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 445
                    _la = self._input.LA(1)
                    if not(_la==67 or _la==69):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 446
                    self.sum_(0) 
                self.state = 451
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,32,self._ctx)

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
        _startState = 102
        self.enterRecursionRule(localctx, 102, self.RULE_sum, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 453
            self.term(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 460
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,33,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.SumContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_sum)
                    self.state = 455
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 456
                    _la = self._input.LA(1)
                    if not(_la==72 or _la==73):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 457
                    self.term(0) 
                self.state = 462
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,33,self._ctx)

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
        _startState = 104
        self.enterRecursionRule(localctx, 104, self.RULE_term, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 464
            self.power()
            self._ctx.stop = self._input.LT(-1)
            self.state = 471
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,34,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.TermContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_term)
                    self.state = 466
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 467
                    _la = self._input.LA(1)
                    if not(_la==56 or _la==74):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 468
                    self.power() 
                self.state = 473
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,34,self._ctx)

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
        self.enterRule(localctx, 106, self.RULE_power)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 474
            self.functional()
            self.state = 477
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,35,self._ctx)
            if la_ == 1:
                self.state = 475
                self.match(AtoParser.POWER)
                self.state = 476
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
        self.enterRule(localctx, 108, self.RULE_functional)
        self._la = 0 # Token type
        try:
            self.state = 489
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,37,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 479
                self.bound()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 480
                self.name()
                self.state = 481
                self.match(AtoParser.OPEN_PAREN)
                self.state = 483 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 482
                    self.bound()
                    self.state = 485 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 144117387099111440) != 0) or _la==72 or _la==73):
                        break

                self.state = 487
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
        self.enterRule(localctx, 110, self.RULE_bound)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 491
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
        self.enterRule(localctx, 112, self.RULE_slice)
        self._la = 0 # Token type
        try:
            self.state = 516
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,44,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 493
                self.match(AtoParser.OPEN_BRACK)
                self.state = 507
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4 or _la==61 or _la==72 or _la==73:
                    self.state = 495
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if _la==4 or _la==72 or _la==73:
                        self.state = 494
                        self.slice_start()


                    self.state = 497
                    self.match(AtoParser.COLON)
                    self.state = 499
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if _la==4 or _la==72 or _la==73:
                        self.state = 498
                        self.slice_stop()


                    self.state = 505
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if _la==61:
                        self.state = 501
                        self.match(AtoParser.COLON)
                        self.state = 503
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if _la==4 or _la==72 or _la==73:
                            self.state = 502
                            self.slice_step()






                self.state = 509
                self.match(AtoParser.CLOSE_BRACK)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 510
                self.match(AtoParser.OPEN_BRACK)

                self.state = 511
                self.match(AtoParser.DOUBLE_COLON)
                self.state = 513
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4 or _la==72 or _la==73:
                    self.state = 512
                    self.slice_step()


                self.state = 515
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
        self.enterRule(localctx, 114, self.RULE_slice_start)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 518
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
        self.enterRule(localctx, 116, self.RULE_slice_stop)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 520
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
        self.enterRule(localctx, 118, self.RULE_slice_step)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 522
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
        self.enterRule(localctx, 120, self.RULE_atom)
        try:
            self.state = 527
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 524
                self.field_reference()
                pass
            elif token in [4, 72, 73]:
                self.enterOuterAlt(localctx, 2)
                self.state = 525
                self.literal_physical()
                pass
            elif token in [57]:
                self.enterOuterAlt(localctx, 3)
                self.state = 526
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
        self.enterRule(localctx, 122, self.RULE_arithmetic_group)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 529
            self.match(AtoParser.OPEN_PAREN)
            self.state = 530
            self.arithmetic_expression(0)
            self.state = 531
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
        self.enterRule(localctx, 124, self.RULE_literal_physical)
        try:
            self.state = 536
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,46,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 533
                self.bound_quantity()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 534
                self.bilateral_quantity()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 535
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
        self.enterRule(localctx, 126, self.RULE_bound_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 538
            self.quantity()
            self.state = 539
            self.match(AtoParser.TO)
            self.state = 540
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
        self.enterRule(localctx, 128, self.RULE_bilateral_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 542
            self.quantity()
            self.state = 543
            self.match(AtoParser.PLUS_OR_MINUS)
            self.state = 544
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
        self.enterRule(localctx, 130, self.RULE_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 546
            self.number()
            self.state = 548
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,47,self._ctx)
            if la_ == 1:
                self.state = 547
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
        self.enterRule(localctx, 132, self.RULE_bilateral_tolerance)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 550
            self.number_signless()
            self.state = 553
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,48,self._ctx)
            if la_ == 1:
                self.state = 551
                self.match(AtoParser.PERCENT)

            elif la_ == 2:
                self.state = 552
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
        self.enterRule(localctx, 134, self.RULE_key)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 555
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
        self.enterRule(localctx, 136, self.RULE_array_index)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 557
            self.match(AtoParser.OPEN_BRACK)
            self.state = 558
            self.key()
            self.state = 559
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
        self.enterRule(localctx, 138, self.RULE_pin_reference_end)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 561
            self.match(AtoParser.DOT)
            self.state = 562
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
        self.enterRule(localctx, 140, self.RULE_field_reference_part)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 564
            self.name()
            self.state = 566
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,49,self._ctx)
            if la_ == 1:
                self.state = 565
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
        self.enterRule(localctx, 142, self.RULE_field_reference)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 568
            self.field_reference_part()
            self.state = 573
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,50,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 569
                    self.match(AtoParser.DOT)
                    self.state = 570
                    self.field_reference_part() 
                self.state = 575
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,50,self._ctx)

            self.state = 577
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,51,self._ctx)
            if la_ == 1:
                self.state = 576
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
        self.enterRule(localctx, 144, self.RULE_type_reference)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 579
            self.name()
            self.state = 584
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==54:
                self.state = 580
                self.match(AtoParser.DOT)
                self.state = 581
                self.name()
                self.state = 586
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
        self.enterRule(localctx, 146, self.RULE_unit)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 587
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
        self.enterRule(localctx, 148, self.RULE_type_info)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 589
            self.match(AtoParser.COLON)
            self.state = 590
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
        self.enterRule(localctx, 150, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 592
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
        self.enterRule(localctx, 152, self.RULE_literal)
        try:
            self.state = 597
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3]:
                self.enterOuterAlt(localctx, 1)
                self.state = 594
                self.string()
                pass
            elif token in [18, 19]:
                self.enterOuterAlt(localctx, 2)
                self.state = 595
                self.boolean_()
                pass
            elif token in [4, 72, 73]:
                self.enterOuterAlt(localctx, 3)
                self.state = 596
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
        self.enterRule(localctx, 154, self.RULE_string)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 599
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
        self.enterRule(localctx, 156, self.RULE_boolean_)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 601
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
        self.enterRule(localctx, 158, self.RULE_number_hint_natural)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 603
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
        self.enterRule(localctx, 160, self.RULE_number_hint_integer)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 605
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
        self.enterRule(localctx, 162, self.RULE_number)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 608
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==72 or _la==73:
                self.state = 607
                _la = self._input.LA(1)
                if not(_la==72 or _la==73):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()


            self.state = 610
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
        self.enterRule(localctx, 164, self.RULE_number_signless)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 612
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
        self._predicates[50] = self.arithmetic_expression_sempred
        self._predicates[51] = self.sum_sempred
        self._predicates[52] = self.term_sempred
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
         




