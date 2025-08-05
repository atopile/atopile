const std = @import("std");
const structure = @import("../structure.zig");

// Component structures
pub const Property = struct {
    name: []const u8,
    value: []const u8,
};

pub const Libsource = struct {
    lib: []const u8,
    part: []const u8,
    description: []const u8,
};

pub const Sheetpath = struct {
    names: []const u8,
    tstamps: []const u8,
};

pub const Field = struct {
    name: []const u8,
    value: ?[]const u8 = null,

    pub const fields_meta = .{
        // comes after name
        .value = structure.SexpField{ .positional = true, .order = 1 },
    };
};

pub const Fields = struct {
    fields: []Field = &.{},

    pub const fields_meta = .{
        .fields = structure.SexpField{ .multidict = true, .sexp_name = "field" },
    };
};

pub const Tstamps = struct {
    tstamps: [][]const u8 = &.{},

    pub const fields_meta = .{
        .tstamps = structure.SexpField{ .positional = true },
    };
};

pub const Component = struct {
    ref: []const u8,
    value: []const u8,
    footprint: []const u8,
    propertys: []Property = &.{},
    // TODO handle multiple tstamp values
    //tstamps: Tstamps,
    tstamps: []const u8,
    fields: ?Fields = null,
    sheetpath: ?Sheetpath = null,
    libsource: ?Libsource = null,
    datasheet: ?[]const u8 = null, // Added based on real file

    pub const fields_meta = .{
        .propertys = structure.SexpField{ .multidict = true, .sexp_name = "property" },
    };
};

pub const Components = struct {
    comps: []Component = &.{},

    pub const fields_meta = .{
        .comps = structure.SexpField{ .multidict = true, .sexp_name = "comp" },
    };
};

// Net structures
pub const Node = struct {
    ref: []const u8,
    pin: []const u8,
    pintype: ?[]const u8 = null,
    pinfunction: ?[]const u8 = null,
};

pub const Net = struct {
    code: []const u8,
    name: []const u8,
    nodes: []Node = &.{},

    pub const fields_meta = .{
        .nodes = structure.SexpField{ .multidict = true, .sexp_name = "node" },
    };
};

pub const Nets = struct {
    nets: []Net = &.{},

    pub const fields_meta = .{
        .nets = structure.SexpField{ .multidict = true, .sexp_name = "net" },
    };
};

// Design structures
pub const Comment = struct {
    number: []const u8,
    value: []const u8,
};

pub const TitleBlock = struct {
    title: []const u8 = "",
    company: []const u8 = "",
    rev: []const u8 = "",
    date: []const u8 = "",
    source: []const u8,
    comment: []Comment = &.{},

    pub const fields_meta = .{
        .comment = structure.SexpField{ .multidict = true },
    };
};

pub const Sheet = struct {
    number: []const u8,
    name: []const u8,
    tstamps: []const u8,
    title_block: TitleBlock,
};

pub const Design = struct {
    source: []const u8,
    date: []const u8,
    tool: []const u8,
    sheet: Sheet,
};

// Libparts structures
pub const Fp = struct {
    fp: []const u8,

    pub const fields_meta = .{
        .fp = structure.SexpField{ .positional = true },
    };
};

pub const Footprints = struct {
    fps: []Fp = &.{},

    pub const fields_meta = .{
        .fps = structure.SexpField{ .multidict = true, .sexp_name = "fp" },
    };
};

pub const Pin = struct {
    num: []const u8,
    name: []const u8,
    type: []const u8,
};

pub const Pins = struct {
    pin: []Pin = &.{},

    pub const fields_meta = .{
        .pin = structure.SexpField{ .multidict = true },
    };
};

pub const Libpart = struct {
    lib: []const u8,
    part: []const u8,
    fields: ?Fields = null,
    pins: ?Pins = null,
    footprints: ?Footprints = null,
};

pub const Libparts = struct {
    libparts: []Libpart = &.{},

    pub const fields_meta = .{
        .libparts = structure.SexpField{ .multidict = true, .sexp_name = "libpart" },
    };
};

pub const Libraries = struct {
    // TODO: implement when needed
};

pub const Netlist = struct {
    version: []const u8,
    components: Components = .{},
    nets: Nets = .{},
    design: ?Design = null,
    libparts: Libparts = .{},
    libraries: Libraries = .{},
};

pub const NetlistFile = struct {
    netlist: ?Netlist = null,

    const root_symbol = "export";

    pub fn read(allocator: std.mem.Allocator, path: []const u8) !NetlistFile {
        const netlist: Netlist = try structure.loadsFileWithSymbol(Netlist, allocator, path, root_symbol);
        return NetlistFile{
            .netlist = netlist,
        };
    }

    pub fn loads(allocator: std.mem.Allocator, content: []const u8) !NetlistFile {
        const netlist = try structure.loadsStringWithSymbol(Netlist, allocator, content, root_symbol);
        return NetlistFile{
            .netlist = netlist,
        };
    }

    pub fn dumps(self: NetlistFile, allocator: std.mem.Allocator) ![]u8 {
        if (self.netlist) |netlist| {
            return try structure.dumpsStringWithSymbol(netlist, allocator, root_symbol);
        }
        return error.NoTable;
    }

    pub fn write(self: NetlistFile, file_path: []const u8, allocator: std.mem.Allocator) !void {
        if (self.netlist) |netlist| {
            return try structure.writeFileWithSymbol(netlist, file_path, root_symbol, allocator);
        }
        return error.NoTable;
    }

    pub fn free(self: *NetlistFile, allocator: std.mem.Allocator) void {
        if (self.netlist) |netlist| {
            structure.free(Netlist, allocator, netlist);
        }
    }
};
