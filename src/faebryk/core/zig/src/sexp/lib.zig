// Root module that exports all sexp functionality
pub const tokenizer = @import("tokenizer.zig");
pub const ast = @import("ast.zig");
pub const structure = @import("structure.zig");
pub const kicad = struct {
    pub const pcb = @import("kicad/pcb.zig");
    pub const netlist = @import("kicad/netlist.zig");
    pub const fp_lib_table = @import("kicad/fp_lib_table.zig");
    pub const footprint = @import("kicad/footprint.zig");
    pub const symbol = @import("kicad/symbol.zig");
    pub const schematic = @import("kicad/schematic.zig");
    pub const v5 = struct {
        pub const footprint = @import("kicad/v5/footprint.zig");
    };
    pub const v6 = struct {
        pub const symbol = @import("kicad/v6/symbol.zig");
    };
};

// Re-export commonly used types for convenience
pub const Token = tokenizer.Token;
pub const TokenType = tokenizer.TokenType;
pub const Node = ast.Node;
pub const Value = structure.Value;
