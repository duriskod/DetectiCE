import argparse
import csv
import os
import pickle
import sys
from datetime import datetime
from random import sample

from behavior import (BehaviorTemplate, AgentTuple, Agent, Confidence, parse_behavior, Configuration as BehaviorConfig,
                      ConfidenceConjunctionStrategy)
from connector.provider import BehaviorProvider
from connector.loader import DbBehaviorLoader
from preview.video_previewer import VideoPreviewer, TrajectoryConfig


def file_path_to_name(file_path):
    return '.'.join(file_path.split('/')[-1].split('.')[:-1])


def read_query(file_path: str) -> BehaviorTemplate:
    query_lines = []
    with open(file_path, 'r') as query_file:
        for line in query_file:
            if line.startswith('#'):
                continue
            else:
                query_lines.append(line)
    query = " ".join(query_lines)

    template = BehaviorTemplate(parse_behavior(query))
    template.root.name = file_path_to_name(file_path)
    return template


def save_paths(file_path: str,
               template: BehaviorTemplate,
               paths: list[tuple[tuple[int, ...], list[datetime], Confidence]],
               create_path: bool = False):
    # if not paths:
    #     return

    if create_path:
        directory_path = os.path.dirname(file_path)
        os.makedirs(directory_path, exist_ok=True)

    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        agent_names = [f"Agent {var.name}" for var in template.variables]
        action_names = [f"Node {child}" for child in template.root.children]
        header = [*agent_names, *action_names, "Behavior end", "Confidence nom", "Confidence denom"]
        writer.writerow(header)

        for path in paths:
            agent_ids, timestamps, confidence = path
            row = [*agent_ids, *[time.strftime("%Y-%m-%d %H:%M:%S.%f") for time in timestamps],
                   confidence.nom, confidence.denom]
            writer.writerow(row)


def read_paths(file_path: str) \
        -> tuple[list[tuple[tuple[int, ...], list[datetime], Confidence]], list[str], list[str]]:
    with open(file_path, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)

        results: list[tuple[tuple[int, ...], list[datetime], Confidence]] = []

        header = next(reader)
        agent_labels = [item[len("Agent "):] for item in header if item.startswith("Agent")]
        agent_count = len(agent_labels)
        node_labels = [item[len("Node "):] for item in header if item.startswith("Node")]
        node_count = len(node_labels)

        for row in reader:
            agent_ids = [int(item) for item in row[:agent_count]]
            timestamps = [datetime.strptime(item, '%Y-%m-%d %H:%M:%S.%f') for item in
                          row[agent_count:agent_count + node_count + 1]]
            confidence = Confidence(float(row[-2]), float(row[-1]))
            results.append((tuple(agent_ids), timestamps, confidence))

        return results, agent_labels, node_labels


def preview(agents: dict[int, Agent],
            agent_tuples: dict[tuple[int, int], AgentTuple],
            best_paths: list[tuple[tuple[int, ...], list[datetime], Confidence]],
            video_file_name: str,
            agent_labels: list[str],
            node_labels: list[str],
            loader: DbBehaviorLoader):
    previewer = VideoPreviewer(video_file_name)

    if not best_paths:
        print("Behavior not found.")
        return

    for agent_ids, tuple_best_path, _ in best_paths:
        start_time = tuple_best_path[0]
        end_time = tuple_best_path[-1]

        pos_info_by_seq_num = loader.get_normalized_traj_points(agent_ids, start_time, end_time)
        pos_info_by_agent: dict[int, dict[int, tuple[int, int, datetime, int, int, int, int, int, int, int, int]]] = \
            {agent_id: {} for agent_id in agent_ids}
        for seq_num, position_info in pos_info_by_seq_num.items():
            for agent_id, x, y, time, sx, sy, ex, ey, psx, psy, nex, ney in position_info:
                pos_info_by_agent[agent_id][seq_num] = (x, y, time, sx, sy, ex, ey, psx, psy, nex, ney)

        behavior_info = [[start_time, "START"]]
        for i, time in enumerate(tuple_best_path[1:]):
            behavior_name = str(node_labels[i])
            behavior_info.append([time, behavior_name])

        previewer.set_traj_info([TrajectoryConfig(agent_id,
                                                  pos_info_by_agent[agent_id],
                                                  agents[agent_id],
                                                  {target: agent_tuples[actor, target]
                                                   for (actor, target), agent_tuple
                                                   in agent_tuples.items()
                                                   if actor == agent_id and target in agent_ids},
                                                  behavior_info,
                                                  agent_labels[i])
                                 for i, agent_id
                                 in enumerate(agent_ids)])

        start_seq_num = min(pos_info_by_seq_num.keys())
        end_seq_num = max(pos_info_by_seq_num.keys())
        previewer.set_clip(start_seq_num, end_seq_num)
        print(f"Play {start_time} - {end_time}")
        for traj_config in previewer.traj_info.values():
            if not traj_config.position_info:
                print(f"No position info for {traj_config.agent_id}")
                continue

            traj_start_time = traj_config.position_info[min(traj_config.position_info.keys())][-1]
            traj_end_time = traj_config.position_info[max(traj_config.position_info.keys())][-1]
            print(f"Trajectory {traj_config.agent_id}: {traj_start_time} - {traj_end_time}")
        previewer.play()


