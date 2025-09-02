#!/usr/bin/env python3

# Add the built module to path
# zig_dir = Path(__file__).parent.parent.parent
# sys.path.insert(0, str(zig_dir / "zig-out" / "lib"))
from faebryk.core.zig import Circle, Setup, Stroke, Xy

# Import directly from pyzig
# from pyzig import Xy  # noqa: E402

# Test creating an Xy instance
xy = Xy(x=1.0, y=2.0)
print(f"Created Xy: {xy}")
print(f"x={xy.x}, y={xy.y}")

# Test modifying fields
xy.x = 3.5
xy.y = 4.5
print(f"Modified: x={xy.x}, y={xy.y}")


c = Circle(
    center=Xy(x=1.0, y=2.0),
    end=Xy(x=3.0, y=4.0),
    layer="F.Cu",
    width=0.1,
    stroke=Stroke(width=0.1, type="solid"),
    fill="red",
    uuid="1234567890",
)

print(c)

setup = Setup()
print(setup)
