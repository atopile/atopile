const std = @import("std");
const structure = @import("../structure.zig");

const str = []const u8;

fn list(comptime T: type) type {
    return std.DoublyLinkedList(T);
}

// Constants
pub const KICAD_PCB_VERSION: i32 = 20241229;
pub const KICAD_FP_VERSION: i32 = 20241229; // Footprint version - same as PCB version

// Basic geometry types
pub const Xy = struct {
    x: f64,
    y: f64,

    pub const fields_meta = .{
        .x = structure.SexpField{ .positional = true },
        .y = structure.SexpField{ .positional = true },
    };
};

pub const Xyz = struct {
    x: f64,
    y: f64,
    z: f64,

    pub const fields_meta = .{
        .x = structure.SexpField{ .positional = true },
        .y = structure.SexpField{ .positional = true },
        .z = structure.SexpField{ .positional = true },
    };
};

pub const Xyr = struct {
    x: f64,
    y: f64,
    r: ?f64 = null,

    pub const fields_meta = .{
        .x = structure.SexpField{ .positional = true },
        .y = structure.SexpField{ .positional = true },
        .r = structure.SexpField{ .positional = true },
    };
};

pub const Wh = struct {
    w: f64,
    h: ?f64 = null,

    pub const fields_meta = .{
        .w = structure.SexpField{ .positional = true },
        .h = structure.SexpField{ .positional = true },
    };
};

pub const E_stroke_type = enum {
    solid,
    dash,
    dash_dot,
    dash_dot_dot,
    dot,
    default,
};

// Text and effects structures
pub const Stroke = struct {
    width: f64,
    type: E_stroke_type,
};

pub const Font = struct {
    size: Wh,
    thickness: ?f64 = null,
    bold: ?bool = null,
    italic: ?bool = null,
};

pub const Justify = struct {
    // null = center/normal
    justify1: ?E_justify = null,
    justify2: ?E_justify = null,
    justify3: ?E_justify = null,

    pub const fields_meta = .{
        .justify1 = structure.SexpField{ .positional = true },
        .justify2 = structure.SexpField{ .positional = true },
        .justify3 = structure.SexpField{ .positional = true },
    };
};

pub const Effects = struct {
    font: Font,
    hide: ?bool = null,
    justify: ?Justify = null,
};

pub const TextLayer = struct {
    layer: str,
    knockout: ?E_knockout = null,

    pub const fields_meta = .{
        .layer = structure.SexpField{ .positional = true },
        .knockout = structure.SexpField{ .positional = true },
    };
};

// Enums
pub const E_justify = enum {
    left,
    right,
    bottom,
    top,
    mirror,
};

pub const E_fill = enum {
    yes,
    no,
    none,
    solid,
};

// Text layer knockout enum
pub const E_knockout = enum {
    knockout,
};

// Paper type enum
pub const E_paper_type = enum {
    A5,
    A4,
    A3,
    A2,
    A1,
    A0,
    A,
    B,
    C,
    D,
    E,
    USLetter,
    USLegal,
    USLedger,
    Custom,
};

// Paper orientation enum
pub const E_paper_orientation = enum {
    portrait,
    landscape,
};

// Layer type enum
pub const E_layer_type = enum {
    signal,
    user,
    mixed,
    jumper,
    power,
};

// Footprint text type enum
pub const E_fp_text_type = enum {
    user,
    reference,
    value,
};

// Pad type enum
pub const E_pad_type = enum {
    thru_hole,
    smd,
    np_thru_hole, // non_plated_through_hole
    connect, // edge_connector
};

// Pad shape enum
pub const E_pad_shape = enum {
    circle,
    rect,
    oval, // stadium
    roundrect,
    custom,
    trapezoid,
    chamfered_rect,
};

// Pad clearance enum
pub const E_pad_clearance = enum {
    outline,
    convexhull,
};

// Pad anchor enum
pub const E_pad_anchor = enum {
    rect,
    circle,
};

// Pad property enum
pub const E_pad_property = enum {
    pad_prop_bga,
    pad_prop_fiducial_glob,
    pad_prop_fiducial_loc,
    pad_prop_testpoint,
    pad_prop_castellated,
    pad_prop_heatsink,
    pad_prop_mechanical,
    none,
};

// Pad chamfer enum
pub const E_pad_chamfer = enum {
    chamfer_top_left,
    chamfer_top_right,
    chamfer_bottom_left,
    chamfer_bottom_right,
};

