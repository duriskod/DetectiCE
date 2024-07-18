from datetime import timedelta

from .base import BehaviorNode

from ..configuration import Configuration, ConfidenceConjunctionStrategy
from ..data import BehaviorVariable, Confidence, RelativeTimeFrame
from ..data.agent import BlockWindow
from ..time_graph import LambdaTimeGraphLayer


class LogicalNode(BehaviorNode):
    """
    Base class for logical behavioral nodes. These nodes contain at least one child and are responsible combining
    children's confidence matrices.
    """

    def get_sequence_info(self, default_min: timedelta | None = None) -> list[tuple[set[BehaviorVariable], timedelta]]:
        seq_info: list[tuple[set[BehaviorVariable], timedelta]] = [(set(), default_min)]
        for child in self.children:
            child_info = child.get_sequence_info(default_min)

            if len(seq_info) == 1 and len(child_info) == 1:
                self_vars, self_time = seq_info[0]
                child_vars, child_time = child_info[0]
                seq_info = [(self_vars.union(child_vars), max(self_time, child_time))]
            elif len(seq_info) == 1:
                # child_info sequential
                self_vars, _ = seq_info[0]
                seq_info = [(self_vars.union(child_vars), child_time) for child_vars, child_time in child_info]
            else:
                # [({A}, 5), ({B}, 5), ({A,C}, 10)]
                # [({C}, 10), ({B,C}, 15), ({D}, 5)]
                # [({A,C}, 5), ({}, 20), ({A,C,D}, 5)]

                self_first_vars, self_first_time = seq_info[0]
                # self_mid_vars, self_mid_time = seq_info[1:-1]
                self_last_vars, self_last_time = seq_info[-1]
                self_total_time = sum([info[1] for info in seq_info], timedelta(0))

                child_first_vars, child_first_time = child_info[0]
                # child_mid_vars, child_mid_time = child_info[1:-1]
                child_last_vars, child_last_time = child_info[-1]
                child_total_time = sum([info[1] for info in child_info], timedelta(0))

                first_seq_time = min(self_first_time, child_first_time)
                last_seq_time = min(self_last_time, child_last_time)
                mid_seq_time = max(self_total_time, child_total_time) - first_seq_time - last_seq_time
                seq_info = [
                    (self_first_vars.union(child_first_vars), first_seq_time),
                    (set(), mid_seq_time),
                    (self_last_vars.union(child_last_vars), last_seq_time)
                ]

        return seq_info

    def get_variables(self) -> list[set[BehaviorVariable]]:

        def union_varlists(varlist1: list[set[BehaviorVariable]], varlist2: list[set[BehaviorVariable]]) \
                -> list[set[BehaviorVariable]]:
            if len(varlist1) == 1 and len(varlist2) == 1:
                return [varlist1[0].union(varlist2[0])]
            elif len(varlist1) == 1 or len(varlist2) == 1:
                return [v1.union(v2) for v1 in varlist1 for v2 in varlist2]
            else:
                return [varlist1[0].union(varlist2[0]), varlist1[-1].union(varlist2[-1])]

        child_variables = [child.get_variables() for child in self.children]

        self_vars = [set()]
        for child_vars in child_variables:
            self_vars = union_varlists(self_vars, child_vars)

        return self_vars

    def get_time_requirement(self, default_min: timedelta | None = None, default_max: timedelta | None = None) \
            -> RelativeTimeFrame:
        child_time_reqs = [child.get_time_requirement(default_min, default_max) for child in self.children]
        time_req = child_time_reqs[0]
        for child_time_req in child_time_reqs[1:]:
            time_req = time_req.intersect(child_time_req)
        return time_req

    def is_symmetrical(self, agent_variables: set[BehaviorVariable]) -> bool:
        return all(child.is_symmetrical(agent_variables) for child in self.children)


