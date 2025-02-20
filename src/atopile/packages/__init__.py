from pathlib import Path

import faebryk.library._F as F

HERE = Path(__file__).parent

KNOWN_PACKAGES_TO_FOOTPRINT = {
    # Capacitors
    F.has_package.Package.C0201: HERE / "C_0201_0603Metric.kicad_mod",
    F.has_package.Package.C0402: HERE / "C_0402_1005Metric.kicad_mod",
    F.has_package.Package.C0603: HERE / "C_0603_1608Metric.kicad_mod",
    F.has_package.Package.C0805: HERE / "C_0805_2012Metric.kicad_mod",
    F.has_package.Package.C1206: HERE / "C_1206_3216Metric.kicad_mod",
    F.has_package.Package.C1210: HERE / "C_1210_3225Metric.kicad_mod",
    F.has_package.Package.C1808: HERE / "C_1808_4520Metric.kicad_mod",
    F.has_package.Package.C1812: HERE / "C_1812_4532Metric.kicad_mod",
    F.has_package.Package.C1825: HERE / "C_1825_4564Metric.kicad_mod",
    F.has_package.Package.C2220: HERE / "C_2220_5750Metric.kicad_mod",
    F.has_package.Package.C2225: HERE / "C_2225_5664Metric.kicad_mod",
    F.has_package.Package.C3640: HERE / "C_3640_9110Metric.kicad_mod",
    F.has_package.Package.C01005: HERE / "C_01005_0402Metric.kicad_mod",
    # Resistors
    F.has_package.Package.R0201: HERE / "R_0201_0603Metric.kicad_mod",
    F.has_package.Package.R0402: HERE / "R_0402_1005Metric.kicad_mod",
    F.has_package.Package.R0603: HERE / "R_0603_1608Metric.kicad_mod",
    F.has_package.Package.R0805: HERE / "R_0805_2012Metric.kicad_mod",
    F.has_package.Package.R0815: HERE / "R_0815_2038Metric.kicad_mod",
    F.has_package.Package.R1020: HERE / "R_1020_2550Metric.kicad_mod",
    F.has_package.Package.R1206: HERE / "R_1206_3216Metric.kicad_mod",
    F.has_package.Package.R1210: HERE / "R_1210_3225Metric.kicad_mod",
    F.has_package.Package.R1218: HERE / "R_1218_3246Metric.kicad_mod",
    F.has_package.Package.R1812: HERE / "R_1812_4532Metric.kicad_mod",
    F.has_package.Package.R2010: HERE / "R_2010_5025Metric.kicad_mod",
    F.has_package.Package.R2512: HERE / "R_2512_6332Metric.kicad_mod",
    F.has_package.Package.R2816: HERE / "R_2816_7142Metric.kicad_mod",
    F.has_package.Package.R4020: HERE / "R_4020_10251Metric.kicad_mod",
    F.has_package.Package.R01005: HERE / "R_01005_0402Metric.kicad_mod",
    # Inductors
    F.has_package.Package.L0201: HERE / "L_0201_0603Metric.kicad_mod",
    F.has_package.Package.L0402: HERE / "L_0402_1005Metric.kicad_mod",
    F.has_package.Package.L0603: HERE / "L_0603_1608Metric.kicad_mod",
    F.has_package.Package.L0805: HERE / "L_0805_2012Metric.kicad_mod",
    F.has_package.Package.L1008: HERE / "L_1008_2520Metric.kicad_mod",
    F.has_package.Package.L1206: HERE / "L_1206_3216Metric.kicad_mod",
    F.has_package.Package.L1210: HERE / "L_1210_3225Metric.kicad_mod",
    F.has_package.Package.L1806: HERE / "L_1806_4516Metric.kicad_mod",
    F.has_package.Package.L1812: HERE / "L_1812_4532Metric.kicad_mod",
    F.has_package.Package.L2010: HERE / "L_2010_5025Metric.kicad_mod",
    F.has_package.Package.L2512: HERE / "L_2512_6332Metric.kicad_mod",
    F.has_package.Package.L01005: HERE / "L_01005_0402Metric.kicad_mod",
}