def preview_all(agents: dict[int, Agent],
                tuple_agents: dict[tuple[int, int], AgentTuple],
                video_file_name: str,
                loader: DbBehaviorLoader):
    previewer = VideoPreviewer(video_file_name)

    agent_ids = agents.keys()
    start_time = min(loader.inv_timestamp_dict.keys())
    end_time = max(loader.inv_timestamp_dict.keys())
    pos_info_by_seq_num = loader.get_normalized_traj_points(tuple(agent_ids), start_time, end_time)
    pos_info_by_agent: dict[int, dict[int, tuple[int, int, datetime, int, int, int, int, int, int, int, int]]] = \
        {agent_id: {} for agent_id in agent_ids}
    for seq_num, position_info in pos_info_by_seq_num.items():
        for agent_id, x, y, time, sx, sy, ex, ey, psx, psy, nex, ney in position_info:
            pos_info_by_agent[agent_id][seq_num] = (x, y, time, sx, sy, ex, ey, psx, psy, nex, ney)

    start_seq_num = min(pos_info_by_seq_num.keys())
    end_seq_num = max(pos_info_by_seq_num.keys())

    previewer.set_traj_info([TrajectoryConfig(agent_id,
                                              pos_info_by_agent[agent_id],
                                              agents[agent_id],
                                              {target: agent_tuples[actor, target]
                                               for (actor, target), agent_tuple
                                               in agent_tuples.items()
                                               if actor == agent_id and target in agent_ids},
                                              [(datetime.max, "")])
                             for agent_id
                             in agent_ids])

    previewer.set_clip(start_seq_num, end_seq_num)
    previewer.play()


def get_sample_agents(sample_size: int,
                      agents: dict[int, Agent],
                      agent_tuples: dict[tuple[int, int], AgentTuple]) \
        -> tuple[dict[int, Agent], dict[tuple[int, int], AgentTuple]]:
    sample_agents = sample(list(agents.values()), sample_size)
    sample_agent_tuples = [agent_tuples[actor.agent_id, target.agent_id]
                           for actor in sample_agents
                           for target in sample_agents
                           if (actor.agent_id, target.agent_id) in agent_tuples]
    return (
        {a.agent_id: a for a in sample_agents},
        {(at.actor.agent_id, at.target.agent_id): at for at in sample_agent_tuples}
    )


def get_sample_agents_old(sample_size: int,
                          agents: dict[int, Agent],
                          agent_tuples: dict[tuple[int, int], AgentTuple]) \
        -> tuple[dict[int, Agent], dict[tuple[int, int], AgentTuple]]:
    sample_agent_tuples_idxs: list[AgentTuple] = sample(list(agent_tuples.values()), sample_size)
    sample_agent_tuples = {
        (at.actor.agent_id, at.target.agent_id):
            at for at in sample_agent_tuples_idxs}

    sample_agent_ids = (set([x.actor.agent_id for x in sample_agent_tuples_idxs]).union(
        set([x.target.agent_id for x in sample_agent_tuples_idxs])))
    sample_agents = {agent.agent_id: agent for agent in agents.values() if agent.agent_id in sample_agent_ids}

    return sample_agents, sample_agent_tuples


