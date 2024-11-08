use crate::*;
use nom::{
    Err as NomErr,
};

#[test]
fn test_assignment_operators() {
    let cases = vec![
        ("x = 42", AssignmentOperator::Simple),
        ("x += 42", AssignmentOperator::Add),
        ("x -= 42", AssignmentOperator::Subtract),
        ("x *= 42", AssignmentOperator::Multiply),
        ("x /= 42", AssignmentOperator::Divide),
        ("x **= 2", AssignmentOperator::Power),
        ("x //= 2", AssignmentOperator::IntegerDivide),
        ("x |= 0xFF", AssignmentOperator::BitwiseOr),
        ("x &= 0xFF", AssignmentOperator::BitwiseAnd),
        ("x ^= 0xFF", AssignmentOperator::BitwiseXor),
        ("x <<= 2", AssignmentOperator::LeftShift),
        ("x >>= 2", AssignmentOperator::RightShift),
        ("x @= matrix", AssignmentOperator::At),
    ];

    for (input, expected_op) in cases {
        let result = parse_assignment(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);

        if let Ok((_, Statement::Assignment(stmt))) = result {
            assert_eq!(stmt.operator, expected_op);
        } else {
            panic!("Expected Assignment statement");
        }
    }
}

#[test]
fn test_complex_assignments() {
    let cases = vec![
        "x **= 2 + 3",         // Power with expression
        "y //= (a + b) * 2",   // Integer divide with grouped expression
        "matrix @= transpose", // Matrix operation
        "bits <<= 1 + shift",  // Shift with expression
    ];

    for input in cases {
        let result = parse_assignment(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);
    }
}

#[test]
fn test_assignment_with_type_info() {
    let cases = vec![
        ("x: int **= 2", "int", AssignmentOperator::Power),
        ("y: float //= 2", "float", AssignmentOperator::IntegerDivide),
        ("m: Matrix @= trans", "Matrix", AssignmentOperator::At),
    ];

    for (input, expected_type, expected_op) in cases {
        let result = parse_assignment(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);

        if let Ok((_, Statement::Assignment(stmt))) = result {
            assert_eq!(stmt.type_info.as_deref(), Some(expected_type));
            assert_eq!(stmt.operator, expected_op);
        } else {
            panic!("Expected Assignment statement");
        }
    }
}

#[test]
fn test_assignment_operator_errors() {
    let cases = vec![
        "x =",       // Missing value
        "x **=",     // Missing power value
        "x //= /",   // Invalid integer divide value
        "x @= @",    // Invalid matrix operation
        "x <<= >>",  // Invalid shift value
        "= value",   // Missing target
        "x += y +=", // Multiple assignments
    ];

    for input in cases {
        let result = parse_assignment(input);
        match result {
            Ok(_) => panic!("Expected error for input: {}", input),
            Err(_) => {
                // Test passes if we get any error
                assert!(true, "Got expected error for input: {}", input);
            }
        }
    }
}

// Helper function to verify assignment operator parsing
fn verify_assignment_error(input: &str) -> bool {
    matches!(parse_assignment(input), Err(_))
}

#[test]
fn test_invalid_assignment_combinations() {
    let cases = vec![
        "x += ",             // Missing right-hand side
        "x **= y **= z",     // Chained power assignment
        "x //= y //= z",     // Chained integer divide
        "@= x",              // Invalid target
        "x = y = z",         // Chained simple assignment
        "x += y += z",       // Chained add assignment
        "x -= y -= z",       // Chained subtract assignment
    ];

    for input in cases {
        assert!(
            verify_assignment_error(input),
            "Expected error but got success for input: {}",
            input
        );
    }
}