// Pad drill shape enum
pub const E_pad_drill_shape = enum {
    circle,
    oval, // stadium

    pub const fields_meta = .{
        .circle = .{ .sexp_name = "" },
        .oval = .{ .sexp_name = "oval" },
    };
};

// Pad tenting enum
pub const E_pad_tenting = enum {
    front,
    back,
    none,
};

// Zone connection enum
pub const E_zone_connection = enum(i32) {
    INHERITED = -1,
    NONE = 0,
    THERMAL = 1,
    FULL = 2,
    THT_THERMAL = 3,
};

// Padstack mode enum
pub const E_padstack_mode = enum {
    front_inner_back,
    custom,
};

// Via tenting enum
pub const E_via_tenting = enum {
    front,
    back,
};

// Zone hatch mode enum
pub const E_zone_hatch_mode = enum {
    edge,
    full,
    none,
};

// Zone connect pads mode enum
pub const E_zone_connect_pads_mode = enum {
    no, // none
    yes, // solid
    thermal_reliefs, // empty string in KiCad
    thru_hole_only,
};

// Zone fill mode enum
pub const E_zone_fill_mode = enum {
    hatch,
    polygon,
};

// Zone smoothing enum
pub const E_zone_smoothing = enum {
    fillet,
    chamfer,
    none, // empty string in KiCad
};

// Zone hatch border algorithm enum
pub const E_zone_hatch_border_algorithm = enum {
    hatch_thickness,
    min_thickness, // empty string in KiCad
};

// Zone island removal mode enum
pub const E_zone_island_removal_mode = enum(i32) {
    always = 0,
    do_not_remove = 1,
    below_area_limit = 2,
};

// Zone keepout enum
pub const E_zone_keepout = enum {
    allowed,
    not_allowed,
};

// Zone placement source type enum
pub const E_zone_placement_source_type = enum {
    sheetname,
    component_class,
};

// Zone teardrop type enum
pub const E_zone_teardrop_type = enum {
    padvia,
    track_end,
};

// Dimension type enum
pub const E_dimension_type = enum {
    aligned,
    orthogonal,
    leader,
    center,
    radial,
};

// Dimension arrow direction enum
pub const E_dimension_arrow_direction = enum {
    inward,
    outward,
};

// Stackup copper finish enum
pub const E_copper_finish = enum {
    ENIG,
    ENEPIG,
    @"HAL SnPb",
    @"HAL lead-free",
    @"Hard Gold",
    @"Immersion tin",
    @"Immersion silver",
    @"Immersion nickel",
    @"Immersion gold",
    OSP,
    HT_OSP,
    None,
    @"User defined",
};

// Stackup edge connector enum
pub const E_edge_connector = enum {
    bevelled,
    yes,
};

// Embedded file type enum
pub const E_embedded_file_type = enum {
    other,
    model,
    font,
    datasheet,
    worksheet,
};

// Shapes

pub const Line = struct {
    start: Xy,
    end: Xy,

    // shape common
    solder_mask_margin: ?f64 = null,
    stroke: ?Stroke = null,
    fill: ?E_fill = null,
    layer: ?str = null,
    layers: list(str) = .{},
    locked: ?bool = null,
    uuid: ?str = null,

    pub const fields_meta = .{
        .start = structure.SexpField{ .order = -2 },
        .end = structure.SexpField{ .order = -1 },
        .uuid = structure.SexpField{ .order = 100 },
    };
};

pub const Arc = struct {
    start: Xy,
    mid: Xy,
    end: Xy,

    // shape common
    solder_mask_margin: ?f64 = null,
    stroke: ?Stroke = null,
    fill: ?E_fill = null,
    layer: ?str = null,
    layers: list(str) = .{},
    locked: ?bool = null,
    uuid: ?str = null,

    pub const fields_meta = .{
        .start = structure.SexpField{ .order = -3 },
        .mid = structure.SexpField{ .order = -2 },
        .end = structure.SexpField{ .order = -1 },
        .uuid = structure.SexpField{ .order = 100 },
    };
};

pub const Circle = struct {
    center: Xy,
    end: Xy,

    // shape common
    solder_mask_margin: ?f64 = null,
    stroke: ?Stroke = null,
    fill: ?E_fill = null,
    layer: ?str = null,
    layers: list(str) = .{},
    locked: ?bool = null,
    uuid: ?str = null,

    pub const fields_meta = .{
        .center = structure.SexpField{ .order = -2 },
        .end = structure.SexpField{ .order = -1 },
        .uuid = structure.SexpField{ .order = 100 },
    };
};

