const std = @import("std");
const structure = @import("../structure.zig");

const str = []const u8;

fn list(comptime T: type) type {
    return ?std.ArrayList(T);
}

const pcb = @import("pcb.zig");

pub const Footprint = struct {
    // common with pcb.Footprint
    name: str,
    uuid: ?str = null,
    path: ?str = null,
    layer: str = "F.Cu",
    propertys: list(pcb.Property) = null,
    attr: list(pcb.E_Attr) = null,
    fp_circles: list(pcb.Circle) = null,
    fp_lines: list(pcb.Line) = null,
    fp_arcs: list(pcb.Arc) = null,
    fp_rects: list(pcb.Rect) = null,
    fp_poly: list(pcb.Polygon) = null,
    fp_texts: list(pcb.FpText) = null,
    pads: list(pcb.Pad) = null,
    models: list(pcb.Model) = null,
    embedded_fonts: ?bool = null,

    // additional fields
    version: i32 = pcb.KICAD_FP_VERSION,
    generator: str = "faebryk",
    generator_version: str = "latest",
    description: ?str = null,
    tags: list(str) = null,
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
