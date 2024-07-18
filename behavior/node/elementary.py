from datetime import timedelta
from typing import TypeVar

from .base import BehaviorNode

from ..configuration import Configuration, ConfidenceConjunctionStrategy
from ..data.agent import BlockWindow
from ..data import (SingleBlock, TupleBlock, Confidence, RelativeTimeFrame, BehaviorVariable, Speed, Direction,
                    DistanceChange, MutualDirection, Distance)
from ..time_graph import TimeGraphLayer, DenseTimeGraphLayer


T = TypeVar("T")


def accuracy(expected: T, actual: list[T]) -> float:
    return sum(val == expected for val in actual) / len(actual)


class ElementaryNode(BehaviorNode):
    """
    Elementary behavioral node. It contains no children and is responsible for matching features of incoming data.
    """

    variables: list[BehaviorVariable]
    """ List of behavioral variables that should be matched. """

    def __init__(self, variables: list[BehaviorVariable], name: str | None = None):
        super().__init__(name)
        self.variables = variables

    def compute_graph_layer(self, variables: list[BehaviorVariable], windows: list[BlockWindow]) -> TimeGraphLayer:
        conformities = []
        for window in windows:
            conformities.append(self.get_confidence(variables, *window))

        layer = DenseTimeGraphLayer(conformities, name=str(self))
        return layer

    def get_confidence(self, variables: list[BehaviorVariable], block_section: list[SingleBlock],
                       tuple_block_section: list[list[TupleBlock]], duration: timedelta) -> Confidence:
        """
        Get a confidence value for a single window - single set of features of a specified duration
        :param variables: All variables of a template, creating mapping to the blocks in block section in order.
        :param block_section: List of blocks in a window, one for each Agent.
        :param tuple_block_section: 2D matrix of tuple blocks a single window.
        :param duration: Duration of the window at hand.
        :return: Confidence value for this window.
        """
        raise NotImplementedError("Abstract method")

    @staticmethod
    def _get_partial_confidence(values: list, expected: object | None) -> Confidence:
        """
        Compute confidence for a set of expected values vs. actual depending on currently configured strategy, without
        time information (i.e, 1 second).
        :param values: Set of actual values, i.e., filtered feature values from block/tuple_block section.
        :param expected: Expected value (or None if ignored)
        :return: Computed confidence value as if for 1 second.
        """
        if values is None or expected is None:
            return Confidence.impartial()

        if Configuration.confidence_conjunction_strategy == ConfidenceConjunctionStrategy.MIN:
            return Confidence(1.0 if all([v == expected for v in values]) else 0.0, 1.0)
        elif Configuration.confidence_conjunction_strategy == ConfidenceConjunctionStrategy.AVG:
            return Confidence(accuracy(expected, values), 1.0)

    def get_sequence_info(self, default_min: timedelta | None = None) -> list[tuple[set[BehaviorVariable], timedelta]]:
        return [(self.get_variables()[0], self.get_time_requirement(default_min).minimal)]

    def get_variables(self) -> list[set[BehaviorVariable]]:
        return [set(self.variables)]

    def get_time_requirement(self, default_min: timedelta | None = None,
                             default_max: timedelta | None = None) -> RelativeTimeFrame:
        return RelativeTimeFrame(default_min, default_max)


