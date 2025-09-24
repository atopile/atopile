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
        4,1,104,597,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,
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
        78,2,79,7,79,2,80,7,80,2,81,7,81,1,0,1,0,5,0,167,8,0,10,0,12,0,170,
        9,0,1,0,1,0,1,1,1,1,1,2,1,2,1,2,3,2,179,8,2,1,3,1,3,1,3,5,3,184,
        8,3,10,3,12,3,187,9,3,1,3,3,3,190,8,3,1,3,1,3,1,4,1,4,1,4,1,4,1,
        4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,3,4,208,8,4,1,5,1,5,3,5,212,
        8,5,1,6,1,6,1,6,3,6,217,8,6,1,6,1,6,1,6,1,7,1,7,1,7,1,8,1,8,1,9,
        1,9,1,9,1,9,4,9,231,8,9,11,9,12,9,232,1,9,1,9,3,9,237,8,9,1,10,1,
        10,3,10,241,8,10,1,10,1,10,1,10,1,11,1,11,1,11,1,12,1,12,3,12,251,
        8,12,1,13,1,13,1,13,1,13,1,14,1,14,1,14,1,14,1,15,1,15,1,15,1,15,
        1,16,1,16,1,17,1,17,3,17,269,8,17,1,18,1,18,1,18,1,18,1,18,3,18,
        276,8,18,1,19,1,19,1,19,1,19,1,20,1,20,1,20,1,20,3,20,286,8,20,1,
        21,1,21,1,21,1,21,1,22,1,22,1,23,1,23,1,24,1,24,1,24,3,24,299,8,
        24,1,25,1,25,1,25,1,26,1,26,1,27,1,27,1,28,1,28,1,28,1,28,3,28,312,
        8,28,1,29,1,29,1,29,1,29,1,29,1,29,3,29,320,8,29,1,29,3,29,323,8,
        29,1,30,1,30,1,31,1,31,1,32,1,32,1,33,1,33,1,33,1,33,5,33,335,8,
        33,10,33,12,33,338,9,33,1,33,3,33,341,8,33,3,33,343,8,33,1,33,1,
        33,1,34,1,34,3,34,349,8,34,1,34,3,34,352,8,34,1,35,1,35,1,35,1,35,
        1,35,1,35,1,35,1,36,1,36,1,36,1,37,1,37,3,37,366,8,37,1,37,1,37,
        1,37,3,37,371,8,37,1,37,3,37,374,8,37,1,38,1,38,1,39,1,39,1,39,1,
        39,5,39,382,8,39,10,39,12,39,385,9,39,1,39,3,39,388,8,39,3,39,390,
        8,39,1,39,1,39,1,40,1,40,1,40,1,40,1,41,1,41,4,41,400,8,41,11,41,
        12,41,401,1,42,1,42,1,42,1,42,1,42,1,42,3,42,410,8,42,1,43,1,43,
        1,43,1,44,1,44,1,44,1,45,1,45,1,45,1,46,1,46,1,46,1,47,1,47,1,47,
        1,48,1,48,1,48,1,49,1,49,1,49,1,49,1,49,1,49,5,49,436,8,49,10,49,
        12,49,439,9,49,1,50,1,50,1,50,1,50,1,50,1,50,5,50,447,8,50,10,50,
        12,50,450,9,50,1,51,1,51,1,51,1,51,1,51,1,51,5,51,458,8,51,10,51,
        12,51,461,9,51,1,52,1,52,1,52,3,52,466,8,52,1,53,1,53,1,53,1,53,
        4,53,472,8,53,11,53,12,53,473,1,53,1,53,3,53,478,8,53,1,54,1,54,
        1,55,1,55,3,55,484,8,55,1,55,1,55,3,55,488,8,55,1,55,1,55,3,55,492,
        8,55,3,55,494,8,55,3,55,496,8,55,1,55,1,55,1,55,1,55,3,55,502,8,
        55,1,55,3,55,505,8,55,1,56,1,56,1,57,1,57,1,58,1,58,1,59,1,59,1,
        59,3,59,516,8,59,1,60,1,60,1,60,1,60,1,61,1,61,1,61,3,61,525,8,61,
        1,62,1,62,1,62,1,62,1,63,1,63,1,63,1,63,1,64,1,64,3,64,537,8,64,
        1,65,1,65,1,65,3,65,542,8,65,1,66,1,66,1,67,1,67,1,67,1,67,1,68,
        1,68,1,68,1,69,1,69,3,69,555,8,69,1,70,1,70,1,70,5,70,560,8,70,10,
        70,12,70,563,9,70,1,70,3,70,566,8,70,1,71,1,71,1,72,1,72,1,73,1,
        73,1,73,1,74,1,74,1,75,1,75,1,75,3,75,580,8,75,1,76,1,76,1,77,1,
        77,1,78,1,78,1,79,1,79,1,80,3,80,591,8,80,1,80,1,80,1,81,1,81,1,
        81,0,3,98,100,102,82,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,
        32,34,36,38,40,42,44,46,48,50,52,54,56,58,60,62,64,66,68,70,72,74,
        76,78,80,82,84,86,88,90,92,94,96,98,100,102,104,106,108,110,112,
        114,116,118,120,122,124,126,128,130,132,134,136,138,140,142,144,
        146,148,150,152,154,156,158,160,162,0,8,1,0,6,8,1,0,92,93,1,0,87,
        88,1,0,24,25,2,0,67,67,69,69,1,0,72,73,2,0,56,56,74,74,1,0,18,19,
        594,0,168,1,0,0,0,2,173,1,0,0,0,4,178,1,0,0,0,6,180,1,0,0,0,8,207,
        1,0,0,0,10,211,1,0,0,0,12,213,1,0,0,0,14,221,1,0,0,0,16,224,1,0,
        0,0,18,236,1,0,0,0,20,240,1,0,0,0,22,245,1,0,0,0,24,250,1,0,0,0,
        26,252,1,0,0,0,28,256,1,0,0,0,30,260,1,0,0,0,32,264,1,0,0,0,34,268,
        1,0,0,0,36,275,1,0,0,0,38,277,1,0,0,0,40,281,1,0,0,0,42,287,1,0,
        0,0,44,291,1,0,0,0,46,293,1,0,0,0,48,298,1,0,0,0,50,300,1,0,0,0,
        52,303,1,0,0,0,54,305,1,0,0,0,56,307,1,0,0,0,58,313,1,0,0,0,60,324,
        1,0,0,0,62,326,1,0,0,0,64,328,1,0,0,0,66,330,1,0,0,0,68,351,1,0,
        0,0,70,353,1,0,0,0,72,360,1,0,0,0,74,363,1,0,0,0,76,375,1,0,0,0,
        78,377,1,0,0,0,80,393,1,0,0,0,82,397,1,0,0,0,84,409,1,0,0,0,86,411,
        1,0,0,0,88,414,1,0,0,0,90,417,1,0,0,0,92,420,1,0,0,0,94,423,1,0,
        0,0,96,426,1,0,0,0,98,429,1,0,0,0,100,440,1,0,0,0,102,451,1,0,0,
        0,104,462,1,0,0,0,106,477,1,0,0,0,108,479,1,0,0,0,110,504,1,0,0,
        0,112,506,1,0,0,0,114,508,1,0,0,0,116,510,1,0,0,0,118,515,1,0,0,
        0,120,517,1,0,0,0,122,524,1,0,0,0,124,526,1,0,0,0,126,530,1,0,0,
        0,128,534,1,0,0,0,130,538,1,0,0,0,132,543,1,0,0,0,134,545,1,0,0,
        0,136,549,1,0,0,0,138,552,1,0,0,0,140,556,1,0,0,0,142,567,1,0,0,
        0,144,569,1,0,0,0,146,571,1,0,0,0,148,574,1,0,0,0,150,579,1,0,0,
        0,152,581,1,0,0,0,154,583,1,0,0,0,156,585,1,0,0,0,158,587,1,0,0,
        0,160,590,1,0,0,0,162,594,1,0,0,0,164,167,5,99,0,0,165,167,3,4,2,
        0,166,164,1,0,0,0,166,165,1,0,0,0,167,170,1,0,0,0,168,166,1,0,0,
        0,168,169,1,0,0,0,169,171,1,0,0,0,170,168,1,0,0,0,171,172,5,0,0,
        1,172,1,1,0,0,0,173,174,5,100,0,0,174,3,1,0,0,0,175,179,3,6,3,0,
        176,179,3,10,5,0,177,179,3,2,1,0,178,175,1,0,0,0,178,176,1,0,0,0,
        178,177,1,0,0,0,179,5,1,0,0,0,180,185,3,8,4,0,181,182,5,62,0,0,182,
        184,3,8,4,0,183,181,1,0,0,0,184,187,1,0,0,0,185,183,1,0,0,0,185,
        186,1,0,0,0,186,189,1,0,0,0,187,185,1,0,0,0,188,190,5,62,0,0,189,
        188,1,0,0,0,189,190,1,0,0,0,190,191,1,0,0,0,191,192,5,99,0,0,192,
        7,1,0,0,0,193,208,3,20,10,0,194,208,3,26,13,0,195,208,3,28,14,0,
        196,208,3,30,15,0,197,208,3,42,21,0,198,208,3,40,20,0,199,208,3,
        38,19,0,200,208,3,54,27,0,201,208,3,50,25,0,202,208,3,72,36,0,203,
        208,3,22,11,0,204,208,3,62,31,0,205,208,3,64,32,0,206,208,3,74,37,
        0,207,193,1,0,0,0,207,194,1,0,0,0,207,195,1,0,0,0,207,196,1,0,0,
        0,207,197,1,0,0,0,207,198,1,0,0,0,207,199,1,0,0,0,207,200,1,0,0,
        0,207,201,1,0,0,0,207,202,1,0,0,0,207,203,1,0,0,0,207,204,1,0,0,
        0,207,205,1,0,0,0,207,206,1,0,0,0,208,9,1,0,0,0,209,212,3,12,6,0,
        210,212,3,70,35,0,211,209,1,0,0,0,211,210,1,0,0,0,212,11,1,0,0,0,
        213,214,3,16,8,0,214,216,3,142,71,0,215,217,3,14,7,0,216,215,1,0,
        0,0,216,217,1,0,0,0,217,218,1,0,0,0,218,219,5,61,0,0,219,220,3,18,
        9,0,220,13,1,0,0,0,221,222,5,12,0,0,222,223,3,142,71,0,223,15,1,
        0,0,0,224,225,7,0,0,0,225,17,1,0,0,0,226,237,3,6,3,0,227,228,5,99,
        0,0,228,230,5,1,0,0,229,231,3,4,2,0,230,229,1,0,0,0,231,232,1,0,
        0,0,232,230,1,0,0,0,232,233,1,0,0,0,233,234,1,0,0,0,234,235,5,2,
        0,0,235,237,1,0,0,0,236,226,1,0,0,0,236,227,1,0,0,0,237,19,1,0,0,
        0,238,239,5,12,0,0,239,241,3,152,76,0,240,238,1,0,0,0,240,241,1,
        0,0,0,241,242,1,0,0,0,242,243,5,13,0,0,243,244,3,142,71,0,244,21,
        1,0,0,0,245,246,3,140,70,0,246,247,3,146,73,0,247,23,1,0,0,0,248,
        251,3,140,70,0,249,251,3,22,11,0,250,248,1,0,0,0,250,249,1,0,0,0,
        251,25,1,0,0,0,252,253,3,24,12,0,253,254,5,64,0,0,254,255,3,36,18,
        0,255,27,1,0,0,0,256,257,3,24,12,0,257,258,3,32,16,0,258,259,3,34,
        17,0,259,29,1,0,0,0,260,261,3,24,12,0,261,262,7,1,0,0,262,263,3,
        34,17,0,263,31,1,0,0,0,264,265,7,2,0,0,265,33,1,0,0,0,266,269,3,
        122,61,0,267,269,3,98,49,0,268,266,1,0,0,0,268,267,1,0,0,0,269,35,
        1,0,0,0,270,276,3,152,76,0,271,276,3,58,29,0,272,276,3,122,61,0,
        273,276,3,98,49,0,274,276,3,154,77,0,275,270,1,0,0,0,275,271,1,0,
        0,0,275,272,1,0,0,0,275,273,1,0,0,0,275,274,1,0,0,0,276,37,1,0,0,
        0,277,278,3,140,70,0,278,279,5,86,0,0,279,280,3,142,71,0,280,39,
        1,0,0,0,281,282,3,44,22,0,282,285,7,3,0,0,283,286,3,44,22,0,284,
        286,3,40,20,0,285,283,1,0,0,0,285,284,1,0,0,0,286,41,1,0,0,0,287,
        288,3,46,23,0,288,289,5,26,0,0,289,290,3,46,23,0,290,43,1,0,0,0,
        291,292,3,48,24,0,292,45,1,0,0,0,293,294,3,48,24,0,294,47,1,0,0,
        0,295,299,3,140,70,0,296,299,3,50,25,0,297,299,3,52,26,0,298,295,
        1,0,0,0,298,296,1,0,0,0,298,297,1,0,0,0,299,49,1,0,0,0,300,301,5,
        10,0,0,301,302,3,148,74,0,302,51,1,0,0,0,303,304,3,56,28,0,304,53,
        1,0,0,0,305,306,3,56,28,0,306,55,1,0,0,0,307,311,5,9,0,0,308,312,
        3,148,74,0,309,312,3,156,78,0,310,312,3,152,76,0,311,308,1,0,0,0,
        311,309,1,0,0,0,311,310,1,0,0,0,312,57,1,0,0,0,313,314,5,11,0,0,
        314,319,3,142,71,0,315,316,5,65,0,0,316,317,3,60,30,0,317,318,5,
        66,0,0,318,320,1,0,0,0,319,315,1,0,0,0,319,320,1,0,0,0,320,322,1,
        0,0,0,321,323,3,78,39,0,322,321,1,0,0,0,322,323,1,0,0,0,323,59,1,
        0,0,0,324,325,3,156,78,0,325,61,1,0,0,0,326,327,3,152,76,0,327,63,
        1,0,0,0,328,329,5,22,0,0,329,65,1,0,0,0,330,342,5,65,0,0,331,336,
        3,140,70,0,332,333,5,59,0,0,333,335,3,140,70,0,334,332,1,0,0,0,335,
        338,1,0,0,0,336,334,1,0,0,0,336,337,1,0,0,0,337,340,1,0,0,0,338,
        336,1,0,0,0,339,341,5,59,0,0,340,339,1,0,0,0,340,341,1,0,0,0,341,
        343,1,0,0,0,342,331,1,0,0,0,342,343,1,0,0,0,343,344,1,0,0,0,344,
        345,5,66,0,0,345,67,1,0,0,0,346,348,3,140,70,0,347,349,3,110,55,
        0,348,347,1,0,0,0,348,349,1,0,0,0,349,352,1,0,0,0,350,352,3,66,33,
        0,351,346,1,0,0,0,351,350,1,0,0,0,352,69,1,0,0,0,353,354,5,14,0,
        0,354,355,3,148,74,0,355,356,5,15,0,0,356,357,3,68,34,0,357,358,
        5,61,0,0,358,359,3,18,9,0,359,71,1,0,0,0,360,361,5,16,0,0,361,362,
        3,82,41,0,362,73,1,0,0,0,363,365,5,23,0,0,364,366,3,140,70,0,365,
        364,1,0,0,0,365,366,1,0,0,0,366,367,1,0,0,0,367,370,3,142,71,0,368,
        369,5,60,0,0,369,371,3,76,38,0,370,368,1,0,0,0,370,371,1,0,0,0,371,
        373,1,0,0,0,372,374,3,78,39,0,373,372,1,0,0,0,373,374,1,0,0,0,374,
        75,1,0,0,0,375,376,3,148,74,0,376,77,1,0,0,0,377,389,5,78,0,0,378,
        383,3,80,40,0,379,380,5,59,0,0,380,382,3,80,40,0,381,379,1,0,0,0,
        382,385,1,0,0,0,383,381,1,0,0,0,383,384,1,0,0,0,384,387,1,0,0,0,
        385,383,1,0,0,0,386,388,5,59,0,0,387,386,1,0,0,0,387,388,1,0,0,0,
        388,390,1,0,0,0,389,378,1,0,0,0,389,390,1,0,0,0,390,391,1,0,0,0,
        391,392,5,79,0,0,392,79,1,0,0,0,393,394,3,148,74,0,394,395,5,64,
        0,0,395,396,3,150,75,0,396,81,1,0,0,0,397,399,3,98,49,0,398,400,
        3,84,42,0,399,398,1,0,0,0,400,401,1,0,0,0,401,399,1,0,0,0,401,402,
        1,0,0,0,402,83,1,0,0,0,403,410,3,86,43,0,404,410,3,88,44,0,405,410,
        3,90,45,0,406,410,3,92,46,0,407,410,3,94,47,0,408,410,3,96,48,0,
        409,403,1,0,0,0,409,404,1,0,0,0,409,405,1,0,0,0,409,406,1,0,0,0,
        409,407,1,0,0,0,409,408,1,0,0,0,410,85,1,0,0,0,411,412,5,78,0,0,
        412,413,3,98,49,0,413,87,1,0,0,0,414,415,5,79,0,0,415,416,3,98,49,
        0,416,89,1,0,0,0,417,418,5,82,0,0,418,419,3,98,49,0,419,91,1,0,0,
        0,420,421,5,81,0,0,421,422,3,98,49,0,422,93,1,0,0,0,423,424,5,20,
        0,0,424,425,3,98,49,0,425,95,1,0,0,0,426,427,5,21,0,0,427,428,3,
        98,49,0,428,97,1,0,0,0,429,430,6,49,-1,0,430,431,3,100,50,0,431,
        437,1,0,0,0,432,433,10,2,0,0,433,434,7,4,0,0,434,436,3,100,50,0,
        435,432,1,0,0,0,436,439,1,0,0,0,437,435,1,0,0,0,437,438,1,0,0,0,
        438,99,1,0,0,0,439,437,1,0,0,0,440,441,6,50,-1,0,441,442,3,102,51,
        0,442,448,1,0,0,0,443,444,10,2,0,0,444,445,7,5,0,0,445,447,3,102,
        51,0,446,443,1,0,0,0,447,450,1,0,0,0,448,446,1,0,0,0,448,449,1,0,
        0,0,449,101,1,0,0,0,450,448,1,0,0,0,451,452,6,51,-1,0,452,453,3,
        104,52,0,453,459,1,0,0,0,454,455,10,2,0,0,455,456,7,6,0,0,456,458,
        3,104,52,0,457,454,1,0,0,0,458,461,1,0,0,0,459,457,1,0,0,0,459,460,
        1,0,0,0,460,103,1,0,0,0,461,459,1,0,0,0,462,465,3,106,53,0,463,464,
        5,63,0,0,464,466,3,106,53,0,465,463,1,0,0,0,465,466,1,0,0,0,466,
        105,1,0,0,0,467,478,3,108,54,0,468,469,3,148,74,0,469,471,5,57,0,
        0,470,472,3,108,54,0,471,470,1,0,0,0,472,473,1,0,0,0,473,471,1,0,
        0,0,473,474,1,0,0,0,474,475,1,0,0,0,475,476,5,58,0,0,476,478,1,0,
        0,0,477,467,1,0,0,0,477,468,1,0,0,0,478,107,1,0,0,0,479,480,3,118,
        59,0,480,109,1,0,0,0,481,495,5,65,0,0,482,484,3,112,56,0,483,482,
        1,0,0,0,483,484,1,0,0,0,484,485,1,0,0,0,485,487,5,61,0,0,486,488,
        3,114,57,0,487,486,1,0,0,0,487,488,1,0,0,0,488,493,1,0,0,0,489,491,
        5,61,0,0,490,492,3,116,58,0,491,490,1,0,0,0,491,492,1,0,0,0,492,
        494,1,0,0,0,493,489,1,0,0,0,493,494,1,0,0,0,494,496,1,0,0,0,495,
        483,1,0,0,0,495,496,1,0,0,0,496,497,1,0,0,0,497,505,5,66,0,0,498,
        499,5,65,0,0,499,501,5,60,0,0,500,502,3,116,58,0,501,500,1,0,0,0,
        501,502,1,0,0,0,502,503,1,0,0,0,503,505,5,66,0,0,504,481,1,0,0,0,
        504,498,1,0,0,0,505,111,1,0,0,0,506,507,3,158,79,0,507,113,1,0,0,
        0,508,509,3,158,79,0,509,115,1,0,0,0,510,511,3,158,79,0,511,117,
        1,0,0,0,512,516,3,140,70,0,513,516,3,122,61,0,514,516,3,120,60,0,
        515,512,1,0,0,0,515,513,1,0,0,0,515,514,1,0,0,0,516,119,1,0,0,0,
        517,518,5,57,0,0,518,519,3,98,49,0,519,520,5,58,0,0,520,121,1,0,
        0,0,521,525,3,124,62,0,522,525,3,126,63,0,523,525,3,128,64,0,524,
        521,1,0,0,0,524,522,1,0,0,0,524,523,1,0,0,0,525,123,1,0,0,0,526,
        527,3,128,64,0,527,528,5,17,0,0,528,529,3,128,64,0,529,125,1,0,0,
        0,530,531,3,128,64,0,531,532,5,50,0,0,532,533,3,130,65,0,533,127,
        1,0,0,0,534,536,3,160,80,0,535,537,3,148,74,0,536,535,1,0,0,0,536,
        537,1,0,0,0,537,129,1,0,0,0,538,541,3,162,81,0,539,542,5,53,0,0,
        540,542,3,148,74,0,541,539,1,0,0,0,541,540,1,0,0,0,541,542,1,0,0,
        0,542,131,1,0,0,0,543,544,3,158,79,0,544,133,1,0,0,0,545,546,5,65,
        0,0,546,547,3,132,66,0,547,548,5,66,0,0,548,135,1,0,0,0,549,550,
        5,54,0,0,550,551,3,156,78,0,551,137,1,0,0,0,552,554,3,148,74,0,553,
        555,3,134,67,0,554,553,1,0,0,0,554,555,1,0,0,0,555,139,1,0,0,0,556,
        561,3,138,69,0,557,558,5,54,0,0,558,560,3,138,69,0,559,557,1,0,0,
        0,560,563,1,0,0,0,561,559,1,0,0,0,561,562,1,0,0,0,562,565,1,0,0,
        0,563,561,1,0,0,0,564,566,3,136,68,0,565,564,1,0,0,0,565,566,1,0,
        0,0,566,141,1,0,0,0,567,568,3,148,74,0,568,143,1,0,0,0,569,570,3,
        148,74,0,570,145,1,0,0,0,571,572,5,61,0,0,572,573,3,144,72,0,573,
        147,1,0,0,0,574,575,5,41,0,0,575,149,1,0,0,0,576,580,3,152,76,0,
        577,580,3,154,77,0,578,580,3,160,80,0,579,576,1,0,0,0,579,577,1,
        0,0,0,579,578,1,0,0,0,580,151,1,0,0,0,581,582,5,3,0,0,582,153,1,
        0,0,0,583,584,7,7,0,0,584,155,1,0,0,0,585,586,3,162,81,0,586,157,
        1,0,0,0,587,588,3,160,80,0,588,159,1,0,0,0,589,591,7,5,0,0,590,589,
        1,0,0,0,590,591,1,0,0,0,591,592,1,0,0,0,592,593,3,162,81,0,593,161,
        1,0,0,0,594,595,5,4,0,0,595,163,1,0,0,0,54,166,168,178,185,189,207,
        211,216,232,236,240,250,268,275,285,298,311,319,322,336,340,342,
        348,351,365,370,373,383,387,389,401,409,437,448,459,465,473,477,
        483,487,491,493,495,501,504,515,524,536,541,554,561,565,579,590
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
    RULE_mif = 23
    RULE_connectable = 24
    RULE_signaldef_stmt = 25
    RULE_pindef_stmt = 26
    RULE_pin_declaration = 27
    RULE_pin_stmt = 28
    RULE_new_stmt = 29
    RULE_new_count = 30
    RULE_string_stmt = 31
    RULE_pass_stmt = 32
    RULE_list_literal_of_field_references = 33
    RULE_iterable_references = 34
    RULE_for_stmt = 35
    RULE_assert_stmt = 36
    RULE_trait_stmt = 37
    RULE_constructor = 38
    RULE_template = 39
    RULE_template_arg = 40
    RULE_comparison = 41
    RULE_compare_op_pair = 42
    RULE_lt_arithmetic_or = 43
    RULE_gt_arithmetic_or = 44
    RULE_lt_eq_arithmetic_or = 45
    RULE_gt_eq_arithmetic_or = 46
    RULE_in_arithmetic_or = 47
    RULE_is_arithmetic_or = 48
    RULE_arithmetic_expression = 49
    RULE_sum = 50
    RULE_term = 51
    RULE_power = 52
    RULE_functional = 53
    RULE_bound = 54
    RULE_slice = 55
    RULE_slice_start = 56
    RULE_slice_stop = 57
    RULE_slice_step = 58
    RULE_atom = 59
    RULE_arithmetic_group = 60
    RULE_literal_physical = 61
    RULE_bound_quantity = 62
    RULE_bilateral_quantity = 63
    RULE_quantity = 64
    RULE_bilateral_tolerance = 65
    RULE_key = 66
    RULE_array_index = 67
    RULE_pin_reference_end = 68
    RULE_field_reference_part = 69
    RULE_field_reference = 70
    RULE_type_reference = 71
    RULE_unit = 72
    RULE_type_info = 73
    RULE_name = 74
    RULE_literal = 75
    RULE_string = 76
    RULE_boolean_ = 77
    RULE_number_hint_natural = 78
    RULE_number_hint_integer = 79
    RULE_number = 80
    RULE_number_signless = 81

    ruleNames =  [ "file_input", "pragma_stmt", "stmt", "simple_stmts", 
                   "simple_stmt", "compound_stmt", "blockdef", "blockdef_super", 
                   "blocktype", "block", "import_stmt", "declaration_stmt", 
                   "field_reference_or_declaration", "assign_stmt", "cum_assign_stmt", 
                   "set_assign_stmt", "cum_operator", "cum_assignable", 
                   "assignable", "retype_stmt", "directed_connect_stmt", 
                   "connect_stmt", "bridgeable", "mif", "connectable", "signaldef_stmt", 
                   "pindef_stmt", "pin_declaration", "pin_stmt", "new_stmt", 
                   "new_count", "string_stmt", "pass_stmt", "list_literal_of_field_references", 
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
            self.state = 168
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 2199035934664) != 0) or _la==99 or _la==100:
                self.state = 166
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [99]:
                    self.state = 164
                    self.match(AtoParser.NEWLINE)
                    pass
                elif token in [3, 6, 7, 8, 9, 10, 12, 13, 14, 16, 22, 23, 41, 100]:
                    self.state = 165
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 170
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 171
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
            self.state = 173
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
            self.state = 178
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 16, 22, 23, 41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 175
                self.simple_stmts()
                pass
            elif token in [6, 7, 8, 14]:
                self.enterOuterAlt(localctx, 2)
                self.state = 176
                self.compound_stmt()
                pass
            elif token in [100]:
                self.enterOuterAlt(localctx, 3)
                self.state = 177
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
            self.state = 180
            self.simple_stmt()
            self.state = 185
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 181
                    self.match(AtoParser.SEMI_COLON)
                    self.state = 182
                    self.simple_stmt() 
                self.state = 187
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 189
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==62:
                self.state = 188
                self.match(AtoParser.SEMI_COLON)


            self.state = 191
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
            self.state = 207
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 193
                self.import_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 194
                self.assign_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 195
                self.cum_assign_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 196
                self.set_assign_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 197
                self.connect_stmt()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 198
                self.directed_connect_stmt()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 199
                self.retype_stmt()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 200
                self.pin_declaration()
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 201
                self.signaldef_stmt()
                pass

            elif la_ == 10:
                self.enterOuterAlt(localctx, 10)
                self.state = 202
                self.assert_stmt()
                pass

            elif la_ == 11:
                self.enterOuterAlt(localctx, 11)
                self.state = 203
                self.declaration_stmt()
                pass

            elif la_ == 12:
                self.enterOuterAlt(localctx, 12)
                self.state = 204
                self.string_stmt()
                pass

            elif la_ == 13:
                self.enterOuterAlt(localctx, 13)
                self.state = 205
                self.pass_stmt()
                pass

            elif la_ == 14:
                self.enterOuterAlt(localctx, 14)
                self.state = 206
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
            self.state = 211
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [6, 7, 8]:
                self.enterOuterAlt(localctx, 1)
                self.state = 209
                self.blockdef()
                pass
            elif token in [14]:
                self.enterOuterAlt(localctx, 2)
                self.state = 210
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
            self.state = 213
            self.blocktype()
            self.state = 214
            self.type_reference()
            self.state = 216
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 215
                self.blockdef_super()


            self.state = 218
            self.match(AtoParser.COLON)
            self.state = 219
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
            self.state = 221
            self.match(AtoParser.FROM)
            self.state = 222
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
            self.state = 224
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
            self.state = 236
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 16, 22, 23, 41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 226
                self.simple_stmts()
                pass
            elif token in [99]:
                self.enterOuterAlt(localctx, 2)
                self.state = 227
                self.match(AtoParser.NEWLINE)
                self.state = 228
                self.match(AtoParser.INDENT)
                self.state = 230 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 229
                    self.stmt()
                    self.state = 232 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 2199035934664) != 0) or _la==100):
                        break

                self.state = 234
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
            self.state = 240
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 238
                self.match(AtoParser.FROM)
                self.state = 239
                self.string()


            self.state = 242
            self.match(AtoParser.IMPORT)
            self.state = 243
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
            self.state = 245
            self.field_reference()
            self.state = 246
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
            self.state = 250
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,11,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 248
                self.field_reference()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 249
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
            self.state = 252
            self.field_reference_or_declaration()
            self.state = 253
            self.match(AtoParser.ASSIGN)
            self.state = 254
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
            self.state = 256
            self.field_reference_or_declaration()
            self.state = 257
            self.cum_operator()
            self.state = 258
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
            self.state = 260
            self.field_reference_or_declaration()
            self.state = 261
            _la = self._input.LA(1)
            if not(_la==92 or _la==93):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 262
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
            self.state = 264
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
        self.enterRule(localctx, 34, self.RULE_cum_assignable)
        try:
            self.state = 268
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 266
                self.literal_physical()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 267
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
            self.state = 275
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 270
                self.string()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 271
                self.new_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 272
                self.literal_physical()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 273
                self.arithmetic_expression(0)
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 274
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
            self.state = 277
            self.field_reference()
            self.state = 278
            self.match(AtoParser.ARROW)
            self.state = 279
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
        self.enterRule(localctx, 40, self.RULE_directed_connect_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 281
            self.bridgeable()
            self.state = 282
            _la = self._input.LA(1)
            if not(_la==24 or _la==25):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 285
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.state = 283
                self.bridgeable()
                pass

            elif la_ == 2:
                self.state = 284
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
        self.enterRule(localctx, 42, self.RULE_connect_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 287
            self.mif()
            self.state = 288
            self.match(AtoParser.WIRE)
            self.state = 289
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
        self.enterRule(localctx, 44, self.RULE_bridgeable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 291
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
        self.enterRule(localctx, 46, self.RULE_mif)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 293
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
        self.enterRule(localctx, 48, self.RULE_connectable)
        try:
            self.state = 298
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 295
                self.field_reference()
                pass
            elif token in [10]:
                self.enterOuterAlt(localctx, 2)
                self.state = 296
                self.signaldef_stmt()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 3)
                self.state = 297
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
            self.state = 300
            self.match(AtoParser.SIGNAL)
            self.state = 301
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
            self.state = 303
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
            self.state = 305
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
            self.state = 307
            self.match(AtoParser.PIN)
            self.state = 311
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41]:
                self.state = 308
                self.name()
                pass
            elif token in [4]:
                self.state = 309
                self.number_hint_natural()
                pass
            elif token in [3]:
                self.state = 310
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
        self.enterRule(localctx, 58, self.RULE_new_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 313
            self.match(AtoParser.NEW)
            self.state = 314
            self.type_reference()
            self.state = 319
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==65:
                self.state = 315
                self.match(AtoParser.OPEN_BRACK)
                self.state = 316
                self.new_count()
                self.state = 317
                self.match(AtoParser.CLOSE_BRACK)


            self.state = 322
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==78:
                self.state = 321
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
        self.enterRule(localctx, 60, self.RULE_new_count)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 324
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
            self.state = 326
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
            self.state = 328
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
        self.enterRule(localctx, 66, self.RULE_list_literal_of_field_references)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 330
            self.match(AtoParser.OPEN_BRACK)
            self.state = 342
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==41:
                self.state = 331
                self.field_reference()
                self.state = 336
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,19,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 332
                        self.match(AtoParser.COMMA)
                        self.state = 333
                        self.field_reference() 
                    self.state = 338
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,19,self._ctx)

                self.state = 340
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==59:
                    self.state = 339
                    self.match(AtoParser.COMMA)




            self.state = 344
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
        self.enterRule(localctx, 68, self.RULE_iterable_references)
        self._la = 0 # Token type
        try:
            self.state = 351
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 346
                self.field_reference()
                self.state = 348
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==65:
                    self.state = 347
                    self.slice_()


                pass
            elif token in [65]:
                self.enterOuterAlt(localctx, 2)
                self.state = 350
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
        self.enterRule(localctx, 70, self.RULE_for_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 353
            self.match(AtoParser.FOR)
            self.state = 354
            self.name()
            self.state = 355
            self.match(AtoParser.IN)
            self.state = 356
            self.iterable_references()
            self.state = 357
            self.match(AtoParser.COLON)
            self.state = 358
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
        self.enterRule(localctx, 72, self.RULE_assert_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 360
            self.match(AtoParser.ASSERT)
            self.state = 361
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
        self.enterRule(localctx, 74, self.RULE_trait_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 363
            self.match(AtoParser.TRAIT)
            self.state = 365
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,24,self._ctx)
            if la_ == 1:
                self.state = 364
                self.field_reference()


            self.state = 367
            self.type_reference()
            self.state = 370
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==60:
                self.state = 368
                self.match(AtoParser.DOUBLE_COLON)
                self.state = 369
                self.constructor()


            self.state = 373
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==78:
                self.state = 372
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
        self.enterRule(localctx, 76, self.RULE_constructor)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 375
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
        self.enterRule(localctx, 78, self.RULE_template)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 377
            self.match(AtoParser.LESS_THAN)
            self.state = 389
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==41:
                self.state = 378
                self.template_arg()
                self.state = 383
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,27,self._ctx)
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt==1:
                        self.state = 379
                        self.match(AtoParser.COMMA)
                        self.state = 380
                        self.template_arg() 
                    self.state = 385
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,27,self._ctx)

                self.state = 387
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==59:
                    self.state = 386
                    self.match(AtoParser.COMMA)




            self.state = 391
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
        self.enterRule(localctx, 80, self.RULE_template_arg)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 393
            self.name()
            self.state = 394
            self.match(AtoParser.ASSIGN)
            self.state = 395
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
        self.enterRule(localctx, 82, self.RULE_comparison)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 397
            self.arithmetic_expression(0)
            self.state = 399 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 398
                self.compare_op_pair()
                self.state = 401 
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
        self.enterRule(localctx, 84, self.RULE_compare_op_pair)
        try:
            self.state = 409
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [78]:
                self.enterOuterAlt(localctx, 1)
                self.state = 403
                self.lt_arithmetic_or()
                pass
            elif token in [79]:
                self.enterOuterAlt(localctx, 2)
                self.state = 404
                self.gt_arithmetic_or()
                pass
            elif token in [82]:
                self.enterOuterAlt(localctx, 3)
                self.state = 405
                self.lt_eq_arithmetic_or()
                pass
            elif token in [81]:
                self.enterOuterAlt(localctx, 4)
                self.state = 406
                self.gt_eq_arithmetic_or()
                pass
            elif token in [20]:
                self.enterOuterAlt(localctx, 5)
                self.state = 407
                self.in_arithmetic_or()
                pass
            elif token in [21]:
                self.enterOuterAlt(localctx, 6)
                self.state = 408
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
        self.enterRule(localctx, 86, self.RULE_lt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 411
            self.match(AtoParser.LESS_THAN)
            self.state = 412
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
        self.enterRule(localctx, 88, self.RULE_gt_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 414
            self.match(AtoParser.GREATER_THAN)
            self.state = 415
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
        self.enterRule(localctx, 90, self.RULE_lt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 417
            self.match(AtoParser.LT_EQ)
            self.state = 418
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
        self.enterRule(localctx, 92, self.RULE_gt_eq_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 420
            self.match(AtoParser.GT_EQ)
            self.state = 421
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
        self.enterRule(localctx, 94, self.RULE_in_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 423
            self.match(AtoParser.WITHIN)
            self.state = 424
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
        self.enterRule(localctx, 96, self.RULE_is_arithmetic_or)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 426
            self.match(AtoParser.IS)
            self.state = 427
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
        _startState = 98
        self.enterRecursionRule(localctx, 98, self.RULE_arithmetic_expression, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 430
            self.sum_(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 437
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,32,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.Arithmetic_expressionContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmetic_expression)
                    self.state = 432
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 433
                    _la = self._input.LA(1)
                    if not(_la==67 or _la==69):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 434
                    self.sum_(0) 
                self.state = 439
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
        _startState = 100
        self.enterRecursionRule(localctx, 100, self.RULE_sum, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 441
            self.term(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 448
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,33,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.SumContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_sum)
                    self.state = 443
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 444
                    _la = self._input.LA(1)
                    if not(_la==72 or _la==73):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 445
                    self.term(0) 
                self.state = 450
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
        _startState = 102
        self.enterRecursionRule(localctx, 102, self.RULE_term, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 452
            self.power()
            self._ctx.stop = self._input.LT(-1)
            self.state = 459
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,34,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.TermContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_term)
                    self.state = 454
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 455
                    _la = self._input.LA(1)
                    if not(_la==56 or _la==74):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 456
                    self.power() 
                self.state = 461
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
        self.enterRule(localctx, 104, self.RULE_power)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 462
            self.functional()
            self.state = 465
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,35,self._ctx)
            if la_ == 1:
                self.state = 463
                self.match(AtoParser.POWER)
                self.state = 464
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
        self.enterRule(localctx, 106, self.RULE_functional)
        self._la = 0 # Token type
        try:
            self.state = 477
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,37,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 467
                self.bound()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 468
                self.name()
                self.state = 469
                self.match(AtoParser.OPEN_PAREN)
                self.state = 471 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 470
                    self.bound()
                    self.state = 473 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 144117387099111440) != 0) or _la==72 or _la==73):
                        break

                self.state = 475
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
        self.enterRule(localctx, 108, self.RULE_bound)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 479
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
        self.enterRule(localctx, 110, self.RULE_slice)
        self._la = 0 # Token type
        try:
            self.state = 504
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,44,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 481
                self.match(AtoParser.OPEN_BRACK)
                self.state = 495
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4 or _la==61 or _la==72 or _la==73:
                    self.state = 483
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if _la==4 or _la==72 or _la==73:
                        self.state = 482
                        self.slice_start()


                    self.state = 485
                    self.match(AtoParser.COLON)
                    self.state = 487
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if _la==4 or _la==72 or _la==73:
                        self.state = 486
                        self.slice_stop()


                    self.state = 493
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if _la==61:
                        self.state = 489
                        self.match(AtoParser.COLON)
                        self.state = 491
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)
                        if _la==4 or _la==72 or _la==73:
                            self.state = 490
                            self.slice_step()






                self.state = 497
                self.match(AtoParser.CLOSE_BRACK)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 498
                self.match(AtoParser.OPEN_BRACK)

                self.state = 499
                self.match(AtoParser.DOUBLE_COLON)
                self.state = 501
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4 or _la==72 or _la==73:
                    self.state = 500
                    self.slice_step()


                self.state = 503
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
        self.enterRule(localctx, 112, self.RULE_slice_start)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 506
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
        self.enterRule(localctx, 114, self.RULE_slice_stop)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 508
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
        self.enterRule(localctx, 116, self.RULE_slice_step)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 510
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
        self.enterRule(localctx, 118, self.RULE_atom)
        try:
            self.state = 515
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [41]:
                self.enterOuterAlt(localctx, 1)
                self.state = 512
                self.field_reference()
                pass
            elif token in [4, 72, 73]:
                self.enterOuterAlt(localctx, 2)
                self.state = 513
                self.literal_physical()
                pass
            elif token in [57]:
                self.enterOuterAlt(localctx, 3)
                self.state = 514
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
        self.enterRule(localctx, 120, self.RULE_arithmetic_group)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 517
            self.match(AtoParser.OPEN_PAREN)
            self.state = 518
            self.arithmetic_expression(0)
            self.state = 519
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
        self.enterRule(localctx, 122, self.RULE_literal_physical)
        try:
            self.state = 524
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,46,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 521
                self.bound_quantity()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 522
                self.bilateral_quantity()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 523
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
        self.enterRule(localctx, 124, self.RULE_bound_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 526
            self.quantity()
            self.state = 527
            self.match(AtoParser.TO)
            self.state = 528
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
        self.enterRule(localctx, 126, self.RULE_bilateral_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 530
            self.quantity()
            self.state = 531
            self.match(AtoParser.PLUS_OR_MINUS)
            self.state = 532
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
        self.enterRule(localctx, 128, self.RULE_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 534
            self.number()
            self.state = 536
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,47,self._ctx)
            if la_ == 1:
                self.state = 535
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
        self.enterRule(localctx, 130, self.RULE_bilateral_tolerance)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 538
            self.number_signless()
            self.state = 541
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,48,self._ctx)
            if la_ == 1:
                self.state = 539
                self.match(AtoParser.PERCENT)

            elif la_ == 2:
                self.state = 540
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
        self.enterRule(localctx, 132, self.RULE_key)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 543
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
        self.enterRule(localctx, 134, self.RULE_array_index)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 545
            self.match(AtoParser.OPEN_BRACK)
            self.state = 546
            self.key()
            self.state = 547
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
        self.enterRule(localctx, 136, self.RULE_pin_reference_end)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 549
            self.match(AtoParser.DOT)
            self.state = 550
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
        self.enterRule(localctx, 138, self.RULE_field_reference_part)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 552
            self.name()
            self.state = 554
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,49,self._ctx)
            if la_ == 1:
                self.state = 553
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
        self.enterRule(localctx, 140, self.RULE_field_reference)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 556
            self.field_reference_part()
            self.state = 561
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,50,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 557
                    self.match(AtoParser.DOT)
                    self.state = 558
                    self.field_reference_part() 
                self.state = 563
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,50,self._ctx)

            self.state = 565
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,51,self._ctx)
            if la_ == 1:
                self.state = 564
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
        self.enterRule(localctx, 142, self.RULE_type_reference)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 567
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
        self.enterRule(localctx, 144, self.RULE_unit)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 569
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
        self.enterRule(localctx, 146, self.RULE_type_info)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 571
            self.match(AtoParser.COLON)
            self.state = 572
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
        self.enterRule(localctx, 148, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 574
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
        self.enterRule(localctx, 150, self.RULE_literal)
        try:
            self.state = 579
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3]:
                self.enterOuterAlt(localctx, 1)
                self.state = 576
                self.string()
                pass
            elif token in [18, 19]:
                self.enterOuterAlt(localctx, 2)
                self.state = 577
                self.boolean_()
                pass
            elif token in [4, 72, 73]:
                self.enterOuterAlt(localctx, 3)
                self.state = 578
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
        self.enterRule(localctx, 152, self.RULE_string)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 581
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
        self.enterRule(localctx, 154, self.RULE_boolean_)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 583
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
        self.enterRule(localctx, 156, self.RULE_number_hint_natural)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 585
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
        self.enterRule(localctx, 158, self.RULE_number_hint_integer)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 587
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
        self.enterRule(localctx, 160, self.RULE_number)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 590
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==72 or _la==73:
                self.state = 589
                _la = self._input.LA(1)
                if not(_la==72 or _la==73):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()


            self.state = 592
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
        self.enterRule(localctx, 162, self.RULE_number_signless)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 594
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
        self._predicates[49] = self.arithmetic_expression_sempred
        self._predicates[50] = self.sum_sempred
        self._predicates[51] = self.term_sempred
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
         




