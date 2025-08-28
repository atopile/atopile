#!/usr/bin/env python3
"""Test what's actually happening with dielectric lookup in the real stackup."""


# Simulate the actual stackup parsing
class MockLayer:
    def __init__(self, material, thickness, epsilon_r=None):
        self.material_val = material
        self.thickness_val = thickness
        self.epsilon_r_val = epsilon_r

    class material:
        def __init__(self, val):
            self.val = val

        def get_literal(self):
            return self.val

    class thickness:
        def __init__(self, val):
            self.val = val

        def get_literal(self):
            return self.val

    class epsilon_r:
        def __init__(self, val):
            self.val = val

        def get_literal(self):
            return self.val

    def __init__(self, material, thickness, epsilon_r=None):
        self.material = self.material(material)
        self.thickness = self.thickness(thickness)
        if epsilon_r is not None:
            self.epsilon_r = self.epsilon_r(epsilon_r)


# Create mock stackup matching JLC4Layer
layers = [
    MockLayer("Solder Mask", 30.48, 4.2),  # 0
    MockLayer("Copper", 35),  # 1 - F.Cu
    MockLayer("FR4", 210, 4.2),  # 2
    MockLayer("Copper", 15.2),  # 3 - In1.Cu
    MockLayer("FR4", 1065, 4.2),  # 4
    MockLayer("Copper", 15.2),  # 5 - In2.Cu
    MockLayer("FR4", 210, 4.2),  # 6
    MockLayer("Copper", 35),  # 7 - B.Cu
    MockLayer("Solder Mask", 30.48, 4.2),  # 8
]

copper_layers = [(1, 0.035), (3, 0.0152), (5, 0.0152), (7, 0.035)]
copper_indices = [idx for idx, _ in copper_layers]
first_copper = copper_indices[0]  # 1
last_copper = copper_indices[-1]  # 7


def _to_mm_any(val):
    # Assume micrometers
    if val is None:
        return None
    return float(val) / 1000.0


def test_nearest_dielectric_props(stack_index: int) -> tuple[float, float]:
    default_er = 4.2

    # First check if current layer is copper
    try:
        current_mat = layers[stack_index].material.get_literal()
    except Exception as e:
        print(f"  ERROR getting material: {e}")
        return (0.2, default_er)

    if not (isinstance(current_mat, str) and current_mat.lower() == "copper"):
        print(f"  Not copper: {current_mat}")
        return (0.2, default_er)

    # Find distance to nearest copper reference plane
    best_h = None
    best_er = None

    # Determine if this is an outer layer
    is_outer = stack_index == first_copper or stack_index == last_copper
    print(f"  Is outer: {is_outer} (first={first_copper}, last={last_copper})")

    if is_outer:
        # Outer copper layers - use adjacent dielectric only
        for dir_ in (-1, 1):
            j = stack_index + dir_
            print(f"    Checking adjacent index {j}")
            if 0 <= j < len(layers):
                try:
                    mat = layers[j].material.get_literal()
                    print(f"      Material: {mat}")
                except Exception as e:
                    print(f"      ERROR: {e}")
                    mat = None
                if isinstance(mat, str) and mat.lower() in {
                    "fr4",
                    "dielectric",
                    "prepreg",
                }:
                    try:
                        thickness_val = layers[j].thickness.get_literal()
                        h = _to_mm_any(thickness_val)
                        print(f"      Found dielectric: {h}mm thick")
                        if h is not None:
                            best_h = h
                            try:
                                best_er = float(layers[j].epsilon_r.get_literal())
                            except Exception:
                                best_er = default_er
                            break
                    except Exception as e:
                        print(f"      ERROR getting thickness: {e}")
                        pass
    else:
        print(f"  Inner layer - finding nearest copper")
        # Inner copper layers - find distance to nearest copper
        for dir_ in (-1, 1):
            total_h = 0.0
            dielectric_count = 0
            er_sum = 0.0

            j = stack_index + dir_
            print(f"    Direction {dir_}:")
            while 0 <= j < len(layers):
                try:
                    mat = layers[j].material.get_literal()
                except Exception:
                    mat = None

                if isinstance(mat, str):
                    mat_lower = mat.lower()
                    print(f"      Index {j}: {mat}")

                    # If we hit another copper layer, we've found our reference
                    if mat_lower == "copper":
                        if dielectric_count > 0:
                            # Average epsilon_r of dielectrics between coppers
                            avg_er = (
                                er_sum / dielectric_count
                                if dielectric_count > 0
                                else default_er
                            )
                            print(f"      Found copper! Distance: {total_h}mm")
                            if best_h is None or total_h < best_h:
                                best_h = total_h
                                best_er = avg_er
                        break

                    # Accumulate dielectric thickness
                    elif mat_lower in {"fr4", "dielectric", "prepreg", "core"}:
                        try:
                            thickness_val = layers[j].thickness.get_literal()
                            h = _to_mm_any(thickness_val)
                            if h is not None:
                                total_h += h
                                dielectric_count += 1
                                try:
                                    er = float(layers[j].epsilon_r.get_literal())
                                except Exception:
                                    er = default_er
                                er_sum += er
                                print(
                                    f"        Accumulated {h}mm, total now {total_h}mm"
                                )
                        except Exception:
                            pass
                j += dir_

    print(f"  Result: h={best_h}mm, er={best_er}")
    return (
        best_h if best_h is not None else 0.2,
        best_er if best_er is not None else default_er,
    )


# Test each copper layer
print("Testing dielectric lookup for each copper layer:")
print("=" * 60)

for i, (stack_idx, t_mm) in enumerate(copper_layers):
    layer_name = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"][i]
    print(f"\n{layer_name} (index {stack_idx}):")
    h_mm, er = test_nearest_dielectric_props(stack_idx)
    print(f"Final: h={h_mm}mm, er={er}")
