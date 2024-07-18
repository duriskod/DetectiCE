import unittest
from datetime import timedelta

from .data_utils import reference_date

from ..agent import Agent, AgentTuple
from ..features import Speed, Direction, DistanceChange, MutualDirection, Distance
from ..single_block import SingleBlock
from ..time_frame import TimeFrame
from ..tuple_block import TupleBlock


class AgentTest(unittest.TestCase):

    def test_at_time(self):
        agent = Agent(0, [
            SingleBlock(reference_date + timedelta(seconds=0), reference_date + timedelta(seconds=7.5),
                        Speed.STAND, Direction.NOT_MOVING),
            SingleBlock(reference_date + timedelta(seconds=7.55), reference_date + timedelta(seconds=21.1),
                        Speed.RUN, Direction.STRAIGHT),
            SingleBlock(reference_date + timedelta(seconds=21.15), reference_date + timedelta(seconds=35.5),
                        Speed.WALK, Direction.STRAIGHT),
            SingleBlock(reference_date + timedelta(seconds=40), reference_date + timedelta(seconds=40.5),
                        Speed.RUN, Direction.STRAIGHT),
            SingleBlock(reference_date + timedelta(seconds=40.55), reference_date + timedelta(minutes=1),
                        Speed.RUN, Direction.LEFT)
        ])

        # Before first block
        block = agent.at_time(reference_date - timedelta(seconds=3))
        self.assertIsNone(block)

        # Left edge of first block
        block = agent.at_time(reference_date + timedelta(seconds=0))
        self.assertEqual(reference_date + timedelta(seconds=0), block.start_time)
        self.assertEqual(reference_date + timedelta(seconds=7.5), block.end_time)

        # In the middle of block
        block = agent.at_time(reference_date + timedelta(seconds=7))
        self.assertEqual(reference_date + timedelta(seconds=0), block.start_time)
        self.assertEqual(reference_date + timedelta(seconds=7.5), block.end_time)

        # Right edge
        block = agent.at_time(reference_date + timedelta(seconds=7.5))
        self.assertEqual(reference_date + timedelta(seconds=0), block.start_time)
        self.assertEqual(reference_date + timedelta(seconds=7.5), block.end_time)

        # In between two blocks with gap
        block = agent.at_time(reference_date + timedelta(seconds=7.53))
        self.assertIsNone(block)

        # In between two blocks without gap -- returns block with end_time == time
        block = agent.at_time(reference_date + timedelta(seconds=21.1))
        self.assertEqual(reference_date + timedelta(seconds=7.55), block.start_time)
        self.assertEqual(reference_date + timedelta(seconds=21.1), block.end_time)

        # Last edge of last block
        block = agent.at_time(reference_date + timedelta(minutes=1))
        self.assertEqual(reference_date + timedelta(seconds=40.55), block.start_time)
        self.assertEqual(reference_date + timedelta(minutes=1), block.end_time)

        # After the last block
        block = agent.at_time(reference_date + timedelta(minutes=2))
        self.assertIsNone(block)

        # Empty agent
        agent = Agent(0, [])
        agent.at_time(reference_date + timedelta(minutes=2))
        self.assertIsNone(block)

    def test_during_time(self):
        agent = Agent(0, [
            SingleBlock(reference_date + timedelta(seconds=0), reference_date + timedelta(seconds=7.5),
                        Speed.STAND, Direction.NOT_MOVING),
            SingleBlock(reference_date + timedelta(seconds=7.55), reference_date + timedelta(seconds=21.1),
                        Speed.RUN, Direction.STRAIGHT),
            SingleBlock(reference_date + timedelta(seconds=21.15), reference_date + timedelta(seconds=35.5),
                        Speed.WALK, Direction.STRAIGHT),
            SingleBlock(reference_date + timedelta(seconds=40), reference_date + timedelta(seconds=40.5),
                        Speed.RUN, Direction.STRAIGHT),
            SingleBlock(reference_date + timedelta(seconds=40.55), reference_date + timedelta(minutes=1),
                        Speed.RUN, Direction.LEFT)
        ])

        # Span multiple
        sub_agent = agent.during_time(TimeFrame(reference_date + timedelta(seconds=10),
                                                reference_date + timedelta(seconds=50)))
        self.assertEqual(4, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=10), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(seconds=50), sub_agent.blocks[-1].end_time)

        # Span multiple & share edge with block
        sub_agent = agent.during_time(TimeFrame(reference_date + timedelta(0),
                                                reference_date + timedelta(seconds=10)))
        self.assertEqual(2, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=0), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(seconds=7.5), sub_agent.blocks[0].end_time)
        self.assertEqual(reference_date + timedelta(seconds=10), sub_agent.blocks[-1].end_time)

        # Inside a single one
        sub_agent = agent.during_time(TimeFrame(reference_date + timedelta(seconds=22),
                                                reference_date + timedelta(seconds=25)))
        self.assertEqual(1, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=22), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(seconds=25), sub_agent.blocks[-1].end_time)

        # Edge lying outside blocks
        sub_agent = agent.during_time(TimeFrame(reference_date + timedelta(seconds=21.125),
                                                reference_date + timedelta(seconds=25)))
        self.assertEqual(1, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=21.15), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(seconds=25), sub_agent.blocks[-1].end_time)

        # Both edges lying outside blocks
        sub_agent = agent.during_time(TimeFrame(reference_date + timedelta(seconds=21.125),
                                                reference_date + timedelta(seconds=40.525)))
        self.assertEqual(2, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=21.15), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(seconds=40.5), sub_agent.blocks[-1].end_time)

        # TimeFrame out of bounds
        sub_agent = agent.during_time(TimeFrame(reference_date - timedelta(seconds=5),
                                                reference_date + timedelta(seconds=61)))
        self.assertEqual(5, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=0), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(minutes=1), sub_agent.blocks[-1].end_time)

        # First block
        sub_agent = agent.during_time(TimeFrame(reference_date + timedelta(seconds=0),
                                                reference_date + timedelta(seconds=1)))
        self.assertEqual(1, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=0), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(seconds=1), sub_agent.blocks[-1].end_time)

        # Last block
        sub_agent = agent.during_time(TimeFrame(reference_date + timedelta(seconds=59),
                                                reference_date + timedelta(seconds=60)))
        self.assertEqual(1, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=59), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(seconds=60), sub_agent.blocks[-1].end_time)

        # Empty
        sub_agent = agent.during_time(TimeFrame(reference_date - timedelta(seconds=5),
                                                reference_date - timedelta(seconds=60)))
        self.assertEqual(0, len(sub_agent.blocks))


