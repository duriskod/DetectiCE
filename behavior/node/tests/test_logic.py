import unittest

from .behavior_utils import BlockBuilder

from ..elementary import StateNode, ActorTargetStateNode, MutualStateNode
from ..logic import ConjunctionNode, DisjunctionNode, NegationNode
from ..sequential import SequentialNode

from ...configuration import Configuration, ConfidenceConjunctionStrategy
from ...data import AgentVariable, Speed, Direction, DistanceChange, Confidence, cut_to_windows


class LogicNodeTest(unittest.TestCase):

    def test_get_variables_from_elementary(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        charlie = AgentVariable("Charlie")

        full_node = ConjunctionNode([
            MutualStateNode([anna, bob]),
            ActorTargetStateNode([bob, charlie])
        ])

        self.assertEqual(1, len(full_node.get_variables()))
        self.assertSetEqual({anna, bob, charlie}, full_node.get_variables()[0])

        partial_node = DisjunctionNode([
            StateNode([anna]),
            StateNode([charlie])
        ])

        self.assertEqual(1, len(partial_node.get_variables()))
        self.assertSetEqual({anna, charlie}, partial_node.get_variables()[0])

    def test_get_variables_from_nested_sequential(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        charlie = AgentVariable("Charlie")

        node = ConjunctionNode([
            SequentialNode(
                StateNode([anna]),
                StateNode([charlie])
            ),
            StateNode([bob])
        ])

        self.assertEqual(2, len(node.get_variables()))
        self.assertSetEqual({anna, bob}, node.get_variables()[0])
        self.assertSetEqual({bob, charlie}, node.get_variables()[1])

    def test_get_variables_from_multiple_nested_sequentials(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        charlie = AgentVariable("Charlie")
        daniel = AgentVariable("Daniel")

        node = ConjunctionNode([
            SequentialNode(
                StateNode([anna]),
                StateNode([charlie]),
                StateNode([bob])
            ),
            SequentialNode(
                StateNode([daniel]),
                StateNode([bob]),
                StateNode([anna])
            ),
            StateNode([charlie])
        ])

        self.assertEqual(2, len(node.get_variables()))
        self.assertSetEqual({anna, charlie, daniel}, node.get_variables()[0])
        self.assertSetEqual({anna, bob, charlie}, node.get_variables()[1])


class ConjunctionNodeTest(unittest.TestCase):

    def test_compute_graph_layer(self):
        anna = AgentVariable("Anna")
        agents, _ = (BlockBuilder([anna])
                     .with_agent(anna, 30, Speed.WALK, Direction.STRAIGHT)
                     .with_agent(anna, 30, Speed.STAND, Direction.NOT_MOVING)
                     .with_agent(anna, 30, Speed.WALK, Direction.LEFT)
                     .with_agent(anna, 30, Speed.STAND, Direction.STRAIGHT)
                     .build())
        windows = cut_to_windows([agents[anna]], [])

        speed_state_node = StateNode([anna], speed=Speed.STAND)
        dir_state_node = StateNode([anna], direction=Direction.STRAIGHT)
        conj_node = ConjunctionNode([speed_state_node, dir_state_node])

        confidence_conjunction_strategy = Configuration.confidence_conjunction_strategy

        # strategy: MIN
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.MIN
        layer = conj_node.compute_graph_layer([anna], windows)

        self.assertEqual(Confidence(0.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(10.0, 20.0), layer(20, 40))
        self.assertEqual(Confidence(0.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(70, 80))
        self.assertEqual(Confidence(10.0, 10.0), layer(90, 100))

        # strategy: AVG
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.AVG
        layer = conj_node.compute_graph_layer([anna], windows)

        self.assertEqual(Confidence(5.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(10.0, 20.0), layer(20, 40))
        self.assertEqual(Confidence(5.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(70, 80))
        self.assertEqual(Confidence(10.0, 10.0), layer(90, 100))

        Configuration.confidence_conjunction_strategy = confidence_conjunction_strategy

    def test_eq(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        conj_node = ConjunctionNode([
            StateNode([anna], speed=Speed.WALK, direction=Direction.STRAIGHT),
            MutualStateNode([anna, bob], distance_change=DistanceChange.DECREASING)
        ])

        self.assertEqual(
            ConjunctionNode([
                StateNode([anna], speed=Speed.WALK, direction=Direction.STRAIGHT),
                MutualStateNode([anna, bob], distance_change=DistanceChange.DECREASING)
            ]),
            conj_node
        )
        self.assertNotEqual(
            ConjunctionNode([
                StateNode([anna], speed=Speed.STAND, direction=Direction.NOT_MOVING),
                MutualStateNode([anna, bob], distance_change=DistanceChange.DECREASING)
            ]),
            conj_node
        )
        self.assertNotEqual(
            ConjunctionNode([
                StateNode([anna], speed=Speed.STAND, direction=Direction.NOT_MOVING)
            ]),
            conj_node
        )
        self.assertNotEqual(
            ConjunctionNode([
                StateNode([anna], speed=Speed.STAND, direction=Direction.NOT_MOVING),
                ConjunctionNode([
                    StateNode([bob], speed=Speed.WALK, direction=Direction.STRAIGHT),
                    MutualStateNode([anna, bob], distance_change=DistanceChange.DECREASING)
                ])
            ]),
            conj_node
        )
        self.assertNotEqual(
            ActorTargetStateNode([anna, bob], intended_distance_change=DistanceChange.DECREASING),
            conj_node
        )


class DisjunctionNodeTest(unittest.TestCase):

    def test_compute_graph_layer(self):
        anna = AgentVariable("Anna")
        agents, _ = (BlockBuilder([anna])
                     .with_agent(anna, 30, Speed.WALK, Direction.STRAIGHT)
                     .with_agent(anna, 30, Speed.STAND, Direction.NOT_MOVING)
                     .with_agent(anna, 30, Speed.WALK, Direction.LEFT)
                     .with_agent(anna, 30, Speed.STAND, Direction.STRAIGHT)
                     .build())
        windows = cut_to_windows([agents[anna]], [])

        speed_state_node = StateNode([anna], speed=Speed.STAND)
        dir_state_node = StateNode([anna], direction=Direction.STRAIGHT)
        conj_node = DisjunctionNode([speed_state_node, dir_state_node])

        layer = conj_node.compute_graph_layer([anna], windows)

        self.assertEqual(Confidence(10.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(10.0, 20.0), layer(20, 40))
        self.assertEqual(Confidence(10.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(70, 80))
        self.assertEqual(Confidence(10.0, 10.0), layer(90, 100))

    def test_eq(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        disj_node = DisjunctionNode([
            StateNode([anna], speed=Speed.WALK, direction=Direction.STRAIGHT),
            MutualStateNode([anna, bob], distance_change=DistanceChange.DECREASING)
        ])

        self.assertEqual(
            DisjunctionNode([
                StateNode([anna], speed=Speed.WALK, direction=Direction.STRAIGHT),
                MutualStateNode([anna, bob], distance_change=DistanceChange.DECREASING)
            ]),
            disj_node
        )
        self.assertNotEqual(
            DisjunctionNode([
                StateNode([anna], speed=Speed.STAND, direction=Direction.NOT_MOVING),
                MutualStateNode([anna, bob], distance_change=DistanceChange.DECREASING)
            ]),
            disj_node
        )
        self.assertNotEqual(
            DisjunctionNode([
                StateNode([anna], speed=Speed.STAND, direction=Direction.NOT_MOVING)
            ]),
            disj_node
        )
        self.assertNotEqual(
            DisjunctionNode([
                StateNode([anna], speed=Speed.STAND, direction=Direction.NOT_MOVING),
                DisjunctionNode([
                    StateNode([bob], speed=Speed.WALK, direction=Direction.STRAIGHT),
                    MutualStateNode([anna, bob], distance_change=DistanceChange.DECREASING)
                ])
            ]),
            disj_node
        )
        self.assertNotEqual(
            ActorTargetStateNode([anna, bob], intended_distance_change=DistanceChange.DECREASING),
            disj_node
        )


class NegationNodeTest(unittest.TestCase):

    def test_compute_graph_layer(self):
        anna = AgentVariable("Anna")
        agents, _ = (BlockBuilder([anna])
                     .with_agent(anna, 30, Speed.WALK, Direction.STRAIGHT)
                     .with_agent(anna, 30, Speed.STAND, Direction.NOT_MOVING)
                     .with_agent(anna, 30, Speed.WALK, Direction.LEFT)
                     .with_agent(anna, 30, Speed.STAND, Direction.STRAIGHT)
                     .build())
        windows = cut_to_windows([agents[anna]], [])

        speed_state_node = StateNode([anna], speed=Speed.STAND)
        neg_node = NegationNode(speed_state_node)

        layer = neg_node.compute_graph_layer([anna], windows)

        self.assertEqual(Confidence(0.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(10.0, 20.0), layer(20, 40))
        self.assertEqual(Confidence(10.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(10.0, 10.0), layer(70, 80))
        self.assertEqual(Confidence(0.0, 10.0), layer(90, 100))

    def test_eq(self):
        anna = AgentVariable("Anna")

        neg_node = NegationNode(
            StateNode([anna], speed=Speed.WALK, direction=Direction.STRAIGHT),
        )

        self.assertEqual(
            NegationNode(
                StateNode([anna], speed=Speed.WALK, direction=Direction.STRAIGHT),
            ),
            neg_node
        )
        self.assertNotEqual(
            StateNode([anna], speed=Speed.RUN, direction=Direction.LEFT),
            neg_node
        )


if __name__ == "__main__":
    unittest.main()