pub const Rect = struct {
    start: Xy,
    end: Xy,

    // shape common
    solder_mask_margin: ?f64 = null,
    stroke: ?Stroke = null,
    fill: ?E_fill = null,
    layer: ?str = null,
    layers: list(str) = .{},
    locked: ?bool = null,
    uuid: ?str = null,

    pub const fields_meta = .{
        .start = structure.SexpField{ .order = -2 },
        .end = structure.SexpField{ .order = -1 },
        .uuid = structure.SexpField{ .order = 100 },
    };
};

pub const Pts = struct {
    xys: list(Xy) = .{},

    pub const fields_meta = .{
        .xys = structure.SexpField{ .multidict = true, .sexp_name = "xy" },
    };
};

pub const Polygon = struct {
    pts: Pts,

    // shape common
    solder_mask_margin: ?f64 = null,
    stroke: ?Stroke = null,
    fill: ?E_fill = null,
    layer: ?str = null,
    layers: list(str) = .{},
    locked: ?bool = null,
    uuid: ?str = null,

    pub const fields_meta = .{
        .pts = structure.SexpField{ .order = -1 },
        .uuid = structure.SexpField{ .order = 100 },
    };
};

pub const Curve = struct {
    pts: Pts,

    // shape common
    solder_mask_margin: ?f64 = null,
    stroke: ?Stroke = null,
    fill: ?E_fill = null,
    layer: ?str = null,
    layers: list(str) = .{},
    locked: ?bool = null,
    uuid: ?str = null,

    pub const fields_meta = .{
        .pts = structure.SexpField{ .order = -1 },
        .uuid = structure.SexpField{ .order = 100 },
    };
};

// Text structures
pub const Text = struct {
    text: str,
    at: Xyr,
    layer: str,
    uuid: ?str = null,
    effects: Effects,

    pub const fields_meta = .{
        .text = structure.SexpField{ .positional = true },
    };
};

pub const FpText = struct {
    type: E_fp_text_type,
    text: str,
    at: Xyr,
    layer: TextLayer,
    hide: ?bool = null,
    uuid: ?str = null,
    effects: Effects,

    pub const fields_meta = .{
        .type = structure.SexpField{ .positional = true },
        .text = structure.SexpField{ .positional = true },
    };
};

// Pad structures
pub const Drill = f64;

// PadDrill can be either a simple number (drill 1.2) or a structured drill with shape/size/offset
pub const PadDrill = struct {
    shape: ?E_pad_drill_shape = null,
    size_x: ?f64 = null,
    size_y: ?f64 = null,
    offset: ?Xy = null,

    pub const fields_meta = .{
        .shape = structure.SexpField{ .positional = true },
        .size_x = structure.SexpField{ .positional = true },
        .size_y = structure.SexpField{ .positional = true },
        .offset = structure.SexpField{},
    };
};

pub const PadOptions = struct {
    clearance: ?E_pad_clearance = null,
    anchor: ?E_pad_anchor = null,
};

pub const PadTenting = struct {
    type: E_pad_tenting,

    pub const fields_meta = .{
        .type = structure.SexpField{ .positional = true },
    };
};

pub const Pad = struct {
    name: str,
    type: E_pad_type,
    shape: E_pad_shape,
    at: Xyr,
    size: Wh,
    drill: ?PadDrill = null,
    layers: list(str) = .{},
    remove_unused_layers: ?bool = null,
    net: ?Net = null,
    solder_mask_margin: ?f64 = null,
    solder_paste_margin: ?f64 = null,
    solder_paste_margin_ratio: ?f64 = null,
    clearance: ?f64 = null,
    zone_connect: ?E_zone_connection = null,
    thermal_bridge_width: ?f64 = null,
    thermal_gap: ?f64 = null,
    roundrect_rratio: ?f64 = null,
    chamfer_ratio: ?f64 = null,
    chamfer: ?E_pad_chamfer = null,
    properties: ?E_pad_property = null,
    options: ?PadOptions = null,
    tenting: ?PadTenting = null,
    uuid: ?str = null,

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
        .type = structure.SexpField{ .positional = true },
        .shape = structure.SexpField{ .positional = true },
    };
};

