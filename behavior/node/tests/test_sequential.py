import unittest

from .behavior_utils import BlockBuilder

from ..elementary import StateNode, ActorTargetStateNode, MutualStateNode
from ..sequential import SequentialNode

from ...data import AgentVariable, Speed, Direction, DistanceChange, Confidence, cut_to_windows


class SequentialNodeTest(unittest.TestCase):

    def test_get_variables_from_elementary(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        charlie = AgentVariable("Charlie")

        full_node = SequentialNode(
            MutualStateNode([anna, bob]),
            ActorTargetStateNode([bob, charlie])
        )

        self.assertEqual(2, len(full_node.get_variables()))
        self.assertSetEqual({anna, bob}, full_node.get_variables()[0])
        self.assertSetEqual({bob, charlie}, full_node.get_variables()[1])

        partial_node = SequentialNode(
            StateNode([anna]),
            StateNode([charlie])
        )

        self.assertEqual(2, len(partial_node.get_variables()))
        self.assertSetEqual({anna}, partial_node.get_variables()[0])
        self.assertSetEqual({charlie}, partial_node.get_variables()[1])

    def test_get_variables_from_nested_sequential(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        charlie = AgentVariable("Charlie")

        node = SequentialNode(
            SequentialNode(
                StateNode([anna]),
                StateNode([charlie])
            ),
            StateNode([bob])
        )

        self.assertEqual(3, len(node.get_variables()))
        self.assertSetEqual({anna}, node.get_variables()[0])
        self.assertSetEqual({charlie}, node.get_variables()[1])
        self.assertSetEqual({bob}, node.get_variables()[2])

    def test_two_actions(self):
        anna = AgentVariable("Anna")
        agents, _ = (BlockBuilder([anna])
                     .with_agent(anna, 30, Speed.WALK, Direction.STRAIGHT)
                     .with_agent(anna, 30, Speed.STAND, Direction.NOT_MOVING)
                     .with_agent(anna, 30, Speed.WALK, Direction.LEFT)
                     .build())

        windows = cut_to_windows([agents[anna]], [])
        seq_node = SequentialNode(
            StateNode([anna], speed=Speed.WALK),
            StateNode([anna], speed=Speed.STAND)
        )
        layer = seq_node.compute_graph_layer([anna], windows)

        self.assertNotEqual(Confidence.impartial(), layer(0, 60))
        self.assertEqual(Confidence(60, 60), layer(0, 60))

    def test_prefer_longer_less_certain_match(self):
        anna = AgentVariable("Anna")
        agents, _ = (BlockBuilder([anna])
                     .with_agent(anna, 8, Speed.WALK, Direction.STRAIGHT)
                     .with_agent(anna, 1, Speed.STAND, Direction.NOT_MOVING)
                     .with_agent(anna, 1, Speed.WALK, Direction.STRAIGHT)
                     .with_agent(anna, 5, Speed.STAND, Direction.NOT_MOVING)
                     .build())

        windows = cut_to_windows([agents[anna]], [])
        seq_node = SequentialNode(
            StateNode([anna], speed=Speed.WALK),
            StateNode([anna], speed=Speed.STAND)
        )

        layer = seq_node.compute_graph_layer([anna], windows)

        self.assertEqual(Confidence(14.0, 15.0), layer(0, 15))

    def test_eq(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        seq_node = SequentialNode(
            StateNode([anna], speed=Speed.WALK, direction=Direction.STRAIGHT),
            StateNode([anna], speed=Speed.STAND, direction=Direction.NOT_MOVING)
        )

        self.assertEqual(
            SequentialNode(
                StateNode([anna], speed=Speed.WALK, direction=Direction.STRAIGHT),
                StateNode([anna], speed=Speed.STAND, direction=Direction.NOT_MOVING)
            ),
            seq_node
        )
        self.assertNotEqual(
            SequentialNode(
                StateNode([anna], speed=Speed.RUN, direction=Direction.LEFT),
                StateNode([anna], speed=Speed.STAND, direction=Direction.NOT_MOVING)
            ),
            seq_node
        )
        self.assertNotEqual(
            SequentialNode(
                StateNode([anna], speed=Speed.RUN, direction=Direction.LEFT)
            ),
            seq_node
        )
        self.assertNotEqual(
            SequentialNode(
                StateNode([anna], speed=Speed.STAND, direction=Direction.NOT_MOVING),
                SequentialNode(
                    StateNode([anna], speed=Speed.RUN, direction=Direction.LEFT),
                    StateNode([bob], speed=Speed.WALK, direction=Direction.STRAIGHT)
                )
            ),
            seq_node
        )
        self.assertNotEqual(
            ActorTargetStateNode([anna, bob], intended_distance_change=DistanceChange.DECREASING),
            seq_node
        )


if __name__ == "__main__":
    unittest.main()
