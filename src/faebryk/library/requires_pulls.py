import faebryk.library._F as F


class requires_pulls(F.ErcTrait):
    def __init__(self, *signals: F.ElectricSignal):
        super().__init__()

        # TODO: direction, magnitude
        self.signals = signals

    @property
    def fulfilled(self) -> bool:
        for signal in self.signals:
            if not (is_pulled := signal.try_get_trait(F.is_pulled)):
                return False

            if not is_pulled.fulfilled:
                return False

        return True
