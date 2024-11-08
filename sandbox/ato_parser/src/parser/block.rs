use nom::{
    branch::alt,
    bytes::complete::tag,
    character::complete::{char, multispace0, space0, space1},
    combinator::{map, opt},
    multi::many0,
    sequence::{preceded, tuple},
    IResult,
};

use crate::ast::{Statement, BlockStmt, BlockType};
use super::basic::{parse_identifier, parse_string_literal, parse_comment, parse_newline};
use super::statement::parse_stmt;

pub fn parse_docstring(input: &str) -> IResult<&str, Statement> {
    map(parse_string_literal, Statement::DocString)(input)
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
        map(parse_docstring, |stmt| vec![stmt]),
        map(parse_comment, |stmt| vec![stmt]),
        preceded(multispace0, parse_stmt),
    )))(input)?;

    let body = body.into_iter()
        .flatten()
        .collect::<Vec<_>>();

    Ok((input, Statement::Block(BlockStmt {
        block_type,
        name,
        parent,
        body,
    })))
}

pub fn parse_block_type(input: &str) -> IResult<&str, BlockType> {
    alt((
        map(tag("component"), |_| BlockType::Component),
        map(tag("module"), |_| BlockType::Module),
        map(tag("interface"), |_| BlockType::Interface),
    ))(input)
} 