use nom::{
    branch::alt,
    bytes::complete::tag,
    character::complete::{char, multispace0, multispace1},
    sequence::{delimited, tuple},
    IResult,
};

/// Helper function to handle whitespace around a parser
pub fn ws<'a, F: 'a, O>(inner: F) -> impl FnMut(&'a str) -> IResult<&'a str, O>
where
    F: FnMut(&'a str) -> IResult<&'a str, O>,
{
    delimited(multispace0, inner, multispace0)
}

/// Helper function to handle required whitespace around a parser
pub fn ws1<'a, F, O>(inner: F) -> impl FnMut(&'a str) -> IResult<&'a str, O>
where
    F: FnMut(&'a str) -> IResult<&'a str, O>,
{
    delimited(multispace1, inner, multispace0)
}

/// Helper function to handle line continuation
pub fn handle_line_continuation(input: &str) -> IResult<&str, String> {
    let mut result = String::new();
    let mut remaining = input;

    while !remaining.is_empty() {
        match take_until_backslash(remaining) {
            Ok((after_line, line)) => {
                result.push_str(line.trim_end());
                let (next_line, _) = tuple((
                    char('\\'),
                    multispace0,
                    alt((tag("\r\n"), tag("\n"), tag("\r"))),
                    multispace0
                ))(after_line)?;
                remaining = next_line;
            },
            Err(_) => {
                result.push_str(remaining);
                break;
            }
        }
    }

    Ok(("", result.trim().to_string()))
}

/// Helper function to take content until backslash or end
fn take_until_backslash(input: &str) -> IResult<&str, &str> {
    let mut pos = 0;
    let mut in_string = false;
    let mut escape_next = false;

    for (i, c) in input.char_indices() {
        if escape_next {
            escape_next = false;
            continue;
        }

        match c {
            '\\' if !in_string => {
                return Ok((&input[i..], &input[..i]));
            }
            '"' | '\'' => in_string = !in_string,
            '\\' => escape_next = true,
            _ => {}
        }
        pos = i + 1;
    }

    Ok(("", &input[..pos]))
}

/// Helper function to take content until newline
pub fn take_until_newline(input: &str) -> IResult<&str, &str> {
    let newline_pos = input.find('\n').unwrap_or(input.len());
    Ok((&input[newline_pos..], &input[..newline_pos]))
} 