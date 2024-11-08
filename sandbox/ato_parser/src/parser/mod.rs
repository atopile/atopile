use nom::{
    branch::alt,
    bytes::complete::tag,
    character::complete::{
        alpha1, alphanumeric1, char, digit1, multispace0, multispace1,
        space0, space1,
    },
    combinator::{map, map_res, not, opt, recognize, value},
    multi::{many0, separated_list0, separated_list1},
    sequence::{delimited, pair, preceded, terminated, tuple},
    IResult,
};

use crate::ast::Statement;

mod basic;
mod block;
mod expression;
mod import;
mod operators;
mod physical;
mod statement;
pub(crate) mod utils;

// Re-export parsers for public API
pub use statement::parse_statement;
pub use block::parse_block;
pub use expression::parse_expression;
pub use import::parse_import_stmt;
pub use physical::{parse_physical_quantity, parse_bilateral_quantity};
pub use basic::parse_identifier;

// Re-export for tests
#[cfg(test)]
pub use {
    statement::{parse_assignment, parse_connection, parse_line},
    block::parse_block,
    expression::parse_arithmetic,
    utils::handle_line_continuation,
};

/// Parse a complete file
pub fn parse_file(input: &str) -> Result<Vec<Statement>, String> {
    match parse_statements(input) {
        Ok((remaining, statements)) => {
            if remaining.trim().is_empty() {
                Ok(statements)
            } else {
                Err(format!("Failed to parse complete input. Remaining: {}", remaining))
            }
        }
        Err(e) => Err(format!("Parse error: {}", e)),
    }
}

/// Parse whitespace-separated statements
pub(crate) fn parse_statements(input: &str) -> IResult<&str, Vec<Statement>> {
    many0(delimited(
        multispace0,
        parse_statement,
        multispace0
    ))(input)
}