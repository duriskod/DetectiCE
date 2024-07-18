from datetime import datetime, timedelta

from ..features import Speed, Direction
from ..single_block import SingleBlock

reference_date = datetime(2000, 1, 1)


def simple_block(start_time_offset_seconds: float, end_time_offset_seconds: float,
                 speed: Speed, direction: Direction):
    return SingleBlock(reference_date + timedelta(0, start_time_offset_seconds),
                       reference_date + timedelta(0, end_time_offset_seconds),
                       speed, direction)
