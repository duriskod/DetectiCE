import unittest
from datetime import datetime, timedelta

from constants import Speed, Direction, DistanceChange, MutualDirection
from data import Block, Vector2
from preprocessing.main import as_intent_distance_category, as_relative_direction_category, DIRECTION_DEGREES_THRESHOLD, \
    as_mutual_direction_category

reference_date = datetime(2000, 1, 1, 0, 0, 0, 0)


class ClassifierTests(unittest.TestCase):

    def test_intent_dist_change_on_constant_blocks(self):
        anna = Block(
            0, reference_date, Vector2(0, 0),
            30, reference_date + timedelta(seconds=1), Vector2(0, 0),
            Speed.STAND, Direction.NOT_MOVING, 10, 20
        )

        bob = Block(
            0, reference_date, Vector2(10, 10),
            30, reference_date + timedelta(seconds=1), Vector2(10, 10),
            Speed.STAND, Direction.NOT_MOVING, 10, 20
        )

        intent_end_dist_px = (bob.start - anna.end)
        intent_start_dist_px = (bob.start - anna.start)
        intent_dist_px = intent_end_dist_px.magnitude - intent_start_dist_px.magnitude
        size_factor = (max(anna.width, anna.height) + max(bob.width, bob.height)) / 2

        intent_distance_category = as_intent_distance_category(
            (intent_dist_px / size_factor) / anna.duration
        )
        self.assertEqual(DistanceChange.CONSTANT, intent_distance_category)

    def test_intent_dist_change_on_increasing_blocks_within_epsilon(self):
        anna = Block(
            0, reference_date, Vector2(0, 0),
            30, reference_date + timedelta(seconds=1), Vector2(0, 7),
            Speed.STAND, Direction.NOT_MOVING, 10, 20
        )

        bob = Block(
            0, reference_date, Vector2(0, 10),
            30, reference_date + timedelta(seconds=1), Vector2(0, 10),
            Speed.WALK, Direction.STRAIGHT, 10, 20
        )

        intent_end_dist_px = (bob.start - anna.end)
        intent_start_dist_px = (bob.start - anna.start)
        intent_dist_px = intent_end_dist_px.magnitude - intent_start_dist_px.magnitude
        size_factor = (max(anna.width, anna.height) + max(bob.width, bob.height)) / 2

        intent_distance_category = as_intent_distance_category(
            (intent_dist_px / size_factor) / anna.duration
        )
        self.assertEqual(DistanceChange.CONSTANT, intent_distance_category)

    def test_intent_dist_change_on_increasing_blocks(self):
        anna = Block(
            0, reference_date, Vector2(0, 0),
            30, reference_date + timedelta(seconds=1), Vector2(0, 8),
            Speed.STAND, Direction.NOT_MOVING, 10, 20
        )

        bob = Block(
            0, reference_date, Vector2(0, 10),
            30, reference_date + timedelta(seconds=1), Vector2(0, 10),
            Speed.STAND, Direction.NOT_MOVING, 10, 20
        )

        intent_end_dist_px = (bob.start - anna.end)
        intent_start_dist_px = (bob.start - anna.start)
        intent_dist_px = intent_end_dist_px.magnitude - intent_start_dist_px.magnitude
        size_factor = (max(anna.width, anna.height) + max(bob.width, bob.height)) / 2

        intent_distance_category = as_intent_distance_category(
            (intent_dist_px / size_factor) / anna.duration
        )
        self.assertEqual(DistanceChange.DECREASING, intent_distance_category)

    def test_relative_direction_on_angles(self):
        self.assertEqual(Direction.STRAIGHT, as_relative_direction_category(-DIRECTION_DEGREES_THRESHOLD))
        self.assertEqual(Direction.STRAIGHT, as_relative_direction_category(0))
        self.assertEqual(Direction.STRAIGHT, as_relative_direction_category(DIRECTION_DEGREES_THRESHOLD))

        self.assertEqual(Direction.LEFT, as_relative_direction_category(-1 - DIRECTION_DEGREES_THRESHOLD))
        self.assertEqual(Direction.LEFT, as_relative_direction_category(-90))
        self.assertEqual(Direction.LEFT, as_relative_direction_category(270))
        self.assertEqual(Direction.LEFT, as_relative_direction_category(-180 + DIRECTION_DEGREES_THRESHOLD + 1))

        self.assertEqual(Direction.RIGHT, as_relative_direction_category(DIRECTION_DEGREES_THRESHOLD + 1))
        self.assertEqual(Direction.RIGHT, as_relative_direction_category(90))
        self.assertEqual(Direction.RIGHT, as_relative_direction_category(-270))
        self.assertEqual(Direction.RIGHT, as_relative_direction_category(180 - DIRECTION_DEGREES_THRESHOLD - 1))

        self.assertEqual(Direction.OPPOSITE, as_relative_direction_category(180 - DIRECTION_DEGREES_THRESHOLD))
        self.assertEqual(Direction.OPPOSITE, as_relative_direction_category(180))
        self.assertEqual(Direction.OPPOSITE, as_relative_direction_category(-180))
        self.assertEqual(Direction.OPPOSITE, as_relative_direction_category(180 + DIRECTION_DEGREES_THRESHOLD))

    def test_mutual_direction_on_angles(self):
        self.assertEqual(MutualDirection.PARALLEL, as_mutual_direction_category(-DIRECTION_DEGREES_THRESHOLD))
        self.assertEqual(MutualDirection.PARALLEL, as_mutual_direction_category(0))
        self.assertEqual(MutualDirection.PARALLEL, as_mutual_direction_category(DIRECTION_DEGREES_THRESHOLD))

        self.assertEqual(MutualDirection.INDEPENDENT, as_mutual_direction_category(-1 - DIRECTION_DEGREES_THRESHOLD))
        self.assertEqual(MutualDirection.INDEPENDENT, as_mutual_direction_category(-90))
        self.assertEqual(MutualDirection.INDEPENDENT, as_mutual_direction_category(270))
        self.assertEqual(MutualDirection.INDEPENDENT,
                         as_mutual_direction_category(-180 + DIRECTION_DEGREES_THRESHOLD + 1))

        self.assertEqual(MutualDirection.INDEPENDENT, as_mutual_direction_category(DIRECTION_DEGREES_THRESHOLD + 1))
        self.assertEqual(MutualDirection.INDEPENDENT, as_mutual_direction_category(90))
        self.assertEqual(MutualDirection.INDEPENDENT, as_mutual_direction_category(-270))
        self.assertEqual(MutualDirection.INDEPENDENT,
                         as_mutual_direction_category(180 - DIRECTION_DEGREES_THRESHOLD - 1))

        self.assertEqual(MutualDirection.OPPOSITE, as_mutual_direction_category(180 - DIRECTION_DEGREES_THRESHOLD))
        self.assertEqual(MutualDirection.OPPOSITE, as_mutual_direction_category(180))
        self.assertEqual(MutualDirection.OPPOSITE, as_mutual_direction_category(-180))
        self.assertEqual(MutualDirection.OPPOSITE, as_mutual_direction_category(180 + DIRECTION_DEGREES_THRESHOLD))

    def test_relative_direction_on_actors_in_line(self):
        anna = Block(
            0, reference_date, Vector2(0, 0),
            30, reference_date + timedelta(seconds=1), Vector2(0, 10),
            Speed.STAND, Direction.NOT_MOVING, 10, 20
        )

        bob = Block(
            0, reference_date, Vector2(0, 10),
            30, reference_date + timedelta(seconds=1), Vector2(0, 20),
            Speed.STAND, Direction.NOT_MOVING, 10, 20
        )

        actor_movement_angle = (anna.end - anna.start).angle_degrees
        actor_target_angle = (bob.start - anna.start).angle_degrees
        actor_relative_angle = actor_target_angle - actor_movement_angle
        self.assertEqual(Direction.STRAIGHT, as_relative_direction_category(actor_relative_angle))

        target_movement_angle = (bob.end - bob.start).angle_degrees
        target_target_angle = (anna.start - bob.start).angle_degrees
        target_relative_angle = target_target_angle - target_movement_angle
        self.assertEqual(Direction.OPPOSITE, as_relative_direction_category(target_relative_angle))
