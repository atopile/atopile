from pydantic import BaseModel

class Position(BaseModel):
    """The position of an element."""
    x: float
    y: float

class Pose(BaseModel):
    """The position, orientation, flipping etc... of an element."""
    position: Position = {'x': 0.0, 'y': 0.0} # {x: 0.0, y: 0.0}
    rotation: int = 0 # degrees, but should only be 0, 90, 180, 270
    mirror_x: bool = False # defined before rotation is applied.
    mirror_y: bool = False # defined before rotation is applied.

