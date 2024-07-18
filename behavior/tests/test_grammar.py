import unittest
from datetime import timedelta

from ..configuration import Configuration
from ..data import Speed, DistanceChange, Direction, Distance, MutualDirection, RelativeTimeFrame, Confidence
from ..grammar import parse_behavior, QueryError
from ..node import (SequentialNode, TimeRestrictingNode, ConjunctionNode, DisjunctionNode, NegationNode, StateNode,
                    ActorTargetStateNode, MutualStateNode, ConfidenceRestrictingNode)
from ..template import BehaviorTemplate


class GrammarTest(unittest.TestCase):

    def test_query_with_invalid_tokens(self):
        query = "Anna walks and Anna jumps."
        self.assertRaises(QueryError, lambda: parse_behavior(query))

    def test_query_with_single_actor_for_tuple_features(self):
        query = "Anna is far from each other"
        self.assertRaises(QueryError, lambda: parse_behavior(query))

        query = "Anna walks towards each other"
        self.assertRaises(QueryError, lambda: parse_behavior(query))

        query = "Anna runs in parallel"
        self.assertRaises(QueryError, lambda: parse_behavior(query))

    def test_behavior_THEN_behavior(self):
        query = "Anna walks and Bob walks then Bob runs then Anna runs"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            SequentialNode(
                ConjunctionNode([
                    StateNode([anna], Speed.WALK),
                    StateNode([bob], Speed.WALK)
                ]),
                StateNode([bob], Speed.RUN),
                StateNode([anna], Speed.RUN)
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

    def test_behavior_AND_behavior(self):
        query = "Anna runs and Bob walks"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            SequentialNode(
                ConjunctionNode([
                    StateNode([anna], Speed.RUN),
                    StateNode([bob], Speed.WALK)
                ])
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

    def test_behavior_OR_behavior(self):
        query = "Anna runs or Bob walks"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            SequentialNode(
                DisjunctionNode([
                    StateNode([anna], Speed.RUN),
                    StateNode([bob], Speed.WALK)
                ])
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

    def test_NOT_behavior(self):
        query = "not Anna walk for at least 30 seconds"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")

        expected_template = BehaviorTemplate(
            SequentialNode(
                NegationNode(
                    TimeRestrictingNode(
                        StateNode([anna], Speed.WALK),
                        RelativeTimeFrame(minimal=timedelta(seconds=30))
                    )
                )
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

    def test_LPAR_behavior_RPAR_optional_timespan_bounds(self):
        query = "Anna walks and Bob runs or Bob walks"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            SequentialNode(
                DisjunctionNode([
                    ConjunctionNode([
                        StateNode([anna], Speed.WALK),
                        StateNode([bob], Speed.RUN)
                    ]),
                    StateNode([bob], Speed.WALK)
                ])
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

        query = "Anna walks and (Bob runs or Bob walks)"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            SequentialNode(
                ConjunctionNode([
                    StateNode([anna], Speed.WALK),
                    DisjunctionNode([
                        StateNode([bob], Speed.RUN),
                        StateNode([bob], Speed.WALK)
                    ])
                ])
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

        query = "(Bob runs or Bob walks) for at least 30 seconds"

        actual_template = BehaviorTemplate(parse_behavior(query))
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            SequentialNode(
                TimeRestrictingNode(
                    DisjunctionNode([
                        StateNode([bob], Speed.RUN),
                        StateNode([bob], Speed.WALK)
                    ]),
                    RelativeTimeFrame(minimal=timedelta(seconds=30))
                )
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

    def test_action_optional_timespan_bounds(self):
        query = "Anna walks for at least 30 seconds"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")

        expected_template = BehaviorTemplate(
            SequentialNode(
                TimeRestrictingNode(
                    StateNode([anna], Speed.WALK),
                    RelativeTimeFrame(minimal=timedelta(seconds=30))
                )
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

    def test_actors_optional_priority_optional_negation_STAND(self):
        query = "Anna stands"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")

        expected_template = BehaviorTemplate(
            StateNode([anna], Speed.STAND)
        )

        self.assertEqual(expected_template.root, actual_template.root)

        query = "Anna must stand"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")

        expected_template = BehaviorTemplate(
            ConfidenceRestrictingNode(
                StateNode([anna], Speed.STAND),
                Confidence(Configuration.min_confidence + (1.0 - Configuration.min_confidence) / 2, 1.0)
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

    def test_actors_optional_priority_IS_optional_negation_relative_distance_ACTOR(self):
        # actors optional_priority optional_negation IS relative_distance ACTOR
        query = "Anna is far from Bob"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            MutualStateNode([anna, bob], distance=Distance.FAR)
        )

        self.assertEqual(expected_template.root, actual_template.root)

        # actors optional_priority optional_negation IS relative_distance EACH_OTHER
        query = "Anna and Bob are far from each other"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            MutualStateNode([anna, bob], distance=Distance.FAR)
        )

        self.assertEqual(expected_template.root, actual_template.root)

    def test_actors_optional_negation_STAND_relative_distance_ACTOR(self):
        # actors optional_priority optional_negation STAND relative_distance ACTOR
        query = "Anna stands near Bob"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            ConjunctionNode([
                StateNode([anna], Speed.STAND),
                MutualStateNode([anna, bob], distance=Distance.NEAR)
            ])
        )

        self.assertEqual(expected_template.root, actual_template.root)

        # actors optional_priority optional_negation STAND relative_distance EACH_OTHER
        query = "Anna and Bob stand near each other"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            ConjunctionNode([
                StateNode([anna, bob], Speed.STAND),
                MutualStateNode([anna, bob], distance=Distance.NEAR)
            ])
        )

        self.assertEqual(expected_template.root, actual_template.root)

    def test_actors_optional_priority_optional_negation_moving_speed(self):
        query = "Anna does not walk for at least 30 seconds"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")

        expected_template = BehaviorTemplate(
            SequentialNode(
                TimeRestrictingNode(
                    NegationNode(
                        StateNode([anna], Speed.WALK)
                    ),
                    RelativeTimeFrame(minimal=timedelta(seconds=30))
                )
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

    def test_actors_optional_priority_optional_negation_moving_speed_absolute_direction(self):
        query = "Anna walks left"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")

        expected_template = BehaviorTemplate(
            SequentialNode(
                StateNode([anna], speed=Speed.WALK, direction=Direction.LEFT)
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

    def test_actors_optional_priority_optional_negation_moving_speed_absolute_direction_ACTOR(self):
        query = "Anna walks to the left of Bob"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            SequentialNode(
                ConjunctionNode([
                    StateNode([anna], Speed.WALK),
                    ActorTargetStateNode([anna, bob], relative_direction=Direction.LEFT)
                ])
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

    def test_actors_optional_priority_optional_negation_moving_speed_mutual_direction(self):
        query = "Anna and Bob run in parallel"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            SequentialNode(
                ConjunctionNode([
                    StateNode([anna, bob], Speed.RUN),
                    MutualStateNode([anna, bob], mutual_direction=MutualDirection.PARALLEL)
                ])
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

    def test_actors_optional_priority_optional_negation_moving_speed_relative_direction_EACH_OTHER(self):
        query = "Anna and Bob run towards each other"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            SequentialNode(
                ConjunctionNode([
                    StateNode([anna, bob], Speed.RUN),
                    MutualStateNode([anna, bob], distance_change=DistanceChange.DECREASING)
                ])
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

    def test_actors_optional_priority_optional_negation_moving_speed_relative_direction_ACTOR(self):
        query = "Anna and Bob run towards Charlie"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")
        charlie = next(var for var in actual_template.variables if var.name == "Charlie")

        expected_template = BehaviorTemplate(
            SequentialNode(
                ConjunctionNode([
                    StateNode([anna, bob], Speed.RUN),
                    ActorTargetStateNode([anna, charlie],
                                         intended_distance_change=DistanceChange.DECREASING,
                                         relative_direction=Direction.STRAIGHT),
                    ActorTargetStateNode([bob, charlie],
                                         intended_distance_change=DistanceChange.DECREASING,
                                         relative_direction=Direction.STRAIGHT)
                ])
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

        query = "Bob runs from Anna"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            SequentialNode(
                ConjunctionNode([
                    StateNode([bob], Speed.RUN),
                    ActorTargetStateNode(
                        [bob, anna],
                        intended_distance_change=DistanceChange.INCREASING,
                        relative_direction=Direction.OPPOSITE
                    )
                ])
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)

        query = "Bob runs with Anna"

        actual_template = BehaviorTemplate(parse_behavior(query))
        anna = next(var for var in actual_template.variables if var.name == "Anna")
        bob = next(var for var in actual_template.variables if var.name == "Bob")

        expected_template = BehaviorTemplate(
            SequentialNode(
                ConjunctionNode([
                    StateNode([bob], Speed.RUN),
                    ActorTargetStateNode(
                        [bob, anna],
                        intended_distance_change=DistanceChange.CONSTANT
                    )
                ])
            )
        )

        self.assertEqual(expected_template.root, actual_template.root)


if __name__ == "__main__":
    unittest.main()
