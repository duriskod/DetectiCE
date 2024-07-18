import unittest
from datetime import timedelta

from .behavior_utils import BlockBuilder

from ..elementary import StateNode, ActorTargetStateNode
from ..restriction import TimeRestrictingNode, ConfidenceRestrictingNode

from ...data import AgentVariable, Speed, Direction, DistanceChange, RelativeTimeFrame, Confidence, cut_to_windows


class TimeRestrictingNodeTest(unittest.TestCase):

    def test_compute_graph_layer(self):
        anna = AgentVariable("Anna")
        agents, _ = (BlockBuilder([anna])
                     .with_agent(anna, 30, Speed.WALK, Direction.STRAIGHT)
                     .with_agent(anna, 30, Speed.STAND, Direction.NOT_MOVING)
                     .with_agent(anna, 30, Speed.WALK, Direction.LEFT)
                     .build())
        windows = cut_to_windows([agents[anna]], [])

        speed_state_node = StateNode([anna], speed=Speed.STAND)
        time_restr_node = TimeRestrictingNode(speed_state_node,
                                              RelativeTimeFrame(timedelta(seconds=10), timedelta(seconds=20)))

        layer = time_restr_node.compute_graph_layer([anna], windows)

        self.assertEqual(Confidence(10.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(20.0, 20.0), layer(40, 60))
        self.assertEqual(Confidence(10.0, 20.0), layer(50, 70))
        self.assertEqual(Confidence(0.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence.impossible(), layer(40, 70))

    def test_eq(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        time_node = TimeRestrictingNode(
            StateNode([anna], Speed.WALK, Direction.STRAIGHT),
            RelativeTimeFrame(timedelta(seconds=10), timedelta(seconds=20))
        )

        self.assertEqual(
            TimeRestrictingNode(
                StateNode([anna], Speed.WALK, Direction.STRAIGHT),
                RelativeTimeFrame(timedelta(seconds=10), timedelta(seconds=20))
            ),
            time_node
        )
        self.assertNotEqual(
            TimeRestrictingNode(
                StateNode([anna], Speed.STAND, Direction.NOT_MOVING),
                RelativeTimeFrame(timedelta(seconds=10), timedelta(seconds=20))
            ),
            time_node
        )
        self.assertNotEqual(
            TimeRestrictingNode(
                StateNode([anna], Speed.WALK, Direction.STRAIGHT),
                RelativeTimeFrame(timedelta(seconds=10), timedelta(seconds=35))
            ),
            time_node
        )
        self.assertNotEqual(
            TimeRestrictingNode(
                StateNode([anna], Speed.STAND, Direction.NOT_MOVING),
                RelativeTimeFrame(timedelta(seconds=10), timedelta(seconds=35))
            ),
            time_node
        )
        self.assertNotEqual(
            ActorTargetStateNode([anna, bob], intended_distance_change=DistanceChange.DECREASING),
            time_node
        )


class ConfidenceRestrictingNodeTest(unittest.TestCase):

    def test_compute_graph_layer(self):
        anna = AgentVariable("Anna")
        agents, _ = (BlockBuilder([anna])
                     .with_agent(anna, 30, Speed.WALK, Direction.STRAIGHT)
                     .with_agent(anna, 30, Speed.STAND, Direction.NOT_MOVING)
                     .with_agent(anna, 30, Speed.WALK, Direction.LEFT)
                     .build())
        windows = cut_to_windows([agents[anna]], [])

        speed_state_node = StateNode([anna], speed=Speed.STAND)
        conf_restr_node = ConfidenceRestrictingNode(
            speed_state_node,
            min_confidence=Confidence(0.7, 1.0)
        )

        layer = conf_restr_node.compute_graph_layer([anna], windows)

        self.assertEqual(Confidence(10.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(20.0, 20.0), layer(40, 60))

        # layer(50, 70) for speed_state_node = Confidence(10.0, 20.0)
        self.assertEqual(Confidence.impossible(), layer(50, 70))
        # layer(10, 20) for speed_state_node = Confidence(0.0, 10.0)
        self.assertEqual(Confidence.impossible(), layer(10, 20))
        # layer(40, 70) for speed_state_node = Confidence(20.0, 30.0)
        self.assertEqual(Confidence.impossible(), layer(40, 70))

    def test_eq(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        conf_node = ConfidenceRestrictingNode(
            StateNode([anna], Speed.WALK, Direction.STRAIGHT),
            Confidence(1.0, 2.0)
        )

        self.assertEqual(
            ConfidenceRestrictingNode(
                StateNode([anna], Speed.WALK, Direction.STRAIGHT),
                Confidence(1.0, 2.0)
            ),
            conf_node
        )
        self.assertNotEqual(
            ConfidenceRestrictingNode(
                StateNode([anna], Speed.STAND, Direction.NOT_MOVING),
                Confidence(1.0, 2.0)
            ),
            conf_node
        )
        self.assertNotEqual(
            ConfidenceRestrictingNode(
                StateNode([anna], Speed.WALK, Direction.STRAIGHT),
                Confidence(1.0, 3.0)
            ),
            conf_node
        )
        self.assertNotEqual(
            ConfidenceRestrictingNode(
                StateNode([anna], Speed.STAND, Direction.NOT_MOVING),
                Confidence(1.0, 3.0)
            ),
            conf_node
        )
        self.assertNotEqual(
            ActorTargetStateNode([anna, bob], intended_distance_change=DistanceChange.DECREASING),
            conf_node
        )


if __name__ == "__main__":
    unittest.main()