class ConjunctionNode(LogicalNode):
    """
    Logical node simulating logical conjunction. Based on configured strategy combines confidences of children.
    """

    def __init__(self, children: list[BehaviorNode], name: str | None = None):
        super().__init__(name)
        self.children = children

    def compute_graph_layer(self, variables: list[BehaviorVariable], windows: list[BlockWindow]) \
            -> LambdaTimeGraphLayer:
        child_layers = [action.compute_graph_layer(variables, windows) for action in self.children]

        comparer_as_key_selector = Configuration.comparer.get_key_sorter()

        if Configuration.confidence_conjunction_strategy == ConfidenceConjunctionStrategy.MIN:
            def get_weight(start: int, stop: int) -> Confidence:
                return min([child_layer(start, stop) for child_layer in child_layers], key=comparer_as_key_selector)

            layer = LambdaTimeGraphLayer(get_weight, len(windows), name=str(self),
                                         sublayers=child_layers if Configuration.debug else None)
            return layer

        elif Configuration.confidence_conjunction_strategy == ConfidenceConjunctionStrategy.AVG:
            def get_weight(start: int, stop: int) -> Confidence:
                sub_confs = [child_layer(start, stop) for child_layer in child_layers]
                return Confidence(sum([c.nom for c in sub_confs]) / len(self.children),
                                  sum([c.denom for c in sub_confs]) / len(self.children))

            layer = LambdaTimeGraphLayer(get_weight, len(windows), name=str(self),
                                         sublayers=child_layers if Configuration.debug else None)
            return layer

    def __str__(self):
        return self.name or f"({") AND (".join(map(str, self.children))})"

    def __eq__(self, other):
        if not isinstance(other, ConjunctionNode):
            return False
        if len(self.children) != len(other.children):
            return False
        for child, other_child in zip(self.children, other.children):
            if child != other_child:
                return False
        return True


class DisjunctionNode(LogicalNode):
    """
    Logical node simulating logical disjunction.
    """

    def __init__(self, children: list[BehaviorNode], name: str | None = None):
        super().__init__(name)
        self.children = children

    def compute_graph_layer(self, variables: list[BehaviorVariable], windows: list[BlockWindow]) \
            -> LambdaTimeGraphLayer:
        child_layers = [action.compute_graph_layer(variables, windows) for action in self.children]

        comparer_as_key_selector = Configuration.comparer.get_key_sorter()

        def get_weight(start: int, stop: int) -> Confidence:
            return max([child_layer(start, stop) for child_layer in child_layers], key=comparer_as_key_selector)

        layer = LambdaTimeGraphLayer(get_weight, len(windows), name=str(self),
                                     sublayers=child_layers if Configuration.debug else None)
        return layer

    def __str__(self):
        return self.name or f"({") OR (".join(map(str, self.children))})"

    def __eq__(self, other):
        if not isinstance(other, DisjunctionNode):
            return False
        if len(self.children) != len(other.children):
            return False
        for child, other_child in zip(self.children, other.children):
            if child != other_child:
                return False
        return True


class NegationNode(LogicalNode):
    """
    Logical node simulating logical negation. Accepts only one child.
    """

    def __init__(self, child: BehaviorNode, name: str | None = None):
        super().__init__(name)
        self.children = [child]

    def compute_graph_layer(self, variables: list[BehaviorVariable], windows: list[BlockWindow]) \
            -> LambdaTimeGraphLayer:
        child_layer = self.children[0].compute_graph_layer(variables, windows)

        def get_weight(start: int, stop: int) -> Confidence:
            child_confidence = child_layer(start, stop)
            return Confidence(child_confidence.denom - child_confidence.nom, child_confidence.denom)

        layer = LambdaTimeGraphLayer(get_weight, len(windows), name=str(self),
                                     sublayers=[child_layer] if Configuration.debug else None)
        return layer

    def is_symmetrical(self, agent_variables: set[BehaviorVariable]) -> bool:
        return self.children[0].is_symmetrical(agent_variables)

    def __str__(self):
        return self.name or f"NOT ({str(self.children[0])})"

    def __eq__(self, other):
        if not isinstance(other, NegationNode):
            return False
        return self.children[0] == other.children[0]
