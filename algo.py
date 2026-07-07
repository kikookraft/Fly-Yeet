"""
Pathfinding algorithm for the Fly-Yeet drone routing simulation.

Provides a :class:`Pathfinder` that computes shortest paths through
the hub graph, respecting zone-type movement costs, and distributes
drones across multiple disjoint routes to maximise throughput.

Graph libraries are intentionally avoided — this is a from-scratch
Dijkstra-style implementation.
"""
from __future__ import annotations

import heapq
from typing import Optional

import gui


# Movement cost (turns) per destination zone type
_ZONE_COST: dict[str, int] = {
    "normal": 1,
    "priority": 1,
    "restricted": 2,
    "blocked": 999_999,  # inaccessible
}


class Pathfinder:
    """Computes shortest paths on a :class:`~gui.Map_gui` graph.

    Uses Dijkstra's algorithm with edge weights derived from zone-type
    movement costs (restricted = 2 turns, normal/priority = 1 turn).
    Also computes alternative paths for multi-drone distribution.
    """

    def __init__(self, map_gui_obj: gui.Map_gui) -> None:
        self.map_gui: gui.Map_gui = map_gui_obj
        self._neighbors: dict[str, list[str]] = {}
        self._build_adjacency()

    # ------------------------------------------------------------------
    # Adjacency
    # ------------------------------------------------------------------

    def _build_adjacency(self) -> None:
        """Populate :attr:`_neighbors` from the map's connections."""
        self._neighbors.clear()
        for conn in self.map_gui.connections:
            self._neighbors.setdefault(conn.hub_a.name, []).append(
                conn.hub_b.name
            )
            self._neighbors.setdefault(conn.hub_b.name, []).append(
                conn.hub_a.name
            )

    def get_neighbors(self, hub_name: str) -> list[str]:
        """Return the names of hubs directly connected to *hub_name*."""
        return self._neighbors.get(hub_name, [])

    # ------------------------------------------------------------------
    # Path computation
    # ------------------------------------------------------------------

    def shortest_path(
        self,
        start_name: str,
        end_name: str,
        edge_penalty: Optional[dict[tuple[str, str], float]] = None,
    ) -> Optional[list[str]]:
        """Return the shortest path from *start_name* to *end_name*.

        Uses Dijkstra with turn-cost weights.  Optionally applies extra
        cost to edges listed in *edge_penalty* to discover diverse routes.

        Args:
            start_name: Name of the start hub.
            end_name: Name of the destination hub.
            edge_penalty: Mapping of (a, b) → extra cost to add.

        Returns:
            List of hub names forming the path, or ``None``.
        """
        if start_name == end_name:
            return [start_name]

        penalties: dict[tuple[str, str], float] = edge_penalty or {}

        # Dijkstra: (cost, hub_name, parent)
        dist: dict[str, float] = {start_name: 0}
        parent: dict[str, Optional[str]] = {start_name: None}
        heap: list[tuple[float, str]] = [(0, start_name)]

        while heap:
            cost, current = heapq.heappop(heap)
            if cost > dist.get(current, float("inf")):
                continue
            if current == end_name:
                break

            for neighbor in self.get_neighbors(current):
                # Normalise edge key
                edge: tuple[str, str] = (
                    (current, neighbor)
                    if current < neighbor
                    else (neighbor, current)
                )

                # Skip blocked zones
                hub = self.map_gui.hubs.get(neighbor)
                if hub is not None and hub.zone_type == "blocked":
                    continue

                edge_cost: float = float(
                    _ZONE_COST.get(
                        hub.zone_type if hub else "normal", 1
                    )
                )
                # Apply penalty for edges used by previous paths
                edge_cost += penalties.get(edge, 0.0)

                new_cost: float = cost + edge_cost
                if new_cost < dist.get(neighbor, float("inf")):
                    dist[neighbor] = new_cost
                    parent[neighbor] = current
                    heapq.heappush(heap, (new_cost, neighbor))

        if end_name not in parent:
            return None

        # Reconstruct path
        path: list[str] = []
        node: Optional[str] = end_name
        while node is not None:
            path.append(node)
            node = parent[node]
        path.reverse()
        return path

    def all_paths(
        self,
        start_name: str,
        end_name: str,
        max_paths: int = 20,
    ) -> list[list[str]]:
        """Compute up to *max_paths* diverse paths from start to end.

        Uses a penalty-based approach: edges used by earlier paths receive
        a large extra cost (10× their base cost), encouraging truly
        different routes.  Paths whose **unpenalized** cost exceeds 1.3×
        the shortest-path cost are discarded — detours through cycles or
        dead ends are never useful for throughput.

        Args:
            start_name: Name of the start hub.
            end_name: Name of the destination hub.
            max_paths: Maximum number of paths to return.

        Returns:
            A list of paths (each a list of hub names).  Always at
            least one path if reachable.
        """
        first: Optional[list[str]] = self.shortest_path(
            start_name, end_name
        )
        if first is None:
            return []

        # Unpenalized cost of the true shortest path
        best_cost: float = self._path_unpenalized_cost(first)
        cost_limit: float = best_cost * 1.2

        paths: list[list[str]] = [first]
        penalty: dict[tuple[str, str], float] = {}

        # Add heavy penalty for edges in the first path
        for i in range(len(first) - 1):
            a, b = first[i], first[i + 1]
            edge: tuple[str, str] = (a, b) if a < b else (b, a)
            hub = self.map_gui.hubs.get(b)
            base: float = float(
                _ZONE_COST.get(hub.zone_type if hub else "normal", 1)
            )
            penalty[edge] = penalty.get(edge, 0.0) + base * 10.0

        for _ in range(max_paths - 1):
            alt: Optional[list[str]] = self.shortest_path(
                start_name, end_name, edge_penalty=penalty
            )
            if alt is None:
                break

            # Skip duplicates and detours
            if alt in paths:
                for i in range(len(alt) - 1):
                    a, b = alt[i], alt[i + 1]
                    edge = (a, b) if a < b else (b, a)
                    penalty[edge] = penalty.get(edge, 0.0) + 100.0
                continue

            alt_cost: float = self._path_unpenalized_cost(alt)
            if alt_cost > cost_limit:
                # This "alternative" is a detour — heavily penalize
                # it so we don't keep finding the same bad route.
                for i in range(len(alt) - 1):
                    a, b = alt[i], alt[i + 1]
                    edge = (a, b) if a < b else (b, a)
                    penalty[edge] = penalty.get(edge, 0.0) + 100.0
                continue

            paths.append(alt)
            for i in range(len(alt) - 1):
                a, b = alt[i], alt[i + 1]
                edge = (a, b) if a < b else (b, a)
                hub = self.map_gui.hubs.get(b)
                base = float(
                    _ZONE_COST.get(
                        hub.zone_type if hub else "normal", 1
                    )
                )
                penalty[edge] = penalty.get(edge, 0.0) + base * 10.0

        return paths

    def _path_unpenalized_cost(self, path: list[str]) -> float:
        """Return the raw turn cost of *path* (no penalties)."""
        total: float = 0.0
        for i in range(len(path) - 1):
            hub = self.map_gui.hubs.get(path[i + 1])
            total += float(
                _ZONE_COST.get(
                    hub.zone_type if hub else "normal", 1
                )
            )
        return total

    def movement_cost(self, to_hub_name: str) -> int:
        """Return the turn cost to move **into** the named hub."""
        hub = self.map_gui.hubs.get(to_hub_name)
        if hub is None:
            return 1
        return _ZONE_COST.get(hub.zone_type, 1)
