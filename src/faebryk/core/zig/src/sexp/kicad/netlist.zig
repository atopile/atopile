const std = @import("std");
const structure = @import("../structure.zig");

const str = []const u8;

fn list(comptime T: type) type {
    return std.DoublyLinkedList(T);
}

// Component structures
pub const Property = struct {
    name: str,
    value: str,
};

pub const Libsource = struct {
    lib: str,
    part: str,
    description: str,
};

pub const Sheetpath = struct {
    names: str,
    tstamps: str,
};

pub const Field = struct {
    name: str,
    value: ?str = null,

    pub const fields_meta = .{
        // comes after name
        .value = structure.SexpField{ .positional = true, .order = 1 },
    };
};

pub const Fields = struct {
    fields: list(Field) = .{},

    pub const fields_meta = .{
        .fields = structure.SexpField{ .multidict = true, .sexp_name = "field" },
    };
};

pub const Component = struct {
    ref: str,
    value: str,
    footprint: str,
    propertys: list(Property) = .{},
    // TODO handle multiple tstamp values
    tstamps: list(str) = .{},
    //tstamps: str,
    fields: ?Fields = null,
    sheetpath: ?Sheetpath = null,
    libsource: ?Libsource = null,
    datasheet: ?str = null, // Added based on real file

    pub const fields_meta = .{
        .propertys = structure.SexpField{ .multidict = true, .sexp_name = "property" },
    };
};

pub const Components = struct {
    comps: list(Component) = .{},

    pub const fields_meta = .{
        .comps = structure.SexpField{ .multidict = true, .sexp_name = "comp" },
    };
};

// Net structures
pub const Node = struct {
    ref: str,
    pin: str,
    pintype: ?str = null,
    pinfunction: ?str = null,
};

pub const Net = struct {
    code: str,
    name: str,
    nodes: list(Node) = .{},

    pub const fields_meta = .{
        .nodes = structure.SexpField{ .multidict = true, .sexp_name = "node" },
    };
};

pub const Nets = struct {
    nets: list(Net) = .{},

    pub const fields_meta = .{
        .nets = structure.SexpField{ .multidict = true, .sexp_name = "net" },
    };
};

// Design structures
pub const Comment = struct {
    number: str,
    value: str,
};

pub const TitleBlock = struct {
    title: str = "",
    company: str = "",
    rev: str = "",
    date: str = "",
    source: str,
    comment: list(Comment) = .{},

    pub const fields_meta = .{
        .comment = structure.SexpField{ .multidict = true },
    };
};

pub const Sheet = struct {
    number: str,
    name: str,
    tstamps: str,
    title_block: TitleBlock,
};

pub const Design = struct {
    source: str,
    date: str,
    tool: str,
    sheet: Sheet,
};

// Libparts structures
pub const Fp = struct {
    fp: str,

    pub const fields_meta = .{
        .fp = structure.SexpField{ .positional = true },
    };
};

pub const Footprints = struct {
    fps: list(Fp) = .{},

    pub const fields_meta = .{
        .fps = structure.SexpField{ .multidict = true, .sexp_name = "fp" },
    };
};

pub const Pin = struct {
    num: str,
    name: str,
    type: str,
};

pub const Pins = struct {
    pin: list(Pin) = .{},

    pub const fields_meta = .{
        .pin = structure.SexpField{ .multidict = true },
    };
};

pub const Libpart = struct {
    lib: str,
    part: str,
    fields: ?Fields = null,
    pins: ?Pins = null,
    footprints: ?Footprints = null,
};

pub const Libparts = struct {
    libparts: list(Libpart) = .{},

    pub const fields_meta = .{
        .libparts = structure.SexpField{ .multidict = true, .sexp_name = "libpart" },
    };
};

pub const Libraries = struct {
    // TODO: implement when needed
};

pub const Netlist = struct {
    version: str,
    components: Components = .{},
    nets: Nets = .{},
    design: ?Design = null,
    libparts: Libparts = .{},
    libraries: Libraries = .{},
};

pub const NetlistFile = struct {
    netlist: Netlist,

    const root_symbol = "export";

    pub fn loads(allocator: std.mem.Allocator, in: structure.input) !NetlistFile {
        const netlist = try structure.loads(Netlist, allocator, in, root_symbol);
        return NetlistFile{
            .netlist = netlist,
        };
    }

    pub fn dumps(self: NetlistFile, allocator: std.mem.Allocator, out: structure.output) !void {
        try structure.dumps(self.netlist, allocator, root_symbol, out);
    }

    pub fn free(self: *NetlistFile, allocator: std.mem.Allocator) void {
        structure.free(Netlist, allocator, self.netlist);
    }
};
