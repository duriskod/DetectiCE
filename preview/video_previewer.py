import colorsys
import random
import sys
from datetime import datetime
from enum import Enum

import cv2

from behavior import Direction, Speed, MutualDirection, DistanceChange, Distance, Agent, AgentTuple

distinct_colors_count = 20
distinct_colors = []
for i in range(distinct_colors_count):
    hsv = (i / distinct_colors_count, 1, 1)
    rgb = colorsys.hsv_to_rgb(*hsv)
    distinct_colors.append(tuple(round(c * 255) for c in rgb))


def generate_random_rgb():
    return random.choice(distinct_colors)


feature_labels = {
    Direction.NOT_MOVING: 'x',
    Direction.STRAIGHT: '^',
    Direction.LEFT: '<',
    Direction.RIGHT: '>',
    Direction.OPPOSITE: 'v',

    Speed.STAND: 'Stand',
    Speed.WALK: 'Walk',
    Speed.RUN: 'Run',

    MutualDirection.PARALLEL: 'Par',
    MutualDirection.INDEPENDENT: 'Ind',
    MutualDirection.OPPOSITE: 'Opp',

    DistanceChange.INCREASING: 'Dist +',
    DistanceChange.CONSTANT: 'Dist =',
    DistanceChange.DECREASING: 'Dist -',

    Distance.ADJACENT: 'Adj',
    Distance.NEAR: 'Near',
    Distance.FAR: 'Far'

}


class TrajInfoMode(Enum):
    Hidden = 0
    Textless = 1
    Simple = 2
    All = 3


