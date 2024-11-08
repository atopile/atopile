from ato_parser import parse_atopile

# Example with various physical quantities and operations
code = """
component PowerSupply:
    \"\"\"Power supply with voltage and current specifications\"\"\"
    
    # Voltage specifications
    voltage_out = 5V +/- 0.1V
    voltage_range = 4.5V to 5.5V
    
    # Current limits
    max_current = 1A
    ripple = 50mV
    
    # Calculations
    power = voltage_out * max_current
    efficiency = 0.95  # 95%
    
    # Assertions
    assert voltage_out within voltage_range
    assert ripple <= 100mV
"""

ast = parse_atopile(code)
ast_dict = ast.to_dict()

# Function to print physical quantities
def print_physical_quantities(node):
    if node["type"] == "Assignment":
        value = node.get("value", {})
        if value.get("type") == "Physical":
            print(f"Found physical quantity: {value['value']}{value.get('unit', '')}")
        elif value.get("type") == "Bilateral":
            nom = value["nominal"]
            tol = value["tolerance"]
            print(f"Found bilateral: {nom['value']}{nom.get('unit', '')} ± {tol}")
        elif value.get("type") == "Bound":
            min_val = value["min"]
            max_val = value["max"]
            print(f"Found bound: {min_val['value']}{min_val.get('unit', '')} to {max_val['value']}{max_val.get('unit', '')}")

# Process the AST
for stmt in ast_dict["statements"]:
    if stmt["type"] == "Block":
        for body_stmt in stmt["body"]:
            print_physical_quantities(body_stmt) 