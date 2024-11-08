use thiserror::Error;

#[derive(Error, Debug)]
pub enum ParserError {
    #[error("Syntax error at position {position}: {message}")]
    Syntax {
        position: usize,
        message: String,
    },
    // ... other error variants

    #[error("Indentation error: {0}")]
    IndentationError(String),

    #[error("Invalid block type: expected 'component', 'module', or 'interface'")]
    InvalidBlockType(String),

    #[error("Invalid physical quantity: {0}")]
    InvalidPhysicalQuantity(String),

    #[error("Invalid tolerance specification: {0}")]
    InvalidTolerance(String),

    #[error("Invalid operator: {0}")]
    InvalidOperator(String),
}

#[derive(Debug)]
pub struct ParseErrorInfo {
    pub message: String,
    pub line: usize,
    pub column: usize,
    pub context: String,
    pub snippet: String,
}

impl ParseErrorInfo {
    pub fn from_error(input: &str, error: ParserError) -> Self {
        let (line, column, snippet) = get_error_location(input, &error);
        ParseErrorInfo {
            message: error.to_string(),
            line,
            column,
            context: get_error_context(&error),
            snippet,
        }
    }

    pub fn format_error(&self) -> String {
        format!("{} at line {}, column {}\n{}", 
            self.message, self.line, self.column, self.snippet)
    }
}

// Updated to use underscore prefix for unused parameters
pub fn get_error_location(_input: &str, _error: &ParserError) -> (usize, usize, String) {
    // Implementation to get error location
    (0, 0, String::new()) // Placeholder - implement actual error location logic
}

pub fn get_error_context(_error: &ParserError) -> String {
    // Implementation to get error context
    String::new() // Placeholder - implement actual error context logic
}

pub fn convert_error(input: &str, error: nom::Err<nom::error::Error<&str>>) -> ParserError {
    match error {
        nom::Err::Error(e) | nom::Err::Failure(e) => {
            ParserError::Syntax {
                position: input.len() - e.input.len(),
                message: format!("Syntax error: {:?}", e.code),
            }
        }
        nom::Err::Incomplete(_) => ParserError::Syntax {
            position: input.len(),
            message: "Incomplete input".to_string(),
        },
    }
}
