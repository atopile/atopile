const std = @import("std");
const structure = @import("../structure.zig");

const str = []const u8;

// Constants
pub const KICAD_PCB_VERSION: i32 = 20241229;

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
    r: f64 = 0,

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

// Text and effects structures
pub const Stroke = struct {
    width: f64,
    type: str,
};

pub const Font = struct {
    size: Wh,
    thickness: ?f64 = null,
};

pub const Effects = struct {
    font: Font,
    hide: ?bool = null,
    // justifys: []Justify = &.{}, // TODO: implement justify
};

pub const TextLayer = struct {
    layer: str,
    knockout: ?str = null,

    pub const fields_meta = .{
        .layer = structure.SexpField{ .positional = true },
        .knockout = structure.SexpField{ .positional = true },
    };
};

// Shapes
pub const Line = struct {
    start: Xy,
    end: Xy,
    layer: ?str = null,
    width: ?f64 = null,
    stroke: ?Stroke = null,
    uuid: str,

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
    layer: ?str = null,
    width: ?f64 = null,
    stroke: ?Stroke = null,
    uuid: str,

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
    layer: ?str = null,
    width: ?f64 = null,
    stroke: ?Stroke = null,
    fill: ?str = null,
    uuid: str,

    pub const fields_meta = .{
        .center = structure.SexpField{ .order = -2 },
        .end = structure.SexpField{ .order = -1 },
        .uuid = structure.SexpField{ .order = 100 },
    };
};

pub const Rect = struct {
    start: Xy,
    end: Xy,
    layer: ?str = null,
    width: ?f64 = null,
    stroke: ?Stroke = null,
    fill: ?str = null,
    uuid: str,

    pub const fields_meta = .{
        .start = structure.SexpField{ .order = -2 },
        .end = structure.SexpField{ .order = -1 },
        .uuid = structure.SexpField{ .order = 100 },
    };
};

pub const Pts = struct {
    xys: []Xy = &.{},

    pub const fields_meta = .{
        .xys = structure.SexpField{ .multidict = true, .sexp_name = "xy" },
    };
};

pub const Polygon = struct {
    pts: Pts,
    layer: ?str = null,
    width: ?f64 = null,
    stroke: ?Stroke = null,
    fill: ?str = null,
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
    uuid: str,
    effects: Effects,

    pub const fields_meta = .{
        .text = structure.SexpField{ .positional = true },
    };
};

pub const FpText = struct {
    type: str,
    text: str,
    at: Xyr,
    layer: str,
    hide: ?bool = null,
    uuid: str,
    effects: Effects,

    pub const fields_meta = .{
        .type = structure.SexpField{ .positional = true },
        .text = structure.SexpField{ .positional = true },
    };
};

// Pad structures
pub const Drill = f64;