def get_fixed_agents(agent_ids: list[int],
                     agents: dict[int, Agent],
                     agent_tuples: dict[tuple[int, int], AgentTuple]) \
        -> tuple[dict[int, Agent], dict[tuple[int, int], AgentTuple]]:
    fixed_agents = {aid: agents[aid] for aid in agent_ids}
    fixed_agent_tuples = {(actor, target): agent_tuples[actor, target]
                          for actor in agent_ids
                          for target in agent_ids
                          if actor != target
                          and (actor, target) in agent_tuples}
    return fixed_agents, fixed_agent_tuples


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--preset', choices=[
        'rvacka_pravo',
        'rvacka_stred',
        'kradez_pravo',
        'kradez_stred'
    ], required=True)

    parser.add_argument('--preview', action='store_true', help="Only preview agents and their features.")

    parser.add_argument('-C', '--compute_only', action='store_true', help="If set, previews won't start at the end of the run.")
    parser.add_argument('-L', '--force_load', action='store_true', help="Delete cached data, load new data from DB.")
    parser.add_argument('-S', '--force_search', action='store_true', help="Delete cached results, run query search.")

    parser.add_argument('-k', '--confidence_coefficient', type=float, default=None, help="Convex parameter t for RC-comparer of confidences.")
    parser.add_argument('-c', '--min_confidence', type=float, default=None, help="Minimal threshold for confidence. Any intermediate confidence below this threshold will be removed from further processing.")
    parser.add_argument('-m', '--max_memory', type=int, default=None, help="Maximal size of memory stack for each node in time graph.")
    parser.add_argument('--and_strategy', choices=['avg', 'min'], default=None, help="Strategy used for conjunction of confidences.")

    parser.add_argument('-r', '--results_path', type=str, default=None, help="Path where results are saved/loaded. Defaults to ./results/<preset>/<query_file.name>.csv")
    parser.add_argument('-v', '--video_path', type=str, default=None, help="Path where video is stored. Defaults to ./videos/<preset>.mp4")
    parser.add_argument('query_path', nargs='?', default=None, help='Path to text file with query to search.')

    args = parser.parse_args()

    # Apply configuration
    BehaviorConfig.min_confidence = args.min_confidence or BehaviorConfig.min_confidence
    BehaviorConfig.max_memory = args.max_memory or BehaviorConfig.max_memory
    BehaviorConfig.confidence_coefficient = args.confidence_coefficient or BehaviorConfig.confidence_coefficient
    if args.and_strategy:
        if args.and_strategy == 'avg':
            BehaviorConfig.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.AVG
        if args.and_strategy == 'min':
            BehaviorConfig.confidence_conjunction_strategy = ConfidenceConjunctionStrategy.MIN

    # Run config
    preset_name = args.preset

    query_name = None if args.query_path is None else file_path_to_name(args.query_path)

    results_path = args.results_path or f'results/{preset_name}/{query_name}.csv'
    results_exist = os.path.isfile(results_path)

    # Video DB data
    video_name = args.video_path or f'videos/{preset_name}.mp4'
    pickle_path = f'pickles/{preset_name}.pickle'
    if not os.path.isfile(pickle_path) or args.force_load:
        provider = getattr(BehaviorProvider, f'from_db_{preset_name}')()
        directory_path = os.path.dirname(pickle_path)
        os.makedirs(directory_path, exist_ok=True)
        with open(pickle_path, "wb") as f:
            pickle.dump(provider, f)
    else:
        with open(pickle_path, "rb") as f:
            provider = pickle.load(f)

    print("Data loaded")
    print("Data size")
    print("Blocks", sys.getsizeof(provider.agents), "bytes")
    print("Tuple blocks", sys.getsizeof(provider.agent_tuples), "bytes")

    print("Agents", len(provider.agents))
    print("Agent tuples", len(provider.agent_tuples))

    agents, agent_tuples = provider.agents, provider.agent_tuples
    # agents = {aid: a for aid, a in agents.items() if aid in friend_catching_up_match}

    # MODE: PREVIEW ALL
    if args.preview:
        preview_all(agents, agent_tuples, video_name, provider.loader)
        exit(0)

    # MODE: SHOW RESULTS
    if results_exist and not args.force_search:
        best_paths, agent_labels, node_labels = read_paths(results_path)
        preview(agents, agent_tuples, best_paths, video_name, agent_labels, node_labels, loader=provider.loader)
        exit(0)

    # MODE: SEARCH RESULTS
    if args.query_path is None:
        raise Exception("No query provided and results file does not exist or is not defined.")

    template = read_query(args.query_path)

    if template is None:
        raise Exception("Template is undefined. Either query is not provided or results file is invalid.")

    best_paths = template.search(agents, agent_tuples)
    save_paths(results_path, template, best_paths, args.results_path is None)

    agent_labels = [f"{var.name}" for var in template.variables]
    node_labels = [f"{child}" for child in template.root.children]
    if not args.compute_only:
        preview(agents, agent_tuples, best_paths, video_name, agent_labels, node_labels, loader=provider.loader)
