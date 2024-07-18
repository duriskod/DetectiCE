from __future__ import annotations

from datetime import timedelta, datetime
from typing import Callable, Any

from .layer import TimeGraphLayer, ContractedTimeGraphLayer
from .types import BacktrackMap, BacktrackInfo, ContractedPathEntry, ContractedTimetableEntry

from ..configuration import Configuration
from ..data import Confidence, ConfidenceComparer


class TimeGraph:
    layers: list[TimeGraphLayer]
    width: int

    timetable: list[timedelta]
    """Of size self.width, where i-th value is accumulated duration of all blocks [0:i+1] of processed data"""
    reference_time: datetime

    max_memory: int
    min_confidence: Confidence

    comparer: ConfidenceComparer
    comparer_as_key_selector: Callable[[Any], Any]

    is_computed: bool = False
    backtrack_map: BacktrackMap = None
    contracted_layer: ContractedTimeGraphLayer = None

    name: str | None

    def __init__(self, layers: list[TimeGraphLayer], width: int,
                 comparer: ConfidenceComparer = ConfidenceComparer(Configuration.confidence_coefficient),
                 timetable: list[timedelta] | None = None,
                 reference_time: datetime | None = None,
                 name: str | None = None):
        """

        :param layers: List of computed layers of children of the calling SequentialLayer.
        :param width: Number of blocks in the processed data.
        :param comparer: Specific version of ConfidenceComparer deciding whether accuracy or reliability are preferred.
        :param timetable: List of durations of processed blocks.
        :param name: Name of the layer for debugging purposes
        """
        self.layers = layers
        self.width = width

        if timetable is None:
            self.timetable = [timedelta(i) for i in range(width + 1)]
        else:
            self.timetable = []
            acc = timedelta(0)
            for time in timetable:
                self.timetable.append(acc)
                acc += time
            self.timetable.append(acc)
        self.reference_time = reference_time

        self.min_confidence = Confidence(Configuration.min_confidence, 1.0)
        self.max_memory = Configuration.max_memory

        self.comparer = comparer
        self.comparer_as_key_selector = self.comparer.get_key_sorter(-1)

        self.name = name

    @property
    def height(self) -> int:
        return len(self.layers)

    def compute(self):
        if self.is_computed:
            return

        cmp = ConfidenceComparer.ConformityBased()
        min_confidence = Confidence(Configuration.min_confidence, 1.0)

        backtrack_map = [
            # ancestor of first layer is virtual #START node
            [[(-1, -1, Confidence.impartial())] for _ in range(self.width)],
            # ancestors of next layers are to be computed (+ #END layer)
            *[[[] for _ in range(self.width)] for _ in self.layers]
        ]

        for depth, layer in enumerate(self.layers):
            for time_start in range(self.width - 1):

                source_ancestors = backtrack_map[depth][time_start]

                for time_end in range(time_start + 1, self.width):
                    step_confidence = layer(time_start, time_end)

                    if cmp.compare_int(step_confidence, min_confidence) < 0:
                        continue

                    target_ancestors = [(time_start, idx, confidence + step_confidence)
                                        for idx, (_, _, confidence) in enumerate(source_ancestors)]

                    existing_ancestors = backtrack_map[depth + 1][time_end]
                    if existing_ancestors:
                        backtrack_map[depth + 1][time_end] = self.__merge_backtrack_info(target_ancestors,
                                                                                         existing_ancestors)
                    else:
                        backtrack_map[depth + 1][time_end] = target_ancestors

        self.is_computed = True
        self.backtrack_map = backtrack_map

    def __merge_backtrack_info(self, left: BacktrackInfo, right: BacktrackInfo) -> BacktrackInfo:
        merge: BacktrackInfo = left + right
        merge = sorted(merge, key=self.comparer_as_key_selector, reverse=True)
        merge = [(node_idx, path_idx, conf)
                 for node_idx, path_idx, conf in merge
                 if self.comparer.compare(conf, self.min_confidence) >= 0]
        return merge[:self.max_memory]

    def __backtrack_all(self, time: int, depth: int) -> list[list[int]]:
        depth = depth % len(self.backtrack_map)
        finish_node = self.backtrack_map[depth][time]
        paths = []
        for backtrack_info in finish_node:
            path = [time]
            while depth >= 0:
                node_idx = backtrack_info[0]
                path_idx = backtrack_info[1]
                depth -= 1
                backtrack_info = self.backtrack_map[depth][node_idx][path_idx]
                path.append(node_idx)
            path.reverse()
            paths.append(path)
        return paths

    def __backtrack(self, time: int, depth: int, idx: int) -> list[int]:
        depth = depth % len(self.backtrack_map)
        finish_node = self.backtrack_map[depth][time]
        backtrack_info = finish_node[idx]
        path = [time]
        while depth > 0:
            node_idx = backtrack_info[0]
            path_idx = backtrack_info[1]
            depth -= 1
            backtrack_info = self.backtrack_map[depth][node_idx][path_idx]
            path.append(node_idx)
        path.reverse()
        return path

    def __create_contracted_layer(self):
        if self.contracted_layer is not None:
            return

        contracted_edge_info: list[ContractedPathEntry] = []
        for final_time in range(self.width):
            if not self.backtrack_map[-1][final_time]:
                continue

            for nth_best in range(len(self.backtrack_map[-1][final_time])):
                _, _, confidence = self.backtrack_map[-1][final_time][nth_best]
                path = self.__backtrack(final_time, -1, nth_best)
                contracted_edge_info.append((path, confidence))

        self.contracted_layer = ContractedTimeGraphLayer(contracted_edge_info, name=self.name)

    @property
    def contracted(self) -> ContractedTimeGraphLayer:
        self.compute()
        self.__create_contracted_layer()
        return self.contracted_layer

    def path_to_time(self, path: list[int]) -> list[datetime]:
        return [self.reference_time + self.timetable[idx] for idx in path]

    def best_paths_debug(self, n: int | None = None):
        self.compute()
        self.__create_contracted_layer()
        return list(
            sorted([(self.path_to_time(path), path, conf) for path, conf in self.contracted_layer.paths.values()],
                   key=self.comparer_as_key_selector,
                   reverse=True))[:n]

    def best_paths(self, n: int | None = None) -> list[ContractedTimetableEntry]:
        self.compute()
        self.__create_contracted_layer()
        return list(
            sorted([(self.path_to_time(path), conf) for path, conf in self.contracted_layer.paths.values()],
                   key=self.comparer_as_key_selector,
                   reverse=True))[:n]
