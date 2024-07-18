import unittest
from datetime import timedelta

from .behavior_utils import BlockBuilder, reference_date

from ..elementary import StateNode, MutualStateNode, ActorTargetStateNode

from ...configuration import Configuration, ConfidenceConjunctionStrategy
from ...data import (AgentVariable, cut_to_windows, Speed, Direction, DistanceChange, MutualDirection, Distance,
                     SingleBlock, TupleBlock, Confidence)


class ElementaryNodeTest(unittest.TestCase):

    def test_get_variables(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        charlie = AgentVariable("Charlie")

        state_node = StateNode([anna], speed=Speed.WALK)
        at_node = ActorTargetStateNode([anna, bob], intended_distance_change=DistanceChange.DECREASING)
        mut_node = MutualStateNode([anna, bob, charlie], mutual_direction=MutualDirection.OPPOSITE)

        self.assertEqual(1, len(state_node.get_variables()))
        self.assertSetEqual({anna}, state_node.get_variables()[0])

        self.assertEqual(1, len(at_node.get_variables()))
        self.assertSetEqual({anna, bob}, at_node.get_variables()[0])

        self.assertEqual(1, len(mut_node.get_variables()))
        self.assertSetEqual({anna, bob, charlie}, mut_node.get_variables()[0])


class StateNodeTest(unittest.TestCase):

    def test_get_confidence(self):
        anna = AgentVariable("Anna")
        walk_block = SingleBlock(
            reference_date,
            reference_date + timedelta(seconds=5),
            Speed.WALK,
            Direction.STRAIGHT
        )
        stand_block = SingleBlock(
            reference_date,
            reference_date + timedelta(seconds=5),
            Speed.STAND,
            Direction.NOT_MOVING
        )

        confidence_conjunction_strategy = Configuration.confidence_conjunction_strategy

        # region strategy: AVG
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.AVG

        speed_state_node = StateNode([anna], speed=Speed.STAND)
        self.assertEqual(
            Confidence(5.0, 5.0),
            speed_state_node.get_confidence([anna], [stand_block], [], stand_block.duration)
        )
        self.assertEqual(
            Confidence(0.0, 5.0),
            speed_state_node.get_confidence([anna], [walk_block], [], walk_block.duration)
        )

        dir_state_node = StateNode([anna], direction=Direction.STRAIGHT)
        self.assertEqual(
            Confidence(5.0, 5.0),
            dir_state_node.get_confidence([anna], [walk_block], [], walk_block.duration)
        )
        self.assertEqual(
            Confidence(0.0, 5.0),
            dir_state_node.get_confidence([anna], [stand_block], [], stand_block.duration)
        )

        speed_dir_state_node = StateNode([anna], speed=Speed.WALK, direction=Direction.STRAIGHT)
        self.assertEqual(
            Confidence(5.0, 5.0),
            speed_dir_state_node.get_confidence([anna], [walk_block], [], walk_block.duration)
        )
        self.assertEqual(
            Confidence(0.0, 5.0),
            speed_dir_state_node.get_confidence([anna], [stand_block], [], stand_block.duration)
        )
        speed_dir_state_node = StateNode([anna], speed=Speed.WALK, direction=Direction.NOT_MOVING)
        self.assertEqual(
            Confidence(2.5, 5.0),
            speed_dir_state_node.get_confidence([anna], [walk_block], [], walk_block.duration)
        )
        # endregion

        # region strategy: MIN
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.MIN

        speed_state_node = StateNode([anna], speed=Speed.STAND)
        self.assertEqual(
            Confidence(5.0, 5.0),
            speed_state_node.get_confidence([anna], [stand_block], [], stand_block.duration)
        )
        self.assertEqual(
            Confidence(0.0, 5.0),
            speed_state_node.get_confidence([anna], [walk_block], [], walk_block.duration)
        )

        dir_state_node = StateNode([anna], direction=Direction.STRAIGHT)
        self.assertEqual(
            Confidence(5.0, 5.0),
            dir_state_node.get_confidence([anna], [walk_block], [], walk_block.duration)
        )
        self.assertEqual(
            Confidence(0.0, 5.0),
            dir_state_node.get_confidence([anna], [stand_block], [], stand_block.duration)
        )

        speed_dir_state_node = StateNode([anna], speed=Speed.WALK, direction=Direction.STRAIGHT)
        self.assertEqual(
            Confidence(5.0, 5.0),
            speed_dir_state_node.get_confidence([anna], [walk_block], [], walk_block.duration)
        )
        self.assertEqual(
            Confidence(0.0, 5.0),
            speed_dir_state_node.get_confidence([anna], [stand_block], [], stand_block.duration)
        )
        speed_dir_state_node = StateNode([anna], speed=Speed.WALK, direction=Direction.NOT_MOVING)
        self.assertEqual(
            Confidence(0.0, 5.0),
            speed_dir_state_node.get_confidence([anna], [walk_block], [], walk_block.duration)
        )
        # endregion

        Configuration.confidence_conjunction_strategy = confidence_conjunction_strategy

    def test_compute_graph_layer_for_one_agent(self):
        anna = AgentVariable("Anna")
        agents, _ = (BlockBuilder([anna])
                     .with_agent(anna, 30, Speed.WALK, Direction.STRAIGHT)
                     .with_agent(anna, 30, Speed.STAND, Direction.NOT_MOVING)
                     .with_agent(anna, 30, Speed.WALK, Direction.LEFT)
                     .build())
        windows = cut_to_windows([agents[anna]], [])

        state_node_stand = StateNode([anna], speed=Speed.STAND)
        state_node_stand_straight = StateNode([anna], speed=Speed.STAND, direction=Direction.STRAIGHT)

        confidence_conjunction_strategy = Configuration.confidence_conjunction_strategy

        # region strategy: AVG
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.AVG
        layer = state_node_stand.compute_graph_layer([anna], windows)

        self.assertEqual(Confidence(10.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(10.0, 20.0), layer(20, 40))
        self.assertEqual(Confidence(0.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(70, 80))

        layer = state_node_stand_straight.compute_graph_layer([anna], windows)

        self.assertEqual(Confidence(5.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(10.0, 20.0), layer(20, 40))
        self.assertEqual(Confidence(5.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(70, 80))
        # endregion

        # region strategy: MIN
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.MIN
        layer = state_node_stand.compute_graph_layer([anna], windows)

        self.assertEqual(Confidence(10.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(10.0, 20.0), layer(20, 40))
        self.assertEqual(Confidence(0.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(70, 80))

        layer = state_node_stand_straight.compute_graph_layer([anna], windows)

        self.assertEqual(Confidence(0.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(0.0, 20.0), layer(20, 40))
        self.assertEqual(Confidence(0.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(70, 80))
        # endregion

        Configuration.confidence_conjunction_strategy = confidence_conjunction_strategy

    def test_compute_graph_layer_for_multiple_agents(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        blocks, _ = (BlockBuilder([anna, bob])
                     .with_agent(anna, 10, Speed.WALK, Direction.STRAIGHT)
                     .with_agent(anna, 10, Speed.STAND, Direction.NOT_MOVING)
                     .with_agent(bob, 8, Speed.WALK, Direction.STRAIGHT)
                     .with_agent(bob, 12, Speed.STAND, Direction.NOT_MOVING)
                     .build())

        windows = cut_to_windows([blocks[anna], blocks[bob]], [])

        state_node = StateNode([anna, bob], speed=Speed.WALK)

        confidence_conjunction_strategy = Configuration.confidence_conjunction_strategy

        # region strategy: AVG
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.AVG
        layer = state_node.compute_graph_layer([anna, bob], windows)

        self.assertEqual(Confidence(5.0, 5.0), layer(0, 5))
        self.assertEqual(Confidence(9.0, 10.0), layer(0, 10))
        self.assertEqual(Confidence(9.0, 20.0), layer(0, 20))
        # endregion

        # region strategy: MIN
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.MIN
        layer = state_node.compute_graph_layer([anna, bob], windows)

        self.assertEqual(Confidence(5.0, 5.0), layer(0, 5))
        self.assertEqual(Confidence(8.0, 10.0), layer(0, 10))
        self.assertEqual(Confidence(8.0, 20.0), layer(0, 20))
        # endregion

        Configuration.confidence_conjunction_strategy = confidence_conjunction_strategy

    def test_compute_graph_layer_for_multiple_actions(self):
        anna = AgentVariable("Anna")
        blocks, _ = (BlockBuilder([anna])
                     .with_agent(anna, 10, Speed.WALK, Direction.STRAIGHT)
                     .with_agent(anna, 10, Speed.WALK, Direction.LEFT)
                     .with_agent(anna, 10, Speed.STAND, Direction.NOT_MOVING)
                     .build())

        windows = cut_to_windows([blocks[anna]], [])

        state_node = StateNode([anna], speed=Speed.WALK, direction=Direction.LEFT)

        confidence_conjunction_strategy = Configuration.confidence_conjunction_strategy

        # region strategy: AVG
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.AVG
        layer = state_node.compute_graph_layer([anna], windows)

        self.assertEqual(Confidence(5.0, 10.0), layer(0, 10))
        self.assertEqual(Confidence(7.5, 10.0), layer(5, 15))
        self.assertEqual(Confidence(10.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(20, 30))
        # endregion

        # region strategy: MIN
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.MIN
        layer = state_node.compute_graph_layer([anna], windows)

        self.assertEqual(Confidence(0.0, 10.0), layer(0, 10))
        self.assertEqual(Confidence(5.0, 10), layer(5, 15))
        self.assertEqual(Confidence(10.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(20, 30))
        # endregion

        Configuration.confidence_conjunction_strategy = confidence_conjunction_strategy

    def test_compute_graph_layer_for_multiple_actions_and_multiple_agents(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        blocks, _ = (BlockBuilder([anna, bob])
                     .with_agent(anna, 10, Speed.WALK, Direction.STRAIGHT)
                     .with_agent(anna, 10, Speed.WALK, Direction.LEFT)
                     .with_agent(anna, 10, Speed.STAND, Direction.NOT_MOVING)
                     .with_agent(bob, 8, Speed.WALK, Direction.LEFT)
                     .with_agent(bob, 10, Speed.WALK, Direction.STRAIGHT)
                     .with_agent(bob, 12, Speed.STAND, Direction.NOT_MOVING)
                     .build())

        windows = cut_to_windows([blocks[anna], blocks[bob]], [])

        state_node = StateNode([anna, bob], speed=Speed.WALK, direction=Direction.LEFT)

        confidence_conjunction_strategy = Configuration.confidence_conjunction_strategy

        # region strategy: AVG
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.AVG
        layer = state_node.compute_graph_layer([anna, bob], windows)

        self.assertEqual(Confidence(2.5 + 4.0 + 0.5, 10.0), layer(0, 10))
        self.assertEqual(Confidence(1.25 + 2.5 + 1.5 + 1.75, 10.0), layer(5, 15))
        self.assertEqual(Confidence(5.0 + 2.0 + 0.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(20, 30))
        # endregion

        # region strategy: MIN
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.MIN
        layer = state_node.compute_graph_layer([anna, bob], windows)

        self.assertEqual(Confidence(0.0, 10.0), layer(0, 10))
        self.assertEqual(Confidence(0.0, 10.0), layer(5, 15))
        self.assertEqual(Confidence(0.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(20, 30))
        # endregion

        Configuration.confidence_conjunction_strategy = confidence_conjunction_strategy

    def test_is_subset(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        state_node = StateNode([anna], speed=Speed.STAND)

        self.assertTrue(
            state_node.is_subset(StateNode([anna], speed=Speed.STAND))
        )
        self.assertTrue(
            state_node.is_subset(StateNode([anna, bob], speed=Speed.STAND))
        )
        self.assertTrue(
            state_node.is_subset(StateNode([anna, bob], speed=Speed.STAND, direction=Direction.NOT_MOVING))
        )
        self.assertFalse(
            state_node.is_subset(ActorTargetStateNode(
                [anna, bob],
                intended_distance_change=DistanceChange.DECREASING)
            )
        )

    def test_eq(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        state_node = StateNode([anna], speed=Speed.STAND)

        self.assertEqual(
            StateNode([anna], speed=Speed.STAND),
            state_node
        )
        self.assertNotEqual(
            StateNode([anna], speed=Speed.STAND, direction=Direction.NOT_MOVING),
            state_node
        )
        self.assertNotEqual(
            ActorTargetStateNode([anna, bob], intended_distance_change=DistanceChange.DECREASING),
            state_node
        )


class ActorTargetStateNodeTest(unittest.TestCase):

    def test_get_confidence(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        conforming_block = TupleBlock(
            reference_date,
            reference_date + timedelta(seconds=5),
            intended_distance_change=DistanceChange.INCREASING,
            actual_distance_change=DistanceChange.DECREASING,
            relative_direction=Direction.STRAIGHT,
            mutual_direction=MutualDirection.INDEPENDENT,
            distance=Distance.FAR
        )
        non_conforming_block = TupleBlock(
            reference_date,
            reference_date + timedelta(seconds=5),
            intended_distance_change=DistanceChange.DECREASING,
            actual_distance_change=DistanceChange.DECREASING,
            relative_direction=Direction.LEFT,
            mutual_direction=MutualDirection.INDEPENDENT,
            distance=Distance.FAR
        )
        half_conforming_block = TupleBlock(
            reference_date,
            reference_date + timedelta(seconds=5),
            intended_distance_change=DistanceChange.DECREASING,
            actual_distance_change=DistanceChange.DECREASING,
            relative_direction=Direction.STRAIGHT,
            mutual_direction=MutualDirection.INDEPENDENT,
            distance=Distance.FAR
        )

        at_state_node = ActorTargetStateNode(
            [anna, bob],
            intended_distance_change=DistanceChange.INCREASING,
            relative_direction=Direction.STRAIGHT
        )

        confidence_conjunction_strategy = Configuration.confidence_conjunction_strategy

        # region strategy: AVG
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.AVG

        self.assertEqual(
            Confidence(5.0, 5.0),
            at_state_node.get_confidence(
                [anna, bob],
                [],
                [[None, conforming_block], [None, None]],
                conforming_block.duration
            )
        )
        self.assertEqual(
            Confidence(0.0, 5.0),
            at_state_node.get_confidence(
                [anna, bob],
                [],
                [[None, non_conforming_block], [None, None]],
                non_conforming_block.duration
            )
        )

        self.assertEqual(
            Confidence(2.5, 5.0),
            at_state_node.get_confidence(
                [anna, bob],
                [],
                [[None, half_conforming_block], [None, None]],
                half_conforming_block.duration
            )
        )
        # endregion

        # region strategy: MIN
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.MIN

        self.assertEqual(
            Confidence(5.0, 5.0),
            at_state_node.get_confidence(
                [anna, bob],
                [],
                [[None, conforming_block], [None, None]],
                conforming_block.duration
            )
        )
        self.assertEqual(
            Confidence(0.0, 5.0),
            at_state_node.get_confidence(
                [anna, bob],
                [],
                [[None, non_conforming_block], [None, None]],
                non_conforming_block.duration
            )
        )

        self.assertEqual(
            Confidence(0.0, 5.0),
            at_state_node.get_confidence(
                [anna, bob],
                [],
                [[None, half_conforming_block], [None, None]],
                half_conforming_block.duration
            )
        )
        # endregion

        Configuration.confidence_conjunction_strategy = confidence_conjunction_strategy

    def test_compute_graph_layer(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        at_state_node = ActorTargetStateNode(
            [anna, bob],
            intended_distance_change=DistanceChange.DECREASING
        )

        agents, tuple_agents = (BlockBuilder([anna, bob])
                                .with_agents(anna, bob, 30,
                                             intent_distance=DistanceChange.INCREASING,
                                             relative_direction=Direction.STRAIGHT)
                                .with_agents(anna, bob, 30,
                                             intent_distance=DistanceChange.DECREASING,
                                             relative_direction=Direction.STRAIGHT)
                                .with_agents(anna, bob, 30,
                                             intent_distance=DistanceChange.CONSTANT,
                                             relative_direction=Direction.LEFT)
                                .build())

        windows = cut_to_windows(
            [agents[anna], agents[bob]], [tuple_agents[(anna, bob)], tuple_agents[(bob, anna)]]
        )

        confidence_conjunction_strategy = Configuration.confidence_conjunction_strategy

        # region strategy: AVG
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.AVG
        layer = at_state_node.compute_graph_layer([anna, bob], windows)

        self.assertEqual(Confidence(10.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(10.0, 20.0), layer(20, 40))
        self.assertEqual(Confidence(0.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(70, 80))
        self.assertEqual(Confidence(30.0, 90.0), layer(0, 90))
        # endregion

        # region strategy: MIN
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.MIN
        layer = at_state_node.compute_graph_layer([anna, bob], windows)

        self.assertEqual(Confidence(10.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(10.0, 20.0), layer(20, 40))
        self.assertEqual(Confidence(0.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(70, 80))
        self.assertEqual(Confidence(30.0, 90.0), layer(0, 90))
        # endregion

        Configuration.confidence_conjunction_strategy = confidence_conjunction_strategy

    def test_is_subset(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        charlie = AgentVariable("Charlie")

        at_state_node = ActorTargetStateNode(
            [anna, bob],
            relative_direction=Direction.STRAIGHT
        )

        self.assertTrue(
            at_state_node.is_subset(ActorTargetStateNode(
                [anna, bob],
                relative_direction=Direction.STRAIGHT)
            )
        )
        self.assertFalse(
            at_state_node.is_subset(ActorTargetStateNode(
                [bob, charlie],
                relative_direction=Direction.STRAIGHT)
            )
        )
        self.assertTrue(
            at_state_node.is_subset(ActorTargetStateNode(
                [anna, bob],
                intended_distance_change=DistanceChange.CONSTANT,
                relative_direction=Direction.STRAIGHT)
            )
        )
        self.assertFalse(
            at_state_node.is_subset(MutualStateNode(
                [anna, bob],
                distance_change=DistanceChange.DECREASING)
            )
        )

    def test_eq(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        at_state_node = ActorTargetStateNode(
            [anna, bob],
            intended_distance_change=DistanceChange.DECREASING
        )

        self.assertEqual(
            ActorTargetStateNode([anna, bob], intended_distance_change=DistanceChange.DECREASING),
            at_state_node
        )
        self.assertNotEqual(
            ActorTargetStateNode(
                [anna, bob],
                intended_distance_change=DistanceChange.DECREASING,
                relative_direction=Direction.LEFT
            ),
            at_state_node
        )
        self.assertNotEqual(
            MutualStateNode([anna, bob], distance_change=DistanceChange.DECREASING),
            at_state_node
        )


class MutualStateNodeTest(unittest.TestCase):

    def test_get_confidence(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        conforming_block = TupleBlock(
            reference_date,
            reference_date + timedelta(seconds=5),
            intended_distance_change=DistanceChange.INCREASING,
            actual_distance_change=DistanceChange.DECREASING,
            relative_direction=Direction.STRAIGHT,
            mutual_direction=MutualDirection.INDEPENDENT,
            distance=Distance.FAR
        )
        non_conforming_block = TupleBlock(
            reference_date,
            reference_date + timedelta(seconds=5),
            intended_distance_change=DistanceChange.DECREASING,
            actual_distance_change=DistanceChange.INCREASING,
            relative_direction=Direction.LEFT,
            mutual_direction=MutualDirection.OPPOSITE,
            distance=Distance.FAR
        )
        half_conforming_block = TupleBlock(
            reference_date,
            reference_date + timedelta(seconds=5),
            intended_distance_change=DistanceChange.DECREASING,
            actual_distance_change=DistanceChange.DECREASING,
            relative_direction=Direction.STRAIGHT,
            mutual_direction=MutualDirection.OPPOSITE,
            distance=Distance.FAR
        )

        mutual_state_node = MutualStateNode(
            [anna, bob],
            distance_change=DistanceChange.DECREASING,
            mutual_direction=MutualDirection.INDEPENDENT
        )

        confidence_conjunction_strategy = Configuration.confidence_conjunction_strategy

        # region strategy: AVG
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.AVG
        self.assertEqual(
            Confidence(5.0, 5.0),
            mutual_state_node.get_confidence(
                [anna, bob],
                [],
                [[None, conforming_block], [conforming_block, None]],
                conforming_block.duration
            )
        )
        self.assertEqual(
            Confidence(0.0, 5.0),
            mutual_state_node.get_confidence(
                [anna, bob],
                [],
                [[None, non_conforming_block], [non_conforming_block, None]],
                non_conforming_block.duration
            )
        )
        self.assertEqual(
            Confidence(2.5, 5.0),
            mutual_state_node.get_confidence(
                [anna, bob],
                [],
                [[None, half_conforming_block], [half_conforming_block, None]],
                half_conforming_block.duration
            )
        )
        # endregion

        # region strategy: MIN
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.MIN
        self.assertEqual(
            Confidence(5.0, 5.0),
            mutual_state_node.get_confidence(
                [anna, bob],
                [],
                [[None, conforming_block], [conforming_block, None]],
                conforming_block.duration
            )
        )
        self.assertEqual(
            Confidence(0.0, 5.0),
            mutual_state_node.get_confidence(
                [anna, bob],
                [],
                [[None, non_conforming_block], [non_conforming_block, None]],
                non_conforming_block.duration
            )
        )
        self.assertEqual(
            Confidence(0.0, 5.0),
            mutual_state_node.get_confidence(
                [anna, bob],
                [],
                [[None, half_conforming_block], [half_conforming_block, None]],
                half_conforming_block.duration
            )
        )
        # endregion

        Configuration.confidence_conjunction_strategy = confidence_conjunction_strategy

    def test_compute_graph_layer_for_two_agents(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        mutual_state_node = MutualStateNode(
            [anna, bob],
            distance_change=DistanceChange.DECREASING
        )

        agents, tuple_agents = (BlockBuilder([anna, bob])
                                .with_agents(anna, bob, 30,
                                             actual_distance=DistanceChange.INCREASING,
                                             mutual_direction=MutualDirection.OPPOSITE)
                                .with_agents(anna, bob, 30,
                                             actual_distance=DistanceChange.DECREASING,
                                             mutual_direction=MutualDirection.PARALLEL)
                                .with_agents(anna, bob, 30,
                                             actual_distance=DistanceChange.CONSTANT,
                                             mutual_direction=MutualDirection.OPPOSITE)
                                .build())

        windows = cut_to_windows(
            [agents[anna], agents[bob]], [tuple_agents[(anna, bob)], tuple_agents[(bob, anna)]]
        )

        confidence_conjunction_strategy = Configuration.confidence_conjunction_strategy

        # region strategy: AVG
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.AVG
        layer = mutual_state_node.compute_graph_layer([anna, bob], windows)

        self.assertEqual(Confidence(10.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(10.0, 20.0), layer(20, 40))
        self.assertEqual(Confidence(0.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(70, 80))
        # endregion

        # region strategy: MIN
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.MIN
        layer = mutual_state_node.compute_graph_layer([anna, bob], windows)

        self.assertEqual(Confidence(10.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(10.0, 20.0), layer(20, 40))
        self.assertEqual(Confidence(0.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(70, 80))
        # endregion

        Configuration.confidence_conjunction_strategy = confidence_conjunction_strategy

    def test_compute_graph_layer_for_multiple_actions(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        agents, tuple_agents = (BlockBuilder([anna, bob])
                                .with_agents(anna, bob, 10,
                                             actual_distance=DistanceChange.CONSTANT,
                                             mutual_direction=MutualDirection.OPPOSITE)
                                .with_agents(anna, bob, 10,
                                             actual_distance=DistanceChange.DECREASING,
                                             mutual_direction=MutualDirection.OPPOSITE)
                                .with_agents(anna, bob, 10,
                                             actual_distance=DistanceChange.INCREASING,
                                             mutual_direction=MutualDirection.OPPOSITE)
                                .build())

        windows = cut_to_windows(
            [agents[anna], agents[bob]], [tuple_agents[(anna, bob)], tuple_agents[(bob, anna)]]
        )

        mutual_state_node = MutualStateNode(
            [anna, bob],
            distance_change=DistanceChange.DECREASING,
            mutual_direction=MutualDirection.OPPOSITE
        )

        confidence_conjunction_strategy = Configuration.confidence_conjunction_strategy

        # region strategy: AVG
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.AVG
        layer = mutual_state_node.compute_graph_layer([anna, bob], windows)

        self.assertEqual(Confidence(5.0, 10.0), layer(0, 10))
        self.assertEqual(Confidence(7.5, 10.0), layer(5, 15))
        self.assertEqual(Confidence(10.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(5.0, 10.0), layer(20, 30))
        # endregion

        # region strategy: MIN
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.MIN
        layer = mutual_state_node.compute_graph_layer([anna, bob], windows)

        self.assertEqual(Confidence(0.0, 10.0), layer(0, 10))
        self.assertEqual(Confidence(5.0, 10.0), layer(5, 15))
        self.assertEqual(Confidence(10.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(20, 30))
        # endregion

        Configuration.confidence_conjunction_strategy = confidence_conjunction_strategy

    def test_compute_graph_layer_for_three_agents(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        charlie = AgentVariable("Charlie")

        agents, tuple_agents = (BlockBuilder([anna, bob, charlie])
                                .with_agents(anna, bob, 30,
                                             actual_distance=DistanceChange.INCREASING,
                                             mutual_direction=MutualDirection.OPPOSITE)
                                .with_agents(anna, bob, 30,
                                             actual_distance=DistanceChange.DECREASING,
                                             mutual_direction=MutualDirection.PARALLEL)
                                .with_agents(anna, bob, 30,
                                             actual_distance=DistanceChange.CONSTANT,
                                             mutual_direction=MutualDirection.OPPOSITE)
                                .with_agents(anna, charlie, 30,
                                             actual_distance=DistanceChange.DECREASING,
                                             mutual_direction=MutualDirection.OPPOSITE)
                                .with_agents(anna, charlie, 30,
                                             actual_distance=DistanceChange.DECREASING,
                                             mutual_direction=MutualDirection.PARALLEL)
                                .with_agents(anna, charlie, 30,
                                             actual_distance=DistanceChange.CONSTANT,
                                             mutual_direction=MutualDirection.OPPOSITE)
                                .with_agents(bob, charlie, 30,
                                             actual_distance=DistanceChange.INCREASING,
                                             mutual_direction=MutualDirection.OPPOSITE)
                                .with_agents(bob, charlie, 30,
                                             actual_distance=DistanceChange.DECREASING,
                                             mutual_direction=MutualDirection.PARALLEL)
                                .with_agents(bob, charlie, 30,
                                             actual_distance=DistanceChange.CONSTANT,
                                             mutual_direction=MutualDirection.OPPOSITE)
                                .build())

        windows = cut_to_windows(
            [agents[anna], agents[bob], agents[charlie]],
            [tuple_agents[(anna, bob)], tuple_agents[(anna, charlie)],
             tuple_agents[(bob, anna)], tuple_agents[(bob, charlie)],
             tuple_agents[(charlie, anna)], tuple_agents[(charlie, bob)]]
        )

        mutual_state_node = MutualStateNode(
            [anna, bob, charlie],
            distance_change=DistanceChange.DECREASING
        )

        confidence_conjunction_strategy = Configuration.confidence_conjunction_strategy

        # region strategy: AVG
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.AVG
        layer = mutual_state_node.compute_graph_layer([anna, bob, charlie], windows)

        self.assertEqual(Confidence(10.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(40.0 / 3, 20.0), layer(20, 40))
        self.assertEqual(Confidence(10.0 / 3, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(70, 80))
        # endregion

        # region strategy: MIN
        Configuration.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.MIN
        layer = mutual_state_node.compute_graph_layer([anna, bob, charlie], windows)

        self.assertEqual(Confidence(10.0, 10.0), layer(40, 50))
        self.assertEqual(Confidence(10.0, 20.0), layer(20, 40))
        self.assertEqual(Confidence(0.0, 10.0), layer(10, 20))
        self.assertEqual(Confidence(0.0, 10.0), layer(70, 80))
        # endregion

        Configuration.confidence_conjunction_strategy = confidence_conjunction_strategy

    def test_is_subset(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        charlie = AgentVariable("Charlie")

        mutual_state_node = MutualStateNode(
            [anna, bob],
            distance_change=DistanceChange.DECREASING
        )

        self.assertTrue(
            mutual_state_node.is_subset(MutualStateNode(
                [anna, bob],
                distance_change=DistanceChange.DECREASING)
            )
        )
        self.assertTrue(
            mutual_state_node.is_subset(MutualStateNode(
                [anna, bob, charlie],
                distance_change=DistanceChange.DECREASING)
            )
        )
        self.assertFalse(
            mutual_state_node.is_subset(MutualStateNode(
                [bob, charlie],
                distance_change=DistanceChange.DECREASING)
            )
        )
        self.assertTrue(
            mutual_state_node.is_subset(MutualStateNode(
                [anna, bob, charlie],
                distance_change=DistanceChange.DECREASING,
                distance=Distance.FAR)
            )
        )
        self.assertFalse(
            mutual_state_node.is_subset(ActorTargetStateNode(
                [anna, bob],
                intended_distance_change=DistanceChange.DECREASING)
            )
        )

    def test_eq(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        charlie = AgentVariable("Charlie")

        mutual_state_node = MutualStateNode(
            [anna, bob, charlie],
            distance_change=DistanceChange.DECREASING
        )

        self.assertEqual(
            MutualStateNode([anna, bob, charlie], distance_change=DistanceChange.DECREASING),
            mutual_state_node
        )
        self.assertNotEqual(
            MutualStateNode([anna, bob], distance_change=DistanceChange.DECREASING),
            mutual_state_node
        )
        self.assertNotEqual(
            MutualStateNode(
                [anna, bob, charlie],
                distance_change=DistanceChange.DECREASING,
                distance=Distance.ADJACENT
            ),
            mutual_state_node
        )
        self.assertNotEqual(
            ActorTargetStateNode([anna, bob], intended_distance_change=DistanceChange.DECREASING),
            mutual_state_node
        )


if __name__ == "__main__":
    unittest.main()
