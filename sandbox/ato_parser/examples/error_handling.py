from ato_parser import parse_atopile

def try_parse(code):
    try:
        ast = parse_atopile(code)
        print("Successfully parsed!")
        return ast
    except ValueError as e:
        print(f"Parse error: {e}")
        return None

# Example 1: Valid code
print("Testing valid code:")
valid_code = """
component MyComponent:
    pin signal1
    signal sig2
"""
try_parse(valid_code)

# Example 2: Invalid indentation
print("\nTesting invalid indentation:")
invalid_indent = """
component MyComponent:
pin signal1  # Wrong indentation
    signal sig2
"""
try_parse(invalid_indent)

# Example 3: Invalid syntax
print("\nTesting invalid syntax:")
invalid_syntax = """
component MyComponent:
    pin @invalid
    signal ->
"""
try_parse(invalid_syntax) 