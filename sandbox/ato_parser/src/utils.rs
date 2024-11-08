use nom::{character::complete::multispace0, sequence::delimited, IResult};

pub fn ws<'a, F: 'a, O>(inner: F) -> impl FnMut(&'a str) -> IResult<&'a str, O>
where
    F: FnMut(&'a str) -> IResult<&'a str, O>,
{
    delimited(multispace0, inner, multispace0)
}

// Add other utility functions here...
// (handle_whitespace, handle_line_continuation, etc.)
