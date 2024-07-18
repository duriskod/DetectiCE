from datetime import datetime, timedelta
from typing import TypeVar, cast

from ...data import (Speed, Direction, MutualDirection, DistanceChange, Distance, SingleBlock, Agent, AgentTuple,
                     TupleBlock)

AgentHandle = TypeVar("AgentHandle")

reference_date = datetime(2000, 1, 1)


class BlockBuilder:
    """
        anna = AgentVariable("Anna")

        state_node = StateNode([anna], speed=Speed.STAND, name="TestState")

        agents, _ = BlockBuilder([anna])\
            .with_agent(anna, 30, Speed.WALK, Direction.STRAIGHT)\
            .with_agent(anna, 30, Speed.STAND, Direction.NOT_MOVING)\
            .with_agent(anna, 30, Speed.WALK, Direction.LEFT)\
            .build()

        blocks = agents[anna].blocks
    """
    agents: dict[AgentHandle, Agent]
    agent_starts: dict[AgentHandle, datetime]

    agent_tuples: dict[tuple[AgentHandle, AgentHandle], AgentTuple]
    agent_tuple_starts: dict[tuple[AgentHandle, AgentHandle], datetime]

    granularity: float
    reference_date: datetime

    def __init__(self,
                 agent_handles: list[AgentHandle],
                 granularity: float | None = 1.0,
                 reference_date: datetime = reference_date):
        self.agents = {handle: Agent(i)
                       for i, handle
                       in enumerate(agent_handles)}
        self.agent_starts = {handle: reference_date
                             for handle
                             in agent_handles}

        self.agent_tuples = {(actor_handle, target_handle): AgentTuple(actor, target, [])
                             for actor_handle, actor in self.agents.items()
                             for target_handle, target in self.agents.items()
                             if actor is not target}
        self.agent_tuple_starts = {handles: reference_date
                                   for handles
                                   in self.agent_tuples.keys()}

        self.granularity = granularity or float('inf')
        self.reference_date = reference_date

    def without_agent(self,
                      handle: AgentHandle,
                      duration: float):
        self.agent_starts[handle] += timedelta(seconds=duration)
        return self

    def with_agent(self,
                   handle: AgentHandle,
                   duration: float,
                   speed: Speed = Speed.WALK,
                   direction: Direction = Direction.STRAIGHT,
                   granularity: float | None = None):
        if granularity is None:
            granularity = self.granularity

        agent = self.agents[handle]

        start_time = self.agent_starts[handle]
        end_time = start_time + timedelta(seconds=duration)

        self.agent_starts[handle] = end_time

        blocks = cast(list[SingleBlock], SingleBlock(start_time, end_time, speed, direction).granulated(granularity))
        agent.blocks.extend(blocks)

        return self

    def without_agents(self,
                       actor_handle: AgentHandle,
                       target_handle: AgentHandle,
                       duration: float):
        self.agent_tuple_starts[actor_handle, target_handle] += timedelta(seconds=duration)
        return self

    def with_agents(self,
                    actor_handle: AgentHandle,
                    target_handle: AgentHandle,
                    duration: float,
                    intent_distance: DistanceChange = DistanceChange.CONSTANT,
                    actual_distance: DistanceChange = DistanceChange.CONSTANT,
                    relative_direction: Direction = Direction.STRAIGHT,
                    mutual_direction: MutualDirection = MutualDirection.INDEPENDENT,
                    distance: Distance = Distance.FAR,
                    granularity: float | None = None):
        if granularity is None:
            granularity = self.granularity

        agent_tuple = self.agent_tuples[actor_handle, target_handle]

        start_time = self.agent_tuple_starts[actor_handle, target_handle]
        end_time = start_time + timedelta(seconds=duration)

        self.agent_tuple_starts[actor_handle, target_handle] = end_time

        blocks = cast(list[TupleBlock], TupleBlock(start_time, end_time, intent_distance, actual_distance,
                                                   relative_direction, mutual_direction, distance).granulated(granularity))
        agent_tuple.blocks.extend(blocks)

        return self

    def build(self):
        return self.agents, self.agent_tuples
