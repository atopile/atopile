#!/usr/bin/env python3
"""Debug the stackup layer detection logic."""

# Simulate the JLC 4-layer stackup
layers = [
    ("Solder Mask", 0.03048),  # 0
    ("Copper", 0.035),  # 1 - F.Cu
    ("FR4", 0.21),  # 2
    ("Copper", 0.0152),  # 3 - In1.Cu
    ("FR4", 1.065),  # 4
    ("Copper", 0.0152),  # 5 - In2.Cu
    ("FR4", 0.21),  # 6
    ("Copper", 0.035),  # 7 - B.Cu
    ("Solder Mask", 0.03048),  # 8
]

print("JLC 4-Layer Stackup:")
print("-" * 50)
for i, (material, thickness) in enumerate(layers):
    print(f"Index {i}: {material:12} {thickness * 1000:7.2f}μm")

print("\nCopper layer indices:")
copper_indices = []
for i, (material, _) in enumerate(layers):
    if material == "Copper":
        copper_indices.append(i)
        print(f"  Index {i}: Copper")

print(f"\nlen(layers) = {len(layers)}")
print(f"len(layers) - 2 = {len(layers) - 2}")

print("\nOuter layer detection:")
for idx in copper_indices:
    is_outer_check1 = idx == 1 or idx == len(layers) - 2
    is_first_copper = idx == copper_indices[0]
    is_last_copper = idx == copper_indices[-1]
    print(f"  Index {idx}:")
    print(f"    idx == 1 or idx == len(layers)-2: {is_outer_check1}")
    print(f"    Is first copper: {is_first_copper}")
    print(f"    Is last copper: {is_last_copper}")
    print(f"    Should be outer: {is_first_copper or is_last_copper}")


# Test what happens with the current logic
def test_dielectric_lookup(stack_index, layers_sim):
    """Simulate what _nearest_dielectric_props does."""
    print(f"\nDielectric lookup for index {stack_index}:")

    # Check if it's considered an outer layer
    if stack_index == 1 or stack_index == len(layers_sim) - 2:
        print(f"  Detected as OUTER layer")
        # Look for adjacent dielectric
        for direction in [-1, 1]:
            j = stack_index + direction
            if 0 <= j < len(layers_sim):
                mat, thickness = layers_sim[j]
                if mat == "FR4":
                    print(f"    Found adjacent FR4 at index {j}: {thickness}mm")
                    return thickness
    else:
        print(f"  Detected as INNER layer")
        # Look for distance to nearest copper
        best_h = None
        for direction in [-1, 1]:
            total_h = 0.0
            j = stack_index + direction
            print(f"    Searching direction {direction}:")
            while 0 <= j < len(layers_sim):
                mat, thickness = layers_sim[j]
                print(f"      Index {j}: {mat} {thickness}mm")
                if mat == "Copper":
                    print(f"      Found copper! Total distance: {total_h}mm")
                    if best_h is None or total_h < best_h:
                        best_h = total_h
                    break
                elif mat == "FR4":
                    total_h += thickness
                j += direction
        return best_h
    return 0.2  # fallback


# Test each copper layer
for idx in copper_indices:
    h = test_dielectric_lookup(idx, layers)
