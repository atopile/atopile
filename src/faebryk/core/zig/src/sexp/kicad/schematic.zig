const std = @import("std");
const structure = @import("../structure.zig");

const str = []const u8;

fn list(comptime T: type) type {
    return std.DoublyLinkedList(T);
}

// Constants
pub const KICAD_SCH_VERSION: i32 = 20211123;

// Import common types from PCB module
const pcb = @import("pcb.zig");
const Xy = pcb.Xy;
const Xyr = pcb.Xyr;
const Wh = pcb.Wh;
const Effects = pcb.Effects;
const UUID = str;

// Enums
pub const E_fill_type = enum {
    background,
    none,
    outline,
};

pub const E_stroke_type = enum {
    solid,
    default,
};

pub const E_pin_type = enum {
    bidirectional,
    free,
    input,
    no_connect,
    open_collector,
    open_emitter,
    output,
    passive,
    power_in,
    power_out,
    tri_state,
    unspecified,
};

pub const E_pin_style = enum {
    clock,
    clock_low,
    edge_clock_high,
    input_low,
    inverted,
    inverted_clock,
    line,
    non_logic,
    output_low,
};

pub const E_sheet_pin_type = enum {
    bidirectional,
    input,
    output,
    passive,
    tri_state,
};

pub const E_global_label_shape = enum {
    input,
    output,
    bidirectional,
    tri_state,
    passive,
    dot,
    round,
    diamond,
    rectangle,
};

pub const E_hide = enum {
    hide,
};

// Basic structures
pub const Pts = struct {
    xys: list(Xy) = .{},

    pub const fields_meta = .{
        .xys = structure.SexpField{ .multidict = true, .sexp_name = "xy" },
    };
};

pub const Fill = struct {
    type: E_fill_type = .background,
};

pub const Stroke = struct {
    width: f64 = 0,
    type: E_stroke_type = .default,
    color: Color = .{ .r = 0, .g = 0, .b = 0, .a = 0 },
};

// Shape structures
pub const Circle = struct {
    center: Xy,
    end: Xy,
    stroke: Stroke,
    fill: Fill,
};

pub const Arc = struct {
    start: Xy,
    mid: Xy,
    end: Xy,
    stroke: Stroke,
    fill: Fill,
};

pub const Rect = struct {
    start: Xy,
    end: Xy,
    stroke: Stroke,
    fill: Fill,
};

pub const Polyline = struct {
    stroke: Stroke,
    fill: Fill,
    pts: Pts = .{},
};

// Property structure
pub const Property = struct {
    name: str,
    value: str,
    id: ?i32 = null,
    at: Xyr,
    effects: ?Effects = null,

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
        .value = structure.SexpField{ .positional = true },
    };
};

// Symbol structures
pub const PinNames = struct {
    offset: f64,
};

pub const PinName = struct {
    name: str,
    effects: Effects,

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
    };
};

pub const PinNumber = struct {
    number: str,
    effects: Effects,

    pub const fields_meta = .{
        .number = structure.SexpField{ .positional = true },
    };
};

pub const SymbolPin = struct {
    at: Xyr,
    length: f64,
    type: E_pin_type,
    style: E_pin_style,
    name: PinName = .{ .name = "", .effects = .{ .font = .{ .size = .{ .w = 1.27, .h = 1.27 } } } },
    number: PinNumber = .{ .number = "", .effects = .{ .font = .{ .size = .{ .w = 1.27, .h = 1.27 } } } },

    pub const fields_meta = .{
        .type = structure.SexpField{ .positional = true },
        .style = structure.SexpField{ .positional = true },
    };
};

pub const SymbolUnit = struct {
    name: str,
    polylines: list(Polyline) = .{},
    circles: list(Circle) = .{},
    rectangles: list(Rect) = .{},
    arcs: list(Arc) = .{},
    pins: list(SymbolPin) = .{},

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
        .polylines = structure.SexpField{ .multidict = true, .sexp_name = "polyline" },
        .circles = structure.SexpField{ .multidict = true, .sexp_name = "circle" },
        .rectangles = structure.SexpField{ .multidict = true, .sexp_name = "rectangle" },
        .arcs = structure.SexpField{ .multidict = true, .sexp_name = "arc" },
        .pins = structure.SexpField{ .multidict = true, .sexp_name = "pin" },
    };
};

pub const Symbol = struct {
    name: str,
    power: bool = false,
    propertys: list(Property) = .{},
    pin_numbers: ?E_hide = null,
    pin_names: ?PinNames = null,
    in_bom: ?bool = null,
    on_board: ?bool = null,
    symbols: list(SymbolUnit) = .{},
    convert: ?i32 = null,

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
        .propertys = structure.SexpField{ .multidict = true, .sexp_name = "property" },
        .symbols = structure.SexpField{ .multidict = true, .sexp_name = "symbol" },
        .power = structure.SexpField{ .boolean_encoding = .parantheses_symbol },
    };
};

// Schematic instance structures
pub const InstancePin = struct {
    name: str,
    uuid: UUID,

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
    };
};

pub const SymbolInstance = struct {
    lib_id: str,
    at: Xyr,
    unit: i32,
    in_bom: bool = false,
    on_board: bool = false,
    uuid: UUID,
    fields_autoplaced: bool = true,
    propertys: list(Property) = .{},
    pins: list(InstancePin) = .{},
    convert: ?i32 = null,

    pub const fields_meta = .{
        .propertys = structure.SexpField{ .multidict = true, .sexp_name = "property" },
        .pins = structure.SexpField{ .multidict = true, .sexp_name = "pin" },
        .fields_autoplaced = structure.SexpField{ .boolean_encoding = .parantheses_symbol },
    };
};