class StateNode(ElementaryNode):
    """
    Elementary node responsible for checking feature values for single blocks - Speed and Direction.
    """

    def __init__(self,
                 variables: list[BehaviorVariable],
                 speed: Speed | None = None,
                 direction: Direction | None = None,
                 name: str | None = None):
        super().__init__(variables, name)
        self.expected_speed = speed
        self.expected_direction = direction

    def get_confidence(self,
                       variables: list[BehaviorVariable],
                       block_section: list[SingleBlock | None],
                       _: list[list[TupleBlock | None]],
                       duration: timedelta) -> Confidence:
        block_section = [block for variable, block in zip(variables, block_section) if variable in self.variables]

        speeds = None if self.expected_speed is None \
            else [block.speed if block is not None else None for block in block_section]
        directions = None if self.expected_direction is None \
            else [block.direction if block is not None else None for block in block_section]
        confidence = self.__get_confidence(duration, speeds, directions)
        return confidence

    def __get_confidence(self,
                         duration: timedelta,
                         speeds: list[Speed | None] = None,
                         directions: list[Direction | None] = None) -> Confidence:

        speed_confidence = ElementaryNode._get_partial_confidence(speeds, self.expected_speed)
        direction_confidence = ElementaryNode._get_partial_confidence(directions, self.expected_direction)

        if Configuration.confidence_conjunction_strategy == ConfidenceConjunctionStrategy.MIN:
            confidences = [c for c in [speed_confidence, direction_confidence] if c != Confidence.impartial()]
            return min(confidences, key=Configuration.comparer.get_key_sorter()) * duration.total_seconds()

        elif Configuration.confidence_conjunction_strategy == ConfidenceConjunctionStrategy.AVG:
            confidence = speed_confidence + direction_confidence
            if speeds and directions:
                confidence = Confidence(confidence.nom / 2, confidence.denom / 2)
            return confidence * duration.total_seconds()

    def is_symmetrical(self, agent_variables: set[BehaviorVariable]) -> bool:
        return set(self.variables) == agent_variables

    def is_subset(self, other: BehaviorNode) -> bool:
        if not isinstance(other, StateNode):
            return False

        return (set(self.variables).issubset(other.variables) and
                (self.expected_speed is None or self.expected_speed == other.expected_speed) and
                (self.expected_direction is None or self.expected_direction == other.expected_direction))

    def __str__(self):
        var_str = f"({", ".join(map(str, self.variables))})"
        speed_str = "" if self.expected_speed is None else self.expected_speed.value
        dir_str = "" if self.expected_direction is None else self.expected_direction.value
        return self.name or f"{var_str} {speed_str} {dir_str}"

    def __eq__(self, other):
        if not isinstance(other, StateNode):
            return False
        return (self.variables == other.variables and
                self.expected_speed == other.expected_speed and
                self.expected_direction == other.expected_direction)


class ActorTargetStateNode(ElementaryNode):
    """
    Elementary node responsible for checking asymmetrical tuple feature values
    for tuple blocks - IntendedDistanceChange and RelativeDirection.
    """

    def __init__(self,
                 variables: list[BehaviorVariable],
                 intended_distance_change: DistanceChange | None = None,
                 relative_direction: Direction | None = None,
                 name: str | None = None):
        assert len(variables) == 2
        super().__init__(variables, name)
        self.expected_intended_distance = intended_distance_change
        self.expected_relative_direction = relative_direction

    def get_confidence(self,
                       variables: list[BehaviorVariable],
                       _: list[SingleBlock],
                       tuple_block_section: list[list[TupleBlock]],
                       duration: timedelta) -> Confidence:
        actor_idx = variables.index(self.variables[0])
        target_idx = variables.index(self.variables[1])
        actor_target_state = tuple_block_section[actor_idx][target_idx]

        if actor_target_state is None:
            return Confidence.impartial()

        intent_dists = None if self.expected_intended_distance is None else [actor_target_state.intended_distance_change]
        relative_dirs = None if self.expected_relative_direction is None else [actor_target_state.relative_direction]
        confidence = self.__get_confidence(duration, intent_dists, relative_dirs)
        return confidence

    def __get_confidence(self,
                         duration: timedelta,
                         intent_dists: list[DistanceChange] = None,
                         relative_directions: list[Direction] = None) -> Confidence:
        intent_dists_confidence = ElementaryNode._get_partial_confidence(
            intent_dists,
            self.expected_intended_distance
        )
        relative_directions_confidence = ElementaryNode._get_partial_confidence(
            relative_directions,
            self.expected_relative_direction
        )

        if Configuration.confidence_conjunction_strategy == ConfidenceConjunctionStrategy.MIN:
            confidences = [c for c in [intent_dists_confidence, relative_directions_confidence]
                           if c != Confidence.impartial()]
            return min(confidences, key=Configuration.comparer.get_key_sorter()) * duration.total_seconds()

        elif Configuration.confidence_conjunction_strategy == ConfidenceConjunctionStrategy.AVG:
            confidence = intent_dists_confidence + relative_directions_confidence
            if intent_dists and relative_directions:
                confidence = Confidence(confidence.nom / 2, confidence.denom / 2)
            return confidence * duration.total_seconds()

    def is_symmetrical(self, agent_variables: set[BehaviorVariable]) -> bool:
        return False

    def is_subset(self, other: BehaviorNode) -> bool:
        if not isinstance(other, ActorTargetStateNode):
            return False

        return (set(self.variables).issubset(other.variables) and
                (self.expected_intended_distance is None or
                 self.expected_intended_distance == other.expected_intended_distance) and
                (self.expected_relative_direction is None or
                 self.expected_relative_direction == other.expected_relative_direction))

    def __str__(self):
        actor_str = str(self.variables[0])
        target_str = str(self.variables[1])
        dist_str = "" if self.expected_intended_distance is None else self.expected_intended_distance.value
        dir_str = "" if self.expected_relative_direction is None else self.expected_relative_direction.value
        return self.name or f"{actor_str} {dist_str} DISTANCE, {dir_str} W.R.T. {target_str}"

    def __eq__(self, other):
        if not isinstance(other, ActorTargetStateNode):
            return False
        return (self.variables == other.variables and
                self.expected_intended_distance == other.expected_intended_distance and
                self.expected_relative_direction == other.expected_relative_direction)