// Net structure
pub const Net = struct {
    number: i32,
    name: ?str = null,

    pub const fields_meta = .{
        .number = structure.SexpField{ .positional = true },
        .name = structure.SexpField{ .positional = true },
    };
};

// Property structure
pub const Property = struct {
    name: str,
    value: str,
    at: Xyr,
    unlocked: ?bool = null,
    layer: str,
    hide: ?bool = null,
    uuid: ?str = null,
    effects: ?Effects = null,

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
        .value = structure.SexpField{ .positional = true },
    };
};

pub const ModelXyz = struct {
    xyz: Xyz,
};

// 3D model structure
pub const Model = struct {
    path: str,
    offset: ModelXyz,
    scale: ModelXyz,
    rotate: ModelXyz,

    pub const fields_meta = .{
        .path = structure.SexpField{ .positional = true },
    };
};

pub const E_Attr = enum {
    smd,
    dnp,
    board_only,
    through_hole,
    exclude_from_pos_files,
    exclude_from_bom,
    allow_missing_courtyard,
};

// Footprint structure
pub const Footprint = struct {
    name: str,
    layer: str = "F.Cu",
    uuid: ?str = null,
    at: Xyr,
    path: ?str = null,
    propertys: list(Property) = .{},
    attr: list(E_Attr) = .{},
    fp_lines: list(Line) = .{},
    fp_arcs: list(Arc) = .{},
    fp_circles: list(Circle) = .{},
    fp_rects: list(Rect) = .{},
    fp_poly: list(Polygon) = .{},
    fp_texts: list(FpText) = .{},
    pads: list(Pad) = .{},
    embedded_fonts: ?bool = null,
    models: list(Model) = .{},

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
        .propertys = structure.SexpField{ .multidict = true, .sexp_name = "property" },
        .fp_texts = structure.SexpField{ .multidict = true, .sexp_name = "fp_text" },
        .fp_lines = structure.SexpField{ .multidict = true, .sexp_name = "fp_line" },
        .fp_arcs = structure.SexpField{ .multidict = true, .sexp_name = "fp_arc" },
        .fp_circles = structure.SexpField{ .multidict = true, .sexp_name = "fp_circle" },
        .fp_rects = structure.SexpField{ .multidict = true, .sexp_name = "fp_rect" },
        .fp_poly = structure.SexpField{ .multidict = true },
        .pads = structure.SexpField{ .multidict = true, .sexp_name = "pad" },
        .models = structure.SexpField{ .multidict = true, .sexp_name = "model" },
    };
};

// Via layer structure
pub const ViaLayer = struct {
    name: str,
    size: ?Xy = null,
    thermal_gap: ?f64 = null,
    thermal_bridge_width: ?f64 = null,
    thermal_bridge_angle: ?f64 = null,
    zone_connect: ?E_zone_connection = null,
};

// Via structure
pub const ViaPadstack = struct {
    mode: E_padstack_mode,
    layers: list(ViaLayer) = .{},

    pub const fields_meta = .{
        .mode = structure.SexpField{ .positional = true },
        .layers = structure.SexpField{ .multidict = true, .sexp_name = "layer" },
    };
};

pub const ViaTenting = struct {
    front: bool = false,
    back: bool = false,
};

pub const Via = struct {
    at: Xy,
    size: f64,
    drill: f64,
    layers: list(str) = .{},
    net: i32,
    remove_unused_layers: ?bool = null,
    keep_end_layers: ?bool = null,
    zone_layer_connections: list(str) = .{},
    padstack: ?ViaPadstack = null,
    teardrops: ?Teardrop = null,
    tenting: ?ViaTenting = null,
    free: ?bool = null,
    locked: ?bool = null,
    uuid: ?str = null,
};

// Zone structures
pub const Hatch = struct {
    mode: E_zone_hatch_mode,
    pitch: f64,

    pub const fields_meta = .{
        .mode = structure.SexpField{ .positional = true },
        .pitch = structure.SexpField{ .positional = true },
    };
};

pub const ConnectPads = struct {
    mode: ?E_zone_connect_pads_mode = null,
    clearance: ?f64 = null,
};

pub const E_zone_fill_enable = enum {
    yes,
};

