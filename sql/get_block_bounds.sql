create function get_block_bounds(traj_ids integer[])
    returns TABLE(id integer, trajectory bigint, start_frame integer, start_x integer, start_y integer, end_frame integer, end_x integer, end_y integer)
    language sql
as
$$
WITH bound_dets AS (
    SELECT block.id,
           block.trajectory,
           MIN(block_detection.detection) AS start_det,
           MAX(block_detection.detection) AS end_det
    FROM block
         INNER JOIN block_detection ON block.id = block_detection.block
    WHERE block.trajectory = ANY(traj_ids)
    GROUP BY block.id)
SELECT bound_dets.id,
       bound_dets.trajectory,
       sd.frame                 AS start_frame,
       (sd.left + sd.right) / 2 AS start_x,
       (sd.top + sd.bottom) / 2 AS start_y,
       ed.frame                 AS end_frame,
       (ed.left + ed.right) / 2 AS end_x,
       (ed.top + ed.bottom) / 2 AS end_y
FROM bound_dets
     INNER JOIN detection AS sd ON sd.id = bound_dets.start_det
     INNER JOIN detection AS ed ON ed.id = bound_dets.end_det
ORDER BY trajectory, id;
$$;