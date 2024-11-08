use nom::{
    branch::alt,
    bytes::complete::{tag, take_until},
    character::complete::{
        alpha1, alphanumeric1, char, digit1, multispace0, newline, space0, space1,
    },
    combinator::{map, map_res, opt, recognize, value},
    multi::{many0, separated_list0, separated_list1},
    sequence::{delimited, pair, preceded, terminated, tuple},
    IResult,
};

use crate::ast::*;
use crate::utils::ws;

pub fn parse_statement(input: &str) -> IResult<&str, Statement> {
    alt((
        map(parse_physical_quantity, Statement::PhysicalQuantity),
        map(parse_bilateral_quantity, Statement::BilateralQuantity),
        // Add other statement types...
    ))(input)
}

pub fn parse_physical_quantity(input: &str) -> IResult<&str, PhysicalQuantity> {
    let (input, sign) = opt(alt((char('+'), char('-'))))(input)?;
    let (input, value) = parse_number(input)?;
    let (input, unit) = opt(preceded(space0, parse_identifier))(input)?;

    let value = match sign {
        Some('-') => -value,
        _ => value,
    };

    Ok((input, PhysicalQuantity { value, unit }))
}

pub fn parse_bilateral_quantity(input: &str) -> IResult<&str, BilateralQuantity> {
    let (input, qty) = parse_physical_quantity(input)?;
    let (input, _) = ws(alt((tag("+/-"), tag("±"))))(input)?;
    let (input, tolerance) = parse_tolerance(input)?;

    Ok((
        input,
        BilateralQuantity {
            value: qty.value,
            unit: qty.unit,
            tolerance: Box::new(tolerance),
        },
    ))
}

pub fn parse_tolerance(input: &str) -> IResult<&str, Tolerance> {
    alt((
        // Parse percentage tolerance (e.g., 5%)
        map(terminated(parse_number, char('%')), Tolerance::Percentage),
        // Parse absolute tolerance (e.g., 0.1V)
        map(parse_physical_quantity, |qty| {
            Tolerance::Absolute(Box::new(BilateralQuantity {
                value: qty.value,
                unit: qty.unit,
                tolerance: Box::new(Tolerance::Percentage(0.0)), // Default tolerance
            }))
        }),
    ))(input)
}

pub fn parse_file_input(input: &str) -> IResult<&str, Vec<Statement>> {
    map(
        many0(alt((map(parse_newline, |_| vec![]), parse_stmt))),
        |nested_vecs: Vec<Vec<Statement>>| nested_vecs.into_iter().flatten().collect(),
    )(input)
}

pub fn parse_stmt(input: &str) -> IResult<&str, Vec<Statement>> {
    alt((
        parse_simple_stmts,
        map(parse_block, |stmt| vec![stmt]),
    ))(input)
}

pub fn parse_simple_stmts(input: &str) -> IResult<&str, Vec<Statement>> {
    let (input, stmts) = separated_list1(char(';'), parse_simple_stmt)(input)?;
    let (input, _) = opt(char(';'))(input)?;
    let (input, _) = parse_newline(input)?;
    Ok((input, stmts))
}

pub fn parse_simple_stmt(input: &str) -> IResult<&str, Statement> {
    alt((
        parse_import_stmt,
        parse_dep_import_stmt,
        parse_assign_stmt,
        parse_connect_stmt,
        parse_retype_stmt,
        parse_pindef_stmt,
        parse_signaldef_stmt,
        parse_assert_stmt,
        parse_declaration_stmt,
        parse_string_stmt,
        parse_pass_stmt,
        parse_comment,
    ))(input)
}

pub fn parse_import_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, _) = tag("from")(input)?;
    let (input, _) = space1(input)?;
    let (input, module) = parse_identifier(input)?;
    let (input, _) = space1(input)?;
    let (input, _) = tag("import")(input)?;
    let (input, _) = space1(input)?;
    let (input, items) = separated_list1(
        tuple((space0, char(','), space0)),
        parse_identifier
    )(input)?;

    Ok((
        input,
        Statement::Import(ImportStmt::FromImport {
            module: module.to_string(),
            items: items.into_iter().map(|s| s.to_string()).collect(),
        }),
    ))
}