pub const ZoneFill = struct {
    enable: ?E_zone_fill_enable = null,
    mode: ?E_zone_fill_mode = null,
    hatch_thickness: ?f64 = null,
    hatch_gap: ?f64 = null,
    hatch_orientation: ?f64 = null,
    hatch_smoothing_level: ?f64 = null,
    hatch_smoothing_value: ?f64 = null,
    hatch_border_algorithm: ?E_zone_hatch_border_algorithm = null,
    hatch_min_hole_area: ?f64 = null,
    arc_segments: ?i32 = null,
    thermal_gap: ?f64 = null,
    thermal_bridge_width: ?f64 = null,
    smoothing: ?E_zone_smoothing = null,
    radius: ?f64 = null,
    //island_removal_mode: ?E_zone_island_removal_mode = null,
    island_removal_mode: ?i32 = null,
    island_area_min: ?f64 = null,

    pub const fields_meta = .{
        .enable = structure.SexpField{ .positional = true },
    };
};

pub const FilledPolygon = struct {
    layer: str,
    pts: Pts,
};

pub const ZoneKeepout = struct {
    tracks: E_zone_keepout,
    vias: E_zone_keepout,
    pads: E_zone_keepout,
    copperpour: E_zone_keepout,
    footprints: E_zone_keepout,
};

pub const ZonePlacement = struct {
    source_type: ?E_zone_placement_source_type = null,
    source: ?str = null,
    enabled: bool = true,
    sheetname: ?str = null,
};

pub const ZoneTeardrop = struct {
    type: E_zone_teardrop_type,
};

pub const ZoneAttr = struct {
    teardrop: ?ZoneTeardrop = null,
};

pub const Zone = struct {
    net: i32,
    net_name: str,
    layer: ?str = null,
    layers: list(str) = .{},
    uuid: ?str = null,
    name: ?str = null,
    hatch: Hatch,
    priority: ?i32 = null,
    attr: ?ZoneAttr = null,
    connect_pads: ?ConnectPads = null,
    min_thickness: ?f64 = null,
    filled_areas_thickness: ?bool = null,
    keepout: ?ZoneKeepout = null,
    placement: ?ZonePlacement = null,
    fill: ?ZoneFill = null,
    polygon: Polygon,
    filled_polygon: list(FilledPolygon) = .{},

    pub const fields_meta = .{
        .filled_polygon = structure.SexpField{ .multidict = true },
    };
};

// Track (segment) structures
pub const Segment = struct {
    start: Xy,
    end: Xy,
    width: f64,
    layer: ?str = null,
    net: i32,
    uuid: ?str = null,

    pub const fields_meta = .{
        .start = structure.SexpField{ .order = -3 },
        .end = structure.SexpField{ .order = -2 },
        .width = structure.SexpField{ .order = -1 },
    };
};

pub const ArcSegment = struct {
    start: Xy,
    mid: Xy,
    end: Xy,
    width: f64,
    layer: ?str = null,
    net: i32,
    uuid: ?str = null,
};

// Board setup structures
pub const General = struct {
    thickness: f64 = 1.6,
    legacy_teardrops: bool = false,
};

pub const Paper = struct {
    type: E_paper_type = .A4,
    size: ?Xy = null,
    orientation: ?E_paper_orientation = null,

    pub const fields_meta = .{
        .type = structure.SexpField{ .positional = true, .symbol = false },
        .size = structure.SexpField{ .positional = true },
        .orientation = structure.SexpField{ .positional = true },
    };
};

pub const TitleBlock = struct {
    title: ?str = null,
    date: ?str = null,
    revision: ?str = null,
    company: ?str = null,
    comment: list(Comment) = .{},

    pub const fields_meta = .{
        .comment = structure.SexpField{ .multidict = true },
    };
};

pub const Comment = struct {
    number: i32,
    text: str,

    pub const fields_meta = .{
        .number = structure.SexpField{ .positional = true },
        .text = structure.SexpField{ .positional = true },
    };
};

pub const Layer = struct {
    number: i32,
    name: str,
    type: E_layer_type,
    alias: ?str = null,

    pub const fields_meta = .{
        .number = structure.SexpField{ .positional = true },
        .name = structure.SexpField{ .positional = true },
        .type = structure.SexpField{ .positional = true, .symbol = true },
        .alias = structure.SexpField{ .positional = true },
    };
};

