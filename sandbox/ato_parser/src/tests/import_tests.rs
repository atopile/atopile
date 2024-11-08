use crate::*;

#[test]
fn test_parse_import() {
    let input = "from mymodule import item1, item2";
    let result = parse_import(input);
    assert!(result.is_ok());
    let (remaining, stmt) = result.unwrap();
    assert_eq!(remaining.trim(), "");
    assert!(matches!(stmt, Statement::Import(_)));
    if let Statement::Import(ImportStmt::FromImport { module, items }) = stmt {
        assert_eq!(module, "mymodule");
        assert_eq!(items, vec!["item1", "item2"]);
    } else {
        panic!("Expected FromImport variant");
    }
}

#[test]
fn test_identifier() {
    assert!(identifier("abc123").is_ok());
    assert!(identifier("_abc123").is_ok());
    assert!(identifier("123abc").is_err());
} 