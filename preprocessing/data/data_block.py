from datetime import datetime, timedelta
from typing import Generator

from behavior import Speed, Direction, SingleBlock
from preprocessing.data.vector import Vector2


class DataBlock(SingleBlock):
    id: int

    start_frame: int
    end_frame: int

    start_time: datetime
    end_time: datetime

    start: Vector2
    end: Vector2

    speed: Speed
    direction: Direction

    width: float
    height: float

    def __init__(self,
                 start_frame: int, start_time: datetime, start: Vector2,
                 end_frame: int, end_time: datetime, end: Vector2,
                 speed: Speed, direction: Direction,
                 width: float, height: float):
        super().__init__(start_time, end_time,
                         speed, direction)

        assert start_frame is not None
        assert end_frame is not None

        self.start_frame = start_frame
        self.start_time = start_time
        self.start = start
        self.end_frame = end_frame
        self.end_time = end_time
        self.end = end
        self.speed = speed
        self.direction = direction
        self.width = width
        self.height = height

    @staticmethod
    def from_block_data(block_data: dict):
        block = DataBlock(block_data['start_frame'], block_data['start_time'],
                          Vector2(block_data['start_x'], block_data['start_y']),
                          block_data['end_frame'], block_data['end_time'],
                          Vector2(block_data['end_x'], block_data['end_y']),
                          block_data['speed_type'], block_data['direction_type'],
                          block_data['width'], block_data['height'])
        block.id = block_data['block']
        return block

    @property
    def delta(self):
        return self.end - self.start

    def pos_at_time(self, time: datetime) -> Vector2:
        assert self.start_time <= time <= self.end_time

        time_offset = (time - self.start_time).total_seconds()
        fraction = time_offset / self.duration.total_seconds()
        return self.start + self.delta * fraction

    def during_time_and_frame(self,
                              from_time: datetime, to_time: datetime,
                              from_frame: int | None = None, to_frame: int | None = None):
        assert from_time <= to_time
        assert self.start_time <= to_time
        assert from_time <= self.end_time

        to_time = min(to_time, self.end_time)
        from_time = max(from_time, self.start_time)

        from_pos = self.pos_at_time(from_time)
        to_pos = self.pos_at_time(to_time)
        block = DataBlock(
            from_frame, from_time, from_pos,
            to_frame, to_time, to_pos,
            self.speed, self.direction,
            self.width, self.height
        )

        if from_frame is not None:
            block.start_frame = from_frame
        if to_frame is not None:
            block.end_frame = to_frame

        return block

    @staticmethod
    def granulate(*block_groups: list["DataBlock"], strip_incomplete: bool = True,
                  max_window_size: timedelta = timedelta(seconds=1)) \
            -> Generator[list["DataBlock"], None, None]:

        # indexes of blocks we are working with
        block_section_idxs = [0 for _ in block_groups]
        # references to blocks we are working with
        block_section: list = [bg[0] for bg in block_groups]
        # absolute start time of passed trajectories
        start_time = min(block.start_time for block in block_section)
        start_frame = min(block.start_frame for block in block_section)
        # absolute end time of passed trajectories
        end_time = max(block_group[-1].end_time for block_group in block_groups)
        end_frame = max(block_group[-1].end_frame for block_group in block_groups)

        # time bounds that will define the next yielded time window

        # INV: everything before left_bound_time was yielded
        left_bound_time = start_time
        left_bound_frame = start_frame
        # needs to be determined as the minimal of all potential bounds in block section
        # - for blocks that started before (or at) left_bound_time - their end_time
        # - for blocks that will start after left_bound_time - their start_time
        right_bound_time = end_time
        right_bound_frame = end_frame

        exhausted_block_idxs = []
        while left_bound_time < end_time:
            for i, block in enumerate(block_section):
                if block is None:
                    continue
                # inside block
                if block.start_time <= left_bound_time:
                    if right_bound_time < block.end_time:
                        pass
                    elif right_bound_time == block.end_time:
                        exhausted_block_idxs.append(i)
                    elif right_bound_time > block.end_time:
                        right_bound_time = block.end_time
                        right_bound_frame = block.end_frame
                        exhausted_block_idxs = [i]
                # first block in agent that is not the earliest
                else:
                    if right_bound_time > block.start_time:
                        right_bound_time = block.start_time
                        right_bound_frame = block.start_frame
                        exhausted_block_idxs = []
                    else:
                        pass

            if right_bound_time - left_bound_time > max_window_size:
                right_bound_time = left_bound_time + max_window_size
                right_bound_frame = left_bound_frame + int(max_window_size.total_seconds() * 30.03)
                exhausted_block_idxs = []

            sliding_window = [block.during_time_and_frame(left_bound_time, right_bound_time, left_bound_frame, right_bound_frame)
                              if block is not None and block.start_time < right_bound_time
                              else None
                              for block in block_section]
            if strip_incomplete and None in sliding_window:
                pass
            else:
                yield sliding_window

            for block_idx in exhausted_block_idxs:
                next_block_idx = block_section_idxs[block_idx] + 1
                block_section_idxs[block_idx] += 1
                if next_block_idx >= len(block_groups[block_idx]):
                    block_section[block_idx] = None
                else:
                    block_section[block_idx] = block_groups[block_idx][next_block_idx]

            left_bound_time = right_bound_time
            left_bound_frame = right_bound_frame
            right_bound_time = end_time
            right_bound_frame = end_frame

    def __eq__(self, other: "DataBlock"):
        if not isinstance(other, DataBlock):
            return False
        return self.start_time == other.start_time \
            and self.end_time == other.end_time \
            and self.start == other.start \
            and self.end == other.end \
            and self.speed == other.speed \
            and self.direction == other.direction

    def __str__(self):
        return f"[({self.start.x}, {self.start.y}) @ {self.start_time.time()}]-[({self.end.x}, {self.end.y} @ {self.end_time.time()})]"

    def __repr__(self):
        return f"Block({self.start_time}, {self.start}, {self.end_time}, {self.end}, {self.speed}, {self.direction})"
