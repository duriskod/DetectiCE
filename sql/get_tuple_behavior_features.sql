CREATE FUNCTION get_tuple_behavior_features(selected_camera_id integer, selected_generation integer, selected_traj_model integer)
    RETURNS TABLE(block bigint, traj_1 bigint, traj_2 bigint, block_order bigint, start_frame integer, end_frame integer, intent_dist character varying, actual_dist character varying, relative_dir character varying, mutual_dir character varying, distance character varying)
    LANGUAGE sql
AS
$$
WITH descriptor_group  AS (
    WITH filtered_tuple_descriptor AS NOT MATERIALIZED (
        SELECT tuple_descriptor.*
        FROM tuple_descriptor
             INNER JOIN traj ON traj.id = tuple_descriptor.traj_1
        WHERE traj.camera = selected_camera_id
          AND traj.traj_model = selected_traj_model
          AND tuple_descriptor.generation = selected_generation),
         intent_dist_props         AS (
             -- Filtered descriptors of property IntentDist
        SELECT traj_1, traj_2, block_order, value AS intent_dist
        FROM filtered_tuple_descriptor
        WHERE property = 'IntendedDistanceChange'),
         actual_dist_props         AS (
             -- Filtered descriptors of property ActualDist
        SELECT traj_1, traj_2, block_order, value AS actual_dist
        FROM filtered_tuple_descriptor
        WHERE property = 'ActualDistanceChange'),
         relative_dir_props        AS (
             -- Filtered descriptors of property RelativeDirection
        SELECT traj_1, traj_2, block_order, value AS relative_dir
        FROM filtered_tuple_descriptor
        WHERE property = 'RelativeDirection'),
         mutual_dir_props          AS (
             -- Filtered descriptors of property MutualDirection + all leftover columns
        SELECT id, traj_1, traj_2, block_order, value AS mutual_dir
        FROM filtered_tuple_descriptor
        WHERE property = 'MutualDirection'),
         distance_props            AS (
             -- Filtered descriptors of property Distance + all leftover columns
        SELECT id, traj_1, traj_2, block_order, value AS distance
        FROM filtered_tuple_descriptor
        WHERE property = 'Distance')
    SELECT mutual_dir_props.id,
           mutual_dir_props.traj_1,
           mutual_dir_props.traj_2,
           mutual_dir_props.block_order,
           intent_dist,
           actual_dist,
           relative_dir,
           mutual_dir,
           distance
    FROM mutual_dir_props
         INNER JOIN intent_dist_props ON
        mutual_dir_props.traj_1 = intent_dist_props.traj_1 AND
        mutual_dir_props.traj_2 = intent_dist_props.traj_2 AND
        mutual_dir_props.block_order = intent_dist_props.block_order
         INNER JOIN actual_dist_props ON
        mutual_dir_props.traj_1 = actual_dist_props.traj_1 AND
        mutual_dir_props.traj_2 = actual_dist_props.traj_2 AND
        mutual_dir_props.block_order = actual_dist_props.block_order
         INNER JOIN relative_dir_props ON
        mutual_dir_props.traj_1 = relative_dir_props.traj_1 AND
        mutual_dir_props.traj_2 = relative_dir_props.traj_2 AND
        mutual_dir_props.block_order = relative_dir_props.block_order
         INNER JOIN distance_props ON
        mutual_dir_props.traj_1 = distance_props.traj_1 AND
        mutual_dir_props.traj_2 = distance_props.traj_2 AND
        mutual_dir_props.block_order = distance_props.block_order),
     block_start_frame AS (
    SELECT DISTINCT ON (tuple_block) tuple_block,
                                     detection.frame AS start_frame
    FROM tuple_block_detection
         INNER JOIN detection
                    ON detection.id = tuple_block_detection.detection
    ORDER BY tuple_block, detection.frame),
     block_end_frame   AS (
    SELECT DISTINCT ON (tuple_block) tuple_block,
                                     detection.frame AS end_frame
    FROM tuple_block_detection
         INNER JOIN detection
                    ON detection.id = tuple_block_detection.detection
    ORDER BY tuple_block, detection.frame DESC)
SELECT block,
       traj_1,
       traj_2,
       block_order,
       start_frame,
       end_frame,
       intent_dist,
       actual_dist,
       relative_dir,
       mutual_dir,
       distance
FROM descriptor_group
     INNER JOIN tuple_block_descriptor ON descriptor_group.id = tuple_block_descriptor.tuple_descriptor
     INNER JOIN block_start_frame ON block_start_frame.tuple_block = tuple_block_descriptor.block
     INNER JOIN block_end_frame ON block_end_frame.tuple_block = tuple_block_descriptor.block;
$$;