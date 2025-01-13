from pathlib import Path

import faebryk.library._F as F

HERE = Path(__file__).parent

KNOWN_PACKAGES_TO_FOOTPRINT = {
    F.has_package.Package.C0201: HERE / "C_0201_0603Metric.kicad_mod",
    F.has_package.Package.C0402: HERE / "C_0402_1005Metric.kicad_mod",
    F.has_package.Package.C0603: HERE / "C_0603_1608Metric.kicad_mod",
    F.has_package.Package.C0805: HERE / "C_0805_2012Metric.kicad_mod",
    F.has_package.Package.R0201: HERE / "R_0201_0603Metric.kicad_mod",
    F.has_package.Package.R0402: HERE / "R_0402_1005Metric.kicad_mod",
    F.has_package.Package.R0603: HERE / "R_0603_1608Metric.kicad_mod",
    F.has_package.Package.R0805: HERE / "R_0805_2012Metric.kicad_mod",
    F.has_package.Package.L0201: HERE / "L_0201_0603Metric.kicad_mod",
    F.has_package.Package.L0402: HERE / "L_0402_1005Metric.kicad_mod",
    F.has_package.Package.L0603: HERE / "L_0603_1608Metric.kicad_mod",
    F.has_package.Package.L0805: HERE / "L_0805_2012Metric.kicad_mod",
}
