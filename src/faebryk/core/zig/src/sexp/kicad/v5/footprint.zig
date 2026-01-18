const std = @import("std");
const structure = @import("../../structure.zig");
const pcb = @import("../pcb.zig");

const str = []const u8;

fn list(comptime T: type) type {
    return std.DoublyLinkedList(T);
}

pub const Line = struct {
    start: pcb.Xy,
    end: pcb.Xy,
    layer: str,
    width: f64,
};

pub const Circle = struct {
    center: pcb.Xy,
    end: pcb.Xy,
    width: f64,
    fill: pcb.E_fill = .no,
    layer: str,
};

pub const Arc = struct {
    start: pcb.Xy,
    end: pcb.Xy,
    angle: f64,
    width: f64,
    layer: str,
};

pub const Rect = struct {
    start: pcb.Xy,
    end: pcb.Xy,
    width: f64,
    fill: pcb.E_fill,
    layer: str,
};

pub const Model = struct {
    path: str,
    scale: pcb.ModelXyz,
    rotate: pcb.ModelXyz,
    // some older versioins have at instead of offset
    offset: ?pcb.ModelXyz = null,
    at: ?pcb.ModelXyz = null,

    pub const fields_meta = .{
        .path = structure.SexpField{ .positional = true },
    };
};

pub const Footprint = struct {
    // common with pcb.Footprint
    name: str,
    layer: str = "F.Cu",
    uuid: ?str = null,
    path: ?str = null,
    propertys: list(pcb.Property) = .{},
    fp_texts: list(pcb.FpText) = .{},
    attr: list(pcb.E_Attr) = .{},
    fp_lines: list(Line) = .{},
    fp_arcs: list(Arc) = .{},
    fp_circles: list(Circle) = .{},
    fp_rects: list(Rect) = .{},
    fp_poly: list(pcb.Polygon) = .{},
    pads: list(pcb.Pad) = .{},
    model: ?Model = null,

    // additional fields
    description: ?str = null,
    tags: list(str) = .{},
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
        .description = structure.SexpField{ .order = -1, .sexp_name = "descr" },
        .tags = structure.SexpField{ .order = -1 },
        .tedit = structure.SexpField{ .order = -1 },
    };
};

pub const FootprintFile = struct {
    footprint: Footprint,

    const root_symbol = "module";

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
