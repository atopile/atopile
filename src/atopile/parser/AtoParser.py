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
        4,1,89,528,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
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
        7,72,2,73,7,73,1,0,1,0,5,0,151,8,0,10,0,12,0,154,9,0,1,0,1,0,1,1,
        1,1,1,2,1,2,1,2,3,2,163,8,2,1,3,1,3,1,3,5,3,168,8,3,10,3,12,3,171,
        9,3,1,3,3,3,174,8,3,1,3,1,3,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,
        1,4,1,4,1,4,1,4,1,4,1,4,3,4,193,8,4,1,5,1,5,3,5,197,8,5,1,6,1,6,
        1,6,3,6,202,8,6,1,6,1,6,1,6,1,7,1,7,1,7,1,8,1,8,1,9,1,9,1,9,1,9,
        4,9,216,8,9,11,9,12,9,217,1,9,1,9,3,9,222,8,9,1,10,1,10,1,10,1,10,
        1,10,1,11,1,11,3,11,231,8,11,1,11,1,11,1,11,1,11,5,11,237,8,11,10,
        11,12,11,240,9,11,1,12,1,12,1,12,1,13,1,13,3,13,247,8,13,1,14,1,
        14,1,14,1,14,1,15,1,15,1,15,1,15,1,16,1,16,1,16,1,16,1,17,1,17,1,
        18,1,18,3,18,265,8,18,1,19,1,19,1,19,1,19,1,19,3,19,272,8,19,1,20,
        1,20,1,20,1,20,1,21,1,21,1,21,4,21,281,8,21,11,21,12,21,282,1,22,
        1,22,1,22,1,22,1,23,1,23,1,24,1,24,1,25,1,25,1,25,3,25,296,8,25,
        1,26,1,26,1,26,1,27,1,27,1,28,1,28,1,29,1,29,1,29,1,29,3,29,309,
        8,29,1,30,1,30,1,30,1,30,1,30,1,30,3,30,317,8,30,1,31,1,31,1,32,
        1,32,1,33,1,33,1,34,1,34,1,34,1,34,1,34,3,34,330,8,34,1,34,1,34,
        1,34,1,35,1,35,1,35,1,36,1,36,1,36,1,37,1,37,4,37,343,8,37,11,37,
        12,37,344,1,38,1,38,1,38,1,38,1,38,1,38,3,38,353,8,38,1,39,1,39,
        1,39,1,40,1,40,1,40,1,41,1,41,1,41,1,42,1,42,1,42,1,43,1,43,1,43,
        1,44,1,44,1,44,1,45,1,45,1,45,1,45,1,45,1,45,5,45,379,8,45,10,45,
        12,45,382,9,45,1,46,1,46,1,46,1,46,1,46,1,46,5,46,390,8,46,10,46,
        12,46,393,9,46,1,47,1,47,1,47,1,47,1,47,1,47,5,47,401,8,47,10,47,
        12,47,404,9,47,1,48,1,48,1,48,3,48,409,8,48,1,49,1,49,1,49,1,49,
        4,49,415,8,49,11,49,12,49,416,1,49,1,49,3,49,421,8,49,1,50,1,50,
        1,51,1,51,3,51,427,8,51,1,51,1,51,3,51,431,8,51,1,51,1,51,3,51,435,
        8,51,3,51,437,8,51,3,51,439,8,51,1,51,1,51,1,52,1,52,1,52,3,52,446,
        8,52,1,53,1,53,1,53,1,53,1,54,1,54,1,54,3,54,455,8,54,1,55,1,55,
        1,55,1,55,1,56,1,56,1,56,1,56,1,57,1,57,3,57,467,8,57,1,58,1,58,
        1,58,3,58,472,8,58,1,59,1,59,1,60,1,60,1,60,1,60,1,61,1,61,1,61,
        1,62,1,62,3,62,485,8,62,1,63,1,63,1,63,5,63,490,8,63,10,63,12,63,
        493,9,63,1,63,3,63,496,8,63,1,64,1,64,1,64,5,64,501,8,64,10,64,12,
        64,504,9,64,1,65,1,65,1,66,1,66,1,66,1,67,1,67,1,68,1,68,1,69,1,
        69,1,70,1,70,1,71,1,71,1,72,3,72,522,8,72,1,72,1,72,1,73,1,73,1,
        73,0,3,90,92,94,74,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,
        34,36,38,40,42,44,46,48,50,52,54,56,58,60,62,64,66,68,70,72,74,76,
        78,80,82,84,86,88,90,92,94,96,98,100,102,104,106,108,110,112,114,
        116,118,120,122,124,126,128,130,132,134,136,138,140,142,144,146,
        0,8,1,0,6,8,1,0,77,78,1,0,72,73,1,0,24,25,2,0,52,52,54,54,1,0,57,
        58,2,0,42,42,59,59,1,0,18,19,521,0,152,1,0,0,0,2,157,1,0,0,0,4,162,
        1,0,0,0,6,164,1,0,0,0,8,192,1,0,0,0,10,196,1,0,0,0,12,198,1,0,0,
        0,14,206,1,0,0,0,16,209,1,0,0,0,18,221,1,0,0,0,20,223,1,0,0,0,22,
        230,1,0,0,0,24,241,1,0,0,0,26,246,1,0,0,0,28,248,1,0,0,0,30,252,
        1,0,0,0,32,256,1,0,0,0,34,260,1,0,0,0,36,264,1,0,0,0,38,271,1,0,
        0,0,40,273,1,0,0,0,42,277,1,0,0,0,44,284,1,0,0,0,46,288,1,0,0,0,
        48,290,1,0,0,0,50,295,1,0,0,0,52,297,1,0,0,0,54,300,1,0,0,0,56,302,
        1,0,0,0,58,304,1,0,0,0,60,310,1,0,0,0,62,318,1,0,0,0,64,320,1,0,
        0,0,66,322,1,0,0,0,68,324,1,0,0,0,70,334,1,0,0,0,72,337,1,0,0,0,
        74,340,1,0,0,0,76,352,1,0,0,0,78,354,1,0,0,0,80,357,1,0,0,0,82,360,
        1,0,0,0,84,363,1,0,0,0,86,366,1,0,0,0,88,369,1,0,0,0,90,372,1,0,
        0,0,92,383,1,0,0,0,94,394,1,0,0,0,96,405,1,0,0,0,98,420,1,0,0,0,
        100,422,1,0,0,0,102,424,1,0,0,0,104,445,1,0,0,0,106,447,1,0,0,0,
        108,454,1,0,0,0,110,456,1,0,0,0,112,460,1,0,0,0,114,464,1,0,0,0,
        116,468,1,0,0,0,118,473,1,0,0,0,120,475,1,0,0,0,122,479,1,0,0,0,
        124,482,1,0,0,0,126,486,1,0,0,0,128,497,1,0,0,0,130,505,1,0,0,0,
        132,507,1,0,0,0,134,510,1,0,0,0,136,512,1,0,0,0,138,514,1,0,0,0,
        140,516,1,0,0,0,142,518,1,0,0,0,144,521,1,0,0,0,146,525,1,0,0,0,
        148,151,5,84,0,0,149,151,3,4,2,0,150,148,1,0,0,0,150,149,1,0,0,0,
        151,154,1,0,0,0,152,150,1,0,0,0,152,153,1,0,0,0,153,155,1,0,0,0,
        154,152,1,0,0,0,155,156,5,0,0,1,156,1,1,0,0,0,157,158,5,85,0,0,158,
        3,1,0,0,0,159,163,3,6,3,0,160,163,3,10,5,0,161,163,3,2,1,0,162,159,
        1,0,0,0,162,160,1,0,0,0,162,161,1,0,0,0,163,5,1,0,0,0,164,169,3,
        8,4,0,165,166,5,47,0,0,166,168,3,8,4,0,167,165,1,0,0,0,168,171,1,
        0,0,0,169,167,1,0,0,0,169,170,1,0,0,0,170,173,1,0,0,0,171,169,1,
        0,0,0,172,174,5,47,0,0,173,172,1,0,0,0,173,174,1,0,0,0,174,175,1,
        0,0,0,175,176,5,84,0,0,176,7,1,0,0,0,177,193,3,22,11,0,178,193,3,
        20,10,0,179,193,3,28,14,0,180,193,3,30,15,0,181,193,3,32,16,0,182,
        193,3,44,22,0,183,193,3,42,21,0,184,193,3,40,20,0,185,193,3,56,28,
        0,186,193,3,52,26,0,187,193,3,70,35,0,188,193,3,24,12,0,189,193,
        3,64,32,0,190,193,3,66,33,0,191,193,3,72,36,0,192,177,1,0,0,0,192,
        178,1,0,0,0,192,179,1,0,0,0,192,180,1,0,0,0,192,181,1,0,0,0,192,
        182,1,0,0,0,192,183,1,0,0,0,192,184,1,0,0,0,192,185,1,0,0,0,192,
        186,1,0,0,0,192,187,1,0,0,0,192,188,1,0,0,0,192,189,1,0,0,0,192,
        190,1,0,0,0,192,191,1,0,0,0,193,9,1,0,0,0,194,197,3,12,6,0,195,197,
        3,68,34,0,196,194,1,0,0,0,196,195,1,0,0,0,197,11,1,0,0,0,198,199,
        3,16,8,0,199,201,3,134,67,0,200,202,3,14,7,0,201,200,1,0,0,0,201,
        202,1,0,0,0,202,203,1,0,0,0,203,204,5,46,0,0,204,205,3,18,9,0,205,
        13,1,0,0,0,206,207,5,12,0,0,207,208,3,128,64,0,208,15,1,0,0,0,209,
        210,7,0,0,0,210,17,1,0,0,0,211,222,3,6,3,0,212,213,5,84,0,0,213,
        215,5,1,0,0,214,216,3,4,2,0,215,214,1,0,0,0,216,217,1,0,0,0,217,
        215,1,0,0,0,217,218,1,0,0,0,218,219,1,0,0,0,219,220,5,2,0,0,220,
        222,1,0,0,0,221,211,1,0,0,0,221,212,1,0,0,0,222,19,1,0,0,0,223,224,
        5,13,0,0,224,225,3,128,64,0,225,226,5,12,0,0,226,227,3,136,68,0,
        227,21,1,0,0,0,228,229,5,12,0,0,229,231,3,136,68,0,230,228,1,0,0,
        0,230,231,1,0,0,0,231,232,1,0,0,0,232,233,5,13,0,0,233,238,3,128,
        64,0,234,235,5,45,0,0,235,237,3,128,64,0,236,234,1,0,0,0,237,240,
        1,0,0,0,238,236,1,0,0,0,238,239,1,0,0,0,239,23,1,0,0,0,240,238,1,
        0,0,0,241,242,3,126,63,0,242,243,3,132,66,0,243,25,1,0,0,0,244,247,
        3,126,63,0,245,247,3,24,12,0,246,244,1,0,0,0,246,245,1,0,0,0,247,
        27,1,0,0,0,248,249,3,26,13,0,249,250,5,49,0,0,250,251,3,38,19,0,
        251,29,1,0,0,0,252,253,3,26,13,0,253,254,3,34,17,0,254,255,3,36,
        18,0,255,31,1,0,0,0,256,257,3,26,13,0,257,258,7,1,0,0,258,259,3,
        36,18,0,259,33,1,0,0,0,260,261,7,2,0,0,261,35,1,0,0,0,262,265,3,
        108,54,0,263,265,3,90,45,0,264,262,1,0,0,0,264,263,1,0,0,0,265,37,
        1,0,0,0,266,272,3,136,68,0,267,272,3,60,30,0,268,272,3,108,54,0,
        269,272,3,90,45,0,270,272,3,138,69,0,271,266,1,0,0,0,271,267,1,0,
        0,0,271,268,1,0,0,0,271,269,1,0,0,0,271,270,1,0,0,0,272,39,1,0,0,
        0,273,274,3,126,63,0,274,275,5,71,0,0,275,276,3,128,64,0,276,41,
        1,0,0,0,277,280,3,46,23,0,278,279,7,3,0,0,279,281,3,46,23,0,280,
        278,1,0,0,0,281,282,1,0,0,0,282,280,1,0,0,0,282,283,1,0,0,0,283,
        43,1,0,0,0,284,285,3,48,24,0,285,286,5,26,0,0,286,287,3,48,24,0,
        287,45,1,0,0,0,288,289,3,50,25,0,289,47,1,0,0,0,290,291,3,50,25,
        0,291,49,1,0,0,0,292,296,3,126,63,0,293,296,3,52,26,0,294,296,3,
        54,27,0,295,292,1,0,0,0,295,293,1,0,0,0,295,294,1,0,0,0,296,51,1,
        0,0,0,297,298,5,10,0,0,298,299,3,134,67,0,299,53,1,0,0,0,300,301,
        3,58,29,0,301,55,1,0,0,0,302,303,3,58,29,0,303,57,1,0,0,0,304,308,
        5,9,0,0,305,309,3,134,67,0,306,309,3,140,70,0,307,309,3,136,68,0,
        308,305,1,0,0,0,308,306,1,0,0,0,308,307,1,0,0,0,309,59,1,0,0,0,310,
        311,5,11,0,0,311,316,3,128,64,0,312,313,5,50,0,0,313,314,3,62,31,
        0,314,315,5,51,0,0,315,317,1,0,0,0,316,312,1,0,0,0,316,317,1,0,0,
        0,317,61,1,0,0,0,318,319,3,140,70,0,319,63,1,0,0,0,320,321,3,136,
        68,0,321,65,1,0,0,0,322,323,5,22,0,0,323,67,1,0,0,0,324,325,5,14,
        0,0,325,326,3,134,67,0,326,327,5,15,0,0,327,329,3,126,63,0,328,330,
        3,102,51,0,329,328,1,0,0,0,329,330,1,0,0,0,330,331,1,0,0,0,331,332,
        5,46,0,0,332,333,3,18,9,0,333,69,1,0,0,0,334,335,5,16,0,0,335,336,
        3,74,37,0,336,71,1,0,0,0,337,338,5,23,0,0,338,339,3,128,64,0,339,
        73,1,0,0,0,340,342,3,90,45,0,341,343,3,76,38,0,342,341,1,0,0,0,343,
        344,1,0,0,0,344,342,1,0,0,0,344,345,1,0,0,0,345,75,1,0,0,0,346,353,
        3,78,39,0,347,353,3,80,40,0,348,353,3,82,41,0,349,353,3,84,42,0,
        350,353,3,86,43,0,351,353,3,88,44,0,352,346,1,0,0,0,352,347,1,0,
        0,0,352,348,1,0,0,0,352,349,1,0,0,0,352,350,1,0,0,0,352,351,1,0,
        0,0,353,77,1,0,0,0,354,355,5,63,0,0,355,356,3,90,45,0,356,79,1,0,
        0,0,357,358,5,64,0,0,358,359,3,90,45,0,359,81,1,0,0,0,360,361,5,
        67,0,0,361,362,3,90,45,0,362,83,1,0,0,0,363,364,5,66,0,0,364,365,
        3,90,45,0,365,85,1,0,0,0,366,367,5,20,0,0,367,368,3,90,45,0,368,
        87,1,0,0,0,369,370,5,21,0,0,370,371,3,90,45,0,371,89,1,0,0,0,372,
        373,6,45,-1,0,373,374,3,92,46,0,374,380,1,0,0,0,375,376,10,2,0,0,
        376,377,7,4,0,0,377,379,3,92,46,0,378,375,1,0,0,0,379,382,1,0,0,
        0,380,378,1,0,0,0,380,381,1,0,0,0,381,91,1,0,0,0,382,380,1,0,0,0,
        383,384,6,46,-1,0,384,385,3,94,47,0,385,391,1,0,0,0,386,387,10,2,
        0,0,387,388,7,5,0,0,388,390,3,94,47,0,389,386,1,0,0,0,390,393,1,
        0,0,0,391,389,1,0,0,0,391,392,1,0,0,0,392,93,1,0,0,0,393,391,1,0,
        0,0,394,395,6,47,-1,0,395,396,3,96,48,0,396,402,1,0,0,0,397,398,
        10,2,0,0,398,399,7,6,0,0,399,401,3,96,48,0,400,397,1,0,0,0,401,404,
        1,0,0,0,402,400,1,0,0,0,402,403,1,0,0,0,403,95,1,0,0,0,404,402,1,
        0,0,0,405,408,3,98,49,0,406,407,5,48,0,0,407,409,3,98,49,0,408,406,
        1,0,0,0,408,409,1,0,0,0,409,97,1,0,0,0,410,421,3,100,50,0,411,412,
        3,134,67,0,412,414,5,43,0,0,413,415,3,100,50,0,414,413,1,0,0,0,415,
        416,1,0,0,0,416,414,1,0,0,0,416,417,1,0,0,0,417,418,1,0,0,0,418,
        419,5,44,0,0,419,421,1,0,0,0,420,410,1,0,0,0,420,411,1,0,0,0,421,
        99,1,0,0,0,422,423,3,104,52,0,423,101,1,0,0,0,424,438,5,50,0,0,425,
        427,3,142,71,0,426,425,1,0,0,0,426,427,1,0,0,0,427,428,1,0,0,0,428,
        430,5,46,0,0,429,431,3,142,71,0,430,429,1,0,0,0,430,431,1,0,0,0,
        431,436,1,0,0,0,432,434,5,46,0,0,433,435,3,142,71,0,434,433,1,0,
        0,0,434,435,1,0,0,0,435,437,1,0,0,0,436,432,1,0,0,0,436,437,1,0,
        0,0,437,439,1,0,0,0,438,426,1,0,0,0,438,439,1,0,0,0,439,440,1,0,
        0,0,440,441,5,51,0,0,441,103,1,0,0,0,442,446,3,126,63,0,443,446,
        3,108,54,0,444,446,3,106,53,0,445,442,1,0,0,0,445,443,1,0,0,0,445,
        444,1,0,0,0,446,105,1,0,0,0,447,448,5,43,0,0,448,449,3,90,45,0,449,
        450,5,44,0,0,450,107,1,0,0,0,451,455,3,110,55,0,452,455,3,112,56,
        0,453,455,3,114,57,0,454,451,1,0,0,0,454,452,1,0,0,0,454,453,1,0,
        0,0,455,109,1,0,0,0,456,457,3,114,57,0,457,458,5,17,0,0,458,459,
        3,114,57,0,459,111,1,0,0,0,460,461,3,114,57,0,461,462,5,36,0,0,462,
        463,3,116,58,0,463,113,1,0,0,0,464,466,3,144,72,0,465,467,3,134,
        67,0,466,465,1,0,0,0,466,467,1,0,0,0,467,115,1,0,0,0,468,471,3,146,
        73,0,469,472,5,39,0,0,470,472,3,134,67,0,471,469,1,0,0,0,471,470,
        1,0,0,0,471,472,1,0,0,0,472,117,1,0,0,0,473,474,3,142,71,0,474,119,
        1,0,0,0,475,476,5,50,0,0,476,477,3,118,59,0,477,478,5,51,0,0,478,
        121,1,0,0,0,479,480,5,40,0,0,480,481,3,140,70,0,481,123,1,0,0,0,
        482,484,3,134,67,0,483,485,3,120,60,0,484,483,1,0,0,0,484,485,1,
        0,0,0,485,125,1,0,0,0,486,491,3,124,62,0,487,488,5,40,0,0,488,490,
        3,124,62,0,489,487,1,0,0,0,490,493,1,0,0,0,491,489,1,0,0,0,491,492,
        1,0,0,0,492,495,1,0,0,0,493,491,1,0,0,0,494,496,3,122,61,0,495,494,
        1,0,0,0,495,496,1,0,0,0,496,127,1,0,0,0,497,502,3,134,67,0,498,499,
        5,40,0,0,499,501,3,134,67,0,500,498,1,0,0,0,501,504,1,0,0,0,502,
        500,1,0,0,0,502,503,1,0,0,0,503,129,1,0,0,0,504,502,1,0,0,0,505,
        506,3,134,67,0,506,131,1,0,0,0,507,508,5,46,0,0,508,509,3,130,65,
        0,509,133,1,0,0,0,510,511,5,27,0,0,511,135,1,0,0,0,512,513,5,3,0,
        0,513,137,1,0,0,0,514,515,7,7,0,0,515,139,1,0,0,0,516,517,3,146,
        73,0,517,141,1,0,0,0,518,519,3,144,72,0,519,143,1,0,0,0,520,522,
        7,5,0,0,521,520,1,0,0,0,521,522,1,0,0,0,522,523,1,0,0,0,523,524,
        3,146,73,0,524,145,1,0,0,0,525,526,5,4,0,0,526,147,1,0,0,0,42,150,
        152,162,169,173,192,196,201,217,221,230,238,246,264,271,282,295,
        308,316,329,344,352,380,391,402,408,416,420,426,430,434,436,438,
        445,454,466,471,484,491,495,502,521
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
                     "'~>'", "'<~'", "'~'", "<INVALID>", "<INVALID>", "<INVALID>", 
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
                      "SPERM", "LSPERM", "WIRE", "NAME", "STRING_LITERAL", 
                      "BYTES_LITERAL", "DECIMAL_INTEGER", "OCT_INTEGER", 
                      "HEX_INTEGER", "BIN_INTEGER", "FLOAT_NUMBER", "IMAG_NUMBER", 
                      "PLUS_OR_MINUS", "PLUS_SLASH_MINUS", "PLUS_MINUS_SIGN", 
                      "PERCENT", "DOT", "ELLIPSIS", "STAR", "OPEN_PAREN", 
                      "CLOSE_PAREN", "COMMA", "COLON", "SEMI_COLON", "POWER", 
                      "ASSIGN", "OPEN_BRACK", "CLOSE_BRACK", "OR_OP", "XOR", 
                      "AND_OP", "LEFT_SHIFT", "RIGHT_SHIFT", "PLUS", "MINUS", 
                      "DIV", "IDIV", "OPEN_BRACE", "CLOSE_BRACE", "LESS_THAN", 
                      "GREATER_THAN", "EQUALS", "GT_EQ", "LT_EQ", "NOT_EQ_1", 
                      "NOT_EQ_2", "AT", "ARROW", "ADD_ASSIGN", "SUB_ASSIGN", 
                      "MULT_ASSIGN", "AT_ASSIGN", "DIV_ASSIGN", "AND_ASSIGN", 
                      "OR_ASSIGN", "XOR_ASSIGN", "LEFT_SHIFT_ASSIGN", "RIGHT_SHIFT_ASSIGN", 
                      "POWER_ASSIGN", "IDIV_ASSIGN", "NEWLINE", "PRAGMA", 
                      "COMMENT", "WS", "EXPLICIT_LINE_JOINING", "ERRORTOKEN" ]

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
    RULE_for_stmt = 34
    RULE_assert_stmt = 35
    RULE_trait_stmt = 36
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
    RULE_functional = 49
    RULE_bound = 50
    RULE_slice = 51
    RULE_atom = 52
    RULE_arithmetic_group = 53
    RULE_literal_physical = 54
    RULE_bound_quantity = 55
    RULE_bilateral_quantity = 56
    RULE_quantity = 57
    RULE_bilateral_tolerance = 58
    RULE_key = 59
    RULE_array_index = 60
    RULE_pin_reference_end = 61
    RULE_field_reference_part = 62
    RULE_field_reference = 63
    RULE_type_reference = 64
    RULE_unit = 65
    RULE_type_info = 66
    RULE_name = 67
    RULE_string = 68
    RULE_boolean_ = 69
    RULE_number_hint_natural = 70
    RULE_number_hint_integer = 71
    RULE_number = 72
    RULE_number_signless = 73

    ruleNames =  [ "file_input", "pragma_stmt", "stmt", "simple_stmts", 
                   "simple_stmt", "compound_stmt", "blockdef", "blockdef_super", 
                   "blocktype", "block", "dep_import_stmt", "import_stmt", 
                   "declaration_stmt", "field_reference_or_declaration", 
                   "assign_stmt", "cum_assign_stmt", "set_assign_stmt", 
                   "cum_operator", "cum_assignable", "assignable", "retype_stmt", 
                   "directed_connect_stmt", "connect_stmt", "bridgeable", 
                   "mif", "connectable", "signaldef_stmt", "pindef_stmt", 
                   "pin_declaration", "pin_stmt", "new_stmt", "new_count", 
                   "string_stmt", "pass_stmt", "for_stmt", "assert_stmt", 
                   "trait_stmt", "comparison", "compare_op_pair", "lt_arithmetic_or", 
                   "gt_arithmetic_or", "lt_eq_arithmetic_or", "gt_eq_arithmetic_or", 
                   "in_arithmetic_or", "is_arithmetic_or", "arithmetic_expression", 
                   "sum", "term", "power", "functional", "bound", "slice", 
                   "atom", "arithmetic_group", "literal_physical", "bound_quantity", 
                   "bilateral_quantity", "quantity", "bilateral_tolerance", 
                   "key", "array_index", "pin_reference_end", "field_reference_part", 
                   "field_reference", "type_reference", "unit", "type_info", 
                   "name", "string", "boolean_", "number_hint_natural", 
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
    NAME=27
    STRING_LITERAL=28
    BYTES_LITERAL=29
    DECIMAL_INTEGER=30
    OCT_INTEGER=31
    HEX_INTEGER=32
    BIN_INTEGER=33
    FLOAT_NUMBER=34
    IMAG_NUMBER=35
    PLUS_OR_MINUS=36
    PLUS_SLASH_MINUS=37
    PLUS_MINUS_SIGN=38
    PERCENT=39
    DOT=40
    ELLIPSIS=41
    STAR=42
    OPEN_PAREN=43
    CLOSE_PAREN=44
    COMMA=45
    COLON=46
    SEMI_COLON=47
    POWER=48
    ASSIGN=49
    OPEN_BRACK=50
    CLOSE_BRACK=51
    OR_OP=52
    XOR=53
    AND_OP=54
    LEFT_SHIFT=55
    RIGHT_SHIFT=56
    PLUS=57
    MINUS=58
    DIV=59
    IDIV=60
    OPEN_BRACE=61
    CLOSE_BRACE=62
    LESS_THAN=63
    GREATER_THAN=64
    EQUALS=65
    GT_EQ=66
    LT_EQ=67
    NOT_EQ_1=68
    NOT_EQ_2=69
    AT=70
    ARROW=71
    ADD_ASSIGN=72
    SUB_ASSIGN=73
    MULT_ASSIGN=74
    AT_ASSIGN=75
    DIV_ASSIGN=76
    AND_ASSIGN=77
    OR_ASSIGN=78
    XOR_ASSIGN=79
    LEFT_SHIFT_ASSIGN=80
    RIGHT_SHIFT_ASSIGN=81
    POWER_ASSIGN=82
    IDIV_ASSIGN=83
    NEWLINE=84
    PRAGMA=85
    COMMENT=86
    WS=87
    EXPLICIT_LINE_JOINING=88
    ERRORTOKEN=89

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
            self.state = 152
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 146896840) != 0) or _la==84 or _la==85:
                self.state = 150
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [84]:
                    self.state = 148
                    self.match(AtoParser.NEWLINE)
                    pass
                elif token in [3, 6, 7, 8, 9, 10, 12, 13, 14, 16, 22, 23, 27, 85]:
                    self.state = 149
                    self.stmt()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 154
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 155
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
            self.state = 157
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
            self.state = 162
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 16, 22, 23, 27]:
                self.enterOuterAlt(localctx, 1)
                self.state = 159
                self.simple_stmts()
                pass
            elif token in [6, 7, 8, 14]:
                self.enterOuterAlt(localctx, 2)
                self.state = 160
                self.compound_stmt()
                pass
            elif token in [85]:
                self.enterOuterAlt(localctx, 3)
                self.state = 161
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
            self.state = 164
            self.simple_stmt()
            self.state = 169
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 165
                    self.match(AtoParser.SEMI_COLON)
                    self.state = 166
                    self.simple_stmt() 
                self.state = 171
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

            self.state = 173
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==47:
                self.state = 172
                self.match(AtoParser.SEMI_COLON)


            self.state = 175
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
            self.state = 192
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,5,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 177
                self.import_stmt()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 178
                self.dep_import_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 179
                self.assign_stmt()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 180
                self.cum_assign_stmt()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 181
                self.set_assign_stmt()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 182
                self.connect_stmt()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 183
                self.directed_connect_stmt()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 184
                self.retype_stmt()
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 185
                self.pin_declaration()
                pass

            elif la_ == 10:
                self.enterOuterAlt(localctx, 10)
                self.state = 186
                self.signaldef_stmt()
                pass

            elif la_ == 11:
                self.enterOuterAlt(localctx, 11)
                self.state = 187
                self.assert_stmt()
                pass

            elif la_ == 12:
                self.enterOuterAlt(localctx, 12)
                self.state = 188
                self.declaration_stmt()
                pass

            elif la_ == 13:
                self.enterOuterAlt(localctx, 13)
                self.state = 189
                self.string_stmt()
                pass

            elif la_ == 14:
                self.enterOuterAlt(localctx, 14)
                self.state = 190
                self.pass_stmt()
                pass

            elif la_ == 15:
                self.enterOuterAlt(localctx, 15)
                self.state = 191
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
            self.state = 196
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [6, 7, 8]:
                self.enterOuterAlt(localctx, 1)
                self.state = 194
                self.blockdef()
                pass
            elif token in [14]:
                self.enterOuterAlt(localctx, 2)
                self.state = 195
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
            self.state = 198
            self.blocktype()
            self.state = 199
            self.name()
            self.state = 201
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 200
                self.blockdef_super()


            self.state = 203
            self.match(AtoParser.COLON)
            self.state = 204
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
            self.state = 206
            self.match(AtoParser.FROM)
            self.state = 207
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
            self.state = 209
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
            self.state = 221
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3, 9, 10, 12, 13, 16, 22, 23, 27]:
                self.enterOuterAlt(localctx, 1)
                self.state = 211
                self.simple_stmts()
                pass
            elif token in [84]:
                self.enterOuterAlt(localctx, 2)
                self.state = 212
                self.match(AtoParser.NEWLINE)
                self.state = 213
                self.match(AtoParser.INDENT)
                self.state = 215 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 214
                    self.stmt()
                    self.state = 217 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 146896840) != 0) or _la==85):
                        break

                self.state = 219
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
            self.state = 223
            self.match(AtoParser.IMPORT)
            self.state = 224
            self.type_reference()
            self.state = 225
            self.match(AtoParser.FROM)
            self.state = 226
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
            self.state = 230
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==12:
                self.state = 228
                self.match(AtoParser.FROM)
                self.state = 229
                self.string()


            self.state = 232
            self.match(AtoParser.IMPORT)
            self.state = 233
            self.type_reference()
            self.state = 238
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==45:
                self.state = 234
                self.match(AtoParser.COMMA)
                self.state = 235
                self.type_reference()
                self.state = 240
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
            self.state = 241
            self.field_reference()
            self.state = 242
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
            self.state = 246
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 244
                self.field_reference()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 245
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
            self.state = 248
            self.field_reference_or_declaration()
            self.state = 249
            self.match(AtoParser.ASSIGN)
            self.state = 250
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
            self.state = 252
            self.field_reference_or_declaration()
            self.state = 253
            self.cum_operator()
            self.state = 254
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
            self.state = 256
            self.field_reference_or_declaration()
            self.state = 257
            _la = self._input.LA(1)
            if not(_la==77 or _la==78):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 258
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
            self.state = 260
            _la = self._input.LA(1)
            if not(_la==72 or _la==73):
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
            self.state = 264
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 262
                self.literal_physical()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 263
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
            self.state = 271
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 266
                self.string()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 267
                self.new_stmt()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 268
                self.literal_physical()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 269
                self.arithmetic_expression(0)
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 270
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
            self.state = 273
            self.field_reference()
            self.state = 274
            self.match(AtoParser.ARROW)
            self.state = 275
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
            self.state = 277
            self.bridgeable()
            self.state = 280 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 278
                _la = self._input.LA(1)
                if not(_la==24 or _la==25):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 279
                self.bridgeable()
                self.state = 282 
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
            self.state = 284
            self.mif()
            self.state = 285
            self.match(AtoParser.WIRE)
            self.state = 286
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
            self.state = 288
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
            self.state = 290
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
            self.state = 295
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [27]:
                self.enterOuterAlt(localctx, 1)
                self.state = 292
                self.field_reference()
                pass
            elif token in [10]:
                self.enterOuterAlt(localctx, 2)
                self.state = 293
                self.signaldef_stmt()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 3)
                self.state = 294
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
            self.state = 297
            self.match(AtoParser.SIGNAL)
            self.state = 298
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
            self.state = 300
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
            self.state = 302
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
            self.state = 304
            self.match(AtoParser.PIN)
            self.state = 308
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [27]:
                self.state = 305
                self.name()
                pass
            elif token in [4]:
                self.state = 306
                self.number_hint_natural()
                pass
            elif token in [3]:
                self.state = 307
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
        self.enterRule(localctx, 60, self.RULE_new_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 310
            self.match(AtoParser.NEW)
            self.state = 311
            self.type_reference()
            self.state = 316
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==50:
                self.state = 312
                self.match(AtoParser.OPEN_BRACK)
                self.state = 313
                self.new_count()
                self.state = 314
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
        self.enterRule(localctx, 62, self.RULE_new_count)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 318
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
            self.state = 320
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
            self.state = 322
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
        self.enterRule(localctx, 68, self.RULE_for_stmt)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 324
            self.match(AtoParser.FOR)
            self.state = 325
            self.name()
            self.state = 326
            self.match(AtoParser.IN)
            self.state = 327
            self.field_reference()
            self.state = 329
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==50:
                self.state = 328
                self.slice_()


            self.state = 331
            self.match(AtoParser.COLON)
            self.state = 332
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
        self.enterRule(localctx, 70, self.RULE_assert_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 334
            self.match(AtoParser.ASSERT)
            self.state = 335
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


        def getRuleIndex(self):
            return AtoParser.RULE_trait_stmt

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTrait_stmt" ):
                return visitor.visitTrait_stmt(self)
            else:
                return visitor.visitChildren(self)




    def trait_stmt(self):

        localctx = AtoParser.Trait_stmtContext(self, self._ctx, self.state)
        self.enterRule(localctx, 72, self.RULE_trait_stmt)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 337
            self.match(AtoParser.TRAIT)
            self.state = 338
            self.type_reference()
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
            self.state = 340
            self.arithmetic_expression(0)
            self.state = 342 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 341
                self.compare_op_pair()
                self.state = 344 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (((((_la - 20)) & ~0x3f) == 0 and ((1 << (_la - 20)) & 237494511599619) != 0)):
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
            self.state = 352
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [63]:
                self.enterOuterAlt(localctx, 1)
                self.state = 346
                self.lt_arithmetic_or()
                pass
            elif token in [64]:
                self.enterOuterAlt(localctx, 2)
                self.state = 347
                self.gt_arithmetic_or()
                pass
            elif token in [67]:
                self.enterOuterAlt(localctx, 3)
                self.state = 348
                self.lt_eq_arithmetic_or()
                pass
            elif token in [66]:
                self.enterOuterAlt(localctx, 4)
                self.state = 349
                self.gt_eq_arithmetic_or()
                pass
            elif token in [20]:
                self.enterOuterAlt(localctx, 5)
                self.state = 350
                self.in_arithmetic_or()
                pass
            elif token in [21]:
                self.enterOuterAlt(localctx, 6)
                self.state = 351
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
            self.state = 354
            self.match(AtoParser.LESS_THAN)
            self.state = 355
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
            self.state = 357
            self.match(AtoParser.GREATER_THAN)
            self.state = 358
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
            self.state = 360
            self.match(AtoParser.LT_EQ)
            self.state = 361
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
            self.state = 363
            self.match(AtoParser.GT_EQ)
            self.state = 364
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
            self.state = 366
            self.match(AtoParser.WITHIN)
            self.state = 367
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
            self.state = 369
            self.match(AtoParser.IS)
            self.state = 370
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
            self.state = 373
            self.sum_(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 380
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,22,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.Arithmetic_expressionContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_arithmetic_expression)
                    self.state = 375
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 376
                    _la = self._input.LA(1)
                    if not(_la==52 or _la==54):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 377
                    self.sum_(0) 
                self.state = 382
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,22,self._ctx)

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
            self.state = 384
            self.term(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 391
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,23,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.SumContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_sum)
                    self.state = 386
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 387
                    _la = self._input.LA(1)
                    if not(_la==57 or _la==58):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 388
                    self.term(0) 
                self.state = 393
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,23,self._ctx)

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
            self.state = 395
            self.power()
            self._ctx.stop = self._input.LT(-1)
            self.state = 402
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,24,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = AtoParser.TermContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_term)
                    self.state = 397
                    if not self.precpred(self._ctx, 2):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                    self.state = 398
                    _la = self._input.LA(1)
                    if not(_la==42 or _la==59):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 399
                    self.power() 
                self.state = 404
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,24,self._ctx)

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
        self.enterRule(localctx, 96, self.RULE_power)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 405
            self.functional()
            self.state = 408
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,25,self._ctx)
            if la_ == 1:
                self.state = 406
                self.match(AtoParser.POWER)
                self.state = 407
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
        self.enterRule(localctx, 98, self.RULE_functional)
        self._la = 0 # Token type
        try:
            self.state = 420
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,27,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 410
                self.bound()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 411
                self.name()
                self.state = 412
                self.match(AtoParser.OPEN_PAREN)
                self.state = 414 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 413
                    self.bound()
                    self.state = 416 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 432354360454807568) != 0)):
                        break

                self.state = 418
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
        self.enterRule(localctx, 100, self.RULE_bound)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 422
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
        self.enterRule(localctx, 102, self.RULE_slice)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 424
            self.match(AtoParser.OPEN_BRACK)
            self.state = 438
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 432415932971745296) != 0):
                self.state = 426
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 432345564227567632) != 0):
                    self.state = 425
                    self.number_hint_integer()


                self.state = 428
                self.match(AtoParser.COLON)
                self.state = 430
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 432345564227567632) != 0):
                    self.state = 429
                    self.number_hint_integer()


                self.state = 436
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==46:
                    self.state = 432
                    self.match(AtoParser.COLON)
                    self.state = 434
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if (((_la) & ~0x3f) == 0 and ((1 << _la) & 432345564227567632) != 0):
                        self.state = 433
                        self.number_hint_integer()






            self.state = 440
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
        self.enterRule(localctx, 104, self.RULE_atom)
        try:
            self.state = 445
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [27]:
                self.enterOuterAlt(localctx, 1)
                self.state = 442
                self.field_reference()
                pass
            elif token in [4, 57, 58]:
                self.enterOuterAlt(localctx, 2)
                self.state = 443
                self.literal_physical()
                pass
            elif token in [43]:
                self.enterOuterAlt(localctx, 3)
                self.state = 444
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
        self.enterRule(localctx, 106, self.RULE_arithmetic_group)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 447
            self.match(AtoParser.OPEN_PAREN)
            self.state = 448
            self.arithmetic_expression(0)
            self.state = 449
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
        self.enterRule(localctx, 108, self.RULE_literal_physical)
        try:
            self.state = 454
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,34,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 451
                self.bound_quantity()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 452
                self.bilateral_quantity()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 453
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
        self.enterRule(localctx, 110, self.RULE_bound_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 456
            self.quantity()
            self.state = 457
            self.match(AtoParser.TO)
            self.state = 458
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
        self.enterRule(localctx, 112, self.RULE_bilateral_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 460
            self.quantity()
            self.state = 461
            self.match(AtoParser.PLUS_OR_MINUS)
            self.state = 462
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
        self.enterRule(localctx, 114, self.RULE_quantity)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 464
            self.number()
            self.state = 466
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,35,self._ctx)
            if la_ == 1:
                self.state = 465
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
        self.enterRule(localctx, 116, self.RULE_bilateral_tolerance)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 468
            self.number_signless()
            self.state = 471
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,36,self._ctx)
            if la_ == 1:
                self.state = 469
                self.match(AtoParser.PERCENT)

            elif la_ == 2:
                self.state = 470
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
        self.enterRule(localctx, 118, self.RULE_key)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 473
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
        self.enterRule(localctx, 120, self.RULE_array_index)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 475
            self.match(AtoParser.OPEN_BRACK)
            self.state = 476
            self.key()
            self.state = 477
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
        self.enterRule(localctx, 122, self.RULE_pin_reference_end)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 479
            self.match(AtoParser.DOT)
            self.state = 480
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
        self.enterRule(localctx, 124, self.RULE_field_reference_part)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 482
            self.name()
            self.state = 484
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,37,self._ctx)
            if la_ == 1:
                self.state = 483
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
        self.enterRule(localctx, 126, self.RULE_field_reference)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 486
            self.field_reference_part()
            self.state = 491
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,38,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 487
                    self.match(AtoParser.DOT)
                    self.state = 488
                    self.field_reference_part() 
                self.state = 493
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,38,self._ctx)

            self.state = 495
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,39,self._ctx)
            if la_ == 1:
                self.state = 494
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
        self.enterRule(localctx, 128, self.RULE_type_reference)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 497
            self.name()
            self.state = 502
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==40:
                self.state = 498
                self.match(AtoParser.DOT)
                self.state = 499
                self.name()
                self.state = 504
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
        self.enterRule(localctx, 130, self.RULE_unit)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 505
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
        self.enterRule(localctx, 132, self.RULE_type_info)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 507
            self.match(AtoParser.COLON)
            self.state = 508
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
        self.enterRule(localctx, 134, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 510
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
        self.enterRule(localctx, 136, self.RULE_string)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 512
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
        self.enterRule(localctx, 138, self.RULE_boolean_)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 514
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
        self.enterRule(localctx, 140, self.RULE_number_hint_natural)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 516
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
        self.enterRule(localctx, 142, self.RULE_number_hint_integer)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 518
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
        self.enterRule(localctx, 144, self.RULE_number)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 521
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==57 or _la==58:
                self.state = 520
                _la = self._input.LA(1)
                if not(_la==57 or _la==58):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()


            self.state = 523
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
        self.enterRule(localctx, 146, self.RULE_number_signless)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 525
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
         