class AgentTupleTest(unittest.TestCase):

    def test_at_time(self):
        agent_tuple = AgentTuple(
            Agent(0, []),
            Agent(1, []),
            [
                TupleBlock(reference_date + timedelta(seconds=0),
                           reference_date + timedelta(seconds=7.5),
                           DistanceChange.DECREASING, DistanceChange.DECREASING,
                           Direction.STRAIGHT, MutualDirection.PARALLEL, Distance.ADJACENT),
                TupleBlock(reference_date + timedelta(seconds=7.55),
                           reference_date + timedelta(seconds=21.1),
                           DistanceChange.DECREASING, DistanceChange.INCREASING,
                           Direction.LEFT, MutualDirection.OPPOSITE, Distance.FAR),
                TupleBlock(reference_date + timedelta(seconds=21.15),
                           reference_date + timedelta(seconds=35.5),
                           DistanceChange.DECREASING, DistanceChange.DECREASING,
                           Direction.LEFT, MutualDirection.OPPOSITE, Distance.ADJACENT),
                TupleBlock(reference_date + timedelta(seconds=40),
                           reference_date + timedelta(seconds=40.5),
                           DistanceChange.DECREASING, DistanceChange.INCREASING,
                           Direction.RIGHT, MutualDirection.OPPOSITE, Distance.NEAR),
                TupleBlock(reference_date + timedelta(seconds=40.55),
                           reference_date + timedelta(minutes=1),
                           DistanceChange.INCREASING, DistanceChange.INCREASING,
                           Direction.STRAIGHT, MutualDirection.OPPOSITE, Distance.FAR)
            ]
        )

        # Before first block
        block = agent_tuple.at_time(reference_date - timedelta(seconds=3))
        self.assertIsNone(block)

        # Left edge of first block
        block = agent_tuple.at_time(reference_date + timedelta(seconds=0))
        self.assertEqual(reference_date + timedelta(seconds=0), block.start_time)
        self.assertEqual(reference_date + timedelta(seconds=7.5), block.end_time)

        # In the middle of block
        block = agent_tuple.at_time(reference_date + timedelta(seconds=7))
        self.assertEqual(reference_date + timedelta(seconds=0), block.start_time)
        self.assertEqual(reference_date + timedelta(seconds=7.5), block.end_time)

        # Right edge
        block = agent_tuple.at_time(reference_date + timedelta(seconds=7.5))
        self.assertEqual(reference_date + timedelta(seconds=0), block.start_time)
        self.assertEqual(reference_date + timedelta(seconds=7.5), block.end_time)

        # In between two blocks with gap
        block = agent_tuple.at_time(reference_date + timedelta(seconds=7.53))
        self.assertIsNone(block)

        # In between two blocks without gap -- returns block with end_time == time
        block = agent_tuple.at_time(reference_date + timedelta(seconds=21.1))
        self.assertEqual(reference_date + timedelta(seconds=7.55), block.start_time)
        self.assertEqual(reference_date + timedelta(seconds=21.1), block.end_time)

        # Last edge of last block
        block = agent_tuple.at_time(reference_date + timedelta(minutes=1))
        self.assertEqual(reference_date + timedelta(seconds=40.55), block.start_time)
        self.assertEqual(reference_date + timedelta(minutes=1), block.end_time)

        # After the last block
        block = agent_tuple.at_time(reference_date + timedelta(minutes=2))
        self.assertIsNone(block)

        # Empty agent
        agent_tuple = Agent(0, [])
        agent_tuple.at_time(reference_date + timedelta(minutes=2))
        self.assertIsNone(block)

    def test_during_time(self):
        agent_tuple = AgentTuple(
            Agent(0, []),
            Agent(1, []),
            [
                TupleBlock(reference_date + timedelta(seconds=0),
                           reference_date + timedelta(seconds=7.5),
                           DistanceChange.DECREASING, DistanceChange.DECREASING,
                           Direction.STRAIGHT, MutualDirection.PARALLEL, Distance.ADJACENT),
                TupleBlock(reference_date + timedelta(seconds=7.55),
                           reference_date + timedelta(seconds=21.1),
                           DistanceChange.DECREASING, DistanceChange.INCREASING,
                           Direction.LEFT, MutualDirection.OPPOSITE, Distance.FAR),
                TupleBlock(reference_date + timedelta(seconds=21.15),
                           reference_date + timedelta(seconds=35.5),
                           DistanceChange.DECREASING, DistanceChange.DECREASING,
                           Direction.LEFT, MutualDirection.OPPOSITE, Distance.ADJACENT),
                TupleBlock(reference_date + timedelta(seconds=40),
                           reference_date + timedelta(seconds=40.5),
                           DistanceChange.DECREASING, DistanceChange.INCREASING,
                           Direction.RIGHT, MutualDirection.OPPOSITE, Distance.NEAR),
                TupleBlock(reference_date + timedelta(seconds=40.55),
                           reference_date + timedelta(minutes=1),
                           DistanceChange.INCREASING, DistanceChange.INCREASING,
                           Direction.STRAIGHT, MutualDirection.OPPOSITE, Distance.FAR)
            ]
        )

        # Span multiple
        sub_agent = agent_tuple.during_time(TimeFrame(reference_date + timedelta(seconds=10),
                                                      reference_date + timedelta(seconds=50)))
        self.assertEqual(4, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=10), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(seconds=50), sub_agent.blocks[-1].end_time)

        # Span multiple & share edge with block
        sub_agent = agent_tuple.during_time(TimeFrame(reference_date + timedelta(0),
                                                      reference_date + timedelta(seconds=10)))
        self.assertEqual(2, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=0), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(seconds=7.5), sub_agent.blocks[0].end_time)
        self.assertEqual(reference_date + timedelta(seconds=10), sub_agent.blocks[-1].end_time)

        # Inside a single one
        sub_agent = agent_tuple.during_time(TimeFrame(reference_date + timedelta(seconds=22),
                                                      reference_date + timedelta(seconds=25)))
        self.assertEqual(1, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=22), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(seconds=25), sub_agent.blocks[-1].end_time)

        # Edge lying outside blocks
        sub_agent = agent_tuple.during_time(TimeFrame(reference_date + timedelta(seconds=21.125),
                                                      reference_date + timedelta(seconds=25)))
        self.assertEqual(1, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=21.15), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(seconds=25), sub_agent.blocks[-1].end_time)

        # Both edges lying outside blocks
        sub_agent = agent_tuple.during_time(TimeFrame(reference_date + timedelta(seconds=21.125),
                                                      reference_date + timedelta(seconds=40.525)))
        self.assertEqual(2, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=21.15), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(seconds=40.5), sub_agent.blocks[-1].end_time)

        # TimeFrame out of bounds
        sub_agent = agent_tuple.during_time(TimeFrame(reference_date - timedelta(seconds=5),
                                                      reference_date + timedelta(seconds=61)))
        self.assertEqual(5, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=0), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(minutes=1), sub_agent.blocks[-1].end_time)

        # First block
        sub_agent = agent_tuple.during_time(TimeFrame(reference_date + timedelta(seconds=0),
                                                      reference_date + timedelta(seconds=1)))
        self.assertEqual(1, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=0), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(seconds=1), sub_agent.blocks[-1].end_time)

        # Last block
        sub_agent = agent_tuple.during_time(TimeFrame(reference_date + timedelta(seconds=59),
                                                      reference_date + timedelta(seconds=60)))
        self.assertEqual(1, len(sub_agent.blocks))
        self.assertEqual(reference_date + timedelta(seconds=59), sub_agent.blocks[0].start_time)
        self.assertEqual(reference_date + timedelta(seconds=60), sub_agent.blocks[-1].end_time)

        # Empty
        sub_agent = agent_tuple.during_time(TimeFrame(reference_date - timedelta(seconds=5),
                                                      reference_date - timedelta(seconds=60)))
        self.assertEqual(0, len(sub_agent.blocks))


if __name__ == "__main__":
    unittest.main()
