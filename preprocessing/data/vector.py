import math


class Vector2:
    x: float
    y: float

    def __init__(self, x: float = 0, y: float = 0):
        self.x = x
        self.y = y

    @property
    def magnitude(self) -> float:
        return math.hypot(self.x, self.y)

    @property
    def normalized(self) -> "Vector2":
        mag = self.magnitude
        return self / mag

    @property
    def angle(self) -> float:
        angle = math.atan2(self.y, self.x)
        if angle < -math.pi:
            angle = 360 + angle
        if angle > math.pi:
            angle = angle - 360
        return angle

    @property
    def angle_degrees(self) -> float:
        return math.degrees(self.angle)

    def __neg__(self):
        return Vector2(-self.x, -self.y)

    def __add__(self, other: "Vector2"):
        if not isinstance(other, Vector2):
            raise TypeError(f"Invalid operation: Vector2 + {type(other)}")
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2"):
        if not isinstance(other, Vector2):
            raise TypeError(f"Invalid operation: Vector2 - {type(other)}")
        return self + -other

    def __mul__(self, other: float):
        return Vector2(self.x * other, self.y * other)

    def __truediv__(self, other: float):
        return Vector2(self.x / other, self.y / other)

    def __eq__(self, other: "Vector2"):
        if not isinstance(other, Vector2):
            return False
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        return f"Vector2({self.x}, {self.y})"
