# Type stub file for KiCad PCB structures
# Generated from pcb.zig

KICAD_PCB_VERSION: int = 20241229

# Basic geometry types
class Xy:
    x: float
    y: float

class Xyz:
    x: float
    y: float
    z: float

class Xyr:
    x: float
    y: float
    r: float

class Wh:
    w: float
    h: float | None

# Text and effects structures
class Stroke:
    width: float
    type: str

class Font:
    size: Wh
    thickness: float | None

class Effects:
    font: Font
    hide: bool | None

class TextLayer:
    layer: str
    knockout: str | None

# Shape structures
class Line:
    start: Xy
    end: Xy
    layer: str | None
    width: float | None
    stroke: Stroke | None
    uuid: str

class Arc:
    start: Xy
    mid: Xy
    end: Xy
    layer: str | None
    width: float | None
    stroke: Stroke | None
    uuid: str

class Circle:
    center: Xy
    end: Xy
    layer: str | None
    width: float | None
    stroke: Stroke | None
    fill: str | None
    uuid: str

class Rect:
    start: Xy
    end: Xy
    layer: str | None
    width: float | None
    stroke: Stroke | None
    fill: str | None
    uuid: str

class Pts:
    xys: list[Xy]

class Polygon:
    pts: Pts
    layer: str | None
    width: float | None
    stroke: Stroke | None
    fill: str | None
    uuid: str | None

# Text structures
class Text:
    text: str
    at: Xyr
    layer: str
    uuid: str
    effects: Effects

class FpText:
    type: str
    text: str
    at: Xyr
    layer: str
    hide: bool | None
    uuid: str
    effects: Effects

# Pad and Net structures
Drill = float

class Net:
    number: int
    name: str | None

class Pad:
    name: str
    type: str
    shape: str
    at: Xyr
    size: Wh
    layers: list[str]
    drill: Drill | None
    net: Net | None
    solder_mask_margin: float | None
    solder_paste_margin: float | None
    solder_paste_margin_ratio: float | None
    clearance: float | None
    zone_connect: int | None
    thermal_bridge_width: float | None
    thermal_gap: float | None
    roundrect_rratio: float | None
    chamfer_ratio: float | None
    uuid: str

# Property structure
class Property:
    name: str
    value: str
    at: Xyr
    layer: str
    hide: bool | None
    uuid: str
    effects: Effects

# 3D model structure
class ModelOffset:
    xyz: Xyz

class ModelScale:
    xyz: Xyz

class ModelRotate:
    xyz: Xyz

class Model:
    path: str
    offset: ModelOffset
    scale: ModelScale
    rotate: ModelRotate

# Footprint structure
class Footprint:
    name: str
    layer: str
    uuid: str
    at: Xyr
    path: str | None
    propertys: list[Property]  # Note: 'propertys' to match Zig naming
    fp_texts: list[FpText]
    attr: list[str]
    fp_lines: list[Line]
    fp_arcs: list[Arc]
    fp_circles: list[Circle]
    fp_rects: list[Rect]
    fp_poly: list[Polygon]
    pads: list[Pad]
    models: list[Model]

# Via structure
class Via:
    at: Xy
    size: float
    drill: float
    layers: list[str]
    net: int
    uuid: str

# Zone structures
class Hatch:
    mode: str
    pitch: float

class ConnectPads:
    mode: str | None
    clearance: float

class Fill:
    enable: str | None
    mode: str | None
    thermal_gap: float
    thermal_bridge_width: float

class FilledPolygon:
    layer: str
    pts: Pts

class Zone:
    net: int
    net_name: str
    layers: list[str] | None
    uuid: str
    name: str | None
    hatch: Hatch
    priority: int | None
    connect_pads: ConnectPads
    min_thickness: float
    filled_areas_thickness: bool
    fill: Fill
    polygon: Polygon
    filled_polygon: list[FilledPolygon]

# Track (segment) structures
class Segment:
    start: Xy
    end: Xy
    width: float
    layer: str | None
    net: int
    uuid: str

class ArcSegment:
    start: Xy
    mid: Xy
    end: Xy
    width: float
    layer: str | None
    net: int
    uuid: str

