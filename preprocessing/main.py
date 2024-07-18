import logging
from datetime import timedelta

from connector.loader import try_connect
from behavior import MutualDirection, DistanceChange, Direction, Distance
from preprocessing.connector.data_provider import DataBehaviorProvider
from preprocessing.data.data_block import DataBlock

# input config
CAMERA = 920
DESCRIPTOR_GENERATION = 1
MODEL = 2259

# processing config
DISTANCE_CHANGE_THRESHOLD = 0.35
DIRECTION_DEGREES_THRESHOLD = 30
PHYSICAL_DISTANCE_THRESHOLD = 0.75
TALK_DISTANCE_THRESHOLD = 1.5

logging.root.setLevel(logging.NOTSET)

DB_STORE = True


def as_actual_distance_category(distance: float) -> DistanceChange:
    if distance >= DISTANCE_CHANGE_THRESHOLD:
        return DistanceChange.INCREASING
    elif distance >= -DISTANCE_CHANGE_THRESHOLD:
        return DistanceChange.CONSTANT
    else:
        return DistanceChange.DECREASING


def as_intent_distance_category(distance: float) -> DistanceChange:
    if distance >= DISTANCE_CHANGE_THRESHOLD:
        return DistanceChange.INCREASING
    elif distance >= -DISTANCE_CHANGE_THRESHOLD:
        return DistanceChange.CONSTANT
    else:
        return DistanceChange.DECREASING


def as_relative_direction_category(degrees: float) -> Direction:
    degrees %= 360
    if 0 <= degrees <= DIRECTION_DEGREES_THRESHOLD or 360 - DIRECTION_DEGREES_THRESHOLD <= degrees <= 360:
        return Direction.STRAIGHT
    elif 180 - DIRECTION_DEGREES_THRESHOLD <= degrees <= 180 + DIRECTION_DEGREES_THRESHOLD:
        return Direction.OPPOSITE
    elif 180 + DIRECTION_DEGREES_THRESHOLD < degrees:
        return Direction.LEFT
    else:
        return Direction.RIGHT


def as_mutual_direction_category(degrees: float) -> MutualDirection:
    degrees %= 360
    if 0 <= degrees <= DIRECTION_DEGREES_THRESHOLD or 360 - DIRECTION_DEGREES_THRESHOLD <= degrees <= 360:
        return MutualDirection.PARALLEL
    elif 180 - DIRECTION_DEGREES_THRESHOLD <= degrees <= 180 + DIRECTION_DEGREES_THRESHOLD:
        return MutualDirection.OPPOSITE
    else:
        return MutualDirection.INDEPENDENT


def as_distance_category(distance: float) -> Distance:
    if distance <= PHYSICAL_DISTANCE_THRESHOLD:
        return Distance.ADJACENT
    elif PHYSICAL_DISTANCE_THRESHOLD < distance <= TALK_DISTANCE_THRESHOLD:
        return Distance.NEAR
    else:
        return Distance.FAR


class ActorTargetFeatures:
    actor_id: int
    target_id: int

    block_order: int

    intended_distance_change: DistanceChange
    actual_distance_change: DistanceChange
    relative_direction: Direction
    mutual_direction: MutualDirection
    distance: Distance

    start_frame: int
    end_frame: int

    def __eq__(self, other):
        if isinstance(other, ActorTargetFeatures):
            return (self.intended_distance_change == other.intended_distance_change and
                    self.actual_distance_change == other.actual_distance_change and
                    self.relative_direction == other.relative_direction and
                    self.mutual_direction == other.mutual_direction and
                    self.distance == other.distance)
        return False

    def __str__(self):
        return f"""
        ActorTargetFeatures:
        - actor_id: {self.actor_id}
        - target_id: {self.target_id}
        - block_order: {self.block_order}
        - intended_distance_change: {self.intended_distance_change}
        - actual_distance_change: {self.actual_distance_change}
        - relative_direction: {self.relative_direction}
        - mutual_direction: {self.mutual_direction}
        - distance: {self.distance}
        """


