"""
Pathfinding algorithm for the Fly-Yeet drone routing simulation.

Provides a :class:`Pathfinder` that computes shortest paths through
the hub graph, respecting zone-type movement costs.

Graph libraries are intentionally avoided — this is a from-scratch
BFS / Dijkstra-style implementation.
"""
from __future__ import annotations

from collections import deque
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

    The algorithm is a simple BFS on an unweighted graph, augmented to
    account for zone-type movement costs (restricted = 2 turns).
    Because restricted zones still allow passage (just slower), a BFS
    still produces correct shortest-hop paths; the simulation handles
    the turn cost at movement time.
    """

    def __init__(self, map_gui_obj: gui.Map_gui) -> None:
        self.map_gui: gui.Map_gui = map_gui_obj
        # Build adjacency once
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
    ) -> Optional[list[str]]:
        """Return the shortest path (list of hub names) from *start_name*
        to *end_name*, or ``None`` if unreachable.

        Uses BFS since all edges have equal hop cost.  Zone-type turn
        costs are handled by the simulation, not the pathfinder.
        """
        if start_name == end_name:
            return [start_name]

        visited: dict[str, Optional[str]] = {start_name: None}
        queue: deque[str] = deque([start_name])

        while queue:
            current: str = queue.popleft()

            for neighbor in self.get_neighbors(current):
                if neighbor in visited:
                    continue

                # Skip blocked zones
                hub = self.map_gui.hubs.get(neighbor)
                if hub is not None and hub.zone_type == "blocked":
                    continue

                visited[neighbor] = current
                if neighbor == end_name:
                    # Reconstruct path
                    path: list[str] = []
                    node: Optional[str] = end_name
                    while node is not None:
                        path.append(node)
                        node = visited[node]
                    path.reverse()
                    return path

                queue.append(neighbor)

        return None  # unreachable

    def movement_cost(self, to_hub_name: str) -> int:
        """Return the turn cost to move **into** the named hub."""
        hub = self.map_gui.hubs.get(to_hub_name)
        if hub is None:
            return 1
        return _ZONE_COST.get(hub.zone_type, 1)
