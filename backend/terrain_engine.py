"""Deterministic, dependency-free terrain and routing kernel for EoV."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import heapq
from typing import Any, Mapping, Optional


Position = tuple[int, int]


@dataclass(frozen=True)
class MaterialLayer:
    material: str
    depth_cm: int
    stock: int


@dataclass(frozen=True)
class SurfaceFeature:
    kind: str
    material: str
    stock: int


@dataclass(frozen=True)
class TerrainTile:
    position: Position
    terrain: str
    elevation: int
    travel_cost_milli: int
    passable: bool
    surface: Optional[SurfaceFeature]
    substrate: tuple[MaterialLayer, ...]


@dataclass(frozen=True)
class RouteResult:
    reached: bool
    path: tuple[Position, ...]
    cost_milli: int
    reason: Optional[str] = None


class FrontierGrid:
    """Generate a bounded frontier without mutable random state."""

    _NEIGHBORS: tuple[Position, ...] = ((0, -1), (-1, 0), (1, 0), (0, 1))

    def __init__(self, seed: int, size: int = 64):
        if size <= 0:
            raise ValueError("frontier size must be positive")
        self.seed = int(seed)
        self.size = int(size)

    def _sample(self, x: int, y: int, channel: str, modulus: int = 10_000) -> int:
        payload = f"{self.seed}:{x}:{y}:{channel}".encode("utf-8")
        digest = hashlib.blake2b(payload, digest_size=8).digest()
        return int.from_bytes(digest, "big") % modulus

    def _validate(self, x: int, y: int) -> None:
        if not (0 <= x < self.size and 0 <= y < self.size):
            raise ValueError(f"tile ({x}, {y}) is outside the {self.size}x{self.size} frontier")

    def tile_at(self, x: int, y: int) -> TerrainTile:
        self._validate(x, y)
        terrain_roll = self._sample(x, y, "terrain")
        near_settlement = abs(x - 8) + abs(y - 9) <= 9
        if not near_settlement and terrain_roll < 900:
            terrain, passable, travel = "water", False, 4_000
        elif terrain_roll < 2_200:
            terrain, passable, travel = "forest", True, 1_450
        elif terrain_roll < 3_100:
            terrain, passable, travel = "rocky", True, 1_700
        elif terrain_roll < 3_800:
            terrain, passable, travel = "wetland", True, 2_100
        else:
            terrain, passable, travel = "grassland", True, 1_000

        elevation = self._sample(x, y, "elevation", 5)
        surface_roll = self._sample(x, y, "surface")
        surface: Optional[SurfaceFeature] = None
        if terrain == "forest" and surface_roll < 7_500:
            surface = SurfaceFeature("tree", "timber", 4 + self._sample(x, y, "surface-stock", 9))
        elif terrain == "rocky" and surface_roll < 4_500:
            surface = SurfaceFeature("outcrop", "stone", 3 + self._sample(x, y, "surface-stock", 8))

        soil_stock = 4 + self._sample(x, y, "soil-stock", 9)
        mineral_roll = self._sample(x, y, "mineral")
        mineral = "clay" if mineral_roll < 3_800 else "stone" if mineral_roll < 8_800 else "iron_ore"
        substrate = (
            MaterialLayer("soil", 40, soil_stock),
            MaterialLayer(mineral, 120, 3 + self._sample(x, y, "mineral-stock", 10)),
        )
        return TerrainTile((x, y), terrain, elevation, travel, passable, surface, substrate)

    def neighbors(self, position: Position) -> list[Position]:
        x, y = position
        self._validate(x, y)
        return [
            (x + dx, y + dy)
            for dx, dy in self._NEIGHBORS
            if 0 <= x + dx < self.size and 0 <= y + dy < self.size
        ]

    def find_route(
        self,
        start: Position,
        goal: Position,
        *,
        known: set[Position],
        modifications: Mapping[str, Mapping[str, Any]],
    ) -> RouteResult:
        self._validate(*start)
        self._validate(*goal)
        if goal not in known:
            return RouteResult(False, (start,), 0, "destination_unknown")
        if start == goal:
            return RouteResult(True, (start,), 0)

        frontier: list[tuple[int, int, Position]] = [(0, 0, start)]
        came_from: dict[Position, Position] = {}
        costs: dict[Position, int] = {start: 0}
        sequence = 0
        while frontier:
            _, _, current = heapq.heappop(frontier)
            if current == goal:
                break
            for neighbor in self.neighbors(current):
                if neighbor not in known:
                    continue
                tile = self.tile_at(*neighbor)
                override = modifications.get(f"{neighbor[0]},{neighbor[1]}", {})
                passable = bool(override.get("passable", tile.passable))
                if not passable:
                    continue
                step_cost = int(override.get("travel_cost_milli", tile.travel_cost_milli))
                candidate = costs[current] + step_cost
                if candidate >= costs.get(neighbor, 2**63 - 1):
                    continue
                costs[neighbor] = candidate
                came_from[neighbor] = current
                sequence += 1
                heuristic = (abs(goal[0] - neighbor[0]) + abs(goal[1] - neighbor[1])) * 1_000
                heapq.heappush(frontier, (candidate + heuristic, sequence, neighbor))

        if goal not in came_from:
            return RouteResult(False, (start,), 0, "no_known_route")
        path = [goal]
        while path[-1] != start:
            path.append(came_from[path[-1]])
        path.reverse()
        return RouteResult(True, tuple(path), costs[goal])
