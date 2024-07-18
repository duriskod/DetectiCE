CREATE FUNCTION get_behavior_features(selected_camera_id integer, selected_generation integer, selected_traj_model integer)
    RETURNS TABLE(block bigint, trajectory bigint, start_frame integer, end_frame integer, speed character varying, direction character varying)
    LANGUAGE sql
AS
$$
    WITH frame_det_block_data  AS (
        WITH start_dets AS (
            -- extract minimal frames & detections per block
            SELECT DISTINCT ON (block) block,
                                       detection.id,
                                       detection.frame
            FROM block_detection
                 INNER JOIN detection
                            ON block_detection.detection = detection.id
            ORDER BY block, detection.frame),
             end_dets   AS (
                 -- extract maximal frames & detections per block
            SELECT DISTINCT ON (block) block,
                                       detection.id,
                                       detection.frame
            FROM block_detection
                 INNER JOIN detection
                            ON block_detection.detection = detection.id
            ORDER BY block, detection.frame DESC)
        SELECT start_dets.block AS block,
               start_dets.frame AS start_frame,
               end_dets.frame   AS end_frame
        FROM start_dets
             INNER JOIN end_dets
                        ON start_dets.block = end_dets.block),
         descriptor_block_data AS (
        WITH blocked_descriptor AS (
            WITH filtered_descriptor AS (
                SELECT descriptor.*,
                       traj.camera
                FROM descriptor
                     INNER JOIN traj
                                ON descriptor.trajectory = traj.id
                WHERE traj.camera = selected_camera_id
                  AND traj_model = selected_traj_model)
            -- label descriptors with block IDs
            SELECT *
            FROM block_descriptor
                 INNER JOIN filtered_descriptor
                            ON block_descriptor.descriptor = filtered_descriptor.id
            WHERE filtered_descriptor.generation = selected_generation)
        -- conjoin Speed and Direction descriptors into single record
        SELECT bd1.block      AS block,
               bd1.trajectory AS trajectory,
               bd1.value      AS speed,
               bd2.value      AS direction
        FROM blocked_descriptor AS bd1
             INNER JOIN blocked_descriptor AS bd2
                        ON bd1.block = bd2.block
        WHERE bd1.property = 'Speed'
          AND bd2.property = 'Direction'
          AND bd1.generation = selected_generation)
    SELECT dbd.block        AS block,
           dbd.trajectory   AS trajectory,
           fdbd.start_frame AS start_frame,
           fdbd.end_frame   AS end_frame,
           dbd.speed        AS speed,
           dbd.direction    AS direction
    FROM descriptor_block_data AS dbd
         INNER JOIN frame_det_block_data AS fdbd
                    ON dbd.block = fdbd.block;
$$;