def send_data(cursor, tuple_info: ActorTargetFeatures):
    # print("Send ", tuple_info)

    cursor.execute(
        f"insert into tuple_descriptor "
        f"  (traj_1, traj_2, block_order, generation, property, value) "
        f"values "
        f"  ({tuple_info.actor_id}, {tuple_info.target_id}, {tuple_info.block_order}, {DESCRIPTOR_GENERATION}, 'IntendedDistanceChange', '{tuple_info.intended_distance_change.value}'), "
        f"  ({tuple_info.actor_id}, {tuple_info.target_id}, {tuple_info.block_order}, {DESCRIPTOR_GENERATION}, 'ActualDistanceChange', '{tuple_info.actual_distance_change.value}'), "
        f"  ({tuple_info.actor_id}, {tuple_info.target_id}, {tuple_info.block_order}, {DESCRIPTOR_GENERATION}, 'RelativeDirection', '{tuple_info.relative_direction.value}'), "
        f"  ({tuple_info.actor_id}, {tuple_info.target_id}, {tuple_info.block_order}, {DESCRIPTOR_GENERATION}, 'MutualDirection', '{tuple_info.mutual_direction.value}'), "
        f"  ({tuple_info.actor_id}, {tuple_info.target_id}, {tuple_info.block_order}, {DESCRIPTOR_GENERATION}, 'Distance', '{tuple_info.distance.value}') "
        f"on conflict do nothing "
        f"returning id;"
    )
    tuple_descriptor_ids = cursor.fetchmany(4)
    cursor.execute(
        f"insert into tuple_block "
        f"  (traj_1, traj_2, block_order, generation) "
        f"values "
        f"  ({tuple_info.actor_id}, {tuple_info.target_id}, {tuple_info.block_order}, {DESCRIPTOR_GENERATION}) "
        f"returning id;"
    )

    tuple_block_id = cursor.fetchone()[0]
    cursor.execute(
        f"insert into tuple_block_detection "
        f"  (tuple_block, detection, source_table, source_trajectory_role) "
        f"select "
        f"  {tuple_block_id} as tuple_block, "
        f"  detection.id as detection, "
        f"  'DETECTION' as source_table, "
        f"  'actor' as source_trajectory_role "
        f"from detection "
        f"  inner join traj_detection on "
        f"    detection.id = traj_detection.detection "
        f"where traj_detection.traj = {tuple_info.actor_id}"
        f"  and frame between {tuple_info.start_frame} and {tuple_info.end_frame}"
    )
    cursor.execute(
        f"insert into tuple_block_detection "
        f"  (tuple_block, detection, source_table, source_trajectory_role) "
        f"select "
        f"  {tuple_block_id} as tuple_block, "
        f"  detection.id as detection, "
        f"  'DETECTION' as source_table, "
        f"  'target' as source_trajectory_role "
        f"from detection "
        f"  inner join traj_detection on "
        f"    detection.id = traj_detection.detection "
        f"where traj_detection.traj = {tuple_info.target_id}"
        f"  and frame between {tuple_info.start_frame} and {tuple_info.end_frame}"
    )
    cursor.execute(
        f"insert into tuple_block_descriptor "
        f"  (tuple_descriptor, block) "
        f"values "
        f"  ({tuple_descriptor_ids[0][0]}, {tuple_block_id}), "
        f"  ({tuple_descriptor_ids[1][0]}, {tuple_block_id}), "
        f"  ({tuple_descriptor_ids[2][0]}, {tuple_block_id}), "
        f"  ({tuple_descriptor_ids[3][0]}, {tuple_block_id});"
    )


