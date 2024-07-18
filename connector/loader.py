import bisect
from collections import defaultdict
from typing import Callable

import psycopg2
from psycopg2.extras import RealDictCursor, RealDictRow
from datetime import datetime, timedelta

from scipy import stats

from behavior import Speed, Direction, DistanceChange, MutualDirection, Distance


def try_connect():
    connection = psycopg2.connect(
        dbname="DB_CONNECTION_HERE",
        user="DB_CONNECTION_HERE",
        password="DB_CONNECTION_HERE",
        host="DB_CONNECTION_HERE",
        port="DB_CONNECTION_HERE"
    )
    print("connection initiated")
    return connection


class DbBehaviorLoader:
    """
    Class responsible for loading video data from the database.
    """

    camera: int
    generation: int
    traj_model: int

    get_connection: Callable

    blocks: list[RealDictRow]
    tuple_blocks: list[RealDictRow]

    raw_timestamp_dict: dict[int, datetime]
    timestamp_dict: dict[int, datetime]
    inv_timestamp_dict: dict[datetime, int]

    def __init__(self, camera: int, generation: int, traj_model: int, get_connection=try_connect):
        """
        :param camera: Camera ID, look up in videolyticsdb.camera (filters videolyticsdb.traj)
        :param generation: Block descriptor generation, look up in videolytics.descriptor_generation
        (filters videolyticsdb.descriptor)
        :param traj_model: Trajectory generation model, look up videolyticsdb.traj_model (filters videolyticsdb.traj)
        """
        self.camera = camera
        self.generation = generation
        self.traj_model = traj_model
        self.get_connection = get_connection

        self.blocks = []
        self.tuple_blocks = []
        self.__query_video_info()

    def __query_video_info(self):
        connection = None
        try:
            connection = self.get_connection()

            # load camera info (fps, width, height)
            camera_cursor = connection.cursor()
            camera_cursor.execute(f"select fps, w, h from camera where id = {self.camera}")
            camera_data = list(camera_cursor)
            assert len(camera_data) == 1
            self.fps, self.w, self.h = camera_data[0]

            # load camera frame to timestamp mapping
            # timestamp mapping is terrible for some videos - fix via linear regression
            timestamp_cursor = connection.cursor()
            timestamp_cursor.execute(
                f"select id, timestamp from frame where camera = {self.camera}")
            timestamp_mapping = timestamp_cursor.fetchall()
            x = [int(seqnum) for seqnum, _ in timestamp_mapping]
            y = [(timestamp - datetime(1970, 1, 1)).total_seconds() for _, timestamp in timestamp_mapping]

            slope, intercept, r, p, std_err = stats.linregress(x, y)

            self.raw_timestamp_dict = {int(seqnum): timestamp for seqnum, timestamp in timestamp_mapping}
            self.timestamp_dict = {seqnum: datetime(1970, 1, 1) + timedelta(seconds=slope * seqnum + intercept)
                                   for seqnum in x}
            self.inv_timestamp_dict = {v: k for k, v in self.timestamp_dict.items()}

            # load blocks
            block_cursor = connection.cursor(cursor_factory=RealDictCursor)
            block_cursor.execute(
                f"select * from get_behavior_features({self.camera}, {self.generation}, {self.traj_model})")
            for row in block_cursor:
                row['start_time'] = self.get_time(row['start_frame'])
                row['end_time'] = self.get_time(row['end_frame'])
                row['speed_type'] = Speed(row['speed'])
                row['direction_type'] = Direction(row['direction'])
                self.blocks.append(row)

            # load tuple blocks
            tuple_block_cursor = connection.cursor(cursor_factory=RealDictCursor)
            tuple_block_cursor.execute(
                f"select * from get_tuple_behavior_features({self.camera}, {self.generation}, {self.traj_model})")
            for row in tuple_block_cursor:
                row['start_time'] = self.get_time(row['start_frame'])
                row['end_time'] = self.get_time(row['end_frame'])
                row['intent_dist'] = DistanceChange(row['intent_dist'])
                row['actual_dist'] = DistanceChange(row['actual_dist'])
                row['relative_dir'] = Direction(row['relative_dir'])
                row['mutual_dir'] = MutualDirection(row['mutual_dir'])
                row['distance'] = Distance(row['distance'])
                self.tuple_blocks.append(row)
        finally:
            if connection is not None:
                connection.close()
                print("Connection closed")

    def get_time(self, frame: int) -> datetime:
        return self.timestamp_dict[frame]

    def get_normalized_traj_points(self, traj_ids: tuple, start_time: datetime, end_time: datetime) -> dict[
        int, list[tuple[int, int, int, datetime, int, int, int, int, int, int, int, int]]]:
        info: dict[int, list[tuple[int, int, int, datetime, int, int, int, int, int, int, int, int]]] = defaultdict(
            list)

        if start_time not in self.inv_timestamp_dict or end_time not in self.inv_timestamp_dict:
            # raise "Invalid start time or end time"
            def closest_date(target_date, date_list):
                return min(date_list, key=lambda d: abs(target_date - d))

            start_time = closest_date(start_time, self.inv_timestamp_dict.keys())
            end_time = closest_date(end_time, self.inv_timestamp_dict.keys())

        start_frame = self.inv_timestamp_dict[start_time]
        end_frame = self.inv_timestamp_dict[end_time]

        connection = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                f"select traj_detection.traj, frame.id, frame.sequence_number, "
                f"(detection.left + detection.right)/2 AS x, (detection.top + detection.bottom)/2 AS y "
                f"from traj_detection "
                f"inner join detection on detection.id = traj_detection.detection "
                f"inner join frame on detection.frame = frame.id "
                f"where frame.id between '{start_frame}' and '{end_frame}' "
                f"and traj_detection.traj in {tuple(traj_ids)} "
                f"order by frame.sequence_number "
            )
            pos_info = list(cursor)

            cursor.execute(f"select * from get_block_bounds(ARRAY{list(traj_ids)})")
            block_info = list(cursor)
            block_info_by_traj = defaultdict(list)
            for row in block_info:
                block_info_by_traj[row['trajectory']].append(row)

            for row in pos_info:
                block_pos_info_idx = bisect.bisect_right(block_info_by_traj[row['traj']], row['id'],
                                                         key=lambda row: row['start_frame']) - 1
                prev_block_pos_info = block_info_by_traj[row['traj']][
                    block_pos_info_idx - 1] if block_pos_info_idx > 0 else None
                block_pos_info = block_info_by_traj[row['traj']][block_pos_info_idx]
                next_block_pos_info = block_info_by_traj[row['traj']][block_pos_info_idx + 1] if len(
                    block_info_by_traj[row['traj']]) > block_pos_info_idx + 1 else None

                psx, psy = (prev_block_pos_info['start_x'],
                            prev_block_pos_info['start_y']) if prev_block_pos_info is not None else (None, None)
                sx, sy, ex, ey = block_pos_info['start_x'], block_pos_info['start_y'], block_pos_info['end_x'], \
                    block_pos_info['end_y']
                nex, ney = (
                    next_block_pos_info['end_x'],
                    next_block_pos_info['end_y']) if next_block_pos_info is not None else (
                    None, None)
                info[row["sequence_number"]].append((
                    row["traj"],
                    row["x"], row["y"],
                    self.get_time(int(row["id"])),
                    sx, sy, ex, ey,
                    psx, psy,
                    nex, ney
                ))
        finally:
            if connection is not None:
                print("Connection closed")
                connection.close()
        return info
