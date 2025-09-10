const std = @import("std");
const structure = @import("../structure.zig");

const str = []const u8;

const pcb = @import("pcb.zig");

pub const Footprint = struct {
    // common with pcb.Footprint
    name: str,
    uuid: ?str = null,
    path: ?str = null,
    layer: str = "F.Cu",
    propertys: []pcb.Property = &.{},
    attr: []pcb.E_Attr = &.{},
    fp_circles: []pcb.Circle = &.{},
    fp_lines: []pcb.Line = &.{},
    fp_arcs: []pcb.Arc = &.{},
    fp_rects: []pcb.Rect = &.{},
    fp_poly: []pcb.Polygon = &.{},
    fp_texts: []pcb.FpText = &.{},
    pads: []pcb.Pad = &.{},
    models: []pcb.Model = &.{},

    // additional fields
    version: i32 = pcb.KICAD_FP_VERSION,
    generator: str = "faebryk",
    generator_version: str = "latest",
    description: ?str = null,
    tags: []str = &.{},
    tedit: ?str = null,

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
        //
        .version = structure.SexpField{ .order = -20 },
        .generator = structure.SexpField{ .order = -19 },
        .generator_version = structure.SexpField{ .order = -18 },
        .layer = structure.SexpField{ .order = -17 },
        .description = structure.SexpField{ .order = -16, .sexp_name = "descr" },
        .tags = structure.SexpField{ .order = -15 },
        .tedit = structure.SexpField{ .order = -14 },
    };
};

pub const FootprintFile = struct {
    footprint: Footprint,

    const root_symbol = "footprint";

    pub fn loads(allocator: std.mem.Allocator, in: structure.input) !FootprintFile {
        const fp = try structure.loads(Footprint, allocator, in, root_symbol);
        return FootprintFile{
            .footprint = fp,
        };
    }

    pub fn dumps(self: FootprintFile, allocator: std.mem.Allocator, out: structure.output) !void {
        try structure.dumps(self.footprint, allocator, root_symbol, out);
    }

    pub fn free(self: *FootprintFile, allocator: std.mem.Allocator) void {
        structure.free(Footprint, allocator, self.footprint);
    }
};
