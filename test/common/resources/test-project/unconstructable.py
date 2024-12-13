from faebryk.core.module import Module


class App(Module):
    def __preinit__(self):
        raise ValueError("unconstructable")