pub const Stackup = struct {
    layers: list(StackupLayer) = .{},
    copper_finish: ?E_copper_finish = null,
    dielectric_constraints: ?bool = null,
    edge_connector: ?E_edge_connector = null,
    castellated_pads: ?bool = null,
    edge_plating: ?bool = null,

    pub const fields_meta = .{
        .layers = structure.SexpField{ .multidict = true, .sexp_name = "layer" },
        .copper_finish = structure.SexpField{ .symbol = false },
    };
};

pub const StackupLayer = struct {
    name: str,
    type: str,
    color: ?str = null,
    thickness: ?f64 = null,
    material: ?str = null,
    epsilon_r: ?f64 = null,
    loss_tangent: ?f64 = null,

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
    };
};

pub const Rules = struct {
    max_error: f64 = 0.005,
    min_clearance: f64 = 0.0,
    min_connection: f64 = 0.0,
    min_copper_edge_clearance: f64 = 0.5,
    min_hole_clearance: f64 = 0.25,
    min_hole_to_hole: f64 = 0.25,
    min_microvia_diameter: f64 = 0.2,
    min_microvia_drill: f64 = 0.1,
    min_resolved_spokes: i32 = 2,
    min_silk_clearance: f64 = 0.0,
    min_text_height: f64 = 0.8,
    min_text_thickness: f64 = 0.08,
    min_through_hole_diameter: f64 = 0.3,
    min_track_width: f64 = 0.0,
    min_via_annular_width: f64 = 0.1,
    min_via_diameter: f64 = 0.5,
    solder_mask_to_copper_clearance: f64 = 0.0,
    use_height_for_length_calcs: bool = true,
};

pub const PcbPlotParams = struct {
    layerselection: str = "0x00010fc_ffffffff",
    plot_on_all_layers_selection: str = "0x0000000_00000000",
    disableapertmacros: ?bool = null,
    usegerberextensions: ?bool = null,
    usegerberattributes: ?bool = null,
    usegerberadvancedattributes: ?bool = null,
    creategerberjobfile: ?bool = null,
    dashed_line_dash_ratio: f64 = 12.0,
    dashed_line_gap_ratio: f64 = 3.0,
    svgprecision: i32 = 4,
    plotframeref: ?bool = null,
    viasonmask: ?bool = null,
    mode: i32 = 1,
    useauxorigin: ?bool = null,
    hpglpennumber: i32 = 1,
    hpglpenspeed: i32 = 20,
    hpglpendiameter: f64 = 15.0,
    pdf_front_fp_property_popups: ?bool = null,
    pdf_back_fp_property_popups: ?bool = null,
    pdf_metadata: ?bool = null,
    pdf_single_document: ?bool = null,
    dxfpolygonmode: ?bool = null,
    dxfimperialunits: ?bool = null,
    dxfusepcbnewfont: ?bool = null,
    psnegative: ?bool = null,
    psa4output: ?bool = null,
    plot_black_and_white: ?bool = null,
    plotinvisibletext: ?bool = null,
    sketchpadsonfab: ?bool = null,
    plotreference: ?bool = null,
    plotvalue: ?bool = null,
    plotpadnumbers: ?bool = null,
    hidednponfab: ?bool = null,
    sketchdnponfab: ?bool = null,
    crossoutdnponfab: ?bool = null,
    plotfptext: ?bool = null,
    subtractmaskfromsilk: ?bool = null,
    outputformat: i32 = 1,
    mirror: ?bool = null,
    drillshape: i32 = 1,
    scaleselection: i32 = 1,
    outputdirectory: str = "",

    pub const fields_meta = .{
        .layerselection = structure.SexpField{ .symbol = true },
        .plot_on_all_layers_selection = structure.SexpField{ .symbol = true },
    };
};

// Special struct for tenting that encodes as positional symbols
pub const Tenting = struct {
    values: list(str) = .{},
};

pub const Setup = struct {
    stackup: ?Stackup = null,
    pad_to_mask_clearance: i32 = 0,
    allow_soldermask_bridges_in_footprints: bool = false,
    tenting: list(str) = .{},
    pcbplotparams: PcbPlotParams = .{},
    rules: ?Rules = null,

    pub const fields_meta = .{
        .tenting = structure.SexpField{ .symbol = true },
    };
};

