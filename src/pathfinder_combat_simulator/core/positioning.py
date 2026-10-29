from enum import Enum, auto
from typing import Set, Optional, Tuple
from dataclasses import dataclass, field


class Size(Enum):
    FINE = "fine"
    DIMINUTIVE = "diminutive"
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"
    GARGANTUAN = "gargantuan"
    COLOSSAL = "colossal"

    def space_ft(self) -> int:
        spaces = {
            Size.FINE: 0.5,
            Size.DIMINUTIVE: 1,
            Size.TINY: 2.5,
            Size.SMALL: 5,
            Size.MEDIUM: 5,
            Size.LARGE: 10,
            Size.HUGE: 15,
            Size.GARGANTUAN: 20,
            Size.COLOSSAL: 30,
        }
        return int(spaces[self])

    def reach_ft(self, tall: bool = True) -> int:
        reaches = {
            Size.FINE: 0,
            Size.DIMINUTIVE: 0,
            Size.TINY: 0,
            Size.SMALL: 5,
            Size.MEDIUM: 5,
            Size.LARGE: 10,
            Size.HUGE: 15,
            Size.GARGANTUAN: 20,
            Size.COLOSSAL: 30,
        }
        return reaches[self]

    @staticmethod
    def from_string(s: str) -> "Size":
        mapping = {size.value: size for size in Size}
        normalized = s.lower().strip()
        return mapping.get(normalized, Size.MEDIUM)


class Facing(Enum):
    NORTH = auto()
    NORTHEAST = auto()
    EAST = auto()
    SOUTHEAST = auto()
    SOUTH = auto()
    SOUTHWEST = auto()
    WEST = auto()
    NORTHWEST = auto()


class MovementType(Enum):
    LAND = "land"
    FLY = "fly"
    SWIM = "swim"
    CLIMB = "climb"
    BURROW = "burrow"


@dataclass(frozen=True)
class Position:
    x: int
    y: int
    z: int = 0

    def distance_to(self, other: "Position") -> float:
        return max(abs(self.x - other.x), abs(self.y - other.y), abs(self.z - other.z))

    def adjacent_to(self, other: "Position") -> bool:
        return self.distance_to(other) <= 1 and self != other

    def __add__(self, other: "Position") -> "Position":
        return Position(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Position") -> "Position":
        return Position(self.x - other.x, self.y - other.y, self.z - other.z)


@dataclass
class CombatantPosition:
    position: Position
    size: Size = Size.MEDIUM
    facing: Facing = Facing.NORTH
    altitude: int = 0

    def get_threatened_squares(self, reach: int = 5) -> Set[Position]:
        threatened = set()
        space = self.size.space_ft()
        squares_occupied = space // 5

        min_x = self.position.x
        max_x = self.position.x + squares_occupied - 1
        min_y = self.position.y
        max_y = self.position.y + squares_occupied - 1

        reach_squares = reach // 5

        for dx in range(-reach_squares - squares_occupied + 1, reach_squares + squares_occupied):
            for dy in range(-reach_squares - squares_occupied + 1, reach_squares + squares_occupied):
                for ox in range(min_x, max_x + 1):
                    for oy in range(min_y, max_y + 1):
                        tx = ox + dx
                        ty = oy + dy
                        if (min_x <= tx <= max_x and min_y <= ty <= max_y):
                            continue
                        dist = max(abs(tx - ox), abs(ty - oy))
                        if 1 <= dist <= reach_squares:
                            threatened.add(Position(tx, ty, self.position.z))

        return threatened