pub fn parse_dep_import_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, _) = tag("from")(input)?;
    let (input, _) = space1(input)?;
    let (input, path) = delimited(char('"'), take_until("\""), char('"'))(input)?;
    let (input, _) = space1(input)?;
    let (input, _) = tag("import")(input)?;
    let (input, _) = space1(input)?;
    let (input, _) = tag("from")(input)?;
    let (input, _) = space1(input)?;
    let (input, module) = parse_identifier(input)?;

    Ok((
        input,
        Statement::Import(ImportStmt::FromStringImport {
            path: path.to_string(),
            items: vec![module],
        })
    ))
}

pub fn parse_assign_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, target) = parse_identifier(input)?;
    let (input, _) = space0(input)?;
    let (input, operator) = parse_assignment_operator(input)?;
    let (input, _) = space0(input)?;
    let (input, value) = parse_expression(input)?;
    let (input, type_info) = opt(preceded(
        tuple((space0, char(':'), space0)),
        parse_identifier,
    ))(input)?;

    Ok((
        input,
        Statement::Assignment(AssignmentStmt {
            target,
            operator,
            value,
            type_info,
        }),
    ))
}

fn parse_assignment_operator(input: &str) -> IResult<&str, AssignmentOperator> {
    alt((
        value(AssignmentOperator::Simple, tag("=")),
        value(AssignmentOperator::Add, tag("+=")),
        value(AssignmentOperator::Subtract, tag("-=")),
        value(AssignmentOperator::Multiply, tag("*=")),
        value(AssignmentOperator::Divide, tag("/=")),
        value(AssignmentOperator::Power, tag("**=")),
        value(AssignmentOperator::IntegerDivide, tag("//=")),
        value(AssignmentOperator::BitwiseOr, tag("|=")),
        value(AssignmentOperator::BitwiseAnd, tag("&=")),
        value(AssignmentOperator::BitwiseXor, tag("^=")),
        value(AssignmentOperator::LeftShift, tag("<<=")),
        value(AssignmentOperator::RightShift, tag(">>=")),
        value(AssignmentOperator::At, tag("@=")),
    ))(input)
}

pub fn parse_connect_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, left) = parse_connectable(input)?;
    let (input, _) = ws(char('~'))(input)?;
    let (input, right) = parse_connectable(input)?;

    Ok((input, Statement::Connection(ConnectionStmt { left, right })))
}

fn parse_connectable(input: &str) -> IResult<&str, Connectable> {
    alt((
        map(
            tuple((parse_identifier, preceded(char('.'), parse_identifier))),
            |(name, pin)| Connectable::Pin(format!("{}.{}", name, pin)),
        ),
        map(preceded(tag("signal"), ws(parse_identifier)), Connectable::Signal),
        map(parse_identifier, Connectable::Name),
    ))(input)
}

pub fn parse_compound_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, block_type) = parse_block_type(input)?;
    let (input, _) = space1(input)?;
    let (input, name) = parse_identifier(input)?;
    let (input, parent) = opt(preceded(
        tuple((space0, char('('), space0)),
        terminated(parse_identifier, tuple((space0, char(')')))),
    ))(input)?;
    let (input, _) = space0(input)?;
    let (input, _) = char('{')(input)?;
    let (input, body) = many0(preceded(space0, parse_stmt))(input)?;
    let (input, _) = space0(input)?;
    let (input, _) = char('}')(input)?;

    Ok((
        input,
        Statement::Block(BlockStmt {
            block_type,
            name,
            parent,
            body: body.into_iter().flatten().collect(),
        }),
    ))
}

fn parse_block_type(input: &str) -> IResult<&str, BlockType> {
    alt((
        value(BlockType::Component, tag("component")),
        value(BlockType::Module, tag("module")),
        value(BlockType::Interface, tag("interface")),
    ))(input)
}

pub fn parse_declaration_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, name) = parse_identifier(input)?;
    let (input, _) = space0(input)?;
    let (input, _) = char(':')(input)?;
    let (input, _) = space0(input)?;
    let (input, type_info) = parse_identifier(input)?;

    Ok((
        input,
        Statement::Declaration(DeclarationStmt { name, type_info }),
    ))
}

pub fn parse_pass_stmt(input: &str) -> IResult<&str, Statement> {
    map(tag("pass"), |_| Statement::Pass)(input)
}

pub fn parse_string_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, content) = delimited(char('"'), take_until("\""), char('"'))(input)?;

    Ok((input, Statement::DocString(content.to_string())))
}

