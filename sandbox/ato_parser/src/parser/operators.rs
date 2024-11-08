use nom::{
    branch::alt,
    bytes::complete::tag,
    character::complete::char,
    combinator::value,
    IResult,
};

use crate::ast::*;

pub fn parse_assignment_operator(input: &str) -> IResult<&str, AssignmentOperator> {
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

pub fn parse_comparison_operator(input: &str) -> IResult<&str, Operator> {
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

pub fn parse_arithmetic_operator(input: &str) -> IResult<&str, Operator> {
    alt((
        value(Operator::Add, char('+')),
        value(Operator::Subtract, char('-')),
        value(Operator::Multiply, char('*')),
        value(Operator::Divide, char('/')),
        value(Operator::Power, tag("**")),
        value(Operator::IntegerDivide, tag("//")),
    ))(input)
}

pub fn parse_bitwise_operator(input: &str) -> IResult<&str, Operator> {
    alt((
        value(Operator::BitwiseOr, char('|')),
        value(Operator::BitwiseAnd, char('&')),
        value(Operator::BitwiseXor, char('^')),
        value(Operator::LeftShift, tag("<<")),
        value(Operator::RightShift, tag(">>")),
    ))(input)
}

pub fn parse_unary_operator(input: &str) -> IResult<&str, Operator> {
    alt((
        value(Operator::Plus, char('+')),
        value(Operator::Minus, char('-')),
        value(Operator::BitwiseNot, char('~')),
    ))(input)
} 