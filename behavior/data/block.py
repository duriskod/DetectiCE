from __future__ import annotations

from datetime import datetime, timedelta
from typing import Generator


class Block:
    """
    Base class of blocks for semantic representations. Bounded by start and end time.
    """

    start_time: datetime
    end_time: datetime

    def __init__(self, start_time: datetime, end_time: datetime):
        self.start_time = start_time
        self.end_time = end_time

    @property
    def duration(self) -> timedelta:
        return self.end_time - self.start_time

    def during_time(self, from_time: datetime | None = None, to_time: datetime | None = None) -> Block:
        assert from_time is None or to_time is None or from_time <= to_time
        assert to_time is None or self.start_time <= to_time
        assert from_time is None or from_time <= self.end_time

        if not to_time:
            to_time = self.end_time
        else:
            to_time = min(to_time, self.end_time)

        if not from_time:
            from_time = self.start_time
        else:
            from_time = max(from_time, self.start_time)

        return Block(from_time, to_time)

    def granulated(self, step_time: float | timedelta = timedelta(seconds=1)) -> list[Block]:
        if step_time == float('inf') or step_time == timedelta.max:
            step_time = None
        if isinstance(step_time, float) or isinstance(step_time, int):
            step_time = timedelta(seconds=step_time)

        granules: list[Block] = []
        start_time = self.start_time
        bound_time = start_time + step_time if step_time is not None else datetime.max

        while bound_time < self.end_time:
            granules.append(self.during_time(start_time, bound_time))
            start_time = bound_time
            bound_time = start_time + step_time
        if start_time < self.end_time:
            granules.append(self.during_time(start_time, self.end_time))
        return granules

    @staticmethod
    def granulate(*block_groups: list["Block"], strip_incomplete: bool = True,
                  max_window_size: timedelta = timedelta(seconds=1)) \
            -> Generator[tuple[list["Block"], tuple[datetime, datetime]], None, None]:
        """
        Generate granulated sliding windows for provided lists of blocks. Generated windows will contain time-aligned
        subsections of blocks for each of the block groups, or None if block group has no spanning block in the
        specific time frame.
        :param block_groups: Lists of chronologically ordered blocks. Each window will contain at most one section of
        one block for each of the block group.
        :param strip_incomplete: If set to true, all windows which contain None will be skipped.
        :param max_window_size: Maximal size of each window in seconds. If a window exceeds this threshold, it will be
        subdivided into windows of max_window_size size, with the last window being at most max_window_size seconds.
        :return: Generator yielding tuples containing the window (list of blocks and Nones of length equal to that of
        block_groups), and tuple of date-times specifying the start and end datetime of the yielded window.
        """

        # indexes of blocks we are working with
        block_section_idxs = [0 for _ in block_groups]
        # references to blocks we are working with
        block_section: list[Block | None] = [bg[0] if len(bg) > 0 else None for bg in block_groups]
        # absolute start time of passed trajectories
        start_time = min(block.start_time for block in block_section if block is not None)
        # absolute end time of passed trajectories
        end_time = max(block_group[-1].end_time for block_group in block_groups if len(block_group) > 0 and block_group[-1] is not None)

        # time bounds that will define the next yielded time window

        # INV: everything before left_bound_time was yielded
        left_bound_time = start_time
        # needs to be determined as the minimal of all potential bounds in block section
        # - for blocks that started before (or at) left_bound_time - their end_time
        # - for blocks that will start after left_bound_time - their start_time
        right_bound_time = end_time

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
                        exhausted_block_idxs = [i]
                # first block in agent that is not the earliest
                else:
                    if right_bound_time > block.start_time:
                        right_bound_time = block.start_time
                        exhausted_block_idxs = []
                    else:
                        pass

            if right_bound_time - left_bound_time > max_window_size:
                right_bound_time = left_bound_time + max_window_size
                exhausted_block_idxs = []

            sliding_window = [block.during_time(left_bound_time, right_bound_time)
                              if block is not None and block.start_time < right_bound_time
                              else None
                              for block in block_section]
            # print(f"Sliding window with {sum([x is not None for x in sliding_window])} values from {left_bound_time} to {right_bound_time}")
            if left_bound_time + timedelta(seconds=0.2) >= right_bound_time:
                pass  # print("LBT >= RBT")
            elif all([b is None for b in sliding_window]):
                pass  # print("Window empty", right_bound_time - left_bound_time)
            elif strip_incomplete and None in sliding_window:
                pass
            else:
                yield sliding_window, (left_bound_time, right_bound_time)

            for block_idx in exhausted_block_idxs:
                next_block_idx = block_section_idxs[block_idx] + 1
                block_section_idxs[block_idx] += 1
                if next_block_idx >= len(block_groups[block_idx]):
                    block_section[block_idx] = None
                else:
                    block_section[block_idx] = block_groups[block_idx][next_block_idx]

            left_bound_time = right_bound_time
            right_bound_time = end_time