pub fn parse_assert_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, _) = tag("assert")(input)?;
    let (input, _) = space1(input)?;
    let (input, condition) = parse_expression(input)?;

    Ok((input, Statement::Assert(AssertStmt { condition })))
}

pub fn parse_retype_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, _) = tag("retype")(input)?;
    let (input, _) = space1(input)?;
    let (input, source) = parse_identifier(input)?;
    let (input, _) = space1(input)?;
    let (input, _) = tag("as")(input)?;
    let (input, _) = space1(input)?;
    let (input, target) = parse_identifier(input)?;

    Ok((input, Statement::Retype(RetypeStmt { source, target })))
}

pub fn parse_pindef_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, _) = tag("pin")(input)?;
    let (input, _) = space1(input)?;
    let (input, pin_id) = alt((
        map(parse_identifier, PinIdentifier::Name),
        map(map_res(digit1, str::parse), PinIdentifier::Number),
        map(parse_string_literal, PinIdentifier::StringLiteral),
    ))(input)?;

    Ok((input, Statement::PinDef(pin_id)))
}

pub fn parse_signaldef_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, _) = tag("signal")(input)?;
    let (input, _) = space1(input)?;
    let (input, name) = parse_identifier(input)?;

    Ok((input, Statement::SignalDef(name)))
}

// Move this function up, before parse_expression
fn parse_primary_expression(input: &str) -> IResult<&str, Expression> {
    alt((
        map(parse_string_literal, Expression::String),
        map(parse_number, Expression::Number),
        map(parse_boolean, Expression::Boolean),
        map(parse_identifier, Expression::Identifier),
        map(parse_physical_quantity, Expression::Physical),
        map(parse_bilateral_quantity, Expression::Bilateral),
        map(
            delimited(
                ws(char('(')),
                parse_expression,
                ws(char(')'))
            ),
            |expr| Expression::Group(Box::new(expr))
        ),
    ))(input)
}

pub fn parse_expression(input: &str) -> IResult<&str, Expression> {
    alt((
        parse_binary_expression,
        parse_unary_expression,
        parse_primary_expression,
        map(
            preceded(ws(tag("new")), parse_identifier),
            Expression::New
        ),
    ))(input)
}

fn parse_binary_expression(input: &str) -> IResult<&str, Expression> {
    let (input, first) = parse_term(input)?;
    let (input, rest) = many0(tuple((
        ws(alt((
            value(Operator::Add, char('+')),
            value(Operator::Subtract, char('-')),
            value(Operator::BitwiseOr, char('|')),
            value(Operator::BitwiseAnd, char('&')),
        ))),
        parse_term
    )))(input)?;

    Ok((
        input,
        rest.into_iter().fold(first, |acc, (op, expr)| {
            Expression::BinaryOp(Box::new(acc), op, Box::new(expr))
        }),
    ))
}

fn parse_term(input: &str) -> IResult<&str, Expression> {
    let (input, first) = parse_factor(input)?;
    let (input, rest) = many0(tuple((
        ws(alt((
            value(Operator::Multiply, char('*')),
            value(Operator::Divide, char('/')),
        ))),
        parse_factor
    )))(input)?;

    Ok((
        input,
        rest.into_iter().fold(first, |acc, (op, expr)| {
            Expression::BinaryOp(Box::new(acc), op, Box::new(expr))
        }),
    ))
}

fn parse_factor(input: &str) -> IResult<&str, Expression> {
    let (input, first) = parse_unary_expression(input)?;
    let (input, rest) = many0(tuple((
        ws(value(Operator::Power, tag("**"))),
        parse_unary_expression
    )))(input)?;

    Ok((
        input,
        rest.into_iter().fold(first, |acc, (op, expr)| {
            Expression::BinaryOp(Box::new(acc), op, Box::new(expr))
        }),
    ))
}

fn parse_unary_expression(input: &str) -> IResult<&str, Expression> {
    alt((
        map(
            tuple((
                alt((
                    value(Operator::Plus, char('+')),
                    value(Operator::Minus, char('-')),
                )),
                parse_primary_expression
            )),
            |(op, expr)| Expression::UnaryOp(op, Box::new(expr)),
        ),
        parse_primary_expression,
    ))(input)
}

