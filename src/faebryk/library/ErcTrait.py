from abc import ABC

from faebryk.core.module import Module


class ERCTrait(Module.TraitT.decless(), ABC):
    def check(self): ...
