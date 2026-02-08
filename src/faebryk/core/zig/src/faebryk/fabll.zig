const std = @import("std");
const graph = @import("graph");
const str = []u8;

// design questions ===============================================================
// - compile-time vs run-time
//  - in python fabll every Node (recipee) gets constructed once on file import
//     construction means we collect all fields in cls.__fields
//     - then on typegraph creation (get_or_create_type) we call Node._create_type
//       which will call _exec_field for each field in cls.__fields
//      this will create the type in the typegraph and thus our recipee is executed
//  - recreating _exec_field should be easy, because it just typegraph operations
//  - the hard bit to replicate is field collection in a zig way
//      the most similar way would be to use zig comptime to build the recipees
//      - its not 100% clear whether comptime is powerful enough for this, 
//          we are calling a bunch of functions like MakeChild and MakeEdge that might do hard stuff
//      - alternatively we will have to do some runtime stuff with type registries for cache reasons
//          very ugly and would love to avoid this if possible
//=================================================================================

pub const Node = struct {
    instance: graph.BoundNode,

    pub fn MakeChild(nodetype: type) ChildField {
        return ChildField{
            .field = .{
                .identifier = null,
                .locator = null,
            },
            .nodetype = nodetype,
        };
    }
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

    //_dependants: std.ArrayList(FieldE),

    pub fn add_dependant(self: *@This(), dependant: FieldE) void {
        //
    }

    pub fn add_as_dependant(self: *@This(), to: ChildField) void {
        //
    }
};

pub const EdgeField = struct {
    lhs: RefPath,
    rhs: RefPath,
    edge: fbrk.EdgeCreationAtttributes,
    identifier: ?str,
};

pub const RefPath = struct {
    pub const Element = enum {
        //
    };
    path: std.ArrayList(Element),
};

// ----------------------------------------------------------------------------------

pub const is_trait = struct {
    is_node: Node,
    //
    pub fn MakeEdge(traitchildfield: ChildField, owner: RefPath) ChildField {
        traitchildfield.add_dependant(owner);
        // TODO 
        traitchildfield.add_dependant(
            {.EdgeField = .{
                .lhs = owner,
                .rhs = RefPath{.path = [traitchildfield]},
                .edge=fbrk.EdgeTrait.build(),
            }};
        )
        return traitchildfield;
    }
};

pub const is_interface = struct {
    is_node: Node,
    //
    is_trait: is_trait,

    pub fn MakeConnectionEdge(n1: RefPath, n2: RefPath, shallow: bool) null {
        //
    }

    pub fn MakeChild() ChildField {
        return Node.MakeChild(@This());
    }
};

pub const Electrical = struct {
    node: Node,
    //
    _is_interface = is_interface.MakeChild(),

    pub fn MakeChild() ChildField {
        return Node.MakeChild(@This());
    }
};

pub const ElectricPower = struct {
    node: Node,

    const hv_lowlevel = ChildField{
        .field = .{
            .identifier = "vcc",
            .locator = null,
        },
        .nodetype = Electrical,
    };

    const hv_highlevel = Electrical.MakeChild();
};