if __name__ == "__main__":
    provider = None
    connection = None
    cursor = None
    try:
        connection = try_connect()
        cursor = connection.cursor()

        provider = DataBehaviorProvider.from_db(connection, CAMERA, DESCRIPTOR_GENERATION, MODEL)
        assert provider is not None

        for i, actor in enumerate(provider.agents.values()):
            logging.info(f"Progress: {int(100 * i / len(provider.agents))}% ({i}/{len(provider.agents)})")

            for j, target in enumerate(provider.agents.values()):
                if actor is target:
                    continue

                block_counter = 0
                previous_tuple_info = None
                current_tuple_info = None

                for block_section in DataBlock.granulate(actor.blocks, target.blocks, strip_incomplete=True, max_window_size=timedelta(seconds=0.5)):

                    actor_block, target_block = block_section[0], block_section[1]
                    block_section_duration = (actor_block.end_frame - actor_block.start_frame) / provider.fps
                    size_factor = (max(actor_block.width, actor_block.height) + max(target_block.width, target_block.height)) / 2

                    current_tuple_info = ActorTargetFeatures()
                    current_tuple_info.start_frame = actor_block.start_frame
                    current_tuple_info.end_frame = actor_block.end_frame
                    current_tuple_info.actor_id = actor.agent_id
                    current_tuple_info.target_id = target.agent_id
                    current_tuple_info.block_order = block_counter

                    distance_px = (target_block.end - actor_block.end).magnitude
                    current_tuple_info.distance = as_distance_category(distance_px / size_factor)
                    # ("Distance") Binary - distance between two agents

                    intent_end_dist_px = (target_block.start - actor_block.end)
                    intent_start_dist_px = (target_block.start - actor_block.start)
                    intent_dist_px = intent_end_dist_px.magnitude - intent_start_dist_px.magnitude
                    current_tuple_info.intended_distance_change = as_intent_distance_category(
                        (intent_dist_px / size_factor) / block_section_duration
                    )
                    # ("IntendedDistanceChange") Binary - change of distance w.r.t last position of other agent

                    actual_end_dist_px = (target_block.end - actor_block.end)
                    actual_start_dist_px = (target_block.start - actor_block.start)
                    actual_dist_px = actual_end_dist_px.magnitude - actual_start_dist_px.magnitude
                    current_tuple_info.actual_distance_change = as_actual_distance_category(
                        (actual_dist_px / size_factor) / block_section_duration
                    )
                    # ("ActualDistanceChange") Binary - change of distance between both agents

                    actor_movement_angle = (actor_block.end - actor_block.start).angle_degrees
                    actor_target_angle = (target_block.start - actor_block.start).angle_degrees
                    actor_relative_angle = actor_target_angle - actor_movement_angle
                    current_tuple_info.relative_direction = as_relative_direction_category(actor_relative_angle)
                    # ("RelativeDirection") Binary - direction of movement w.r.t. second agent

                    target_movement_angle = (target_block.end - target_block.start).angle_degrees
                    mutual_angle = target_movement_angle - actor_movement_angle
                    current_tuple_info.mutual_direction = as_mutual_direction_category(mutual_angle)
                    # ("MutualDirection") Binary - relation of directions of both agents

                    if previous_tuple_info is None:
                        previous_tuple_info = current_tuple_info
                        block_counter += 1
                    elif previous_tuple_info == current_tuple_info:
                        # print("TB Merge", previous_tuple_info.end_frame - previous_tuple_info.start_frame, " + ", current_tuple_info.end_frame - current_tuple_info.start_frame)
                        previous_tuple_info.end_frame = current_tuple_info.end_frame
                    else:
                        # print("TB Push ", previous_tuple_info.end_frame - previous_tuple_info.start_frame)
                        if DB_STORE:
                            send_data(cursor, previous_tuple_info)

                        previous_tuple_info = current_tuple_info
                        block_counter += 1

                if DB_STORE and previous_tuple_info is not None:
                    send_data(cursor, previous_tuple_info)

        if DB_STORE:
            connection.commit()
            logging.debug("Changes committed")
    finally:
        if connection is not None:
            cursor.close()
            logging.debug("Cursor closed")

            connection.close()
            print("Connection closed")


