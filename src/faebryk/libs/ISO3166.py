# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import IntEnum


class ISO3166_1_A3(IntEnum):
    """
    ISO 3166-1 alpha-3 country and numeric codes.
    https://en.wikipedia.org/wiki/ISO_3166-1_alpha-3
    """

    ABW = 533
    AFG = 4
    AGO = 24
    AIA = 660
    ALA = 248
    ALB = 8
    AND = 20
    ARE = 784
    ARG = 32
    ARM = 51
    ASM = 16
    ATA = 10
    ATF = 260
    ATG = 28
    AUS = 36
    AUT = 40
    AZE = 31
    BDI = 108
    BEL = 56
    BEN = 204
    BES = 535
    BFA = 854
    BGD = 50
    BGR = 100
    BHR = 48
    BHS = 44
    BIH = 70
    BLM = 652
    BLR = 112
    BLZ = 84
    BMU = 60
    BOL = 68
    BRA = 76
    BRB = 52
    BRN = 96
    BTN = 64
    BVT = 74
    BWA = 72
    CAF = 140
    CAN = 124
    CCK = 166
    CHE = 756
    CHL = 152
    CHN = 156
    CIV = 384
    CMR = 120
    COD = 180
    COG = 178
    COK = 184
    COL = 170
    COM = 174
    CPV = 132
    CRI = 188
    CUB = 192
    CUW = 531
    CXR = 162
    CYM = 136
    CYP = 196
    CZE = 203
    DEU = 276
    DJI = 262
    DMA = 212
    DNK = 208
    DOM = 214
    DZA = 12
    ECU = 218
    EGY = 818
    ERI = 232
    ESH = 732
    ESP = 724
    EST = 233
    ETH = 231
    FIN = 246
    FJI = 242
    FLK = 238
    FRA = 250
    FRO = 234
    FSM = 583
    GAB = 266
    GBR = 826
    GEO = 268
    GGY = 831
    GHA = 288
    GIB = 292
    GIN = 324
    GLP = 312
    GMB = 270
    GNB = 624
    GNQ = 226
    GRC = 300
    GRD = 308
    GRL = 304
    GTM = 320
    GUF = 254
    GUM = 316
    GUY = 328
    HKG = 344
    HMD = 334
    HND = 340
    HRV = 191
    HTI = 332
    HUN = 348
    IDN = 360
    IMN = 833
    IND = 356
    IOT = 86
    IRL = 372
    IRN = 364
    IRQ = 368
    ISL = 352
    ISR = 376
    ITA = 380
    JAM = 388
    JEY = 832
    JOR = 400
    JPN = 392
    KAZ = 398
    KEN = 404
    KGZ = 417
    KHM = 116
    KIR = 296
    KNA = 659
    KOR = 410
    KWT = 414
    LAO = 418
    LBN = 422
    LBR = 430
    LBY = 434
    LCA = 662
    LIE = 438
    LKA = 144
    LSO = 426
    LTU = 440
    LUX = 442
    LVA = 428
    MAC = 446
    MAF = 663
    MAR = 504
    MCO = 492
    MDA = 498
    MDG = 450
    MDV = 462
    MEX = 484
    MHL = 584
    MKD = 807
    MLI = 466
    MLT = 470
    MMR = 104
    MNE = 499
    MNG = 496
    MNP = 580
    MOZ = 508
    MRT = 478
    MSR = 500
    MTQ = 474
    MUS = 480
    MWI = 454
    MYS = 458
    MYT = 175
    NAM = 516
    NCL = 540
    NER = 562
    NFK = 574
    NGA = 566
    NIC = 558
    NIU = 570
    NLD = 528
    NOR = 578
    NPL = 524
    NRU = 520
    NZL = 554
    OMN = 512
    PAK = 586
    PAN = 591
    PCN = 612
    PER = 604
    PHL = 608
    PLW = 585
    PNG = 598
    POL = 616
    PRK = 408
    PRI = 630
    PRY = 600
    PRT = 620
    PSE = 275
    PYF = 258
    QAT = 634
    REU = 638
    ROU = 642
    RUS = 643
    RWA = 646
    SAU = 682
    SDN = 729
    SEN = 686
    SGP = 702
    SGS = 239
    SHN = 654
    SJM = 744
    SLB = 90
    SLE = 694
    SLV = 222
    SMR = 674
    SOM = 706
    SPM = 666
    SRB = 688
    SSD = 728
    STP = 678
    SUR = 740
    SVK = 703
    SVN = 705
    SWE = 752
    SWZ = 748
    SXM = 534
    SYC = 690
    SYR = 760
    TCA = 796
    TCD = 148
    TGO = 768
    THA = 764
    TJK = 762
    TKL = 772
    TKM = 795
    TLS = 626
    TON = 776
    TTO = 780
    TUN = 788
    TUR = 792
    TUV = 798
    TWN = 158
    TZA = 834
    UGA = 800
    UKR = 804
    UMI = 581
    URY = 858
    USA = 840
    UZB = 860
    VAT = 336
    VCT = 670
    VEN = 862
    VGB = 92
    VIR = 850
    VNM = 704
    VUT = 548
    WLF = 876
    WSM = 882
    YEM = 887
    ZAF = 710
    ZMB = 894
    ZWE = 716

    @property
    def full_name(self) -> str:
        """Return the full country name for this ISO 3166-1 alpha-3 code."""
        return _COUNTRY_NAMES[self.name]


