class Nested:
    x: int
    y: str

class Top:
    a: int
    b: int
    c: Nested

    def __init__(self, a: int, b: int, c: Nested) -> None: ...
    def __repr__(self) -> str: ...
    def sum(self) -> int: ...

def add(*, a: int, b: int) -> int: ...
