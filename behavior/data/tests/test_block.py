import unittest
from datetime import timedelta

from .data_utils import reference_date

from ..block import Block
from ..features import Direction, Speed
from ..single_block import SingleBlock
from ..variable import AgentVariable

from ...node.tests.behavior_utils import BlockBuilder


class BlockTest(unittest.TestCase):

    def test_during_time(self):
        block = SingleBlock(reference_date, reference_date + timedelta(seconds=30), Speed.STAND, Direction.NOT_MOVING)

        sub_block = block.during_time(reference_date + timedelta(seconds=10), reference_date + timedelta(seconds=20))
        self.assertEqual(reference_date + timedelta(seconds=10), sub_block.start_time)
        self.assertEqual(reference_date + timedelta(seconds=20), sub_block.end_time)

        sub_block = block.during_time(from_time=reference_date + timedelta(seconds=25))
        self.assertEqual(reference_date + timedelta(seconds=25), sub_block.start_time)
        self.assertEqual(reference_date + timedelta(seconds=30), sub_block.end_time)

        sub_block = block.during_time(to_time=reference_date + timedelta(seconds=5))
        self.assertEqual(reference_date + timedelta(seconds=0), sub_block.start_time)
        self.assertEqual(reference_date + timedelta(seconds=5), sub_block.end_time)

    def test_granulate(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        agents, _ = (
            BlockBuilder([anna, bob], granularity=None)
            .with_agent(anna, 30)
            .with_agent(anna, 10)
            .without_agent(bob, 5)
            .with_agent(bob, 10)
            .without_agent(bob, 5)
            .with_agent(bob, 15)
            .with_agent(bob, 15)
            .build()
        )

        granulated = list(Block.granulate(*[agent.blocks for agent in agents.values()]))
        self.assertEqual(30, len(granulated))
        self.assertEqual(reference_date + timedelta(seconds=5), granulated[0][1][0])
        self.assertEqual(reference_date + timedelta(seconds=40), granulated[-1][1][1])

        granulated = list(Block.granulate(*[agent.blocks for agent in agents.values()],
                                          max_window_size=timedelta.max))
        self.assertEqual(4, len(granulated))
        self.assertEqual(reference_date + timedelta(seconds=5), granulated[0][1][0])
        self.assertEqual(reference_date + timedelta(seconds=40), granulated[-1][1][1])

        granulated = list(Block.granulate(*[agent.blocks for agent in agents.values()],
                                          strip_incomplete=False))
        self.assertEqual(50, len(granulated))
        self.assertEqual(reference_date + timedelta(seconds=0), granulated[0][1][0])
        self.assertEqual(reference_date + timedelta(seconds=50), granulated[-1][1][1])


if __name__ == "__main__":
    unittest.main()
