const std = @import("std");
const str = []u8;

pub const Node = struct {
    //
};

pub const Field = struct {
    identifier: ?str,
    locator: ?str,
};

pub const FieldE = union(enum) {
    ChildField: ChildField,
    EdgeField: EdgeField,
};

pub const ChildField = struct {
    field: Field,
    nodetype: type,
    //attributes: NodeAttributes,

    _dependants: std.ArrayList(FieldE),
};

pub const EdgeField = struct {
    //
};

pub const RefPath = struct {
    pub const Element = enum {
        //
    };
    path: std.ArrayList(Element),
};

// ----------------------------------------------------------------------------------

pub const ImplementsTrait = struct {
    node: Node,
    //
};

pub const is_interface = struct {
    node: Node,
    //
    is_trait: ImplementsTrait,

    pub fn MakeConnectionEdge(n1: RefPath, n2: RefPath, shallow: bool) null {
        //
    }
};

pub const Electrical = struct {
    node: Node,
    //
    _is_interface: is_interface,
};

pub const ElectricPower = struct {
    node: Node,

    hv: Electrical,
    lv: Electrical,
};
