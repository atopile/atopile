use crate::*;

#[test]
fn test_physical_quantity_basic() {
    let cases = vec![
        ("42V", (42.0, Some("V"))),
        ("3.14MHz", (3.14, Some("MHz"))),
        ("-5.0ohm", (-5.0, Some("ohm"))),
        ("+1.23", (1.23, None)),
        ("100", (100.0, None)),
    ];

    for (input, (expected_value, expected_unit)) in cases {
        let result = parse_physical_quantity(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);

        let (_, quantity) = result.unwrap();
        assert_eq!(quantity.value, expected_value);
        assert_eq!(quantity.unit.as_deref(), expected_unit);
    }
}

#[test]
fn test_bilateral_quantity() {
    let cases = vec![
        ("10V +/- 5%", (10.0, "V", true, 5.0)),
        ("3.3V +/- 0.1V", (3.3, "V", false, 0.1)),
        ("100ohm ± 10%", (100.0, "ohm", true, 10.0)),
    ];

    for (input, (value, unit, is_percent, tolerance_value)) in cases {
        let result = parse_bilateral_quantity(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);

        let (_, qty) = result.unwrap();
        assert_eq!(qty.value, value);
        assert_eq!(qty.unit.as_deref(), Some(unit));
        
        match *qty.tolerance {
            Tolerance::Percentage(t) if is_percent => {
                assert_eq!(t, tolerance_value);
            }
            Tolerance::Absolute(ref t) if !is_percent => {
                assert_eq!(t.value, tolerance_value);
                assert_eq!(t.unit.as_deref(), Some(unit));
            }
            _ => panic!("Unexpected tolerance type"),
        }
    }
}

#[test]
fn test_bound_quantity() {
    let cases = vec![
        ("1V to 5V", (1.0, 5.0, Some("V"))),
        ("-10dB to +10dB", (-10.0, 10.0, Some("dB"))),
        ("0 to 100", (0.0, 100.0, None)),
    ];

    for (input, (min, max, unit)) in cases {
        let result = parse_bound_quantity(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);

        if let Ok((_, Expression::BinaryOp(min_expr, op, max_expr))) = result {
            assert!(matches!(op, Operator::Within));
            if let (Expression::Physical(min_qty), Expression::Physical(max_qty)) = 
                (*min_expr, *max_expr) {
                assert_eq!(min_qty.value, min);
                assert_eq!(max_qty.value, max);
                assert_eq!(min_qty.unit.as_deref(), unit);
                assert_eq!(max_qty.unit.as_deref(), unit);
            } else {
                panic!("Expected physical quantities");
            }
        } else {
            panic!("Expected binary operation");
        }
    }
}

#[test]
fn test_physical_arithmetic() {
    let cases = vec![
        "10V + 5V",
        "3.3V * 2",
        "(100ohm + 200ohm) * 0.5",
        "1kHz to 10kHz",
        "10V +/- 5% + 2V",
    ];

    for input in cases {
        let result = parse_arithmetic(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);
    }
}

#[test]
fn test_physical_quantity_errors() {
    let cases = vec![
        "V",       // Missing value
        "10V+",    // Incomplete expression
        "5 +/- %", // Missing tolerance value
        "1V to",   // Incomplete bound
        "10V +/-", // Missing tolerance
    ];

    for input in cases {
        let result = parse_arithmetic(input);
        assert!(result.is_err(), "Expected error for input: {}", input);
    }
}

#[test]
fn test_physical_quantity_with_spaces() {
    let cases = vec!["10 V", "3.3 MHz", "100 ohm +/- 5 %", "1 V to 5 V"];

    for input in cases {
        let result = parse_arithmetic(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);
    }
}