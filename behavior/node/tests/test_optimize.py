import unittest
from datetime import timedelta

from ..elementary import StateNode
from ..logic import ConjunctionNode, DisjunctionNode, NegationNode
from ..optimize import optimize_node
from ..restriction import TimeRestrictingNode
from ..sequential import SequentialNode

from ...data import AgentVariable, Speed, RelativeTimeFrame


class OptimizeTest(unittest.TestCase):

    def test_seq_seq_optimize(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        node = SequentialNode(
            SequentialNode(
                ConjunctionNode([
                    StateNode([anna], Speed.WALK),
                    StateNode([bob], Speed.WALK)
                ]),
                StateNode([bob], Speed.RUN)
            ),
            StateNode([anna], Speed.RUN)
        )

        expected_node = SequentialNode(
            ConjunctionNode([
                StateNode([anna], Speed.WALK),
                StateNode([bob], Speed.WALK)
            ]),
            StateNode([bob], Speed.RUN),
            StateNode([anna], Speed.RUN)
        )

        self.assertEqual(expected_node, optimize_node(node))

    def test_time_time_optimize(self):
        anna = AgentVariable("Anna")

        #     "Anna walks for at most 20 seconds for at least 10 seconds"
        # ~~> "Anna walks between 10 and 20 seconds"

        node = SequentialNode(
            TimeRestrictingNode(
                TimeRestrictingNode(
                    StateNode([anna], Speed.WALK),
                    RelativeTimeFrame(maximal=timedelta(seconds=20))
                ),
                RelativeTimeFrame(minimal=timedelta(seconds=10))
            )
        )

        expected_node = SequentialNode(
            TimeRestrictingNode(
                StateNode([anna], Speed.WALK),
                RelativeTimeFrame(minimal=timedelta(seconds=10), maximal=timedelta(seconds=20))
            )
        )

        self.assertEqual(expected_node, optimize_node(node))

    def test_and_time_optimize(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        #     "Anna walks for at least 5 seconds and Bob stands for at least 10 seconds"
        # ~~> "(Anna walks and Bob stands) for at least 10 seconds"

        node = SequentialNode(
            ConjunctionNode([
                TimeRestrictingNode(
                    StateNode([anna], Speed.WALK),
                    RelativeTimeFrame(minimal=timedelta(seconds=5))
                ),
                TimeRestrictingNode(
                    StateNode([bob], Speed.STAND),
                    RelativeTimeFrame(minimal=timedelta(seconds=10))
                ),
            ])
        )

        expected_node = SequentialNode(
            TimeRestrictingNode(
                ConjunctionNode([
                    StateNode([anna], Speed.WALK),
                    StateNode([bob], Speed.STAND),
                ]),
                RelativeTimeFrame(minimal=timedelta(seconds=10))
            )
        )

        self.assertEqual(expected_node, optimize_node(node))

    def test_conj_conj_optimize(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        node = SequentialNode(
            ConjunctionNode([
                ConjunctionNode([
                    ConjunctionNode([
                        StateNode([anna], Speed.WALK),
                        StateNode([bob], Speed.WALK)
                    ]),
                    StateNode([anna], Speed.RUN)
                ]),
                StateNode([bob], Speed.RUN)
            ]),
        )

        expected_node = SequentialNode(
            ConjunctionNode([
                StateNode([anna], Speed.WALK),
                StateNode([bob], Speed.WALK),
                StateNode([anna], Speed.RUN),
                StateNode([bob], Speed.RUN)
            ])
        )

        self.assertEqual(expected_node, optimize_node(node))

    def test_conj_conj_with_time_optimize(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        node = SequentialNode(
            ConjunctionNode([
                TimeRestrictingNode(
                    ConjunctionNode([
                        ConjunctionNode([
                            StateNode([anna], Speed.RUN),
                            StateNode([bob], Speed.STAND),
                        ]),
                        StateNode([anna], Speed.WALK),
                        StateNode([bob], Speed.WALK)
                    ]),
                    RelativeTimeFrame(minimal=timedelta(seconds=30))
                ),
                StateNode([bob], Speed.RUN)
            ])
        )

        expected_node = SequentialNode(
            TimeRestrictingNode(
                ConjunctionNode([
                    StateNode([anna], Speed.RUN),
                    StateNode([bob], Speed.STAND),
                    StateNode([anna], Speed.WALK),
                    StateNode([bob], Speed.WALK),
                    StateNode([bob], Speed.RUN)
                ]),
                RelativeTimeFrame(minimal=timedelta(seconds=30))
            )
        )

        self.assertEqual(expected_node, optimize_node(node))

    def test_disj_disj_optimize(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        node = SequentialNode(
            DisjunctionNode([
                DisjunctionNode([
                    StateNode([anna], Speed.WALK),
                    StateNode([bob], Speed.WALK)
                ]),
                StateNode([bob], Speed.RUN)
            ]),
            StateNode([anna], Speed.RUN)
        )

        expected_node = SequentialNode(
            DisjunctionNode([
                StateNode([anna], Speed.WALK),
                StateNode([bob], Speed.WALK),
                StateNode([bob], Speed.RUN)
            ]),
            StateNode([anna], Speed.RUN)
        )

        self.assertEqual(expected_node, optimize_node(node))


def test_neg_neg_optimize(self):
    anna = AgentVariable("Anna")

    node = SequentialNode(
        NegationNode(
            NegationNode(
                StateNode([anna], Speed.WALK)
            )
        ),
        StateNode([anna], Speed.RUN)
    )

    expected_node = SequentialNode(
        StateNode([anna], Speed.WALK),
        StateNode([anna], Speed.RUN)
    )

    self.assertEqual(expected_node, optimize_node(node))


def test_logic_node_node(self):
    anna = AgentVariable("Anna")
    bob = AgentVariable("Bob")

    node = SequentialNode(
        DisjunctionNode([
            DisjunctionNode([
                StateNode([anna], Speed.WALK),
                StateNode([bob], Speed.WALK)
            ]),
            StateNode([bob], Speed.WALK)
        ]),
        StateNode([anna], Speed.RUN)
    )

    expected_node = SequentialNode(
        DisjunctionNode([
            StateNode([anna], Speed.WALK),
            StateNode([bob], Speed.WALK)
        ]),
        StateNode([anna], Speed.RUN)
    )

    self.assertEqual(expected_node, optimize_node(node))

    node = SequentialNode(
        ConjunctionNode([
            DisjunctionNode([
                StateNode([anna], Speed.WALK),
                StateNode([bob], Speed.WALK)
            ]),
            DisjunctionNode([
                StateNode([anna], Speed.WALK),
                StateNode([bob], Speed.WALK)
            ])
        ])
    )

    expected_node = SequentialNode(
        ConjunctionNode([
            DisjunctionNode([
                StateNode([anna], Speed.WALK),
                StateNode([bob], Speed.WALK)
            ])
        ])
    )

    self.assertEqual(expected_node, node)


def test_logic_node_subset_node(self):
    anna = AgentVariable("Anna")
    bob = AgentVariable("Bob")

    node = SequentialNode(
        ConjunctionNode([
            StateNode([anna], Speed.WALK),
            StateNode([bob], Speed.WALK),
            StateNode([anna, bob], Speed.WALK)
        ]),
        StateNode([bob], Speed.WALK)
    )

    expected_node = SequentialNode(
        ConjunctionNode([
            StateNode([anna, bob], Speed.WALK)
        ]),
        StateNode([bob], Speed.WALK)
    )

    self.assertEqual(expected_node, optimize_node(node))

    node = SequentialNode(
        DisjunctionNode([
            StateNode([anna], Speed.WALK),
            StateNode([bob], Speed.WALK),
            StateNode([anna, bob], Speed.WALK)
        ]),
        StateNode([bob], Speed.WALK)
    )

    expected_node = SequentialNode(
        DisjunctionNode([
            StateNode([anna], Speed.WALK),
            StateNode([bob], Speed.WALK),
        ]),
        StateNode([bob], Speed.WALK)
    )

    self.assertEqual(expected_node, optimize_node(node))


if __name__ == "__main__":
    unittest.main()
