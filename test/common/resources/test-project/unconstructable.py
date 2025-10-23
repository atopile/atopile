import faebryk.core.node as fabll


class App(fabll.Module):
    def __preinit__(self):
        raise ValueError("unconstructable")
