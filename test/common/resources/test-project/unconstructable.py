import faebryk.core.node as fabll


class App(fabll.Node):
    def __preinit__(self):
        raise ValueError("unconstructable")
