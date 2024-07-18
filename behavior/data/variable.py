from abc import ABC


class BehaviorVariable(ABC):
    """
    Placeholder variable in behavioral templates to create mapping to actual data during processing.
    """

    name: str = "UnnamedBV"

    def __repr__(self):
        return "BehaviorVariable()"


class AgentVariable(BehaviorVariable):
    """
    Placeholder actor in behavioral templates to create mapping to actual data during processing.
    """

    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"AgentVariable(\"{self.name}\")"

    def __str__(self):
        return self.name