pub fn parse_string_literal(input: &str) -> IResult<&str, String> {
    alt((
        delimited(tag("\"\"\""), take_until("\"\"\""), tag("\"\"\"")),
        delimited(tag("'''"), take_until("'''"), tag("'''")),
        delimited(char('"'), take_until("\""), char('"')),
        delimited(char('\''), take_until("'"), char('\'')),
    ))(input)
    .map(|(i, s)| (i, s.to_string()))
}

fn parse_number(input: &str) -> IResult<&str, f64> {
    map_res(
        recognize(tuple((
            opt(char('-')),
            digit1,
            opt(tuple((char('.'), digit1))),
            opt(tuple((
                alt((char('e'), char('E'))),
                opt(alt((char('+'), char('-')))),
                digit1,
            ))),
        ))),
        str::parse::<f64>,
    )(input)
}

fn parse_boolean(input: &str) -> IResult<&str, bool> {
    alt((value(true, tag("True")), value(false, tag("False"))))(input)
}

fn parse_identifier(input: &str) -> IResult<&str, String> {
    map(
        recognize(pair(
            alt((alpha1, tag("_"))),
            many0(alt((alphanumeric1, tag("_")))),
        )),
        String::from,
    )(input)
}

pub fn parse_newline(input: &str) -> IResult<&str, ()> {
    map(newline, |_| ())(input)
}

pub fn parse_statements(input: &str) -> IResult<&str, Vec<Statement>> {
    many0(delimited(multispace0, parse_statement, multispace0))(input)
}

pub fn parse_import(input: &str) -> IResult<&str, Statement> {
    alt((parse_import_stmt, parse_dep_import_stmt))(input)
}

pub fn parse_arithmetic(input: &str) -> IResult<&str, Expression> {
    parse_expression(input)
}

pub fn parse_block(input: &str) -> IResult<&str, Statement> {
    let (input, block_type) = parse_block_type(input)?;
    let (input, _) = space1(input)?;
    let (input, name) = parse_identifier(input)?;
    let (input, parent) = opt(preceded(
        tuple((space1, tag("from"), space1)),
        parse_identifier,
    ))(input)?;
    let (input, _) = space0(input)?;
    let (input, _) = char(':')(input)?;
    let (input, _) = multispace0(input)?;
    let (input, body) = many0(alt((
        map(parse_newline, |_| vec![]),
        map(parse_comment, |stmt| vec![stmt]),
        map(parse_docstring, |stmt| vec![stmt]),
        preceded(multispace0, parse_stmt),
    )))(input)?;

    Ok((
        input,
        Statement::Block(BlockStmt {
            block_type,
            name,
            parent,
            body: body.into_iter().flatten().collect(),
        }),
    ))
}

pub fn parse_assignment(input: &str) -> IResult<&str, Statement> {
    parse_assign_stmt(input)
}

pub fn parse_connection(input: &str) -> IResult<&str, Statement> {
    parse_connect_stmt(input)
}

fn parse_comparison_operator(input: &str) -> IResult<&str, Operator> {
    alt((
        value(Operator::LessThan, tag("<")),
        value(Operator::GreaterThan, tag(">")),
        value(Operator::LessEqual, tag("<=")),
        value(Operator::GreaterEqual, tag(">=")),
        value(Operator::Equal, tag("==")),
        value(Operator::NotEqual, alt((tag("!="), tag("<>")))),
        value(Operator::Within, tag("within")),
    ))(input)
}

pub fn parse_docstring(input: &str) -> IResult<&str, Statement> {
    let (input, content) = alt((
        delimited(tag("\"\"\""), take_until("\"\"\""), tag("\"\"\"")),
        delimited(tag("'''"), take_until("'''"), tag("'''")),
        delimited(char('"'), take_until("\""), char('"')),
        delimited(char('\''), take_until("'"), char('\'')),
    ))(input)?;

    Ok((input, Statement::DocString(content.to_string())))
}

pub fn parse_comment(input: &str) -> IResult<&str, Statement> {
    let (input, _) = char('#')(input)?;
    let (input, content) = take_until("\n")(input)?;
    let (input, _) = opt(newline)(input)?;
    Ok((input, Statement::Comment(content.trim().to_string())))
}

pub fn parse_line(input: &str) -> IResult<&str, Vec<Statement>> {
    terminated(separated_list0(char(';'), parse_simple_stmt), opt(newline))(input)
}

