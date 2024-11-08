use nom::{
    branch::alt,
    bytes::complete::tag,
    character::complete::{char, space0, space1},
    combinator::{map, map_res, opt},
    multi::separated_list1,
    sequence::{preceded, tuple},
    IResult,
};

use crate::ast::*;
use super::{
    basic::{parse_identifier, parse_newline, parse_string_literal},
    expression::parse_expression,
    import::{parse_dep_import_stmt, parse_import_stmt},
    operators::parse_assignment_operator,
    physical::{parse_bilateral_quantity, parse_physical_quantity},
    utils::ws,
};

pub fn parse_statement(input: &str) -> IResult<&str, Statement> {
    alt((
        map(parse_physical_quantity, Statement::PhysicalQuantity),
        map(parse_bilateral_quantity, Statement::BilateralQuantity),
        parse_simple_stmt,
        parse_block,
    ))(input)
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

pub fn parse_assign_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, target) = parse_identifier(input)?;
    let (input, type_info) = opt(preceded(
        tuple((space0, char(':'), space0)),
        parse_identifier,
    ))(input)?;
    let (input, _) = space0(input)?;
    let (input, operator) = parse_assignment_operator(input)?;
    let (input, _) = space0(input)?;
    let (input, value) = parse_expression(input)?;

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

pub fn parse_connect_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, left) = parse_connectable(input)?;
    let (input, _) = ws(char('~'))(input)?;
    let (input, right) = parse_connectable(input)?;

    Ok((input, Statement::Connection(ConnectionStmt { left, right })))
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
    let (input, content) = parse_string_literal(input)?;
    Ok((input, Statement::DocString(content)))
}

pub fn parse_assert_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, _) = tag("assert")(input)?;
    let (input, _) = space1(input)?;
    let (input, condition) = parse_expression(input)?;

    Ok((input, Statement::Assert(AssertStmt { condition })))
}

pub fn parse_retype_stmt(input: &str) -> IResult<&str, Statement> {
    let (input, source) = parse_identifier(input)?;
    let (input, _) = ws(tag("->"))(input)?;
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

pub fn parse_line(input: &str) -> IResult<&str, Vec<Statement>> {
    let (input, stmts) = separated_list0(char(';'), parse_simple_stmt)(input)?;
    let (input, _) = opt(char(';'))(input)?;
    let (input, comment) = opt(parse_comment)(input)?;
    let (input, _) = opt(newline)(input)?;

    let mut result = stmts;
    if let Some(c) = comment {
        result.push(c);
    }
    Ok((input, result))
}