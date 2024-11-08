use nom::{
    branch::alt,
    bytes::complete::{tag, take_until},
    character::complete::{alpha1, alphanumeric1, char, digit1, newline, none_of},
    combinator::{map, map_res, opt, recognize, value},
    multi::many0,
    sequence::{delimited, pair, tuple},
    IResult,
};

use crate::ast::Statement;

pub fn parse_identifier(input: &str) -> IResult<&str, String> {
    map(
        recognize(pair(
            alt((alpha1, tag("_"))),
            many0(alt((alphanumeric1, tag("_")))),
        )),
        String::from,
    )(input)
}

pub fn parse_number(input: &str) -> IResult<&str, f64> {
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

pub fn parse_boolean(input: &str) -> IResult<&str, bool> {
    alt((
        value(true, tag("True")),
        value(false, tag("False"))
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

pub fn parse_newline(input: &str) -> IResult<&str, ()> {
    map(newline, |_| ())(input)
}

pub fn parse_comment(input: &str) -> IResult<&str, Statement> {
    let (input, _) = char('#')(input)?;
    let (input, content) = alt((
        take_until("\n"),
        recognize(many0(none_of("\n")))  // Handle end of input
    ))(input)?;
    let (input, _) = opt(newline)(input)?;
    Ok((input, Statement::Comment(content.trim().to_string())))
} 