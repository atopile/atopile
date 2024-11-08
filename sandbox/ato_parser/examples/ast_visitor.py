from ato_parser import parse_atopile

def visit_ast(node):
    """Example visitor pattern for AST traversal"""
    node_type = node["type"]
    
    if node_type == "Block":
        print(f"Visiting block: {node['name']}")
        for stmt in node["body"]:
            visit_ast(stmt)
    elif node_type == "SignalDef":
        print(f"Found signal: {node['name']}")
    elif node_type == "PinDef":
        print(f"Found pin definition")
    elif node_type == "Assignment":
        print(f"Found assignment to: {node['target']}")
    elif node_type == "DocString":
        print(f"Found docstring: {node['content'][:30]}...")

# Example code with multiple constructs
code = """
component LED:
    \"\"\"
    A basic LED component with power and ground connections.
    \"\"\"
    pin vcc
    pin gnd
    
    voltage = 3.3V
    current_limit = 20mA
    
    signal power_good
    
    assert voltage <= 5V
"""

# Parse and visit
ast = parse_atopile(code)
visit_ast(ast.to_dict()) 