import unittest
from datetime import timedelta

from ..data import (Speed, DistanceChange, MutualDirection, Direction, Distance, Confidence, RelativeTimeFrame,
                    AgentVariable)
from ..data.tests import reference_date
from ..node import (SequentialNode, ConjunctionNode, StateNode, MutualStateNode, ActorTargetStateNode, DisjunctionNode,
                    TimeRestrictingNode)
from ..node.tests import BlockBuilder
from ..template import BehaviorTemplate


class BehaviorTemplateTest(unittest.TestCase):

    def test_check_viability_simple(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        agents, _ = (
            BlockBuilder([anna, bob], granularity=1)
            .with_agent(anna, 5, speed=Speed.WALK)
            .with_agent(anna, 10, speed=Speed.STAND)
            .with_agent(anna, 10, speed=Speed.WALK)
            .without_agent(bob, 10)
            .with_agent(bob, 10, speed=Speed.WALK)
            .with_agent(bob, 10, speed=Speed.STAND)
            .build()
        )

        #       Anna 10
        # Anna + Bob 15
        #        Bob  5

        fitting_template = BehaviorTemplate(
            SequentialNode(
                TimeRestrictingNode(
                    StateNode([anna]),
                    RelativeTimeFrame(minimal=timedelta(seconds=5))
                ),
                TimeRestrictingNode(
                    StateNode([anna, bob]),
                    RelativeTimeFrame(minimal=timedelta(seconds=15))
                ),
                TimeRestrictingNode(
                    StateNode([bob]),
                    RelativeTimeFrame(minimal=timedelta(seconds=5))
                )
            )
        )
        is_viable, start_time, end_time = fitting_template.check_viability(
            [agents[var] for var in fitting_template.variables])
        self.assertTrue(is_viable)
        self.assertEqual(reference_date, start_time)
        self.assertEqual(reference_date + timedelta(seconds=30), end_time)

        non_fitting_template = BehaviorTemplate(
            SequentialNode(
                TimeRestrictingNode(
                    StateNode([anna]),
                    RelativeTimeFrame(minimal=timedelta(seconds=5))
                ),
                TimeRestrictingNode(
                    StateNode([anna, bob]),
                    RelativeTimeFrame(minimal=timedelta(seconds=10))
                ),
                TimeRestrictingNode(
                    StateNode([bob]),
                    RelativeTimeFrame(minimal=timedelta(seconds=11))
                )
            )
        )
        is_viable, start_time, end_time = non_fitting_template.check_viability(
            [agents[var] for var in non_fitting_template.variables])
        self.assertFalse(is_viable)
        self.assertIsNone(start_time)
        self.assertIsNone(end_time)

    def test_check_viability(self):
        # Anna    00:00:05 - 00:00:35
        # Bob     00:00:20 - 00:00:40
        # Charlie 00:00:15 - 00:00:45

        # granularize single agents

        # 05-15  Anna
        # 15-20  Anna Charlie
        # 20-35  Anna Bob Charlie
        # 35-40  Bob Charlie
        # 40-45  Charlie

        # matching requirements

        # 20-23 [Anna, Bob] in [Anna Bob Charlie]
        # 23-33 [Anna, Bob, Charlie] in [Anna Bob Charlie]
        # 33-35 [Bob] in [Anna Bob Charlie]
        # 35-36 [Bob] in [Bob Charlie]

        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")
        charlie = AgentVariable("Charlie")

        agents, agent_tuples = (
            BlockBuilder([anna, bob, charlie])
            .without_agent(anna, 5)
            .with_agent(anna, 30)
            .without_agent(bob, 20)
            .with_agent(bob, 20)
            .without_agent(charlie, 15)
            .with_agent(charlie, 30)
            .build()
        )

        template = BehaviorTemplate(
            SequentialNode(
                StateNode([anna, bob], Speed.WALK),
                TimeRestrictingNode(
                    ConjunctionNode([
                        MutualStateNode([anna, charlie], mutual_direction=MutualDirection.OPPOSITE),
                        StateNode([bob], Speed.WALK)
                    ]),
                    RelativeTimeFrame(timedelta(seconds=10))
                ),
                StateNode([bob], Speed.WALK),
            )
        )

        is_viable, start_time, end_time = template.check_viability([agents[var] for var in template.variables])
        self.assertTrue(is_viable)
        self.assertEqual(reference_date + timedelta(seconds=20), start_time)
        self.assertEqual(reference_date + timedelta(seconds=40), end_time)

    def test_one_side_finished_meeting_conforms(self):
        """
        Anna walks towards Bob until Anna meets Bob,
        then Anna stands and Bob stands for at least 30 seconds,
        then Anna walks to A and Bob walks to not A.
        """
        meeting_time = RelativeTimeFrame(timedelta(seconds=30))

        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        agents, agent_tuples = (
            BlockBuilder([anna, bob])
            # Anna walks straight for 20 sec, Bob stands for 20 sec, their mutual distance decreasing
            .with_agent(anna, 20, Speed.WALK, Direction.STRAIGHT)
            .with_agent(bob, 20, Speed.STAND, Direction.NOT_MOVING)
            .with_agents(anna, bob, 20, intent_distance=DistanceChange.DECREASING,
                         actual_distance=DistanceChange.DECREASING,
                         mutual_direction=MutualDirection.PARALLEL)

            # Anna and Bob both stand for 35 sec with their mutual direction being opposite
            .with_agent(anna, 35, Speed.STAND, Direction.NOT_MOVING)
            .with_agent(bob, 35, Speed.STAND, Direction.NOT_MOVING)
            .with_agents(anna, bob, 35, intent_distance=DistanceChange.CONSTANT,
                         actual_distance=DistanceChange.CONSTANT,
                         mutual_direction=MutualDirection.OPPOSITE)

            # Anna and Bob walk for 15 sec, their mutual distance increasing, their mutual direction is independent
            .with_agent(anna, 15, Speed.WALK, Direction.STRAIGHT)
            .with_agent(bob, 15, Speed.WALK, Direction.STRAIGHT)
            .with_agents(anna, bob, 15, intent_distance=DistanceChange.INCREASING,
                         actual_distance=DistanceChange.INCREASING,
                         mutual_direction=MutualDirection.INDEPENDENT)
            .build()
        )

        template = BehaviorTemplate(
            SequentialNode(
                ConjunctionNode([
                    # Anna walks towards Bob
                    ActorTargetStateNode([anna, bob], intended_distance_change=DistanceChange.DECREASING),
                    # <and>
                    # Bob stands
                    StateNode([bob], speed=Speed.STAND, name="SN1")
                ], name="CN1"),
                # <then>
                #   Anna and Bob stands
                #   for at least 30 seconds
                TimeRestrictingNode(
                    StateNode([anna, bob], speed=Speed.STAND),
                    time_requirement=meeting_time,
                    name="TRN1"
                ),
                # <then>
                ConjunctionNode([
                    #   Anna and Bob leave each other
                    DisjunctionNode([
                        MutualStateNode([anna, bob], mutual_direction=MutualDirection.INDEPENDENT),
                        MutualStateNode([anna, bob], mutual_direction=MutualDirection.OPPOSITE)
                    ]),
                    MutualStateNode([anna, bob], distance_change=DistanceChange.INCREASING)
                ], name="CN2")
            )
        )

        best_paths = template.process(
            [agents[var] for var in template.variables],
            agent_tuples.values()
        )

        time_path, best_confidence = best_paths[0]

        self.assertEqual(Confidence(70, 70), best_confidence)
        self.assertEqual(reference_date, time_path[0])
        self.assertEqual(reference_date + timedelta(seconds=70), time_path[-1])

    def test_nested_sequential(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        agents, agent_tuples = (
            BlockBuilder([anna, bob])
            # Anna & Bob together
            .with_agent(anna, 55, Speed.STAND, Direction.NOT_MOVING)
            .with_agent(bob, 15, Speed.STAND, Direction.NOT_MOVING)
            .with_agents(anna, bob, 15, mutual_direction=MutualDirection.OPPOSITE,
                         distance=Distance.ADJACENT)
            .with_agents(bob, anna, 15, mutual_direction=MutualDirection.OPPOSITE,
                         distance=Distance.ADJACENT)
            # Bob leaving
            .with_agent(bob, 10, Speed.WALK, Direction.STRAIGHT)
            .with_agents(bob, anna, 10, intent_distance=DistanceChange.INCREASING)
            # Bob away
            .with_agent(bob, 20, Speed.STAND, Direction.NOT_MOVING)
            .with_agents(bob, anna, 20, intent_distance=DistanceChange.CONSTANT)
            # Bob returning
            .with_agent(bob, 5, Speed.WALK, Direction.STRAIGHT)
            .with_agents(bob, anna, 5, intent_distance=DistanceChange.DECREASING)
            # Bob back (not in BT)
            .with_agent(bob, 5, Speed.STAND, Direction.NOT_MOVING)
            .with_agents(bob, anna, 5, intent_distance=DistanceChange.CONSTANT)
            .build()
        )

        template = BehaviorTemplate(
            SequentialNode(
                TimeRestrictingNode(
                    MutualStateNode([anna, bob], distance=Distance.ADJACENT),
                    RelativeTimeFrame(minimal=timedelta(seconds=10)),
                    name="Anna & Bob together"
                ),
                ConjunctionNode([
                    StateNode([anna], speed=Speed.STAND, name="Anna waiting"),
                    SequentialNode(
                        ActorTargetStateNode(
                            [bob, anna],
                            intended_distance_change=DistanceChange.INCREASING,
                            name="Bob leaving"
                        ),
                        ActorTargetStateNode(
                            [bob, anna],
                            intended_distance_change=DistanceChange.CONSTANT,
                            name="Bob away"
                        ),
                        ActorTargetStateNode(
                            [bob, anna],
                            intended_distance_change=DistanceChange.DECREASING,
                            name="Bob returning"
                        )
                    )
                ], name="Bob running errand")
            )
        )

        best_paths = template.process([agents[var] for var in template.variables], agent_tuples.values())

        time_path, confidence = best_paths[0]
        self.assertEqual(Confidence.certain(50), confidence)
        self.assertEqual(reference_date, time_path[0])
        self.assertEqual(reference_date + timedelta(seconds=50), time_path[-1])


if __name__ == "__main__":
    unittest.main()
