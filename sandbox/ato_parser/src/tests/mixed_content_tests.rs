use crate::*;

#[test]
fn test_mixed_content() {
    let input = r#"
        # File header comment
        """
        Module documentation
        Multiple lines
        """
        component MyComponent:  # Inline comment
            "Component doc"  # Docstring comment
            pin signal1  # Pin comment
            # Standalone comment
            signal sig2
    "#;

    let result = parse_lines(input);
    assert!(result.is_ok());

    let (_, statements) = result.unwrap();

    // Verify we have all types of content
    let has_comment = statements
        .iter()
        .any(|s| matches!(s, Statement::Comment(_)));
    let has_docstring = statements
        .iter()
        .any(|s| matches!(s, Statement::DocString(_)));
    let has_block = statements.iter().any(|s| matches!(s, Statement::Block(_)));

    assert!(has_comment);
    assert!(has_docstring);
    assert!(has_block);
}

#[test]
fn test_mixed_imports() {
    let input = r#"
        import core
        from utils import pin, signal
        from 'components/led.ato' import LED, RGB_LED
        from math import sin, cos, tan
    "#;

    let result = parse_lines(input);
    assert!(result.is_ok());

    let (_, statements) = result.unwrap();
    let import_count = statements
        .iter()
        .filter(|stmt| matches!(stmt, Statement::Import(_)))
        .count();
    assert_eq!(import_count, 4);
}

#[test]
fn test_mixed_assignments() {
    let input = r#"
        component MyComponent:
            x += 42
            voltage -= 5V
            flags |= 0x0F
            mask &= 0xFF
            value = x + voltage
    "#;

    let result = parse_block(input);
    assert!(result.is_ok());

    if let Ok((_, Statement::Block(block))) = result {
        let cum_assign_count = block
            .body
            .iter()
            .filter(|stmt| matches!(stmt, Statement::CumulativeAssign(_)))
            .count();
        let set_assign_count = block
            .body
            .iter()
            .filter(|stmt| matches!(stmt, Statement::SetAssign(_)))
            .count();

        assert_eq!(cum_assign_count, 2);
        assert_eq!(set_assign_count, 2);
    }
}

#[test]
fn test_mixed_statements() {
    let input = r#"
        component MyComponent:
            signal clock
            pin 1
            pin "A0"
            assert voltage within 5V
            data -> clock
            pass
    "#;

    let result = parse_block(input);
    assert!(result.is_ok());

    if let Ok((_, Statement::Block(block))) = result {
        assert!(block
            .body
            .iter()
            .any(|stmt| matches!(stmt, Statement::SignalDef(_))));
        assert!(block
            .body
            .iter()
            .any(|stmt| matches!(stmt, Statement::PinDef(_))));
        assert!(block
            .body
            .iter()
            .any(|stmt| matches!(stmt, Statement::Assert(_))));
        assert!(block
            .body
            .iter()
            .any(|stmt| matches!(stmt, Statement::Retype(_))));
    }
}

#[test]
fn test_complex_line_continuation() {
    let input = r#"component MyComponent:
        """This is a \
        multi-line \
        docstring"""

        from module \
            import item1, \
                    item2

        value = new \
            Component( \
                param1, \
                param2 \
            )

        signal1 ~ \
            signal2"#;

    let result = parse_block(input);
    assert!(result.is_ok());
} 