use crate::ast::*;
use super::{
    basic::{parse_identifier, parse_string_literal},
    utils::ws,
};

use nom::{
    branch::alt,
    bytes::complete::{tag, take_until},
    character::complete::{char, space0, space1},
    combinator::map,
    multi::separated_list1,
    sequence::{delimited, preceded, tuple},
    IResult,
};

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
    let (input, items) = separated_list1(
        tuple((space0, char(','), space0)),
        parse_identifier
    )(input)?;

    Ok((
        input,
        Statement::Import(ImportStmt::FromStringImport {
            path,
            items,
        })
    ))
}

pub fn parse_import_items(input: &str) -> IResult<&str, Vec<String>> {
    separated_list1(
        tuple((space0, char(','), space0)),
        parse_identifier
    )(input)
}