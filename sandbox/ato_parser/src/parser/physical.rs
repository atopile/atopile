use crate::ast::*;
use super::{
    basic::{parse_identifier, parse_number},
    utils::ws,
};

use nom::{
    branch::alt,
    bytes::complete::tag,
    character::complete::{alpha1, alphanumeric1, char, digit1, multispace1},
    combinator::{map, map_res, opt, recognize, value},
    multi::many0,
    sequence::{pair, preceded, terminated},
    IResult,
};

pub fn parse_physical_quantity(input: &str) -> IResult<&str, PhysicalQuantity> {
    let (input, sign) = opt(alt((char('+'), char('-'))))(input)?;
    let (input, value) = recognize(tuple((
        digit1,
        opt(tuple((char('.'), digit1)))
    )))(input)?;
    
    let value = value.parse::<f64>().unwrap();
    let value = if let Some('-') = sign { -value } else { value };
    
    let (input, unit) = opt(preceded(
        multispace1,
        recognize(pair(
            alpha1,
            many0(alt((alphanumeric1, tag("_"))))
        ))
    ))(input)?;

    Ok((input, PhysicalQuantity {
        value,
        unit: unit.map(|s| s.to_string())
    }))
}

pub fn parse_bilateral_quantity(input: &str) -> IResult<&str, BilateralQuantity> {
    let (input, base) = parse_physical_quantity(input)?;
    let (input, _) = ws(alt((tag("+/-"), tag("±"))))(input)?;
    let (input, tolerance) = parse_tolerance(input)?;
    
    Ok((input, BilateralQuantity {
        value: base.value,
        unit: base.unit,
        tolerance: Box::new(tolerance)
    }))
}

fn parse_tolerance(input: &str) -> IResult<&str, Tolerance> {
    alt((
        // Parse percentage tolerance (e.g., 5%)
        map(
            terminated(parse_number, char('%')), 
            Tolerance::Percentage
        ),
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