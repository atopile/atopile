use crate::*;

#[test]
fn test_parse_assignment() {
    let input = "my_var: MyType = new Component";
    let result = parse_assignment(input);
    assert!(result.is_ok());

    if let Ok((_, Statement::Assignment(assign))) = result {
        assert_eq!(assign.target, "my_var");
        assert_eq!(assign.type_info, Some("MyType".to_string()));
        assert!(matches!(assign.value, Expression::New(_)));
    } else {
        panic!("Expected Assignment statement");
    }
}

#[test]
fn test_parse_connection() {
    let input = "pin1 ~ signal mysignal";
    let result = parse_connection(input);
    assert!(result.is_ok());

    if let Ok((_, Statement::Connection(conn))) = result {
        assert!(matches!(conn.left, Connectable::Name(_)));
        assert!(matches!(conn.right, Connectable::Signal(_)));
    } else {
        panic!("Expected Connection statement");
    }
}

#[test]
fn test_parse_expression() {
    assert!(matches!(
        parse_expression("42").unwrap().1,
        Expression::Number(42.0)
    ));
    assert!(matches!(
        parse_expression("\"hello\"").unwrap().1,
        Expression::String(_)
    ));
    assert!(matches!(
        parse_expression("True").unwrap().1,
        Expression::Boolean(true)
    ));
    assert!(matches!(
        parse_expression("new MyComponent").unwrap().1,
        Expression::New(_)
    ));
}

#[test]
fn test_parse_docstring() {
    let cases = vec![
        "\"Simple docstring\"",
        "'''Multi-line\ndocstring'''",
        "\"\"\"Triple-quoted\ndocstring\nwith multiple lines\"\"\"",
    ];

    for input in cases {
        let result = parse_docstring(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);

        if let Ok((_, Statement::DocString(content))) = result {
            assert!(!content.is_empty());
            assert!(!content.contains('\"')); // Quotes should be stripped
        } else {
            panic!("Expected docstring");
        }
    }
}

#[test]
fn test_parse_comment() {
    let cases = vec![
        "# Simple comment",
        "#   Indented comment  ",
        "# Comment with special chars: !@#$%^&*()",
    ];

    for input in cases {
        let result = parse_comment(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);

        if let Ok((_, Statement::Comment(content))) = result {
            assert!(!content.is_empty());
            assert!(!content.starts_with('#')); // Hash should be stripped
            assert_eq!(content, content.trim()); // Should be trimmed
        } else {
            panic!("Expected comment");
        }
    }
}

#[test]
fn test_parse_line_with_comment() {
    let cases = vec![
        ("x = 42  # Assignment comment", 2),
        ("# Just a comment", 1),
        ("signal mysig  # Signal definition", 2),
        ("pass  # Do nothing", 2),
    ];

    for (input, expected_count) in cases {
        let result = parse_line(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);

        let (_, statements) = result.unwrap();
        assert_eq!(statements.len(), expected_count);

        if expected_count > 1 {
            assert!(matches!(statements.last(), Some(Statement::Comment(_))));
        }
    }
}