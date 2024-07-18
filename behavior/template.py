import itertools
import math
import timeit
from datetime import timedelta, datetime

from .configuration import Configuration
from .data import (BehaviorVariable, Direction, Speed, Agent, AgentTuple, Confidence,
                   ConfidenceComparer, Block, SingleBlock, TimeFrame, cut_to_windows)
from .node import SequentialNode, BehaviorNode, optimize_node
from .time_graph import ContractedTimetableEntry


class BehaviorTemplate:
    """
    Structure holding encoded behavioral tree. Provides a set of functions for searching behavior.
    """

    root: SequentialNode
    variables: list[BehaviorVariable]

    variable_sequence: list[set[BehaviorVariable]]
    time_req_sequence: list[timedelta]

    def __init__(self, root: BehaviorNode):
        root = BehaviorTemplate.optimize_tree(root)
        self.root = root

        sequence_info = self.root.get_sequence_info(default_min=timedelta(seconds=3))
        self.variable_sequence, self.time_req_sequence = zip(*sequence_info)

        variables = set()
        for child_vars in self.variable_sequence:
            variables = variables.union(child_vars)
        self.variables = list(variables)

    @staticmethod
    def optimize_tree(root: BehaviorNode) -> SequentialNode:
        # Root must be sequential
        if not isinstance(root, SequentialNode):
            root = SequentialNode(root)

        root = optimize_node(root)

        if not isinstance(root, SequentialNode):
            raise "Won't happen"

        return root

    def search(self,
               agents: dict[int, Agent],
               agent_tuples: dict[(int, int), AgentTuple],
               max_results: int = 100) -> list[tuple[tuple[int, ...], list[datetime], Confidence]]:
        """
        Complete search of encoded behavior on a set of provided agents and their agent tuples.
        :param agents: Dictionary of all Agents to search through
        :param agent_tuples: Dictionary of all AgentTuples to search through
        :param max_results: Maximum number of final results.
        :return: List of potential matches in form of tuples:
        - tuple of agent IDs in order they were mapped to variables
        - list of timestamps where each chronologically successive sub-behavior started
        - final confidence for the whole match
        """
        print(f"Template.search({len(agents)} agents, {len(agent_tuples)} agent_tuples)")

        confidence_comparer_as_key_selector = Configuration.comparer.get_key_sorter(-1)

        best_found_paths: list[tuple[tuple[int, ...], list[datetime], Confidence]] = []

        # region Progress info
        start_time = timeit.default_timer()
        perm_percent = 0
        eval_counter = 0
        skip_viability_counter = 0
        processed_time_counter = timedelta(0)
        cutoff_time_counter = timedelta(0)
        perm_counter = 0
        # endregion

        if self.root.is_symmetrical(set(self.variables)):
            agent_selections = itertools.combinations(agents.values(), len(self.variables))
            perm_count = math.comb(len(agents.values()), len(self.variables))
            # print("Template is symmetrical.")
        else:
            agent_selections = itertools.permutations(agents.values(), len(self.variables))
            perm_count = math.perm(len(agents.values()), len(self.variables))
            # print("Template is not symmetrical.")

        for agent_selection in agent_selections:

            # region Progress info
            perm_counter += 1
            new_perm_percent = (perm_counter * 100) // perm_count
            if new_perm_percent > perm_percent:
                perm_percent = new_perm_percent

                temp_time = timeit.default_timer()
                exact_percent = perm_counter / perm_count
                eta = (temp_time - start_time) / exact_percent
                print(f"{new_perm_percent}% est. runtime {temp_time - start_time:.1f}/{eta:.1f} seconds")
                print(f"    best running result: {best_found_paths[0][-1] if len(best_found_paths) > 0 else "None"}")
            # endregion

            agent_selection_ids = [agent.agent_id for agent in agent_selection]

            agent_tuple_selection = [agent_tuples[actor.agent_id, target.agent_id]
                                     for actor, target
                                     in itertools.permutations(agent_selection, 2)
                                     if (actor.agent_id, target.agent_id) in agent_tuples]

            is_viable, viability_start_time, viability_stop_time = self.check_viability(list(agent_selection))
            if not is_viable:
                skip_viability_counter += 1
                continue

            eval_counter += 1
            selection_start = min([agent.blocks[0].start_time for agent in agent_selection if len(agent.blocks) > 0])
            selection_end = max([agent.blocks[-1].end_time for agent in agent_selection if len(agent.blocks) > 0])
            processed_time_counter += selection_end - selection_start
            cutoff_time_counter += selection_end - viability_stop_time
            cutoff_time_counter += viability_start_time - selection_start

            best_paths = self.process([agent.during_time(TimeFrame(viability_start_time, viability_stop_time))
                                       for agent in agent_selection],
                                      [agent_tuple.during_time(TimeFrame(viability_start_time, viability_stop_time))
                                       for agent_tuple in agent_tuple_selection])

            best_found_paths += [(agent_selection_ids, timestamp_path, conf)
                                 for timestamp_path, conf
                                 in best_paths]

            best_found_paths = list(sorted(best_found_paths,
                                           key=confidence_comparer_as_key_selector,
                                           reverse=True))[:max_results]

        print()
        print("Total considered agent variations:", perm_counter)
        print("Total non-viable agent variations:", skip_viability_counter)
        print("Total evaluated agent variations: ", eval_counter)
        print()
        print("Total processed time saved via viability checks: ", cutoff_time_counter, "/", processed_time_counter, "s")

        return [fp for fp in best_found_paths if fp[-1].denom != float('inf')]

    def check_viability(self, agents: list[Agent]) -> tuple[True, datetime, datetime] | tuple[False, None, None]:
        """
        Check whether provided set of agents is viable, by checking whether agents have sufficient presence
        with regards to their required presence as defined by the behavioral pattern structure.
        :param agents: Set of agents mapped to template's behavioral variables.
        :return: True if tuple of agents is viable and should be processed.
        False if tuple can be safely discarded.
        """

        current_sequential_idx = 0
        current_variables = self.variable_sequence[current_sequential_idx]
        current_variable_indexes = [self.variables.index(var) for var in current_variables]
        sequential_time_left = self.time_req_sequence[current_sequential_idx]

        windows = list(
            Block.granulate(
                *[[SingleBlock(agent.blocks[0].start_time, agent.blocks[-1].end_time,
                               Speed.STAND, Direction.NOT_MOVING)] for agent in agents],
                strip_incomplete=False, max_window_size=timedelta.max)
        )

        current_window_idx = 0
        current_window, (current_window_start, current_window_end) = windows[current_window_idx]
        window_time_left = current_window_end - current_window_start

        is_viable = None
        while True:
            # Window must contain all current variables
            if any(current_window[i] is None for i in current_variable_indexes):
                # print(f"Seq {current_sequential_idx} does not fit win {current_window_idx} ({[self.variables[i].name if block is not None else "-" for i, block in enumerate(current_window)]})")
                # reset sequence
                sequential_time_left = self.time_req_sequence[current_sequential_idx]

                # go to next window
                current_window_idx += 1
                if current_window_idx >= len(windows):
                    # print("Win exhausted, NON-VIABLE")
                    is_viable = False
                    break

                current_window, (current_window_start, current_window_end) = windows[current_window_idx]
                window_time_left = current_window_end - current_window_start

                continue

            shift_sequence = sequential_time_left <= window_time_left
            shift_window = sequential_time_left >= window_time_left

            if shift_sequence:
                # print(f"Seq {current_sequential_idx} satisfied in win {current_window_idx} ({[self.variables[i].name if block is not None else "-" for i, block in enumerate(current_window)]}), {window_time_left} win time left")
                window_time_left -= sequential_time_left

                # go to next sequence
                current_sequential_idx += 1
                if current_sequential_idx >= len(self.variable_sequence):
                    # print("Seq exhausted, VIABLE")
                    is_viable = True
                    break

                current_variables = self.variable_sequence[current_sequential_idx]
                current_variable_indexes = [self.variables.index(var) for var in current_variables]
                sequential_time_left = self.time_req_sequence[current_sequential_idx]

            if shift_window:
                sequential_time_left -= window_time_left
                # print(f"Win {current_window_idx} exhausted, {sequential_time_left} seq left")

                # go to next window
                current_window_idx += 1
                if current_window_idx >= len(windows):
                    # print("Win exhausted, NON-VIABLE")
                    is_viable = False
                    break

                current_window, (current_window_start, current_window_end) = windows[current_window_idx]
                window_time_left = current_window_end - current_window_start

        if not is_viable:
            return False, None, None

        if is_viable:
            # Since we know template can potentially fit AND we ignore gaps in trajectories
            # we can find first block where first sequence fits, and call it the potential start
            first_var_seq = self.variable_sequence[0]
            first_var_seq_idxs = [self.variables.index(var) for var in first_var_seq]
            first_potential_time = None
            for blocks, time_frame in windows:
                is_window_viable_start = True
                for idx in first_var_seq_idxs:
                    if not blocks[idx]:
                        is_window_viable_start = False

                if is_window_viable_start:
                    first_potential_time = time_frame[0]
                    break

            # same for end
            last_var_seq = self.variable_sequence[-1]
            last_var_seq_idxs = [self.variables.index(var) for var in last_var_seq]
            last_potential_time = None
            for blocks, time_frame in windows[::-1]:
                is_window_viable_end = True
                for idx in last_var_seq_idxs:
                    if not blocks[idx]:
                        is_window_viable_end = False

                if is_window_viable_end:
                    last_potential_time = time_frame[1]
                    break

            return True, first_potential_time, last_potential_time

    def process(self, agents: list[Agent], agent_tuples: list[AgentTuple]) -> list[ContractedTimetableEntry]:
        """
        Process a specific tuple of agents and their agent tuples using internal behavioral tree.
        :param agents: Set of agents to be checked, mapped to template's variables in the order they are defined.
        :param agent_tuples: Set of agent tuples for agents.
        :return: Found path with the best possible confidence.
        """
        windows = cut_to_windows(agents, agent_tuples)
        graph = self.root.compute_graph(self.variables, windows)

        return graph.best_paths(1)

    def __repr__(self):
        return f"BehaviorTemplate({repr(self.root)})"
