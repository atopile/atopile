import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F


class App(fabll.Node):
    r1 = F.Resistor.MakeChild()
    # r2 = F.Resistor.MakeChild()

    # @classmethod
    # def MakeChild(cls):
    #     out = fabll._ChildField(cls)
    #     out.add_dependant(
    #         fabll.MakeEdge(
    #             lhs=[cls.r1.get().unnamed[0]],
    #             rhs=[cls.r2.get().unnamed[0]],
    #             edge=fbrk.EdgeInterfaceConnection.build()
    #         )
    #     )
    #     return out
