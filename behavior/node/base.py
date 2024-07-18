from __future__ import annotations

from abc import ABC
from datetime import timedelta

from ..data import BehaviorVariable, RelativeTimeFrame
from ..data.agent import BlockWindow

from ..time_graph import TimeGraphLayer


class BehaviorNode(ABC):
    """
    Base class for all behavioral nodes.
    """

    children: list[BehaviorNode]
    name: str | None

    def __init__(self, name: str | None):
        self.children = []
        self.name = name

    def compute_graph_layer(self, variables: list[BehaviorVariable], windows: list[BlockWindow]) -> TimeGraphLayer:
        """
        Compute graph layer - a representation of this node's confidence matrix.
        :param variables: Behavior variables of the whole template.
        :param windows: Sliding windows for which to compute confidences.
        :return: A computed time graph layer.
        """
        raise NotImplementedError("Abstract method")

    def get_sequence_info(self, default_min: timedelta | None = None) -> list[tuple[set[BehaviorVariable], timedelta]]:
        """
        Compute actor-temporal constraints for this node.
        :param default_min: The default minimal time requirement
        to be used when no time requirements are explicitly set.
        :return: Actor-temporal constraints in the form of a list, which specifies in chronological sequence, which
        actors need to be present for what minimal amount of time.
        """
        raise NotImplementedError("Abstract method")

    def get_variables(self) -> list[set[BehaviorVariable]]:
        """
        Compute actor constraints for this node.
        """
        raise NotImplementedError("Abstract method")

    def get_time_requirement(self, default_min: timedelta | None = None, default_max: timedelta | None = None) \
            -> RelativeTimeFrame:
        """
        Compute time requirements for this node.
        :param default_min: Default minimal time requirement to be set if no explicit minimum is found.
        :param default_max: Default maximal time requirement to be set if no implicit maximum is found.
        :return: Relative time frame containing computed time requirements.
        """
        raise NotImplementedError("Abstract method")

    def is_symmetrical(self, agent_variables: set[BehaviorVariable]) -> bool:
        """
        Check whether this node is symmetrical (i.e., if the order of agent variables matters).
        :param agent_variables: List of agent variables of the entire template.
        :return: True if order does not matter, False otherwise.
        """
        raise NotImplementedError("Abstract method")

    def is_subset(self, other_node: BehaviorNode) -> bool:
        """
        Check whether this node is a subset of another in terms of information.
        :return: True if this node is a subset, i.e., holds no more information than the other node, False otherwise.
        """
        return False

    def __str__(self):
        return self.name if self.name is not None else repr(self)