class TrajectoryConfig:
    agent_id: int

    agent_label: str | None

    position_info: dict[int, tuple[int, int, datetime, int, int, int, int, int, int, int, int]]
    """seq_num -> (X, Y, timestamp)"""

    last_position_seq_num: int
    """seq_num"""
    last_position_info: tuple[int, int, datetime, int, int, int, int, int, int, int, int] | None
    """(X, Y, timestamp)"""

    position_cache_timeout: int = 30

    agent_data: Agent

    tuple_agent_by_target: dict[int, AgentTuple]

    behavior_info: list[[datetime, str]]

    color: tuple[int, int, int]

    previewer: 'VideoPreviewer'

    def __init__(self,
                 agent_id: int,
                 position_info: dict[int, tuple[int, int, datetime, int, int, int, int, int, int, int, int]],
                 agent_data: Agent,
                 tuple_agent_by_target: dict[int, AgentTuple],
                 behavior_info: list[[datetime, str]],
                 agent_label: str | None = None,
                 interpolate_position_info: bool = True):
        self.agent_id = agent_id
        self.agent_label = agent_label
        self.agent_data = agent_data
        self.tuple_agent_by_target = tuple_agent_by_target
        self.behavior_info = behavior_info
        self.color = generate_random_rgb()

        self.last_position_seq_num = 0
        self.last_position_info = None

        self.position_info = position_info

    def get_position_info(self, seq_num: int) -> tuple[int, int, datetime, int, int, int, int] | None:
        # Reset (i.e., when rewinding vid to start)
        if seq_num < self.last_position_seq_num:
            self.last_position_info = None
            self.last_position_seq_num = 0
            return None

        position_info = self.position_info.get(seq_num, None)

        if position_info is None:
            # Is cache valid?
            if seq_num - self.last_position_seq_num > self.position_cache_timeout:
                return None

            return self.last_position_info
        else:
            self.last_position_seq_num = seq_num
            self.last_position_info = position_info
            return position_info

    def draw(self, frame, seq_num: int, base_pos: tuple[int, int], info_mode: TrajInfoMode = TrajInfoMode.Hidden) \
            -> tuple[int, int] | None:
        if info_mode == TrajInfoMode.Hidden:
            return None

        position_info = self.get_position_info(seq_num)
        if position_info is None:
            return None

        final_width = 0
        final_height = 0

        temp_pos = base_pos

        x, y, timestamp, sx, sy, ex, ey, psx, psy, nex, ney = position_info

        traj_pos = (x, y)
        prev_block_start_pos = (psx, psy)
        block_start_pos = (sx, sy)
        block_end_pos = (ex, ey)
        next_block_end_pos = (nex, ney)

        # Traj circle
        cv2.circle(frame, traj_pos, 10, self.color, -1)

        if info_mode == TrajInfoMode.Textless:
            return None

        cv2.circle(frame, prev_block_start_pos, 4, self.color, 2)
        cv2.circle(frame, block_start_pos, 6, self.color, 2)
        cv2.circle(frame, block_end_pos, 6, self.color, -1)
        cv2.circle(frame, next_block_end_pos, 4, self.color, -1)
        cv2.line(frame, prev_block_start_pos, block_start_pos, self.color, 2)
        cv2.line(frame, block_start_pos, block_end_pos, self.color, 2)
        cv2.line(frame, block_end_pos, next_block_end_pos, self.color, 2)

        # Traj ID
        agent_label_width, agent_label_height = put_text_with_background(frame, str(self.agent_label or self.agent_id),
                                                                         temp_pos, self.color)
        temp_pos = (temp_pos[0], temp_pos[1] + agent_label_height)
        final_height += agent_label_height
        final_width = max(final_width, agent_label_width)

        # Line
        cv2.line(frame, traj_pos, (base_pos[0], base_pos[1] + 90), self.color, 2)

        # Behavior
        behavior_idx = 0
        behavior_end, behavior_label = self.behavior_info[0]
        while behavior_end < timestamp:
            if behavior_idx >= len(self.behavior_info) - 1:
                behavior_label = "END"
                break
            behavior_idx += 1
            behavior_end, behavior_label = self.behavior_info[behavior_idx]

        if behavior_label:
            b_label_width, b_label_height = put_text_with_background(frame, behavior_label, temp_pos, self.color)
            temp_pos = (temp_pos[0], temp_pos[1] + b_label_height)
            final_height += b_label_height
            final_width = max(final_width, b_label_width)

        agent_info = self.agent_data.at_time(timestamp)
        agent_info_width, agent_info_height = put_text_with_background(
            frame,
            f"{feature_labels[agent_info.speed]}, {feature_labels[agent_info.direction]}",
            temp_pos, self.color
        )
        temp_pos = (temp_pos[0], temp_pos[1] + agent_info_height)
        final_height += agent_info_height
        final_width = max(final_width, agent_info_width)

        if info_mode != TrajInfoMode.All:
            return final_width, final_height

        for target_id, tuple_agent in self.tuple_agent_by_target.items():
            tuple_block = tuple_agent.at_time(timestamp)
            if tuple_block is None:
                continue

            target_info = self.previewer.get_traj_info(target_id)
            target_label = target_info.agent_label or target_info.agent_id
            target_color = target_info.color

            mutual_text = (f"<> {target_label}: {feature_labels[tuple_block.actual_distance_change]}, "
                           f"{feature_labels[tuple_block.mutual_direction]}, {tuple_block.distance.value[0:3]}")
            mut_text_width, mut_text_height = put_text_with_background(frame, mutual_text, temp_pos, target_color,
                                                                       font_scale=1, font_thickness=2, padding=(2, 2))
            temp_pos = (temp_pos[0], temp_pos[1] + mut_text_height)
            final_height += mut_text_height
            final_width = max(final_width, mut_text_width)

            actor_target_text = (f"-> {target_label}: {feature_labels[tuple_block.intended_distance_change]}, "
                                 f"{feature_labels[tuple_block.relative_direction]}")
            at_text_width, at_text_height = put_text_with_background(frame, actor_target_text, temp_pos, target_color,
                                                                     font_scale=1, font_thickness=2, padding=(2, 2))
            temp_pos = (temp_pos[0], temp_pos[1] + at_text_height)
            final_height += at_text_height
            final_width = max(final_width, at_text_width)

        return final_width, final_height


