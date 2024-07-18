from __future__ import annotations

import collections
import math
from enum import Enum
from functools import cmp_to_key
from operator import itemgetter
from typing import Callable, Any


class ConfidenceCategory(Enum):
    IMPOSSIBLE = 1
    """ 0 / inf """
    IMPROBABLE = 2
    """ 0 / C """
    IMPARTIAL = 3
    """ 0 / 0 """
    UNCERTAIN = 4
    """ C / C + D """
    CERTAIN = 5
    """ C / C """
    ABSOLUTE = 6
    """ inf / inf """


class Confidence(collections.namedtuple('Confidence', ['nom', 'denom'])):
    """
    2-tuple structure specifying the confidence level. Conceptually, a fraction of (self.nom/self.denom).
    """

    __slots__ = ()

    def __float__(self):
        if self.nom == float('inf') and self.denom == float('inf'):
            return 1.0
        return self.nom / self.denom

    def __add__(self, other: Confidence) -> Confidence:
        return Confidence(self.nom + other.nom, self.denom + other.denom)

    def __mul__(self, other: float) -> Confidence:
        return Confidence(self.nom * other, self.denom * other)

    def __repr__(self):
        return f"Confidence({self.nom}, {self.denom})"

    def __str__(self):
        return f"Confidence({self.nom:.2f}/{self.denom:.2f})"

    @staticmethod
    def impossible():
        return Confidence(0.0, float('inf'))

    @staticmethod
    def impartial():
        return Confidence(0.0, 0.0)

    @staticmethod
    def certain(amount: float):
        return Confidence(amount, amount)

    @staticmethod
    def absolute():
        return Confidence(float('inf'), float('inf'))


class ConfidenceComparer:
    """
    Configurable comparer instance used to create an absolute ordering of confidences.
    It is parametrized by parameter t (between 0 and 1).
    - t = 0 corresponds to fully confidence-based (i.e., accuracy) comparison.
    - t = 1 corresponds to fully reliability-based (i.e., nominator) comparison.
    """
    def __init__(self, param: float):
        self.param = param

    def compare(self, c1: Confidence, c2: Confidence) -> float:
        """
        Compare two confidences, returning their compared difference.
        :return: Value between -1 and 1 specifying the "amount" of difference between compared confidences,
        with -1 signifying c1 is infinitely smaller than c2 and vice versa.
        """
        return self.param * ConfidenceComparer._compare_by_time(c1, c2) + \
            (1 - self.param) * ConfidenceComparer._compare_by_confidence(c1, c2)

    def compare_int(self, c1: Confidence, c2: Confidence) -> int:
        """
        Compare two confidences, returning the sign of their compared difference.
        :return: Value of either -1, 0 or 1, with -1 specifying c1 is smaller, 1 specifying c2 is smaller,
        and 0 specifying they are equal.
        """
        cmp = self.compare(c1, c2)
        return int(math.copysign(1, cmp))

    def get_key_sorter(self, getter: None | int | Callable[[Any], Confidence] = None) -> Callable | None:
        """
        Convert comparer to a key selector function (i.e., used in built-ins such as sum or sort).
        :param getter: Direction to the getter. Can be None, int as an index selector in lists of tuples,
        or Callable to get the value dynamically.
        :return: A Callable key selector usable for key=... arguments.
        """
        if getter is None:
            return None
        if isinstance(getter, int):
            getter = itemgetter(getter)
        return cmp_to_key(lambda be1, be2: self.compare_int(getter(be1), getter(be2)))

    @staticmethod
    def _compare_by_confidence(c1: Confidence, c2: Confidence) -> float:
        """
        Compares two confidences by how much their conformity (float() value), regardless of time.
        """

        c1imp = c1.nom == 0 and c1.denom == 0
        c2imp = c2.nom == 0 and c2.denom == 0
        if c1imp and c2imp:
            return 0
        if c1imp:
            return 0 - float(c2)
        if c2imp:
            return float(c1) - 0
        return float(c1) - float(c2)

    @staticmethod
    def _compare_by_time(c1: Confidence, c2: Confidence) -> float:
        """
        Compares two confidences by their reliability (total conforming time).
        """

        if c1.nom == c2.nom:
            return 0

        if c1.nom >= c2.nom:
            nom_div = c2.nom / c1.nom
            return 1 - nom_div
        else:
            nom_div = c1.nom / c2.nom
            return nom_div - 1

    @staticmethod
    def ConformityBased() -> ConfidenceComparer:
        return ConfidenceComparer(0.01)

    @staticmethod
    def ReliabilityBased() -> ConfidenceComparer:
        return ConfidenceComparer(0.99)
