from ato_parser import parse_atopile

# Parse some Atopile code
code = """
component MyComponent:
    "This is a docstring"
    pin signal1
    signal sig2
    x = 42
    voltage += 5V
"""

# Parse into AST
ast = parse_atopile(code)

# Find all statements of a specific type
components = ast.find_all("Block")
signals = ast.find_all("SignalDef")
pins = ast.find_all("PinDef")

# Print what we found
print("Found components:", len(components))
print("Found signals:", len(signals))
print("Found pins:", len(pins))

# Convert to dictionary for easy navigation
ast_dict = ast.to_dict()

# Navigate the structure
print("\nComponent structure:")
for stmt in ast_dict["statements"]:
    if stmt["type"] == "Block":
        print(f"Found {stmt['block_type']} named {stmt['name']}")
        for body_stmt in stmt["body"]:
            print(f"  - {body_stmt['type']}") 