pub fn parse_lines(input: &str) -> IResult<&str, Vec<Statement>> {
    let mut statements = Vec::new();
    let mut remaining = input;

    while !remaining.is_empty() {
        // Skip empty lines and whitespace
        let (after_space, _) = multispace0(remaining)?;
        if after_space.is_empty() {
            break;
        }
        remaining = after_space;

        // Parse statement with potential line continuation
        match parse_statement_with_continuation(remaining) {
            Ok((after_stmt, stmt)) => {
                statements.push(stmt);
                remaining = after_stmt;
            }
            Err(nom::Err::Error(_)) => {
                // Skip problematic line
                if let Ok((after_line, _)) = take_until_newline(remaining) {
                    remaining = after_line;
                } else {
                    break;
                }
            }
            Err(e) => return Err(e),
        }
    }

    Ok((remaining, statements))
}

pub fn parse_cumulative_assign(input: &str) -> IResult<&str, Statement> {
    let (input, target) = parse_identifier(input)?;
    let (input, type_info) = opt(preceded(
        tuple((space0, char(':'), space0)),
        parse_identifier,
    ))(input)?;
    let (input, operator) = alt((
        value(AssignmentOperator::Add, tag("+=")),
        value(AssignmentOperator::Subtract, tag("-=")),
    ))(input)?;
    let (input, value) = parse_cumulative_value(input)?;

    Ok((
        input,
        Statement::CumulativeAssign(CumulativeAssignStmt {
            target,
            operator,
            value,
            type_info,
        }),
    ))
}

pub fn parse_set_assign(input: &str) -> IResult<&str, Statement> {
    let (input, target) = parse_identifier(input)?;
    let (input, type_info) = opt(preceded(
        tuple((space0, char(':'), space0)),
        parse_identifier,
    ))(input)?;
    let (input, operator) = alt((
        value(AssignmentOperator::BitwiseOr, tag("|=")),
        value(AssignmentOperator::BitwiseAnd, tag("&=")),
    ))(input)?;
    let (input, value) = parse_cumulative_value(input)?;

    Ok((
        input,
        Statement::SetAssign(SetAssignStmt {
            target,
            operator,
            value,
            type_info,
        }),
    ))
}

pub fn parse_from_import(input: &str) -> IResult<&str, Statement> {
    let (input, _) = tag("from")(input)?;
    let (input, _) = space1(input)?;
    let (input, module) = parse_identifier(input)?;
    let (input, _) = space1(input)?;
    let (input, _) = tag("import")(input)?;
    let (input, _) = space1(input)?;
    let (input, items) = separated_list1(
        tuple((space0, char(','), space0)),
        parse_identifier
    )(input)?;

    Ok((
        input,
        Statement::Import(ImportStmt::FromImport {
            module: module.to_string(),
            items
        }),
    ))
}

pub fn parse_direct_import(input: &str) -> IResult<&str, Statement> {
    let (input, _) = tag("import")(input)?;
    let (input, _) = space1(input)?;
    let (input, module) = parse_identifier(input)?;

    Ok((
        input,
        Statement::Import(ImportStmt::DirectImport {
            module: module.to_string()
        }),
    ))
}

pub fn parse_from_string_import(input: &str) -> IResult<&str, Statement> {
    let (input, _) = tag("from")(input)?;
    let (input, _) = space1(input)?;
    let (input, path) = parse_string_literal(input)?;
    let (input, _) = space1(input)?;
    let (input, _) = tag("import")(input)?;
    let (input, _) = space1(input)?;
    let (input, items) =
        separated_list1(tuple((space0, char(','), space0)), parse_identifier)(input)?;

    Ok((
        input,
        Statement::Import(ImportStmt::FromStringImport {
            path,
            items,
        })
    ))
}

pub fn parse_import_items(input: &str) -> IResult<&str, Vec<String>> {
    separated_list1(tuple((space0, char(','), space0)), parse_identifier)(input)
}

// Make parse_identifier public
pub fn identifier(input: &str) -> IResult<&str, String> {
    parse_identifier(input)
}

pub fn parse_assert(input: &str) -> IResult<&str, Statement> {
    let (input, _) = tag("assert")(input)?;
    let (input, _) = space1(input)?;
    let (input, condition) = parse_expression(input)?;

    Ok((input, Statement::Assert(AssertStmt { condition })))
}

