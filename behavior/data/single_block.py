from __future__ import annotations
from datetime import datetime

from .features import Speed, Direction
from .block import Block


class SingleBlock(Block):
    """
    Block wrapper containing information regarding feature values for trajectory's block in a specific time frame.
    """

    speed: Speed
    direction: Direction

    def __init__(self, start_time: datetime, end_time: datetime, speed: Speed, direction: Direction):
        super().__init__(start_time, end_time)
        self.start_time = start_time
        self.end_time = end_time
        self.speed = speed
        self.direction = direction

    @staticmethod
    def from_block_data(block_data: dict):
        block = SingleBlock(block_data['start_time'],
                            block_data['end_time'],
                            block_data['speed_type'],
                            block_data['direction_type'])
        return block

    def during_time(self, from_time: datetime | None = None, to_time: datetime | None = None) -> SingleBlock:
        block = super().during_time(from_time, to_time)
        return SingleBlock(block.start_time, block.end_time, self.speed, self.direction)

    def __eq__(self, other: "SingleBlock"):
        if not isinstance(other, SingleBlock):
            return False
        return self.start_time == other.start_time \
            and self.end_time == other.end_time \
            and self.speed == other.speed \
            and self.direction == other.direction

    def __repr__(self):
        return f"SingleBlock({self.duration}, {self.speed}, {self.direction})"
