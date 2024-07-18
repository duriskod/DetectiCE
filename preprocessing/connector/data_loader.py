from datetime import datetime, timedelta

from psycopg2.extras import RealDictCursor

from behavior import Speed, Direction


class DataBehaviorLoader:
    def __init__(self, connection, camera, generation, model):
        self.connection = connection
        self.camera = camera
        self.generation = generation
        self.model = model
        self._preload()

    def get_time(self, frame: int) -> datetime:
        return self.start_time + timedelta(seconds=(frame - self.start_frame) / self.fps)

    def data(self):
        for row in self.data_cursor:
            row['start_time'] = self.get_time(row['start_frame'])
            row['end_time'] = self.get_time(row['end_frame'])
            row['speed_type'] = Speed(row['speed'])
            row['direction_type'] = Direction(row['direction'])
            yield row

    def _preload(self):
        # load behavior data
        self.data_cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        self.data_cursor.execute(f"select * from get_behavior_data({self.camera}, {self.generation}, {self.model})")

        # load camera info (fps, width, height)
        self.camera_cursor = self.connection.cursor()
        self.camera_cursor.execute(f"select fps, w, h from camera where id = {self.camera}")
        camera_data = list(self.camera_cursor)
        assert len(camera_data) == 1
        self.fps, self.w, self.h = camera_data[0]

        # load camera frame to timestamp mapping
        self.timestamp_cursor = self.connection.cursor()
        self.timestamp_cursor.execute(
            f"select id, timestamp from frame where camera = {self.camera} and sequence_number = 0")
        timestamp_data = list(self.timestamp_cursor)
        assert len(timestamp_data) == 1
        # i.e., 2022-06-03 20:12:38.882490
        self.start_frame = timestamp_data[0][0]
        self.start_time = timestamp_data[0][1]
