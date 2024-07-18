from datetime import datetime

from ..data import Confidence

BacktrackEntry = tuple[int, int, Confidence]
""" [index of parent in prev. layer, index of prev. path segment in parent, incoming confidence] """
BacktrackInfo = list[BacktrackEntry]
""" List of all confident incoming edges of a node. """
BacktrackInfoRow = list[BacktrackInfo]
""" List of BacktrackInfo for specific depth. """
BacktrackMap = list[BacktrackInfoRow]
""" 2D matrix representing confident edges for whole graph. """
ContractedPathEntry = tuple[list[int], Confidence]
""" Entry for single known path in contracted layer's memory. """

ContractedTimetableEntry = tuple[list[datetime], Confidence]
