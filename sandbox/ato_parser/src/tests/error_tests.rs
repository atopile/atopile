use crate::*;

#[test]
fn test_error_invalid_block_type() {
    let input = "invalid_block MyComponent:";
    let result = parse_block(input);
    assert!(result.is_err());
    let error = convert_error(input, result.unwrap_err());
    assert!(matches!(error, ParserError::Syntax { .. }));
}

// ... other error handling tests ... 