// Main PCB structure
pub const KicadPcb = struct {
    version: i32 = KICAD_PCB_VERSION,
    generator: str,
    generator_version: str,
    general: General = .{},
    paper: ?E_paper_type = null,
    title_block: ?TitleBlock = null,
    layers: list(Layer) = .{},
    setup: Setup = .{},
    nets: list(Net) = .{},
    footprints: list(Footprint) = .{},
    vias: list(Via) = .{},
    segments: list(Segment) = .{},
    arcs: list(ArcSegment) = .{},
    gr_lines: list(Line) = .{},
    gr_arcs: list(Arc) = .{},
    gr_curves: list(Curve) = .{},
    gr_circles: list(Circle) = .{},
    gr_rects: list(Rect) = .{},
    gr_polys: list(Polygon) = .{},
    gr_texts: list(Text) = .{},
    gr_text_boxes: list(TextBox) = .{},
    zones: list(Zone) = .{},
    images: list(Image) = .{},
    dimensions: list(Dimension) = .{},
    groups: list(Group) = .{},
    targets: list(Target) = .{},
    embedded_fonts: ?bool = null,
    embedded_files: ?EmbeddedFiles = null,
    tables: list(Table) = .{},
    generateds: list(Generated) = .{},

    pub const fields_meta = .{
        // Note: layers is NOT multidict - it's a single (layers ...) entry containing multiple Layer items
        .nets = structure.SexpField{ .multidict = true, .sexp_name = "net" },
        .footprints = structure.SexpField{ .multidict = true, .sexp_name = "footprint" },
        .vias = structure.SexpField{ .multidict = true, .sexp_name = "via" },
        .zones = structure.SexpField{ .multidict = true, .sexp_name = "zone" },
        .segments = structure.SexpField{ .multidict = true, .sexp_name = "segment" },
        .arcs = structure.SexpField{ .multidict = true, .sexp_name = "arc" },
        .gr_lines = structure.SexpField{ .multidict = true, .sexp_name = "gr_line" },
        .gr_arcs = structure.SexpField{ .multidict = true, .sexp_name = "gr_arc" },
        .gr_curves = structure.SexpField{ .multidict = true, .sexp_name = "gr_curve" },
        .gr_circles = structure.SexpField{ .multidict = true, .sexp_name = "gr_circle" },
        .gr_rects = structure.SexpField{ .multidict = true, .sexp_name = "gr_rect" },
        .gr_polys = structure.SexpField{ .multidict = true, .sexp_name = "gr_poly" },
        .gr_texts = structure.SexpField{ .multidict = true, .sexp_name = "gr_text" },
        .gr_text_boxes = structure.SexpField{ .multidict = true, .sexp_name = "gr_text_box" },
        .images = structure.SexpField{ .multidict = true, .sexp_name = "image" },
        .dimensions = structure.SexpField{ .multidict = true, .sexp_name = "dimension" },
        .groups = structure.SexpField{ .multidict = true, .sexp_name = "group" },
        .targets = structure.SexpField{ .multidict = true, .sexp_name = "target" },
        .generateds = structure.SexpField{ .multidict = true, .sexp_name = "generated" },
        .tables = structure.SexpField{ .multidict = true, .sexp_name = "table" },
        .paper = structure.SexpField{ .symbol = false },
    };
};

pub const Generated = struct {
    uuid: str,
    type: str,
    name: str,
    layer: str,
    members: list(str) = .{},
    locked: ?bool = null,
};

pub const Image = struct {
    at: Xy,
    layer: str,
    scale: f64 = 1.0,
    data: list(str) = .{},
    uuid: ?str = null,
};

pub const EmbeddedFile = struct {
    name: str,
    type: E_embedded_file_type,
    data: list(str) = .{},
    checksum: ?str = null,
};

pub const EmbeddedFiles = struct {
    files: list(EmbeddedFile) = .{},

    pub const fields_meta = .{
        .files = structure.SexpField{ .multidict = true, .sexp_name = "file" },
    };
};

pub const Teardrop = struct {
    enabled: bool = false,
    allow_two_segments: bool = false,
    prefer_zone_connections: bool = true,
    best_length_ratio: f64,
    max_length: f64,
    best_width_ratio: f64,
    max_width: f64,
    curved_edges: bool,
    filter_ratio: f64,
};

pub const RenderCache = struct {
    text: str = "",
    rotation: f64 = 0,
    polygons: list(Polygon) = .{},

    pub const fields_meta = .{
        .text = structure.SexpField{ .positional = true },
        .rotation = structure.SexpField{ .positional = true },
        .polygons = structure.SexpField{ .multidict = true },
    };
};

