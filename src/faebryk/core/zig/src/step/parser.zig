const std = @import("std");
const tokenizer = @import("tokenizer.zig");
const ast = @import("ast.zig");

const Token = tokenizer.Token;
const TokenType = tokenizer.TokenType;
const Parameter = ast.Parameter;
const TypedParameter = ast.TypedParameter;
const Entity = ast.Entity;
const Header = ast.Header;
const StepFile = ast.StepFile;

pub const ParseError = error{
    UnexpectedToken,
    UnexpectedEnd,
    InvalidEntityId,
    InvalidHeader,
    DuplicateEntityId,
    OutOfMemory,
};

pub const Parser = struct {
    tokens: []const Token,
    position: usize,
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator, tokens: []const Token) Parser {
        return .{
            .tokens = tokens,
            .position = 0,
            .allocator = allocator,
        };
    }

    fn peek(self: *Parser) ?Token {
        if (self.position >= self.tokens.len) return null;
        return self.tokens[self.position];
    }

    fn advance(self: *Parser) ?Token {
        if (self.position >= self.tokens.len) return null;
        const token = self.tokens[self.position];
        self.position += 1;
        return token;
    }

    fn expect(self: *Parser, expected: TokenType) ParseError!Token {
        const token = self.advance() orelse return error.UnexpectedEnd;
        if (token.type != expected) {
            return error.UnexpectedToken;
        }
        return token;
    }

    fn expectKeyword(self: *Parser, expected: []const u8) ParseError!Token {
        const token = self.advance() orelse return error.UnexpectedEnd;
        if (token.type != .keyword or !std.mem.eql(u8, token.value, expected)) {
            return error.UnexpectedToken;
        }
        return token;
    }

    /// Skip over the ISO header/footer tokens (ISO-10303-21 or END-ISO-10303-21)
    fn skipIsoMarker(self: *Parser) ParseError!void {
        // Format is: ISO-10303-21 or END-ISO-10303-21
        // Tokenized as: keyword, integer (negative), integer (negative), etc.
        // Just skip tokens until we hit semicolon
        while (self.peek()) |token| {
            _ = self.advance();
            if (token.type == .semicolon) break;
        }
    }

    /// Parse complete STEP file
    pub fn parse(self: *Parser) ParseError!StepFile {
        var step_file = StepFile.init(self.allocator);
        errdefer step_file.deinit();

        // ISO-10303-21;
        // Just verify first token is ISO and skip to semicolon
        const first = self.peek() orelse return error.UnexpectedEnd;
        if (first.type != .keyword or !std.mem.eql(u8, first.value, "ISO")) {
            return error.UnexpectedToken;
        }
        try self.skipIsoMarker();

        // HEADER;
        _ = try self.expectKeyword("HEADER");
        _ = try self.expect(.semicolon);

        // Parse header entities
        try self.parseHeader(&step_file.header);

        // ENDSEC;
        _ = try self.expectKeyword("ENDSEC");
        _ = try self.expect(.semicolon);

        // DATA;
        _ = try self.expectKeyword("DATA");
        _ = try self.expect(.semicolon);

        // Parse entities
        while (self.peek()) |token| {
            if (token.type == .keyword and std.mem.eql(u8, token.value, "ENDSEC")) {
                break;
            }
            if (token.type == .entity_id) {
                const entity = try self.parseEntity();
                const id = entity.id;
                if (step_file.entities.contains(id)) {
                    return error.DuplicateEntityId;
                }
                try step_file.entities.put(id, entity);
                try step_file.entity_order.append(id);
            } else {
                // Skip unexpected tokens
                _ = self.advance();
            }
        }

        // ENDSEC;
        _ = try self.expectKeyword("ENDSEC");
        _ = try self.expect(.semicolon);

        // END-ISO-10303-21;
        const end_token = self.peek() orelse return error.UnexpectedEnd;
        if (end_token.type != .keyword or !std.mem.eql(u8, end_token.value, "END")) {
            return error.UnexpectedToken;
        }
        try self.skipIsoMarker();

        return step_file;
    }

    fn parseHeader(self: *Parser, header: *Header) ParseError!void {
        while (self.peek()) |token| {
            if (token.type == .keyword and std.mem.eql(u8, token.value, "ENDSEC")) {
                break;
            }

            if (token.type != .keyword) {
                _ = self.advance();
                continue;
            }

            if (std.mem.eql(u8, token.value, "FILE_DESCRIPTION")) {
                _ = self.advance();
                _ = try self.expect(.lparen);
                // Parse description list
                if ((try self.expect(.lparen)).type == .lparen) {
                    var descriptions = std.ArrayList([]const u8).init(self.allocator);
                    while (self.peek()) |t| {
                        if (t.type == .rparen) break;
                        if (t.type == .string) {
                            try descriptions.append(t.value);
                        }
                        _ = self.advance();
                    }
                    _ = try self.expect(.rparen);
                    header.file_description.description = try descriptions.toOwnedSlice();
                }
                // Skip to end of FILE_DESCRIPTION
                var depth: usize = 1;
                while (self.advance()) |t| {
                    if (t.type == .lparen) depth += 1;
                    if (t.type == .rparen) {
                        depth -= 1;
                        if (depth == 0) break;
                    }
                }
                _ = try self.expect(.semicolon);
            } else if (std.mem.eql(u8, token.value, "FILE_NAME")) {
                _ = self.advance();
                _ = try self.expect(.lparen);
                // Parse name
                if (self.peek()) |t| {
                    if (t.type == .string) {
                        header.file_name.name = t.value;
                        _ = self.advance();
                    }
                }
                // Skip comma if present
                if (self.peek()) |t| {
                    if (t.type == .comma) _ = self.advance();
                }
                // Parse timestamp
                if (self.peek()) |t| {
                    if (t.type == .string) {
                        header.file_name.time_stamp = t.value;
                        _ = self.advance();
                    }
                }
                // Skip to end of FILE_NAME
                var depth: usize = 1;
                while (self.advance()) |t| {
                    if (t.type == .lparen) depth += 1;
                    if (t.type == .rparen) {
                        depth -= 1;
                        if (depth == 0) break;
                    }
                }
                _ = try self.expect(.semicolon);
            } else if (std.mem.eql(u8, token.value, "FILE_SCHEMA")) {
                _ = self.advance();
                _ = try self.expect(.lparen);
                // Parse schema list
                if ((try self.expect(.lparen)).type == .lparen) {
                    var schemas = std.ArrayList([]const u8).init(self.allocator);
                    while (self.peek()) |t| {
                        if (t.type == .rparen) break;
                        if (t.type == .string) {
                            try schemas.append(t.value);
                        }
                        _ = self.advance();
                    }
                    _ = try self.expect(.rparen);
                    header.file_schema.schemas = try schemas.toOwnedSlice();
                }
                _ = try self.expect(.rparen);
                _ = try self.expect(.semicolon);
            } else {
                // Skip unknown header entity
                _ = self.advance();
                var depth: usize = 0;
                while (self.advance()) |t| {
                    if (t.type == .lparen) depth += 1;
                    if (t.type == .rparen) {
                        if (depth == 0) break;
                        depth -= 1;
                    }
                    if (t.type == .semicolon and depth == 0) break;
                }
            }
        }
    }

    fn parseEntity(self: *Parser) ParseError!Entity {
        const id_token = try self.expect(.entity_id);
        const id = std.fmt.parseInt(u32, id_token.value, 10) catch return error.InvalidEntityId;

        _ = try self.expect(.equals);

        // Check for complex entity: #id = (TYPE1(...) TYPE2(...))
        const next = self.peek() orelse return error.UnexpectedEnd;

        if (next.type == .lparen) {
            return self.parseComplexEntity(id, id_token.location);
        }

        // Simple entity: #id = TYPE_NAME(params)
        const type_token = try self.expect(.keyword);
        _ = try self.expect(.lparen);

        const parameters = try self.parseParameterList();

        _ = try self.expect(.rparen);
        _ = try self.expect(.semicolon);

        return Entity{
            .id = id,
            .type_name = type_token.value,
            .parameters = parameters,
            .complex_types = null,
            .location = id_token.location,
        };
    }

    fn parseComplexEntity(self: *Parser, id: u32, location: tokenizer.TokenLocation) ParseError!Entity {
        _ = try self.expect(.lparen);

        var types = std.ArrayList(TypedParameter).init(self.allocator);
        errdefer {
            for (types.items) |*t| {
                t.deinit(self.allocator);
            }
            types.deinit();
        }

        while (self.peek()) |token| {
            if (token.type == .rparen) break;

            if (token.type == .keyword) {
                const type_token = self.advance().?;
                _ = try self.expect(.lparen);
                const params = try self.parseParameterList();
                _ = try self.expect(.rparen);

                try types.append(TypedParameter{
                    .type_name = type_token.value,
                    .parameters = params,
                });
            } else {
                _ = self.advance();
            }
        }

        _ = try self.expect(.rparen);
        _ = try self.expect(.semicolon);

        const complex_types = try types.toOwnedSlice();

        // Use first type as the main type name
        const type_name = if (complex_types.len > 0) complex_types[0].type_name else "";

        return Entity{
            .id = id,
            .type_name = type_name,
            .parameters = &.{},
            .complex_types = complex_types,
            .location = location,
        };
    }

    fn parseParameterList(self: *Parser) ParseError![]Parameter {
        var params = std.ArrayList(Parameter).init(self.allocator);
        errdefer {
            for (params.items) |*p| {
                p.deinit(self.allocator);
            }
            params.deinit();
        }

        while (self.peek()) |token| {
            if (token.type == .rparen) break;
            if (token.type == .comma) {
                _ = self.advance();
                continue;
            }

            const param = try self.parseParameter();
            try params.append(param);
        }

        return params.toOwnedSlice();
    }

    fn parseParameter(self: *Parser) ParseError!Parameter {
        const token = self.peek() orelse return error.UnexpectedEnd;

        switch (token.type) {
            .entity_id => {
                _ = self.advance();
                const id = std.fmt.parseInt(u32, token.value, 10) catch return error.InvalidEntityId;
                return Parameter{ .entity_ref = id };
            },
            .integer => {
                _ = self.advance();
                const i = std.fmt.parseInt(i64, token.value, 10) catch return Parameter{ .real = token.value };
                return Parameter{ .integer = i };
            },
            .real => {
                _ = self.advance();
                return Parameter{ .real = token.value };
            },
            .string => {
                _ = self.advance();
                return Parameter{ .string = token.value };
            },
            .enumeration => {
                _ = self.advance();
                return Parameter{ .enumeration = token.value };
            },
            .undefined => {
                _ = self.advance();
                return Parameter.undefined;
            },
            .omitted => {
                _ = self.advance();
                return Parameter.omitted;
            },
            .lparen => {
                // List or typed parameter
                _ = self.advance();

                // Check if this is an empty list
                if (self.peek()) |next| {
                    if (next.type == .rparen) {
                        _ = self.advance();
                        const empty: []Parameter = &.{};
                        return Parameter{ .list = empty };
                    }
                }

                // Check if first item is a keyword (typed parameter)
                const first = self.peek() orelse return error.UnexpectedEnd;
                if (first.type == .keyword) {
                    // Could be typed parameter or just a list
                    // Look ahead to see if there's a lparen after keyword
                    if (self.position + 1 < self.tokens.len) {
                        const after = self.tokens[self.position + 1];
                        if (after.type == .lparen) {
                            // This is a typed parameter list (complex entity style within a param)
                            // For simplicity, treat as list
                        }
                    }
                }

                // Parse as list
                var items = std.ArrayList(Parameter).init(self.allocator);
                errdefer {
                    for (items.items) |*p| {
                        p.deinit(self.allocator);
                    }
                    items.deinit();
                }

                while (self.peek()) |t| {
                    if (t.type == .rparen) break;
                    if (t.type == .comma) {
                        _ = self.advance();
                        continue;
                    }
                    const item = try self.parseParameter();
                    try items.append(item);
                }

                _ = try self.expect(.rparen);

                return Parameter{ .list = try items.toOwnedSlice() };
            },
            .keyword => {
                // Typed parameter: TYPE(params)
                const type_token = self.advance().?;

                // Check if followed by lparen
                if (self.peek()) |next| {
                    if (next.type == .lparen) {
                        _ = self.advance();
                        const params = try self.parseParameterList();
                        _ = try self.expect(.rparen);

                        return Parameter{ .typed = TypedParameter{
                            .type_name = type_token.value,
                            .parameters = params,
                        } };
                    }
                }

                // Just a keyword used as string/enum
                return Parameter{ .enumeration = type_token.value };
            },
            else => {
                _ = self.advance();
                return error.UnexpectedToken;
            },
        }
    }
};

/// Parse STEP tokens into a StepFile
pub fn parse(allocator: std.mem.Allocator, tokens: []const Token) ParseError!StepFile {
    var parser = Parser.init(allocator, tokens);
    return parser.parse();
}

// Tests
test "parse simple entity" {
    const allocator = std.testing.allocator;
    const input = "ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('test'),'1');\nFILE_NAME('test.step','2024-01-01',(''),(''),'',' ','');\nFILE_SCHEMA(('AUTOMOTIVE_DESIGN'));\nENDSEC;\nDATA;\n#1 = CARTESIAN_POINT('NONE', (0.0, 1.0, 2.0));\nENDSEC;\nEND-ISO-10303-21;";
    const tokens = try tokenizer.tokenize(allocator, input);
    defer allocator.free(tokens);

    var step_file = try parse(allocator, tokens);
    defer step_file.deinit();

    try std.testing.expectEqual(@as(usize, 1), step_file.entities.count());
    const entity = step_file.getEntity(1).?;
    try std.testing.expectEqualStrings("CARTESIAN_POINT", entity.type_name);
    try std.testing.expectEqual(@as(usize, 2), entity.parameters.len);
}
