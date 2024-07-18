from __future__ import annotations

from datetime import datetime

from .features import Direction, DistanceChange, MutualDirection, Distance
from .block import Block


class TupleBlock(Block):
    """
    Block wrapper containing information regarding tuple feature values for
    trajectory pair's tuple block in a specific time frame.
    """

    intended_distance_change: DistanceChange
    actual_distance_change: DistanceChange

    relative_direction: Direction
    mutual_direction: MutualDirection

    distance: Distance

    def __init__(self,
                 start_time: datetime,
                 end_time: datetime,
                 intended_distance_change: DistanceChange,
                 actual_distance_change: DistanceChange,
                 relative_direction: Direction,
                 mutual_direction: MutualDirection,
                 distance: Distance):
        super().__init__(start_time, end_time)
        self.start_time = start_time
        self.end_time = end_time
        self.intended_distance_change = intended_distance_change
        self.actual_distance_change = actual_distance_change
        self.relative_direction = relative_direction
        self.mutual_direction = mutual_direction
        self.distance = distance

    @staticmethod
    def from_block_data(block_data: dict):
        block = TupleBlock(block_data['start_time'],
                           block_data['end_time'],
                           block_data['intent_dist'],
                           block_data['actual_dist'],
                           block_data['relative_dir'],
                           block_data['mutual_dir'],
                           block_data['distance'])
        return block

    def during_time(self, from_time: datetime | None = None, to_time: datetime | None = None) -> TupleBlock:
        block = super().during_time(from_time, to_time)
        return TupleBlock(block.start_time, block.end_time,
                          self.intended_distance_change, self.actual_distance_change, self.relative_direction,
                          self.mutual_direction, self.distance)

    def __repr__(self):
        return (f"TupleBlock({self.duration}, {self.intended_distance_change}, {self.actual_distance_change}, "
                f"{self.relative_direction}, {self.mutual_direction}, {self.distance})")