class MutualStateNode(ElementaryNode):
    """
    Elementary node responsible for checking symmetrical tuple feature values
    for tuple blocks  - ActualDistanceChange, MutualDirection and Distance.
    """

    def __init__(self,
                 variables: list[BehaviorVariable],
                 distance_change: DistanceChange | None = None,
                 mutual_direction: MutualDirection | None = None,
                 distance: Distance | None = None,
                 name: str | None = None):
        super().__init__(variables, name)
        self.expected_distance_change = distance_change
        self.expected_mutual_direction = mutual_direction
        self.expected_distance = distance

    def get_confidence(self,
                       variables: list[BehaviorVariable],
                       _: list[SingleBlock],
                       tuple_block_section: list[list[TupleBlock]],
                       duration: timedelta) -> Confidence:
        used_indices = {i for i, var in enumerate(variables) if var in self.variables}
        tuple_blocks = []
        for i in range(len(tuple_block_section)):
            for j in range(len(tuple_block_section[i])):
                if i == j:
                    continue
                tuple_blocks.append(tuple_block_section[i][j] or tuple_block_section[j][i])

        dist_changes = None if self.expected_distance_change is None \
            else [b.actual_distance_change if b is not None else None for b in tuple_blocks]
        mutual_dirs = None if self.expected_mutual_direction is None \
            else [b.mutual_direction if b is not None else None for b in tuple_blocks]
        distances = None if self.expected_distance is None \
            else [b.distance if b is not None else None for b in tuple_blocks]

        confidence = self.__get_confidence(duration, dist_changes, mutual_dirs, distances)
        return confidence

    def __get_confidence(self,
                         duration: timedelta,
                         distance_changes: list[DistanceChange] = None,
                         mutual_directions: list[MutualDirection] = None,
                         distances: list[Distance] = None) -> Confidence:
        distance_changes_confidence = ElementaryNode._get_partial_confidence(
            distance_changes,
            self.expected_distance_change
        )
        mutual_directions_confidence = ElementaryNode._get_partial_confidence(
            mutual_directions,
            self.expected_mutual_direction
        )
        distances_confidence = ElementaryNode._get_partial_confidence(
            distances,
            self.expected_distance
        )

        if Configuration.confidence_conjunction_strategy == ConfidenceConjunctionStrategy.MIN:
            confidences = [c for c in [distance_changes_confidence, mutual_directions_confidence, distances_confidence]
                           if c != Confidence.impartial()]
            return min(confidences, key=Configuration.comparer.get_key_sorter()) * duration.total_seconds()

        elif Configuration.confidence_conjunction_strategy == ConfidenceConjunctionStrategy.AVG:
            confidence = distance_changes_confidence + mutual_directions_confidence + distances_confidence

            feature_count = sum([distance_changes is not None, mutual_directions is not None, distances is not None])
            confidence = Confidence(confidence.nom / feature_count, confidence.denom / feature_count)
            return confidence * duration.total_seconds()

    def is_symmetrical(self, agent_variables: set[BehaviorVariable]) -> bool:
        return set(self.variables) == agent_variables

    def is_subset(self, other: BehaviorNode) -> bool:
        if not isinstance(other, MutualStateNode):
            return False

        return (set(self.variables).issubset(other.variables) and
                (self.expected_distance_change is None or
                 self.expected_distance_change == other.expected_distance_change) and
                (self.expected_mutual_direction is None or
                 self.expected_mutual_direction == other.expected_mutual_direction) and
                (self.expected_distance is None or
                 self.expected_distance == other.expected_distance))

    def __str__(self):
        var_str = f"({", ".join(map(str, self.variables))})"
        mutual_dir = "" if self.expected_mutual_direction is None else f"{self.expected_mutual_direction.value} DISTANCE,"
        actual_dist = "" if self.expected_distance_change is None else f"ORIENTED {self.expected_distance_change.value},"
        distance = "" if self.expected_distance is None else self.expected_distance.value
        return self.name or f"{var_str} {actual_dist} {mutual_dir} {distance}"

    def __eq__(self, other):
        if not isinstance(other, MutualStateNode):
            return False
        return (self.variables == other.variables and
                self.expected_distance_change == other.expected_distance_change and
                self.expected_mutual_direction == other.expected_mutual_direction and
                self.expected_distance == other.expected_distance)
