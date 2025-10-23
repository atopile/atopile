import faebryk.core.node as fabll


class App(Module):
    def __preinit__(self):
        raise ValueError("unconstructable")
