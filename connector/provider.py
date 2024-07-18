from collections import defaultdict
from datetime import timedelta

from behavior import Agent, AgentTuple, cut_to_windows
from connector.loader import DbBehaviorLoader


class BehaviorProvider:
    """
    Class responsible for easy access to video data. Contains sets of presets, which take care of configuring
    and constructing BehaviorLoader.
    """

    agents: dict[int, Agent]
    agent_tuples: dict[(int, int), AgentTuple]

    loader: DbBehaviorLoader

    @staticmethod
    def from_db(camera: int, generation: int, model: int):
        loader = DbBehaviorLoader(camera, generation, model)
        return BehaviorProvider.__from_behavior_loader(loader)

    @staticmethod
    def from_db_rvacka_pravo():
        return BehaviorProvider.from_db(920, 9, 2259)

    @staticmethod
    def from_db_kradez_stred():
        return BehaviorProvider.from_db(921, 3, 2198)

    @staticmethod
    def from_db_rvacka_stred():
        return BehaviorProvider.from_db(922, 3, 2198)

    @staticmethod
    def from_db_kradez_pravo():
        return BehaviorProvider.from_db(928, 3, 2286)

    @staticmethod
    def __from_behavior_loader(loader: DbBehaviorLoader):
        provider = BehaviorProvider()

        blocks = loader.blocks
        blocks_by_traj = defaultdict(list)
        for record in blocks:
            blocks_by_traj[record['trajectory']].append(record)
        provider.agents = {
            key: Agent.from_block_data(key, val)
            for key, val
            in blocks_by_traj.items()}

        tuple_blocks = loader.tuple_blocks
        tuple_blocks_by_traj = defaultdict(list)
        for record in tuple_blocks:
            key = (record['traj_1'], record['traj_2'])
            tuple_blocks_by_traj[key].append(record)
        provider.agent_tuples = {
            (actor_id, target_id): AgentTuple.from_block_data(provider.agents[actor_id],
                                                              provider.agents[target_id],
                                                              tuple_block_data)
            for (actor_id, target_id), tuple_block_data
            in tuple_blocks_by_traj.items()}

        # To use in fixing inconsistent data
        provider.loader = loader

        return provider

    def sanity_check(self, frame_epsilon: float = 0.2):
        epsilon = timedelta(seconds=frame_epsilon)
        print("Agent sanity check...")
        for agent in self.agents.values():
            total_gap = timedelta(0)
            total_overstep = timedelta(0)
            total_used_time = timedelta(0)
            # print(f"Agent {agent.agent_id} ({agent.blocks[0].start_time} - {agent.blocks[-1].end_time})")
            last_bound_time = agent.blocks[0].start_time
            for block in agent.blocks:
                total_used_time += block.duration

                if last_bound_time + epsilon < block.start_time:
                    print(f".. Agent {agent.agent_id} empty gap {(block.start_time - last_bound_time).total_seconds()}")
                    total_gap += block.start_time - last_bound_time
                elif block.start_time + epsilon < last_bound_time:
                    print(f".. Agent {agent.agent_id} over step {(last_bound_time - block.start_time).total_seconds()}")
                    total_overstep += last_bound_time - block.start_time

                last_bound_time = block.end_time
            if total_gap > timedelta(0) or total_overstep > timedelta(0):
                print(f"Agent {agent.agent_id} stats -- total gap: {total_gap.total_seconds()}, total overstep: {total_overstep.total_seconds()}, total used time: {total_used_time.total_seconds()}")

        print("Agent tuple sanity check...")
        for actor in self.agents.values():
            for target in self.agents.values():
                # print(f"Actor-target {actor.agent_id} {target.agent_id} ({agent.blocks[0].start_time} - {agent.blocks[-1].end_time})")
                actor_target = self.agent_tuples.get((actor.agent_id, target.agent_id), None)
                target_actor = self.agent_tuples.get((target.agent_id, actor.agent_id), None)

                windows = cut_to_windows([actor, target], [at for at in [actor_target, target_actor] if at is not None], max_window_size=timedelta.max)

                for (actor_block, target_block), tuple_block_map, duration in windows:
                    both_agents_defined = actor_block is not None and target_block is not None
                    actor_target_defined = tuple_block_map[0][1] is not None
                    target_actor_defined = tuple_block_map[1][0] is not None

                    if not both_agents_defined and not actor_target_defined and not target_actor_defined:
                        print(f".. Tuple {actor.agent_id} {target.agent_id} empty window -- {duration}")
                    if both_agents_defined and not actor_target_defined:
                        print(f".. Tuple {actor.agent_id} {target.agent_id} undefined actor-target block")
                        print(f"   ({actor_block.start_time} - {actor_block.end_time}) -- {duration}")
                    if both_agents_defined and not target_actor_defined:
                        print(f".. Tuple {actor.agent_id} {target.agent_id} undefined target-actor block")
                        print(f"   ({actor_block.start_time} - {actor_block.end_time}) -- {duration}")
                    if not both_agents_defined and actor_target_defined:
                        print(f".. Tuple {actor.agent_id} {target.agent_id} missing either block but have actor-target block")
                        print(f"   ({tuple_block_map[0][1].start_time} - {tuple_block_map[0][1].end_time}) -- {duration}")
                    if not both_agents_defined and target_actor_defined:
                        print(f".. Tuple {actor.agent_id} {target.agent_id} missing either block but have actor-target block")
                        print(f"   ({tuple_block_map[1][0].start_time} - {tuple_block_map[1][0].end_time}) -- {duration}")
