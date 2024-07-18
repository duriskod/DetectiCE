from enum import Enum


# ("Speed") Unary - speed of agent's movement
class Speed(Enum):
    STAND = "Stand"
    WALK = "Walk"
    RUN = "Run"


# ("Direction") Unary - direction of movement w.r.t. previous movement
# ("RelativeDirection") Binary - direction of movement w.r.t. second agent
class Direction(Enum):
    NOT_MOVING = "NotMoving"
    LEFT = "Left"
    STRAIGHT = "Straight"
    RIGHT = "Right"
    OPPOSITE = "Opposite"


# ("MutualDirection") Binary - relation of directions of both agents
class MutualDirection(Enum):
    PARALLEL = "Parallel"
    INDEPENDENT = "Independent"
    OPPOSITE = "Opposite"


# ("IntendedDistanceChange") Binary - change of distance w.r.t last position of other agent
# ("ActualDistanceChange") Binary - change of distance between both agents
class DistanceChange(Enum):
    DECREASING = "Decreasing"
    CONSTANT = "Constant"
    INCREASING = "Increasing"


# ("Distance") Binary - distance between two agents
class Distance(Enum):
    ADJACENT = "Adjacent"
    NEAR = "Near"
    FAR = "Far"
