from __future__ import annotations

import bisect
from datetime import datetime, timedelta
from typing import cast, TypeAlias

from .block import Block
from .single_block import SingleBlock
from .time_frame import TimeFrame
from .tuple_block import TupleBlock


class BlockList:
    """
    Wrapper of list of chronologically ordered blocks with no overlap but potential gaps.
    Inherited by Agent and AgentTuple sub-classes.
    """

    blocks: list[Block]

    def __init__(self, blocks: list[Block] | None):
        self.blocks = [] if blocks is None else blocks

    def at_time(self, time: datetime) -> Block | None:
        if len(self.blocks) == 0:
            return None

        idx = bisect.bisect_right(self.blocks, time, key=lambda b: b.start_time)

        if idx == 0 and self.blocks[0].start_time > time:
            return None
        if self.blocks[idx - 1].end_time < time:
            return None
        return self.blocks[idx - 1]

    def during_time(self, timeframe: TimeFrame) -> BlockList:
        if timeframe.start >= self.blocks[-1].end_time or timeframe.end <= self.blocks[0].start_time:
            return BlockList([])

        start_idx = bisect.bisect_left(self.blocks, timeframe.start, key=lambda b: b.start_time)
        end_idx = bisect.bisect_left(self.blocks, timeframe.end, key=lambda b: b.end_time)
        # Everything inbetween start_idx (inclusive) and end_id (exclusive) should be returned
        # Additionally, part of start_idx-1 block may be returned (part timeframe.start_time - block.end_time)
        # Additionally, part of end_idx block may be returned (part block.start_time - timeframe.end_time)

        blocks = self.blocks[start_idx:end_idx]

        if start_idx > end_idx:
            return BlockList([self.blocks[end_idx].during_time(timeframe.start, timeframe.end)])

        prepend_slice = (
                0 <= start_idx - 1 < len(self.blocks) and  # the block is defined
                (start_idx >= len(self.blocks) or self.blocks[
                    start_idx].start_time > timeframe.start) and  # first full block start after required start
                self.blocks[start_idx - 1].end_time > timeframe.start  # previous block intersects required timeframe
        )
        append_slice = (
                0 <= end_idx < len(self.blocks) and  # the block is defined
                (end_idx == 0 or self.blocks[
                    end_idx - 1].end_time < timeframe.end) and  # last full block start after required end
                self.blocks[end_idx].start_time < timeframe.end  # following block intersects required timeframe
        )

        if prepend_slice:
            blocks.insert(0, self.blocks[start_idx - 1].during_time(from_time=timeframe.start))
        if append_slice:
            blocks.append(self.blocks[end_idx].during_time(to_time=timeframe.end))

        return BlockList(blocks)

    @property
    def duration(self) -> timedelta:
        return self.blocks[-1].end_time - self.blocks[0].start_time


class Agent(BlockList):
    """
    Class corresponding to a semantically enriched trajectory.
    Holds a trajectory as specified by the blocks and their feature values.
    """

    agent_id: int
    blocks: list[SingleBlock]

    def __init__(self, agent_id: int, blocks: list[SingleBlock] | None = None):
        super().__init__(blocks)
        self.agent_id = agent_id

    @staticmethod
    def from_block_data(agent_id: int, blocks_data: list[dict]):
        agent = Agent(agent_id)

        agent.blocks = list(map(SingleBlock.from_block_data, blocks_data))
        agent.blocks.sort(key=lambda b: b.start_time)
        return agent

    def during_time(self, timeframe: TimeFrame) -> Agent:
        blist = super().during_time(timeframe)
        return Agent(self.agent_id, cast(list[SingleBlock], blist.blocks))

    def __repr__(self):
        return f"Agent({self.agent_id}, {self.blocks[:2]}{"..." if len(self.blocks) > 0 else ""})"


BlockSection: TypeAlias = list[SingleBlock | None]
TupleBlockSection: TypeAlias = list[list[TupleBlock | None]]
BlockWindow: TypeAlias = tuple[BlockSection, TupleBlockSection, timedelta]


class AgentTuple(BlockList):
    """
    Class corresponding to a semantically enriched trajectory pair.
    Holds a trajectory pair as specified by the tuple blocks and their tuple feature values.
    """

    actor: Agent
    target: Agent
    blocks: list[TupleBlock]

    def __init__(self, actor: Agent, target: Agent, blocks: list[TupleBlock]):
        super().__init__(blocks)
        self.actor = actor
        self.target = target

    @staticmethod
    def from_block_data(actor: Agent, target: Agent, blocks_data: list[dict]) -> AgentTuple:
        blocks = list(map(TupleBlock.from_block_data, blocks_data))
        blocks.sort(key=lambda b: b.start_time)
        return AgentTuple(actor, target, blocks)

    def during_time(self, timeframe: TimeFrame) -> AgentTuple:
        blist = super().during_time(timeframe)
        return AgentTuple(self.actor, self.target, cast(list[TupleBlock], blist.blocks))

    @property
    def duration(self) -> timedelta:
        return self.blocks[-1].end_time - self.blocks[0].start_time

    def __repr__(self):
        return f"AgentTuple({self.actor}, {self.target}, {self.blocks[:2]}{"..." if len(self.blocks) > 0 else ""})"


def cut_to_windows(agents: list[Agent], agent_tuples: list[AgentTuple],
                   strip_incomplete: bool = False,
                   max_window_size: timedelta = timedelta(seconds=1)) -> list[BlockWindow]:
    windows: list[BlockWindow] = []
    for block_section, (start_offset, end_offset) in Block.granulate(*[agent.blocks for agent in agents],
                                                                     *[agent_tuple.blocks for agent_tuple in
                                                                       agent_tuples],
                                                                     strip_incomplete=strip_incomplete,
                                                                     max_window_size=max_window_size):

        single_block_section = cast(list[SingleBlock], block_section[:len(agents)])
        traj_to_idx = {agent.agent_id: i for i, agent in enumerate(agents)}

        tuple_block_section = cast(list[TupleBlock], block_section[len(agents):])

        tuple_block_section_map = [[None for _ in agents] for _ in agents]
        for agent_tuple, tuple_block in zip(agent_tuples, tuple_block_section):
            actor_id = agent_tuple.actor.agent_id
            actor_idx = traj_to_idx[actor_id]
            target_id = agent_tuple.target.agent_id
            target_idx = traj_to_idx[target_id]
            tuple_block_section_map[actor_idx][target_idx] = tuple_block

        duration = end_offset - start_offset

        windows.append((single_block_section, tuple_block_section_map, duration))
    return windows
