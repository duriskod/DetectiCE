import unittest
from datetime import timedelta

from .behavior_utils import BlockBuilder, reference_date

from ...data import AgentVariable, Speed, Direction


class BlockBuilderTest(unittest.TestCase):

    def test_builder_on_single_traj(self):
        anna = AgentVariable("Anna")

        agents, tuple_agents = (BlockBuilder([anna])
                                .with_agent(anna, 5)
                                .with_agent(anna, 5, Speed.RUN, Direction.LEFT)
                                .build())

        self.assertEqual(1, len(agents))
        self.assertEqual(0, len(tuple_agents))
        self.assertEqual(10, len(agents[anna].blocks))

    def test_builder_on_single_traj_without_granularity(self):
        anna = AgentVariable("Anna")

        agents, tuple_agents = (BlockBuilder([anna], granularity=None)
                                .with_agent(anna, 5)
                                .with_agent(anna, 5, Speed.RUN, Direction.LEFT)
                                .build())

        self.assertEqual(1, len(agents))
        self.assertEqual(0, len(tuple_agents))
        self.assertEqual(2, len(agents[anna].blocks))

    def test_builder_on_single_traj_with_gaps(self):
        anna = AgentVariable("Anna")

        agents, tuple_agents = (BlockBuilder([anna], granularity=None)
                                .with_agent(anna, 5)
                                .without_agent(anna, 5)
                                .with_agent(anna, 5, Speed.RUN, Direction.LEFT)
                                .build())

        self.assertEqual(1, len(agents))
        self.assertEqual(0, len(tuple_agents))
        self.assertEqual(2, len(agents[anna].blocks))
        self.assertEqual(timedelta(seconds=5), agents[anna].blocks[-1].start_time - agents[anna].blocks[0].end_time)

    def test_builder_on_two_trajs(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        agents, agent_tuples = (BlockBuilder([anna, bob])
                                .with_agent(anna, 10)
                                .with_agent(bob, 10)
                                .with_agents(anna, bob, 10)
                                .build())

        self.assertEqual(2, len(agents))
        self.assertEqual(2, len(agent_tuples))
        self.assertEqual(10, len(agents[anna].blocks))
        self.assertEqual(10, len(agents[bob].blocks))
        self.assertEqual(10, len(agent_tuples[anna, bob].blocks))

    def test_builder_on_two_offset_trajs(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        agents, agent_tuples = (BlockBuilder([anna, bob])
                                .without_agent(anna, 5)
                                .with_agent(anna, 10)
                                .with_agent(bob, 10)
                                .build())

        self.assertEqual(2, len(agents))
        self.assertEqual(2, len(agent_tuples))
        self.assertEqual(10, len(agents[anna].blocks))
        self.assertEqual(10, len(agents[bob].blocks))
        self.assertEqual(0, len(agent_tuples[anna, bob].blocks))
        self.assertEqual(0, len(agent_tuples[bob, anna].blocks))

    def test_builder_mixed_singles_and_tuples(self):
        anna = AgentVariable("Anna")
        bob = AgentVariable("Bob")

        agents, agent_tuples = (BlockBuilder([anna, bob])
                                .with_agent(anna, 10)
                                .without_agents(bob, anna, 10)
                                .with_agents(anna, bob, 20)
                                .with_agent(anna, 5)
                                .with_agents(anna, bob, 5)
                                .with_agents(bob, anna, 15)
                                .without_agent(bob, 5)
                                .without_agents(anna, bob, 5)
                                .without_agent(anna, 10)
                                .with_agents(bob, anna, 10)
                                .with_agent(bob, 10)
                                .with_agent(anna, 10)
                                .build())

        # Anna 10 + 5 + <10> + 10
        #  Bob <5> + 10
        #  A>B 20 + 5 + <5>
        #  B>A <10> + 15 + 10

        self.assertEqual(2, len(agents))
        self.assertEqual(2, len(agent_tuples))

        self.assertEqual(25, len(agents[anna].blocks))
        self.assertEqual(reference_date + timedelta(seconds=35), agents[anna].blocks[-1].end_time)

        self.assertEqual(10, len(agents[bob].blocks))
        self.assertEqual(reference_date + timedelta(seconds=15), agents[bob].blocks[-1].end_time)

        self.assertEqual(25, len(agent_tuples[anna, bob].blocks))
        self.assertEqual(reference_date + timedelta(seconds=25), agent_tuples[anna, bob].blocks[-1].end_time)

        self.assertEqual(25, len(agent_tuples[bob, anna].blocks))
        self.assertEqual(reference_date + timedelta(seconds=35), agent_tuples[bob, anna].blocks[-1].end_time)


if __name__ == "__main__":
    unittest.main()
