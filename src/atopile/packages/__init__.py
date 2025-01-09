from pathlib import Path

import faebryk.library._F as F

HERE = Path(__file__).parent

KNOWN_PACKAGES_TO_FOOTPRINT = {
    F.has_package.Package.C0201: HERE / "C0201.kicad_mod",
    F.has_package.Package.C0402: HERE / "C0402.kicad_mod",
    F.has_package.Package.C0603: HERE / "C0603.kicad_mod",
    F.has_package.Package.C0805: HERE / "C0805.kicad_mod",
    F.has_package.Package.R0201: HERE / "R0201.kicad_mod",
    F.has_package.Package.R0402: HERE / "R0402.kicad_mod",
    F.has_package.Package.R0603: HERE / "R0603.kicad_mod",
    F.has_package.Package.R0805: HERE / "R0805.kicad_mod",
    F.has_package.Package.L0201: HERE / "L0201.kicad_mod",
    F.has_package.Package.L0402: HERE / "L0402.kicad_mod",
    F.has_package.Package.L0603: HERE / "L0603.kicad_mod",
    F.has_package.Package.L0805: HERE / "L0805.kicad_mod",
}
