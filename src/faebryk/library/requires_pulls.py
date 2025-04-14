import faebryk.library._F as F


class requires_pulls(F.ErcTrait):
    def __init__(self, *signals: F.ElectricSignal):
        super().__init__()

        # TODO: direction, magnitude
        self.signals = signals

    def check(self):
        for signal in self.signals:
            if not (is_pulled := signal.try_get_trait(F.is_pulled)):
                raise ValueError(
                    f"Signal `{signal}` does not implement `is_pulled`"
                )  # TODO: erc error

            if not is_pulled.check():
                raise ValueError(f"Signal `{signal}` is not pulled")  # TODO: erc error
