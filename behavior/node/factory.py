from .base import BehaviorNode
from .logic import DisjunctionNode
from .elementary import StateNode

from ..data import AgentVariable, Speed, Direction


class Factory:
    """
    Factory containing convenience factory methods for behavioral constructs.
    """

    @staticmethod
    def MovingState(variables: list[AgentVariable], speeds: Speed | list[Speed], direction: Direction | None = None) \
            -> BehaviorNode:
        """
        :param variables: Agent variables.
        :param speeds: Allowed speed feature values.
        :param direction: Direction.
        :return: BehaviorNode Disjunction of all values or sole state node if only 1 value.
        """
        if isinstance(speeds, list):

            if len(speeds) > 1:
                return DisjunctionNode([
                    StateNode(variables, speed=speed, direction=direction) for speed in speeds
                ])

            speeds = speeds[0]
        return StateNode(variables, speed=speeds, direction=direction)
