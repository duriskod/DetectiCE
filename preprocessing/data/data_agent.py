import bisect
from datetime import datetime
from typing import List

from behavior import Agent, TimeFrame
from preprocessing.data.data_block import DataBlock


class DataAgent(Agent):
    agent_id: int
    blocks: List[DataBlock]

    def __init__(self, agent_id: int):
        self.agent_id = agent_id

    @staticmethod
    def from_block_data(agent_id: int, blocks_data: list[dict]):
        agent = Agent(agent_id)

        agent.blocks = list(map(DataBlock.from_block_data, blocks_data))
        agent.blocks.sort(key=lambda b: b.start_time)
        return agent

    def at_time(self, time: datetime):
        idx = bisect.bisect_right(self.blocks, time, key=lambda b: b.start_time)
        return self.blocks[idx]

    def during_time(self, timeframe: TimeFrame) -> list[DataBlock]:
        start_idx = bisect.bisect_left(self.blocks, timeframe.start, key=lambda b: b.start_time)
        end_idx = bisect.bisect_right(self.blocks, timeframe.end, key=lambda b: b.end_time)
        return self.blocks[start_idx:end_idx]
