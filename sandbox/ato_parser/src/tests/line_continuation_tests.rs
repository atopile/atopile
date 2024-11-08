use crate::*;

#[test]
fn test_line_continuation_basic() {
    let cases = vec![
        "line1 \\\nline2",
        "line1 \\\n  line2",
        "line1 \\\n\n  line2",
        "line1 \\\r\n  line2",
    ];

    for input in cases {
        let result = handle_line_continuation(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);
        let (_, content) = result.unwrap();
        assert!(!content.contains('\\'));
        assert!(!content.contains('\n'));
    }
}

#[test]
fn test_line_continuation_in_statements() {
    let cases = vec![
        // Import statement with continuation
        ("from mymodule \\\nimport item1, \\\nitem2", 1),
        // Assignment with continuation
        ("x = new \\\nMyComponent", 1),
        // Long expression with multiple continuations
        ("result = 1 + \\\n2 * \\\n3", 1),
        // Import with comment and continuation
        ("from module \\\nimport item  # Comment", 2),
    ];

    for (input, expected_stmt_count) in cases {
        let result = parse_line(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);
        let (_, statements) = result.unwrap();
        assert_eq!(statements.len(), expected_stmt_count);
    }
}

#[test]
fn test_line_continuation_in_block() {
    let input = r#"component MyComponent:
        pin \
            signal1
        signal \
            sig2 \
            # Comment
        value = 1 + \
            2 + \
            3
        pass"#;

    let result = parse_block(input);
    assert!(result.is_ok());

    if let Ok((_, Statement::Block(block))) = result {
        assert!(block.body.len() >= 4); // pin, signal, assignment, pass
    } else {
        panic!("Expected block statement");
    }
}

#[test]
fn test_line_continuation_errors() {
    let cases = vec![
        "\\",                 // Lone backslash
        "line \\ not_at_eol", // Backslash not at end of line
        "line \\",            // Backslash at EOF
        "line \\\n\\",        // Multiple backslashes without content
    ];

    for input in cases {
        let result = handle_line_continuation(input);
        assert!(result.is_err(), "Expected error for input: {}", input);
    }
}

#[test]
fn test_line_continuation_whitespace() {
    let cases = vec![
        "line1 \\\n    line2",
        "line1 \\\n\t\tline2",
        "line1 \\\n\n    line2",
        "line1 \\\n    \\\n    line2",
    ];

    for input in cases {
        let result = handle_line_continuation(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);
        let (_, content) = result.unwrap();
        assert!(!content.contains('\\'));
        assert!(!content.contains('\n'));
    }
} 