pub fn parse_retype(input: &str) -> IResult<&str, Statement> {
    let (input, source) = parse_identifier(input)?;
    let (input, _) = ws(tag("->"))(input)?;
    let (input, target) = parse_identifier(input)?;

    Ok((input, Statement::Retype(RetypeStmt { source, target })))
}

pub fn parse_signal_def(input: &str) -> IResult<&str, Statement> {
    let (input, _) = tag("signal")(input)?;
    let (input, _) = space1(input)?;
    let (input, name) = parse_identifier(input)?;

    Ok((input, Statement::SignalDef(name)))
}

pub fn parse_pin_def(input: &str) -> IResult<&str, Statement> {
    let (input, _) = tag("pin")(input)?;
    let (input, _) = space1(input)?;
    let (input, pin_id) = alt((
        map(parse_identifier, PinIdentifier::Name),
        map(map_res(digit1, str::parse), PinIdentifier::Number),
        map(parse_string_literal, PinIdentifier::StringLiteral),
    ))(input)?;

    Ok((input, Statement::PinDef(pin_id)))
}

pub fn parse_bound_quantity(input: &str) -> IResult<&str, Expression> {
    let (input, min) = parse_physical_quantity(input)?;
    let (input, _) = ws(tag("to"))(input)?;
    let (input, max) = parse_physical_quantity(input)?;

    Ok((
        input,
        Expression::BinaryOp(
            Box::new(Expression::Physical(min)),
            Operator::Within,
            Box::new(Expression::Physical(max)),
        ),
    ))
}

fn parse_cumulative_value(input: &str) -> IResult<&str, CumulativeValue> {
    alt((
        map(parse_physical_quantity, CumulativeValue::Physical),
        map(parse_expression, CumulativeValue::Arithmetic),
    ))(input)
}

// Implement comparison parsing
pub fn parse_comparison(input: &str) -> IResult<&str, Expression> {
    let (input, first) = parse_arithmetic(input)?;
    let (input, rest) = many0(tuple((ws(parse_comparison_operator), parse_arithmetic)))(input)?;

    Ok((
        input,
        rest.into_iter().fold(first, |acc, (op, expr)| {
            Expression::BinaryOp(Box::new(acc), op, Box::new(expr))
        }),
    ))
}

// Implement line continuation handling
pub fn handle_line_continuation(input: &str) -> IResult<&str, String> {
    let mut result = String::new();
    let mut remaining = input;

    while !remaining.is_empty() {
        match take_until_backslash(remaining) {
            Ok((after_line, line)) => {
                result.push_str(line.trim_end());
                // Handle the continuation
                let (next_line, _) = tuple((
                    char('\\'),
                    multispace0,
                    alt((tag("\r\n"), tag("\n"), tag("\r"))),
                    multispace0
                ))(after_line)?;
                
                if next_line.is_empty() {
                    break;
                }
                remaining = next_line;
            },
            Err(_) => {
                result.push_str(remaining.trim_end());
                break;
            }
        }
    }

    Ok(("", result))  // Return empty remaining input since we consumed it all
}

// Helper function to take content until backslash or end
fn take_until_backslash(input: &str) -> IResult<&str, &str> {
    let mut end_pos = 0;
    let mut in_string = false;
    let mut escape_next = false;

    for (i, c) in input.char_indices() {
        if escape_next {
            escape_next = false;
            continue;
        }

        match c {
            '\\' if !in_string => {
                end_pos = i;
                break;
            }
            '"' | '\'' => in_string = !in_string,
            '\\' => escape_next = true,
            _ => {}
        }
        end_pos = i + 1;
    }

    Ok((&input[end_pos..], &input[..end_pos]))
}

// Add support for parsing statements with line continuations
pub fn parse_statement_with_continuation(input: &str) -> IResult<&str, Statement> {
    let (remaining, joined_input) = handle_line_continuation(input)?;
    let joined = joined_input.to_string();
    parse_statement(&joined)
        .map(|(_, stmt)| (remaining, stmt))
        .map_err(|_| {
            nom::Err::Error(nom::error::Error::new(
                input,
                nom::error::ErrorKind::Fail
            ))
        })
}

// Helper function to take content until newline
fn take_until_newline(input: &str) -> IResult<&str, &str> {
    let newline_pos = input.find('\n').unwrap_or(input.len());
    Ok((&input[newline_pos..], &input[..newline_pos]))
}
