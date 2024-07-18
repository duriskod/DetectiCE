from __future__ import annotations

from typing import Callable

from .types import ContractedPathEntry

from ..data import Confidence


class TimeGraphLayer:
    name: str | None
    sublayers: list[TimeGraphLayer] | None
    """Only for debug purposes"""

    def __init__(self, name: str | None, sublayers: list[TimeGraphLayer] | None = None):
        self.name = name
        self.sublayers = sublayers

    def __call__(self, i: int, j: int) -> Confidence:
        raise "Abstract method"

    @property
    def memory(self) -> dict[tuple[int, int], Confidence]:
        raise "Abstract method"

    def __str__(self):
        return self.name or repr(self)


class ContractedTimeGraphLayer(TimeGraphLayer):
    paths: dict[tuple[int, int], ContractedPathEntry]

    def __init__(self,
                 paths: list[ContractedPathEntry],
                 name: str | None = None,
                 sublayers: list[TimeGraphLayer] | None = None):
        super().__init__(name, sublayers)
        self.paths = {(path[0], path[-1]): (path, confidence) for path, confidence in paths}

    def __call__(self, i: int, j: int) -> Confidence:
        if (i, j) not in self.paths:
            return Confidence.impartial()
        return self.paths[i, j][-1]

    @property
    def memory(self) -> dict[tuple[int, int], Confidence]:
        return {edge: conf for edge, (path, conf) in self.paths.items()}


class LambdaTimeGraphLayer(TimeGraphLayer):
    width: int

    def __init__(self,
                 weighting: Callable[[int, int], Confidence],
                 width: int, name: str | None = None,
                 sublayers: list[TimeGraphLayer] | None = None):
        super().__init__(name, sublayers)
        self.width = width
        self.weighting = weighting

    def __call__(self, i: int, j: int) -> Confidence:
        return self.weighting(i, j)

    @property
    def memory(self) -> dict[tuple[int, int], Confidence]:
        memory = {}
        for i in range(self.width):
            for j in range(i + 1, self.width + 1):
                memory[(i, j)] = self(i, j)
        return memory


class DenseTimeGraphLayer(TimeGraphLayer):
    right_edges: list[Confidence]
    bot_edges: list[Confidence] | None
    default: float
    confidences: dict[tuple[int, int], Confidence]

    def __init__(self,
                 right_edges: list[Confidence], bot_edges: list[Confidence] | None = None,
                 default: float = 0, name: str | None = None,
                 sublayers: list[TimeGraphLayer] | None = None):
        super().__init__(name, sublayers)
        self.right_edges = right_edges
        self.bot_edges = bot_edges
        self.default = default
        self.confidences = {}

    def __call__(self, i: int, j: int) -> Confidence:
        if i >= j:
            return Confidence.impossible()

        if (i, j) not in self.confidences:
            edges = self.right_edges[i:j - 1] + [
                self.bot_edges[j - 1] if self.bot_edges is not None else self.right_edges[j - 1]]

            self.confidences[i, j] = sum(edges, start=Confidence.impartial())

        return self.confidences[i, j]

    @property
    def memory(self) -> dict[tuple[int, int], Confidence]:
        for i in range(len(self.right_edges)):
            for j in range(i + 1, len(self.right_edges) + 1):
                self.confidences[(i, j)] = self(i, j)
        return self.confidences

    def __repr__(self):
        return f"DenseTimeGraphLayer({self.right_edges}, {self.bot_edges}, {self.default})"

    def __str__(self):
        bots = self.right_edges if self.bot_edges is None else self.bot_edges
        return ("".join([f"() -[{c:.2f}]->" for c, d in self.right_edges])
                + "".join([f"   \\[{c:.2f}]\\v" for c, d in bots]))
