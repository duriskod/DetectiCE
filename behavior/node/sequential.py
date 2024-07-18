import itertools
from datetime import timedelta

from .base import BehaviorNode

from ..data.agent import BlockWindow
from ..data import BehaviorVariable, RelativeTimeFrame
from ..time_graph import TimeGraph, ContractedTimeGraphLayer


class SequentialNode(BehaviorNode):
    """
    Sequential node ensures its sub-nodes are matched in chronological order, one after another.
    """

    graph: TimeGraph | None

    def __init__(self, *nodes: BehaviorNode, name: str | None = None):
        super().__init__(name)
        self.children = list(nodes)

    def get_sequence_info(self, default_min: timedelta | None = None, default_max: timedelta | None = None) \
            -> list[tuple[set[BehaviorVariable], RelativeTimeFrame]]:
        seq_info = []
        for child in self.children:
            seq_info += child.get_sequence_info(default_min)
        return seq_info

    def get_variables(self) -> list[set[BehaviorVariable]]:
        self_vars = []
        for child in self.children:
            self_vars.extend(child.get_variables())
        return self_vars

    def get_time_requirement(self, default_min: timedelta | None = None, default_max: timedelta | None = None) \
            -> RelativeTimeFrame:
        child_time_reqs = [child.get_time_requirement(default_min, default_max) for child in self.children]
        if any(child_time_req.maximal == timedelta.max for child_time_req in child_time_reqs):
            new_max = timedelta.max
        else:
            new_max = sum([ctr.maximal for ctr in child_time_reqs], timedelta(0))
        return RelativeTimeFrame(sum([ctr.minimal for ctr in child_time_reqs], timedelta(0)), new_max)

    def compute_graph(self, variables: list[BehaviorVariable], windows: list[BlockWindow]) -> TimeGraph:
        self.__compute_sequence(variables, windows)
        return self.graph

    def compute_graph_layer(self, variables: list[BehaviorVariable], windows: list[BlockWindow]) \
            -> ContractedTimeGraphLayer:
        layer = self.__compute_sequence(variables, windows)
        return layer

    def __compute_sequence(self, variables: list[BehaviorVariable], windows: list[BlockWindow]) \
            -> ContractedTimeGraphLayer:
        window_count = len(windows)
        time_layers = [action.compute_graph_layer(variables, windows) for action in self.children]

        timetable = [duration for _, _, duration in windows]

        ref_time = None
        for block in itertools.chain(windows[0][0], *windows[0][1]):
            if block is not None:
                ref_time = block.start_time
                break

        self.graph = TimeGraph(time_layers, window_count + 1, timetable=timetable, reference_time=ref_time,
                               name=self.name)
        return self.graph.contracted

    def is_symmetrical(self, agent_variables: set[BehaviorVariable]) -> bool:
        return all(child.is_symmetrical(agent_variables) for child in self.children)

    def is_subset(self, other_node: BehaviorNode) -> bool:
        return False

    def __str__(self):
        return self.name or f"({") THEN (".join(map(str, self.children))})"

    def __eq__(self, other):
        if not isinstance(other, SequentialNode):
            return False
        if len(self.children) != len(other.children):
            return False
        for child, other_child in zip(self.children, other.children):
            if child != other_child:
                return False
        return True
