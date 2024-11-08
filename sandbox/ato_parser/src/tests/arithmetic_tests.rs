use crate::*;

#[test]
fn test_arithmetic_basic() {
    let cases = vec![
        ("1 + 2", "Add"),
        ("3 - 4", "Subtract"),
        ("5 * 6", "Multiply"),
        ("8 / 2", "Divide"),
        ("2 ** 3", "Power"),
        ("1 | 2", "BitwiseOr"),
        ("3 & 4", "BitwiseAnd"),
    ];

    for (input, expected_op) in cases {
        let result = parse_arithmetic(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);
    }
}

#[test]
fn test_unary_operators() {
    let cases = vec![
        ("+42", Operator::Plus),
        ("-42", Operator::Minus),
        ("+-42", Operator::Plus),
        ("-+42", Operator::Minus),
    ];

    for (input, expected_op) in cases {
        let result = parse_arithmetic(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);

        if let Ok((_, Expression::UnaryOp(op, _))) = result {
            assert_eq!(op, expected_op);
        } else {
            panic!("Expected unary operation for input: {}", input);
        }
    }
}

#[test]
fn test_arithmetic_grouping() {
    let input = "(1 + 2) * 3";
    let result = parse_arithmetic(input).unwrap().1;

    match result {
        Expression::BinaryOp(left, Operator::Multiply, right) => {
            assert!(matches!(*right, Expression::Number(3.0)));
            match *left {
                Expression::Group(expr) => match *expr {
                    Expression::BinaryOp(l, Operator::Add, r) => {
                        assert!(matches!(*l, Expression::Number(1.0)));
                        assert!(matches!(*r, Expression::Number(2.0)));
                    }
                    _ => panic!("Expected addition inside group"),
                },
                _ => panic!("Expected group as left operand"),
            }
        }
        _ => panic!("Expected multiplication at top level"),
    }
}

#[test]
fn test_complex_arithmetic() {
    let cases = vec![
        "1 + 2 * 3 ** 2",
        "(1 + 2) * (3 + 4)",
        "1 | 2 & 3",
        "1 + 2 - 3 * 4 / 5 ** 6",
    ];

    for input in cases {
        let result = parse_arithmetic(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);
        assert_eq!(result.unwrap().0.trim(), "");
    }
}

#[test]
fn test_arithmetic_errors() {
    let cases = vec![
        "1 +",        // Incomplete expression
        "* 2",        // Missing left operand
        "1 + (2 * 3", // Unclosed parenthesis
        "1 ** ** 2",  // Double operator
    ];

    for input in cases {
        let result = parse_arithmetic(input);
        assert!(result.is_err(), "Expected error for input: {}", input);
    }
}

#[test]
fn test_unary_with_binary() {
    let cases = vec![
        "-1 + 2", "+1 - 2", "1 + -2", "-1 * -2", "-(1 + 2)", "+1 ** 2",
    ];

    for input in cases {
        let result = parse_arithmetic(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);
    }
}

#[test]
fn test_unary_precedence() {
    let input = "-1 + 2";
    let result = parse_arithmetic(input).unwrap().1;

    match result {
        Expression::BinaryOp(left, Operator::Add, right) => {
            assert!(matches!(
                *left,
                Expression::UnaryOp(Operator::Minus, _)
            ));
            assert!(matches!(*right, Expression::Number(2.0)));
        }
        _ => panic!("Expected binary operation at top level"),
    }
}

#[test]
fn test_nested_unary() {
    let input = "--42";
    let result = parse_arithmetic(input).unwrap().1;

    match result {
        Expression::UnaryOp(Operator::Minus, inner) => match *inner {
            Expression::UnaryOp(Operator::Minus, num) => {
                assert!(matches!(*num, Expression::Number(42.0)));
            }
            _ => panic!("Expected nested unary minus"),
        },
        _ => panic!("Expected unary operation at top level"),
    }
}

#[test]
fn test_unary_errors() {
    let cases = vec![
        "+",     // Incomplete unary expression
        "- ",    // Missing operand
        "++",    // Double plus without operand
        "+ * 2", // Missing operand before binary operator
    ];

    for input in cases {
        let result = parse_arithmetic(input);
        assert!(result.is_err(), "Expected error for input: {}", input);
    }
}