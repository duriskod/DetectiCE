from enum import Enum

from behavior.data.confidence import ConfidenceComparer


class ConfidenceConjunctionStrategy(Enum):
    MIN = 1,
    AVG = 2


class Configuration:
    confidence_coefficient = 0.05
    """
    Coefficient used when comparing confidence, between 0.0 - 1.0.
    0.0 - Favours accuracy (comparison of conf. cast to floats).
    1.0 - Favours length (comparison of conf. nominators, clamped to -1..1).
    """
    comparer = ConfidenceComparer(confidence_coefficient)

    min_confidence: float = 0.65
    """Confidence limit for pruning time graph paths."""

    max_memory: int = 3
    """Limit for maximum paths kept in each node in time graph computing."""

    debug: bool = False
    """Debug mode triggers some additional steps for computing (for better information during breakpoint inspection)"""

    confidence_conjunction_strategy: ConfidenceConjunctionStrategy = ConfidenceConjunctionStrategy.AVG