pub const Margins = struct {
    left: f64,
    top: f64,
    right: f64,
    bottom: f64,

    pub const fields_meta = .{
        .left = structure.SexpField{ .positional = true },
        .top = structure.SexpField{ .positional = true },
        .right = structure.SexpField{ .positional = true },
        .bottom = structure.SexpField{ .positional = true },
    };
};

pub const Span = struct {
    cols: i32,
    rows: i32,

    pub const fields_meta = .{
        .cols = structure.SexpField{ .positional = true },
        .rows = structure.SexpField{ .positional = true },
    };
};

pub const TextBox = struct {
    text: str,
    start: ?Xy = null,
    end: ?Xy = null,
    pts: ?Pts = null,
    margins: ?Margins = null,
    angle: ?f64 = null,
    layer: str,
    uuid: ?str = null,
    effects: Effects,
    border: ?bool = null,
    stroke: ?Stroke = null,
    locked: ?bool = null,
    //span: ?Span = null,
    //render_cache: ?RenderCache = null,

    pub const fields_meta = .{
        .text = structure.SexpField{ .positional = true },
    };
};

pub const TableCell = struct {
    text: str,
    locked: bool = false,
    start: ?Xy = null,
    end: ?Xy = null,
    pts: ?Pts = null,
    angle: ?f64 = null,
    stroke: ?Stroke = null,
    border: ?bool = null,
    margins: ?Margins = null,
    layer: str,
    span: ?Span = null,
    effects: Effects,
    render_cache: ?RenderCache = null,
    uuid: ?str = null,

    pub const fields_meta = .{
        .text = structure.SexpField{ .positional = true },
    };
};

pub const Cells = struct {
    table_cells: list(TableCell) = .{},

    pub const fields_meta = .{
        .table_cells = structure.SexpField{ .multidict = true },
    };
};

pub const Border = struct {
    external: bool,
    header: bool,
    stroke: Stroke,
};

pub const Separator = struct {
    rows: bool,
    cols: bool,
    stroke: Stroke,
};

pub const Table = struct {
    column_count: i32,
    locked: ?bool = null,
    layer: str,
    column_widths: list(f64) = .{},
    row_heights: list(f64) = .{},
    cells: Cells,
    border: Border,
    separators: Separator,
};

pub const DimensionPts = struct {
    xys: list(Xy) = .{},

    pub const fields_meta = .{
        .xys = structure.SexpField{ .multidict = true, .sexp_name = "xy" },
    };
};

pub const DimensionFormat = struct {
    prefix: str,
    suffix: str,
    units: i32,
    units_format: i32,
    precision: i32,
    override_value: ?str = null,
    suppress_zeroes: bool = false,
};

pub const DimensionStyle = struct {
    thickness: ?f64 = null,
    arrow_length: ?f64 = null,
    arrow_direction: E_dimension_arrow_direction = .outward,
    text_position_mode: ?i32 = null,
    extension_height: ?f64 = null,
    extension_offset: ?f64 = null,
    keep_text_aligned: bool = true,
    text_frame: ?i32 = null,
};

pub const Dimension = struct {
    type: E_dimension_type,
    layer: str,
    uuid: ?str = null,
    pts: DimensionPts,
    height: f64,
    orientation: ?f64 = null,
    leader_length: ?f64 = null,
    format: ?DimensionFormat = null,
    style: ?DimensionStyle = null,
    gr_text: Text,
};

pub const Group = struct {
    name: ?str = null,
    uuid: ?str = null,
    locked: ?bool = null,
    members: list(str) = .{},

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
    };
};

pub const Target = struct {
    at: Xy,
    size: Xy,
    width: f64,
    layer: str,
    uuid: ?str = null,
};

// File structure
pub const PcbFile = struct {
    kicad_pcb: KicadPcb,

    const root_symbol = "kicad_pcb";

    pub fn loads(allocator: std.mem.Allocator, in: structure.input) !PcbFile {
        const pcb = try structure.loads(KicadPcb, allocator, in, root_symbol);
        return PcbFile{
            .kicad_pcb = pcb,
        };
    }

    pub fn dumps(self: PcbFile, allocator: std.mem.Allocator, out: structure.output) !void {
        try structure.dumps(self.kicad_pcb, allocator, root_symbol, out);
    }

    pub fn free(self: *PcbFile, allocator: std.mem.Allocator) void {
        structure.free(KicadPcb, allocator, self.kicad_pcb);
    }
};
