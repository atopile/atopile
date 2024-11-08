use crate::*;

#[test]
fn test_parse_block() {
    let input = r#"component MyComponent from BaseComponent:
        pin signal1
        signal sig2
        pass"#;

    let result = parse_block(input);
    assert!(result.is_ok());
    let (remaining, stmt) = result.unwrap();
    assert_eq!(remaining.trim(), "");

    if let Statement::Block(block) = stmt {
        assert!(matches!(block.block_type, BlockType::Component));
        assert_eq!(block.name, "MyComponent");
        assert_eq!(block.parent, Some("BaseComponent".to_string()));
        assert_eq!(block.body.len(), 3);
    } else {
        panic!("Expected Block statement");
    }
}

#[test]
fn test_parse_block_with_docstring() {
    let input = r#"component MyComponent:
        """
        This is a documentation string
        for MyComponent.
        """
        pin signal1  # First signal
        # Comment line
        signal sig2
        pass"#;

    let result = parse_block(input);
    assert!(result.is_ok());

    if let Ok((_, Statement::Block(block))) = result {
        assert!(block.body.len() >= 5); // Docstring + 2 signals + comment + pass
        assert!(matches!(block.body[0], Statement::DocString(_)));

        // Find and verify the comment
        let has_comment = block
            .body
            .iter()
            .any(|stmt| matches!(stmt, Statement::Comment(_)));
        assert!(has_comment);
    } else {
        panic!("Expected block statement");
    }
}

#[test]
fn test_empty_lines_and_comments() {
    let input = r#"
        # Initial comment
        component MyComponent:
            # Component comment

            """Component docstring"""

            pin signal1

            # Signal comment
            signal sig2
            pass
    "#;

    let result = parse_block(input);
    assert!(result.is_ok());

    if let Ok((_, Statement::Block(block))) = result {
        // Verify we have the expected number of statements
        let comment_count = block
            .body
            .iter()
            .filter(|stmt| matches!(stmt, Statement::Comment(_)))
            .count();
        assert!(comment_count >= 2);

        let docstring_count = block
            .body
            .iter()
            .filter(|stmt| matches!(stmt, Statement::DocString(_)))
            .count();
        assert_eq!(docstring_count, 1);
    }
}