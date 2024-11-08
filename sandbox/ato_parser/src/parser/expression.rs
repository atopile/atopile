use crate::ast::*;
use super::{
    basic::{parse_boolean, parse_identifier, parse_number, parse_string_literal},
    operators::{parse_comparison_operator, parse_unary_operator},
    physical::{parse_bilateral_quantity, parse_physical_quantity},
    utils::ws,
};

use nom::{
    branch::alt,
    bytes::complete::tag,
    character::complete::char,
    combinator::{map, not, value},
    multi::many0,
    sequence::{delimited, preceded, tuple},
    IResult,
};

pub fn parse_expression(input: &str) -> IResult<&str, Expression> {
    alt((
        map(
            preceded(ws(tag("new")), parse_identifier),
            Expression::New
        ),
        parse_binary_expression,
        parse_unary_expression,
        parse_primary_expression,
    ))(input)
}

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

    let (input, _) = not(ws(alt((
        char('+'),
        char('-'),
        char('|'),
        char('&'),
        char('*'),
        char('/'),
    ))))(input)?;

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

    let (input, _) = not(ws(alt((
        char('*'),
        char('/'),
    ))))(input)?;

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

    let (input, _) = not(ws(tag("**")))(input)?;

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
                parse_unary_expression
            )),
            |(op, expr)| Expression::UnaryOp(op, Box::new(expr)),
        ),
        parse_primary_expression,
    ))(input)
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

pub fn parse_comparison(input: &str) -> IResult<&str, Expression> {
    let (input, first) = parse_arithmetic(input)?;
    let (input, rest) = many0(tuple((
        ws(parse_comparison_operator),
        parse_arithmetic
    )))(input)?;

    Ok((
        input,
        rest.into_iter().fold(first, |acc, (op, expr)| {
            Expression::BinaryOp(Box::new(acc), op, Box::new(expr))
        }),
    ))
}

pub fn parse_arithmetic(input: &str) -> IResult<&str, Expression> {
    parse_expression(input)
}