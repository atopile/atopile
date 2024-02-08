from typing import List, Optional

from attrs import define, field


@define
class KicadField:
    """KV pair"""

    name: str  # eg value
    value: str  # eg 10 Ohms


@define
class KicadPin:
    """
    eg. (pin (num "1") (name "") (type "passive"))
    """

    name: str
    type: str

    @property
    def num(self) -> str:
        return self.name


@define
class KicadLibpart:
    """
    eg.
    (libpart (lib "Device") (part "R")
      (description "Resistor")
      (docs "~")
      (footprints
        (fp "R_*"))
      (fields
        (field (name "Reference") "R")
        (field (name "Value") "R")
        (field (name "Datasheet") "~"))
      (pins
        (pin (num "1") (name "") (type "passive"))
        (pin (num "2") (name "") (type "passive"))))
    """

    lib: str
    part: str
    description: str
    docs: str
    footprints: List[str] = field(factory=list)
    fields: List[KicadField] = field(factory=list)
    pins: List[KicadPin] = field(factory=list)


@define
class KicadSheetpath:
    """
    eg. (sheetpath (names "/") (tstamps "/"))
    """

    names: str = "/"  # module path, eg. toy.ato/Vdiv1
    tstamps: str = "/"  # module UID, eg. b1d41e3b-ef4b-4472-9aa4-7860376ef0ce


@define
class KicadComponent:
    """
    eg.
    (comp (ref "R4")
      (value "5R")
      (libsource (lib "Device") (part "R") (description "Resistor"))
      (property (name "Sheetname") (value ""))
      (property (name "Sheetfile") (value "example.kicad_sch"))
      (sheetpath (names "/") (tstamps "/"))
      (tstamps "9c26a741-12df-4e56-baa6-794e6b3aa7cd")))
    """

    ref: str  # eg. "R1" -- should be unique, we should assign these here I think
    value: str  # eg. "10k" -- seems to be an arbitrary string
    libsource: KicadLibpart
    tstamp: str  # component UID, eg. b1d41e3b-ef4b-4472-9aa4-7860376ef0ce
    src_path: str
    footprint: Optional[str] = None  # eg. "Resistor_SMD:R_0603_1608Metric"
    properties: List[KicadField] = field(factory=list)
    fields: List[KicadField] = field(factory=list)
    sheetpath: KicadSheetpath = field(factory=KicadSheetpath)


@define
class KicadNode:
    """
    eg. (node (ref "R1") (pin "1") (pintype "passive"))
    """

    ref: str
    pin: str
    pintype: str = "stereo"


@define
class KicadNet:
    """
    eg.
    (net (code "1") (name "Net-(R1-Pad1)")
      (node (ref "R1") (pin "1") (pintype "passive"))
      (node (ref "R2") (pin "1") (pintype "passive")))
    """

    code: str  # TODO: do these have to be numbers, or can they be more UIDs?
    name: str
    nodes: List[KicadNode] = field(factory=list)


class KicadLibraries:
    """
    eg.
    (libraries
    (library (logical "Device")
      (uri "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols//Device.kicad_sym")))
    """

    def __init__(self):
        # don't believe these are mandatory and I don't think they're useful in the context of atopile
        raise NotImplementedError


@define
class KicadNetlist:
    version: str = "E"  # What does this mean?
    source: str = "unknown"  # eg. "/Users/mattwildoer/Projects/SizzleSack/schematic/sandbox.py" TODO: point this at the sourcefile
    date: str = ""  # NOTE: we don't want a data in here because it'll make a diff in our outputs -- although perhaps it's a useful field for a hash here
    tool: str = "atopile"  # TODO: add version in here too

    components: List[KicadComponent] = field(factory=list)
    libparts: List[KicadLibpart] = field(factory=list)
    nets: List[KicadNet] = field(factory=list)
    """
    (net (code "3") (name "Net-(R2-Pad2)")
      (node (ref "R2") (pin "2") (pintype "passive"))
      (node (ref "R3") (pin "1") (pintype "passive"))
      (node (ref "R4") (pin "1") (pintype "passive")))
    """