pub const Pad = struct {
    name: str,
    type: str,
    shape: str,
    at: Xyr,
    size: Wh,
    layers: []str,
    drill: ?Drill = null,
    net: ?Net = null,
    solder_mask_margin: ?f64 = null,
    solder_paste_margin: ?f64 = null,
    solder_paste_margin_ratio: ?f64 = null,
    clearance: ?f64 = null,
    zone_connect: ?i32 = null,
    thermal_bridge_width: ?f64 = null,
    thermal_gap: ?f64 = null,
    roundrect_rratio: ?f64 = null,
    chamfer_ratio: ?f64 = null,
    uuid: str,

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
    layer: str,
    hide: ?bool = null,
    uuid: str,
    effects: Effects,

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

// Footprint structure
pub const Footprint = struct {
    name: str,
    layer: str = "F.Cu",
    uuid: str,
    at: Xyr,
    path: ?str = null,
    propertys: []Property = &.{},
    fp_texts: []FpText = &.{},
    attr: []str = &.{},
    fp_lines: []Line = &.{},
    fp_arcs: []Arc = &.{},
    fp_circles: []Circle = &.{},
    fp_rects: []Rect = &.{},
    fp_poly: []Polygon = &.{},
    pads: []Pad = &.{},
    models: []Model = &.{},

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

// Via structure
pub const Via = struct {
    at: Xy,
    size: f64,
    drill: f64,
    layers: []str = &.{},
    net: i32,
    uuid: str,
};

// Zone structures
pub const Hatch = struct {
    mode: str,
    pitch: f64,

    pub const fields_meta = .{
        .mode = structure.SexpField{ .positional = true },
        .pitch = structure.SexpField{ .positional = true },
    };
};

pub const ConnectPads = struct {
    mode: ?str = null,
    clearance: f64,

    pub const fields_meta = .{
        .mode = structure.SexpField{ .positional = true },
    };
};

pub const Fill = struct {
    enable: ?str = null,
    mode: ?str = null,
    thermal_gap: f64,
    thermal_bridge_width: f64,

    pub const fields_meta = .{
        .enable = structure.SexpField{ .positional = true },
    };
};

pub const FilledPolygon = struct {
    layer: str,
    pts: Pts,
};

pub const Zone = struct {
    net: i32,
    net_name: str,
    layers: ?[]str = null,
    uuid: str,
    name: ?str = null,
    hatch: Hatch,
    priority: ?i32 = null,
    connect_pads: ConnectPads,
    min_thickness: f64,
    filled_areas_thickness: bool,
    fill: Fill,
    polygon: Polygon,
    filled_polygon: []FilledPolygon = &.{},

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
    uuid: str,

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
    uuid: str,
};

// Board setup structures
pub const General = struct {
    thickness: f64 = 1.6,
    legacy_teardrops: bool = false,
};

pub const Paper = struct {
    type: str = "A4",
    size: ?Xy = null,
    orientation: ?str = null,

    pub const fields_meta = .{
        .type = structure.SexpField{ .positional = true },
        .size = structure.SexpField{ .positional = true },
        .orientation = structure.SexpField{ .positional = true },
    };
};

pub const TitleBlock = struct {
    title: ?str = null,
    date: ?str = null,
    revision: ?str = null,
    company: ?str = null,
    comment: []Comment = &.{},

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
    type: str,
    alias: ?str = null,

    pub const fields_meta = .{
        .number = structure.SexpField{ .positional = true },
        .name = structure.SexpField{ .positional = true },
        .type = structure.SexpField{ .positional = true, .symbol = true },
        .alias = structure.SexpField{ .positional = true },
    };
};

pub const Stackup = struct {
    layers: []StackupLayer = &.{},
    copper_finish: ?str = null,
    dielectric_constraints: ?bool = null,
    edge_connector: ?str = null,
    castellated_pads: ?bool = null,
    edge_plating: ?bool = null,

    pub const fields_meta = .{
        .layers = structure.SexpField{ .multidict = true, .sexp_name = "layer" },
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
    disableapertmacros: bool = false,
    usegerberextensions: bool = false,
    usegerberattributes: bool = true,
    usegerberadvancedattributes: bool = true,
    creategerberjobfile: bool = true,
    dashed_line_dash_ratio: f64 = 12.0,
    dashed_line_gap_ratio: f64 = 3.0,
    svgprecision: i32 = 4,
    plotframeref: bool = false,
    viasonmask: ?bool = null,
    mode: i32 = 1,
    useauxorigin: bool = false,
    hpglpennumber: i32 = 1,
    hpglpenspeed: i32 = 20,
    hpglpendiameter: f64 = 15.0,
    pdf_front_fp_property_popups: bool = true,
    pdf_back_fp_property_popups: bool = true,
    pdf_metadata: bool = true,
    pdf_single_document: bool = false,
    dxfpolygonmode: bool = true,
    dxfimperialunits: bool = true,
    dxfusepcbnewfont: bool = true,
    psnegative: bool = false,
    psa4output: bool = false,
    plot_black_and_white: bool = true,
    plotinvisibletext: bool = false,
    sketchpadsonfab: bool = false,
    plotreference: bool = true,
    plotvalue: bool = true,
    plotpadnumbers: bool = false,
    hidednponfab: bool = false,
    sketchdnponfab: bool = true,
    crossoutdnponfab: bool = true,
    plotfptext: bool = true,
    subtractmaskfromsilk: bool = false,
    outputformat: i32 = 1,
    mirror: bool = false,
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
    values: []str,

    // Custom encoding to output values as positional symbols
    pub fn encode(self: Tenting, allocator: std.mem.Allocator) !structure.SExp {
        var items = try allocator.alloc(structure.SExp, self.values.len);
        for (self.values, 0..) |val, i| {
            items[i] = structure.SExp{ .value = .{ .symbol = val }, .location = null };
        }
        return structure.SExp{ .value = .{ .list = items }, .location = null };
    }
};

pub const Setup = struct {
    stackup: ?Stackup = null,
    pad_to_mask_clearance: i32 = 0,
    allow_soldermask_bridges_in_footprints: bool = false,
    tenting: ?[]str = null,
    pcbplotparams: PcbPlotParams = .{},
    rules: ?Rules = null,

    pub const fields_meta = .{
        .tenting = structure.SexpField{ .symbol = true },
    };
};

// Main PCB structure
pub const KicadPcb = struct {
    version: i32,
    generator: str,
    generator_version: str,
    general: General = .{},
    paper: ?str = null,
    title_block: ?TitleBlock = null,
    layers: []Layer = &.{},
    setup: Setup = .{},
    nets: []Net = &.{},
    footprints: []Footprint = &.{},
    vias: []Via = &.{},
    zones: []Zone = &.{},
    segments: []Segment = &.{},
    arcs: []ArcSegment = &.{},
    gr_lines: []Line = &.{},
    gr_arcs: []Arc = &.{},
    gr_circles: []Circle = &.{},
    gr_rects: []Rect = &.{},
    gr_polys: []Polygon = &.{},
    gr_texts: []Text = &.{},
    images: []Image = &.{},
    dimensions: []Dimension = &.{},
    groups: []Group = &.{},
    targets: []Target = &.{},

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
        .gr_circles = structure.SexpField{ .multidict = true, .sexp_name = "gr_circle" },
        .gr_rects = structure.SexpField{ .multidict = true, .sexp_name = "gr_rect" },
        .gr_polys = structure.SexpField{ .multidict = true, .sexp_name = "gr_poly" },
        .gr_texts = structure.SexpField{ .multidict = true, .sexp_name = "gr_text" },
        .images = structure.SexpField{ .multidict = true, .sexp_name = "image" },
        .dimensions = structure.SexpField{ .multidict = true, .sexp_name = "dimension" },
        .groups = structure.SexpField{ .multidict = true, .sexp_name = "group" },
        .targets = structure.SexpField{ .multidict = true, .sexp_name = "target" },
    };
};

// Additional structures referenced but not fully defined above
pub const Image = struct {
    at: Xy,
    layer: str,
    scale: f64 = 1.0,
    data: ?str = null,
    uuid: str,
};

pub const DimensionPts = struct {
    xys: []Xy = &.{},
};

pub const Dimension = struct {
    type: str,
    layer: str,
    uuid: str,
    pts: DimensionPts,
    height: f64,
    orientation: ?f64 = null,
    leader_length: ?f64 = null,
    gr_text: Text,
};

pub const Group = struct {
    name: ?str = null,
    uuid: str,
    locked: ?bool = null,
    members: []str = &.{},

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
    };
};

pub const Target = struct {
    at: Xy,
    size: Xy,
    width: f64,
    layer: str,
    uuid: str,
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