_COUNTRY_NAMES: dict[str, str] = {
    "ABW": "Aruba",
    "AFG": "Afghanistan",
    "AGO": "Angola",
    "AIA": "Anguilla",
    "ALA": "\u00c5land Islands",
    "ALB": "Albania",
    "AND": "Andorra",
    "ARE": "United Arab Emirates",
    "ARG": "Argentina",
    "ARM": "Armenia",
    "ASM": "American Samoa",
    "ATA": "Antarctica",
    "ATF": "French Southern Territories",
    "ATG": "Antigua and Barbuda",
    "AUS": "Australia",
    "AUT": "Austria",
    "AZE": "Azerbaijan",
    "BDI": "Burundi",
    "BEL": "Belgium",
    "BEN": "Benin",
    "BES": "Bonaire, Sint Eustatius and Saba",
    "BFA": "Burkina Faso",
    "BGD": "Bangladesh",
    "BGR": "Bulgaria",
    "BHR": "Bahrain",
    "BHS": "Bahamas",
    "BIH": "Bosnia and Herzegovina",
    "BLM": "Saint Barth\u00e9lemy",
    "BLR": "Belarus",
    "BLZ": "Belize",
    "BMU": "Bermuda",
    "BOL": "Bolivia, Plurinational State of",
    "BRA": "Brazil",
    "BRB": "Barbados",
    "BRN": "Brunei Darussalam",
    "BTN": "Bhutan",
    "BVT": "Bouvet Island",
    "BWA": "Botswana",
    "CAF": "Central African Republic",
    "CAN": "Canada",
    "CCK": "Cocos (Keeling) Islands",
    "CHE": "Switzerland",
    "CHL": "Chile",
    "CHN": "China",
    "CIV": "C\u00f4te d'Ivoire",
    "CMR": "Cameroon",
    "COD": "Congo, Democratic Republic of the",
    "COG": "Congo",
    "COK": "Cook Islands",
    "COL": "Colombia",
    "COM": "Comoros",
    "CPV": "Cabo Verde",
    "CRI": "Costa Rica",
    "CUB": "Cuba",
    "CUW": "Cura\u00e7ao",
    "CXR": "Christmas Island",
    "CYM": "Cayman Islands",
    "CYP": "Cyprus",
    "CZE": "Czechia",
    "DEU": "Germany",
    "DJI": "Djibouti",
    "DMA": "Dominica",
    "DNK": "Denmark",
    "DOM": "Dominican Republic",
    "DZA": "Algeria",
    "ECU": "Ecuador",
    "EGY": "Egypt",
    "ERI": "Eritrea",
    "ESH": "Western Sahara",
    "ESP": "Spain",
    "EST": "Estonia",
    "ETH": "Ethiopia",
    "FIN": "Finland",
    "FJI": "Fiji",
    "FLK": "Falkland Islands (Malvinas)",
    "FRA": "France",
    "FRO": "Faroe Islands",
    "FSM": "Micronesia, Federated States of",
    "GAB": "Gabon",
    "GBR": "United Kingdom of Great Britain and Northern Ireland",
    "GEO": "Georgia",
    "GGY": "Guernsey",
    "GHA": "Ghana",
    "GIB": "Gibraltar",
    "GIN": "Guinea",
    "GLP": "Guadeloupe",
    "GMB": "Gambia",
    "GNB": "Guinea-Bissau",
    "GNQ": "Equatorial Guinea",
    "GRC": "Greece",
    "GRD": "Grenada",
    "GRL": "Greenland",
    "GTM": "Guatemala",
    "GUF": "French Guiana",
    "GUM": "Guam",
    "GUY": "Guyana",
    "HKG": "Hong Kong",
    "HMD": "Heard Island and McDonald Islands",
    "HND": "Honduras",
    "HRV": "Croatia",
    "HTI": "Haiti",
    "HUN": "Hungary",
    "IDN": "Indonesia",
    "IMN": "Isle of Man",
    "IND": "India",
    "IOT": "British Indian Ocean Territory",
    "IRL": "Ireland",
    "IRN": "Iran, Islamic Republic of",
    "IRQ": "Iraq",
    "ISL": "Iceland",
    "ISR": "Israel",
    "ITA": "Italy",
    "JAM": "Jamaica",
    "JEY": "Jersey",
    "JOR": "Jordan",
    "JPN": "Japan",
    "KAZ": "Kazakhstan",
    "KEN": "Kenya",
    "KGZ": "Kyrgyzstan",
    "KHM": "Cambodia",
    "KIR": "Kiribati",
    "KNA": "Saint Kitts and Nevis",
    "KOR": "Korea, Republic of",
    "KWT": "Kuwait",
    "LAO": "Lao People's Democratic Republic",
    "LBN": "Lebanon",
    "LBR": "Liberia",
    "LBY": "Libya",
    "LCA": "Saint Lucia",
    "LIE": "Liechtenstein",
    "LKA": "Sri Lanka",
    "LSO": "Lesotho",
    "LTU": "Lithuania",
    "LUX": "Luxembourg",
    "LVA": "Latvia",
    "MAC": "Macao",
    "MAF": "Saint Martin (French part)",
    "MAR": "Morocco",
    "MCO": "Monaco",
    "MDA": "Moldova, Republic of",
    "MDG": "Madagascar",
    "MDV": "Maldives",
    "MEX": "Mexico",
    "MHL": "Marshall Islands",
    "MKD": "North Macedonia",
    "MLI": "Mali",
    "MLT": "Malta",
    "MMR": "Myanmar",
    "MNE": "Montenegro",
    "MNG": "Mongolia",
    "MNP": "Northern Mariana Islands",
    "MOZ": "Mozambique",
    "MRT": "Mauritania",
    "MSR": "Montserrat",
    "MTQ": "Martinique",
    "MUS": "Mauritius",
    "MWI": "Malawi",
    "MYS": "Malaysia",
    "MYT": "Mayotte",
    "NAM": "Namibia",
    "NCL": "New Caledonia",
    "NER": "Niger",
    "NFK": "Norfolk Island",
    "NGA": "Nigeria",
    "NIC": "Nicaragua",
    "NIU": "Niue",
    "NLD": "Netherlands, Kingdom of the",
    "NOR": "Norway",
    "NPL": "Nepal",
    "NRU": "Nauru",
    "NZL": "New Zealand",
    "OMN": "Oman",
    "PAK": "Pakistan",
    "PAN": "Panama",
    "PCN": "Pitcairn",
    "PER": "Peru",
    "PHL": "Philippines",
    "PLW": "Palau",
    "PNG": "Papua New Guinea",
    "POL": "Poland",
    "PRI": "Puerto Rico",
    "PRK": "Korea, Democratic People's Republic of",
    "PRT": "Portugal",
    "PRY": "Paraguay",
    "PSE": "Palestine, State of",
    "PYF": "French Polynesia",
    "QAT": "Qatar",
    "REU": "R\u00e9union",
    "ROU": "Romania",
    "RUS": "Russian Federation",
    "RWA": "Rwanda",
    "SAU": "Saudi Arabia",
    "SDN": "Sudan",
    "SEN": "Senegal",
    "SGP": "Singapore",
    "SGS": "South Georgia and the South Sandwich Islands",
    "SHN": "Saint Helena, Ascension and Tristan da Cunha",
    "SJM": "Svalbard and Jan Mayen",
    "SLB": "Solomon Islands",
    "SLE": "Sierra Leone",
    "SLV": "El Salvador",
    "SMR": "San Marino",
    "SOM": "Somalia",
    "SPM": "Saint Pierre and Miquelon",
    "SRB": "Serbia",
    "SSD": "South Sudan",
    "STP": "Sao Tome and Principe",
    "SUR": "Suriname",
    "SVK": "Slovakia",
    "SVN": "Slovenia",
    "SWE": "Sweden",
    "SWZ": "Eswatini",
    "SXM": "Sint Maarten (Dutch part)",
    "SYC": "Seychelles",
    "SYR": "Syrian Arab Republic",
    "TCA": "Turks and Caicos Islands",
    "TCD": "Chad",
    "TGO": "Togo",
    "THA": "Thailand",
    "TJK": "Tajikistan",
    "TKL": "Tokelau",
    "TKM": "Turkmenistan",
    "TLS": "Timor-Leste",
    "TON": "Tonga",
    "TTO": "Trinidad and Tobago",
    "TUN": "Tunisia",
    "TUR": "T\u00fcrkiye",
    "TUV": "Tuvalu",
    "TWN": "Taiwan, Province of China",
    "TZA": "Tanzania, United Republic of",
    "UGA": "Uganda",
    "UKR": "Ukraine",
    "UMI": "United States Minor Outlying Islands",
    "URY": "Uruguay",
    "USA": "United States of America",
    "UZB": "Uzbekistan",
    "VAT": "Holy See",
    "VCT": "Saint Vincent and the Grenadines",
    "VEN": "Venezuela, Bolivarian Republic of",
    "VGB": "Virgin Islands (British)",
    "VIR": "Virgin Islands (U.S.)",
    "VNM": "Viet Nam",
    "VUT": "Vanuatu",
    "WLF": "Wallis and Futuna",
    "WSM": "Samoa",
    "YEM": "Yemen",
    "ZAF": "South Africa",
    "ZMB": "Zambia",
    "ZWE": "Zimbabwe",
}