# Board setup structures
class General:
    thickness: float
    legacy_teardrops: bool

class Paper:
    type: str
    size: Xy | None
    orientation: str | None

class TitleBlock:
    title: str | None
    date: str | None
    revision: str | None
    company: str | None
    comment: list["Comment"]

class Comment:
    number: int
    text: str

class Layer:
    number: int
    name: str
    type: str
    alias: str | None

class StackupLayer:
    name: str
    type: str
    color: str | None
    thickness: float | None
    material: str | None
    epsilon_r: float | None
    loss_tangent: float | None

class Stackup:
    layers: list[StackupLayer]
    copper_finish: str | None
    dielectric_constraints: bool | None
    edge_connector: str | None
    castellated_pads: bool | None
    edge_plating: bool | None

class Rules:
    max_error: float
    min_clearance: float
    min_connection: float
    min_copper_edge_clearance: float
    min_hole_clearance: float
    min_hole_to_hole: float
    min_microvia_diameter: float
    min_microvia_drill: float
    min_resolved_spokes: int
    min_silk_clearance: float
    min_text_height: float
    min_text_thickness: float
    min_through_hole_diameter: float
    min_track_width: float
    min_via_annular_width: float
    min_via_diameter: float
    solder_mask_to_copper_clearance: float
    use_height_for_length_calcs: bool

class PcbPlotParams:
    layerselection: str
    plot_on_all_layers_selection: str
    disableapertmacros: bool
    usegerberextensions: bool
    usegerberattributes: bool
    usegerberadvancedattributes: bool
    creategerberjobfile: bool
    dashed_line_dash_ratio: float
    dashed_line_gap_ratio: float
    svgprecision: int
    plotframeref: bool
    viasonmask: bool | None
    mode: int
    useauxorigin: bool
    hpglpennumber: int
    hpglpenspeed: int
    hpglpendiameter: float
    pdf_front_fp_property_popups: bool
    pdf_back_fp_property_popups: bool
    pdf_metadata: bool
    pdf_single_document: bool
    dxfpolygonmode: bool
    dxfimperialunits: bool
    dxfusepcbnewfont: bool
    psnegative: bool
    psa4output: bool
    plot_black_and_white: bool
    plotinvisibletext: bool
    sketchpadsonfab: bool
    plotreference: bool
    plotvalue: bool
    plotpadnumbers: bool
    hidednponfab: bool
    sketchdnponfab: bool
    crossoutdnponfab: bool
    plotfptext: bool
    subtractmaskfromsilk: bool
    outputformat: int
    mirror: bool
    drillshape: int
    scaleselection: int
    outputdirectory: str

class Tenting:
    values: list[str]

class Setup:
    stackup: Stackup | None
    pad_to_mask_clearance: int
    allow_soldermask_bridges_in_footprints: bool
    tenting: list[str] | None
    pcbplotparams: PcbPlotParams
    rules: Rules | None

# Additional structures
class Image:
    at: Xy
    layer: str
    scale: float
    data: str | None
    uuid: str

class DimensionPts:
    xys: list[Xy]

class Dimension:
    type: str
    layer: str
    uuid: str
    pts: DimensionPts
    height: float
    orientation: float | None
    leader_length: float | None
    gr_text: Text

class Group:
    name: str | None
    uuid: str
    locked: bool | None
    members: list[str]

class Target:
    at: Xy
    size: Xy
    width: float
    layer: str

# Main PCB structure
class KicadPcb:
    version: int
    generator: str
    generator_version: str
    general: General
    paper: str | None
    title_block: TitleBlock | None
    layers: list[Layer]
    setup: Setup
    nets: list[Net]
    footprints: list[Footprint]
    vias: list[Via]
    zones: list[Zone]
    segments: list[Segment]
    arcs: list[ArcSegment]
    gr_lines: list[Line]
    gr_arcs: list[Arc]
    gr_circles: list[Circle]
    gr_rects: list[Rect]
    gr_polys: list[Polygon]
    gr_texts: list[Text]
    images: list[Image]
    dimensions: list[Dimension]
    groups: list[Group]
    targets: list[Target]
