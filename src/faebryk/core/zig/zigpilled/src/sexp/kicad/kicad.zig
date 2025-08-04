const std = @import("std");
const dataclass_sexp = @import("../dataclass_sexp.zig");

// KiCad-specific aliases for the generic functions
pub const loadsKicadFile = dataclass_sexp.loadsStringWithSymbol;
pub const dumpsKicadFile = dataclass_sexp.dumpsStringWithSymbol;
pub const writeKicadFile = dataclass_sexp.writeFileWithSymbol;
