from datetime import timedelta

from .base import BehaviorNode

from ..configuration import Configuration
from ..data.agent import BlockWindow
from ..data import BehaviorVariable, RelativeTimeFrame, Confidence, ConfidenceComparer
from ..time_graph import LambdaTimeGraphLayer


class RestrictingNode(BehaviorNode):
    """
    Restricting node base class. Restricting nodes are used as a filter, enforcing conditions on confidence matrices of
    sub-nodes. If condition fails, confidence is penalized (or entirely removed).
    """
    pass


class TimeRestrictingNode(RestrictingNode):
    """
    Time-restricting node is responsible for enforcing temporal constraints on confidences. It checks whether
    length of underlying window for a confidence fits into its requirements.
    """

    time_requirement: RelativeTimeFrame

    def __init__(self, action: BehaviorNode, time_requirement: RelativeTimeFrame, name: str | None = None):
        super().__init__(name)
        self.children = [action]
        self.time_requirement = time_requirement

    def compute_graph_layer(self, variables: list[BehaviorVariable],
                            windows: list[BlockWindow]) -> LambdaTimeGraphLayer:

        durations = [duration for _, _, duration in windows]
        child_layer = self.children[0].compute_graph_layer(variables, windows)

        def get_weight(start: int, stop: int) -> Confidence:
            frame_duration = sum(durations[start:stop], start=timedelta(0))

            if frame_duration in self.time_requirement:
                return child_layer(start, stop)
            return Confidence.impossible()

        layer = LambdaTimeGraphLayer(get_weight, len(windows), name=str(self),
                                     sublayers=[child_layer] if Configuration.debug else None)
        return layer

    def get_sequence_info(self, default_min: timedelta | None = None) -> list[tuple[set[BehaviorVariable], timedelta]]:
        return [(self.get_variables()[0], self.get_time_requirement(default_min).minimal)]

    def get_variables(self) -> list[set[BehaviorVariable]]:
        return self.children[0].get_variables()

    def get_time_requirement(self, default_min: timedelta | None = None,
                             default_max: timedelta | None = None) -> RelativeTimeFrame:
        child_time_req = self.children[0].get_time_requirement(default_min, default_max)
        if child_time_req == RelativeTimeFrame(default_min, default_max):
            return self.time_requirement
        return self.time_requirement.intersect(child_time_req)

    def is_symmetrical(self, agent_variables: set[BehaviorVariable]) -> bool:
        return self.children[0].is_symmetrical(agent_variables)

    def __str__(self):
        return self.name or f"{str(self.children[0])} FOR {self.time_requirement.name_string()}"

    def __eq__(self, other):
        if not isinstance(other, TimeRestrictingNode):
            return False
        return self.children[0] == other.children[0] and self.time_requirement == other.time_requirement


class ConfidenceRestrictingNode(RestrictingNode):
    """
    Confidence-restricting node is responsible for enforcing confidence constraints on confidences. It checks whether
    confidence value is sufficiently high.
    """

    def __init__(self, action: BehaviorNode, min_confidence: Confidence | None = None, name: str | None = None):
        super().__init__(name)
        self.children = [action]
        self.min_confidence = min_confidence or Confidence(
            Configuration.min_confidence + (1.0 - Configuration.min_confidence) / 2, 1.0)
        self.cmp = ConfidenceComparer.ConformityBased()

    def compute_graph_layer(self, variables: list[BehaviorVariable],
                            windows: list[BlockWindow]) -> LambdaTimeGraphLayer:
        child_layer = self.children[0].compute_graph_layer(variables, windows)

        def get_weight(start: int, stop: int) -> Confidence:
            child_conf = child_layer(start, stop)
            if self.cmp.compare_int(child_conf, self.min_confidence) < 0:
                return Confidence.impossible()
            return child_conf

        layer = LambdaTimeGraphLayer(get_weight, len(windows), name=str(self),
                                     sublayers=[child_layer] if Configuration.debug else None)
        return layer

    def get_sequence_info(self, default_min: timedelta | None = None) -> list[tuple[set[BehaviorVariable], timedelta]]:
        return [(self.get_variables()[0], self.get_time_requirement(default_min).minimal)]

    def get_variables(self) -> list[set[BehaviorVariable]]:
        return self.children[0].get_variables()

    def get_time_requirement(self, default_min: timedelta | None = None,
                             default_max: timedelta | None = None) -> RelativeTimeFrame:
        return self.children[0].get_time_requirement(default_min, default_max)

    def is_symmetrical(self, agent_variables: set[BehaviorVariable]) -> bool:
        return self.children[0].is_symmetrical(agent_variables)

    def __repr__(self):
        return f"ConfidenceRestrictingNode({self.children[0]}, {self.min_confidence})"

    def __str__(self):
        return self.name or f"{str(self.children[0])} WITH c >= {float(self.min_confidence)}"

    def __eq__(self, other):
        if not isinstance(other, ConfidenceRestrictingNode):
            return False
        return self.children[0] == other.children[0] and self.min_confidence == other.min_confidence
