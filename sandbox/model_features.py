"""
To simplify the model, I'm stripping out these features for now, because they're not fully formed ideas.
"""
from atopile.model.model import define, field, List, EtherealPin

@define
class ModelNode:
    """
    The base class for all nodes in the model
    """
    source: str = field(default=None)
    locn_start: int = field(default=None)
    locn_end: int = field(default=None)

@define
class Function(ModelNode):
    """
    Represents a function that controls pin behaviour

    NOTE: this is ultimately mean to represent a mathematical function and should be a richer type.
    It's just currently a string so we can preserve the data somewhere.
    """
    eqn: str

@define
class Limit(ModelNode):
    """
    Represents a limit (a mathematical equality/inequality) a component or feature is subject to

    NOTE: this is ultimately mean to represent a mathematical function and should be a richer type.
    It's just currently a string so we can preserve the data somewhere.
    """
    eqn: str

@define
class State(ModelNode):
    """
    Represents a state of a component or feature
    """
    name: str
    functions: List[Function] = field(factory=list)
    limits: List[Limit] = field(factory=list)
    type: List['EtherealPin'] = field(default=None)