class VideoPreviewer:
    scale: float
    video_name: str
    cap: cv2.VideoCapture
    fps: int

    first_seq_num: int
    last_seq_num: int

    traj_info: dict[int, TrajectoryConfig]
    traj_info_shown: TrajInfoMode = TrajInfoMode.All

    def __init__(self, video_name, scale=0.7):
        self.video_name = video_name
        self.scale = scale

    def set_clip(self, start_frame, end_frame):
        self.first_seq_num = start_frame
        self.last_seq_num = end_frame

    def set_traj_info(self, traj_configs: list[TrajectoryConfig]):
        self.traj_info = {tinfo.agent_id: tinfo for tinfo in traj_configs}

        for info in self.traj_info.values():
            info.previewer = self

    def get_traj_info(self, traj_id: int) -> TrajectoryConfig:
        return self.traj_info[traj_id]

    @property
    def agent_ids(self):
        return tuple(self.traj_info.keys())

    def play(self):
        self.cap = cv2.VideoCapture(self.video_name)
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))

        if self.cap.isOpened():
            self._play_video_frames()
        else:
            raise "Can't open video."

    def _play_video_frames(self):

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.first_seq_num)
        while self.cap.get(cv2.CAP_PROP_POS_FRAMES) <= self.last_seq_num:
            success, frame = self.cap.read()
            if not success:
                print("Can't read frame.")
                break

            frame_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            height, width, layers = frame.shape

            # Frame info
            frame_label_text = f"{self.first_seq_num} / {frame_idx} / {self.last_seq_num}"
            put_text_with_background(frame, frame_label_text, (20, 20))

            base_pos = (width - 250, 20)
            for info in self.traj_info.values():
                size = info.draw(frame, frame_idx, base_pos, info_mode=self.traj_info_shown)
                if size is not None:
                    base_pos = (base_pos[0], base_pos[1] + size[1])
                if base_pos[1] >= 0.5 * height:
                    base_pos = (base_pos[0] - 250, 20)

            rescaled_frame = cv2.resize(frame, (int(width * self.scale), int(height * self.scale)))
            cv2.imshow(self.video_name, rescaled_frame)

            key_press = cv2.waitKeyEx(self.fps)
            if key_press >= 0:
                print("Press", hex(key_press))

            if key_press == ord('n'):
                # skip to next result
                break
            elif key_press == ord('q'):
                # quit
                sys.exit(0)
            elif key_press == ord(' '):
                # cv2.waitKey(0)
                while cv2.waitKey(0) != ord(' '):
                    continue
            elif key_press == 0x9:
                self.traj_info_shown = TrajInfoMode((self.traj_info_shown.value + 1) % len(TrajInfoMode))
                print("TrajInfoMode", self.traj_info_shown)
            elif key_press == 0x250000 or key_press == ord('a'):
                # Rewind 5sec
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx - 5 * self.fps)
            elif key_press == ord('A'):
                # Rewind to start
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.first_seq_num)
            elif key_press == 0x270000 or key_press == ord('d'):
                # Fast-forward 5sec
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx + 5 * self.fps)
            elif key_press == ord('D'):
                # Fast-forward 30sec
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx + 30 * self.fps)

        self.cap.release()
        cv2.destroyAllWindows()


def put_text_with_background(frame,
                             text,
                             position,
                             text_color=(255, 255, 255),
                             background_color=(0, 0, 0),
                             font=cv2.FONT_HERSHEY_PLAIN,
                             font_scale=2,
                             font_thickness=2,
                             padding=(10, 10)) -> tuple[int, int]:
    text_size, baseline = cv2.getTextSize(text, font, font_scale, font_thickness)
    cv2.rectangle(
        frame,
        (position[0], position[1]),
        (position[0] + text_size[0] + 2 * padding[0], position[1] + text_size[1] + 2 * padding[1]),
        background_color,
        -1
    )
    cv2.putText(
        frame,
        text,
        (position[0] + padding[0], position[1] + text_size[1] + padding[1] + font_scale - 1),
        font,
        font_scale,
        text_color,
        font_thickness
    )
    return text_size[0] + 2 * padding[0], text_size[1] + 2 * padding[1]