pub const Junction = struct {
    at: Xy,
    diameter: f64,
    color: Color = .{ .r = 0, .g = 0, .b = 0, .a = 0 },
    uuid: UUID,
};

pub const Wire = struct {
    pts: Pts,
    stroke: Stroke,
    uuid: UUID,
};

pub const Text = struct {
    text: str,
    at: Xyr,
    effects: Effects,
    uuid: UUID,

    pub const fields_meta = .{
        .text = structure.SexpField{ .positional = true },
    };
};

pub const SheetPin = struct {
    name: str,
    type: E_sheet_pin_type,
    at: Xyr,
    effects: Effects,
    uuid: UUID,

    pub const fields_meta = .{
        .name = structure.SexpField{ .positional = true },
        .type = structure.SexpField{ .positional = true },
    };
};

pub const Sheet = struct {
    at: Xy,
    size: Xy,
    stroke: Stroke,
    fill: Fill,
    uuid: UUID,
    fields_autoplaced: bool = true,
    propertys: list(Property) = .{},
    pins: list(SheetPin) = .{},

    pub const fields_meta = .{
        .propertys = structure.SexpField{ .multidict = true, .sexp_name = "property" },
        .pins = structure.SexpField{ .multidict = true, .sexp_name = "pin" },
        .fields_autoplaced = structure.SexpField{ .boolean_encoding = .parantheses_symbol },
    };
};

pub const GlobalLabel = struct {
    text: str,
    shape: E_global_label_shape,
    at: Xyr,
    effects: Effects,
    uuid: UUID,
    fields_autoplaced: bool = true,
    propertys: list(Property) = .{},

    pub const fields_meta = .{
        .text = structure.SexpField{ .positional = true },
        .propertys = structure.SexpField{ .multidict = true, .sexp_name = "property" },
        .fields_autoplaced = structure.SexpField{ .boolean_encoding = .parantheses_symbol },
    };
};

pub const Label = struct {
    text: str,
    at: Xyr,
    effects: Effects,
    uuid: UUID,

    pub const fields_meta = .{
        .text = structure.SexpField{ .positional = true },
    };
};

pub const Bus = struct {
    pts: Pts,
    stroke: Stroke,
    uuid: UUID,
};

pub const BusEntry = struct {
    at: Xy,
    size: Xy,
    stroke: Stroke,
    uuid: UUID,
};

// Main schematic structures
pub const TitleBlock = struct {
    title: ?str = null,
    date: ?str = null,
    rev: ?str = null,
    company: ?str = null,
};

pub const LibSymbols = struct {
    symbols: list(Symbol) = .{},

    pub const fields_meta = .{
        .symbols = structure.SexpField{ .multidict = true, .sexp_name = "symbol" },
    };
};

pub const Color = struct {
    r: i32,
    g: i32,
    b: i32,
    a: i32,

    pub const fields_meta = .{
        .r = structure.SexpField{ .positional = true },
        .g = structure.SexpField{ .positional = true },
        .b = structure.SexpField{ .positional = true },
        .a = structure.SexpField{ .positional = true },
    };
};

pub const KicadSch = struct {
    version: i32 = KICAD_SCH_VERSION,
    generator: str,
    paper: str,
    uuid: UUID,
    lib_symbols: LibSymbols = .{},
    title_block: TitleBlock = .{},
    junctions: list(Junction) = .{},
    wires: list(Wire) = .{},
    texts: list(Text) = .{},
    symbols: list(SymbolInstance) = .{},
    sheets: list(Sheet) = .{},
    global_labels: list(GlobalLabel) = .{},
    no_connects: list(Xy) = .{},
    buss: list(Bus) = .{},
    labels: list(Label) = .{},
    bus_entrys: list(BusEntry) = .{},

    pub const fields_meta = .{
        .junctions = structure.SexpField{ .multidict = true, .sexp_name = "junction" },
        .wires = structure.SexpField{ .multidict = true, .sexp_name = "wire" },
        .texts = structure.SexpField{ .multidict = true, .sexp_name = "text" },
        .symbols = structure.SexpField{ .multidict = true, .sexp_name = "symbol" },
        .sheets = structure.SexpField{ .multidict = true, .sexp_name = "sheet" },
        .global_labels = structure.SexpField{ .multidict = true, .sexp_name = "global_label" },
        .no_connects = structure.SexpField{ .multidict = true, .sexp_name = "no_connect" },
        .buss = structure.SexpField{ .multidict = true, .sexp_name = "bus" },
        .labels = structure.SexpField{ .multidict = true, .sexp_name = "label" },
        .bus_entrys = structure.SexpField{ .multidict = true, .sexp_name = "bus_entry" },
    };
};

// File structure
pub const SchematicFile = struct {
    kicad_sch: KicadSch,

    const root_symbol = "kicad_sch";

    pub fn loads(allocator: std.mem.Allocator, in: structure.input) !SchematicFile {
        const sch = try structure.loads(KicadSch, allocator, in, root_symbol);
        return SchematicFile{
            .kicad_sch = sch,
        };
    }

    pub fn dumps(self: SchematicFile, allocator: std.mem.Allocator, out: structure.output) !void {
        try structure.dumps(self.kicad_sch, allocator, root_symbol, out);
    }

    pub fn free(self: *SchematicFile, allocator: std.mem.Allocator) void {
        structure.free(KicadSch, allocator, self.kicad_sch);
    }
};
